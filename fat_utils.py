import struct

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