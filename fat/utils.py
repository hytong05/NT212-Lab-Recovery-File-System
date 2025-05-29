import struct
import os

def extract_fat_info(boot_sector):
    """
    Trích xuất thông tin cơ bản từ boot sector của FAT
    
    Args:
        boot_sector: Dữ liệu raw của boot sector (512 bytes)
        
    Returns:
        Dictionary chứa các thông số cơ bản của hệ thống file FAT
    """
    if not isinstance(boot_sector, (bytes, bytearray)):
        raise TypeError("Boot sector phải là bytes hoặc bytearray")
        
    if len(boot_sector) < 512:
        raise ValueError(f"Boot sector không đủ dữ liệu: {len(boot_sector)} bytes")
        
    if boot_sector[510:512] != b'\x55\xAA':
        raise ValueError("Boot sector không có chữ ký hợp lệ")
    
    # Trích xuất thông tin từ boot sector
    bytes_per_sector = struct.unpack("<H", boot_sector[11:13])[0]
    sectors_per_cluster = boot_sector[13]
    reserved_sectors = struct.unpack("<H", boot_sector[14:16])[0]
    num_fats = boot_sector[16]
    root_entries = struct.unpack("<H", boot_sector[17:19])[0]
    total_sectors_small = struct.unpack("<H", boot_sector[19:21])[0]
    media_descriptor = boot_sector[21]
    sectors_per_fat = struct.unpack("<H", boot_sector[22:24])[0]
    sectors_per_track = struct.unpack("<H", boot_sector[24:26])[0]
    num_heads = struct.unpack("<H", boot_sector[26:28])[0]
    hidden_sectors = struct.unpack("<I", boot_sector[28:32])[0]
    total_sectors_large = struct.unpack("<I", boot_sector[32:36])[0]
    
    # Xác định tổng số sector
    total_sectors = total_sectors_large if total_sectors_small == 0 else total_sectors_small
    
    # Xác định loại FAT
    if total_sectors < 4085:
        fat_type = 12  # FAT12
    elif total_sectors < 65525:
        fat_type = 16  # FAT16
    else:
        fat_type = 32  # FAT32
    
    # Tính các thông số quan trọng
    root_dir_sectors = ((root_entries * 32) + (bytes_per_sector - 1)) // bytes_per_sector
    first_data_sector = reserved_sectors + (num_fats * sectors_per_fat) + root_dir_sectors
    data_sectors = total_sectors - first_data_sector
    total_clusters = data_sectors // sectors_per_cluster
    
    # Lưu trữ các thông số đã trích xuất
    return {
        "bytes_per_sector": bytes_per_sector,
        "sectors_per_cluster": sectors_per_cluster,
        "reserved_sectors": reserved_sectors,
        "num_fats": num_fats,
        "root_entries": root_entries,
        "total_sectors": total_sectors,
        "sectors_per_fat": sectors_per_fat,
        "fat_type": fat_type,
        "first_data_sector": first_data_sector,
        "total_clusters": total_clusters,
        "root_dir_sectors": root_dir_sectors,
        "media_descriptor": media_descriptor
    }

def format_time(time_value):
    """Format FAT time value into human-readable string
    FAT time: Bits 0-4=seconds/2, Bits 5-10=minutes, Bits 11-15=hours"""
    hours = (time_value >> 11) & 0x1F
    minutes = (time_value >> 5) & 0x3F
    seconds = (time_value & 0x1F) * 2
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_date(date_value):
    """Format FAT date value into human-readable string
    FAT date: Bits 0-4=day, Bits 5-8=month, Bits 9-15=year+1980"""
    year = ((date_value >> 9) & 0x7F) + 1980
    month = (date_value >> 5) & 0x0F
    day = date_value & 0x1F
    return f"{year}-{month:02d}-{day:02d}"

def identify_file_type(extension, is_directory, is_volume_label):
    """Identify the file type based on extension and attributes"""
    if is_directory:
        return "Directory"
    elif is_volume_label:
        return "Volume Label"
    else:
        # Phân tích extension để xác định loại file
        if extension.upper() in ["TXT", "LOG", "INI", "CFG"]:
            return "Text file"
        elif extension.upper() in ["EXE", "COM", "SYS"]:
            return "Executable"
        elif extension.upper() in ["DLL", "DRV"]:
            return "System library"
        elif extension.upper() in ["DOC", "XLS", "PPT"]:
            return "Office document"
        elif extension.upper() in ["JPG", "GIF", "BMP", "PNG"]:
            return "Image file"
        else:
            return f"Data file (.{extension})"

def get_attribute_details(attr):
    """Get detailed attribute descriptions"""
    attr_details = []
    if attr & 0x01:
        attr_details.append("Read-only file")
    if attr & 0x02:
        attr_details.append("Hidden file")
    if attr & 0x04:
        attr_details.append("System file")
    if attr & 0x10:
        attr_details.append("Directory")
    if attr & 0x20:
        attr_details.append("Archive (modified since last backup)")
    if attr & 0x08:
        attr_details.append("Volume label")
    return attr_details

def print_directory_tree(tree, level=0, prefix=''):
    """Print a directory tree structure with proper indentation
    Args:
        tree: Dictionary containing directory structure
        level: Current level in the tree (for indentation)
        prefix: Prefix string for better visualization
    """
    # Sort items to show directories first, then files
    try:
        sorted_items = sorted(tree.items(), key=lambda x: (0 if isinstance(x[1], dict) else 1, x[0].lower()))
    except:
        # Fallback if there are strange characters that can't be sorted
        sorted_items = sorted(tree.items(), key=lambda x: (0 if isinstance(x[1], dict) else 1))
    
    count = len(sorted_items)
    for i, (name, content) in enumerate(sorted_items):
        # Ensure name is clean (no 0xFF characters)
        clean_name = ''.join(c for c in name if ord(c) != 0xFF)
        
        # Determine if this is the last item at this level
        is_last = i == count - 1
        
        # Choose the appropriate prefix characters
        if level == 0:
            # Root level
            print(f"{clean_name}")
            new_prefix = '    '
        else:
            # Non-root level
            if is_last:
                print(f"{prefix}└── {clean_name}")
                new_prefix = prefix + '    '
            else:
                print(f"{prefix}├── {clean_name}")
                new_prefix = prefix + '│   '
        
        # Recursively print subdirectories
        if isinstance(content, dict):
            print_directory_tree(content, level + 1, new_prefix)

def apply_boot_sector(drive_letter, boot_file):
    """Áp dụng boot sector đã khôi phục vào ổ đĩa thật"""
    try:
        import os
        if not boot_file or not isinstance(boot_file, str):
            raise ValueError(f"Tham số boot_file không hợp lệ: {boot_file}")
            
        if not os.path.exists(boot_file):
            raise FileNotFoundError(f"Không tìm thấy file boot sector: {boot_file}")
        
        # Đọc boot sector đã khôi phục
        with open(boot_file, 'rb') as f:
            boot_data = f.read(512)
        
        # Sử dụng Windows API để có quyền ghi cao hơn
        try:
            import win32file
            
            drive_path = f"\\\\.\\{drive_letter}:"
            hfile = win32file.CreateFile(
                drive_path, 
                win32file.GENERIC_WRITE, 
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None, 
                win32file.OPEN_EXISTING, 
                0, 
                None
            )
            
            try:
                # Ghi boot sector
                win32file.WriteFile(hfile, boot_data)
                win32file.FlushFileBuffers(hfile)
                print(f"Boot sector đã được ghi vào ổ đĩa {drive_letter}")
                return True
            finally:
                win32file.CloseHandle(hfile)
                
        except ImportError:
            # Nếu không có win32file, sử dụng phương pháp thông thường
            from fat.reader import open_volume
            with open_volume(drive_letter, 'r+b') as volume:  # Mở trong chế độ đọc và ghi
                volume.seek(0)  # Vị trí boot sector
                volume.write(boot_data)
                volume.flush()
                print(f"Boot sector đã được ghi vào ổ đĩa {drive_letter}")
                return True
            
    except Exception as e:
        print(f"Lỗi khi ghi boot sector: {str(e)}")
        return False