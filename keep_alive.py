from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os
import time

# Variabel global buat nyimpen data bot
bot_instance = None
start_time = time.time()

INVITE_LINK = "https://discord.gg/fYMu3msZ"

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        servers_html = ""
        total_members = 0
        total_servers = 0
        
        if bot_instance and bot_instance.is_ready():
            total_servers = len(bot_instance.guilds)
            for guild in bot_instance.guilds:
                total_members += guild.member_count
                icon_url = guild.icon.url if guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png"
                servers_html += f"""
                <div class="server-card">
                    <img src="{icon_url}" class="server-icon" alt="icon">
                    <div class="server-info">
                        <h3>{guild.name}</h3>
                        <p>{guild.member_count:,} Operatives</p>
                    </div>
                </div>
                """
            ping = round(bot_instance.latency * 1000)
        else:
            servers_html = "<div class='loading'>Menghubungkan ke satelit Cártel...</div>"
            ping = 0
            
        uptime_sec = int(time.time() - start_time)
        hours, remainder = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        HTML = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Cártel de Jalisco | Mainframe</title>
            <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #050505;
                    --card: #111111;
                    --border: #2a0000;
                    --text: #e0e0e0;
                    --red: #ff1a1a;
                    --dark-red: #8a0000;
                    --gold: #d4af37;
                    --green: #00ff00;
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background-color: var(--bg);
                    background-image: radial-gradient(circle at 50% 0%, #1a0000 0%, #050505 60%);
                    color: var(--text);
                    font-family: 'Inter', sans-serif;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                }}
                .top-bar {{
                    border-bottom: 1px solid var(--border);
                    padding: 20px 40px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: rgba(5, 5, 5, 0.9);
                    backdrop-filter: blur(10px);
                }}
                .brand {{
                    font-family: 'Cinzel', serif;
                    font-size: 1.5rem;
                    font-weight: 900;
                    letter-spacing: 2px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .brand span {{ color: var(--red); font-size: 1.8rem; }}
                .status-badge {{
                    border: 1px solid var(--green);
                    color: var(--green);
                    padding: 6px 16px;
                    border-radius: 4px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.8rem;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
                }}
                .dot {{
                    width: 8px; height: 8px;
                    background: var(--green);
                    border-radius: 50%;
                    animation: pulse 1.5s infinite;
                }}
                @keyframes pulse {{
                    0% {{ opacity: 1; box-shadow: 0 0 10px var(--green); }}
                    50% {{ opacity: 0.4; }}
                    100% {{ opacity: 1; box-shadow: 0 0 10px var(--green); }}
                }}
                .hero {{
                    text-align: center;
                    padding: 60px 20px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .hero h1 {{
                    font-family: 'Cinzel', serif;
                    font-size: 3rem;
                    color: var(--red);
                    text-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
                    margin-bottom: 10px;
                }}
                .hero p {{
                    color: #a0a0a0;
                    font-size: 1.1rem;
                    margin-bottom: 40px;
                    font-style: italic;
                }}
                .join-btn {{
                    display: inline-block;
                    background: linear-gradient(45deg, var(--dark-red), var(--red));
                    color: white;
                    text-decoration: none;
                    padding: 15px 40px;
                    border-radius: 4px;
                    font-weight: 600;
                    letter-spacing: 2px;
                    transition: all 0.3s;
                    border: 1px solid #ff6666;
                }}
                .join-btn:hover {{
                    transform: scale(1.05);
                    box-shadow: 0 0 25px rgba(255, 0, 0, 0.6);
                }}
                .container {{
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 0 20px 60px;
                    width: 100%;
                    flex: 1;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin-bottom: 40px;
                }}
                @media (max-width: 768px) {{
                    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
                    .hero h1 {{ font-size: 2rem; }}
                }}
                .stat-box {{
                    background: var(--card);
                    border-left: 3px solid var(--red);
                    padding: 20px;
                    text-align: center;
                    border-top: 1px solid var(--border);
                    border-right: 1px solid var(--border);
                    border-bottom: 1px solid var(--border);
                }}
                .stat-val {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 1.8rem;
                    color: var(--gold);
                    margin-bottom: 5px;
                }}
                .stat-lbl {{
                    font-size: 0.75rem;
                    color: #888;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .section-title {{
                    font-family: 'Cinzel', serif;
                    font-size: 1.2rem;
                    color: var(--text);
                    border-bottom: 1px solid var(--border);
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .server-list {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 15px;
                }}
                .server-card {{
                    background: var(--card);
                    border: 1px solid #222;
                    padding: 15px;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    transition: 0.2s;
                }}
                .server-card:hover {{
                    border-color: var(--red);
                    background: #1a0505;
                }}
                .server-icon {{
                    width: 45px;
                    height: 45px;
                    border-radius: 50%;
                    background: #000;
                }}
                .server-info h3 {{
                    font-size: 1rem;
                    color: var(--text);
                    margin-bottom: 3px;
                }}
                .server-info p {{
                    font-size: 0.8rem;
                    color: var(--red);
                    font-family: 'JetBrains Mono', monospace;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    border-top: 1px solid var(--border);
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.8rem;
                    color: #666;
                    background: #000;
                }}
            </style>
        </head>
        <body>
            <div class="top-bar">
                <div class="brand">
                    <span>🩸</span> CÁRTEL MAINFRAME
                </div>
                <div class="status-badge">
                    <div class="dot"></div> SECURE CONNECTION
                </div>
            </div>

            <div class="hero">
                <h1>Cártel de Jalisco</h1>
                <p>"El que se va, nunca vuelve."</p>
                <a href="{INVITE_LINK}" target="_blank" class="join-btn">JOIN THE FAMILIA</a>
            </div>

            <div class="container">
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-val">{total_servers}</div>
                        <div class="stat-lbl">Networks</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-val">{total_members:,}</div>
                        <div class="stat-lbl">Operatives</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-val">{ping}ms</div>
                        <div class="stat-lbl">Latency</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-val">{uptime_str}</div>
                        <div class="stat-lbl">Uptime</div>
                    </div>
                </div>

                <div class="section-title">
                    <span>🌐</span> CONNECTED NETWORKS
                </div>
                <div class="server-list">
                    {servers_html}
                </div>
            </div>

            <div class="footer">
                Cártel de Jalisco Nueva Generación © 2026 | Bot Infrastructure System
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
    print(f"[keep_alive] Mainframe jalan di 0.0.0.0:{port}")
    server.serve_forever()

def keep_alive(bot):
    global bot_instance
    bot_instance = bot
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
