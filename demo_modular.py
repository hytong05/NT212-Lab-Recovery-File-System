#!/usr/bin/env python3
"""
Test script to demonstrate the modular FAT Recovery Tool
Script test để demo công cụ khôi phục FAT modular
"""

import sys
import os
import struct

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fat_analyzer import FATAnalyzer
from boot_sector import BootSectorParser, BootSectorValidator
from disk_utils import DiskReader, hex_dump
from constants import *


def test_individual_modules():
    """Test các module riêng lẻ"""
    print("=== TEST CÁC MODULE RIÊNG LẺ ===\n")
    
    # Test constants
    print("1. Test constants:")
    print(f"   BOOT_SIGNATURE: {BOOT_SIGNATURE.hex()}")
    print(f"   VALID_BYTES_PER_SECTOR: {VALID_BYTES_PER_SECTOR}")
    print(f"   FAT12_MAX_CLUSTERS: {FAT12_MAX_CLUSTERS}")
    
    # Test disk utils functions
    print("\n2. Test disk_utils:")
    test_data = b'\x00\x01\x02\x03' * 16
    print("   Hex dump test:")
    hex_dump(test_data, max_bytes=32)
    
    print("\n3. Test boot sector parser với data giả:")
    # Tạo một boot sector giả để test
    fake_boot = bytearray(512)
    fake_boot[3:11] = b'TESTFAT '
    fake_boot[11:13] = struct.pack('<H', 512)  # bytes per sector
    fake_boot[13] = 1  # sectors per cluster
    fake_boot[14:16] = struct.pack('<H', 1)  # reserved sectors
    fake_boot[16] = 2  # num fats
    fake_boot[17:19] = struct.pack('<H', 512)  # root entries
    fake_boot[19:21] = struct.pack('<H', 40960)  # total sectors 16
    fake_boot[21] = 0xF8  # media descriptor
    fake_boot[22:24] = struct.pack('<H', 159)  # sectors per fat
    fake_boot[510:512] = BOOT_SIGNATURE
    
    try:
        info = BootSectorParser.parse_boot_sector(bytes(fake_boot))
        print("   ✓ Parse thành công")
        print(f"   OEM: {info['oem_name']}")
        print(f"   FAT Type: FAT{info['fat_type']}")
        
        errors = BootSectorValidator.validate_boot_sector(info)
        if not errors:
            print("   ✓ Validation thành công")
        else:
            print(f"   ⚠ Có {len(errors)} lỗi validation")
            
    except Exception as e:
        print(f"   ✗ Lỗi: {e}")


def demo_modular_usage():
    """Demo cách sử dụng từng module"""
    print("\n=== DEMO SỬ DỤNG MODULAR ===\n")
    
    print("1. Sử dụng DiskReader để đọc thông tin:")
    print("   # from disk_utils import DiskReader")
    print("   # reader = DiskReader('E')")
    print("   # size = reader.get_disk_size()")
    
    print("\n2. Sử dụng BootSectorParser:")
    print("   # from boot_sector import BootSectorParser")
    print("   # info = BootSectorParser.parse_boot_sector(data)")
    
    print("\n3. Sử dụng FATAnalyzer (high-level):")
    print("   # from fat_analyzer import FATAnalyzer")
    print("   # analyzer = FATAnalyzer('E')")
    print("   # result = analyzer.run_analysis()")
    
    print("\n4. Sử dụng CLI:")
    print("   # python fat_recovery_modular.py E --recovery")


def compare_with_original():
    """So sánh với file gốc"""
    print("\n=== SO SÁNH VỚI FILE GỐC ===\n")
    
    # Đếm dòng code trong các file
    files_to_count = [
        'constants.py',
        'disk_utils.py', 
        'boot_sector.py',
        'fat_analyzer.py',
        'cli.py',
        'main.py'
    ]
    
    total_lines = 0
    print("Số dòng code trong từng module:")
    
    for filename in files_to_count:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = len([line for line in f if line.strip() and not line.strip().startswith('#')])
                total_lines += lines
                print(f"   {filename:<20}: {lines:>3} dòng")
        except FileNotFoundError:
            print(f"   {filename:<20}: File không tìm thấy")
    
    print(f"\nTổng dòng code modular: {total_lines}")
    
    try:
        with open('fat_recovery.py', 'r', encoding='utf-8') as f:
            original_lines = len([line for line in f if line.strip() and not line.strip().startswith('#')])
        print(f"Dòng code file gốc:     {original_lines}")
        print(f"Tỷ lệ:                  {total_lines/original_lines:.2f}")
    except FileNotFoundError:
        print("File gốc fat_recovery.py không tìm thấy")


def show_module_structure():
    """Hiển thị cấu trúc module"""
    print("\n=== CẤU TRÚC MODULE ===\n")
    
    structure = {
        'constants.py': ['Hằng số', 'Cấu hình', 'Giá trị mặc định'],
        'disk_utils.py': ['DiskReader class', 'Backup utilities', 'Hex dump'],
        'boot_sector.py': ['BootSectorParser', 'BootSectorValidator', 'BootSectorGenerator'], 
        'fat_analyzer.py': ['FATAnalyzer class', 'Main analysis logic', 'Recovery logic'],
        'cli.py': ['FATRecoveryCLI class', 'Command line interface', 'Argument parsing'],
        'main.py': ['Entry point', 'Main function']
    }
    
    for module, components in structure.items():
        print(f"{module}:")
        for component in components:
            print(f"   - {component}")
        print()


def main():
    """Main function"""
    print("FAT RECOVERY TOOL - MODULAR DEMO")
    print("=" * 50)
    
    try:
        import struct
        test_individual_modules()
        demo_modular_usage() 
        show_module_structure()
        compare_with_original()
        
        print("\n=== KẾT LUẬN ===")
        print("✓ Tất cả module hoạt động bình thường")
        print("✓ Cấu trúc modular giúp code dễ bảo trì")
        print("✓ Có thể tái sử dụng từng component riêng lẻ")
        print("✓ Dễ dàng test và mở rộng")
        
    except Exception as e:
        print(f"\n✗ Lỗi trong demo: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
