import struct
import os
from fat.reader import read_volume_sectors

def extract_fat_parameters_from_disk(drive_letter):
    """Extract FAT parameters by scanning the disk and making educated guesses"""
    possible_boot_sectors = []
    
    # Scan first 50 sectors for potential boot sectors
    for sector in range(0, 50):
        try:
            data = read_volume_sectors(drive_letter, sector, 1)
            
            # Check for boot sector signatures
            if data[510:512] == b'\x55\xAA':
                # Check if this looks like a FAT boot sector
                oem_name = data[3:11]
                bytes_per_sector = struct.unpack('<H', data[11:13])[0]
                sectors_per_cluster = data[13]
                
                # Basic validation
                if (bytes_per_sector in [512, 1024, 2048, 4096] and 
                    sectors_per_cluster in [1, 2, 4, 8, 16, 32, 64, 128]):
                    
                    possible_boot_sectors.append({
                        'sector': sector,
                        'data': data,
                        'oem_name': oem_name,
                        'bytes_per_sector': bytes_per_sector,
                        'sectors_per_cluster': sectors_per_cluster
                    })
        except:
            pass
    
    return possible_boot_sectors

def recover_boot_sector(drive_letter, output_path=None):
    """Attempt to recover a damaged boot sector"""
    print("Scanning for potential boot sectors...")
    candidates = extract_fat_parameters_from_disk(drive_letter)
    
    if not candidates:
        print("No valid boot sectors found!")
        return None
    
    print(f"Found {len(candidates)} potential boot sector(s):")
    
    for i, candidate in enumerate(candidates):
        print(f"\nCandidate {i+1}:")
        print(f"  Sector: {candidate['sector']}")
        print(f"  OEM Name: {candidate['oem_name']}")
        print(f"  Bytes per sector: {candidate['bytes_per_sector']}")
        print(f"  Sectors per cluster: {candidate['sectors_per_cluster']}")
    
    # Save the first candidate (most likely valid) if output requested
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(candidates[0]['data'])
        print(f"\nSaved most likely boot sector to {output_path}")
    
    return candidates[0]['data'] if candidates else None

def rebuild_boot_sector(drive_letter, bytes_per_sector=512, sectors_per_cluster=8, 
                        num_fats=2, reserved_sectors=1, root_entries=512):
    """Create a new boot sector with the specified parameters"""
    boot = bytearray(512)
    
    # Basic boot code (jump instruction)
    boot[0:3] = b'\xEB\x3C\x90'
    
    # OEM Name (8 bytes)
    oem_name = b'FATRECOV'
    boot[3:11] = oem_name
    
    # Bytes per sector (2 bytes)
    boot[11:13] = struct.pack('<H', bytes_per_sector)
    
    # Sectors per cluster (1 byte)
    boot[13] = sectors_per_cluster
    
    # Reserved sectors (2 bytes)
    boot[14:16] = struct.pack('<H', reserved_sectors)
    
    # Number of FATs (1 byte)
    boot[16] = num_fats
    
    # Root directory entries (2 bytes)
    boot[17:19] = struct.pack('<H', root_entries)
    
    # Add boot signature
    boot[510:512] = b'\x55\xAA'
    
    return boot