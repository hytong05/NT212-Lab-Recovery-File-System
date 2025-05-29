from recovery.signature_db import FILE_SIGNATURES
from fat.reader import read_volume_sectors

def scan_disk_for_signatures(drive_letter, start_sector=0, max_sectors=None, bytes_per_sector=512):
    """Scan disk for known file signatures"""
    found_files = []
    sector = start_sector
    
    while True:
        if max_sectors and sector >= start_sector + max_sectors:
            break
            
        try:
            # Read a sector
            sector_data = read_volume_sectors(drive_letter, sector, 1, bytes_per_sector)
            
            # Check for file signatures
            for file_type, signatures in FILE_SIGNATURES.items():
                for sig in signatures:
                    header = sig['header']
                    if sector_data.startswith(header):
                        # Found a file signature
                        found_files.append({
                            'file_type': file_type,
                            'extension': sig.get('extension', 'bin'),
                            'start_sector': sector,
                            'signature': header.hex(),
                            'footer': sig.get('footer', b'').hex()
                        })
                        break
            
            sector += 1
            if sector % 1000 == 0:
                print(f"Scanning sector {sector}...")
                
        except Exception as e:
            print(f"Error reading sector {sector}: {e}")
            break
    
    return found_files

def carve_file(drive_letter, start_sector, output_path, file_type, max_size=10*1024*1024, bytes_per_sector=512):
    """Carve a file from disk based on its signature"""
    sig_info = next((sig for sigs in FILE_SIGNATURES.get(file_type, []) 
                     for sig in sigs if 'extension' in sig), None)
                     
    if not sig_info:
        print(f"Unknown file type: {file_type}")
        return False
    
    footer = sig_info.get('footer', None)
    max_sectors = max_size // bytes_per_sector
    
    try:
        with open(output_path, 'wb') as outfile:
            current_sector = start_sector
            footer_found = False
            
            for i in range(max_sectors):
                try:
                    sector_data = read_volume_sectors(drive_letter, current_sector, 1, bytes_per_sector)
                    
                    # Write the sector data
                    outfile.write(sector_data)
                    
                    # Check for footer if defined
                    if footer and footer in sector_data:
                        footer_pos = sector_data.find(footer)
                        outfile.truncate(outfile.tell() - len(sector_data) + footer_pos + len(footer))
                        footer_found = True
                        break
                        
                    current_sector += 1
                    
                except Exception as e:
                    print(f"Error reading sector {current_sector}: {e}")
                    break
            
        file_size = os.path.getsize(output_path)
        print(f"Carved {file_size} bytes to {output_path}")
        
        if not footer_found and footer:
            print("Warning: File footer not found, file may be truncated or corrupt")
        
        return True
        
    except Exception as e:
        print(f"Error carving file: {e}")
        return False