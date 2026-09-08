import datetime
import os
from typing import Optional, Dict, Any, List

# Lazy imports to reduce startup time
_requests = None
_sqlite3 = None
_traceback = None


def _get_requests():
    global _requests
    if _requests is None:
        import requests
        _requests = requests
    return _requests


def _get_sqlite3():
    global _sqlite3
    if _sqlite3 is None:
        import sqlite3
        _sqlite3 = sqlite3
    return _sqlite3


def _get_traceback():
    global _traceback
    if _traceback is None:
        import traceback
        _traceback = traceback
    return _traceback


import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME: str = "Covers Downloader"
VERSION: str = "2.026.07"

ROOT_FOLDER: str = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
DB_FOLDER: str = os.path.join(ROOT_FOLDER, 'Databases/')
DB_FILE: str = os.path.join(DB_FOLDER, 'music_releases.db')
COVERS_FOLDER: str = os.path.join(ROOT_FOLDER, 'Covers/Fresh Covers to Check/')


def clean_folder_name(text: str) -> str:
    """
    Clean a text string for use as a folder name.
    
    Removes or replaces forbidden characters ((),/:.) and normalizes whitespace.
    
    Args:
        text: The text to clean.
    
    Returns:
        A cleaned string suitable for use as a folder name.
    """
    forbidden = set('()/:.')
    result: List[str] = []
    
    # Iterate through the text to process forbidden characters
    for i, char in enumerate(text):
        if char in forbidden:
            left = text[i-1] if i > 0 else None
            right = text[i+1] if i < len(text) - 1 else None
            # Replace with space only if surrounded by non-spaces on both sides
            if left is not None and right is not None and left != ' ' and right != ' ':
                result.append(' ')
            # Otherwise, the character is simply removed
        else:
            result.append(char)
    
    # Join the result, collapse multiple spaces into one, and trim edges
    return ' '.join(''.join(result).split())


def is_jp_chars(text: str) -> bool:
    """
    Check if a text contains Japanese characters.
    
    Args:
        text: The text to check.
    
    Returns:
        True if Japanese characters are found, False otherwise.
    """
    return any(
        0x3040 <= ord(ch) <= 0x309F or   # Hiragana
        0x30A0 <= ord(ch) <= 0x30FF or   # Katakana
        0x4E00 <= ord(ch) <= 0x9FFF      # Kanji (CJK Unified Ideographs)
        for ch in text
    )


def replace_symbols(text_line: str) -> str:
    """
    Replace symbols that are invalid in file names and folder paths.
    
    Args:
        text_line: The text to process.
    
    Returns:
        The text with invalid symbols replaced by underscores.
    """
    symbols_to_replace = '\\/*:?<>|`"'
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, '_')
    return text_line


def image_download(file_name: str, folder: str, link: str) -> None:
    """
    Download an image from a URL and save it to a specified folder.
    
    Args:
        file_name: The base name for the saved file.
        folder: The subfolder within COVERS_FOLDER to save the file.
        link: The URL of the image to download.
    """
    requests = _get_requests()
    file_name = replace_symbols(file_name)
    folder = replace_symbols(folder)
    folder_path = os.path.join(COVERS_FOLDER, folder)

    os.makedirs(folder_path, exist_ok=True)

    response = requests.get(link)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"{file_name}.jpg"), "wb") as file:
            file.write(response.content)
    else:
        with open(os.path.join(folder_path, f"{file_name}.txt"), "wb") as file:
            file.write(response.content)


def count_covers_to_download() -> Optional[int]:
    """
    Count the number of covers remaining to download.
    
    Returns:
        The count of covers to download, or None if an error occurs.
    """
    sqlite3 = _get_sqlite3()
    traceback = _get_traceback()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(row_id) FROM my_releases 
            WHERE cover_download_date IS NULL
        ''')
        result = cursor.fetchone()
        conn.close()
        if result:
            return int(result[0])
        return None
    except Exception as e:
        print(f'Error counting covers to download: {e}')
        traceback.print_exc()
        return None


def get_cover_to_download() -> Optional[Dict[str, Any]]:
    """
    Get the next cover record to download from the database.
    
    Returns:
        A dictionary with cover information, or None if no covers remain or an error occurs.
    """
    sqlite3 = _get_sqlite3()
    traceback = _get_traceback()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT row_id, main_artist, artist, album, release_date, cover_link  
            FROM my_releases 
            WHERE cover_download_date IS NULL
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                'row_id': result[0],
                'main_artist': result[1],
                'artist': result[2],
                'album': result[3],
                'release_date': result[4],
                'cover_link': result[5]
            }
        return None
    except Exception as e:
        print(f'Error getting cover to download: {e}')
        traceback.print_exc()
        return None


def update_cover_downloaded(row_id: int, date_of_update: str) -> bool:
    """
    Update the cover download date for a release record.
    
    Args:
        row_id: The row ID of the release to update.
        date_of_update: The date/time string to store.
    
    Returns:
        True if successful, False otherwise.
    """
    sqlite3 = _get_sqlite3()
    traceback = _get_traceback()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE my_releases SET cover_download_date = ? WHERE row_id = ?',
                       (date_of_update, row_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating cover download date: {e}')
        traceback.print_exc()
        return False


def main() -> None:
    """Main entry point for the Covers Downloader script."""
    amr.print_name(SCRIPT_NAME, VERSION)

    requests = _get_requests()
    session = requests.Session() 
    session.headers.update({
        'Referer': 'https://itunes.apple.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    })

    while True:
        covers_count = count_covers_to_download()
        cover_to_download = get_cover_to_download()
        
        if not cover_to_download:
            print("\nAll covers downloaded, nothing left to download...")
            break

        row_id = int(cover_to_download['row_id'])

        # Clean artist name for folder (remove forbidden characters: /, :, (, ), . at end)
        artist_folder_name = clean_folder_name(str(cover_to_download['main_artist']))
        
        # Check for Japanese characters. If found, use the uncleaned main_artist
        non_JP_artist_name = str(cover_to_download['artist'])
        if is_jp_chars(non_JP_artist_name):
            non_JP_artist_name = str(cover_to_download['main_artist'])

        image_download(
            f"{non_JP_artist_name} - "
            f"{str(cover_to_download['album'])[:100]} - "
            f"{str(cover_to_download['release_date'])} [{row_id}]",
            artist_folder_name,
            str(cover_to_download['cover_link'])
        )
        
        print(f"ID: {row_id}. {str(cover_to_download['main_artist'])} | "
              f"{str(cover_to_download['artist'])} - "
              f"{str(cover_to_download['album'])} - "
              f"{str(cover_to_download['release_date'])}. "
              f"(Covers left: {covers_count - 1})")

        date_of_update = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not update_cover_downloaded(row_id, date_of_update):
            print(f'\n✗ Failed to update progress for cover № {row_id}')

    amr.db_backup(DB_FILE)

    print("\nDONE")


if __name__ == "__main__":
    main()
