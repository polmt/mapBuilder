#!/usr/bin/env python3
"""
ArcGIS to MBTiles with MGRS Grid Overlay and Zone Labels
Creates .mbtiles files from ArcGIS map services with MGRS military grid overlays
Shows MGRS zone identifiers (first 5 characters) only at zone boundaries
Reads configuration from JSON files
"""

import os
import sys
import sqlite3
import requests
import math
import logging
import json
import argparse
from typing import Tuple, List, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont

    print("PASS: PIL (Pillow) imported successfully")
except ImportError as e:
    print(f"FAIL: Failed to import PIL: {e}")
    sys.exit(1)

try:
    import mercantile

    print("PASS: mercantile imported successfully")
except ImportError as e:
    print(f"FAIL: Failed to import mercantile: {e}")
    sys.exit(1)

try:
    import mgrs

    print("PASS: mgrs imported successfully")
except ImportError as e:
    print(f"FAIL: Failed to import mgrs: {e}")
    sys.exit(1)

try:
    from pyproj import Transformer

    print("PASS: pyproj imported successfully")
except ImportError as e:
    print(f"FAIL: Failed to import pyproj: {e}")
    print("Note: pyproj installation can be tricky on Windows.")
    print("Try: pip install --upgrade pyproj")
    print("Or: conda install pyproj")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TileRegion:
    """Configuration for a tile region"""
    map_url: str
    name: str
    bounds: Tuple[float, float, float, float]  # (west, south, east, north)
    zoom_min: int
    zoom_max: int
    output_file: str


def load_config_from_json(json_file: str) -> TileRegion:
    """Load configuration from JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Validate required fields
        required_fields = ['MAP_URL', 'name', 'lat_min', 'long_min', 'lat_max', 'long_max', 'zoom_min', 'zoom_max',
                           'output_file']
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            raise ValueError(f"Missing required fields in {json_file}: {missing_fields}")

        # Convert coordinates to bounds tuple (west, south, east, north)
        bounds = (
            float(config['long_min']),  # west
            float(config['lat_min']),  # south
            float(config['long_max']),  # east
            float(config['lat_max'])  # north
        )

        # Validate bounds
        if bounds[0] >= bounds[2]:  # west >= east
            raise ValueError(f"Invalid longitude bounds in {json_file}: long_min must be < long_max")
        if bounds[1] >= bounds[3]:  # south >= north
            raise ValueError(f"Invalid latitude bounds in {json_file}: lat_min must be < lat_max")

        # Validate zoom levels
        zoom_min = int(config['zoom_min'])
        zoom_max = int(config['zoom_max'])
        if zoom_min > zoom_max:
            raise ValueError(f"Invalid zoom levels in {json_file}: zoom_min must be <= zoom_max")
        if zoom_min < 0 or zoom_max > 22:
            raise ValueError(f"Invalid zoom levels in {json_file}: must be between 0 and 22")

        return TileRegion(
            map_url=config['MAP_URL'].rstrip('/'),
            name=config['name'],
            bounds=bounds,
            zoom_min=zoom_min,
            zoom_max=zoom_max,
            output_file=config['output_file']
        )

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {json_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {json_file}: {e}")
        raise
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Configuration error in {json_file}: {e}")
        raise


class MGRSGridGenerator:
    """Generate MGRS grid overlays for map tiles with zone labels"""

    def __init__(self):
        self.mgrs_converter = mgrs.MGRS()
        # Transformer for coordinate conversions
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        self.reverse_transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    def get_mgrs_precision_for_zoom(self, zoom: int) -> int:
        """Determine MGRS precision based on zoom level"""
        if zoom <= 6:
            return 1  # 100km squares
        elif zoom <= 10:
            return 2  # 10km squares
        elif zoom <= 13:
            return 3  # 1km squares
        elif zoom <= 16:
            return 4  # 100m squares
        else:
            return 5  # 10m squares

    def tile_to_lat_lon(self, tile_x: int, tile_y: int, zoom: int) -> Tuple[float, float, float, float]:
        """Convert tile coordinates to lat/lon bounds"""
        bbox = mercantile.bounds(tile_x, tile_y, zoom)
        return (bbox.west, bbox.south, bbox.east, bbox.north)

    def lat_lon_to_pixel(self, lat: float, lon: float, tile_bounds: Tuple[float, float, float, float],
                         tile_size: int = 256) -> Tuple[int, int]:
        """Convert lat/lon to pixel coordinates within a tile"""
        west, south, east, north = tile_bounds

        # Calculate relative position within tile bounds
        x_ratio = (lon - west) / (east - west)
        y_ratio = (north - lat) / (north - south)  # Note: inverted for image coordinates

        # Convert to pixel coordinates
        pixel_x = int(x_ratio * tile_size)
        pixel_y = int(y_ratio * tile_size)

        return (pixel_x, pixel_y)

    def get_mgrs_zones_in_tile(self, tile_bounds: Tuple[float, float, float, float]) -> Set[str]:
        """Get all unique MGRS zone identifiers (first 5 chars) in a tile"""
        west, south, east, north = tile_bounds
        zones = set()

        # Sample points across the tile to find zone boundaries
        sample_points = 10  # Number of sample points per dimension
        lat_step = (north - south) / sample_points
        lon_step = (east - west) / sample_points

        for i in range(sample_points + 1):
            for j in range(sample_points + 1):
                lat = south + i * lat_step
                lon = west + j * lon_step

                try:
                    mgrs_code = self.mgrs_converter.toMGRS(lat, lon, MGRSPrecision=5)
                    # Get first 5 characters (zone + band + square)
                    zone_id = mgrs_code[:5]
                    zones.add(zone_id)
                except:
                    pass  # Skip invalid coordinates

        return zones

    def find_zone_boundaries(self, tile_bounds: Tuple[float, float, float, float]) -> List[dict]:
        """Find locations where MGRS zones change within a tile"""
        west, south, east, north = tile_bounds
        zone_labels = []

        # Get zones in this tile
        zones = self.get_mgrs_zones_in_tile(tile_bounds)

        if len(zones) <= 1:
            # Only one zone, place label in center
            if zones:
                center_lat = (north + south) / 2
                center_lon = (east + west) / 2
                zone_labels.append({
                    'zone_id': list(zones)[0],
                    'lat': center_lat,
                    'lon': center_lon
                })
        else:
            # Multiple zones, find boundaries
            sample_resolution = 20  # Higher resolution for boundary detection
            lat_step = (north - south) / sample_resolution
            lon_step = (east - west) / sample_resolution

            found_zones = set()

            # Scan the tile for zone transitions
            for i in range(0, sample_resolution + 1, 5):  # Sample every 5th point
                for j in range(0, sample_resolution + 1, 5):
                    lat = south + i * lat_step
                    lon = west + j * lon_step

                    try:
                        mgrs_code = self.mgrs_converter.toMGRS(lat, lon, MGRSPrecision=5)
                        zone_id = mgrs_code[:5]

                        if zone_id not in found_zones:
                            zone_labels.append({
                                'zone_id': zone_id,
                                'lat': lat,
                                'lon': lon
                            })
                            found_zones.add(zone_id)

                    except:
                        pass  # Skip invalid coordinates

        return zone_labels

    def get_mgrs_grid_lines(self, tile_bounds: Tuple[float, float, float, float],
                            zoom: int) -> List[dict]:
        """Generate MGRS grid lines for a tile"""
        west, south, east, north = tile_bounds
        precision = self.get_mgrs_precision_for_zoom(zoom)
        grid_lines = []

        # Grid spacing in degrees (approximate)
        if precision == 1:  # 100km
            spacing = 1.0
        elif precision == 2:  # 10km
            spacing = 0.1
        elif precision == 3:  # 1km
            spacing = 0.01
        elif precision == 4:  # 100m
            spacing = 0.001
        else:  # 10m
            spacing = 0.0001

        # Generate vertical lines (longitude)
        lon = math.floor(west / spacing) * spacing
        while lon <= east:
            if west <= lon <= east:
                grid_lines.append({
                    'type': 'vertical',
                    'coordinate': lon
                })
            lon += spacing

        # Generate horizontal lines (latitude)
        lat = math.floor(south / spacing) * spacing
        while lat <= north:
            if south <= lat <= north:
                grid_lines.append({
                    'type': 'horizontal',
                    'coordinate': lat
                })
            lat += spacing

        return grid_lines

    def draw_mgrs_overlay(self, image: Image.Image, tile_x: int, tile_y: int, zoom: int) -> Image.Image:
        """Draw MGRS grid overlay with zone labels on a tile image"""
        tile_bounds = self.tile_to_lat_lon(tile_x, tile_y, zoom)
        grid_lines = self.get_mgrs_grid_lines(tile_bounds, zoom)
        zone_labels = self.find_zone_boundaries(tile_bounds)

        # Create a copy to draw on
        img_with_grid = image.copy()
        draw = ImageDraw.Draw(img_with_grid)

        # Try to load a font, fall back to default if not available
        try:
            # Windows font paths
            if os.name == 'nt':  # Windows
                font_paths = [
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/calibri.ttf",
                    "C:/Windows/Fonts/tahoma.ttf"
                ]
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, 14)  # Slightly larger for zone labels
                        break
                if font is None:
                    font = ImageFont.load_default()
            else:
                # Linux/Mac
                font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()

        # Draw grid lines
        for line in grid_lines:
            if line['type'] == 'vertical':
                # Vertical line
                lon = line['coordinate']
                x1, _ = self.lat_lon_to_pixel(tile_bounds[1], lon, tile_bounds)  # south
                x2, _ = self.lat_lon_to_pixel(tile_bounds[3], lon, tile_bounds)  # north

                if 0 <= x1 <= 256:
                    draw.line([(x1, 0), (x1, 256)], fill='red', width=1)

            elif line['type'] == 'horizontal':
                # Horizontal line
                lat = line['coordinate']
                _, y1 = self.lat_lon_to_pixel(lat, tile_bounds[0], tile_bounds)  # west
                _, y2 = self.lat_lon_to_pixel(lat, tile_bounds[2], tile_bounds)  # east

                if 0 <= y1 <= 256:
                    draw.line([(0, y1), (256, y1)], fill='red', width=1)

        # Draw zone labels only at zone boundaries/centers
        for label in zone_labels:
            pixel_x, pixel_y = self.lat_lon_to_pixel(label['lat'], label['lon'], tile_bounds)

            # Only draw if the label position is within the tile
            if 10 <= pixel_x <= 246 and 10 <= pixel_y <= 246:  # Leave some margin
                # Draw background rectangle for better readability
                text = label['zone_id']
                bbox = draw.textbbox((pixel_x, pixel_y), text, font=font)

                # Add padding to background
                bg_bbox = (bbox[0] - 2, bbox[1] - 1, bbox[2] + 2, bbox[3] + 1)
                draw.rectangle(bg_bbox, fill='white', outline='red')

                # Draw the zone identifier text
                draw.text((pixel_x, pixel_y), text, fill='red', font=font)

        return img_with_grid


class MBTilesCreator:
    """Create MBTiles files from ArcGIS services with MGRS overlays"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.mgrs_generator = MGRSGridGenerator()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def init_mbtiles_schema(self, conn: sqlite3.Connection, metadata: dict):
        """Initialize MBTiles database schema"""
        # Create tables
        conn.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                name TEXT,
                value TEXT
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS tiles (
                zoom_level INTEGER,
                tile_column INTEGER,
                tile_row INTEGER,
                tile_data BLOB
            )
        ''')

        # Create index
        conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS tile_index 
            ON tiles (zoom_level, tile_column, tile_row)
        ''')

        # Insert metadata
        for key, value in metadata.items():
            conn.execute('INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)',
                         (key, str(value)))

        conn.commit()

    def download_tile(self, map_url: str, z: int, x: int, y: int) -> Optional[bytes]:
        """Download a single tile from ArcGIS service"""
        # ArcGIS REST API tile URL format
        tile_url = f"{map_url}/tile/{z}/{y}/{x}"

        try:
            response = self.session.get(tile_url, timeout=30)
            response.raise_for_status()

            # Check if we got a valid image
            if response.headers.get('content-type', '').startswith('image/'):
                return response.content
            else:
                logger.warning(f"Invalid content type for tile {z}/{x}/{y}: {response.headers.get('content-type')}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download tile {z}/{x}/{y}: {e}")
            return None

    def process_tile(self, tile_info: Tuple[str, int, int, int]) -> Tuple[int, int, int, Optional[bytes]]:
        """Process a single tile - download and add MGRS overlay"""
        map_url, z, x, y = tile_info

        # Download base tile
        tile_data = self.download_tile(map_url, z, x, y)
        if not tile_data:
            return (z, x, y, None)

        try:
            # Load image and add MGRS overlay
            image = Image.open(BytesIO(tile_data))
            image_with_mgrs = self.mgrs_generator.draw_mgrs_overlay(image, x, y, z)

            # Convert back to bytes
            output_buffer = BytesIO()
            image_with_mgrs.save(output_buffer, format='PNG')
            return (z, x, y, output_buffer.getvalue())

        except Exception as e:
            logger.error(f"Failed to process tile {z}/{x}/{y}: {e}")
            return (z, x, y, None)

    def create_mbtiles(self, region: TileRegion):
        """Create MBTiles file for a region"""
        logger.info(f"Creating {region.name} MBTiles file: {region.output_file}")
        logger.info(f"Map URL: {region.map_url}")
        logger.info(f"Bounds: {region.bounds}")
        logger.info(f"Zoom levels: {region.zoom_min}-{region.zoom_max}")

        # Calculate total number of tiles
        total_tiles = 0
        for z in range(region.zoom_min, region.zoom_max + 1):
            tiles = list(mercantile.tiles(*region.bounds, z))
            total_tiles += len(tiles)

        logger.info(f"Total tiles to process: {total_tiles}")

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(region.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Create database
        conn = sqlite3.connect(region.output_file)

        # Metadata
        metadata = {
            'name': region.name,
            'type': 'baselayer',
            'version': '1.0',
            'description': f'{region.name} with MGRS grid overlay and zone labels',
            'format': 'png',
            'bounds': f"{region.bounds[0]},{region.bounds[1]},{region.bounds[2]},{region.bounds[3]}",
            'minzoom': region.zoom_min,
            'maxzoom': region.zoom_max
        }

        self.init_mbtiles_schema(conn, metadata)

        processed_tiles = 0
        start_time = time.time()

        # Process tiles by zoom level
        for z in range(region.zoom_min, region.zoom_max + 1):
            logger.info(f"Processing zoom level {z}")

            # Get all tiles for this zoom level
            tiles = list(mercantile.tiles(*region.bounds, z))
            tile_coords = [(region.map_url, z, tile.x, tile.y) for tile in tiles]

            # Process tiles in batches with threading
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_tile = {executor.submit(self.process_tile, tile_coord): tile_coord
                                  for tile_coord in tile_coords}

                for future in as_completed(future_to_tile):
                    z, x, y, tile_data = future.result()

                    if tile_data:
                        # Convert TMS y to XYZ y coordinate for MBTiles
                        tms_y = (2 ** z - 1) - y

                        # Insert tile into database
                        conn.execute(
                            'INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?, ?, ?, ?)',
                            (z, x, tms_y, tile_data)
                        )

                    processed_tiles += 1

                    # Progress update
                    if processed_tiles % 100 == 0:
                        elapsed = time.time() - start_time
                        tiles_per_second = processed_tiles / elapsed
                        remaining_tiles = total_tiles - processed_tiles
                        eta = remaining_tiles / tiles_per_second if tiles_per_second > 0 else 0

                        logger.info(f"Progress: {processed_tiles}/{total_tiles} tiles "
                                    f"({processed_tiles / total_tiles * 100:.1f}%) "
                                    f"Rate: {tiles_per_second:.1f} tiles/sec "
                                    f"ETA: {eta / 60:.1f} minutes")

            # Commit after each zoom level
            conn.commit()

        conn.close()

        elapsed = time.time() - start_time
        logger.info(f"Completed {region.name}: {processed_tiles} tiles in {elapsed / 60:.1f} minutes")


def create_example_configs():
    """Create example configuration files"""
    examples = [
        {
            "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer",
            "name": "World",
            "lat_min": -85.0511,
            "long_min": -180.0,
            "lat_max": 85.0511,
            "long_max": 180.0,
            "zoom_min": 0,
            "zoom_max": 6,
            "output_file": "world_with_mgrs_zones.mbtiles"
        },
        {
            "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer",
            "name": "Greece",
            "lat_min": 34.8,
            "long_min": 19.3,
            "lat_max": 41.7,
            "long_max": 29.6,
            "zoom_min": 7,
            "zoom_max": 13,
            "output_file": "greece_with_mgrs_zones.mbtiles"
        },
        {
            "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer",
            "name": "Attiki",
            "lat_min": 37.7,
            "long_min": 23.3,
            "lat_max": 38.3,
            "long_max": 24.1,
            "zoom_min": 14,
            "zoom_max": 18,
            "output_file": "attiki_with_mgrs_zones.mbtiles"
        }
    ]

    for i, config in enumerate(examples):
        filename = f"config_example_{i + 1}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"Created example configuration: {filename}")


def main():
    """Main function to create MBTiles files from JSON configurations"""
    parser = argparse.ArgumentParser(
        description="Create MBTiles files with MGRS grid overlays from JSON configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py config1.json
  python script.py config1.json config2.json config3.json
  python script.py --create-examples
  python script.py configs/*.json

JSON Configuration Format:
{
    "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer",
    "name": "Region Name",
    "lat_min": 34.8,
    "long_min": 19.3,
    "lat_max": 41.7,
    "long_max": 29.6,
    "zoom_min": 7,
    "zoom_max": 13,
    "output_file": "region_with_mgrs.mbtiles"
}
        """
    )

    parser.add_argument(
        'config_files',
        nargs='*',
        help='JSON configuration files to process'
    )

    parser.add_argument(
        '--create-examples',
        action='store_true',
        help='Create example configuration files and exit'
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='Maximum number of worker threads (default: 4)'
    )

    args = parser.parse_args()

    # Create example configurations if requested
    if args.create_examples:
        create_example_configs()
        return

    # Check if any configuration files were provided
    if not args.config_files:
        parser.print_help()
        print("\nError: No configuration files provided.")
        print("Use --create-examples to generate example configuration files.")
        sys.exit(1)

    # Load configurations from JSON files
    regions = []
    for config_file in args.config_files:
        try:
            region = load_config_from_json(config_file)
            regions.append(region)
            logger.info(f"Loaded configuration from {config_file}: {region.name}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")
            continue

    if not regions:
        logger.error("No valid configurations loaded. Exiting.")
        sys.exit(1)

    # Create MBTiles creator
    creator = MBTilesCreator(max_workers=args.max_workers)

    # Process each region
    success_count = 0
    for region in regions:
        try:
            creator.create_mbtiles(region)
            logger.info(f"Successfully created {region.output_file}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to create {region.name}: {e}")
            continue

    logger.info(f"Completed! Successfully created {success_count}/{len(regions)} MBTiles files.")

    # Windows-specific: Keep console window open
    if os.name == 'nt':
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
