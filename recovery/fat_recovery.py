import struct
from fat.reader import read_volume_sectors

def find_fat_copies(drive_letter, boot_sector):
    """Find and compare FAT copies to determine corruption"""
    bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
    sectors_per_fat = struct.unpack('<H', boot_sector[22:24])[0]
    reserved_sectors = struct.unpack('<H', boot_sector[14:16])[0]
    num_fats = boot_sector[16]
    
    fat_copies = []
    
    # Read all FAT copies
    for i in range(num_fats):
        start_sector = reserved_sectors + (i * sectors_per_fat)
        try:
            fat_data = read_volume_sectors(drive_letter, start_sector, sectors_per_fat, bytes_per_sector)
            fat_copies.append({
                'index': i+1,
                'start_sector': start_sector,
                'data': fat_data
            })
        except Exception as e:
            print(f"Error reading FAT {i+1}: {e}")
    
    return fat_copies

def compare_fat_copies(fat_copies):
    """Compare FAT copies to find differences"""
    if len(fat_copies) < 2:
        return None
    
    diffs = []
    primary_fat = fat_copies[0]['data']
    
    for i in range(1, len(fat_copies)):
        secondary_fat = fat_copies[i]['data']
        
        # Skip if FATs are of different sizes
        if len(primary_fat) != len(secondary_fat):
            diffs.append(f"FAT {i+1} has different size than primary FAT")
            continue
            
        diff_count = 0
        diff_positions = []
        
        for pos in range(0, len(primary_fat), 2):
            if pos + 2 > len(primary_fat):
                break
                
            val1 = struct.unpack('<H', primary_fat[pos:pos+2])[0]
            val2 = struct.unpack('<H', secondary_fat[pos:pos+2])[0]
            
            if val1 != val2:
                diff_count += 1
                if diff_count <= 10:  # Show only first 10 diffs
                    diff_positions.append(f"Entry {pos//2}: {val1:04X}h vs {val2:04X}h")
        
        if diff_count > 0:
            diffs.append({
                'fat_index': i+1, 
                'diff_count': diff_count,
                'examples': diff_positions
            })
    
    return diffs

def recover_fat_from_copy(drive_letter, boot_sector, output_path=None):
    """Recover a damaged FAT by using another FAT copy"""
    fat_copies = find_fat_copies(drive_letter, boot_sector)
    
    if len(fat_copies) < 2:
        print("Not enough FAT copies found for recovery!")
        return None
    
    diffs = compare_fat_copies(fat_copies)
    
    if not diffs:
        print("All FAT copies are identical - no recovery needed!")
        return fat_copies[0]['data']
    
    print("Differences found between FAT copies:")
    for diff in diffs:
        if isinstance(diff, str):
            print(f"- {diff}")
        else:
            print(f"- FAT {diff['fat_index']} has {diff['diff_count']} differences")
            for example in diff['examples']:
                print(f"  * {example}")
    
    # Find most consistent FAT
    if len(fat_copies) > 2:
        print("Finding most consistent FAT copy...")
        # TODO: Add algorithm to determine most consistent FAT
    
    print(f"Using FAT copy #1 as recovery source")
    
    # Save to output file if requested
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(fat_copies[0]['data'])
        print(f"Saved recovered FAT to {output_path}")
    
    return fat_copies[0]['data']

def reconstruct_fat_by_scanning(drive_letter, boot_sector, output_path=None):
    """Reconstruct FAT by scanning disk clusters for file signatures"""
    bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
    sectors_per_cluster = boot_sector[13]
    reserved_sectors = struct.unpack('<H', boot_sector[14:16])[0]
    root_entries = struct.unpack('<H', boot_sector[17:19])[0]
    sectors_per_fat = struct.unpack('<H', boot_sector[22:24])[0]
    num_fats = boot_sector[16]
    
    # Calculate data region start
    root_dir_sectors = ((root_entries * 32) + (bytes_per_sector - 1)) // bytes_per_sector
    data_start_sector = reserved_sectors + (num_fats * sectors_per_fat) + root_dir_sectors
    
    print(f"Scanning clusters starting from sector {data_start_sector}...")
    
    # TODO: Implement actual cluster scanning algorithm
    # This would be quite complex and require carving techniques
    
    print("Full FAT reconstruction by scanning not implemented in this demo")
    print("This would require advanced carving techniques")
    
    return None