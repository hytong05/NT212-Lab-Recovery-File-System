import struct
import os
from fat.reader import open_volume, read_volume_sectors
from fat.utils import extract_fat_info

def recover_boot_sector(drive_letter, output_path="recovered_boot.bin", fat_type=None):
    """
    Scan for potential boot sectors and save the most likely one
    
    Args:
        drive_letter: Chữ cái ổ đĩa (ví dụ: 'E')
        output_path: Đường dẫn để lưu boot sector đã khôi phục
        fat_type: Loại FAT do người dùng chỉ định (12, 16 hoặc 32)
    """
    print("Scanning for potential boot sectors...")
    candidates = []
    
    # Scan first few sectors for boot sector candidates
    with open_volume(drive_letter) as volume:
        for sector in range(10):  # Check first 10 sectors
            volume.seek(sector * 512)
            data = volume.read(512)
            
            # Check for boot sector signature
            if data[510:512] == b'\x55\xAA':
                # Extract basic info
                oem_name = data[3:11]
                bytes_per_sector = struct.unpack("<H", data[11:13])[0]
                sectors_per_cluster = data[13]
                
                if bytes_per_sector in [512, 1024, 2048, 4096] and sectors_per_cluster in [1, 2, 4, 8, 16, 32, 64, 128]:
                    candidate_fat_type = None
                    
                    # Thử xác định loại FAT từ dữ liệu boot sector
                    try:
                        info = extract_fat_info(data)
                        candidate_fat_type = info["fat_type"]
                    except:
                        pass
                        
                    candidates.append({
                        "sector": sector,
                        "data": data,
                        "oem_name": oem_name,
                        "bytes_per_sector": bytes_per_sector,
                        "sectors_per_cluster": sectors_per_cluster,
                        "fat_type": candidate_fat_type
                    })
    
    # If no candidates with standard boot signature, try advanced recovery
    if not candidates:
        return rebuild_boot_sector(drive_letter, output_path, fat_type)
    
    print(f"Found {len(candidates)} potential boot sector(s):\n")
    
    # Sắp xếp lại candidates nếu người dùng đã chỉ định loại FAT
    if fat_type is not None:
        # Ưu tiên các ứng viên có loại FAT phù hợp với yêu cầu của người dùng
        candidates.sort(key=lambda c: 0 if c["fat_type"] == fat_type else 1)
    
    # Hiển thị thông tin các ứng viên
    for i, candidate in enumerate(candidates):
        print(f"Candidate {i+1}:")
        print(f"  Sector: {candidate['sector']}")
        print(f"  OEM Name: {candidate['oem_name']}")
        print(f"  Bytes per sector: {candidate['bytes_per_sector']}")
        print(f"  Sectors per cluster: {candidate['sectors_per_cluster']}")
        if candidate['fat_type']:
            print(f"  FAT type: FAT{candidate['fat_type']}")
        print()
    
    # Sử dụng ứng viên đầu tiên (thường là tốt nhất nếu tìm thấy)
    with open(output_path, "wb") as f:
        f.write(candidates[0]["data"])
    
    print(f"Saved most likely boot sector to {output_path}")
    return candidates[0]["data"]

def rebuild_boot_sector(drive_letter, output_path="recovered_boot.bin", fat_type=None):
    """
    Advanced boot sector recovery by analyzing disk structures
    """
    print("Performing advanced boot sector recovery...")
    
    # Thử khôi phục từ một backup được lưu ở vị trí phổ biến
    with open_volume(drive_letter) as volume:
        # FAT thường có backup boot sector ở sector thứ 6
        for backup_sector in [6, 12]:
            try:
                volume.seek(backup_sector * 512)
                backup_data = volume.read(512)
                
                # Kiểm tra chữ ký hợp lệ
                if backup_data[510:512] == b'\x55\xAA':
                    # Kiểm tra các thông số hợp lệ
                    backup_bps = struct.unpack("<H", backup_data[11:13])[0]
                    backup_spc = backup_data[13]
                    
                    if backup_bps in [512, 1024, 2048, 4096] and backup_spc in [1, 2, 4, 8, 16, 32]:
                        print(f"Tìm thấy backup boot sector tại sector {backup_sector}!")
                        with open(output_path, "wb") as f:
                            f.write(backup_data)
                        print(f"Đã khôi phục boot sector từ bản backup")
                        return backup_data
            except:
                pass
    
    # Nếu không tìm thấy backup, tiếp tục với phân tích cấu trúc
    # Common FAT parameters to try
    bytes_per_sectors = [512, 1024, 2048, 4096]
    sectors_per_clusters = [1, 2, 4, 8, 16, 32]
    fat_types = [fat_type] if fat_type else [16, 12, 32]  # Ưu tiên loại FAT người dùng chỉ định
    
    best_config = None
    best_score = -1
    
    # Get disk size
    disk_size = get_disk_size(drive_letter)
    
    # Create a template boot sector based on typical FAT16 values
    template = bytearray(512)
    
    # Jump instruction and OEM name
    template[0:3] = b'\xEB\x3C\x90'  # Standard jump instruction
    template[3:11] = b'MSDOS5.0'     # Common OEM name
    
    # FAT16 signature at the end
    template[510:512] = b'\x55\xAA'
    
    # Try different combinations of parameters
    for bytes_per_sector in bytes_per_sectors:
        for sectors_per_cluster in sectors_per_clusters:
            for fat_type in fat_types:
                for reserved_sectors in [1, 2]:
                    for fats in [1, 2]:
                        config = {
                            "bytes_per_sector": bytes_per_sector,
                            "sectors_per_cluster": sectors_per_cluster,
                            "reserved_sectors": reserved_sectors,
                            "num_fats": fats,
                            "root_entries": 512,  # Standard for FAT16
                            "fat_type": fat_type
                        }
                        
                        # Calculate total sectors based on disk size
                        config["total_sectors"] = disk_size // bytes_per_sector
                        
                        # Calculate sectors per FAT based on total sectors and FAT type
                        if fat_type == 12:
                            entries_per_sector = bytes_per_sector // 1.5  # Approx for FAT12
                        else:  # FAT16
                            entries_per_sector = bytes_per_sector // 2
                            
                        sectors_needed = config["total_sectors"] // sectors_per_cluster / entries_per_sector
                        config["sectors_per_fat"] = max(1, int(sectors_needed * 1.1))  # Add 10% margin
                        
                        # Score this configuration
                        score = score_fat_config(drive_letter, config)
                        
                        if score > best_score:
                            best_score = score
                            best_config = config
    
    if best_config:
        # Build boot sector from best configuration
        boot_sector = create_boot_sector(template, best_config)
        
        # Save recovered boot sector
        with open(output_path, "wb") as f:
            f.write(boot_sector)
            
        print(f"Rebuilt boot sector with parameters:")
        print(f"  Bytes per sector: {best_config['bytes_per_sector']}")
        print(f"  Sectors per cluster: {best_config['sectors_per_cluster']}")
        print(f"  Reserved sectors: {best_config['reserved_sectors']}")
        print(f"  Number of FATs: {best_config['num_fats']}")
        print(f"  Root entries: {best_config['root_entries']}")
        print(f"  Sectors per FAT: {best_config['sectors_per_fat']}")
        print(f"  FAT type: FAT{best_config['fat_type']}")
        print(f"Saved rebuilt boot sector to {output_path}")
        
        return boot_sector
    
    print("Could not determine valid boot sector parameters.")
    return None

def score_fat_config(drive_letter, config):
    """
    Score a FAT configuration based on how well it produces valid file system structures.
    Higher score means more likely to be correct.
    """
    score = 0
    
    # Calculate key offsets
    fat_start = config["reserved_sectors"] * config["bytes_per_sector"]
    root_dir_start = fat_start + (config["num_fats"] * config["sectors_per_fat"] * config["bytes_per_sector"])
    root_dir_size = config["root_entries"] * 32
    data_start = root_dir_start + root_dir_size
    
    # Read the potential FAT area
    with open_volume(drive_letter) as volume:
        # Check FAT area for valid patterns
        volume.seek(fat_start)
        fat_data = volume.read(config["sectors_per_fat"] * config["bytes_per_sector"])
        
        # FAT should start with specific markers
        if config["fat_type"] == 16 and fat_data[0:4] == b'\xF8\xFF\xFF\xFF':
            score += 10
        elif config["fat_type"] == 12 and fat_data[0:3] == b'\xF8\xFF\xFF':
            score += 10
        
        # Check for valid FAT entries (not all zeros or all FFs)
        zeros_count = fat_data.count(b'\x00')
        ff_count = fat_data.count(b'\xFF')
        
        # Good FAT should have a mix of values
        if zeros_count < len(fat_data) * 0.9 and ff_count < len(fat_data) * 0.9:
            score += 5
        
        # Check root directory for valid entries
        volume.seek(root_dir_start)
        root_data = volume.read(root_dir_size)
        
        # Look for standard directory entries (first byte 0x00, 0xE5 or valid ASCII)
        valid_entries = 0
        for i in range(0, len(root_data), 32):
            entry = root_data[i:i+32]
            first_byte = entry[0]
            
            if first_byte == 0x00:  # End of directory marker
                valid_entries += 1
            elif first_byte == 0xE5:  # Deleted entry marker
                valid_entries += 1
            elif 0x20 <= first_byte <= 0x7E:  # Valid ASCII
                # Check for valid attributes (byte 11)
                attr = entry[11]
                if attr in [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20]:
                    valid_entries += 2  # Higher score for valid attributes
                else:
                    valid_entries += 1
        
        # Score based on percentage of potentially valid entries
        score += (valid_entries / config["root_entries"]) * 20
        
        # Check for common directory names in ASCII
        common_names = [b'SYSTEM', b'RECYCL', b'WINDOWS', b'PROGRAM', b'USERS']
        for name in common_names:
            if name in root_data:
                score += 5
    
    return score

def create_boot_sector(template, config):
    """
    Create a boot sector based on the template and configuration
    """
    boot = bytearray(template)
    
    # Kiểm tra xem 'total_sectors' có trong config không
    if 'total_sectors' not in config:
        # Ước tính dựa trên các thông số khác
        config['total_sectors'] = 32768  # Giá trị mặc định an toàn cho FAT16
    
    # Fill in the boot sector fields
    struct.pack_into("<H", boot, 11, config["bytes_per_sector"])
    boot[13] = config["sectors_per_cluster"]
    struct.pack_into("<H", boot, 14, config["reserved_sectors"])
    boot[16] = config["num_fats"]
    struct.pack_into("<H", boot, 17, config["root_entries"])
    
    # Total sectors (16-bit field if possible, otherwise use 32-bit field)
    if config["total_sectors"] < 65536:
        struct.pack_into("<H", boot, 19, config["total_sectors"])
        struct.pack_into("<I", boot, 32, 0)  # Clear 32-bit field
    else:
        struct.pack_into("<H", boot, 19, 0)  # Clear 16-bit field
        struct.pack_into("<I", boot, 32, config["total_sectors"])
    
    # Media descriptor - standard value for fixed disk
    boot[21] = 0xF8
    
    # Sectors per FAT
    struct.pack_into("<H", boot, 22, config["sectors_per_fat"])
    
    # Sectors per track and number of heads (not critical, use standard values)
    struct.pack_into("<H", boot, 24, 63)    # Sectors per track
    struct.pack_into("<H", boot, 26, 255)   # Number of heads
    
    # Hidden sectors - usually 0 for non-partitioned media
    struct.pack_into("<I", boot, 28, 0)
    
    # For FAT16, add extended boot record
    if config["fat_type"] == 16:
        # Drive number
        boot[36] = 0x80  # Fixed disk
        
        # Reserved
        boot[37] = 0
        
        # Extended boot signature
        boot[38] = 0x29
        
        # Volume ID (random)
        import random
        volume_id = random.randint(0, 0xFFFFFFFF)
        struct.pack_into("<I", boot, 39, volume_id)
        
        # Volume label and file system type
        volume_label = b'NO NAME    '
        fs_type = b'FAT16   '
        
        for i, c in enumerate(volume_label):
            boot[43 + i] = c
            
        for i, c in enumerate(fs_type):
            boot[54 + i] = c
    
    return boot

def get_disk_size(drive_letter):
    """Get the total size of the disk in bytes"""
    try:
        import win32api
        import win32file
        
        drive_path = f"\\\\.\\{drive_letter}:"
        hfile = win32file.CreateFile(
            drive_path, win32file.GENERIC_READ,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None, win32file.OPEN_EXISTING, 0, None
        )
        
        try:
            return win32file.GetFileSize(hfile)
        finally:
            win32file.CloseHandle(hfile)
    except:
        # Fallback: estimate based on what we can read
        max_size = 100 * 1024 * 1024  # 100MB - arbitrary limit for scanning
        
        with open_volume(drive_letter) as volume:
            volume.seek(0)
            try:
                data = volume.read(max_size)
                return len(data)
            except:
                # If reading fails, return a conservative estimate
                return 16 * 1024 * 1024  # 16MB (typical for small FAT volumes)

def compare_and_recover_boot(drive_letter, output_path="recovered_boot.bin", fat_type=None):
    """
    So sánh boot sector hiện tại với boot sector phân tích được và chỉ phục hồi nếu cần
    """
    print("Đọc boot sector hiện tại...")
    current_boot = read_volume_sectors(drive_letter, 0, 1)
    
    # Phân tích boot sector hiện tại
    current_params = {}
    try:
        current_params = extract_fat_info(current_boot)
        print("\n=== THÔNG SỐ BOOT SECTOR HIỆN TẠI ===")
        print(f"Bytes per sector: {current_params['bytes_per_sector']}")
        print(f"Sectors per cluster: {current_params['sectors_per_cluster']}")
        print(f"Reserved sectors: {current_params['reserved_sectors']}")
        print(f"Số bảng FAT: {current_params['num_fats']}")
        print(f"Số entry RDET: {current_params['root_entries']}")
        print(f"Tổng sectors: {current_params['total_sectors']}")
        print(f"Sectors per FAT: {current_params['sectors_per_fat']}")
        print(f"Loại FAT: FAT{current_params['fat_type']}")
    except Exception as e:
        print(f"Không thể phân tích boot sector hiện tại: {str(e)}")
        print("Tiến hành khôi phục...")
        return recover_boot_sector(drive_letter, output_path, fat_type)
    
    # Phân tích boot sector tối ưu
    print("\nPhân tích cấu trúc hệ thống file để tìm thông số tối ưu...")
    optimal_boot = None
    
    # Scan first few sectors for boot sector candidates
    candidates = []
    with open_volume(drive_letter) as volume:
        for sector in range(10):  # Check first 10 sectors
            volume.seek(sector * 512)
            data = volume.read(512)
            
            # Check for boot sector signature
            if data[510:512] == b'\x55\xAA':
                try:
                    info = extract_fat_info(data)
                    candidates.append({
                        "sector": sector,
                        "data": data,
                        "params": info
                    })
                except:
                    pass
    
    if not candidates:
        print("Không tìm thấy boot sector khác, thử phân tích hệ thống file...")
        return rebuild_boot_sector(drive_letter, output_path, fat_type)
    
    # So sánh với các ứng viên tìm được
    differences = []
    for candidate in candidates:
        diff = compare_boot_params(current_params, candidate["params"])
        if diff:
            differences.append({
                "candidate": candidate,
                "differences": diff
            })
    
    if not differences:
        print("\n=== KẾT QUẢ SO SÁNH ===")
        print("Boot sector hiện tại có vẻ tốt. Không phát hiện sự khác biệt so với cấu trúc dữ liệu thực tế.")
        print("Không cần thực hiện khôi phục.")
        return None
    
    # Hiển thị các khác biệt và đề xuất thay đổi
    print("\n=== PHÁT HIỆN SỰ KHÁC BIỆT ===")
    for i, diff_entry in enumerate(differences):
        candidate = diff_entry["candidate"]
        diffs = diff_entry["differences"]
        
        print(f"\nỨng viên {i+1} (Sector {candidate['sector']}):")
        for param, values in diffs.items():
            print(f"  - {param}: Hiện tại={values['current']} → Đề xuất={values['suggested']}")
    
    print("\nBạn có muốn khôi phục boot sector với thông số tối ưu? (y/n)")
    choice = input().strip().lower()
    
    if choice == 'y':
        # Sử dụng ứng viên đầu tiên (có thể cải tiến để cho người dùng chọn)
        with open(output_path, "wb") as f:
            f.write(differences[0]["candidate"]["data"])
        
        print(f"Đã lưu boot sector được đề xuất vào {output_path}")
        print("Để áp dụng boot sector mới, hãy sử dụng: python main.py E --apply-boot recovered_boot.bin")
        return differences[0]["candidate"]["data"]
    else:
        print("Đã hủy quá trình khôi phục.")
        return None

def compare_boot_params(current, suggested):
    """So sánh các thông số quan trọng của boot sector"""
    differences = {}
    critical_params = [
        "bytes_per_sector", 
        "sectors_per_cluster", 
        "reserved_sectors",
        "num_fats", 
        "root_entries", 
        "sectors_per_fat",
        "fat_type"
    ]
    
    for param in critical_params:
        if current[param] != suggested[param]:
            differences[param] = {
                "current": current[param],
                "suggested": suggested[param]
            }
    
    return differences

def interactive_boot_sector_repair(drive_letter, fat_type=None):
    """
    Phân tích boot sector hiện tại, đề xuất thông số tối ưu và cho phép người dùng
    chọn lựa từng thông số trước khi áp dụng thay đổi.
    """
    print("=== PHÂN TÍCH & SỬA CHỮA TƯƠNG TÁC BOOT SECTOR ===\n")
    
    # Đọc boot sector hiện tại
    print("Đọc boot sector hiện tại...")
    current_boot = read_volume_sectors(drive_letter, 0, 1)
    
    # Phân tích boot sector hiện tại
    current_params = {}
    current_valid = True
    try:
        current_params = extract_fat_info(current_boot)
        print("\n=== THÔNG SỐ BOOT SECTOR HIỆN TẠI ===")
        print(f"Bytes per sector: {current_params['bytes_per_sector']}")
        print(f"Sectors per cluster: {current_params['sectors_per_cluster']}")
        print(f"Reserved sectors: {current_params['reserved_sectors']}")
        print(f"Số bảng FAT: {current_params['num_fats']}")
        print(f"Số entry RDET: {current_params['root_entries']}")
        print(f"Tổng sectors: {current_params['total_sectors']}")
        print(f"Sectors per FAT: {current_params['sectors_per_fat']}")
        print(f"Loại FAT: FAT{current_params['fat_type']}")
    except Exception as e:
        print(f"Không thể phân tích boot sector hiện tại: {str(e)}")
        current_valid = False
        current_params = {
            'bytes_per_sector': 512,  # Giá trị mặc định
            'sectors_per_cluster': 1,
            'reserved_sectors': 1,
            'num_fats': 2,
            'root_entries': 512,
            'total_sectors': 0,  # Sẽ được tính toán
            'sectors_per_fat': 0,  # Sẽ được tính toán
            'fat_type': fat_type if fat_type else 16
        }
    
    # Phân tích cấu trúc ổ đĩa để đề xuất thông số tối ưu
    print("\nPhân tích cấu trúc hệ thống file để đề xuất thông số tối ưu...")
    
    # Tìm kiếm các thông số phù hợp nhất dựa trên cấu trúc dữ liệu
    # (Sử dụng phương pháp trong rebuild_boot_sector với một số điều chỉnh)
    bytes_per_sectors = [512, 1024, 2048, 4096]
    sectors_per_clusters = [1, 2, 4, 8, 16, 32]
    fat_types_to_try = [fat_type] if fat_type else [16, 12, 32]
    
    # Đo kích thước ổ đĩa
    disk_size = get_disk_size(drive_letter)
    
    # Tạo các cấu hình để thử và tính điểm
    best_config = None
    best_score = -1
    
    for bytes_per_sector in bytes_per_sectors:
        for sectors_per_cluster in sectors_per_clusters:
            for fat_type_to_try in fat_types_to_try:
                for reserved_sectors in [1, 2]:
                    for fats in [1, 2]:
                        config = {
                            "bytes_per_sector": bytes_per_sector,
                            "sectors_per_cluster": sectors_per_cluster,
                            "reserved_sectors": reserved_sectors,
                            "num_fats": fats,
                            "root_entries": 512,  # Tiêu chuẩn cho FAT16
                            "fat_type": fat_type_to_try
                        }
                        
                        # Tính toán các tham số còn lại
                        config["total_sectors"] = disk_size // bytes_per_sector
                        
                        # Tính toán kích thước FAT
                        if fat_type_to_try == 12:
                            entries_per_sector = bytes_per_sector // 1.5  # Xấp xỉ cho FAT12
                        else:  # FAT16/FAT32
                            entries_per_sector = bytes_per_sector // 2
                            
                        sectors_needed = config["total_sectors"] // sectors_per_cluster / entries_per_sector
                        config["sectors_per_fat"] = max(1, int(sectors_needed * 1.1))  # Thêm 10% dự phòng
                        
                        # Tính điểm cho cấu hình
                        score = score_fat_config(drive_letter, config)
                        
                        if score > best_score:
                            best_score = score
                            best_config = config
    
    if not best_config:
        print("Không thể xác định thông số tối ưu. Sử dụng thông số FAT16 tiêu chuẩn.")
        best_config = {
            'bytes_per_sector': 512,
            'sectors_per_cluster': 1,
            'reserved_sectors': 1,
            'num_fats': 2,
            'root_entries': 512,
            'total_sectors': disk_size // 512,
            'sectors_per_fat': 32,
            'fat_type': 16
        }
    
    # Hiển thị so sánh và cho phép người dùng lựa chọn
    print("\n=== SO SÁNH THÔNG SỐ ===")
    print("Thông số           | Hiện tại      | Đề xuất       | Lựa chọn")
    print("------------------ | ------------- | ------------- | -------")
    
    # Khởi tạo thông số được chọn với giá trị hiện tại hoặc đề xuất
    chosen_params = {}
    
    # Danh sách các thông số cần xem xét
    param_names = [
        ('bytes_per_sector', 'Bytes per sector'),
        ('sectors_per_cluster', 'Sectors per cluster'),
        ('reserved_sectors', 'Reserved sectors'),
        ('num_fats', 'Số bảng FAT'),
        ('root_entries', 'Số entry RDET'),
        ('total_sectors', 'Tổng sectors'),  # Thêm dòng này
        ('sectors_per_fat', 'Sectors per FAT'),
        ('fat_type', 'Loại FAT')
    ]
    
    # Hiển thị và yêu cầu người dùng chọn lựa từng thông số
    for param_key, param_name in param_names:
        current_val = current_params.get(param_key, 'N/A')
        suggested_val = best_config.get(param_key, 'N/A')
        
        # Định dạng hiển thị
        current_display = str(current_val).ljust(13)
        suggested_display = str(suggested_val).ljust(13)
        
        print(f"{param_name.ljust(18)} | {current_display} | {suggested_display} | ", end='')
        
        if current_valid and current_val == suggested_val:
            print("Giống nhau")
            chosen_params[param_key] = current_val
        else:
            # Yêu cầu người dùng chọn
            choice = input(f"Chọn hiện tại (c) hoặc đề xuất (s): ").strip().lower()
            if choice == 'c' and current_valid:
                chosen_params[param_key] = current_val
                print(f"Đã chọn giá trị hiện tại: {current_val}")
            else:
                chosen_params[param_key] = suggested_val
                print(f"Đã chọn giá trị đề xuất: {suggested_val}")
    
    # Thêm đoạn code này trước khi gọi create_boot_sector:

    # Đảm bảo tất cả thông số cần thiết đều có trong chosen_params
    required_params = ['bytes_per_sector', 'sectors_per_cluster', 'reserved_sectors', 
                      'num_fats', 'root_entries', 'sectors_per_fat', 'fat_type',
                      'total_sectors']  # 'total_sectors' là cần thiết

    for param in required_params:
        if param not in chosen_params:
            if param in best_config:
                chosen_params[param] = best_config[param]
            elif param in current_params:
                chosen_params[param] = current_params[param]
            else:
                # Giá trị mặc định trong trường hợp không tìm thấy
                if param == 'total_sectors':
                    chosen_params[param] = disk_size // chosen_params['bytes_per_sector']

    # Sau đó mới gọi hàm create_boot_sector
    # Tạo boot sector mới với các thông số đã chọn
    print("\n=== THÔNG SỐ BOOT SECTOR ĐÃ CHỌN ===")
    for param_key, param_name in param_names:
        print(f"{param_name}: {chosen_params[param_key]}")
    
    # Xác nhận áp dụng thay đổi
    confirm = input("\nBạn có muốn áp dụng các thông số đã chọn vào boot sector? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Đã hủy thao tác. Không có thay đổi nào được áp dụng.")
        return False
    
    # Tạo boot sector mới
    new_boot = create_boot_sector(bytearray(current_boot) if current_valid else bytearray(512), chosen_params)
    
    # Ghi boot sector mới vào ổ đĩa
    try:
        from fat.reader import open_volume
        with open_volume(drive_letter, 'r+b') as volume:
            volume.seek(0)
            volume.write(new_boot)
            volume.flush()
        print(f"\nĐã áp dụng boot sector mới cho ổ đĩa {drive_letter}.")
        print("Hãy kiểm tra lại với lệnh: python main.py E -t")
        return True
    except Exception as e:
        print(f"\nLỗi khi ghi boot sector: {str(e)}")
        print("Thử chạy lại với quyền Administrator hoặc sử dụng lệnh:")
        print(f"python main.py {drive_letter} --apply-boot recovered_boot.bin")
        
        # Vẫn lưu boot sector để có thể áp dụng sau
        with open("recovered_boot.bin", "wb") as f:
            f.write(new_boot)
        
        return False