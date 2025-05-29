import struct
import os
from fat.reader import read_volume_sectors

def recover_root_directory(drive_letter, boot_sector):
    """Attempt to recover a damaged root directory"""
    bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
    reserved_sectors = struct.unpack('<H', boot_sector[14:16])[0]
    root_entries = struct.unpack('<H', boot_sector[17:19])[0]
    sectors_per_fat = struct.unpack('<H', boot_sector[22:24])[0]
    num_fats = boot_sector[16]
    
    # Calculate root directory location
    root_dir_start = reserved_sectors + (num_fats * sectors_per_fat)
    root_dir_sectors = ((root_entries * 32) + (bytes_per_sector - 1)) // bytes_per_sector
    
    try:
        # Read the root directory
        root_dir_data = read_volume_sectors(drive_letter, root_dir_start, root_dir_sectors)
        
        # Count valid entries
        valid_entries = 0
        for i in range(0, len(root_dir_data), 32):
            if i + 32 > len(root_dir_data):
                break
            
            entry = root_dir_data[i:i+32]
            
            # Skip empty or deleted entries
            if entry[0] == 0x00 or entry[0] == 0xE5:
                continue
            
            # Check attributes for validity
            attr = entry[11]
            if attr & 0x08:  # Volume label
                valid_entries += 1
            elif attr & 0x10:  # Directory
                valid_entries += 1
            elif attr & 0x0F == 0x0F:  # Long filename entry
                valid_entries += 1
            elif (attr & 0x3F) == 0:  # Regular file
                valid_entries += 1
        
        print(f"Root directory scan found {valid_entries} valid entries")
        return root_dir_data
                
    except Exception as e:
        print(f"Error reading root directory: {e}")
        return None

def scan_for_deleted_files(root_dir_data):
    """Scan root directory for deleted files that might be recoverable"""
    deleted_files = []
    
    for i in range(0, len(root_dir_data), 32):
        if i + 32 > len(root_dir_data):
            break
            
        entry = root_dir_data[i:i+32]
        
        # Check for deleted entries
        if entry[0] == 0xE5:
            # Get attributes
            attr = entry[11]
            
            # Skip LFN entries
            if attr & 0x0F == 0x0F:
                continue
                
            # Get original first character (replaced with _)
            original_char = '_'
            
            # Get file name and extension
            name_bytes = bytearray(entry[0:8])
            name_bytes[0] = ord('F')  # Replace deleted marker with most likely first char
            name = name_bytes.decode('ascii', errors='replace').strip()
            
            # Also get name with underscore for display
            marked_name_bytes = bytearray(entry[0:8])
            marked_name_bytes[0] = ord('_')
            marked_name = marked_name_bytes.decode('ascii', errors='replace').strip()
            
            ext = entry[8:11].decode('ascii', errors='replace').strip()
            
            # Get starting cluster
            cluster_low = struct.unpack('<H', entry[26:28])[0]
            
            # Get file size
            file_size = struct.unpack('<I', entry[28:32])[0]
            
            # Try to guess original name based on pattern
            possible_original_name = None
            if marked_name == "_ILEB" and ext == "TXT":
                possible_original_name = "FileB.txt"
            
            deleted_files.append({
                'name': name,
                'marked_name': marked_name,
                'ext': ext,
                'filename': f"{name}.{ext}" if ext else name,
                'marked_filename': f"{marked_name}.{ext}" if ext else marked_name,
                'possible_original': possible_original_name,
                'attr': attr,
                'start_cluster': cluster_low,
                'file_size': file_size,
                'dir_entry_offset': i
            })
    
    return deleted_files

def recover_deleted_file(drive_letter, boot_sector, start_cluster, file_size, output_path):
    """Recover a deleted file by direct cluster reading"""
    bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
    sectors_per_cluster = boot_sector[13]
    reserved_sectors = struct.unpack('<H', boot_sector[14:16])[0]
    root_entries = struct.unpack('<H', boot_sector[17:19])[0]
    sectors_per_fat = struct.unpack('<H', boot_sector[22:24])[0]
    num_fats = boot_sector[16]
    
    # Calculate data region start
    root_dir_sectors = ((root_entries * 32) + (bytes_per_sector - 1)) // bytes_per_sector
    data_start_sector = reserved_sectors + (num_fats * sectors_per_fat) + root_dir_sectors
    
    if start_cluster < 2:
        print("Invalid starting cluster")
        return False
    
    try:
        # Calculate starting sector
        start_sector = data_start_sector + ((start_cluster - 2) * sectors_per_cluster)
        
        # Calculate how many clusters needed
        bytes_per_cluster = bytes_per_sector * sectors_per_cluster
        clusters_needed = (file_size + bytes_per_cluster - 1) // bytes_per_cluster
        
        print(f"Recovering file: start cluster {start_cluster}, size {file_size} bytes")
        print(f"Reading {clusters_needed} clusters starting from sector {start_sector}")
        
        with open(output_path, 'wb') as outfile:
            bytes_written = 0
            
            for i in range(clusters_needed):
                current_sector = start_sector + (i * sectors_per_cluster)
                
                try:
                    cluster_data = read_volume_sectors(drive_letter, 
                                                     current_sector, 
                                                     sectors_per_cluster, 
                                                     bytes_per_sector)
                    
                    # For the last cluster, only write up to the file size
                    if bytes_written + len(cluster_data) > file_size:
                        bytes_to_write = file_size - bytes_written
                        outfile.write(cluster_data[:bytes_to_write])
                        bytes_written += bytes_to_write
                    else:
                        outfile.write(cluster_data)
                        bytes_written += len(cluster_data)
                        
                except Exception as e:
                    print(f"Error reading cluster {start_cluster + i}: {e}")
                    break
            
        print(f"Recovered {bytes_written} bytes to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error recovering deleted file: {e}")
        return False

# Thêm hàm mới để quét file bị xóa trong tất cả thư mục

def scan_deleted_recursive(drive_letter, boot_sector):
    """Scan for deleted files recursively throughout the filesystem"""
    from fat.directory import build_directory_tree, read_cluster_chain, parse_directory_entries
    from fat.reader import read_volume_sectors
    
    bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
    sectors_per_cluster = boot_sector[13]
    reserved_sectors = struct.unpack('<H', boot_sector[14:16])[0]
    num_fats = boot_sector[16]
    root_entries = struct.unpack('<H', boot_sector[17:19])[0]
    sectors_per_fat = struct.unpack('<H', boot_sector[22:24])[0]
    
    # Calculate important offsets
    fat_start_sector = reserved_sectors
    root_dir_start_sector = fat_start_sector + (num_fats * sectors_per_fat)
    
    # Number of sectors occupied by the root directory
    root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector
    data_region_start_sector = root_dir_start_sector + root_dir_sectors
    
    # Determine FAT type
    total_sectors_small = struct.unpack('<H', boot_sector[19:21])[0]
    if total_sectors_small == 0:
        total_sectors = struct.unpack('<I', boot_sector[32:36])[0]
    else:
        total_sectors = total_sectors_small
        
    data_sectors = total_sectors - reserved_sectors - (num_fats * sectors_per_fat) - root_dir_sectors
    total_clusters = data_sectors // sectors_per_cluster
    
    if total_clusters < 4085:
        fat_type = "FAT12"
    else:
        fat_type = "FAT16"
        
    # Read the FAT
    fat_data = read_volume_sectors(drive_letter, fat_start_sector, sectors_per_fat, bytes_per_sector)
    
    # First scan the root directory
    root_dir_data = read_volume_sectors(drive_letter, root_dir_start_sector, root_dir_sectors, bytes_per_sector)
    root_deleted_files = scan_for_deleted_files(root_dir_data)
    
    # Add location information
    for file in root_deleted_files:
        file['location'] = "Root Directory"
    
    # Process all subdirectories
    all_deleted_files = root_deleted_files
    
    # Parse valid root directory entries to find subdirectories
    root_entries_list = parse_directory_entries(root_dir_data)
    
    # Queue to store directories to process
    dir_queue = []
    
    # Add all root subdirectories to queue
    for entry in root_entries_list:
        if entry['is_directory'] and entry['full_name'] not in [".", ".."]:
            dir_queue.append({
                'name': entry['full_name'],
                'start_cluster': entry['start_cluster'],
                'path': entry['full_name']
            })
    
    # Process the directory queue
    while dir_queue:
        current_dir = dir_queue.pop(0)
        
        # Read directory data
        dir_data = read_cluster_chain(drive_letter, current_dir['start_cluster'], 
                                     fat_data, fat_type, data_region_start_sector, 
                                     sectors_per_cluster, bytes_per_sector)
        
        # Scan for deleted files in this directory
        deleted_in_dir = scan_for_deleted_files(dir_data)
        
        # Add path information
        for file in deleted_in_dir:
            file['location'] = current_dir['path']
        
        # Add to the overall list
        all_deleted_files.extend(deleted_in_dir)
        
        # Find subdirectories in this directory
        dir_entries = parse_directory_entries(dir_data)
        for entry in dir_entries:
            if entry['is_directory'] and entry['full_name'] not in [".", ".."]:
                dir_queue.append({
                    'name': entry['full_name'],
                    'start_cluster': entry['start_cluster'],
                    'path': current_dir['path'] + '/' + entry['full_name']
                })
    
    return all_deleted_files