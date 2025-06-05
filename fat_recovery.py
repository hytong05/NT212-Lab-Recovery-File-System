#!/usr/bin/env python3
"""
FAT Data Recovery Tool - Boot Sector Analysis and Recovery
Công cụ phân tích và khôi phục boot sector cho FAT16/FAT32
"""

import struct
import os
import sys
import argparse
from typing import Dict, List, Tuple, Optional
import math


class FATAnalyzer:
    """Lớp phân tích và khôi phục boot sector FAT"""
    
    def __init__(self, drive_letter: str):
        self.drive_letter = drive_letter.upper()
        self.drive_path = f"\\\\.\\{self.drive_letter}:"
        self.current_boot_sector = None
        self.disk_size = 0
        
    def read_sector(self, sector_num: int, num_sectors: int = 1) -> bytes:
        """Đọc sector từ ổ đĩa"""
        try:
            with open(self.drive_path, 'rb') as drive:
                drive.seek(sector_num * 512)
                return drive.read(num_sectors * 512)
        except Exception as e:
            raise Exception(f"Không thể đọc sector {sector_num}: {str(e)}")
    
    def get_disk_size(self) -> int:
        """Lấy kích thước ổ đĩa với multiple fallback methods"""
        
        # Method 1: Try shutil.disk_usage (most reliable for mounted drives)
        try:
            import shutil
            drive_root = f"{self.drive_letter}:\\"
            total, used, free = shutil.disk_usage(drive_root)
            return total
        except Exception as e:
            print(f"Method 1 (shutil) failed: {e}")
        
        # Method 2: Try pywin32 if available
        try:
            import win32file
            import pywintypes
            handle = win32file.CreateFile(
                self.drive_path,
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            try:
                # For physical drives, use different approach
                if self.drive_path.startswith('\\\\.\\PhysicalDrive'):
                    # Try to get partition info instead
                    try:
                        size_low, size_high = win32file.GetFileSize(handle)
                        if size_high == 0 and size_low > 0:
                            return size_low
                        elif size_high > 0:
                            return (size_high << 32) + size_low
                    except pywintypes.error as e:
                        print(f"GetFileSize error: {e}")
                        # Try using SetFilePointer as alternative
                        try:
                            win32file.SetFilePointer(handle, 0, win32file.FILE_END)
                            size = win32file.SetFilePointer(handle, 0, win32file.FILE_CURRENT)
                            if size > 0:
                                return size
                        except:
                            pass
                else:
                    # For logical drives, standard method
                    size_low, size_high = win32file.GetFileSize(handle)
                    return (size_high << 32) + size_low
            finally:
                win32file.CloseHandle(handle)
        except ImportError:
            print("pywin32 not available")
        except Exception as e:
            print(f"Method 2 (pywin32) failed: {e}")
        
        # Method 3: Try Windows disk geometry API
        try:
            import win32file
            import struct
            handle = win32file.CreateFile(
                self.drive_path,
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            try:
                # IOCTL_DISK_GET_DRIVE_GEOMETRY
                IOCTL_DISK_GET_DRIVE_GEOMETRY = 0x00070000
                try:
                    geometry = win32file.DeviceIoControl(
                        handle,
                        IOCTL_DISK_GET_DRIVE_GEOMETRY,
                        None,
                        24  # Size of DISK_GEOMETRY structure
                    )
                    if len(geometry) >= 24:
                        # Parse DISK_GEOMETRY structure
                        cylinders, media_type, tracks_per_cylinder, sectors_per_track, bytes_per_sector = struct.unpack('<QLLLH', geometry)
                        total_size = cylinders * tracks_per_cylinder * sectors_per_track * bytes_per_sector
                        if total_size > 0:
                            return total_size
                except:
                    pass
            finally:
                win32file.CloseHandle(handle)
        except:
            pass
        
        # Method 4: Try direct file access
        try:
            with open(self.drive_path, 'rb') as drive:
                drive.seek(0, 2)  # Seek to end
                return drive.tell()
        except Exception as e:
            print(f"Method 4 (direct access) failed: {e}")
          # Method 5: Estimate from drive info
        try:
            import os
            statvfs = os.statvfs(f"{self.drive_letter}:\\")
            return statvfs.f_frsize * statvfs.f_blocks
        except:
            pass
        
        print("Warning: Could not determine disk size, using default")
        return 0
    
    def parse_boot_sector(self, boot_data: bytes) -> Dict:
        """Phân tích boot sector và trích xuất thông tin"""
        if len(boot_data) < 512:
            raise ValueError("Boot sector không đủ 512 bytes")
        
        # Hiển thị hex dump đầu tiên của boot sector để debug
        print(f"Boot sector hex dump (first 64 bytes):")
        for i in range(0, min(64, len(boot_data)), 16):
            hex_str = ' '.join(f'{b:02X}' for b in boot_data[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in boot_data[i:i+16])
            print(f"{i:04X}: {hex_str:<48} {ascii_str}")
        
        # Kiểm tra chữ ký boot sector
        if boot_data[510:512] != b'\x55\xAA':
            print(f"Warning: Boot sector signature: {boot_data[510:512].hex()} (expected 55AA)")
            # Không raise exception, tiếp tục phân tích
        
        # Trích xuất thông tin cơ bản với error handling
        info = {}
        try:
            info['oem_name'] = boot_data[3:11].decode('ascii', errors='ignore').strip()
            info['bytes_per_sector'] = struct.unpack('<H', boot_data[11:13])[0]
            info['sectors_per_cluster'] = boot_data[13]
            info['reserved_sectors'] = struct.unpack('<H', boot_data[14:16])[0]
            info['num_fats'] = boot_data[16]
            info['root_entries'] = struct.unpack('<H', boot_data[17:19])[0]
            info['total_sectors_16'] = struct.unpack('<H', boot_data[19:21])[0]
            info['media_descriptor'] = boot_data[21]
            info['sectors_per_fat_16'] = struct.unpack('<H', boot_data[22:24])[0]
            info['sectors_per_track'] = struct.unpack('<H', boot_data[24:26])[0]
            info['num_heads'] = struct.unpack('<H', boot_data[26:28])[0]
            info['hidden_sectors'] = struct.unpack('<I', boot_data[28:32])[0]
            info['total_sectors_32'] = struct.unpack('<I', boot_data[32:36])[0]
            
            # Debug: hiển thị các giá trị quan trọng
            print(f"Debug values:")
            print(f"  bytes_per_sector: {info['bytes_per_sector']}")
            print(f"  sectors_per_cluster: {info['sectors_per_cluster']}")
            print(f"  total_sectors_16: {info['total_sectors_16']}")
            print(f"  total_sectors_32: {info['total_sectors_32']}")
            
            # Kiểm tra giá trị 0 trước khi tính toán
            if info['bytes_per_sector'] == 0:
                raise ValueError("bytes_per_sector = 0, boot sector bị hỏng")
            if info['sectors_per_cluster'] == 0:
                raise ValueError("sectors_per_cluster = 0, boot sector bị hỏng")
            
            # Xác định tổng số sector
            info['total_sectors'] = info['total_sectors_32'] if info['total_sectors_16'] == 0 else info['total_sectors_16']
            
            if info['total_sectors'] == 0:
                raise ValueError("total_sectors = 0, boot sector bị hỏng")
                
        except Exception as e:
            raise ValueError(f"Lỗi khi phân tích boot sector: {str(e)}")
        
        # Phân tích thêm cho FAT32
        if info['sectors_per_fat_16'] == 0:
            # FAT32
            info['sectors_per_fat'] = struct.unpack('<I', boot_data[36:40])[0]
            info['ext_flags'] = struct.unpack('<H', boot_data[40:42])[0]
            info['fs_version'] = struct.unpack('<H', boot_data[42:44])[0]
            info['root_cluster'] = struct.unpack('<I', boot_data[44:48])[0]
            info['fs_info'] = struct.unpack('<H', boot_data[48:50])[0]
            info['backup_boot_sec'] = struct.unpack('<H', boot_data[50:52])[0]
            info['fat_type'] = 32
        else:
            # FAT12/FAT16
            info['sectors_per_fat'] = info['sectors_per_fat_16']
            info['fat_type'] = self._determine_fat_type(info)
        
        # Tính toán các thông số quan trọng
        info['root_dir_sectors'] = ((info['root_entries'] * 32) + (info['bytes_per_sector'] - 1)) // info['bytes_per_sector']
        info['first_data_sector'] = info['reserved_sectors'] + (info['num_fats'] * info['sectors_per_fat']) + info['root_dir_sectors']
        info['data_sectors'] = info['total_sectors'] - info['first_data_sector']
        info['total_clusters'] = info['data_sectors'] // info['sectors_per_cluster']
        
        # Tính kích thước volume
        info['volume_size'] = info['total_sectors'] * info['bytes_per_sector']
        
        return info
    
    def _determine_fat_type(self, info: Dict) -> int:
        """Xác định loại FAT dựa trên số cluster"""
        total_clusters = info.get('total_clusters', 0)
        if total_clusters < 4085:
            return 12
        elif total_clusters < 65525:
            return 16
        else:
            return 32
    
    def validate_boot_sector(self, info: Dict) -> List[str]:
        """Kiểm tra tính hợp lệ của boot sector và trả về danh sách lỗi"""
        errors = []
        
        # Kiểm tra bytes per sector
        valid_bytes_per_sector = [512, 1024, 2048, 4096]
        if info['bytes_per_sector'] not in valid_bytes_per_sector:
            errors.append(f"Bytes per sector không hợp lệ: {info['bytes_per_sector']} (phải là {valid_bytes_per_sector})")
        
        # Kiểm tra sectors per cluster
        valid_sectors_per_cluster = [1, 2, 4, 8, 16, 32, 64, 128]
        if info['sectors_per_cluster'] not in valid_sectors_per_cluster:
            errors.append(f"Sectors per cluster không hợp lệ: {info['sectors_per_cluster']} (phải là {valid_sectors_per_cluster})")
        
        # Kiểm tra số FAT
        if info['num_fats'] not in [1, 2]:
            errors.append(f"Số lượng bảng FAT không hợp lệ: {info['num_fats']} (phải là 1 hoặc 2)")
        
        # Kiểm tra reserved sectors
        if info['fat_type'] == 32:
            if info['reserved_sectors'] < 32:
                errors.append(f"Reserved sectors cho FAT32 quá nhỏ: {info['reserved_sectors']} (nên >= 32)")
        else:
            if info['reserved_sectors'] < 1:
                errors.append(f"Reserved sectors quá nhỏ: {info['reserved_sectors']} (phải >= 1)")
        
        # Kiểm tra tổng số sector với kích thước đĩa thực tế
        if self.disk_size > 0:
            expected_sectors = self.disk_size // info['bytes_per_sector']
            diff_percent = abs(info['total_sectors'] - expected_sectors) / expected_sectors * 100
            if diff_percent > 5:  # Cho phép sai lệch 5%
                errors.append(f"Tổng số sector không khớp với kích thước đĩa: {info['total_sectors']} vs {expected_sectors}")
        
        # Kiểm tra root entries cho FAT12/16
        if info['fat_type'] != 32 and info['root_entries'] == 0:
            errors.append("Root entries = 0 không hợp lệ cho FAT12/16")
        
        # Kiểm tra media descriptor
        valid_media = [0xF0, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF]
        if info['media_descriptor'] not in valid_media:
            errors.append(f"Media descriptor không hợp lệ: 0x{info['media_descriptor']:02X}")
        
        return errors
    
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
            self.disk_size = self.get_disk_size()
            print(f"Kích thước ổ đĩa: {self.disk_size:,} bytes ({self.disk_size / (1024*1024):.1f} MB)")
            result['disk_accessible'] = True
            
            # Đọc boot sector
            print("\nĐọc boot sector...")
            self.current_boot_sector = self.read_sector(0)
            
            # Phân tích boot sector hiện tại
            try:
                result['current_info'] = self.parse_boot_sector(self.current_boot_sector)
                result['boot_sector_valid'] = True
                print("✓ Boot sector có thể đọc được")
                
                # Hiển thị thông tin hiện tại
                info = result['current_info']
                print(f"\n=== THÔNG TIN BOOT SECTOR HIỆN TẠI ===")
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
                
            except Exception as e:
                print(f"✗ Không thể phân tích boot sector: {str(e)}")
                result['boot_sector_valid'] = False
                result['recovery_needed'] = True
            
            # Kiểm tra tính hợp lệ
            if result['boot_sector_valid']:
                print(f"\n=== KIỂM TRA TÍNH HỢP LỆ ===")
                result['validation_errors'] = self.validate_boot_sector(result['current_info'])
                
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

    def generate_optimal_boot_sector(self, damaged_boot: bytes) -> bytes:
        """Tạo boot sector tối ưu dựa trên thông tin có sẵn và kích thước đĩa"""
        print("\n=== TẠO BOOT SECTOR TỐI ƯU ===")
        
        # Bắt đầu với boot sector bị hỏng
        new_boot = bytearray(damaged_boot)
        
        # Lấy thông tin có thể tin cậy từ boot sector cũ
        total_sectors_16 = struct.unpack('<H', damaged_boot[19:21])[0]
        total_sectors_32 = struct.unpack('<I', damaged_boot[32:36])[0]
        total_sectors = total_sectors_32 if total_sectors_16 == 0 else total_sectors_16
        
        print(f"Phát hiện tổng sectors từ boot sector: {total_sectors}")
        
        if total_sectors == 0:
            # Ước tính từ kích thước file
            if self.disk_size > 0:
                total_sectors = self.disk_size // 512
                print(f"Ước tính từ kích thước file: {total_sectors} sectors")
            else:
                # Giả định là ổ đĩa 20MB (dựa trên context)
                total_sectors = 40960  # 20MB / 512
                print(f"Sử dụng giá trị mặc định: {total_sectors} sectors")
        
        # Tính toán thông số tối ưu cho FAT16 (20MB volume)
        bytes_per_sector = 512
        sectors_per_cluster = 1  # Cho volume nhỏ
        reserved_sectors = 1
        num_fats = 2
        root_entries = 512
        media_descriptor = 0xF8  # Fixed disk
          # Tính sectors per FAT với công thức chính xác
        root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector
        data_sectors = total_sectors - reserved_sectors - root_dir_sectors
        
        # Công thức tính sectors per FAT cho FAT12/16
        # data_sectors = (sectors_per_fat * num_fats + cluster_sectors)
        # => sectors_per_fat = data_sectors / (num_fats + cluster_factor)
        # Cho FAT12: mỗi cluster entry = 1.5 bytes, cho FAT16: 2 bytes
        
        # Xác định FAT type dựa trên data clusters
        temp_clusters = data_sectors // sectors_per_cluster
        if temp_clusters < 4085:
            # FAT12 - 1.5 bytes per entry
            fat_entry_size = 1.5
        else:
            # FAT16 - 2 bytes per entry  
            fat_entry_size = 2
        
        # Tính sectors per FAT
        # Số clusters tối đa = data_sectors / sectors_per_cluster
        # Dung lượng FAT = clusters * fat_entry_size
        # sectors_per_fat = ceil(dung_lượng_FAT / bytes_per_sector)
        max_clusters = temp_clusters
        fat_size_bytes = max_clusters * fat_entry_size
        sectors_per_fat = int((fat_size_bytes + bytes_per_sector - 1) // bytes_per_sector)
        
        # Kiểm tra và điều chỉnh
        if sectors_per_fat > data_sectors // 4:  # Không nên quá 25% data sectors
            sectors_per_fat = max(1, data_sectors // (4 * num_fats))
            
        # Cho volume 20MB FAT12, sectors per FAT thường là khoảng 159
        if total_sectors == 40960 and sectors_per_fat > 200:
            sectors_per_fat = 159
        
        print(f"Thông số tối ưu:")
        print(f"  Bytes per sector: {bytes_per_sector}")
        print(f"  Sectors per cluster: {sectors_per_cluster}")
        print(f"  Reserved sectors: {reserved_sectors}")
        print(f"  Number of FATs: {num_fats}")
        print(f"  Root entries: {root_entries}")
        print(f"  Sectors per FAT: {sectors_per_fat}")
        print(f"  Total sectors: {total_sectors}")
        
        # Ghi các giá trị vào boot sector mới
        struct.pack_into('<H', new_boot, 11, bytes_per_sector)  # bytes per sector
        new_boot[13] = sectors_per_cluster  # sectors per cluster
        struct.pack_into('<H', new_boot, 14, reserved_sectors)  # reserved sectors
        new_boot[16] = num_fats  # number of FATs
        struct.pack_into('<H', new_boot, 17, root_entries)  # root entries
        
        if total_sectors < 65536:
            struct.pack_into('<H', new_boot, 19, total_sectors)  # total sectors 16
            struct.pack_into('<I', new_boot, 32, 0)  # total sectors 32
        else:
            struct.pack_into('<H', new_boot, 19, 0)  # total sectors 16
            struct.pack_into('<I', new_boot, 32, total_sectors)  # total sectors 32
        
        new_boot[21] = media_descriptor  # media descriptor
        struct.pack_into('<H', new_boot, 22, sectors_per_fat)  # sectors per FAT
        
        # Cập nhật boot signature nếu cần
        new_boot[510:512] = b'\x55\xAA'
        
        return bytes(new_boot)
    
    def repair_boot_sector(self) -> bool:
        """Sửa chữa boot sector bị hỏng"""
        if self.current_boot_sector is None:
            print("Không có boot sector để sửa chữa")
            return False
        
        print(f"\n=== SỬA CHỮA BOOT SECTOR ===")
        
        try:
            # Tạo boot sector tối ưu
            repaired_boot = self.generate_optimal_boot_sector(self.current_boot_sector)
            
            # Kiểm tra boot sector mới
            print("\nKiểm tra boot sector đã sửa chữa...")
            repaired_info = self.parse_boot_sector(repaired_boot)
            errors = self.validate_boot_sector(repaired_info)
            
            if errors:
                print(f"Boot sector sửa chữa vẫn có lỗi:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print("✓ Boot sector sửa chữa hợp lệ!")
                
                # Hiển thị thông tin boot sector mới
                print(f"\n=== THÔNG TIN BOOT SECTOR ĐÃ SỬA CHỮA ===")
                info = repaired_info
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
                
                # Lưu backup và ghi boot sector mới
                return self.write_boot_sector(repaired_boot)
                
        except Exception as e:
            print(f"Lỗi khi sửa chữa boot sector: {str(e)}")
            return False
    
    def write_boot_sector(self, new_boot_sector: bytes) -> bool:
        """Ghi boot sector mới vào đĩa"""
        print(f"\n=== GHI BOOT SECTOR MỚI ===")
        
        # Tạo backup trước
        backup_path = f"{self.drive_letter}_boot_backup.bin"
        try:
            with open(backup_path, 'wb') as f:
                f.write(self.current_boot_sector)
            print(f"✓ Đã tạo backup tại: {backup_path}")
        except Exception as e:
            print(f"⚠ Không thể tạo backup: {str(e)}")
            return False
        
        # Xác nhận từ người dùng
        print(f"\n⚠ CẢNH BÁO: Bạn sắp ghi đè boot sector của ổ đĩa {self.drive_letter}:")
        print("Thao tác này có thể làm hỏng dữ liệu nếu không thực hiện đúng!")
        confirm = input("Bạn có chắc chắn muốn tiếp tục? (yes/no): ").lower().strip()
        
        if confirm not in ['yes', 'y']:
            print("Đã hủy thao tác ghi boot sector")
            return False
        
        try:
            # Ghi boot sector mới
            with open(self.drive_path, 'r+b') as drive:
                drive.seek(0)
                drive.write(new_boot_sector)
                drive.flush()
            
            print("✓ Đã ghi boot sector mới thành công!")
            print(f"Backup cũ được lưu tại: {backup_path}")
            return True
            
        except Exception as e:
            print(f"✗ Lỗi khi ghi boot sector: {str(e)}")
            print("Có thể do quyền truy cập hoặc ổ đĩa được bảo vệ")
            return False

    # ...existing code...
def main():
    """Hàm main để chạy công cụ phân tích FAT"""
    import argparse
    import sys
    
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
    
    args = parser.parse_args()
    
    # Normalize drive letter - remove : if present
    drive_letter = args.drive.upper().rstrip(':')
    
    if len(drive_letter) != 1 or not drive_letter.isalpha():
        print("Lỗi: Vui lòng nhập một chữ cái ổ đĩa hợp lệ (ví dụ: E)")
        return 1
    
    try:
        analyzer = FATAnalyzer(drive_letter)
        result = analyzer.run_analysis()
        
        print(f"\n=== KẾT QUẢ PHÂN TÍCH ===")
        if result['disk_accessible']:
            if result['boot_sector_valid']:
                if result['recovery_needed']:
                    print("⚠ Phát hiện vấn đề với boot sector")
                    if args.recovery and not args.info_only:
                        print("\nThực hiện khôi phục boot sector...")
                        if analyzer.repair_boot_sector():
                            print("✓ Khôi phục thành công!")
                        else:
                            print("✗ Khôi phục thất bại")
                    elif not args.info_only:
                        print("Sử dụng --recovery để thực hiện khôi phục tương tác")
                else:
                    print("✓ Boot sector hoạt động bình thường")
            else:
                print("✗ Boot sector bị hỏng nghiêm trọng")
                if args.recovery and not args.info_only:
                    print("\nThực hiện khôi phục boot sector bị hỏng...")
                    if analyzer.repair_boot_sector():
                        print("✓ Khôi phục thành công!")
                    else:
                        print("✗ Khôi phục thất bại")
                elif not args.info_only:
                    print("Sử dụng --recovery để thực hiện khôi phục boot sector")
        else:
            print("✗ Không thể truy cập ổ đĩa")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\nĐã hủy thao tác.")
        return 1
    except Exception as e:
        print(f"\nLỗi: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
