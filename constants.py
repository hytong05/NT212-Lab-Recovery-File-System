#!/usr/bin/env python3
"""
Constants and configuration for FAT Recovery Tool
Các hằng số và cấu hình cho công cụ khôi phục FAT
"""

# Boot sector signature
BOOT_SIGNATURE = b'\x55\xAA'

# Valid bytes per sector values
VALID_BYTES_PER_SECTOR = [512, 1024, 2048, 4096]

# Valid sectors per cluster values
VALID_SECTORS_PER_CLUSTER = [1, 2, 4, 8, 16, 32, 64, 128]

# Valid number of FATs
VALID_NUM_FATS = [1, 2]

# Valid media descriptor values
VALID_MEDIA_DESCRIPTORS = [0xF0, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF]

# FAT type thresholds
FAT12_MAX_CLUSTERS = 4085
FAT16_MAX_CLUSTERS = 65525

# Default values for recovery
DEFAULT_BYTES_PER_SECTOR = 512
DEFAULT_SECTORS_PER_CLUSTER = 1
DEFAULT_RESERVED_SECTORS = 1
DEFAULT_NUM_FATS = 2
DEFAULT_ROOT_ENTRIES = 512
DEFAULT_MEDIA_DESCRIPTOR = 0xF8  # Fixed disk

# FAT32 minimum reserved sectors
FAT32_MIN_RESERVED_SECTORS = 32

# Sector size
SECTOR_SIZE = 512

# Windows disk geometry IOCTL code
IOCTL_DISK_GET_DRIVE_GEOMETRY = 0x00070000

# Default disk size for estimation (20MB)
DEFAULT_DISK_SIZE_SECTORS = 40960  # 20MB / 512
