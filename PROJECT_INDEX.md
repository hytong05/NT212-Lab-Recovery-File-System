# FAT Recovery Tool - Project Index
# Chỉ mục dự án công cụ khôi phục FAT

## 📁 Cấu trúc Project

### Core Files (Files chính)
- **`fat_recovery.py`** - File gốc monolithic (607 dòng)
- **`fat_recovery_modular.py`** - Entry point của phiên bản modular

### Modular Components (Các module)
- **`constants.py`** - Hằng số và cấu hình hệ thống
- **`disk_utils.py`** - Utilities cho việc đọc/ghi đĩa
- **`boot_sector.py`** - Xử lý boot sector (parse, validate, generate)  
- **`fat_analyzer.py`** - Logic phân tích và khôi phục chính
- **`cli.py`** - Command line interface
- **`main.py`** - Alternative entry point
- **`__init__.py`** - Package initialization

### Testing & Demo (Test và demo)
- **`test_modules.py`** - Unit tests cho các module
- **`demo_modular.py`** - Demo các chức năng modular

### Documentation (Tài liệu)
- **`README_modular.md`** - Hướng dẫn sử dụng modular
- **`ANALYSIS_SUMMARY.md`** - Tóm tắt phân tích module hóa
- **`requirements.txt`** - Dependencies
- **`Makefile`** - Build automation

### Data Files (Files dữ liệu)
- **`Bonus_Lab.vhd`** - Virtual disk file for testing

## 🚀 Quick Start

### 1. Sử dụng file gốc:
```bash
python fat_recovery.py E --recovery
```

### 2. Sử dụng phiên bản modular:
```bash
python fat_recovery_modular.py E --recovery
```

### 3. Chạy demo:
```bash
python demo_modular.py
```

### 4. Chạy tests:
```bash  
python test_modules.py
```

### 5. Sử dụng Makefile:
```bash
make demo     # Chạy demo
make test     # Chạy tests  
make clean    # Dọn dẹp
```

## 📊 Module Dependencies

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

## 🔧 API Overview

### High-level API (FATAnalyzer)
```python
from fat_analyzer import FATAnalyzer

analyzer = FATAnalyzer('E')
result = analyzer.run_analysis()
success = analyzer.repair_boot_sector()
```

### Mid-level API (Boot Sector)
```python
from boot_sector import BootSectorParser, BootSectorValidator

info = BootSectorParser.parse_boot_sector(data)
errors = BootSectorValidator.validate_boot_sector(info)
```

### Low-level API (Disk Utils)
```python
from disk_utils import DiskReader

reader = DiskReader('E')
data = reader.read_sector(0)
size = reader.get_disk_size()
```

## 📈 Improvements Made

| Feature | Original | Modular |
|---------|----------|---------|
| **Files** | 1 | 7 |
| **Testability** | ❌ | ✅ |
| **Reusability** | ❌ | ✅ |
| **Maintainability** | ⚠️ | ✅ |
| **Documentation** | ⚠️ | ✅ |
| **Type Hints** | ⚠️ | ✅ |

## 🎯 Use Cases

1. **System Administrator**: Khôi phục FAT boot sector bị hỏng
2. **Forensics Expert**: Phân tích cấu trúc FAT file system  
3. **Developer**: Sử dụng components cho project khác
4. **Student**: Học về FAT file system structure

## 🔍 Key Features

- ✅ Support FAT12/16/32
- ✅ Multi-method disk size detection
- ✅ Interactive recovery mode
- ✅ Automatic backup creation
- ✅ Comprehensive validation
- ✅ Cross-platform compatible
- ✅ Well-documented API

---
**Tác giả**: FAT Recovery Tool Team  
**Phiên bản**: 1.0.0  
**Ngày**: June 2025
