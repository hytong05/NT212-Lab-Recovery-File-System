#!/usr/bin/env python3
"""
Command Line Interface for FAT Recovery Tool
Giao diện dòng lệnh cho công cụ khôi phục FAT
"""

import argparse
import sys
from fat_analyzer import FATAnalyzer


class FATRecoveryCLI:
    """Lớp xử lý giao diện dòng lệnh"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Tạo argument parser"""
        parser = argparse.ArgumentParser(
            description="FAT Data Recovery Tool - Công cụ phân tích và khôi phục boot sector",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Ví dụ sử dụng:
  python fat_recovery.py E              # Phân tích ổ đĩa E:
  python fat_recovery.py D --recovery   # Phân tích và khôi phục ổ đĩa D:
  python fat_recovery.py F --info-only  # Chỉ hiển thị thông tin, không khôi phục
            """
        )
        
        parser.add_argument('drive', help='Chữ cái ổ đĩa (ví dụ: E, D)')
        parser.add_argument('--recovery', action='store_true', 
                           help='Thực hiện khôi phục tương tác nếu phát hiện lỗi')
        parser.add_argument('--info-only', action='store_true',
                           help='Chỉ hiển thị thông tin phân tích, không khôi phục')
        
        return parser
    
    def run(self, args=None) -> int:
        """Chạy CLI với các tham số"""
        try:
            parsed_args = self.parser.parse_args(args)
            return self._execute(parsed_args)
        except KeyboardInterrupt:
            print("\nĐã hủy thao tác.")
            return 1
        except Exception as e:
            print(f"\nLỗi: {str(e)}")
            return 1
    
    def _execute(self, args) -> int:
        """Thực thi lệnh"""
        # Normalize drive letter - remove : if present
        drive_letter = args.drive.upper().rstrip(':')
        
        if len(drive_letter) != 1 or not drive_letter.isalpha():
            print("Lỗi: Vui lòng nhập một chữ cái ổ đĩa hợp lệ (ví dụ: E)")
            return 1
        
        analyzer = FATAnalyzer(drive_letter)
        result = analyzer.run_analysis()
        
        return self._handle_analysis_result(result, args, analyzer)
    
    def _handle_analysis_result(self, result: dict, args, analyzer: FATAnalyzer) -> int:
        """Xử lý kết quả phân tích"""
        print(f"\n=== KẾT QUẢ PHÂN TÍCH ===")
        
        if not result['disk_accessible']:
            print("✗ Không thể truy cập ổ đĩa")
            return 1
        
        if result['boot_sector_valid']:
            if result['recovery_needed']:
                print("⚠ Phát hiện vấn đề với boot sector")
                return self._handle_recovery(args, analyzer, "vấn đề")
            else:
                print("✓ Boot sector hoạt động bình thường")
                return 0
        else:
            print("✗ Boot sector bị hỏng nghiêm trọng")
            return self._handle_recovery(args, analyzer, "hỏng")
    
    def _handle_recovery(self, args, analyzer: FATAnalyzer, issue_type: str) -> int:
        """Xử lý khôi phục"""
        if args.recovery and not args.info_only:
            print(f"\nThực hiện khôi phục boot sector {issue_type}...")
            if analyzer.repair_boot_sector():
                print("✓ Khôi phục thành công!")
                return 0
            else:
                print("✗ Khôi phục thất bại")
                return 1
        elif not args.info_only:
            print("Sử dụng --recovery để thực hiện khôi phục tương tác")
            return 1
        
        return 0
