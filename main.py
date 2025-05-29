import sys
import argparse
from fat.analyzer import analyze_fat_volume
from fat.directory import analyze_directory_structure
from fat.utils import print_directory_tree
from fat_extractor import extract_file_from_volume
from recovery.boot_recovery import recover_boot_sector, rebuild_boot_sector
from recovery.fat_recovery import recover_fat_from_copy, reconstruct_fat_by_scanning
from recovery.directory_recovery import recover_root_directory, scan_for_deleted_files, recover_deleted_file
from recovery.carving import scan_disk_for_signatures, carve_file
from fat.analyzer import check_filesystem_integrity

def main():
    parser = argparse.ArgumentParser(description="FAT volume analyzer and file extractor for mounted volumes")
    parser.add_argument("drive", help="Drive letter of the mounted volume (e.g., E)")
    parser.add_argument("-f", "--extract", help="Extract a specific file")
    parser.add_argument("-o", "--output", help="Output file path for extraction")
    parser.add_argument("-t", "--tree", action="store_true", help="Show only directory tree structure")
    
    # New recovery options
    recovery_group = parser.add_argument_group('Recovery options')
    recovery_group.add_argument("--recover-boot", nargs='?', const=True, default=False, 
                               help="Recover damaged boot sector (optionally specify FAT type: 12, 16, 32)")
    recovery_group.add_argument("--fat-type", type=int, choices=[12, 16, 32],
                               help="Specify FAT type for boot sector recovery (12, 16, or 32)")
    recovery_group.add_argument("--recover-fat", action="store_true", 
                               help="Recover damaged FAT from backup copy")
    recovery_group.add_argument("--scan-deleted", action="store_true", 
                               help="Scan for deleted files")
    recovery_group.add_argument("--recover-deleted", 
                               help="Recover deleted file by file number or name")
    recovery_group.add_argument("--carve", action="store_true", 
                               help="Scan for file signatures and carve files")
    recovery_group.add_argument("--carve-type", 
                               help="File type to carve (e.g., JPEG, PDF)")
    recovery_group.add_argument("--apply-boot", metavar="BOOT_FILE",
                               help="Áp dụng boot sector đã khôi phục vào ổ đĩa")
    recovery_group.add_argument("--interactive-repair", action="store_true",
                          help="Sửa chữa boot sector với chế độ tương tác")

    args = parser.parse_args()
    
    # Remove any colon from the drive letter
    drive_letter = args.drive.strip().rstrip(':')
    
    # Handle recovery options
    if args.recover_boot:
        from recovery.boot_recovery import compare_and_recover_boot
        
        # Kiểm tra xem người dùng đã chỉ định loại FAT chưa
        fat_type = args.fat_type
        if isinstance(args.recover_boot, str) and args.recover_boot.isdigit():
            fat_type = int(args.recover_boot)
            if fat_type not in [12, 16, 32]:
                print(f"Loại FAT không hợp lệ: {fat_type}. Sử dụng 12, 16 hoặc 32.")
                return
        
        boot_data = compare_and_recover_boot(drive_letter, fat_type=fat_type)
        if boot_data:
            print("Boot sector đã được phân tích và lưu vào file")
        return
        
    elif args.recover_fat:
        # First read the boot sector
        from fat.reader import read_volume_sectors
        boot_sector = read_volume_sectors(drive_letter, 0, 1)
        
        fat = recover_fat_from_copy(drive_letter, boot_sector, args.output or "recovered_fat.bin")
        if fat:
            print("FAT recovery successful")
        return
        
    elif args.scan_deleted:
        # First read the boot sector
        from fat.reader import read_volume_sectors
        boot_sector = read_volume_sectors(drive_letter, 0, 1)
        
        # Use recursive scan instead of just root directory
        from recovery.directory_recovery import scan_deleted_recursive
        deleted_files = scan_deleted_recursive(drive_letter, boot_sector)
        
        print("\n=== DELETED FILES THAT MAY BE RECOVERABLE ===")
        for i, file in enumerate(deleted_files):
            location = file['location'] if 'location' in file else 'Root Directory'
            display_name = file['marked_filename']  # Hiển thị tên với dấu xóa
            
            # Hiển thị tên gốc nếu có thể đoán được
            if 'possible_original' in file and file['possible_original']:
                print(f"{i+1}. {location}/{display_name} (có thể là {file['possible_original']}) - {file['file_size']} bytes")
            else:
                print(f"{i+1}. {location}/{display_name} - {file['file_size']} bytes")
        
        if not deleted_files:
            print("No deleted files found")
        return
        
    elif args.recover_deleted:
        # First read the boot sector
        from fat.reader import read_volume_sectors
        boot_sector = read_volume_sectors(drive_letter, 0, 1)
        
        # Use recursive scan to find deleted files in all directories
        from recovery.directory_recovery import scan_deleted_recursive
        deleted_files = scan_deleted_recursive(drive_letter, boot_sector)
        
        if not deleted_files:
            print("No deleted files found in the filesystem")
            return
            
        # Find the file to recover
        file_to_recover = None
        try:
            # Try to interpret as a number
            file_num = int(args.recover_deleted)
            if 1 <= file_num <= len(deleted_files):
                file_to_recover = deleted_files[file_num-1]
        except ValueError:
            # Interpret as a filename
            search_name = args.recover_deleted.lower()
            
            for file in deleted_files:
                # Check several possible matches
                if file['filename'].lower() == search_name:
                    file_to_recover = file
                    break
                if 'marked_filename' in file and file['marked_filename'].lower() == search_name:
                    file_to_recover = file
                    break
                if 'possible_original' in file and file['possible_original'] and file['possible_original'].lower() == search_name:
                    file_to_recover = file
                    break
                
                # Check if it's path/filename format
                if 'location' in file:
                    full_path = f"{file['location']}/{file['filename']}".lower()
                    if full_path == search_name:
                        file_to_recover = file
                        break
        
        if file_to_recover:
            output_path = args.output or f"recovered_{file_to_recover['filename']}"
            success = recover_deleted_file(
                drive_letter, 
                boot_sector, 
                file_to_recover['start_cluster'], 
                file_to_recover['file_size'],
                output_path
            )
            
            if success:
                location = file_to_recover['location'] if 'location' in file_to_recover else 'Root Directory'
                print(f"File {location}/{file_to_recover['filename']} recovered successfully to {output_path}")
        else:
            print(f"File '{args.recover_deleted}' not found among deleted files")
            
            # Show available files for recovery
            print("\nDeleted files available for recovery:")
            for i, file in enumerate(deleted_files):
                loc = file['location'] if 'location' in file else 'Root Directory'
                print(f"{i+1}. {loc}/{file['filename']} - {file['file_size']} bytes")
        return
        
    elif args.carve:
        print("Scanning disk for file signatures...")
        files = scan_disk_for_signatures(drive_letter)
        
        print("\n=== FILES FOUND BY SIGNATURE ===")
        for i, file in enumerate(files):
            print(f"{i+1}. {file['file_type']} ({file['extension']}) - Starting at sector {file['start_sector']}")
            
        if not files:
            print("No file signatures found")
        elif args.carve_type:
            # Filter by type
            matching_files = [f for f in files if f['file_type'].upper() == args.carve_type.upper()]
            
            if not matching_files:
                print(f"No {args.carve_type} files found")
                return
                
            print(f"\nCarving {len(matching_files)} {args.carve_type} files...")
            
            for i, file in enumerate(matching_files):
                output_path = f"carved_{i+1}.{file['extension']}"
                carve_file(drive_letter, file['start_sector'], output_path, file['file_type'])
                
        return
    
    elif args.apply_boot:
        from fat.utils import apply_boot_sector
        
        if apply_boot_sector(drive_letter, args.apply_boot):
            print("Đã áp dụng boot sector thành công!")
            print("Hệ thống file đã được khôi phục. Hãy kiểm tra lại với lệnh:")
            print(f"python main.py {drive_letter} -t")
        return
    
    elif args.interactive_repair:
        from recovery.boot_recovery import interactive_boot_sector_repair
        
        # Kiểm tra loại FAT đã được chỉ định
        if interactive_boot_sector_repair(drive_letter, args.fat_type):
            print("Đã hoàn tất sửa chữa boot sector tương tác.")
        return
    
    # Regular operation
    if args.extract:
        if not args.output:
            print("Error: Output path (-o) must be specified when extracting files")
            sys.exit(1)
        extract_file_from_volume(drive_letter, args.extract, args.output)
    elif args.tree:
        # Just show the directory tree
        from fat.directory import analyze_directory_structure
        from fat.utils import print_directory_tree
        directory_tree = analyze_directory_structure(drive_letter)
        print("=== DIRECTORY TREE STRUCTURE ===")
        print_directory_tree({"ROOT": directory_tree})
    else:
        boot_sector = analyze_fat_volume(drive_letter)
        
        # After analyzing the FAT volume, check the filesystem integrity
        from fat.reader import read_volume_sectors

        # Đọc boot sector đúng cách
        boot_sector_data = read_volume_sectors(drive_letter, 0, 1)
        
        # Check filesystem integrity
        integrity_issues = check_filesystem_integrity(drive_letter, boot_sector_data)
        
        if integrity_issues:
            print("\033[91m\nBạn có thể khôi phục boot sector với lệnh: python main.py E --recover-boot\033[0m")
        else:
            print("\033[92mKhông phát hiện vấn đề trong hệ thống file.\033[0m")

if __name__ == "__main__":
    main()