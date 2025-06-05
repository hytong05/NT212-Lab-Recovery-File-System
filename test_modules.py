#!/usr/bin/env python3
"""
Unit tests for FAT Recovery Tool modules
Test đơn vị cho các module của công cụ khôi phục FAT
"""

import unittest
import struct
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import *
from boot_sector import BootSectorParser, BootSectorValidator, BootSectorGenerator
from disk_utils import hex_dump, create_backup


class TestConstants(unittest.TestCase):
    """Test constants module"""
    
    def test_boot_signature(self):
        """Test boot signature constant"""
        self.assertEqual(BOOT_SIGNATURE, b'\x55\xAA')
        self.assertEqual(len(BOOT_SIGNATURE), 2)
    
    def test_valid_values(self):
        """Test valid values lists"""
        self.assertIn(512, VALID_BYTES_PER_SECTOR)
        self.assertIn(1, VALID_SECTORS_PER_CLUSTER)
        self.assertIn(2, VALID_NUM_FATS)
        self.assertIn(0xF8, VALID_MEDIA_DESCRIPTORS)
    
    def test_fat_thresholds(self):
        """Test FAT type thresholds"""
        self.assertEqual(FAT12_MAX_CLUSTERS, 4085)
        self.assertEqual(FAT16_MAX_CLUSTERS, 65525)


class TestBootSectorParser(unittest.TestCase):
    """Test boot sector parser"""
    
    def setUp(self):
        """Set up test data"""
        # Create a valid FAT12 boot sector
        self.valid_boot = bytearray(512)
        self.valid_boot[3:11] = b'TESTFAT '
        self.valid_boot[11:13] = struct.pack('<H', 512)  # bytes per sector
        self.valid_boot[13] = 1  # sectors per cluster
        self.valid_boot[14:16] = struct.pack('<H', 1)  # reserved sectors
        self.valid_boot[16] = 2  # num fats
        self.valid_boot[17:19] = struct.pack('<H', 512)  # root entries
        self.valid_boot[19:21] = struct.pack('<H', 40960)  # total sectors 16
        self.valid_boot[21] = 0xF8  # media descriptor
        self.valid_boot[22:24] = struct.pack('<H', 159)  # sectors per fat
        self.valid_boot[510:512] = BOOT_SIGNATURE
    
    def test_parse_valid_boot_sector(self):
        """Test parsing valid boot sector"""
        info = BootSectorParser.parse_boot_sector(bytes(self.valid_boot))
        
        self.assertEqual(info['oem_name'], 'TESTFAT')
        self.assertEqual(info['bytes_per_sector'], 512)
        self.assertEqual(info['sectors_per_cluster'], 1)
        self.assertEqual(info['num_fats'], 2)
        self.assertEqual(info['fat_type'], 12)
        self.assertEqual(info['total_sectors'], 40960)
    
    def test_parse_invalid_boot_sector(self):
        """Test parsing invalid boot sector"""
        # Test with too short data
        with self.assertRaises(ValueError):
            BootSectorParser.parse_boot_sector(b'\x00' * 100)
        
        # Test with zero bytes per sector
        invalid_boot = bytearray(self.valid_boot)
        invalid_boot[11:13] = struct.pack('<H', 0)
        
        with self.assertRaises(ValueError):
            BootSectorParser.parse_boot_sector(bytes(invalid_boot))
    
    def test_determine_fat_type(self):
        """Test FAT type determination"""
        # Test data with different cluster counts
        test_cases = [
            ({'total_clusters': 1000}, 12),
            ({'total_clusters': 10000}, 16),
            ({'total_clusters': 100000}, 32)
        ]
        
        for info, expected_type in test_cases:
            result = BootSectorParser._determine_fat_type(info)
            self.assertEqual(result, expected_type)


class TestBootSectorValidator(unittest.TestCase):
    """Test boot sector validator"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_info = {
            'bytes_per_sector': 512,
            'sectors_per_cluster': 1,
            'num_fats': 2,
            'reserved_sectors': 1,
            'fat_type': 12,
            'root_entries': 512,
            'media_descriptor': 0xF8,
            'total_sectors': 40960
        }
    
    def test_validate_valid_boot_sector(self):
        """Test validation of valid boot sector"""
        errors = BootSectorValidator.validate_boot_sector(self.valid_info)
        self.assertEqual(len(errors), 0)
    
    def test_validate_invalid_bytes_per_sector(self):
        """Test validation with invalid bytes per sector"""
        invalid_info = self.valid_info.copy()
        invalid_info['bytes_per_sector'] = 1000  # Invalid value
        
        errors = BootSectorValidator.validate_boot_sector(invalid_info)
        self.assertTrue(any('Bytes per sector' in error for error in errors))
    
    def test_validate_invalid_sectors_per_cluster(self):
        """Test validation with invalid sectors per cluster"""
        invalid_info = self.valid_info.copy()
        invalid_info['sectors_per_cluster'] = 3  # Invalid value
        
        errors = BootSectorValidator.validate_boot_sector(invalid_info)
        self.assertTrue(any('Sectors per cluster' in error for error in errors))


class TestBootSectorGenerator(unittest.TestCase):
    """Test boot sector generator"""
    
    def test_generate_optimal_boot_sector(self):
        """Test generating optimal boot sector"""
        # Create damaged boot sector
        damaged_boot = bytearray(512)
        damaged_boot[19:21] = struct.pack('<H', 40960)  # total sectors
        
        # Generate optimal boot sector
        optimal_boot = BootSectorGenerator.generate_optimal_boot_sector(
            bytes(damaged_boot), disk_size=20*1024*1024
        )
        
        # Verify boot signature
        self.assertEqual(optimal_boot[510:512], BOOT_SIGNATURE)
        
        # Verify some key fields
        bytes_per_sector = struct.unpack('<H', optimal_boot[11:13])[0]
        self.assertEqual(bytes_per_sector, 512)
        
        sectors_per_cluster = optimal_boot[13]
        self.assertEqual(sectors_per_cluster, 1)


class TestDiskUtils(unittest.TestCase):
    """Test disk utilities"""
    
    def test_create_backup(self):
        """Test backup creation"""
        test_data = b'test backup data'
        test_file = 'test_backup.tmp'
        
        try:
            # Create backup
            result = create_backup(test_file, test_data)
            self.assertTrue(result)
            
            # Verify backup content
            with open(test_file, 'rb') as f:
                saved_data = f.read()
            self.assertEqual(saved_data, test_data)
            
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_hex_dump(self):
        """Test hex dump function"""
        test_data = b'\x00\x01\x02\x03\x04\x05\x06\x07'
        
        # This should not raise any exception
        try:
            hex_dump(test_data, max_bytes=8)
        except Exception as e:
            self.fail(f"hex_dump raised {type(e).__name__}: {e}")


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestConstants,
        TestBootSectorParser,
        TestBootSectorValidator,
        TestBootSectorGenerator,
        TestDiskUtils
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("FAT RECOVERY TOOL - UNIT TESTS")
    print("=" * 50)
    
    success = run_tests()
    
    if success:
        print("\n✓ Tất cả test cases đều pass!")
        sys.exit(0)
    else:
        print("\n✗ Một số test cases bị fail!")
        sys.exit(1)
