"""Server HTTP kecil biar Render gak tidur."""
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
        pass  # matikan log biar gak spam

def _run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"[keep_alive] Server jalan di port {port}")
    server.serve_forever()

def keep_alive():
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
