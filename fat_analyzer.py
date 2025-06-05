#!/usr/bin/env python3
"""
FAT Analysis and Recovery Module
Module phân tích và khôi phục FAT
"""

from typing import Dict, Optional
from disk_utils import DiskReader, create_backup
from boot_sector import BootSectorParser, BootSectorValidator, BootSectorGenerator


class FATAnalyzer:
    """Lớp phân tích và khôi phục boot sector FAT"""
    
    def __init__(self, drive_letter: str):
        self.drive_letter = drive_letter.upper()
        self.disk_reader = DiskReader(drive_letter)
        self.current_boot_sector = None
        self.disk_size = 0
        
    def run_analysis(self) -> Dict:
        """Chạy phân tích toàn diện ổ đĩa"""
        print(f"=== PHÂN TÍCH Ổ ĐĨA {self.drive_letter}: ===\n")
        
        result = {
            'drive_letter': self.drive_letter,
            'disk_accessible': False,
            'boot_sector_valid': False,
            'current_info': {},
            'validation_errors': [],
            'recovery_needed': False
        }
        
        try:
            # Lấy kích thước ổ đĩa
            self.disk_size = self.disk_reader.get_disk_size()
            print(f"Kích thước ổ đĩa: {self.disk_size:,} bytes ({self.disk_size / (1024*1024):.1f} MB)")
            result['disk_accessible'] = True
            
            # Đọc boot sector
            print("\nĐọc boot sector...")
            self.current_boot_sector = self.disk_reader.read_sector(0)
            
            # Phân tích boot sector hiện tại
            try:
                result['current_info'] = BootSectorParser.parse_boot_sector(self.current_boot_sector)
                result['boot_sector_valid'] = True
                print("✓ Boot sector có thể đọc được")
                
                # Hiển thị thông tin hiện tại
                self._display_boot_sector_info(result['current_info'], "THÔNG TIN BOOT SECTOR HIỆN TẠI")
                
            except Exception as e:
                print(f"✗ Không thể phân tích boot sector: {str(e)}")
                result['boot_sector_valid'] = False
                result['recovery_needed'] = True
            
            # Kiểm tra tính hợp lệ
            if result['boot_sector_valid']:
                print(f"\n=== KIỂM TRA TÍNH HỢP LỆ ===")
                result['validation_errors'] = BootSectorValidator.validate_boot_sector(
                    result['current_info'], self.disk_size
                )
                
                if not result['validation_errors']:
                    print("✓ Boot sector hợp lệ")
                else:
                    print(f"✗ Phát hiện {len(result['validation_errors'])} lỗi:")
                    for i, error in enumerate(result['validation_errors'], 1):
                        print(f"  {i}. {error}")
                    result['recovery_needed'] = True
            else:
                # Boot sector bị hỏng nghiêm trọng, cần khôi phục
                result['recovery_needed'] = True
            
        except Exception as e:
            print(f"✗ Lỗi khi phân tích ổ đĩa: {str(e)}")
            result['disk_accessible'] = False
        
        return result
    
    def repair_boot_sector(self) -> bool:
        """Sửa chữa boot sector bị hỏng"""
        if self.current_boot_sector is None:
            print("Không có boot sector để sửa chữa")
            return False
        
        print(f"\n=== SỬA CHỮA BOOT SECTOR ===")
        
        try:
            # Tạo boot sector tối ưu
            repaired_boot = BootSectorGenerator.generate_optimal_boot_sector(
                self.current_boot_sector, self.disk_size
            )
            
            # Kiểm tra boot sector mới
            print("\nKiểm tra boot sector đã sửa chữa...")
            repaired_info = BootSectorParser.parse_boot_sector(repaired_boot)
            errors = BootSectorValidator.validate_boot_sector(repaired_info, self.disk_size)
            
            if errors:
                print(f"Boot sector sửa chữa vẫn có lỗi:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print("✓ Boot sector sửa chữa hợp lệ!")
                
                # Hiển thị thông tin boot sector mới
                self._display_boot_sector_info(repaired_info, "THÔNG TIN BOOT SECTOR ĐÃ SỬA CHỮA")
                
                # Lưu backup và ghi boot sector mới
                return self._write_boot_sector(repaired_boot)
                
        except Exception as e:
            print(f"Lỗi khi sửa chữa boot sector: {str(e)}")
            return False
    
    def _write_boot_sector(self, new_boot_sector: bytes) -> bool:
        """Ghi boot sector mới vào đĩa"""
        print(f"\n=== GHI BOOT SECTOR MỚI ===")
        
        # Tạo backup trước
        backup_path = f"{self.drive_letter}_boot_backup.bin"
        if not create_backup(backup_path, self.current_boot_sector):
            return False
        
        print(f"✓ Đã tạo backup tại: {backup_path}")
        
        # Xác nhận từ người dùng
        print(f"\n⚠ CẢNH BÁO: Bạn sắp ghi đè boot sector của ổ đĩa {self.drive_letter}:")
        print("Thao tác này có thể làm hỏng dữ liệu nếu không thực hiện đúng!")
        confirm = input("Bạn có chắc chắn muốn tiếp tục? (yes/no): ").lower().strip()
        
        if confirm not in ['yes', 'y']:
            print("Đã hủy thao tác ghi boot sector")
            return False
        
        try:
            # Ghi boot sector mới
            success = self.disk_reader.write_sector(0, new_boot_sector)
            if success:
                print("✓ Đã ghi boot sector mới thành công!")
                print(f"Backup cũ được lưu tại: {backup_path}")
                return True
            
        except Exception as e:
            print(f"✗ Lỗi khi ghi boot sector: {str(e)}")
            print("Có thể do quyền truy cập hoặc ổ đĩa được bảo vệ")
            return False
    
    def _display_boot_sector_info(self, info: Dict, title: str) -> None:
        """Hiển thị thông tin boot sector"""
        print(f"\n=== {title} ===")
        print(f"OEM Name: {info['oem_name']}")
        print(f"Bytes per sector: {info['bytes_per_sector']}")
        print(f"Sectors per cluster: {info['sectors_per_cluster']}")
        print(f"Reserved sectors: {info['reserved_sectors']}")
        print(f"Số bảng FAT: {info['num_fats']}")
        print(f"Root entries: {info['root_entries']}")
        print(f"Tổng sectors: {info['total_sectors']}")
        print(f"Sectors per FAT: {info['sectors_per_fat']}")
        print(f"Loại FAT: FAT{info['fat_type']}")
        print(f"Kích thước volume: {info['volume_size']:,} bytes")
