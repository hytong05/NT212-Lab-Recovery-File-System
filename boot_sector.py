#!/usr/bin/env python3
"""
Boot sector analysis and handling for FAT Recovery Tool
Phân tích và xử lý boot sector cho công cụ khôi phục FAT
"""

import struct
from typing import Dict, List
from constants import (
    BOOT_SIGNATURE, VALID_BYTES_PER_SECTOR, VALID_SECTORS_PER_CLUSTER,
    VALID_NUM_FATS, VALID_MEDIA_DESCRIPTORS, FAT12_MAX_CLUSTERS, FAT16_MAX_CLUSTERS,
    FAT32_MIN_RESERVED_SECTORS, DEFAULT_BYTES_PER_SECTOR, DEFAULT_SECTORS_PER_CLUSTER,
    DEFAULT_RESERVED_SECTORS, DEFAULT_NUM_FATS, DEFAULT_ROOT_ENTRIES, DEFAULT_MEDIA_DESCRIPTOR,
    DEFAULT_DISK_SIZE_SECTORS, SECTOR_SIZE
)
from disk_utils import hex_dump


class BootSectorParser:
    """Lớp phân tích boot sector"""
    
    @staticmethod
    def parse_boot_sector(boot_data: bytes) -> Dict:
        """Phân tích boot sector và trích xuất thông tin"""
        if len(boot_data) < 512:
            raise ValueError("Boot sector không đủ 512 bytes")
        
        # Hiển thị hex dump đầu tiên của boot sector để debug
        print("Boot sector hex dump (first 64 bytes):")
        hex_dump(boot_data, max_bytes=64)
        
        # Kiểm tra chữ ký boot sector
        if boot_data[510:512] != BOOT_SIGNATURE:
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
            print("Debug values:")
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
            info['fat_type'] = BootSectorParser._determine_fat_type(info)
        
        # Tính toán các thông số quan trọng
        info['root_dir_sectors'] = ((info['root_entries'] * 32) + (info['bytes_per_sector'] - 1)) // info['bytes_per_sector']
        info['first_data_sector'] = info['reserved_sectors'] + (info['num_fats'] * info['sectors_per_fat']) + info['root_dir_sectors']
        info['data_sectors'] = info['total_sectors'] - info['first_data_sector']
        info['total_clusters'] = info['data_sectors'] // info['sectors_per_cluster']
        
        # Tính kích thước volume
        info['volume_size'] = info['total_sectors'] * info['bytes_per_sector']
        
        return info
    
    @staticmethod
    def _determine_fat_type(info: Dict) -> int:
        """Xác định loại FAT dựa trên số cluster"""
        total_clusters = info.get('total_clusters', 0)
        if total_clusters < FAT12_MAX_CLUSTERS:
            return 12
        elif total_clusters < FAT16_MAX_CLUSTERS:
            return 16
        else:
            return 32


class BootSectorValidator:
    """Lớp kiểm tra tính hợp lệ của boot sector"""
    
    @staticmethod
    def validate_boot_sector(info: Dict, disk_size: int = 0) -> List[str]:
        """Kiểm tra tính hợp lệ của boot sector và trả về danh sách lỗi"""
        errors = []
        
        # Kiểm tra bytes per sector
        if info['bytes_per_sector'] not in VALID_BYTES_PER_SECTOR:
            errors.append(f"Bytes per sector không hợp lệ: {info['bytes_per_sector']} (phải là {VALID_BYTES_PER_SECTOR})")
        
        # Kiểm tra sectors per cluster
        if info['sectors_per_cluster'] not in VALID_SECTORS_PER_CLUSTER:
            errors.append(f"Sectors per cluster không hợp lệ: {info['sectors_per_cluster']} (phải là {VALID_SECTORS_PER_CLUSTER})")
        
        # Kiểm tra số FAT
        if info['num_fats'] not in VALID_NUM_FATS:
            errors.append(f"Số lượng bảng FAT không hợp lệ: {info['num_fats']} (phải là 1 hoặc 2)")
        
        # Kiểm tra reserved sectors
        if info['fat_type'] == 32:
            if info['reserved_sectors'] < FAT32_MIN_RESERVED_SECTORS:
                errors.append(f"Reserved sectors cho FAT32 quá nhỏ: {info['reserved_sectors']} (nên >= {FAT32_MIN_RESERVED_SECTORS})")
        else:
            if info['reserved_sectors'] < 1:
                errors.append(f"Reserved sectors quá nhỏ: {info['reserved_sectors']} (phải >= 1)")
        
        # Kiểm tra tổng số sector với kích thước đĩa thực tế
        if disk_size > 0:
            expected_sectors = disk_size // info['bytes_per_sector']
            diff_percent = abs(info['total_sectors'] - expected_sectors) / expected_sectors * 100
            if diff_percent > 5:  # Cho phép sai lệch 5%
                errors.append(f"Tổng số sector không khớp với kích thước đĩa: {info['total_sectors']} vs {expected_sectors}")
        
        # Kiểm tra root entries cho FAT12/16
        if info['fat_type'] != 32 and info['root_entries'] == 0:
            errors.append("Root entries = 0 không hợp lệ cho FAT12/16")
        
        # Kiểm tra media descriptor
        if info['media_descriptor'] not in VALID_MEDIA_DESCRIPTORS:
            errors.append(f"Media descriptor không hợp lệ: 0x{info['media_descriptor']:02X}")
        
        return errors


class BootSectorGenerator:
    """Lớp tạo boot sector tối ưu"""
    
    @staticmethod
    def generate_optimal_boot_sector(damaged_boot: bytes, disk_size: int = 0) -> bytes:
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
            if disk_size > 0:
                total_sectors = disk_size // SECTOR_SIZE
                print(f"Ước tính từ kích thước file: {total_sectors} sectors")
            else:
                # Giả định là ổ đĩa 20MB (dựa trên context)
                total_sectors = DEFAULT_DISK_SIZE_SECTORS
                print(f"Sử dụng giá trị mặc định: {total_sectors} sectors")
        
        # Tính toán thông số tối ưu cho FAT16
        bytes_per_sector = DEFAULT_BYTES_PER_SECTOR
        sectors_per_cluster = DEFAULT_SECTORS_PER_CLUSTER
        reserved_sectors = DEFAULT_RESERVED_SECTORS
        num_fats = DEFAULT_NUM_FATS
        root_entries = DEFAULT_ROOT_ENTRIES
        media_descriptor = DEFAULT_MEDIA_DESCRIPTOR
        
        # Tính sectors per FAT với công thức chính xác
        root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector
        data_sectors = total_sectors - reserved_sectors - root_dir_sectors
        
        # Xác định FAT type dựa trên data clusters
        temp_clusters = data_sectors // sectors_per_cluster
        if temp_clusters < FAT12_MAX_CLUSTERS:
            # FAT12 - 1.5 bytes per entry
            fat_entry_size = 1.5
        else:
            # FAT16 - 2 bytes per entry  
            fat_entry_size = 2
        
        # Tính sectors per FAT
        max_clusters = temp_clusters
        fat_size_bytes = max_clusters * fat_entry_size
        sectors_per_fat = int((fat_size_bytes + bytes_per_sector - 1) // bytes_per_sector)
        
        # Kiểm tra và điều chỉnh
        if sectors_per_fat > data_sectors // 4:  # Không nên quá 25% data sectors
            sectors_per_fat = max(1, data_sectors // (4 * num_fats))
            
        # Cho volume 20MB FAT12, sectors per FAT thường là khoảng 159
        if total_sectors == DEFAULT_DISK_SIZE_SECTORS and sectors_per_fat > 200:
            sectors_per_fat = 159
        
        print("Thông số tối ưu:")
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
        new_boot[510:512] = BOOT_SIGNATURE
        
        return bytes(new_boot)
