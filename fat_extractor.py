import struct
from fat_reader import read_volume_sectors, read_fat_entry

def extract_file_from_volume(drive_letter, target_file, output_path):
    """Extract a specific file from the volume to output_path"""
    try:
        # First read the boot sector
        boot_sector = read_volume_sectors(drive_letter, 0, 1)
        
        # Extract necessary information to locate the file
        bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
        sectors_per_cluster = boot_sector[13]
        reserved_sectors = struct.unpack('<H', boot_sector[14:16])[0]
        num_fats = boot_sector[16]
        root_entries = struct.unpack('<H', boot_sector[17:19])[0]
        sectors_per_fat = struct.unpack('<H', boot_sector[22:24])[0]
        
        # Calculate positions
        fat_start_sector = reserved_sectors
        root_dir_start_sector = fat_start_sector + (num_fats * sectors_per_fat)
        data_region_start_sector = root_dir_start_sector + ((root_entries * 32) // bytes_per_sector)
        
        # Determine FAT type
        total_sectors_small = struct.unpack('<H', boot_sector[19:21])[0]
        if total_sectors_small == 0:
            total_sectors = struct.unpack('<I', boot_sector[32:36])[0]
        else:
            total_sectors = total_sectors_small
            
        data_sectors = total_sectors - reserved_sectors - (num_fats * sectors_per_fat) - ((root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector)
        total_clusters = data_sectors // sectors_per_cluster
        
        if total_clusters < 4085:
            fat_type = "FAT12"
        else:
            fat_type = "FAT16"
            
        # Read the FAT
        fat_data = read_volume_sectors(drive_letter, fat_start_sector, sectors_per_fat, bytes_per_sector)
        
        # Read the root directory
        root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector
        root_dir_data = read_volume_sectors(drive_letter, root_dir_start_sector, root_dir_sectors, bytes_per_sector)
        
        # Find the target file in the root directory
        target_name = target_file
        target_ext = ""
        
        if "." in target_file:
            parts = target_file.split(".")
            target_name = parts[0]
            target_ext = parts[1]
            
        # Pad or truncate to 8.3 format
        target_name = target_name.upper().ljust(8)[:8]
        target_ext = target_ext.upper().ljust(3)[:3]
        
        found_entry = None
        
        for i in range(root_entries):
            entry_offset = i * 32
            if entry_offset >= len(root_dir_data):
                break
                
            entry = root_dir_data[entry_offset:entry_offset+32]
            
            # Skip empty entries and deleted files
            if entry[0] == 0x00 or entry[0] == 0xE5:
                continue
                
            # Extract file name and extension
            name = entry[0:8].decode('ascii', errors='replace').strip()
            extension = entry[8:11].decode('ascii', errors='replace').strip()
            
            # Pad to match the 8.3 format for comparison
            name_padded = name.ljust(8)
            ext_padded = extension.ljust(3)
            
            if name_padded.upper() == target_name and ext_padded.upper() == target_ext:
                found_entry = entry
                break
                
        if found_entry is None:
            print(f"File '{target_file}' not found in the root directory")
            return False
            
        # Get file information
        start_cluster_high = struct.unpack('<H', found_entry[20:22])[0]
        start_cluster_low = struct.unpack('<H', found_entry[26:28])[0]
        start_cluster = (start_cluster_high << 16) + start_cluster_low
        file_size = struct.unpack('<I', found_entry[28:32])[0]
        
        if start_cluster == 0:
            print(f"File '{target_file}' has no data clusters (empty file)")
            # Create an empty file
            with open(output_path, 'wb') as f:
                pass
            return True
                
        # Follow cluster chain
        cluster_chain = []
        current_cluster = start_cluster
        
        # Different end markers depending on FAT type
        if fat_type == "FAT12":
            end_marker = 0xFF8
        else:  # FAT16
            end_marker = 0xFFF8
            
        # Follow the chain until we hit an end marker
        while current_cluster < end_marker:
            cluster_chain.append(current_cluster)
            current_cluster = read_fat_entry(fat_data, current_cluster, fat_type)
            
            # Sanity check to avoid infinite loops
            if current_cluster == 0 or len(cluster_chain) > 100000:
                break
                
        print(f"File '{target_file}' found with {len(cluster_chain)} clusters, size: {file_size} bytes")
        
        # Extract the file content
        with open(output_path, 'wb') as out_file:
            bytes_per_cluster = bytes_per_sector * sectors_per_cluster
            bytes_written = 0
            
            for cluster in cluster_chain:
                # Calculate the offset of the cluster
                cluster_offset_sector = data_region_start_sector + ((cluster - 2) * sectors_per_cluster)
                
                # Read the cluster data
                cluster_data = read_volume_sectors(drive_letter, cluster_offset_sector, 
                                                sectors_per_cluster, bytes_per_sector)
                
                # Determine how much to write from this cluster
                remaining = file_size - bytes_written
                to_write = min(len(cluster_data), remaining)
                
                # Write the data
                out_file.write(cluster_data[:to_write])
                bytes_written += to_write
                
                # Stop if we've written the entire file
                if bytes_written >= file_size:
                    break
                    
        print(f"File extracted to '{output_path}'")
        return True
        
    except Exception as e:
        print(f"Error extracting file: {e}")
        return False