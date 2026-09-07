import sqlite3
import json
import os
from typing import List

# ================= CONSTANTS & VARIABLES =================
ROOT_FOLDER: str = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
DB_FOLDER: str = os.path.join(ROOT_FOLDER, 'Website/Databases/')
DB_BACKUP_FOLDER: str = DB_FOLDER  # Backups are saved directly in Website/Databases folder
DB_FILE: str = os.path.join(DB_FOLDER, 'music_releases.db')
TABLES: List[str] = ['artists', 'my_releases', 'new_releases', 'soon_releases']


def export_database() -> None:
    """
    Export all tables from the SQLite database to JSON files.
    
    Each table is exported to a separate JSON file in the backup folder.
    """
    # Check if database file exists
    if not os.path.exists(DB_FILE):
        print(f"Error: Database '{DB_FILE}' not found in current folder.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print(f"Starting export from {DB_FILE}...\n")

    for table in TABLES:
        json_filename = os.path.join(DB_BACKUP_FOLDER, f"{table}.json")

        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]

            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"[{table}] Exported {len(data)} records to '{table}.json'")

        except sqlite3.Error as e:
            print(f"[{table}] SQL error: {e}\n")
        except Exception as e:
            print(f"[{table}] Unexpected error: {e}\n")

    conn.close()
    print("Export completed!")


if __name__ == "__main__":
    export_database()
