""" 
AMR Functions Module - Common utilities for Alternative & Metal Releases scripts

Usage:
    import amr_functions as amr
    
    amr.print_name(SCRIPT_NAME, VERSION)
    amr.mdv2(text_line)
    amr.send_message(text, token, chat_id, image, topic)
    amr.logger(log_line, log_file, script_name, *args)
    amr.db_backup(db_file)
"""

import datetime
import json
import os
from typing import Optional, Dict, List, Any

# Lazy import for requests to avoid overhead when not used
_requests = None
_sqlite3 = None


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


THREAD_ID_DICT: Dict[str, int] = {
    'New Updates': 6, 
    'Top Releases': 10, 
    'Coming Soon': 3, 
    'New Releases': 2, 
    'Next Week Releases': 80, 
    'General': 0
}

TABLES: List[str] = ['artists', 'my_releases', 'new_releases', 'soon_releases']


def print_name(script_name: str, version: str) -> None:
    """Print formatted script header with name and version."""
    print_line = f'{script_name} v.{version}'
    print_line_len = 30
    if len(print_line) > 28:
        print_line_len = len(print_line) + 2
    print(f"\n{'':{'='}^{print_line_len}}")
    print(f"{'\033[1m'}{'Alternative & Metal Releases':{' '}^{print_line_len}}{'\033[0m'}")
    print(f"{print_line:{' '}^{print_line_len}}")
    print(f"{'':{'='}^{print_line_len}}\n")


def mdv2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.
    Already escaped characters are not re-escaped.
    
    Args:
        text: Raw text to escape
        
    Returns:
        Escaped text safe for Telegram MarkdownV2
    """
    SPECIAL = '_*[]()~`>#+-=|{}.!'
    
    def escape_special(s: str) -> str:
        """Escape special characters, except already escaped ones."""
        result = []
        for i, c in enumerate(s):
            if c in SPECIAL and (i == 0 or s[i-1] != '\\'):
                result.append('\\' + c)
            else:
                result.append(c)
        return ''.join(result)
    
    result = []
    i = 0
    is_bold_link = False

    while i < len(text):
        # Code block: `...` — preserve as-is, no escaping
        if text[i] == '`':
            end = text.find('`', i + 1)
            if end != -1:
                result.append(text[i:end+1])
                i = end + 1
                continue
        
        # Link: [text](url) — escape content but not structural brackets
        if text[i] == '[':
            bracket_end = text.find(']', i + 1)
            if bracket_end != -1 and bracket_end + 1 < len(text) and text[bracket_end+1] == '(':
                paren_end = text.find(')', bracket_end + 2)
                if paren_end != -1:
                    link_text = text[i+1:bracket_end]
                    url = text[bracket_end+2:paren_end]
                    if is_bold_link:
                        result.append(f'*[{escape_special(link_text)}]({escape_special(url)})*')
                        is_bold_link = False
                        i = paren_end + 2
                    else:
                        result.append(f'[{escape_special(link_text)}]({escape_special(url)})')
                        i = paren_end + 1
                    continue
        
        # Bold/italic/strike: *...*, _..._, ~...~ — escape content inside
        if text[i] in '*_~':
            marker = text[i]
            end = text.find(marker, i + 1)
            if end != -1:
                content = text[i+1:end]
                if content[0] != '[' and content[len(content)-1] != ')':
                    result.append(f'{marker}{escape_special(content)}{marker}')
                    i = end + 1
                else:
                    is_bold_link = True
                    i += 1
                continue
        
        # Regular character: escape if special and not already escaped
        c = text[i]
        if c in SPECIAL and (i == 0 or text[i-1] != '\\'):
            result.append('\\' + c)
        else:
            result.append(c)
        i += 1
    
    return ''.join(result)


def send_message(
    text: str, 
    token: str, 
    chat_id: str, 
    image: Optional[str], 
    topic: Optional[str]
) -> Optional[int]:
    """
    Send message to Telegram with error handling and debug output.
    
    Args:
        text: Message text (will be escaped for MarkdownV2)
        token: Telegram bot token
        chat_id: Target chat ID
        image: Optional image URL for photo messages
        topic: Optional topic name for threaded messages
        
    Returns:
        Message ID if successful, None otherwise
    """
    requests = _get_requests()
    escaped_text = mdv2(text)

    send_method = 'sendMessage'
    data_arguments = {
        "text": escaped_text,
        "chat_id": chat_id,
        "parse_mode": 'MarkdownV2'
    }
    
    if image:
        send_method = 'sendPhoto'
        data_arguments.update({"photo": image, "caption": escaped_text})
    
    if topic:
        data_arguments.update({"message_thread_id": THREAD_ID_DICT[topic]})
    
    url = f"https://api.telegram.org/bot{token}/{send_method}"

    try:
        response = requests.post(url, data=data_arguments)
        json_response = json.loads(response.text)
        return json_response['result']['message_id']
        
    except KeyError:
        print(f"🔍 Telegram API error response: {response.text}")
        print("❌ Ошибка отправки сообщения")
        
    except TypeError:
        print(f"🔍 Telegram API unexpected response: {response.text}")
        print("❌ Ошибка отправки сообщения (некорректный формат ответа)")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети при отправке: {e}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON-ответа: {e}")
        print(f"🔍 Сырой ответ: {response.text if 'response' in locals() else 'N/A'}")    

    print(f"📄 Отправляемый текст: {escaped_text}")
    print('')
    
    # Try to send error notification
    try:
        logger_chat_id = os.environ.get('tg_logger_id', '')
        if logger_chat_id:
            error_msg = "Ошибка: сообщение отправить не удалось!"
            error_url = f"https://api.telegram.org/bot{token}/sendMessage"
            error_data = {"chat_id": logger_chat_id, "text": error_msg}
            requests.post(error_url, data=error_data, timeout=10)
    except Exception:
        print("⚠️ Не удалось отправить уведомление об ошибке")

    return None


def logger(
    log_line: str, 
    log_file: str, 
    script_name: str, 
    *args: str
) -> None:
    """
    Write log line to log file.
    
    For GitHub Actions:
      - Add +3 hours to datetime
    
    For Local scripts:
      - Print() without '▲','▼' and leading spaces
      - Additional conditions for print() without logging
      
    Args:
        log_line: Log message content
        log_file: Path to log file
        script_name: Name of the script for log prefix
        *args: Optional flags (e.g., 'noprint' to suppress console output)
    """
    if log_line[0] not in ['▲', '▼']:
        log_line = f'  {log_line}'
    
    is_github = os.getenv("GITHUB_ACTIONS") == "true"
    should_print = 'noprint' not in args
    
    with open(log_file, 'r+') as file:
        log_file_content = file.read()
        file.seek(0, 0)
        log_date = datetime.datetime.now()
        
        if is_github:
            log_date = log_date + datetime.timedelta(hours=3)
            
        file.write(
            f'{log_date.strftime("%Y-%m-%d %H:%M:%S")} '
            f'[{script_name}] {log_line.rstrip(chr(13) + chr(10))}\n'
            f'{log_file_content}'
        )
    
    # Print for Local scripts only, if there's no 'noprint' parameter
    if not is_github and should_print:
        print(log_line[2:])


def db_backup(db_file: str) -> None:
    """
    Backup database tables to JSON files.
    
    Args:
        db_file: Path to SQLite database file
    """
    sqlite3 = _get_sqlite3()
    db_path, db_name = os.path.split(db_file)
    db_backup_folder = os.path.join(db_path, 'Backups/')

    print('')
    if not os.path.exists(db_file):
        print(f"Ошибка: база данных '{db_name}' не найдена в папке '{db_path}'.")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for table in TABLES:
        json_filename = os.path.join(db_backup_folder, f"{table}.json")

        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]

            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"[{table}] Экспортировано {len(data)} записей в '{table}.json'")

        except sqlite3.Error as e:
            print(f"[{table}] Ошибка при работе с таблицей: {e}\n")
        except Exception as e:
            print(f"[{table}] Непредвиденная ошибка: {e}\n")

    conn.close()
    print('')
