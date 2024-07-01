import logging
import urllib.parse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import mimetypes
import socket
import json
import threading
from datetime import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path()
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)
DATA_FILE = STORAGE_DIR / "data.json"

SOCKET_ADDRESS = ('localhost', 5000)

class GoitFramework(BaseHTTPRequestHandler):

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case '/error':
                self.send_html('error.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html(filename= 'error.html', status_code= '404')


    def do_POST(self):
        route = urllib.parse.urlparse(self.path)
        if route.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = urllib.parse.parse_qs(post_data)

            # Подготовка данных для отправки на сокет-сервер
            message_data = {
                "username": data.get("username", [""])[0],
                "message": data.get("message", [""])[0]
            }

            # Отправка данных на сокет-сервер
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(json.dumps(message_data).encode('utf-8'), SOCKET_ADDRESS)

            # Ответ клиенту
            self.send_html('message.html')
        else:
            self.send_html(filename='error.html', status_code=404)



    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header(keyword= 'Content-Type', value= 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header(keyword= 'Content-Type', value=mime_type)
        else:
            self.send_header(keyword='Content-Type', value='text/plain')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

def run_server():
    address = ('localhost', 3000)
    http_server = HTTPServer(address, GoitFramework)
    try:
        logger.info("HTTP server running on http://localhost:3000")
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http_server.server_close()

def run_socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(SOCKET_ADDRESS)
        logger.info(f"Socket server running on udp://{SOCKET_ADDRESS[0]}:{SOCKET_ADDRESS[1]}")
        while True:
            message, _ = server_socket.recvfrom(1024)
            data = json.loads(message.decode('utf-8'))
            timestamp = datetime.now().isoformat()
            if DATA_FILE.exists():
                with open(DATA_FILE, 'r', encoding='utf-8') as file:
                    stored_data = json.load(file)
            else:
                stored_data = {}
            stored_data[timestamp] = data
            with open(DATA_FILE, 'w', encoding='utf-8') as file:
                json.dump(stored_data, file, ensure_ascii=False, indent=4)

def main():
    http_thread = threading.Thread(target=run_server)
    socket_thread = threading.Thread(target=run_socket_server)
    http_thread.start()
    socket_thread.start()
    http_thread.join()
    socket_thread.join()


if __name__ == '__main__':
    main()