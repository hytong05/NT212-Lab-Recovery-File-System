import struct
from fat.reader import read_volume_sectors, read_fat_entry
from fat.utils import format_time, format_date

def read_cluster_chain(drive_letter, start_cluster, fat_data, fat_type, 
                       data_region_start_sector, sectors_per_cluster, bytes_per_sector):
    """Read all clusters in a cluster chain"""
    if start_cluster <= 0:
        return bytearray()
    
    # Different end markers depending on FAT type
    if fat_type == "FAT12":
        end_marker = 0xFF8
    else:  # FAT16
        end_marker = 0xFFF8
    
    # Follow the chain until we hit an end marker
    all_data = bytearray()
    current_cluster = start_cluster
    
    while current_cluster < end_marker:
        # Calculate the offset of the cluster
        cluster_offset_sector = data_region_start_sector + ((current_cluster - 2) * sectors_per_cluster)
        
        # Read the cluster data
        cluster_data = read_volume_sectors(drive_letter, cluster_offset_sector, 
                                        sectors_per_cluster, bytes_per_sector)
        
        # Add to the accumulated data
        all_data.extend(cluster_data)
        
        # Move to next cluster in chain
        current_cluster = read_fat_entry(fat_data, current_cluster, fat_type)
        
        # Sanity check to avoid infinite loops
        if current_cluster == 0 or len(all_data) > 10 * 1024 * 1024:  # 10MB limit for safety
            break
    
    return all_data

def parse_directory_entries(directory_data):
    """Parse a directory data into entry objects with LFN support"""
    entries = []
    current_lfn = ""
    
    i = 0
    while i < len(directory_data):
        if i + 32 > len(directory_data):
            break
            
        entry = directory_data[i:i+32]
        i += 32  # Move to next entry
        
        # Skip empty entries
        if entry[0] == 0x00:
            continue  # End of directory
            
        # Check if it's a deleted entry
        is_deleted = entry[0] == 0xE5
        if is_deleted:
            current_lfn = ""  # Reset LFN for deleted files
            continue
            
        # Check attributes
        attr = entry[11]
        
        # Check for LFN entries (Long File Name)
        if attr == 0x0F:
            if not is_deleted:
                # This is an LFN entry, extract the name part
                lfn_part = ""
                # First 5 characters (10 bytes)
                for j in range(1, 11, 2):
                    if entry[j] != 0 and entry[j] != 0xFF:  # Skip null and 0xFF bytes
                        lfn_part += chr(entry[j])
                # Next 6 characters (12 bytes)
                for j in range(14, 26, 2):
                    if entry[j] != 0 and entry[j] != 0xFF:  # Skip null and 0xFF bytes
                        lfn_part += chr(entry[j])
                # Last 2 characters (4 bytes)
                for j in range(28, 32, 2):
                    if entry[j] != 0 and entry[j] != 0xFF:  # Skip null and 0xFF bytes
                        lfn_part += chr(entry[j])
                
                # Check if this is the first part of the LFN
                sequence_number = entry[0] & 0x1F
                is_last = entry[0] & 0x40
                
                if is_last:
                    current_lfn = lfn_part
                else:
                    current_lfn = lfn_part + current_lfn
            continue
            
        # This is a regular entry
        # Extract file name and extension (8.3 format) - CLEAN properly
        name_bytes = entry[0:8]
        ext_bytes = entry[8:11]
        
        # Clean name bytes - remove 0xFF and any non-printable ASCII
        short_name = ""
        for b in name_bytes:
            if b != 0xFF and b >= 0x20 and b < 0x7F:
                short_name += chr(b)
        short_name = short_name.strip()
        
        # Clean extension bytes
        short_ext = ""
        for b in ext_bytes:
            if b != 0xFF and b >= 0x20 and b < 0x7F:
                short_ext += chr(b)
        short_ext = short_ext.strip()
        
        # Create the 8.3 format name
        if short_ext:
            short_full_name = f"{short_name}.{short_ext}"
        else:
            short_full_name = short_name
            
        # If we have a LFN, use it; otherwise use the short name
        full_name = current_lfn if current_lfn else short_full_name
        
        # Ensure full_name is clean as well
        full_name = ''.join(c for c in full_name if ord(c) != 0xFF and (ord(c) >= 0x20 or ord(c) == 0x09))
        
        # Clear current LFN for next entry
        current_lfn = ""
        
        # Special handling for . and .. directory entries
        if short_name == "." or short_name == "..":
            full_name = short_name
        
        # Attributes byte parsing
        is_directory = bool(attr & 0x10)
        is_volume_label = bool(attr & 0x08)
        
        # Skip volume labels
        if is_volume_label:
            continue
            
        # Get timestamps
        creation_time = struct.unpack('<H', entry[14:16])[0]
        creation_date = struct.unpack('<H', entry[16:18])[0]
        
        # Starting cluster
        start_cluster_high = struct.unpack('<H', entry[20:22])[0] 
        start_cluster_low = struct.unpack('<H', entry[26:28])[0]
        start_cluster = (start_cluster_high << 16) + start_cluster_low
        
        # File size
        file_size = struct.unpack('<I', entry[28:32])[0]
        
        entries.append({
            'name': short_name,
            'extension': short_ext,
            'short_name': short_full_name,
            'full_name': full_name,
            'is_directory': is_directory,
            'start_cluster': start_cluster,
            'file_size': file_size,
            'creation_time': format_time(creation_time),
            'creation_date': format_date(creation_date),
            'attr': attr
        })
    
    return entries

def build_directory_tree(drive_letter, start_cluster, fat_data, fat_type, 
                         data_region_start_sector, sectors_per_cluster, bytes_per_sector):
    """Recursively build a directory tree structure starting from a specific cluster"""
    # Skip special directories . and ..
    if start_cluster <= 0:
        return {}
    
    # Read the directory data
    dir_data = read_cluster_chain(drive_letter, start_cluster, fat_data, fat_type,
                                 data_region_start_sector, sectors_per_cluster, bytes_per_sector)
    
    # Parse directory entries
    entries = parse_directory_entries(dir_data)
    
    tree = {}
    
    # Process each entry
    for entry in entries:
        name = entry['full_name']
        
        # Skip . and .. directory entries
        if name == "." or name == "..":
            continue
        
        if entry['is_directory']:
            # Recursively process subdirectory
            subtree = build_directory_tree(drive_letter, entry['start_cluster'], fat_data, fat_type,
                                         data_region_start_sector, sectors_per_cluster, bytes_per_sector)
            tree[name] = subtree
        else:
            # Add file with its size
            tree[name] = entry['file_size']
    
    return tree

def analyze_directory_structure(drive_letter):
    """Analyze the directory structure of a FAT volume"""
    try:
        # First read the boot sector
        boot_sector = read_volume_sectors(drive_letter, 0, 1)
        
        # Extract boot sector information
        bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
        sectors_per_cluster = boot_sector[13]
        reserved_sectors = struct.unpack('<H', boot_sector[14:16])[0]
        num_fats = boot_sector[16]
        root_entries = struct.unpack('<H', boot_sector[17:19])[0]
        total_sectors_small = struct.unpack('<H', boot_sector[19:21])[0]
        
        # If total_sectors_small is 0, use the large sectors field
        if total_sectors_small == 0:
            total_sectors = struct.unpack('<I', boot_sector[32:36])[0]
        else:
            total_sectors = total_sectors_small
            
        sectors_per_fat = struct.unpack('<H', boot_sector[22:24])[0]
        
        # Calculate important offsets
        fat_start_sector = reserved_sectors
        root_dir_start_sector = fat_start_sector + (num_fats * sectors_per_fat)
        
        # Number of sectors occupied by the root directory
        root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector
        data_region_start_sector = root_dir_start_sector + root_dir_sectors
        
        # Determine FAT type
        data_sectors = total_sectors - reserved_sectors - (num_fats * sectors_per_fat) - root_dir_sectors
        total_clusters = data_sectors // sectors_per_cluster
        
        if total_clusters < 4085:
            fat_type = "FAT12"
        else:
            fat_type = "FAT16"
            
        # Read the FAT
        fat_data = read_volume_sectors(drive_letter, fat_start_sector, sectors_per_fat, bytes_per_sector)
        
        # For FAT12/16, the root directory is not part of the data area and has a fixed size
        root_dir_data = read_volume_sectors(drive_letter, root_dir_start_sector, root_dir_sectors, bytes_per_sector)
        
        # Parse root directory entries
        root_entries_list = parse_directory_entries(root_dir_data)
        
        # Build the root of our tree
        dir_tree = {}
        
        # Process all entries in the root directory
        for entry in root_entries_list:
            name = entry['full_name']
            
            if entry['is_directory']:
                # Recursively process subdirectory
                subtree = build_directory_tree(drive_letter, entry['start_cluster'], fat_data, fat_type,
                                             data_region_start_sector, sectors_per_cluster, bytes_per_sector)
                dir_tree[name] = subtree
            else:
                # Add file with its size
                dir_tree[name] = entry['file_size']
                
        return dir_tree
        
    except Exception as e:
        print(f"Error analyzing directory structure: {e}")
        return {}