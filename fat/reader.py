import struct
import win32file
import win32con
import os

def open_volume(drive_letter, mode="rb"):
    """
    Mở thiết bị lưu trữ để đọc/ghi dữ liệu thô.
    
    Args:
        drive_letter: Chữ cái ổ đĩa (ví dụ: 'E')
        mode: Chế độ mở (mặc định là "rb" - đọc nhị phân)
        
    Returns:
        File object đã mở
    """
    # Trên Windows, sử dụng đường dẫn \\.\X: để mở thiết bị vật lý
    volume_path = f"\\\\.\\{drive_letter}:"
    try:
        return open(volume_path, mode)
    except Exception as e:
        raise IOError(f"Không thể mở ổ đĩa {drive_letter} trong chế độ {mode}: {str(e)}")

def read_volume_sectors(drive_letter, start_sector, num_sectors, bytes_per_sector=512):
    """Read sectors directly from a mounted volume"""
    # Create device path for the drive letter
    volume_path = f"\\\\.\\{drive_letter}:"
    
    try:
        # Open the volume with direct access
        handle = win32file.CreateFile(
            volume_path,
            win32con.GENERIC_READ,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            0,
            None
        )
        
        if handle == win32file.INVALID_HANDLE_VALUE:
            raise Exception(f"Could not open volume {drive_letter}:")
        
        # Seek to the desired sector
        win32file.SetFilePointer(handle, start_sector * bytes_per_sector, 0)
        
        # Read the sectors
        error, data = win32file.ReadFile(handle, num_sectors * bytes_per_sector)
        
        win32file.CloseHandle(handle)
        return data
    except Exception as e:
        raise Exception(f"Error reading sectors: {e}")

def read_fat_entry(fat, entry_number, fat_type):
    """Read a specific entry from the FAT"""
    if fat_type == "FAT12":
        # Calculate byte position and offset in FAT
        byte_pos = entry_number + (entry_number // 2)
        
        # Make sure we're not reading past the end of the FAT
        if byte_pos + 2 > len(fat):
            return 0
        
        # Read 2 bytes from FAT
        value = struct.unpack("<H", fat[byte_pos:byte_pos+2])[0]
        
        # Extract proper 12-bit value depending on whether it's odd or even
        if entry_number % 2 == 0:
            return value & 0x0FFF
        else:
            return value >> 4
    else:  # FAT16
        pos = entry_number * 2
        if pos + 2 > len(fat):
            return 0
        return struct.unpack("<H", fat[pos:pos+2])[0]