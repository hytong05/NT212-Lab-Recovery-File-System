import sys
import argparse
from fat_analyzer import analyze_fat_volume
from fat_extractor import extract_file_from_volume

def main():
    parser = argparse.ArgumentParser(description="FAT volume analyzer and file extractor for mounted volumes")
    parser.add_argument("drive", help="Drive letter of the mounted volume (e.g., E)")
    parser.add_argument("-f", "--extract", help="Extract a specific file")
    parser.add_argument("-o", "--output", help="Output file path for extraction")
    parser.add_argument("-t", "--tree", action="store_true", help="Show only directory tree structure")
    
    args = parser.parse_args()
    
    # Remove any colon from the drive letter
    drive_letter = args.drive.strip().rstrip(':')
    
    if args.extract:
        if not args.output:
            print("Error: Output path (-o) must be specified when extracting files")
            sys.exit(1)
        extract_file_from_volume(drive_letter, args.extract, args.output)
    elif args.tree:
        # Just show the directory tree
        from fat_directory import analyze_directory_structure
        from fat_utils import print_directory_tree
        directory_tree = analyze_directory_structure(drive_letter)
        print("=== DIRECTORY TREE STRUCTURE ===")
        print_directory_tree({"ROOT": directory_tree})
    else:
        analyze_fat_volume(drive_letter)

if __name__ == "__main__":
    main()