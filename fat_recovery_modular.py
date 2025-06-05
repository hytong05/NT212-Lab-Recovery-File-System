#!/usr/bin/env python3
"""
FAT Data Recovery Tool - Modular Version
Công cụ phân tích và khôi phục boot sector cho FAT16/FAT32 - Phiên bản module hóa

Sử dụng:
  python fat_recovery_modular.py E              # Phân tích ổ đĩa E:
  python fat_recovery_modular.py D --recovery   # Phân tích và khôi phục ổ đĩa D:
  python fat_recovery_modular.py F --info-only  # Chỉ hiển thị thông tin, không khôi phục
"""

import sys
from cli import FATRecoveryCLI


def main():
    """Hàm main để chạy công cụ phân tích FAT"""
    cli = FATRecoveryCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
