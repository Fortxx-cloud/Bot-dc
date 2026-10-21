from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
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
                servers_html += f'''
                <a href="{INVITE_LINK}" target="_blank" class="server-card">
                    <img src="{icon_url}" class="srv-icon" alt="icon">
                    <div class="srv-info">
                        <span class="srv-name">{guild.name}</span>
                        <span class="srv-members">{guild.member_count:,} OPERATIVES</span>
                    </div>
                    <span class="srv-btn">JOIN &rarr;</span>
                </a>
                '''
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
            <meta http-equiv="refresh" content="60">
            <title>FORTXX | Command Center</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&family=Cinzel:wght@700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #050505;
                    --panel: rgba(18, 18, 20, 0.6);
                    --border: rgba(255, 255, 255, 0.08);
                    --text: #ffffff;
                    --muted: #a1a1aa;
                    --red: #ff1a1a;
                    --glow: 0 0 20px rgba(255, 26, 26, 0.4);
                    --gold: #eab308;
                    --green: #00ff88;
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background-color: var(--bg);
                    color: var(--text);
                    font-family: 'Inter', sans-serif;
                    min-height: 100vh;
                    overflow-x: hidden;
                    display: flex;
                    flex-direction: column;
                }}
                .bg-animate {{
                    position: fixed;
                    top: 0; left: 0; width: 100vw; height: 100vh;
                    background: linear-gradient(-45deg, #000000, #1a0000, #000000, #0a0000);
                    background-size: 400% 400%;
                    animation: gradientBG 15s ease infinite;
                    z-index: -1;
                }}
                @keyframes gradientBG {{
                    0% {{ background-position: 0% 50%; }}
                    50% {{ background-position: 100% 50%; }}
                    100% {{ background-position: 0% 50%; }}
                }}
                .nav {{
                    padding: 15px 30px;
                    border-bottom: 1px solid var(--border);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: rgba(5, 5, 5, 0.8);
                    backdrop-filter: blur(12px);
                    position: sticky; top: 0; z-index: 10;
                }}
                .brand {{
                    font-family: 'JetBrains Mono', monospace;
                    font-weight: 700; font-size: 1rem;
                    display: flex; align-items: center; gap: 8px;
                }}
                .brand span {{ color: var(--red); text-shadow: var(--glow); }}
                .nav-right {{ display: flex; align-items: center; gap: 15px; }}
                .clock {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.8rem; color: var(--muted);
                }}
                .status {{
                    display: flex; align-items: center; gap: 6px;
                    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
                    color: var(--green); padding: 5px 12px;
                    background: rgba(0, 255, 136, 0.1); border: 1px solid rgba(0, 255, 136, 0.2); border-radius: 4px;
                }}
                .dot {{ width: 6px; height: 6px; background: var(--green); border-radius: 50%; box-shadow: 0 0 8px var(--green); animation: pulse 1.5s infinite; }}
                @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
                .hero {{ padding: 60px 20px 40px; text-align: center; }}
                .hero h1 {{
                    font-family: 'JetBrains Mono', monospace; font-size: 3rem; font-weight: 800;
                    letter-spacing: -1px; margin-bottom: 15px;
                    text-shadow: 0 0 10px rgba(255,255,255,0.2);
                }}
                .hero h1 span {{ color: var(--red); text-shadow: var(--glow); }}
                .owner {{
                    display: inline-flex; align-items: center; gap: 8px;
                    background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3);
                    padding: 8px 20px; border-radius: 99px;
                    font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--gold);
                    margin-bottom: 20px;
                }}
                .owner b {{ color: #fff; }}
                .hero p {{ color: var(--muted); font-family: 'Cinzel', serif; font-style: italic; font-size: 1.1rem; }}
                .container {{ max-width: 900px; margin: 0 auto; padding: 0 20px 50px; width: 100%; flex: 1; }}
                .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 40px; }}
                @media (min-width: 600px) {{ .stats {{ grid-template-columns: repeat(4, 1fr); }} }}
                .stat-box {{
                    background: var(--panel); backdrop-filter: blur(10px);
                    border: 1px solid var(--border); padding: 20px 15px;
                    border-radius: 10px; text-align: center;
                    transition: transform 0.3s;
                }}
                .stat-box:hover {{ transform: translateY(-5px); border-color: rgba(255,26,26,0.3); }}
                .stat-val {{ font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 700; color: var(--gold); margin-bottom: 5px; }}
                .stat-lbl {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }}
                .section-title {{
                    font-family: 'JetBrains Mono', monospace; font-size: 1rem; color: var(--text);
                    margin-bottom: 20px; display: flex; align-items: center; gap: 10px; text-transform: uppercase;
                    border-left: 3px solid var(--red); padding-left: 10px;
                }}
                .features-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 40px; }}
                .feature-card {{
                    background: var(--panel); backdrop-filter: blur(10px);
                    border: 1px solid var(--border); padding: 20px;
                    border-radius: 10px; display: flex; align-items: flex-start; gap: 15px;
                    transition: all 0.3s;
                }}
                .feature-card {{ cursor: pointer; text-decoration: none; color: var(--text); position: relative; }}
                .feature-card:hover {{ border-color: var(--red); box-shadow: var(--glow); background: rgba(255,26,26,0.05); }}
                .f-arrow {{ position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.2rem; color: var(--red); opacity: 0; transition: all 0.3s; }}
                .feature-card:hover .f-arrow {{ opacity: 1; right: 15px; }}
                .f-icon {{ font-size: 1.8rem; background: rgba(255,26,26,0.1); padding: 10px; border-radius: 8px; }}
                .f-info h4 {{ font-size: 1rem; margin-bottom: 5px; }}
                .f-info p {{ font-size: 0.8rem; color: var(--muted); line-height: 1.4; }}
                .server-list {{ display: flex; flex-direction: column; gap: 12px; }}
                .server-card {{
                    display: flex; align-items: center; gap: 15px;
                    background: var(--panel); backdrop-filter: blur(10px);
                    border: 1px solid var(--border); padding: 15px; border-radius: 10px;
                    text-decoration: none; color: var(--text); transition: all 0.2s;
                }}
                .server-card:hover {{ border-color: var(--red); background: rgba(255,26,26,0.05); transform: translateX(5px); }}
                .srv-icon {{ width: 45px; height: 45px; border-radius: 50%; border: 1px solid var(--border); }}
                .srv-info {{ display: flex; flex-direction: column; flex: 1; }}
                .srv-name {{ font-weight: 600; font-size: 1.05rem; }}
                .srv-members {{ font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--muted); margin-top: 3px; }}
                .srv-btn {{
                    font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 700;
                    color: var(--red); padding: 6px 12px; border: 1px solid var(--red); border-radius: 4px;
                }}
                .server-card:hover .srv-btn {{ background: var(--red); color: #fff; }}
                .loading {{ font-family: 'JetBrains Mono', monospace; color: var(--red); text-align: center; padding: 20px; animation: pulse 1.5s infinite; }}
                .footer {{ text-align: center; padding: 25px; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #444; border-top: 1px solid var(--border); }}
            </style>
        </head>
        <body>
            <div class="bg-animate"></div>
            <nav class="nav">
                <div class="brand"><span>&#129656;</span> FORTXX SYSTEM</div>
                <div class="nav-right">
                    <div class="clock" id="clock">00:00:00</div>
                    <div class="status"><div class="dot"></div> SECURE ONLINE</div>
                </div>
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
                <div class="section-title"><span>&#128736;</span> System Modules & Features</div>
                <div class="features-grid">
                    <a href="{INVITE_LINK}" target="_blank" class="feature-card">
                        <div class="f-icon">&#128737;</div>
                        <div class="f-info"><h4>Moderation</h4><p>Auto-warn pop-up, Cartel Hitlist, Kick & Ban system.</p></div>
                        <span class="f-arrow">&rarr;</span>
                    </a>
                    <a href="{INVITE_LINK}" target="_blank" class="feature-card">
                        <div class="f-icon">&#127915;</div>
                        <div class="f-info"><h4>Ticket System</h4><p>Dropdown support tickets with private channels & transcript.</p></div>
                        <span class="f-arrow">&rarr;</span>
                    </a>
                    <a href="{INVITE_LINK}" target="_blank" class="feature-card">
                        <div class="f-icon">&#128220;</div>
                        <div class="f-info"><h4>Roleplay Character</h4><p>ID card generator, Auto-Nickname, and Auto-Role Origin.</p></div>
                        <span class="f-arrow">&rarr;</span>
                    </a>
                    <a href="{INVITE_LINK}" target="_blank" class="feature-card">
                        <div class="f-icon">&#129302;</div>
                        <div class="f-info"><h4>AI Assistant</h4><p>Powered by Aion Labs. Private AI channels for members.</p></div>
                        <span class="f-arrow">&rarr;</span>
                    </a>
                    <a href="{INVITE_LINK}" target="_blank" class="feature-card">
                        <div class="f-icon">&#127912;</div>
                        <div class="f-info"><h4>Auto-Decorator</h4><p>One-click channel renaming, Embed builder & Verify system.</p></div>
                        <span class="f-arrow">&rarr;</span>
                    </a>
                    <a href="{INVITE_LINK}" target="_blank" class="feature-card">
                        <div class="f-icon">&#128202;</div>
                        <div class="f-info"><h4>Server Logs</h4><p>Comprehensive audit logs for bans, kicks, warns, and edits.</p></div>
                        <span class="f-arrow">&rarr;</span>
                    </a>
                </div>
                <div class="section-title"><span>&#127760;</span> Connected Networks</div>
                <div class="server-list">
                    {servers_html}
                </div>
            </div>
            <div class="footer">
                FORTXX SYSTEM &copy; 2026 | POWERED BY @zomahaci
            </div>
            <script>
                function updateClock() {{
                    const now = new Date();
                    document.getElementById('clock').innerText = now.toLocaleTimeString('en-US', {{ hour12: false }});
                }}
                setInterval(updateClock, 1000);
                updateClock();
            </script>
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
    port = 11963
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"[keep_alive] Command Center jalan di 0.0.0.0:{port}")
    server.serve_forever()

def keep_alive(bot):
    global bot_instance
    bot_instance = bot
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
