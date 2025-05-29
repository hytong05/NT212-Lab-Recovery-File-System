import struct
from fat.reader import read_volume_sectors, open_volume
from fat.utils import format_time, format_date, identify_file_type, get_attribute_details, extract_fat_info
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

def check_filesystem_integrity(drive_letter, boot_sector):
    """
    Kiểm tra tính toàn vẹn của hệ thống file FAT và trả về danh sách vấn đề
    """
    issues = []
    
    # Kiểm tra kiểu dữ liệu boot sector
    if not isinstance(boot_sector, (bytes, bytearray)) or len(boot_sector) < 512:
        issues.append("Boot sector không đủ dữ liệu hoặc kiểu dữ liệu không hợp lệ")
        return issues
    
    # Kiểm tra chữ ký boot sector
    if boot_sector[510:512] != b'\x55\xAA':
        issues.append("Boot sector không có chữ ký hợp lệ (0x55AA)")
    
    # Tiếp tục phân tích nếu có chữ ký hợp lệ
    try:
        bs_info = extract_fat_info(boot_sector)
    except Exception as e:
        issues.append(f"Lỗi khi phân tích boot sector: {str(e)}")
        return issues
    
    # Kiểm tra các thông số boot sector hợp lý
    if bs_info['bytes_per_sector'] not in [512, 1024, 2048, 4096]:
        issues.append(f"Giá trị bytes per sector bất thường: {bs_info['bytes_per_sector']}")
    
    if bs_info['sectors_per_cluster'] not in [1, 2, 4, 8, 16, 32, 64, 128]:
        issues.append(f"Giá trị sectors per cluster bất thường: {bs_info['sectors_per_cluster']}")
    
    if bs_info['num_fats'] not in [1, 2]:
        issues.append(f"Số lượng bảng FAT bất thường: {bs_info['num_fats']}")
    
    # Kiểm tra tính nhất quán của các bảng FAT nếu có nhiều bảng
    if bs_info['num_fats'] > 1:
        fat1_start = bs_info['reserved_sectors'] * bs_info['bytes_per_sector']
        fat_size = bs_info['sectors_per_fat'] * bs_info['bytes_per_sector']
        
        with open_volume(drive_letter) as volume:
            volume.seek(fat1_start)
            fat1_data = volume.read(fat_size)
            
            volume.seek(fat1_start + fat_size)
            fat2_data = volume.read(fat_size)
            
            if fat1_data != fat2_data:
                issues.append("Các bảng FAT không đồng nhất - có thể bị hỏng")
    
    # Kiểm tra các entry trong thư mục gốc
    root_dir_start = bs_info['reserved_sectors'] * bs_info['bytes_per_sector'] + (bs_info['num_fats'] * bs_info['sectors_per_fat'] * bs_info['bytes_per_sector'])
    root_dir_size = bs_info['root_entries'] * 32
    
    with open_volume(drive_letter) as volume:
        volume.seek(root_dir_start)
        root_data = volume.read(root_dir_size)
        
        valid_entries = 0
        invalid_entries = 0
        
        for i in range(0, len(root_data), 32):
            entry = root_data[i:i+32]
            first_byte = entry[0]
            
            if first_byte == 0x00:  # End of directory
                continue
            elif first_byte == 0xE5:  # Deleted entry
                continue
            
            # Kiểm tra thuộc tính hợp lệ
            attr = entry[11]
            if attr not in [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x01 | 0x02, 0x01 | 0x10, 0x02 | 0x10, 0x01 | 0x02 | 0x10]:
                invalid_entries += 1
            else:
                valid_entries += 1
                
                # Kiểm tra tên tập tin hợp lệ
                name = entry[0:8].replace(b' ', b'')
                ext = entry[8:11].replace(b' ', b'')
                
                for c in name:
                    if not (0x20 <= c <= 0x7E or c == 0x05):
                        invalid_entries += 1
                        valid_entries -= 1
                        break
        
        if valid_entries == 0 and invalid_entries > 0:
            issues.append("Không tìm thấy entry hợp lệ trong thư mục gốc")
        elif invalid_entries > valid_entries:
            issues.append(f"Nhiều entry không hợp lệ trong thư mục gốc ({invalid_entries}/{invalid_entries+valid_entries})")
    
    # Kiểm tra các giá trị bất thường trong bảng FAT
    fat_start = bs_info['reserved_sectors'] * bs_info['bytes_per_sector']
    fat_size = bs_info['sectors_per_fat'] * bs_info['bytes_per_sector']
    
    with open_volume(drive_letter) as volume:
        volume.seek(fat_start)
        fat_data = volume.read(fat_size)
        
        # FAT16: Mỗi entry = 2 bytes
        if bs_info['fat_type'] == 16:
            # FAT entry đầu tiên phải là 0xFF8 hoặc 0xFFF8
            first_entry = struct.unpack("<H", fat_data[0:2])[0]
            if first_entry not in [0xFF8, 0xFFF8]:
                issues.append(f"Entry đầu tiên trong bảng FAT không hợp lệ: 0x{first_entry:X}")
    
    # Kiểm tra kích thước ổ đĩa
    total_size = bs_info['total_sectors'] * bs_info['bytes_per_sector']
    try:
        actual_size = get_disk_size(drive_letter)
        if abs(total_size - actual_size) > bs_info['bytes_per_sector'] * 10:
            issues.append(f"Kích thước tính toán từ boot sector ({total_size} bytes) khác nhiều so với kích thước thực ({actual_size} bytes)")
    except:
        pass
    
    return issues