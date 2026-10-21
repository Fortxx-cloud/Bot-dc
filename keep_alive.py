from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os
import time

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
                <a href="{INVITE_LINK}" target="_blank" class="server-card">
                    <img src="{icon_url}" class="srv-icon" alt="icon">
                    <div class="srv-info">
                        <span class="srv-name">{guild.name}</span>
                        <span class="srv-members">{guild.member_count:,} OPERATIVES</span>
                    </div>
                    <span class="srv-btn">JOIN &rarr;</span>
                </a>
                """
            ping = round(bot_instance.latency * 1000)
        else:
            servers_html = "<div class='loading'>ESTABLISHING SECURE UPLINK...</div>"
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
            <title>FORTXX SYSTEM | Dashboard</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&family=Cinzel:wght@700&display=swap" rel="stylesheet">
            <style>
                :root {{ --bg: #09090b; --card: #121214; --border: #27272a; --text: #e4e4e7; --muted: #a1a1aa; --red: #ef4444; --gold: #eab308; --green: #22c55e; }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ background-color: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; display: flex; flex-direction: column; }}
                .nav {{ padding: 15px 30px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: rgba(9, 9, 11, 0.8); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 10; }}
                .brand {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1rem; color: var(--text); display: flex; align-items: center; gap: 8px; }}
                .brand span {{ color: var(--red); }}
                .status {{ display: flex; align-items: center; gap: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--green); padding: 4px 10px; background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 4px; }}
                .dot {{ width: 6px; height: 6px; background: var(--green); border-radius: 50%; box-shadow: 0 0 8px var(--green); }}
                .hero {{ padding: 50px 20px; text-align: center; }}
                .hero h1 {{ font-family: 'JetBrains Mono', monospace; font-size: 2.5rem; font-weight: 800; color: #fff; letter-spacing: -1px; margin-bottom: 10px; }}
                .hero h1 span {{ color: var(--red); }}
                .owner {{ display: inline-flex; align-items: center; gap: 8px; background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3); padding: 6px 16px; border-radius: 99px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--gold); margin-bottom: 15px; }}
                .owner b {{ color: #fff; }}
                .hero p {{ color: var(--muted); font-family: 'Cinzel', serif; font-style: italic; font-size: 1rem; }}
                .container {{ max-width: 900px; margin: 0 auto; padding: 0 20px 50px; width: 100%; flex: 1; }}
                .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 30px; }}
                @media (min-width: 600px) {{ .stats {{ grid-template-columns: repeat(4, 1fr); }} }}
                .stat-box {{ background: var(--card); border: 1px solid var(--border); padding: 15px; border-radius: 8px; text-align: center; }}
                .stat-val {{ font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; font-weight: 700; color: var(--gold); margin-bottom: 4px; }}
                .stat-lbl {{ font-size: 0.65rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }}
                .section-title {{ font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: var(--text); margin-bottom: 15px; display: flex; align-items: center; gap: 8px; text-transform: uppercase; }}
                .section-title span {{ color: var(--red); }}
                .server-list {{ display: flex; flex-direction: column; gap: 10px; }}
                .server-card {{ display: flex; align-items: center; gap: 15px; background: var(--card); border: 1px solid var(--border); padding: 15px; border-radius: 8px; text-decoration: none; color: var(--text); transition: all 0.2s; cursor: pointer; }}
                .server-card:hover {{ border-color: var(--red); background: rgba(239, 68, 68, 0.05); transform: translateY(-2px); }}
                .srv-icon {{ width: 45px; height: 45px; border-radius: 50%; border: 1px solid var(--border); }}
                .srv-info {{ display: flex; flex-direction: column; flex: 1; }}
                .srv-name {{ font-weight: 600; font-size: 1rem; }}
                .srv-members {{ font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--muted); margin-top: 2px; }}
                .srv-btn {{ font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 700; color: var(--red); padding: 6px 12px; border: 1px solid var(--red); border-radius: 4px; }}
                .server-card:hover .srv-btn {{ background: var(--red); color: #fff; }}
                .loading {{ font-family: 'JetBrains Mono', monospace; color: var(--red); text-align: center; padding: 20px; }}
                .footer {{ text-align: center; padding: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #555; border-top: 1px solid var(--border); }}
            </style>
        </head>
        <body>
            <nav class="nav">
                <div class="brand"><span>&#129656;</span> FORTXX SYSTEM</div>
                <div class="status"><div class="dot"></div> ONLINE</div>
            </nav>
            <div class="hero">
                <h1>FORTXX<span>.</span>BOT</h1>
                <div class="owner">&#128081; EL JEFE: <b>@zomahaci</b></div>
                <p>"La Familia es todo."</p>
            </div>
            <div class="container">
                <div class="stats">
                    <div class="stat-box"><div class="stat-val">{total_servers}</div><div class="stat-lbl">Networks</div></div>
                    <div class="stat-box"><div class="stat-val">{total_members:,}</div><div class="stat-lbl">Operatives</div></div>
                    <div class="stat-box"><div class="stat-val">{ping}ms</div><div class="stat-lbl">Latency</div></div>
                    <div class="stat-box"><div class="stat-val">{uptime_str}</div><div class="stat-lbl">Uptime</div></div>
                </div>
                <div class="section-title"><span>&#127760;</span> Connected Networks</div>
                <div class="server-list">
                    {servers_html}
                </div>
            </div>
            <div class="footer">
                FORTXX SYSTEM &copy; 2026 | POWERED BY @zomahaci
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
    print(f"[keep_alive] Server jalan di 0.0.0.0:{port}")
    server.serve_forever()

def keep_alive(bot):
    global bot_instance
    bot_instance = bot
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
