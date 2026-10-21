from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os
import time
import json

# Variabel global buat nyimpen data bot
bot_instance = None
start_time = time.time()

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Ambil data server
        servers_html = ""
        total_members = 0
        total_servers = 0
        
        if bot_instance and bot_instance.is_ready():
            total_servers = len(bot_instance.guilds)
            for guild in bot_instance.guilds:
                total_members += guild.member_count
                servers_html += f"""
                <div class="server-card">
                    <div class="server-icon">🛡️</div>
                    <div class="server-info">
                        <h3>{guild.name}</h3>
                        <p>{guild.member_count:,} Members</p>
                    </div>
                </div>
                """
                
            ping = round(bot_instance.latency * 1000)
        else:
            servers_html = "<p class='text-muted'>Bot sedang memuat data atau offline...</p>"
            ping = 0
            
        # 2. Hitung Uptime
        uptime_sec = int(time.time() - start_time)
        hours, remainder = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # 3. HTML Dashboard
        HTML = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Cártel System | Dashboard</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #09090b;
                    --card-bg: #18181b;
                    --border: #27272a;
                    --text: #e4e4e7;
                    --text-muted: #a1a1aa;
                    --red: #ef4444;
                    --green: #22c55e;
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background-color: var(--bg);
                    color: var(--text);
                    font-family: 'Inter', sans-serif;
                    line-height: 1.5;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                }}
                .header {{
                    border-bottom: 1px solid var(--border);
                    padding: 20px 40px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: rgba(9, 9, 11, 0.8);
                    backdrop-filter: blur(10px);
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }}
                .brand {{
                    font-family: 'JetBrains Mono', monospace;
                    font-weight: 700;
                    font-size: 1.2rem;
                    color: var(--text);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .brand span {{ color: var(--red); }}
                .status-badge {{
                    background: rgba(34, 197, 94, 0.1);
                    color: var(--green);
                    padding: 6px 12px;
                    border-radius: 99px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    border: 1px solid rgba(34, 197, 94, 0.2);
                }}
                .status-dot {{
                    width: 8px; height: 8px;
                    background: var(--green);
                    border-radius: 50%;
                    box-shadow: 0 0 10px var(--green);
                    animation: pulse 2s infinite;
                }}
                @keyframes pulse {{
                    0% {{ opacity: 1; }}
                    50% {{ opacity: 0.5; }}
                    100% {{ opacity: 1; }}
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 40px 20px;
                    width: 100%;
                    flex: 1;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                .stat-card {{
                    background: var(--card-bg);
                    border: 1px solid var(--border);
                    padding: 24px;
                    border-radius: 12px;
                    text-align: center;
                }}
                .stat-value {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 2rem;
                    font-weight: 700;
                    color: var(--text);
                    margin-bottom: 5px;
                }}
                .stat-label {{
                    color: var(--text-muted);
                    font-size: 0.85rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                h2 {{
                    font-size: 1.5rem;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .server-list {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 15px;
                }}
                .server-card {{
                    background: var(--card-bg);
                    border: 1px solid var(--border);
                    padding: 16px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    transition: all 0.2s;
                }}
                .server-card:hover {{
                    border-color: var(--red);
                    transform: translateY(-2px);
                }}
                .server-icon {{
                    font-size: 1.5rem;
                    background: rgba(239, 68, 68, 0.1);
                    padding: 10px;
                    border-radius: 8px;
                }}
                .server-info h3 {{
                    font-size: 1rem;
                    margin-bottom: 4px;
                    color: var(--text);
                }}
                .server-info p {{
                    font-size: 0.8rem;
                    color: var(--text-muted);
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: var(--text-muted);
                    font-size: 0.8rem;
                    border-top: 1px solid var(--border);
                    font-family: 'JetBrains Mono', monospace;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="brand">
                    <span>🩸</span> CÁRTEL SYSTEM
                </div>
                <div class="status-badge">
                    <div class="status-dot"></div> OPERATIONAL
                </div>
            </div>

            <div class="container">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{total_servers}</div>
                        <div class="stat-label">Servers Connected</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{total_members:,}</div>
                        <div class="stat-label">Total Members</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{ping} ms</div>
                        <div class="stat-label">API Latency</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{uptime_str}</div>
                        <div class="stat-label">System Uptime</div>
                    </div>
                </div>

                <h2>🌐 Active Networks</h2>
                <div class="server-list">
                    {servers_html}
                </div>
            </div>

            <div class="footer">
                "El que se va, nunca vuelve." • Protected by Cártel de Jalisco
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML.encode('utf-8'))

    def log_message(self, *args):
        pass

def _run_server():
    port = int(os.environ.get("PORT", 11963))
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"[keep_alive] Dashboard jalan di 0.0.0.0:{port}")
    server.serve_forever()

def keep_alive(bot):
    global bot_instance
    bot_instance = bot
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
