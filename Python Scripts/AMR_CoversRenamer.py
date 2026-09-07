import os
import shutil
from typing import Optional, Tuple
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME: str = "Covers Renamer"
VERSION: str = "2.026.07"

ROOT_FOLDER: str = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
ORIGINAL_COVERS_FOLDER: str = '/Users/mushroomoff/Yandex.Disk.localized/Проекты/_Covers/_BIG'


def parse_cover_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a cover filename to extract band, album, and year components.
    
    Args:
        filename: The filename to parse (without extension).
    
    Returns:
        A tuple of (band_name, album_name, year) if successful, None otherwise.
    """
    text_block_count = filename.count(' - ')
    
    # If the filename contains 2 or 3 ' - ' split into components
    if text_block_count == 2:
        name_band, name_album, name_year = filename.split(' - ')
        return (name_band, name_album, name_year)
    elif text_block_count == 3:
        name_band, name_album, name_type, name_year = filename.split(' - ')
        name_album = f'{name_album} [{name_type}]'
        return (name_band, name_album, name_year)
    else:
        return None


def get_band_folder_prefix(band_name: str) -> str:
    """
    Determine the folder prefix based on the first character of the band name.
    
    Args:
        band_name: The name of the band.
    
    Returns:
        A string representing the folder prefix (A-Z, Русское, or 0).
    """
    first_char = str(band_name[0]).upper()
    char_code = ord(first_char)
    
    # Cyrillic letter range
    if 1025 <= char_code <= 1105:
        return 'Русское'
    # Non-alphabetical character
    elif char_code < 65:
        return '0'
    
    return first_char


def main() -> None:
    """Main entry point for the Covers Renamer script."""
    amr.print_name(SCRIPT_NAME, VERSION)

    # Prompt user for a path, if nothing is entered, use the original covers folder
    covers_folder = input(f'Path to big covers folder:\nEnter -> {ORIGINAL_COVERS_FOLDER}\n')
    if not covers_folder:
        covers_folder = ORIGINAL_COVERS_FOLDER

    # Loop through all files in the root folder
    for check_file in os.listdir(covers_folder):
        # Check if the file is a JPG or JPEG
        is_jpg = '.jpg' in check_file.lower()
        is_jpeg = '.jpeg' in check_file.lower()
        
        if is_jpg or is_jpeg:
            # Remove extension for parsing
            filename_without_ext = check_file.rsplit('.', 1)[0]
            
            parsed_result = parse_cover_filename(filename_without_ext)
            
            if parsed_result is None:
                print(f'ERROR: {check_file}')
                continue
            
            name_band, name_album, name_year = parsed_result
            name_band_folder = get_band_folder_prefix(name_band)
            
            # Determine extension
            new_filename_extension = '.jpg' if is_jpg else '.jpeg'
            
            new_filename = f'{name_year[:4]} {name_album}{new_filename_extension}'
            new_directory = os.path.join(covers_folder, name_band_folder, name_band)
            current_file = os.path.join(covers_folder, check_file)
            new_file = os.path.join(new_directory, new_filename)

            # If the directory does not exist, create it
            if not os.path.exists(new_directory):
                os.makedirs(new_directory)

            # Move the file to the new directory
            shutil.move(current_file, new_file)
            print(f'FILE: {check_file} >>> GOTO: {name_band_folder}/{name_band}/{new_filename}')


if __name__ == "__main__":
    main()
