import struct
from fat.reader import read_volume_sectors
from fat.utils import format_time, format_date, identify_file_type, get_attribute_details
from fat.directory import analyze_directory_structure

def analyze_fat_volume(drive_letter):
    """Analyze a FAT volume from a mounted drive"""
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
        
        # Calculate volume size in bytes
        volume_size = total_sectors * bytes_per_sector
        
        # Determine FAT type (FAT12/FAT16)
        data_sectors = total_sectors - reserved_sectors - (num_fats * sectors_per_fat) - ((root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector)
        total_clusters = data_sectors // sectors_per_cluster
        
        if total_clusters < 4085:
            fat_type = "FAT12"
        else:
            fat_type = "FAT16"  # Actually, could be FAT32 if > 65525, but we simplify
            
        # Calculate important offsets
        boot_sector_start = 0
        fat_start = reserved_sectors * bytes_per_sector
        root_dir_start = fat_start + (num_fats * sectors_per_fat * bytes_per_sector)
        data_region_start = root_dir_start + (root_entries * 32)
        
        fat_start_sector = reserved_sectors
        root_dir_start_sector = fat_start_sector + (num_fats * sectors_per_fat)
        data_region_start_sector = root_dir_start_sector + ((root_entries * 32) // bytes_per_sector)
        
        # Print boot sector information
        print("=== BOOT SECTOR INFORMATION ===")
        print(f"Bytes per sector: {bytes_per_sector}")
        print(f"Sectors per cluster: {sectors_per_cluster}")
        print(f"Reserved sectors (before FAT): {reserved_sectors}")
        print(f"Number of FAT tables: {num_fats}")
        print(f"Number of RDET entries: {root_entries}")
        print(f"Total sectors: {total_sectors}")
        print(f"Sectors per FAT: {sectors_per_fat}")
        print(f"Volume size: {volume_size} bytes ({volume_size / (1024*1024):.2f} MB)")
        print(f"FAT type: {fat_type}")
        print("\n=== LOCATIONS ===")
        print(f"Boot sector starts at: sector {boot_sector_start} (offset 0x{boot_sector_start * bytes_per_sector:X})")
        print(f"FAT region starts at: sector {fat_start_sector} (offset 0x{fat_start:X})")
        print(f"Root directory starts at: sector {root_dir_start_sector} (offset 0x{root_dir_start:X})")
        print(f"Data region starts at: sector {data_region_start_sector} (offset 0x{data_region_start:X})")
        
        # Read and parse root directory entries
        # Calculate number of sectors for the root directory
        root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector
        root_dir_data = read_volume_sectors(drive_letter, root_dir_start_sector, root_dir_sectors, bytes_per_sector)
        
        print("\n=== ROOT DIRECTORY ENTRIES ===")
        
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
            full_name = name
            if extension:
                full_name = f"{name}.{extension}"
            
            # Attributes byte
            attr = entry[11]
            is_directory = bool(attr & 0x10)
            is_volume_label = bool(attr & 0x08)
            is_system = bool(attr & 0x04)
            is_hidden = bool(attr & 0x02)
            is_readonly = bool(attr & 0x01)
            
            if is_volume_label:
                continue  # Skip volume labels
                
            # Get timestamps
            creation_time = struct.unpack('<H', entry[14:16])[0]
            creation_date = struct.unpack('<H', entry[16:18])[0]
            last_access_date = struct.unpack('<H', entry[18:20])[0]
            last_mod_time = struct.unpack('<H', entry[22:24])[0]
            last_mod_date = struct.unpack('<H', entry[24:26])[0]
            
            # Starting cluster
            start_cluster_high = struct.unpack('<H', entry[20:22])[0]
            start_cluster_low = struct.unpack('<H', entry[26:28])[0]
            start_cluster = (start_cluster_high << 16) + start_cluster_low
            
            # File size
            file_size = struct.unpack('<I', entry[28:32])[0]
            
            # Tính toán vị trí sector bắt đầu của file/thư mục
            if start_cluster > 0:
                start_sector = data_region_start_sector + ((start_cluster - 2) * sectors_per_cluster)
            else:
                start_sector = 0  # Với file trống, không có sector dữ liệu
            
            # Phân tích chi tiết thuộc tính
            file_type = identify_file_type(extension, is_directory, is_volume_label)
            attr_details = get_attribute_details(attr)

            # Print entry information
            print(f"\nEntry {i+1}:")
            print(f"  Name: {name}")
            print(f"  Extension: {extension}")
            print(f"  Full name: {full_name}")
            print(f"  Attributes: {'R' if is_readonly else '-'}{'H' if is_hidden else '-'}" +
                  f"{'S' if is_system else '-'}{'D' if is_directory else '-'}")
            print(f"  Creation time: {format_time(creation_time)} on {format_date(creation_date)}")
            print(f"  Last access date: {format_date(last_access_date)}")
            print(f"  Last modification: {format_time(last_mod_time)} on {format_date(last_mod_date)}")
            print(f"  Starting cluster - high word: 0x{start_cluster_high:04X}")
            print(f"  Starting cluster - low word: 0x{start_cluster_low:04X}")
            print(f"  Starting cluster: {start_cluster}")
            print(f"  Starting sector: {start_sector} (0x{start_sector:X})")
            print(f"  File type: {file_type}")
            print(f"  Attribute details: {', '.join(attr_details) if attr_details else 'Normal file'}")
            print(f"  File size: {file_size} bytes")
            
        # Add directory tree analysis
        print("\n=== DIRECTORY TREE STRUCTURE ===")
        directory_tree = analyze_directory_structure(drive_letter)
        
    except Exception as e:
        print(f"Error: {e}")
        return False
        
    return True