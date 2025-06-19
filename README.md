# ArcGIS to MBTiles with MGRS Grid Overlay

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

A powerful Python tool that downloads map tiles from ArcGIS REST services and creates MBTiles files with Military Grid Reference System (MGRS) grid overlays. Perfect for military operations, emergency response, surveying, and any application requiring precise geographic reference systems.

## 🚀 Features

- **🗺️ Multiple Map Sources**: Support for any ArcGIS REST service (satellite imagery, topographic maps, etc.)
- **🎯 MGRS Grid Overlay**: Automatic Military Grid Reference System grid generation with zone labels
- **📱 MBTiles Output**: Industry-standard MBTiles format for offline map usage
- **⚙️ JSON Configuration**: Flexible configuration system for batch processing
- **🧵 Multi-threaded**: Concurrent tile downloading for optimal performance
- **🌍 Global Coverage**: Works worldwide with automatic coordinate system handling
- **📏 Adaptive Precision**: Grid precision automatically adjusts based on zoom level
- **🏷️ Smart Zone Labels**: Shows MGRS zone identifiers only at boundaries to reduce clutter
- **✅ Robust Error Handling**: Graceful failure recovery and detailed logging
- **🖥️ Cross-Platform**: Runs on Windows, Linux, and macOS

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [MGRS Grid System](#mgrs-grid-system)
- [Command Line Reference](#command-line-reference)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)
- [Contributing](#contributing)
- [License](#license)

## 🛠️ Installation

### Prerequisites

- **Python 3.7+** (Python 3.9+ recommended)
- **Internet connection** for downloading map tiles
- **~2GB disk space** for dependencies and generated tiles

### Step 1: Clone the Repository

```bash
git clone https://github.com/polmt/mapBuilder.git
cd mapBuilder
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python map_builder.py --help
```

If you see the help message, installation was successful!

## ⚡ Quick Start

### 1. Generate Example Configurations

```bash
python map_builder.py --create-examples
```

This creates three example configuration files:
- `config_example_1.json` - World overview (zoom 0-6)
- `config_example_2.json` - Greece detailed (zoom 7-13)
- `config_example_3.json` - Attiki high-res (zoom 14-18)

### 2. Process Your First Map

```bash
python map_builder.py config_example_1.json
```

### 3. View Results

The generated `.mbtiles` file can be opened in:
- **QGIS** (free, cross-platform GIS software)
- **TileServer GL** (web-based tile server)
- **Mobile apps** supporting MBTiles format
- **Custom applications** using MBTiles libraries

## ⚙️ Configuration

### JSON Configuration Format

```json
{
    "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer",
    "name": "My Region",
    "lat_min": 34.8,
    "long_min": 19.3,
    "lat_max": 41.7,
    "long_max": 29.6,
    "zoom_min": 7,
    "zoom_max": 13,
    "output_file": "my_region_mgrs.mbtiles"
}
```

### Configuration Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `MAP_URL` | string | ArcGIS REST service URL | `"https://server.com/arcgis/rest/services/Map/MapServer"` |
| `name` | string | Descriptive name for the region | `"Operations Area Alpha"` |
| `lat_min` | number | Southern boundary (latitude) | `34.8` |
| `long_min` | number | Western boundary (longitude) | `19.3` |
| `lat_max` | number | Northern boundary (latitude) | `41.7` |
| `long_max` | number | Eastern boundary (longitude) | `29.6` |
| `zoom_min` | integer | Minimum zoom level (0-22) | `7` |
| `zoom_max` | integer | Maximum zoom level (0-22) | `13` |
| `output_file` | string | Output MBTiles filename | `"region.mbtiles"` |

### Popular ArcGIS Services

```json
// Satellite Imagery
"MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer"

// Topographic Map
"MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Topo_Map/MapServer"

// Street Map
"MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Street_Map/MapServer"

// Terrain
"MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Terrain_Base/MapServer"
```

## 📖 Usage Examples

### Single Region Processing

```bash
python map_builder.py my_config.json
```

### Multiple Regions

```bash
python map_builder.py config1.json config2.json config3.json
```

### Batch Processing with Wildcards

```bash
# Windows
python map_builder.py configs\*.json

# Linux/macOS
python map_builder.py configs/*.json
```

### Performance Tuning

```bash
# Increase worker threads for faster processing
python map_builder.py --max-workers 8 config.json

# Reduce workers for slower internet/server
python map_builder.py --max-workers 2 config.json
```

### Real-World Configuration Examples

#### Military Operations Area
```json
{
    "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer",
    "name": "Operations_Area_Bravo",
    "lat_min": 35.1,
    "long_min": 25.8,
    "lat_max": 36.4,
    "long_max": 27.2,
    "zoom_min": 10,
    "zoom_max": 16,
    "output_file": "ops_bravo_mgrs.mbtiles"
}
```

#### Training Range
```json
{
    "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Topo_Map/MapServer",
    "name": "Training_Range_Charlie",
    "lat_min": 38.5,
    "long_min": 22.1,
    "lat_max": 39.2,
    "long_max": 23.3,
    "zoom_min": 8,
    "zoom_max": 14,
    "output_file": "training_charlie_mgrs.mbtiles"
}
```

#### Emergency Response Zone
```json
{
    "MAP_URL": "https://services.arcgisonline.com/arcgis/rest/services/World_Street_Map/MapServer",
    "name": "Emergency_Response_Delta",
    "lat_min": 37.9,
    "long_min": 23.7,
    "lat_max": 38.1,
    "long_max": 24.0,
    "zoom_min": 12,
    "zoom_max": 18,
    "output_file": "emergency_delta_mgrs.mbtiles"
}
```

## 🎯 MGRS Grid System

### What is MGRS?

The Military Grid Reference System (MGRS) is a geocoordinate standard used by NATO militaries for locating points on Earth. It divides the world into a series of 6° longitude zones and 8° latitude bands.

### Grid Precision by Zoom Level

| Zoom Level | Grid Precision | Grid Size | Use Case |
|------------|----------------|-----------|----------|
| 0-6 | 100km squares | 100,000m | Strategic overview |
| 7-10 | 10km squares | 10,000m | Operational planning |
| 11-13 | 1km squares | 1,000m | Tactical operations |
| 14-16 | 100m squares | 100m | Detailed navigation |
| 17-22 | 10m squares | 10m | Precision targeting |

### MGRS Zone Labels

The tool displays the first 5 characters of MGRS coordinates:
- **Positions 1-2**: UTM Zone Number (01-60)
- **Position 3**: Latitude Band Letter (C-X, excluding I and O)
- **Positions 4-5**: 100km Square Identifier (AA-ZZ)

Example: `34SGG` = Zone 34, Band S, Square GG

### Grid Display Logic

- **Single Zone Tiles**: Label placed in center
- **Multi-Zone Tiles**: Labels at zone boundaries
- **Grid Lines**: Red lines showing grid structure
- **Label Background**: White background with red border for readability

## 🖥️ Command Line Reference

```
python map_builder.py [OPTIONS] [CONFIG_FILES...]

Arguments:
  CONFIG_FILES              JSON configuration files to process

Options:
  --create-examples         Create example configuration files and exit
  --max-workers INTEGER     Maximum number of worker threads (default: 4)
  --help                    Show help message and exit

Examples:
  python map_builder.py config1.json
  python map_builder.py config1.json config2.json config3.json
  python map_builder.py --create-examples
  python map_builder.py configs/*.json
  python map_builder.py --max-workers 8 config.json
```

## 🔧 Advanced Usage

### Custom Map Sources

You can use any ArcGIS REST service that supports the standard tile format:

```json
{
    "MAP_URL": "https://your-server.com/arcgis/rest/services/CustomMap/MapServer",
    "name": "Custom_Map_Data",
    // ... other parameters
}
```

### Coordinate System Considerations

- **Input coordinates**: Always use WGS84 (EPSG:4326) decimal degrees
- **Internal processing**: Automatic conversion to Web Mercator (EPSG:3857)
- **MGRS calculation**: Uses appropriate UTM zones automatically
- **Output format**: Standard MBTiles with XYZ tile scheme

### File Size Estimation

Approximate file sizes for different zoom ranges:

| Zoom Range | Area Coverage | Approx. Tiles | File Size |
|------------|---------------|---------------|-----------|
| 0-6 | World | 1,365 | 50-200 MB |
| 7-13 | Country | 50,000-500,000 | 1-10 GB |
| 14-18 | City/Region | 1M-50M | 10-100 GB |

### Directory Structure

```
project/
├── map_builder.py
├── requirements.txt
├── README.md
├── configs/
│   ├── region1.json
│   ├── region2.json
│   └── region3.json
├── output/
│   ├── region1_mgrs.mbtiles
│   ├── region2_mgrs.mbtiles
│   └── region3_mgrs.mbtiles
└── logs/
    └── processing.log
```

## 🐛 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Error: No module named 'mgrs'
pip install mgrs

# Error: No module named 'packaging'
pip install packaging

# Error: pyproj installation failed
pip install --upgrade pyproj
# or
conda install pyproj
```

#### Network Issues
```bash
# Error: Failed to download tile
# Check internet connection and MAP_URL accessibility
curl "https://your-map-url/tile/0/0/0"
```

#### Invalid Configuration
```bash
# Error: Invalid JSON
# Validate JSON syntax at jsonlint.com

# Error: Invalid coordinates
# Ensure lat_min < lat_max and long_min < long_max
```

#### Memory Issues
```bash
# Reduce worker threads
python map_builder.py --max-workers 2 config.json

# Process smaller areas or lower zoom ranges
```

### Platform-Specific Issues

#### Windows
- **pyproj installation**: Use conda or pre-compiled wheels
- **Font loading**: Windows fonts automatically detected
- **Path separators**: Use forward slashes in JSON files

#### Linux
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3-dev libgdal-dev proj-bin libproj-dev

# Alternative for CentOS/RHEL
sudo yum install python3-devel gdal-devel proj-devel
```

#### macOS
```bash
# Install with Homebrew
brew install proj gdal

# For M1/M2 Macs
conda install pyproj  # Recommended over pip
```

### Debugging

Enable detailed logging:
```python
# Add to script beginning
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check tile availability:
```bash
# Test single tile download
curl "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/5/10/12"
```

## ⚡ Performance Optimization

### Hardware Recommendations

- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 8GB+ for large areas, 4GB for small regions
- **Storage**: SSD recommended for faster I/O
- **Network**: Stable broadband connection

### Optimization Strategies

#### Worker Thread Tuning
```bash
# Conservative (slow internet/server)
--max-workers 2

# Balanced (most cases)
--max-workers 4

# Aggressive (fast internet/powerful machine)
--max-workers 8
```

#### Memory Management
- Process smaller zoom ranges separately
- Use lower precision for overview maps
- Monitor system resources during processing

#### Network Optimization
- Use wired connection instead of WiFi
- Avoid peak hours for better server response
- Consider geographic proximity to tile servers

### Batch Processing Tips

1. **Group by zoom level**: Similar zoom ranges process more efficiently
2. **Sort by area size**: Process smaller areas first
3. **Monitor progress**: Use logs to track performance
4. **Parallel processing**: Run multiple instances for different regions

```bash
# Example: Process multiple regions in parallel
python map_builder.py region1.json &
python map_builder.py region2.json &
python map_builder.py region3.json &
wait
```

## 🔄 Integration

### QGIS Integration

1. **Install QGIS**: Download from [qgis.org](https://qgis.org)
2. **Add MBTiles**: Layer → Add Layer → Add Vector Tile Layer
3. **Select file**: Browse to your `.mbtiles` file
4. **Style**: Customize appearance as needed

### Web Integration

```javascript
// Using Leaflet with MBTiles
var map = L.map('map').setView([38.0, 23.7], 10);

// Load MBTiles layer (requires additional plugins)
L.tileLayer.mbTiles('path/to/your/tiles.mbtiles', {
    attribution: 'Map data © Your Organization'
}).addTo(map);
```

### Mobile Applications

Popular apps supporting MBTiles:
- **OruxMaps** (Android)
- **Guru Maps** (iOS/Android)
- **Avenza Maps** (iOS/Android)
- **MapBox SDK** (custom development)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/polmt/mapBuilder.git
cd mapBuilder
python -m venv dev-env
source dev-env/bin/activate  # Linux/macOS
# or
dev-env\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Running Tests

```bash
pytest tests/
```

### Code Style

We use Black for code formatting:
```bash
black map_builder.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **MGRS Library**: Python MGRS implementation
- **Mercantile**: Spherical mercator tile utilities
- **Pillow**: Python Imaging Library
- **PyProj**: Cartographic projections and coordinate transformations
- **ArcGIS**: ESRI's mapping and analytics platform

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/polmt/mapBuilder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/polmt/mapBuilder/discussions)
- **Documentation**: [Wiki](https://github.com/polmt/mapBuilder/wiki)

## 🔮 Roadmap

- [ ] GUI interface for configuration management
- [ ] Support for WMS/WMTS services
- [ ] Custom grid systems (UTM, USNG)
- [ ] Tile optimization and compression
- [ ] Progress bars and better status reporting
- [ ] Docker containerization
- [ ] Cloud deployment scripts
- [ ] Mobile app for field validation

---

**Made with ❤️ for the geospatial community**

*Star ⭐ this repository if you find it useful!*