# FAT Recovery Tool - Modular Version

Công cụ phân tích và khôi phục boot sector cho FAT16/FAT32 được tách thành các module.

## Cấu trúc Module

### 1. `constants.py`
- Chứa tất cả các hằng số và cấu hình
- Các giá trị hợp lệ cho boot sector
- Mã IOCTL và các thiết lập mặc định

### 2. `disk_utils.py`
- `DiskReader`: Lớp xử lý đọc/ghi đĩa
  - `read_sector()`: Đọc sector từ đĩa
  - `write_sector()`: Ghi sector vào đĩa
  - `get_disk_size()`: Lấy kích thước đĩa với nhiều phương pháp fallback
- `create_backup()`: Tạo file backup
- `hex_dump()`: Hiển thị hex dump

### 3. `boot_sector.py`
- `BootSectorParser`: Phân tích boot sector
  - `parse_boot_sector()`: Trích xuất thông tin từ boot sector
  - `_determine_fat_type()`: Xác định loại FAT
- `BootSectorValidator`: Kiểm tra tính hợp lệ
  - `validate_boot_sector()`: Kiểm tra các trường boot sector
- `BootSectorGenerator`: Tạo boot sector tối ưu
  - `generate_optimal_boot_sector()`: Tạo boot sector mới

### 4. `fat_analyzer.py`
- `FATAnalyzer`: Lớp phân tích chính
  - `run_analysis()`: Chạy phân tích toàn diện
  - `repair_boot_sector()`: Sửa chữa boot sector
  - `_write_boot_sector()`: Ghi boot sector mới
  - `_display_boot_sector_info()`: Hiển thị thông tin

### 5. `cli.py`
- `FATRecoveryCLI`: Giao diện dòng lệnh
  - `run()`: Chạy CLI
  - `_execute()`: Thực thi lệnh
  - `_handle_analysis_result()`: Xử lý kết quả
  - `_handle_recovery()`: Xử lý khôi phục

### 6. `main.py` / `fat_recovery_modular.py`
- Entry point chính của chương trình

## Sử dụng

### Chạy từ file modular:
```bash
python fat_recovery_modular.py E              # Phân tích ổ đĩa E:
python fat_recovery_modular.py D --recovery   # Phân tích và khôi phục ổ đĩa D:
python fat_recovery_modular.py F --info-only  # Chỉ hiển thị thông tin
```

### Sử dụng như module:
```python
from fat_analyzer import FATAnalyzer

# Tạo analyzer
analyzer = FATAnalyzer('E')

# Chạy phân tích
result = analyzer.run_analysis()

# Khôi phục nếu cần
if result['recovery_needed']:
    analyzer.repair_boot_sector()
```

## Ưu điểm của cấu trúc modular

1. **Separation of Concerns**: Mỗi module có một chức năng rõ ràng
2. **Reusability**: Có thể tái sử dụng các component riêng lẻ
3. **Testability**: Dễ dàng test từng module độc lập
4. **Maintainability**: Dễ bảo trì và mở rộng
5. **Readability**: Code dễ đọc và hiểu hơn

## So sánh với file gốc

| Khía cạnh | File gốc | Version modular |
|-----------|----------|-----------------|
| Dòng code | 607 dòng | ~600 dòng (phân tán) |
| File | 1 file | 7 files |
| Tính module | Thấp | Cao |
| Khả năng test | Khó | Dễ |
| Bảo trì | Khó | Dễ |

## Dependencies

- Python 3.6+
- pywin32 (tùy chọn, cho Windows disk access)
- Standard library: struct, os, sys, argparse, typing
