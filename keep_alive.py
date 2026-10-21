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
                <div class="server-row">
                    <img src="{icon_url}" class="srv-icon" alt="icon">
                    <div class="srv-info">
                        <span class="srv-name">{guild.name}</span>
                        <span class="srv-members">{guild.member_count:,} PERSONNEL</span>
                    </div>
                    <span class="srv-status">ACTIVE</span>
                </div>
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
            <title>CÁRTEL MAINFRAME | Classified</title>
            <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg-deep: #020202;
                    --bg-panel: rgba(12, 12, 14, 0.75);
                    --border: rgba(255, 26, 26, 0.15);
                    --text-main: #e0e0e0;
                    --text-muted: #777777;
                    --accent-red: #ff1a1a;
                    --accent-dark: #8a0000;
                    --accent-gold: #d4af37;
                    --accent-green: #00ff88;
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background-color: var(--bg-deep);
                    background-image: 
                        radial-gradient(circle at 15% 50%, rgba(138, 0, 0, 0.08) 0%, transparent 40%),
                        radial-gradient(circle at 85% 30%, rgba(255, 26, 26, 0.05) 0%, transparent 40%);
                    color: var(--text-main);
                    font-family: 'Inter', sans-serif;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    overflow-x: hidden;
                }}
                
                /* Scanline effect */
                body::after {{
                    content: "";
                    position: fixed;
                    top: 0; left: 0; width: 100%; height: 100%;
                    background: linear-gradient(rgba(0,0,0,0) 50%, rgba(0,0,0,0.1) 50%);
                    background-size: 100% 4px;
                    pointer-events: none;
                    z-index: 100;
                    opacity: 0.3;
                }}

                .nav {{
                    padding: 15px 40px;
                    border-bottom: 1px solid rgba(255, 26, 26, 0.1);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: rgba(0, 0, 0, 0.4);
                    backdrop-filter: blur(8px);
                    position: sticky;
                    top: 0;
                    z-index: 50;
                }}
                .brand-lockup {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    font-family: 'Cinzel', serif;
                    font-weight: 900;
                    letter-spacing: 3px;
                    font-size: 1.1rem;
                }}
                .brand-mark {{
                    color: var(--accent-red);
                    font-size: 1.4rem;
                    text-shadow: 0 0 10px var(--accent-red);
                }}
                .sys-status {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.7rem;
                    color: var(--accent-green);
                    padding: 4px 12px;
                    border: 1px solid rgba(0, 255, 136, 0.3);
                    border-radius: 2px;
                    background: rgba(0, 255, 136, 0.05);
                }}
                .blink {{
                    width: 6px; height: 6px;
                    background: var(--accent-green);
                    border-radius: 50%;
                    box-shadow: 0 0 8px var(--accent-green);
                    animation: blink 1s infinite alternate;
                }}
                @keyframes blink {{ from {{ opacity: 0.3; }} to {{ opacity: 1; }} }}

                .hero {{
                    padding: 80px 20px 40px;
                    text-align: center;
                    position: relative;
                }}
                .hero-label {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.75rem;
                    color: var(--accent-red);
                    letter-spacing: 4px;
                    margin-bottom: 20px;
                    text-transform: uppercase;
                }}
                .hero h1 {{
                    font-family: 'Cinzel', serif;
                    font-size: clamp(2.5rem, 5vw, 4.5rem);
                    font-weight: 900;
                    line-height: 1.1;
                    background: linear-gradient(180deg, #ffffff 0%, #a0a0a0 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 15px;
                    text-shadow: 0 0 30px rgba(255, 26, 26, 0.2);
                }}
                .hero p {{
                    color: var(--text-muted);
                    font-style: italic;
                    letter-spacing: 1px;
                    margin-bottom: 30px;
                    font-size: 0.95rem;
                }}
                .cta-btn {{
                    display: inline-flex;
                    align-items: center;
                    gap: 10px;
                    background: rgba(255, 26, 26, 0.1);
                    color: #ffcccc;
                    border: 1px solid var(--accent-red);
                    padding: 12px 30px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.85rem;
                    font-weight: 700;
                    text-decoration: none;
                    letter-spacing: 2px;
                    transition: all 0.3s;
                    box-shadow: 0 0 20px rgba(255, 26, 26, 0.15);
                }}
                .cta-btn:hover {{
                    background: var(--accent-red);
                    color: #000;
                    box-shadow: 0 0 30px rgba(255, 26, 26, 0.5);
                }}

                .grid-container {{
                    max-width: 1100px;
                    margin: 0 auto;
                    padding: 20px;
                    width: 100%;
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    flex: 1;
                }}
                @media (max-width: 768px) {{
                    .grid-container {{ grid-template-columns: repeat(2, 1fr); }}
                    .col-span-4 {{ grid-column: span 2 !important; }}
                }}

                /* Glassmorphism Cards */
                .card {{
                    background: var(--bg-panel);
                    border: 1px solid var(--border);
                    border-radius: 4px;
                    padding: 24px;
                    backdrop-filter: blur(12px);
                    position: relative;
                    overflow: hidden;
                    transition: border-color 0.3s;
                }}
                .card:hover {{
                    border-color: rgba(255, 26, 26, 0.4);
                }}
                .card::before {{
                    content: '';
                    position: absolute;
                    top: 0; left: 0; width: 100%; height: 1px;
                    background: linear-gradient(90deg, transparent, rgba(255, 26, 26, 0.5), transparent);
                }}
                
                .stat-val {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: var(--accent-gold);
                    line-height: 1;
                    margin-bottom: 8px;
                }}
                .stat-lbl {{
                    font-size: 0.65rem;
                    color: var(--text-muted);
                    letter-spacing: 2px;
                    text-transform: uppercase;
                }}

                .col-span-4 {{
                    grid-column: span 4;
                }}

                .networks-title {{
                    font-family: 'Cinzel', serif;
                    font-size: 1.1rem;
                    color: var(--text-main);
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .networks-title span {{ color: var(--accent-red); }}

                .srv-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 12px;
                }}
                .server-row {{
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    background: rgba(0,0,0,0.3);
                    border: 1px solid rgba(255,255,255,0.03);
                    padding: 12px;
                    border-radius: 4px;
                }}
                .srv-icon {{
                    width: 40px; height: 40px;
                    border-radius: 4px;
                    border: 1px solid rgba(255,255,255,0.1);
                }}
                .srv-info {{
                    display: flex;
                    flex-direction: column;
                    flex: 1;
                }}
                .srv-name {{
                    font-weight: 600;
                    font-size: 0.9rem;
                }}
                .srv-members {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.65rem;
                    color: var(--text-muted);
                    margin-top: 2px;
                }}
                .srv-status {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.6rem;
                    color: var(--accent-green);
                    border: 1px solid rgba(0,255,136,0.2);
                    padding: 2px 6px;
                    border-radius: 2px;
                }}

                .loading {{
                    font-family: 'JetBrains Mono', monospace;
                    color: var(--accent-red);
                    text-align: center;
                    padding: 20px;
                    animation: blink 1.5s infinite;
                }}

                .footer {{
                    text-align: center;
                    padding: 25px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.65rem;
                    color: #444;
                    border-top: 1px solid rgba(255,255,255,0.05);
                    background: #000;
                    letter-spacing: 1px;
                }}
            </style>
        </head>
        <body>
            <nav class="nav">
                <div class="brand-lockup">
                    <span class="brand-mark">🩸</span> CÁRTEL MAINFRAME
                </div>
                <div class="sys-status">
                    <div class="blink"></div> SECURE LINK
                </div>
            </nav>

            <div class="hero">
                <div class="hero-label">// SYSTEM OVERRIDE // AUTHORIZED PERSONNEL ONLY //</div>
                
                <h1 class="glitch" data-text="FORTXX">FORTXX</h1>
                
                <div class="owner-badge">
                    <span class="crown">👑</span> EL JEFE: <span class="owner-name">@zomahaci</span>
                </div>
                
                <p class="tagline">"La Familia es todo."</p>
                
                <a href="{INVITE_LINK}" target="_blank" class="cta-btn">REQUEST ENTRY TO SYNDICATE →</a>
            </div>

            <div class="grid-container">
                <!-- Stats Row -->
                <div class="card">
                    <div class="stat-val">{total_servers}</div>
                    <div class="stat-lbl">Networks</div>
                </div>
                <div class="card">
                    <div class="stat-val">{total_members:,}</div>
                    <div class="stat-lbl">Operatives</div>
                </div>
                <div class="card">
                    <div class="stat-val">{ping}ms</div>
                    <div class="stat-lbl">Uplink Latency</div>
                </div>
                <div class="card">
                    <div class="stat-val">{uptime_str}</div>
                    <div class="stat-lbl">System Uptime</div>
                </div>

                <!-- Networks List -->
                <div class="card col-span-4">
                    <div class="networks-title"><span>🌐</span> CONNECTED NETWORKS</div>
                    <div class="srv-grid">
                        {servers_html}
                    </div>
                </div>
            </div>

            <div class="footer">
                CÁRTEL DE JALISCO NUEVA GENERACIÓN © 2026 // INFRASTRUCTURE DIVISION
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
    print(f"[keep_alive] Classified Command Center jalan di 0.0.0.0:{port}")
    server.serve_forever()

def keep_alive(bot):
    global bot_instance
    bot_instance = bot
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
