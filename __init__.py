#!/usr/bin/env python3
"""
Package initialization for FAT Recovery Tool
Khởi tạo package cho công cụ khôi phục FAT
"""

from .fat_analyzer import FATAnalyzer
from .boot_sector import BootSectorParser, BootSectorValidator, BootSectorGenerator
from .disk_utils import DiskReader, create_backup, hex_dump
from .cli import FATRecoveryCLI
from .constants import *

__version__ = "1.0.0"
__author__ = "FAT Recovery Tool Team"

# Export main classes
__all__ = [
    'FATAnalyzer',
    'BootSectorParser', 
    'BootSectorValidator',
    'BootSectorGenerator',
    'DiskReader',
    'FATRecoveryCLI',
    'create_backup',
    'hex_dump'
]
