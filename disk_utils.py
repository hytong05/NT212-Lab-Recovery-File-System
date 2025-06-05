#!/usr/bin/env python3
"""
Disk utilities for FAT Recovery Tool
Các tiện ích xử lý đĩa cho công cụ khôi phục FAT
"""

import os
import struct
from typing import Optional
from constants import SECTOR_SIZE, IOCTL_DISK_GET_DRIVE_GEOMETRY


class DiskReader:
    """Lớp xử lý đọc/ghi đĩa"""
    
    def __init__(self, drive_letter: str):
        self.drive_letter = drive_letter.upper()
        self.drive_path = f"\\\\.\\{self.drive_letter}:"
    
    def read_sector(self, sector_num: int, num_sectors: int = 1) -> bytes:
        """Đọc sector từ ổ đĩa"""
        try:
            with open(self.drive_path, 'rb') as drive:
                drive.seek(sector_num * SECTOR_SIZE)
                return drive.read(num_sectors * SECTOR_SIZE)
        except Exception as e:
            raise Exception(f"Không thể đọc sector {sector_num}: {str(e)}")
    
    def write_sector(self, sector_num: int, data: bytes) -> bool:
        """Ghi data vào sector"""
        try:
            with open(self.drive_path, 'r+b') as drive:
                drive.seek(sector_num * SECTOR_SIZE)
                drive.write(data)
                drive.flush()
            return True
        except Exception as e:
            raise Exception(f"Không thể ghi sector {sector_num}: {str(e)}")
    
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
            statvfs = os.statvfs(f"{self.drive_letter}:\\")
            return statvfs.f_frsize * statvfs.f_blocks
        except:
            pass
        
        print("Warning: Could not determine disk size, using default")
        return 0


def create_backup(file_path: str, data: bytes) -> bool:
    """Tạo backup file"""
    try:
        with open(file_path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"Không thể tạo backup: {str(e)}")
        return False


def hex_dump(data: bytes, start_offset: int = 0, max_bytes: int = 64) -> None:
    """Hiển thị hex dump của data"""
    print(f"Hex dump (first {min(max_bytes, len(data))} bytes):")
    for i in range(0, min(max_bytes, len(data)), 16):
        offset = start_offset + i
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        print(f"{offset:04X}: {hex_str:<48} {ascii_str}")
