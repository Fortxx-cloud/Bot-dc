from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, *args):
        pass # Matikan log biar gak spam di console

def _run_server():
    # Wispbyte ngeset port ke 11963 buat subdomain
    port = int(os.environ.get("PORT", 11963))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"[keep_alive] Web server jalan di 0.0.0.0:{port}")
    server.serve_forever()

def keep_alive():
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
