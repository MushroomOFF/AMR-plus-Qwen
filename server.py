#!/usr/bin/env python3
"""
Сервер для страницы музыкальных релизов (только для локальной разработки).
В продакшене (на GitHub Pages) вместо него работает GitHub API — см. releases.js.

Структура проекта:
    server.py                 <- этот файл (в корне)
    website/releases.html
    website/releases.css
    website/releases.js
    website/new_releases.json

Запуск: python server.py   (из корня проекта)
Адрес:  http://localhost:8000/releases.html
"""
import http.server
import socketserver
import json
import os
import sys
import urllib.parse
from datetime import datetime

PORT = 8000
WEBSITE_DIR = 'website'                 # папка с файлами сайта
HTML_FILE = 'releases.html'             # относительно WEBSITE_DIR
JSON_FILE = os.path.join(WEBSITE_DIR, 'new_releases.json')  # относительно корня

ADMIN_LOGIN = os.environ.get('ADMIN_LOGIN', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin2026')


class Handler(http.server.SimpleHTTPRequestHandler):
    # Раздаём файлы из папки website
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBSITE_DIR, **kwargs)

    def do_GET(self):
        if self.path in ('/', ''):
            self.send_response(302)
            self.send_header('Location', f'/{HTML_FILE}')
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/verify':
            self.handle_verify()
        elif parsed.path == '/api/update_my_type':
            self.handle_update_my_type()
        else:
            self.send_error(404)

    def handle_verify(self):
        try:
            data = self.read_body()
            login = data.get('login', '')
            password = data.get('password', '')
            ok = (login == ADMIN_LOGIN and password == ADMIN_PASSWORD)
            self.send_json(
                {'success': ok, 'message': 'OK' if ok else 'Неверный логин или пароль'},
                200 if ok else 403
            )
        except Exception as e:
            self.send_json({'success': False, 'message': str(e)}, 400)

    def handle_update_my_type(self):
        try:
            data = self.read_body()
            login = data.get('login', '')
            password = data.get('password', '')
            row_id = data.get('row_id')
            new_type = data.get('new_type', '').strip()

            if login != ADMIN_LOGIN or password != ADMIN_PASSWORD:
                self.send_json({'success': False, 'message': 'Неверный логин или пароль'}, 403)
                return

            if row_id is None or new_type not in ('v', 'd', 'o', 'x'):
                self.send_json({'success': False, 'message': 'Некорректные данные'}, 400)
                return

            if not os.path.exists(JSON_FILE):
                self.send_json({'success': False, 'message': 'JSON не найден'}, 404)
                return

            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                releases = json.load(f)

            updated = 0
            old_type = None
            for r in releases:
                rid = r.get('row_id') if 'row_id' in r else r.get('row_id ')
                if str(rid) == str(row_id):
                    old_type = r.get('my_type') or r.get('my_type ')
                    # Обновляем оба варианта ключа (из-за бага с пробелами)
                    if 'my_type' in r:
                        r['my_type'] = new_type
                    if 'my_type ' in r:
                        r['my_type '] = new_type
                    updated += 1

            if updated == 0:
                self.send_json({'success': False, 'message': f'row_id={row_id} не найден'}, 404)
                return

            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(releases, f, ensure_ascii=False, indent=1)

            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] ✅ row_id={row_id}: '{old_type}' → '{new_type}' ({updated} записей)")

            self.send_json({
                'success': True,
                'message': f'Обновлено: {updated} записей',
                'old_type': old_type,
                'new_type': new_type
            })
        except Exception as e:
            self.send_json({'success': False, 'message': f'Ошибка: {e}'}, 500)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length).decode('utf-8'))

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} - {fmt % args}")


def main():
    print("=" * 60)
    print("🎵 AMR Server — локальная разработка")
    print("=" * 60)
    print(f"📁 Сайт:    {os.path.abspath(WEBSITE_DIR)}")
    print(f"📄 JSON:    {os.path.abspath(JSON_FILE)}")
    print(f"🌐 Страница: http://localhost:{PORT}/{HTML_FILE}")
    print(f"👤 Логин:   {ADMIN_LOGIN}")
    print(f"🔑 Пароль:  {ADMIN_PASSWORD}")
    print("=" * 60)

    if not os.path.isdir(WEBSITE_DIR):
        print(f"❌ ОШИБКА: папка '{WEBSITE_DIR}' не найдена!")
        print("   Запускайте сервер из корня проекта.")
        sys.exit(1)

    if not os.path.exists(JSON_FILE):
        print(f"❌ ВНИМАНИЕ: {JSON_FILE} не найден!")

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Остановлено.")


if __name__ == '__main__':
    main()