# FAT Recovery Tool

A comprehensive tool for analyzing and recovering FAT16/FAT32 boot sectors, available in both monolithic and modular versions.

## 🚀 Quick Start

### Basic Usage
```bash
# Using original monolithic version
python fat_recovery.py E --recovery

# Using modular version  
python fat_recovery_modular.py E --recovery

# Info only mode
python fat_recovery_modular.py F --info-only
```

### Demo & Testing
```bash
python demo_modular.py    # Run demo
python test_modules.py    # Run unit tests
make demo                 # Using Makefile
make test                 # Run tests via Makefile
```

## 📁 Project Structure

```
FAT-Recovery-Tool/
├── 📄 Core Files
│   ├── fat_recovery.py              # Original monolithic version (607 lines)
│   └── fat_recovery_modular.py      # Modular entry point
├── 🧩 Modular Components  
│   ├── constants.py                 # System constants & configuration
│   ├── disk_utils.py               # Disk read/write utilities
│   ├── boot_sector.py              # Boot sector processing
│   ├── fat_analyzer.py             # Core analysis & recovery logic
│   ├── cli.py                      # Command line interface
│   ├── main.py                     # Alternative entry point
│   └── __init__.py                 # Package initialization
├── 🧪 Testing & Demo
│   ├── test_modules.py             # Unit tests
│   └── demo_modular.py             # Feature demonstration
├── 📚 Documentation
│   ├── README_modular.md           # Modular version guide
│   ├── ANALYSIS_SUMMARY.md         # Modularization analysis
│   ├── PROJECT_INDEX.md            # Project index
│   └── requirements.txt            # Dependencies
├── 🛠️ Build & Data
│   ├── Makefile                    # Build automation
│   └── Bonus_Lab.vhd              # Test virtual disk
```

## 🏗️ Architecture Overview

### Module Dependencies
```
fat_recovery_modular.py
└── cli.py
    └── fat_analyzer.py
        ├── boot_sector.py
        │   ├── constants.py
        │   └── disk_utils.py
        └── disk_utils.py
            └── constants.py
```

### Key Components

#### 1. **Constants Module** (`constants.py`)
- Boot signature definitions
- Valid sector sizes and cluster counts
- IOCTL codes and system configurations

#### 2. **Disk Utilities** (`disk_utils.py`)
```python
class DiskReader:
    def read_sector(sector_num, num_sectors=1)    # Read disk sectors
    def write_sector(sector_num, data)            # Write to disk
    def get_disk_size()                           # Multi-method size detection
```

#### 3. **Boot Sector Processing** (`boot_sector.py`)
```python
class BootSectorParser:
    def parse_boot_sector(data)                   # Extract boot sector info
    
class BootSectorValidator:
    def validate_boot_sector(info, disk_size=0)   # Validate boot sector
    
class BootSectorGenerator:
    def generate_optimal_boot_sector(damaged, disk_size=0)  # Generate new boot sector
```

#### 4. **FAT Analyzer** (`fat_analyzer.py`)
```python
class FATAnalyzer:
    def run_analysis()                           # Comprehensive analysis
    def repair_boot_sector()                     # Repair damaged boot sector
    def _display_boot_sector_info()              # Display detailed info
```

#### 5. **CLI Interface** (`cli.py`)
```python
class FATRecoveryCLI:
    def run(args=None)                           # Main CLI entry point
    def _handle_recovery()                       # Handle recovery operations
```

## 💻 Usage Examples

### Command Line Interface
```bash
# Analyze drive E:
python fat_recovery_modular.py E

# Analyze and recover drive D:
python fat_recovery_modular.py D --recovery

# Information only mode
python fat_recovery_modular.py F --info-only
```

### Programmatic API

#### High-level API
```python
from fat_analyzer import FATAnalyzer

# Create analyzer instance
analyzer = FATAnalyzer('E')

# Run comprehensive analysis
result = analyzer.run_analysis()

# Repair if needed
if result['recovery_needed']:
    success = analyzer.repair_boot_sector()
```

#### Mid-level API
```python
from boot_sector import BootSectorParser, BootSectorValidator
from disk_utils import DiskReader

# Read and parse boot sector
reader = DiskReader('E')
data = reader.read_sector(0)
info = BootSectorParser.parse_boot_sector(data)

# Validate boot sector
errors = BootSectorValidator.validate_boot_sector(info)
```

#### Low-level API
```python
from disk_utils import DiskReader

reader = DiskReader('E')
data = reader.read_sector(0)           # Read boot sector
size = reader.get_disk_size()          # Get disk size
reader.write_sector(0, new_data)       # Write new boot sector
```

## 🔍 Key Features

- ✅ **Multi-FAT Support**: FAT12/16/32 compatibility
- ✅ **Smart Detection**: Multi-method disk size detection
- ✅ **Interactive Recovery**: User-guided repair process
- ✅ **Automatic Backup**: Safe recovery with backups
- ✅ **Comprehensive Validation**: Thorough boot sector checking
- ✅ **Cross-platform**: Windows/Linux compatible
- ✅ **Well-documented**: Complete API documentation
- ✅ **Modular Design**: Reusable components

## 📊 Comparison: Monolithic vs Modular

| Aspect | Original File | Modular Version |
|--------|---------------|-----------------|
| **Structure** | 1 file, 607 lines | 7 files, ~540 lines |
| **Maintainability** | ⚠️ Difficult | ✅ Easy |
| **Testability** | ❌ Hard to test individually | ✅ Easy unit testing |
| **Reusability** | ❌ Must copy entire file | ✅ Import specific components |
| **Readability** | ⚠️ Good | ✅ Excellent |
| **Extensibility** | ❌ Hard to extend | ✅ Easy to extend |
| **Documentation** | ⚠️ Basic | ✅ Comprehensive |
| **Type Hints** | ⚠️ Partial | ✅ Complete |

## 🎯 Use Cases

1. **System Administrators**: Recover corrupted FAT boot sectors
2. **Forensics Experts**: Analyze FAT file system structure
3. **Developers**: Use components in other projects
4. **Students**: Learn about FAT file system internals
5. **Data Recovery**: Professional data recovery operations

## 🧪 Testing

### Run Tests
```bash
python test_modules.py    # Run all unit tests
make test                 # Using Makefile
```

### Run Demo
```bash
python demo_modular.py    # Interactive demonstration
make demo                 # Using Makefile
```

## 📦 Installation & Requirements

### Dependencies
```bash
pip install -r requirements.txt
```

### System Requirements
- Python 3.6+
- pywin32 (optional, for Windows disk access)
- Standard library: struct, os, sys, argparse, typing

### Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## 🔧 Development

### Build Commands
```bash
make demo     # Run demonstration
make test     # Run unit tests
make clean    # Clean up temporary files
```

### Adding New Features
1. Create new module in appropriate category
2. Add tests in `test_modules.py`
3. Update documentation
4. Test with `demo_modular.py`

## 🎉 Benefits of Modularization

1. **Separation of Concerns**: Each module has a clear responsibility
2. **High Cohesion, Low Coupling**: Well-structured dependencies
3. **Enhanced Testability**: Individual component testing
4. **Improved Maintainability**: Easier bug fixes and updates
5. **Code Reusability**: Components can be used in other projects
6. **Better Documentation**: Clear API for each module
7. **Extensibility**: Easy to add new file system support

## 🔮 Future Enhancements

- [ ] **Logging Module**: Comprehensive logging system
- [ ] **Configuration Files**: External configuration support
- [ ] **Plugin Architecture**: Extensible plugin system
- [ ] **GUI Interface**: Graphical user interface
- [ ] **Extended Support**: exFAT, NTFS support
- [ ] **Parallel Processing**: Multi-threaded operations
- [ ] **Network Drives**: Remote disk support
- [ ] **Recovery Wizard**: Step-by-step recovery guide

## 🚨 Important Notes

- **Administrator Rights**: Required for direct disk access
- **Backup First**: Always backup before recovery operations
- **Test Environment**: Use test VHD files for experimentation
- **Data Safety**: Tool creates automatic backups during recovery

## 📄 License & Support

**Version**: 1.0.0  
**Date**: June 2025  
**Authors**: FAT Recovery Tool Team

For issues, suggestions, or contributions, please refer to the project documentation or contact the development team.

---
*This tool is designed for educational and professional data recovery purposes. Always ensure proper backups before performing recovery operations on critical data.*
