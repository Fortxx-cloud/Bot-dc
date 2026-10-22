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
            <title>FORTXX | Command Center v3</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&family=Cinzel:wght@700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #050505;
                    --panel: rgba(18, 18, 20, 0.8);
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
                    transition: all 0.3s; cursor: pointer; position: relative;
                    text-decoration: none; color: var(--text);
                }}
                .feature-card:hover {{ border-color: var(--red); box-shadow: var(--glow); background: rgba(255,26,26,0.05); transform: translateY(-3px); }}
                .f-icon {{ font-size: 1.8rem; background: rgba(255,26,26,0.1); padding: 10px; border-radius: 8px; }}
                .f-info h4 {{ font-size: 1rem; margin-bottom: 5px; }}
                .f-info p {{ font-size: 0.8rem; color: var(--muted); line-height: 1.4; }}
                .f-arrow {{ position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.2rem; color: var(--red); opacity: 0.5; transition: all 0.3s; }}
                .feature-card:hover .f-arrow {{ opacity: 1; right: 15px; }}

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

                .modal {{
                    display: none; position: fixed; z-index: 100;
                    left: 0; top: 0; width: 100%; height: 100%;
                    background-color: rgba(0,0,0,0.8); backdrop-filter: blur(5px);
                    align-items: center; justify-content: center;
                }}
                .modal-content {{
                    background: #111; border: 1px solid var(--red);
                    padding: 30px; border-radius: 12px; max-width: 500px; width: 90%;
                    box-shadow: 0 0 40px rgba(255,26,26,0.2); position: relative;
                    animation: modalFade 0.3s ease; max-height: 80vh; overflow-y: auto;
                }}
                @keyframes modalFade {{ from {{ opacity: 0; transform: scale(0.9); }} to {{ opacity: 1; transform: scale(1); }} }}
                .close-btn {{
                    position: absolute; top: 15px; right: 20px;
                    font-size: 1.5rem; color: var(--muted); cursor: pointer;
                }}
                .close-btn:hover {{ color: var(--red); }}
                .modal-title {{ font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; color: var(--red); margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }}
                .cmd-list {{ list-style: none; }}
                .cmd-list li {{ margin-bottom: 12px; font-size: 0.9rem; background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border-left: 2px solid var(--gold); }}
                .cmd-name {{ font-family: 'JetBrains Mono', monospace; color: var(--gold); font-weight: bold; margin-right: 10px; }}
                .cmd-desc {{ color: var(--muted); }}
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

                <div class="section-title"><span>&#128736;</span> All System Modules (13)</div>
                <div class="features-grid">
                    <!-- 0. SERVER BUILDER -->
                    <div class="feature-card" onclick="openModal('builder')"><div class="f-icon">&#127959;</div><div class="f-info"><h4>Server Builder</h4><p>Auto build channels, roles & permissions.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 1. MODERATION -->
                    <div class="feature-card" onclick="openModal('mod')"><div class="f-icon">&#128737;</div><div class="f-info"><h4>Moderation</h4><p>Warn, Kick, Ban, Timeout & Snipe.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 2. TICKET -->
                    <div class="feature-card" onclick="openModal('ticket')"><div class="f-icon">&#127915;</div><div class="f-info"><h4>Ticket System</h4><p>Dropdown support tickets & Hitlist.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 3. ROLEPLAY -->
                    <div class="feature-card" onclick="openModal('rp')"><div class="f-icon">&#128220;</div><div class="f-info"><h4>Roleplay Char</h4><p>ID card, Auto-Nick, Auto-Role.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 4. AI -->
                    <div class="feature-card" onclick="openModal('ai')"><div class="f-icon">&#129302;</div><div class="f-info"><h4>AI Assistant</h4><p>Private AI channels (Aion Labs).</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 5. AUTO DECORATOR -->
                    <div class="feature-card" onclick="openModal('setup')"><div class="f-icon">&#127912;</div><div class="f-info"><h4>Auto-Decorator</h4><p>One-click rename & Embed builder.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 6. LOGS -->
                    <div class="feature-card" onclick="openModal('logs')"><div class="f-icon">&#128202;</div><div class="f-info"><h4>Server Logs</h4><p>Audit logs for ban, kick, warn.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 7. ROLE MANAGEMENT -->
                    <div class="feature-card" onclick="openModal('role')"><div class="f-icon">&#127917;</div><div class="f-info"><h4>Role Manager</h4><p>Add, remove, mass-role & auto-role.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 8. CHANNEL MANAGEMENT -->
                    <div class="feature-card" onclick="openModal('channel')"><div class="f-icon">&#128421;</div><div class="f-info"><h4>Channel Manager</h4><p>Create, delete, lock & slowmode.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 9. VERIFICATION -->
                    <div class="feature-card" onclick="openModal('verify')"><div class="f-icon">&#9989;</div><div class="f-info"><h4>Gatekeeper Verify</h4><p>Reaction role lock for new members.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 10. UTILITY -->
                    <div class="feature-card" onclick="openModal('utility')"><div class="f-icon">&#128295;</div><div class="f-info"><h4>Utility & Info</h4><p>Ping, Uptime, Avatar, Userinfo.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 11. FUN -->
                    <div class="feature-card" onclick="openModal('fun')"><div class="f-icon">&#127881;</div><div class="f-info"><h4>Fun & Social</h4><p>Poll, Say, Embed, AFK, Remind.</p></div><span class="f-arrow">&#128269;</span></div>
                    <!-- 12. OWNER -->
                    <div class="feature-card" onclick="openModal('owner')"><div class="f-icon">&#128081;</div><div class="f-info"><h4>Owner Tools</h4><p>Bot admin, Setmodrole, Warnlog.</p></div><span class="f-arrow">&#128269;</span></div>
                </div>

                <div class="section-title"><span>&#127760;</span> Connected Networks</div>
                <div class="server-list">
                    {servers_html}
                </div>
            </div>
            <div class="footer">
                FORTXX SYSTEM &copy; 2026 | POWERED BY @zomahaci
            </div>

            <div id="cmdModal" class="modal">
                <div class="modal-content">
                    <span class="close-btn" onclick="closeModal()">&times;</span>
                    <h3 class="modal-title" id="modalTitle">Title</h3>
                    <ul class="cmd-list" id="modalList"></ul>
                </div>
            </div>

            <script>
                function updateClock() {{
                    const now = new Date();
                    document.getElementById('clock').innerText = now.toLocaleTimeString('en-US', {{ hour12: false }});
                }}
                setInterval(updateClock, 1000);
                updateClock();

                const featureData = {{
                    'builder': {{ title: '🏗 Server Builder Tools', cmds: [
                        {{ name: '!buildcommunity', desc: 'Bikin struktur server komunitas dasar' }},
                        {{ name: '!buildcommunity2', desc: 'Tambah channel Events, Music, Welcome, Partner' }},
                        {{ name: '!buildcommunity3', desc: 'Tambah channel Creative, Lifestyle, Safe Space' }},
                        {{ name: '!buildroles', desc: 'Bikin semua role Staff, Minat, & Ping otomatis' }},
                        {{ name: '!setup_permissions', desc: 'Setel izin (perms) role otomatis' }},
                        {{ name: '!setup_channels', desc: 'Kunci channel informasi jadi Read-Only' }},
                        {{ name: '!ticketv2', desc: 'Pasang panel Ticket khusus komunitas' }}
                    ]}},
                    'mod': {{ title: '🛡 Moderation System', cmds: [
                        {{ name: '!warn @user', desc: 'Kasih warning (Form Pop-up + Role)' }},
                        {{ name: '!warns @user', desc: 'Liat history warning' }},
                        {{ name: '!clearwarns @user', desc: 'Hapus semua warning' }},
                        {{ name: '!kick / !ban', desc: 'Usir / Ban member' }},
                        {{ name: '!timeout @user', desc: 'Mute sementara' }},
                        {{ name: '!snipe / !editsnipe', desc: 'Liat chat yang dihapus/diedit' }}
                    ]}},
                    'ticket': {{ title: '🎫 Ticket System', cmds: [
                        {{ name: '!ticket setup', desc: 'Bikin panel bantuan (Dropdown)' }},
                        {{ name: '!setupwarnlist', desc: 'Bikin Live Dashboard Cartel Hitlist' }}
                    ]}},
                    'rp': {{ title: '📜 Roleplay Character', cmds: [
                        {{ name: '!setupchar', desc: 'Bikin panel pendaftaran karakter' }},
                        {{ name: '!char set', desc: 'Bikin ID Card (Auto-Nickname)' }},
                        {{ name: '!char @user', desc: 'Liat profil karakter orang lain' }}
                    ]}},
                    'ai': {{ title: '🤖 AI Assistant', cmds: [
                        {{ name: '!setupai', desc: 'Bikin channel AI pribadi' }},
                        {{ name: '!ai [teks]', desc: 'Tanya AI (Global)' }},
                        {{ name: '!rp [aksi]', desc: 'Roleplay bareng AI' }}
                    ]}},
                    'setup': {{ title: '🎨 Auto-Decorator & Setup', cmds: [
                        {{ name: '!dekorasi', desc: 'Rapihin nama channel otomatis' }},
                        {{ name: '!buatpesan', desc: 'Bikin pengumuman Embed cantik' }},
                        {{ name: '!setupwelcome', desc: 'Setup pesan Welcome & Goodbye' }}
                    ]}},
                    'logs': {{ title: '📊 Server Logs', cmds: [
                        {{ name: '!setbotlog', desc: 'Set channel pantau aktivitas bot' }},
                        {{ name: '!setwarnlog', desc: 'Set channel khusus log warning' }},
                        {{ name: '!testlog', desc: 'Ngetes apakah channel log berfungsi' }}
                    ]}},
                    'role': {{ title: '🏷 Role Manager', cmds: [
                        {{ name: '!addrole / !removerole', desc: 'Kasih / cabut role member' }},
                        {{ name: '!massrole @role', desc: 'Kasih role ke semua member' }},
                        {{ name: '!autorole @role', desc: 'Role otomatis pas join' }},
                        {{ name: '!roleedit / !roleperm', desc: 'Edit warna / izin role' }}
                    ]}},
                    'channel': {{ title: '💻 Channel Manager', cmds: [
                        {{ name: '!createchannel / !deletechannel', desc: 'Bikin / Hapus channel' }},
                        {{ name: '!lock / !unlock', desc: 'Kunci channel biar gak bisa chat' }},
                        {{ name: '!slowmode [detik]', desc: 'Atur jeda chat (anti-spam)' }},
                        {{ name: '!purge [jumlah]', desc: 'Hapus pesan massal' }}
                    ]}},
                    'verify': {{ title: '✅ Gatekeeper Verify', cmds: [
                        {{ name: '!setupverify', desc: 'Bikin sistem klik emoji untuk buka channel' }},
                        {{ name: '!setupwarnlog', desc: 'Sistem privasi channel' }}
                    ]}},
                    'utility': {{ title: '🔧 Utility & Info', cmds: [
                        {{ name: '!ping / !uptime', desc: 'Cek kesehatan bot' }},
                        {{ name: '!userinfo / !serverinfo', desc: 'Info profil / server' }},
                        {{ name: '!avatar @user', desc: 'Ambil foto profil HD' }},
                        {{ name: '!dm @user', desc: 'Kirim pesan pribadi via bot' }}
                    ]}},
                    'fun': {{ title: '🎉 Fun & Social', cmds: [
                        {{ name: '!poll', desc: 'Bikin voting dengan reaction' }},
                        {{ name: '!say / !embed', desc: 'Bot ngomong / bikin pesan keren' }},
                        {{ name: '!afk', desc: 'Status AFK (auto-reply kalau di-tag)' }},
                        {{ name: '!remind', desc: 'Set alarm / pengingat' }}
                    ]}},
                    'owner': {{ title: '👑 Owner Tools', cmds: [
                        {{ name: '!botrun / !botremove', desc: 'Tambah / cabut akses admin bot' }},
                        {{ name: '!setmodrole', desc: 'Daftarin role yang boleh jadi Mod' }},
                        {{ name: '!setwarnlog / !setwarntag', desc: 'Kustomisasi sistem warning' }}
                    ]}}
                }};

                function openModal(key) {{
                    const data = featureData[key];
                    if (!data) return;
                    document.getElementById('modalTitle').innerText = data.title;
                    const list = document.getElementById('modalList');
                    list.innerHTML = '';
                    data.cmds.forEach(cmd => {{
                        const li = document.createElement('li');
                        li.innerHTML = `<span class="cmd-name">${{cmd.name}}</span><br><span class="cmd-desc">${{cmd.desc}}</span>`;
                        list.appendChild(li);
                    }});
                    document.getElementById('cmdModal').style.display = 'flex';
                }}

                function closeModal() {{
                    document.getElementById('cmdModal').style.display = 'none';
                }}

                window.onclick = function(event) {{
                    const modal = document.getElementById('cmdModal');
                    if (event.target == modal) {{ closeModal(); }}
                }}
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
    print(f"[keep_alive] Command Center v3 jalan di 0.0.0.0:{port}")
    server.serve_forever()

def keep_alive(bot):
    global bot_instance
    bot_instance = bot
    t = threading.Thread(target=_run_server)
    t.daemon = True
    t.start()
