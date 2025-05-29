# Define common file signatures for file carving
FILE_SIGNATURES = {
    'JPEG': [
        {'header': b'\xFF\xD8\xFF\xE0', 'footer': b'\xFF\xD9', 'extension': 'jpg'},
        {'header': b'\xFF\xD8\xFF\xE1', 'footer': b'\xFF\xD9', 'extension': 'jpg'}
    ],
    'PNG': [
        {'header': b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A', 'footer': b'\x49\x45\x4E\x44\xAE\x42\x60\x82', 'extension': 'png'}
    ],
    'GIF': [
        {'header': b'\x47\x49\x46\x38\x37\x61', 'footer': b'\x00\x3B', 'extension': 'gif'},
        {'header': b'\x47\x49\x46\x38\x39\x61', 'footer': b'\x00\x3B', 'extension': 'gif'}
    ],
    'PDF': [
        {'header': b'\x25\x50\x44\x46', 'footer': b'\x25\x25\x45\x4F\x46', 'extension': 'pdf'}
    ],
    'DOC': [
        {'header': b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1', 'extension': 'doc'}
    ],
    'ZIP': [
        {'header': b'\x50\x4B\x03\x04', 'footer': b'\x50\x4B\x05\x06', 'extension': 'zip'}
    ],
    'EXE': [
        {'header': b'\x4D\x5A', 'extension': 'exe'}
    ],
    'TXT': [
        # Text files don't have a standard signature, but we can look for BOM for unicode
        {'header': b'\xEF\xBB\xBF', 'extension': 'txt'},  # UTF-8 
        {'header': b'\xFF\xFE', 'extension': 'txt'},      # UTF-16 (LE)
        {'header': b'\xFE\xFF', 'extension': 'txt'}       # UTF-16 (BE)
    ]
}