# NT212-Lab-Recovery-File-System

A Python-based toolkit for FAT file system analysis and file recovery. This project provides tools for examining FAT file system structures and extracting files from disk images or mounted volumes.

## Overview

This project was developed as part of the NT212 Lab course, focusing on file system forensics and recovery techniques. The toolkit allows users to:

1. Analyze FAT file system structures (FAT12/FAT16)
2. Extract metadata from boot sectors
3. Examine Root Directory Entry Tables (RDET)
4. Display complete directory trees with Long File Name support
5. Recover deleted files from volumes
6. Repair damaged boot sectors and FAT tables
7. Extract individual files from FAT volumes
8. Perform file carving based on file signatures

## Features

- **Boot Sector Analysis**: Extract critical information including bytes per sector, sectors per cluster, FAT type, etc.
- **FAT Chain Analysis**: Trace file allocation chains through the FAT tables
- **Root Directory Parsing**: Display detailed information about files and directories
- **Directory Tree Display**: Visualize the complete directory structure in an easy-to-read tree format
- **Long File Name Support**: Properly display and process long filenames (beyond the 8.3 format)
- **Deleted File Recovery**: Scan for and recover deleted files from anywhere in the filesystem
- **Boot Sector Recovery**: Identify and recover damaged boot sectors
- **FAT Table Repair**: Restore damaged FAT tables using backup copies
- **File Carving**: Extract files based on their binary signatures even when directory entries are damaged

## System Requirements

- Python 3.6 or higher
- pywin32 library (`pip install pywin32`)
- Windows operating system

## Installation

1. Clone repository:
    ```
    git clone https://github.com/hytong05/NT212-Lab-Recovery-File-System.git
    cd NT212-Lab-Recovery-File-System
    ```

2. Install required libraries:
    ```
    pip install pywin32
    ```

## Project Structure

```
NT212-Lab-Recovery-File-System/
├── main.py                  # Main entry point of the program
├── README.md                # Documentation
│
├── fat/                     # FAT analysis module
│   ├── __init__.py
│   ├── analyzer.py          # Detailed FAT analysis
│   ├── directory.py         # Directory structure handling
│   ├── reader.py            # Device data reading
│   ├── utils.py             # Utility functions
│   └── parser.py            # FAT structure parsing
│
└── recovery/                # Data recovery module
     ├── __init__.py
     ├── boot_recovery.py     # Boot sector recovery
     ├── fat_recovery.py      # FAT table recovery
     ├── directory_recovery.py # Directory recovery
     ├── carving.py           # File carving
     └── signature_db.py      # File signature database
```

## Usage Examples

### Example 1: Analyzing a mounted FAT volume
```
python main.py E

=== BOOT SECTOR INFORMATION ===
Bytes per sector: 512
Sectors per cluster: 4
Reserved sectors (before FAT): 1
Number of FAT tables: 2
Number of RDET entries: 512
Total sectors: 8192
Sectors per FAT: 6
Volume size: 4194304 bytes (4.00 MB)
FAT type: FAT16
```

### Example 2: Displaying directory tree
```
python main.py E -t

=== DIRECTORY TREE STRUCTURE ===
ROOT
     ├── $RECYCLE.BIN
     │   └── DESKTOP.INI
     ├── Lab
     │   ├── Assignment_2
     │   │   ├── 2.1
     │   │   │   └── Document.pdf
     │   │   └── 2.2
     │   │       └── Report.docx
     │   └── FileA.txt
     └── System Volume Information
          └── WPSettings.dat
```

### Example 3: Extracting a file
```
python main.py E -f Document.pdf -o extracted_document.pdf

Extracting: Document.pdf...
Extracted to: extracted_document.pdf
```

### Example 4: Scanning for deleted files
```
python main.py E --scan-deleted

=== DELETED FILES THAT MAY BE RECOVERABLE ===
1. Lab/_ILEB.TXT (possibly FileB.txt) - 720 bytes
2. $RECYCLE.BIN/_RAV01NO.TXT - 720 bytes
```

### Example 5: Recovering a deleted file
```
python main.py E --recover-deleted FileB.txt -o recovered_file.txt

Recovering file: start cluster 123, size 720 bytes
Reading 1 clusters starting from sector 456
Recovered 720 bytes to recovered_file.txt
```


## FAT File System Structure

The FAT file system consists of four main regions:

1. **Boot Sector**: Contains essential parameters needed to access the volume
   - Bytes per sector
   - Sectors per cluster
   - Number of FAT tables
   - Number of root directory entries
   - Total sectors
   - Sectors per FAT

2. **File Allocation Tables (FAT)**: Contains chains of clusters for each file
   - FAT12: 12-bit entries (for volumes < 16MB)
   - FAT16: 16-bit entries (for volumes < 2GB)

3. **Root Directory**: Fixed-size table with information about files and directories
   - Each entry is 32 bytes
   - Contains filename, extension, attributes, timestamps, starting cluster, size

4. **Data Region**: Area where actual file and directory data is stored
   - Organized in clusters (multiple sectors)
   - Referenced through chains in the FAT

## Command Line Arguments

| Argument | Description |
|--------|-------|
| `drive` | Drive letter to analyze (e.g., E) |
| `-t`, `--tree` | Display directory structure as a tree |
| `-f`, `--extract FILE` | Extract a specific file |
| `-o`, `--output PATH` | Specify output path for extracted/recovered files |
| `--recover-boot` | Scan for and recover damaged boot sector |
| `--recover-fat` | Recover FAT table from backup copy |
| `--scan-deleted` | Scan for deleted files throughout the filesystem |
| `--recover-deleted FILE` | Recover a deleted file by name or index |
| `--carve` | Scan for file signatures and carve files |
| `--carve-type TYPE` | Specify file type for carving (JPEG, PDF, etc.) |

## Troubleshooting

1. **Problem**: Cannot access drive
   **Solution**: Ensure you have administrator privileges. Run CMD or PowerShell as administrator.

2. **Problem**: Recovered file is corrupted
   **Solution**: Check if the original data area has been overwritten. Try file carving as an alternative.

3. **Problem**: Cannot find deleted files
   **Solution**: Try scanning the entire drive with `--scan-deleted`. Note that files may have been overwritten.

4. **Problem**: pywin32 module not found
   **Solution**: Install the module using `pip install pywin32`

## Technical Details

### Directory Entry Structure

Each directory entry in FAT is 32 bytes with the following structure:
- Bytes 0-7: Filename (padded with spaces)
- Bytes 8-10: Extension (padded with spaces)
- Byte 11: Attributes (Read-only, Hidden, System, Volume label, Directory, Archive)
- Bytes 12-21: Reserved and system-use fields
- Bytes 22-23: Creation time
- Bytes 24-25: Creation date
- Bytes 26-27: Starting cluster number
- Bytes 28-31: File size in bytes

### Long Filename Entries

LFN (Long Filename) entries use a special format:
- Byte 11: Attribute value 0x0F
- Multiple LFN entries may be used for a single filename
- Each entry can store up to 13 Unicode characters

## Authors

- **Hy Tong** - [hytong05](https://github.com/hytong05)

## License

This project is licensed for educational purposes only.