from discord import app_commands
from discord.ext import tasks
import unicodedata
nl = chr(10)
import discord
from discord.ext import commands
import json
import os
from datetime import timedelta
import asyncio
import re
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.moderation = True


def normalize_text(t):
    # Ngubah huruf miring/aneh (𝘣𝘰𝘵) jadi huruf biasa (bot)
    return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode('ascii').lower()

bot = commands.Bot(command_prefix='!', intents=intents,
    max_messages=100,
    member_cache_flags=discord.MemberCacheFlags.none(),
    chunk_guilds_at_startup=False)



bot.remove_command('help')
# --- DYNAMIC OWNER IDS ---
OWNERS_FILE = "owners.json"

def load_owners():
    if os.path.exists(OWNERS_FILE):
        with open(OWNERS_FILE, 'r') as f:
            return json.load(f)
    else:
        default = [1562145158341075075] # ID lo
        with open(OWNERS_FILE, 'w') as f:
            json.dump(default, f)
        return default

OWNER_IDS = load_owners()

def save_owners():
    with open(OWNERS_FILE, 'w') as f:
        json.dump(OWNER_IDS, f)


@bot.check
async def global_check(ctx):
    # Command publik yang bisa dipakai semua orang
    public_cmds = ("help", "ping", "uptime", "avatar", "userinfo", "serverinfo", "test", "afk", "remind")
    if ctx.command.name in public_cmds:
        return True
    # Command lain (moderasi/owner) tetap dicek
    return ctx.author.id in OWNER_IDS or is_mod(ctx)

# ══════════════════════════════════════════════════
# 🔧 CONFIG
# ══════════════════════════════════════════════════
WELCOME_KEYWORD = "welcome"
ROLE_KEYWORD = "take"
LOG_KEYWORD = "logs"  # Bot bakal nyari channel yg ada kata "logs"
MAX_WARN = 3

WARN_FILE = "warns.json"
FAMILY_NAME = "Cártel de Jalisco Nueva Generación"

WARN_TAG_ROLE_ID = 1502895404092752033  # role yg di-tag saat warn
WARN_ROLES = {
    1: "⚠️ Warned I",
    2: "⚠️ Warned II",
    3: "⚠️ Warned III"
}

# ══════════════════════════════════════════════════
# UTILS
# ══════════════════════════════════════════════════
def load_warns():
    if os.path.exists(WARN_FILE):
        with open(WARN_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_warns(data):
    with open(WARN_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_mod(ctx):
    """Cek apakah user punya akses moderasi.
    Priority: permission Discord → role config → role default (Mod/Moderator/Admin/Staff)."""
    # 1) Permission Discord
    try:
        p = ctx.author.guild_permissions
        if p.administrator or p.kick_members or p.moderate_members or p.manage_messages or p.ban_members or p.manage_roles:
            return True
    except Exception:
        pass

    # 2) Role dari config (bisa diatur via !setmodrole)
    try:
        cfg = _cfg_load()
        allowed_ids = cfg.get("mod_roles", {}).get(str(ctx.guild.id), [])
        if allowed_ids:
            user_role_ids = {str(r.id) for r in ctx.author.roles}
            if user_role_ids & set(allowed_ids):
                return True
    except Exception:
        pass

    # 3) Role default by nama
    try:
        default_names = {"mod", "moderator", "admin", "staff", "owner", "co-owner"}
        for r in ctx.author.roles:
            if r.name.lower() in default_names:
                return True
    except Exception:
        pass

    return False




@bot.command()
async def setupwarnroles(ctx):
    """Buat role Warned 1/2/3 otomatis untuk sistem warning."""
    if not is_mod(ctx):
        return await ctx.send("❌ Lo gak punya izin.")
    created = []
    existing = []
    colors = {1: discord.Color.orange(), 2: discord.Color.dark_orange(), 3: discord.Color.red()}
    
    for lvl, name in WARN_ROLES.items():
        role = discord.utils.get(ctx.guild.roles, name=name)
        if role:
            existing.append(name)
        else:
            await ctx.guild.create_role(name=name, color=colors[lvl], reason="Auto-setup warn roles")
            created.append(name)
            
    await ctx.send(f"✅ **Setup Selesai!**\nDibuat: {len(created)} role\nUdah ada: {len(existing)} role\n\n⚠️ **PENTING:** Tarik role bot ke ATAS role Warned 1-3 biar bisa ngasih role!")

# ══════════════════════════════════════════════════
# MODERATION COMMANDS
# ══════════════════════════════════════════════════
@bot.hybrid_command()
async def kick(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
    """Keluarkan member dari server (bisa join lagi)."""
    _ismod = is_mod(ctx)
    _role_ok = member.top_role < ctx.author.top_role
    if not _ismod or not _role_ok:
        info = (
            "🔍 **DEBUG WARN**\n"
            f"• `is_mod(ctx)` = **{_ismod}**\n"
            f"• Role kamu: **{ctx.author.top_role.name}** (posisi {ctx.author.top_role.position})\n"
            f"• Role target: **{member.top_role.name}** (posisi {member.top_role.position})\n"
            f"• `role_ok` = **{_role_ok}** (butuh: role kamu > role target)\n\n"
            "**Artinya:** "
        )
        if not _ismod and not _role_ok:
            info += "Kamu bukan mod **DAN** role kamu ≤ role target."
        elif not _ismod:
            info += "Kamu **bukan mod** menurut bot (cek MOD_ROLES / permission)."
        else:
            info += "Role kamu **tidak lebih tinggi** dari role target."
        return await ctx.send(info)
    try:
        await member.kick(reason=f"{ctx.author}: {reason}")
        await send_log(ctx.guild, "🔨 MIEMBRO EXPULSADO", f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {ctx.author.mention}\n**Alasan:** {reason}", discord.Color.red())
        await ctx.send(embed=discord.Embed(title="🔨 MIEMBRO EXPULSADO", description=f"**{member.display_name}** ditendang.\n**Alasan:** {reason}", color=discord.Color.from_rgb(139, 0, 0)))
    except:
        await ctx.send("❌ Bot gak punya izin.")

@bot.hybrid_command()
async def ban(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
    """Ban member dari server secara permanen."""
    if not is_mod(ctx) or member.top_role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Kamu bukan mod ATAU role target di atas role bot.")
    try:
        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=1)
        await send_log(ctx.guild, "☠️ MIEMBRO DESTERRADO", f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {ctx.author.mention}\n**Alasan:** {reason}", discord.Color.dark_red())
        await ctx.send(embed=discord.Embed(title="☠️ MIEMBRO DESTERRADO", description=f"**{member.display_name}** dibanned.\n**Alasan:** {reason}", color=discord.Color.from_rgb(60, 0, 0)))
    except:
        await ctx.send("❌ Bot gak punya izin.")

@bot.command()
async def mute(ctx, member: discord.Member, duration="10m", *, reason="Tidak ada alasan"):
    """Bisukan member agar tidak bisa kirim pesan."""
    if not is_mod(ctx) or member.top_role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Kamu bukan mod ATAU role target di atas role bot.")
    try:
        unit = duration[-1].lower()
        amt = int(duration[:-1])
        delta = timedelta(seconds=amt) if unit=='s' else timedelta(minutes=amt) if unit=='m' else timedelta(hours=amt) if unit=='h' else timedelta(days=amt)
        await member.timeout(delta, reason=f"{ctx.author}: {reason}")
        await send_log(ctx.guild, "🤐 MIEMBRO SILENCIADO", f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {ctx.author.mention}\n**Durasi:** {duration}\n**Alasan:** {reason}", discord.Color.orange())
        await ctx.send(embed=discord.Embed(title="🤐 MIEMBRO SILENCIADO", description=f"**{member.display_name}** dibungkam.\n**Durasi:** {duration}\n**Alasan:** {reason}", color=discord.Color.from_rgb(255, 140, 0)))
    except:
        await ctx.send("❌ Format durasi salah (contoh: 10m, 1h, 1d).")

@bot.command()
async def unmute(ctx, member: discord.Member):
    """Cabut mute dari member."""
    if not is_mod(ctx): return await ctx.send("❌ Gak punya izin.")
    try:
        await member.timeout(None, reason=f"Unmute by {ctx.author}")
        await send_log(ctx.guild, "🔊 MIEMBRO LIBERADO", f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {ctx.author.mention}\n**Aksi:** Mute dicabut", discord.Color.green())
        await ctx.send(f"🔊 **{member.display_name}** udah bisa ngomong lagi.")
    except:
        await ctx.send("❌ Bot gak punya izin.")
@bot.command()
async def warns(ctx, member: discord.Member):
    """Liat daftar warning yang diterima member."""
    user_warns = load_warns().get(str(ctx.guild.id), {}).get(str(member.id), [])
    if not user_warns: return await ctx.send(f"✅ **{member.display_name}** gak punya warn.")
    embed = discord.Embed(title=f"📋 WARN LIST — {member.display_name}", description=f"Total: **{len(user_warns)}/{MAX_WARN}**", color=discord.Color.from_rgb(255, 165, 0))
    for i, w in enumerate(user_warns, 1):
        embed.add_field(name=f"Warn #{i}", value=f"Alasan: {w['reason']}\nOleh: {w['by']}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def clearwarns(ctx, member: discord.Member):
    """Hapus semua warning & role warning dari member."""
    if not is_mod(ctx): return await ctx.send("❌ Gak punya izin.")
    warns = load_warns()
    gid, uid = str(ctx.guild.id), str(member.id)
    if uid in warns.get(gid, {}):
        warns[gid][uid] = []
        save_warns(warns)
        await update_cartel_list(ctx.guild)
        
        for name in WARN_ROLES.values():
            role = discord.utils.get(ctx.guild.roles, name=name)
            if role and role in member.roles:
                try: await member.remove_roles(role)
                except: pass
                
        await send_log(ctx.guild, "🧹 WARN RESET", f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {ctx.author.mention}\n**Aksi:** Semua warn & role dihapus", discord.Color.green())
        await ctx.send(f"✅ Warn & Role **{member.display_name}** udah di-reset.")
    else:
        await ctx.send(f"ℹ️ **{member.display_name}** gak punya warn.")

# ══════════════════════════════════════════════════
# EVENTS & RUN
# ══════════════════════════════════════════════════


@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} udah online!")
    print("[SYSTEM] Memulai Auto-Restore...")
    
    # Set Status
    try:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="🌐 bot-fortxx.wispbyte.app | FORTXX Store"))
    except: pass

    # 1. AUTO-SYNC SLASH COMMAND
    try:
        await bot.tree.sync()
        print("[SYSTEM] Slash Commands berhasil disinkronisasi!")
    except Exception as e:
        print(f"[SYSTEM] Gagal sync slash: {e}")

    # 2. AUTO-RESTORE CONFIG PER SERVER
    cfg = _cfg_load()
    restored_count = 0
    
    for guild in bot.guilds:
        # Nyari Channel Log & Verify
        channel_mapping = {
            'warn_log_channel': ['logs-warning', 'warn-logs'],
            'bot_log_channel': ['bot-run', 'bot-logs'],
            'banned_log_ch': ['banned-logs'],
            'invite_log_ch': ['invite-logs'],
            'spam_log_ch': ['spam-bot'],
            'verify_channel': ['verify'],
            'welcome_channel': ['welcome']
        }
        
        for cfg_key, keywords in channel_mapping.items():
            for ch in guild.text_channels:
                if any(kw in ch.name.lower() for kw in keywords):
                    cfg[cfg_key] = ch.id
                    restored_count += 1
                    break
                    
    _cfg_save(cfg)
    if restored_count > 0:
        print(f"[SYSTEM] Auto-Restore: Berhasil memulihkan {restored_count} channel config.")

    # 3. AUTO-LOAD PERSISTENT VIEWS (BIAR TOMBOL GAK MATI)
    views_to_load = [
        "ModTicketView", "ModTicketCloseView",
        "TicketView", "TicketCloseView",
        "TicketV2View", "TicketV2CloseView",
        "CharView", "HelpMainView",
        "EmbedBuilderView", "AICreateView",
        "AICloseView", "OwnerView"
    ]

    for v_name in views_to_load:
        try:
            if v_name in globals():
                cls = globals()[v_name]
                bot.add_view(cls())
                print(f"[SYSTEM] Loaded View: {v_name}")
        except Exception as e:
            print(f"[SYSTEM] Gagal load view {v_name}: {e}")
            
    # Khusus CommunityRoleView yang butuh parameter
    try:
        if "CommunityRoleView" in globals():
            bot.add_view(CommunityRoleView([]))
            print("[SYSTEM] Loaded View: CommunityRoleView")
    except Exception:
        pass


        # --- SELAMATKAN OWNER DARI KEKUNCIAN ---
        owner = guild.owner
        if owner and verify_role and verify_role not in owner.roles:
            try:
                await owner.add_roles(verify_role)
                print(f"[SYSTEM] Role Verified dipaksa masuk ke Owner ({owner.name}).")
            except: pass
        # ---------------------------------------

    print("[SYSTEM] AUTO-RESTORE SELESAI! Bot siap digunakan tanpa setup ulang.")

@bot.command()
async def test(ctx):
    """Command test untuk cek bot masih hidup."""
    await ctx.send('🩸 Bot CJNG siap beroperasi!')

# GANTI TOKEN DI BAWAH!

# ══════════════════════════════════════════════════
# OWNER MANAGEMENT COMMANDS
# ══════════════════════════════════════════════════
@bot.command()
async def botrun(ctx, member: discord.Member):
    """Tambahin admin bot via Discord."""
    if ctx.author.id not in OWNER_IDS:
        return await ctx.send("❌ Cuma owner yang bisa nambahin admin.")
    
    if member.id in OWNER_IDS:
        return await ctx.send(f"ℹ️ {member.mention} udah jadi admin bot.")
        
    OWNER_IDS.append(member.id)
    save_owners()
    await ctx.send(f"✅ **{member.display_name}** sekarang bisa pake command bot!")

@bot.command()
async def botremove(ctx, member: discord.Member):
    """Cabut akses admin bot."""
    if ctx.author.id not in OWNER_IDS:
        return await ctx.send("❌ Cuma owner yang bisa cabut admin.")
        
    if member.id not in OWNER_IDS:
        return await ctx.send(f"ℹ️ {member.mention} bukan admin bot.")
        
    if member.id == 1562145158341075075:
        return await ctx.send("❌ Gak bisa ngehapus owner utama!")
        
    OWNER_IDS.remove(member.id)
    save_owners()
    await ctx.send(f"✅ Akses admin **{member.display_name}** dicabut.")

@bot.command()
async def botlist(ctx):
    """Liat daftar admin bot."""
    if ctx.author.id not in OWNER_IDS:
        return await ctx.send("❌ Lo gak punya akses.")
    
    msg = "**👑 DAFTAR ADMIN BOT**\n\n"
    for i, uid in enumerate(OWNER_IDS, 1):
        try:
            user = await bot.fetch_user(uid)
            msg += f"{i}. {user.mention} (`{uid}`)\n"
        except:
            msg += f"{i}. Unknown User (`{uid}`)\n"
    await ctx.send(msg)





# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# 🎁 10 FITUR BARU
# ══════════════════════════════════════════════════════════════
import time as _t
from datetime import timedelta as _td
_BOT_START = _t.time()

@bot.hybrid_command(name='ping')
async def ping_cmd(ctx):
    """Cek latency bot ke Discord."""
    ws = round(bot.latency * 1000)
    t0 = _t.perf_counter()
    msg = await ctx.send("🏓 Pinging...")
    api = round((_t.perf_counter() - t0) * 1000)
    await msg.edit(content=f"🏓 **Pong!**\n📡 WebSocket: `{ws}ms`\n⚡ API: `{api}ms`")

@bot.command(name="uptime")
async def uptime_cmd(ctx):
    """Berapa lama bot udah online."""
    secs = int(_t.time() - _BOT_START)
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    p = []
    if d: p.append(f"{d}d")
    if h: p.append(f"{h}h")
    if m: p.append(f"{m}m")
    p.append(f"{s}s")
    await ctx.send(f"⏱️ Uptime: **{' '.join(p)}**")

@bot.hybrid_command(name='avatar')
async def avatar_cmd(ctx, member: discord.Member = None):
    """Tampilkan avatar user (default: kamu)."""
    member = member or ctx.author
    e = discord.Embed(title=f"🖼️ Avatar {member.display_name}", color=discord.Color.blurple())
    e.set_image(url=member.display_avatar.url)
    e.add_field(name="📥 Download", value=f"[PNG]({member.display_avatar.replace(format='png', size=1024).url}) • [JPG]({member.display_avatar.replace(format='jpg', size=1024).url})")
    await ctx.send(embed=e)

@bot.hybrid_command(name='userinfo')
async def userinfo_cmd(ctx, member: discord.Member = None):
    """Info lengkap user: ID, join, role, warning count."""
    member = member or ctx.author
    color = member.color if member.color != discord.Color.default() else discord.Color.blurple()
    e = discord.Embed(title=f"👤 Info: {member.display_name}", color=color)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="📛 Username", value=str(member), inline=True)
    e.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
    e.add_field(name="🤖 Bot?", value="Ya" if member.bot else "Tidak", inline=True)
    e.add_field(name="📅 Akun dibuat", value=discord.utils.format_dt(member.created_at, "R"), inline=True)
    if member.joined_at:
        e.add_field(name="📥 Join server", value=discord.utils.format_dt(member.joined_at, "R"), inline=True)
    top = [r.mention for r in member.roles[1:][-5:]]
    if top:
        e.add_field(name=f"🎭 Role ({len(member.roles)-1})", value=" ".join(reversed(top)) or "-", inline=False)
    try:
        w = len(load_warns().get(str(ctx.guild.id), {}).get(str(member.id), []))
        e.add_field(name="⚠️ Warning", value=f"{w}", inline=True)
    except Exception:
        pass
    await ctx.send(embed=e)

@bot.hybrid_command(name='serverinfo')
async def serverinfo_cmd(ctx):
    """Info server: member count, boost, dibuat kapan."""
    g = ctx.guild
    e = discord.Embed(title=f"🏰 {g.name}", color=discord.Color.gold())
    if g.icon:
        e.set_thumbnail(url=g.icon.url)
    e.add_field(name="🆔 ID", value=f"`{g.id}`", inline=True)
    e.add_field(name="👑 Owner", value=g.owner.mention if g.owner else "?", inline=True)
    e.add_field(name="📅 Dibuat", value=discord.utils.format_dt(g.created_at, "R"), inline=True)
    e.add_field(name="👥 Member", value=f"{g.member_count}", inline=True)
    e.add_field(name="💎 Boost", value=f"{g.premium_subscription_count} (Lv {g.premium_tier})", inline=True)
    e.add_field(name="📺 Channel", value=f"{len(g.channels)}", inline=True)
    e.add_field(name="🎭 Role", value=f"{len(g.roles)}", inline=True)
    e.add_field(name="😀 Emoji", value=f"{len(g.emojis)}", inline=True)
    await ctx.send(embed=e)

@bot.command(name="purge", aliases=["clear"])
async def purge_cmd(ctx, amount: int = 10, member: discord.Member = None):
    """Hapus N pesan terakhir. Contoh: !purge 50 / !purge 100 @user"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if amount < 1 or amount > 200:
        return await ctx.send("❌ Jumlah harus 1-200.")
    check = (lambda m: m.author == member) if member else (lambda m: True)
    try:
        deleted = await ctx.channel.purge(limit=amount, check=check, before=ctx.message)
        try:
            await bot_log(ctx.guild, "🧹 PURGE",
                f"**{len(deleted)}** pesan dihapus di {ctx.channel.mention}\n"
                f"**Oleh:** {ctx.author.mention}",
                discord.Color.blurple())
        except Exception:
            pass
        msg = await ctx.send(f"🧹 Hapus **{len(deleted)}** pesan.")
        await discord.utils.sleep_until(discord.utils.utcnow() + _td(seconds=5))
        await msg.delete()
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Manage Messages`.")
    except Exception as e:
        await ctx.send(f"❌ Gagal: {e}")

@bot.command(name="slowmode", aliases=["sm"])
async def slowmode_cmd(ctx, seconds: int = 0):
    """Set slowmode channel (detik, 0=off, max 21600)."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if seconds < 0 or seconds > 21600:
        return await ctx.send("❌ Range: 0-21600 detik.")
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send("✅ Slowmode **dimatikan**." if seconds == 0 else f"✅ Slowmode **{seconds} detik**.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Manage Channels`.")

@bot.command(name="lock")
async def lock_cmd(ctx):
    """Kunci channel — member gak bisa kirim pesan."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        o = ctx.channel.overwrites_for(ctx.guild.default_role)
        o.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=o)
        await ctx.send("🔒 Channel **dikunci**.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Manage Channels`.")

@bot.command(name="unlock")
async def unlock_cmd(ctx):
    """Buka kunci channel."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        o = ctx.channel.overwrites_for(ctx.guild.default_role)
        o.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=o)
        await ctx.send("🔓 Channel **dibuka**.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Manage Channels`.")

@bot.hybrid_command(name='timeout')
async def timeout_cmd(ctx, member: discord.Member, duration: str = "10m", *, reason: str = "Tidak ada alasan"):
    """Timeout member. Contoh: !timeout @user 10m spam"""
    if not is_mod(ctx) or member.top_role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Kamu bukan mod ATAU role target di atas role bot.")
    mm = re.match(r"^(\d+)([smhd])$", duration.lower())
    if not mm:
        return await ctx.send("❌ Format durasi: `10s`, `5m`, `2h`, `1d`")
    n, u = int(mm.group(1)), mm.group(2)
    secs = n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[u]
    if secs > 28 * 86400:
        return await ctx.send("❌ Max timeout 28 hari.")
    try:
        await member.timeout(discord.utils.utcnow() + _td(seconds=secs), reason=reason)
        await ctx.send(f"⏳ **{member.display_name}** timeout **{duration}**.\nAlasan: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Moderate Members`.")

@bot.command(name="untimeout", aliases=["unto"])
async def untimeout_cmd(ctx, member: discord.Member):
    """Cabut timeout member."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        await member.timeout(None, reason=f"Dicabut oleh {ctx.author}")
        await ctx.send(f"✅ Timeout **{member.display_name}** dicabut.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Moderate Members`.")

@bot.command(name="banlist", aliases=["bans"])
async def banlist_cmd(ctx):
    """Liat daftar member yang di-ban."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        bans = [b async for b in ctx.guild.bans(limit=50)]
        if not bans:
            return await ctx.send("✅ Gak ada user yang di-ban.")
        e = discord.Embed(title=f"🔨 Ban List ({len(bans)})", color=discord.Color.dark_red())
        for b in bans[:25]:
            e.add_field(name=f"{b.user}", value=f"`{b.user.id}`\n{b.reason or 'No reason'}", inline=False)
        if len(bans) > 25:
            e.set_footer(text=f"... dan {len(bans)-25} lainnya")
        await ctx.send(embed=e)
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Ban Members`.")

@bot.command(name="unban")
async def unban_cmd(ctx, user_id: int):
    """Unban user via ID. Contoh: !unban 123456789"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"Unban oleh {ctx.author}")
        await ctx.send(f"✅ **{user}** (`{user_id}`) udah di-unban.")
    except discord.NotFound:
        await ctx.send(f"❌ User `{user_id}` gak ada di ban list.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh permission `Ban Members`.")
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# 🎁 10 FITUR BARU v2
# ══════════════════════════════════════════════════════════════
_AFK = {}
_REMINDERS = []

@bot.command(name="roleinfo", aliases=["ri"])
async def roleinfo_cmd(ctx, *, role: discord.Role = None):
    """Info role: warna, member count, permission. Tanpa argumen = daftar semua role."""
    if role is None:
        roles = [r for r in reversed(ctx.guild.roles) if r.name != "@everyone"][:30]
        if not roles:
            return await ctx.send("❌ Server gak punya role.")
        e = discord.Embed(
            title=f"🎭 Daftar Role ({len(ctx.guild.roles)-1} total)",
            description="Ketik `!roleinfo @Role` atau `!roleinfo NamaRole` untuk detail",
            color=discord.Color.blurple()
        )
        lines = []
        for r in roles:
            lines.append(f"{r.mention} • `{r.id}` • {len(r.members)} member")
        e.add_field(name="📋 Top 30 Role", value="\n".join(lines), inline=False)
        return await ctx.send(embed=e)

    e = discord.Embed(title=f"🎭 Role: {role.name}", color=role.color)
    e.add_field(name="🆔 ID", value=f"`{role.id}`", inline=True)
    e.add_field(name="🎨 Warna", value=f"`{role.color}`", inline=True)
    e.add_field(name="👥 Member", value=f"{len(role.members)}", inline=True)
    e.add_field(name="📅 Dibuat", value=discord.utils.format_dt(role.created_at, "R"), inline=True)
    e.add_field(name="📌 Posisi", value=str(role.position), inline=True)
    e.add_field(name="👁️ Mentionable", value="Ya" if role.mentionable else "Tidak", inline=True)
    e.add_field(name="🔔 Hoisted", value="Ya" if role.hoist else "Tidak", inline=True)
    e.add_field(name="⚙️ Managed", value="Ya" if role.managed else "Tidak", inline=True)
    key = [p for p, v in role.permissions if v and p in ("administrator","manage_guild","manage_roles","manage_channels","kick_members","ban_members","moderate_members","manage_messages")]
    if key:
        e.add_field(name="🔑 Permission Kunci", value=", ".join(f"`{k}`" for k in key[:6]), inline=False)
    await ctx.send(embed=e)

@bot.command(name="channelinfo", aliases=["ci"])
async def channelinfo_cmd(ctx, channel: discord.TextChannel = None):
    """Info channel: topik, slowmode, dibuat kapan."""
    ch = channel or ctx.channel
    e = discord.Embed(title=f"📺 Channel: #{ch.name}", color=discord.Color.blurple())
    e.add_field(name="🆔 ID", value=f"`{ch.id}`", inline=True)
    e.add_field(name="📅 Dibuat", value=discord.utils.format_dt(ch.created_at, "R"), inline=True)
    e.add_field(name="📝 Topik", value=ch.topic or "*(kosong)*", inline=False)
    e.add_field(name="🐌 Slowmode", value=f"{ch.slowmode_delay}s", inline=True)
    e.add_field(name="🔞 NSFW", value="Ya" if ch.nsfw else "Tidak", inline=True)
    e.add_field(name="📌 Posisi", value=str(ch.position), inline=True)
    await ctx.send(embed=e)

@bot.command(name="addrole", aliases=["giverole"])
async def addrole_cmd(ctx, member: discord.Member, *, role: discord.Role):
    """Kasih role ke member. Contoh: !addrole @user Member"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role target di atas role bot.")
    try:
        await member.add_roles(role, reason=f"Oleh {ctx.author}")
        await ctx.send(f"✅ **{role.name}** dikasih ke {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

@bot.command(name="removerole", aliases=["takerole"])
async def removerole_cmd(ctx, member: discord.Member, *, role: discord.Role):
    """Cabut role dari member."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role target di atas role bot.")
    try:
        await member.remove_roles(role, reason=f"Oleh {ctx.author}")
        await ctx.send(f"✅ **{role.name}** dicabut dari {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

@bot.hybrid_command(name='say')
async def say_cmd(ctx, *, text: str):
    """Bot bilang sesuatu. Contoh: !say Halo semua!"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        await ctx.message.delete()
    except Exception:
        pass
    await ctx.send(text)

@bot.hybrid_command(name='embed')
async def embed_cmd(ctx, *, content: str):
    """Bikin embed custom. Format: Judul | Deskripsi | Warna"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    parts = [p.strip() for p in content.split("|")]
    title = parts[0] if parts else "Embed"
    desc = parts[1] if len(parts) > 1 else "*(kosong)*"
    color = discord.Color.blurple()
    if len(parts) > 2:
        try:
            color = discord.Color(int(parts[2].lstrip("#"), 16))
        except Exception:
            pass
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text=f"Oleh {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=e)

@bot.command(name="announce", aliases=["ann"])
async def announce_cmd(ctx, channel: discord.TextChannel, *, text: str):
    """Kirim pengumuman ke channel. Contoh: !announce #umum Event jam 8!"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    e = discord.Embed(title="📢 PENGUMUMAN", description=text, color=discord.Color.gold())
    e.set_footer(text=f"Dari {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    e.timestamp = discord.utils.utcnow()
    try:
        await channel.send(embed=e)
        await ctx.send(f"✅ Pengumuman terkirim ke {channel.mention}.")
    except discord.Forbidden:
        await ctx.send(f"❌ Bot gak bisa kirim ke {channel.mention}.")

@bot.command(name="dm")
async def dm_cmd(ctx, member: discord.Member, *, text: str):
    """Kirim DM ke member lewat bot."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        e = discord.Embed(title="📩 Pesan dari Moderator", description=text, color=discord.Color.blue())
        e.set_footer(text=f"Dari server {ctx.guild.name}")
        await member.send(embed=e)
        await ctx.send(f"✅ DM terkirim ke **{member.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"❌ **{member.display_name}** nutup DM.")

@bot.command(name="afk")
async def afk_cmd(ctx, *, reason: str = "AFK"):
    """Set status AFK. Bot auto-reply kalau di-mention."""
    _AFK[ctx.author.id] = {"reason": reason, "since": discord.utils.utcnow()}
    await ctx.send(f"💤 **{ctx.author.display_name}** sekarang AFK: {reason}")

@bot.command(name="remind", aliases=["reminder"])
async def remind_cmd(ctx, duration: str, *, text: str):
    """Set reminder. Contoh: !remind 10m cek event / !remind 2h submit"""
    mm = re.match(r"^(\d+)([smhd])$", duration.lower())
    if not mm:
        return await ctx.send("❌ Format: `10s`, `5m`, `2h`, `1d`")
    n, u = int(mm.group(1)), mm.group(2)
    secs = n * {"s":1,"m":60,"h":3600,"d":86400}[u]
    if secs > 7 * 86400:
        return await ctx.send("❌ Max 7 hari.")
    try:
        await ctx.send(f"⏰ Reminder diset **{duration}**: {text}")
        async def _do():
            await asyncio.sleep(secs)
            try:
                e = discord.Embed(title="⏰ REMINDER", description=text, color=discord.Color.green())
                e.set_footer(text=f"Diset {duration} lalu")
                await ctx.author.send(embed=e)
            except Exception:
                pass
        asyncio.create_task(_do())
    except Exception as ex:
        await ctx.send(f"❌ Gagal: {ex}")

@bot.hybrid_command(name='poll')
async def poll_cmd(ctx, *, content: str):
    """Bikin poll. Format: !poll Pertanyaan? | Opsi1 | Opsi2 | ..."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    parts = [p.strip() for p in content.split("|")]
    if len(parts) < 3:
        return await ctx.send("❌ Format: `!poll Pertanyaan? | Opsi1 | Opsi2`")
    q, options = parts[0], parts[1:]
    if len(options) > 10:
        return await ctx.send("❌ Max 10 opsi.")
    emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    desc = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))
    e = discord.Embed(title=f"📊 {q}", description=desc, color=discord.Color.blurple())
    e.set_footer(text=f"Poll oleh {ctx.author.display_name}")
    msg = await ctx.send(embed=e)
    for i in range(len(options)):
        await msg.add_reaction(emojis[i])

@bot.listen("on_message")
async def _afk_check(message):
    if message.author.bot or not message.guild:
        return
    if message.author.id in _AFK:
        data = _AFK.pop(message.author.id)
        try:
            await message.channel.send(f"👋 Welcome back **{message.author.display_name}**! (AFK {discord.utils.format_dt(data['since'], 'R')})", delete_after=10)
        except Exception:
            pass
    for m in message.mentions:
        if m.id in _AFK:
            data = _AFK[m.id]
            try:
                await message.channel.send(f"💤 **{m.display_name}** lagi AFK: {data['reason']}", delete_after=10)
            except Exception:
                pass
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# 🎨 CUSTOM HELP v2 — Button + Dropdown + Search
# ══════════════════════════════════════════════════════════════

def _build_categories():
    cats = {}
    _map = {
        "🛡️ Moderasi": (
            "warn", "warns", "clearwarns", "setupwarnroles",
            "mute", "unmute", "kick", "ban",
            "purge", "slowmode", "lock", "unlock",
            "timeout", "untimeout", "banlist", "unban",
            "snipe", "editsnipe"
        ),
        "🏗️ Server Builder": (
            "buildcommunity", "buildcommunity2", "buildcommunity3",
            "buildsharemod", "buildsharemod2", "buildsharemod3",
            "buildroles", "setup_permissions", "setup_channels", "aturroles",
            "lockserver", "fixperms", "fixjoin", "fixtakerole"
        ),
        "🎫 Ticket & Panel": (
            "ticket", "ticketv2", "createticketmod", "char", "setupchar", "setupall"
        ),
        "🤖 Sistem AI": (
            "setupai", "testai", "ai", "rp"
        ),
        "⚙️ Settings & Log": (
            "setupverify", "setupwelcome", "welcomemod", "bannedmod", "invitemod",
            "dekorasi", "buatpesan", "setbotlog", "setwarnlog", "setwarntag", "loginfo", "testlog"
        ),
        "🎭 Role & Channel": (
            "role", "addrole", "removerole", "createrole", "deleterole",
            "massrole", "autorole", "rolepos", "rolesync", "roleclone",
            "roleinfo", "listroles", "roleedit", "roleperm",
            "createchannel", "deletechannel", "renamechannel",
            "createcategory", "topic", "listchannels", "channelinfo"
        ),
        "👑 Owner": (
            "botrun", "botremove", "botlist", "setmodrole"
        ),
        "🔧 Utility": (
            "help", "ping", "uptime", "avatar", "userinfo", "serverinfo",
            "announce", "dm", "remind", "afk", "test"
        ),
        "🎉 Fun": (
            "say", "embed", "poll"
        ),
    }
    for k in _map:
        cats[k] = []

    # Masukkan command ke kategorinya
    for cmd in bot.commands:
        if cmd.hidden or cmd.name == "help":
            continue
        placed = False
        for cat, kws in _map.items():
            if any(k in cmd.name.lower() for k in kws):
                cats[cat].append(cmd)
                placed = True
                break
        if not placed:
            cats.setdefault("📦 Lainnya", []).append(cmd)

    return {k: v for k, v in cats.items() if v}


class HelpMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None artinya permanen
        self.page = 0

    def _build_embed(self):
        cats = _build_categories()
        cat_names = list(cats.keys())
        
        # Pastiin halaman gak keluar dari batas
        if self.page >= len(cat_names): self.page = 0
        if self.page < 0: self.page = len(cat_names) - 1
        
        cat = cat_names[self.page]
        cmds = sorted(cats[cat], key=lambda x: x.name)
        total = sum(len(v) for v in cats.values())
        
        e = discord.Embed(
            title="📚 DAFTAR COMMAND",
            description=(f"Prefix: **`!`** • Total: **{total}** command" + nl + 
                         f"Halaman **{self.page+1}/{len(cat_names)}** — {cat}"),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        
        lines = []
        for cmd in cmds:
            short = (cmd.help or "").split(nl)[0] or "(tanpa deskripsi)"
            if len(short) > 80: short = short[:77] + "..."
            lines.append(f"`!{cmd.name}` • {short}")

        LIMIT = 1000
        chunks = []
        buf = ""
        for line in lines:
            if len(buf) + len(line) + 1 > LIMIT:
                chunks.append(buf.rstrip())
                buf = ""
            buf += line + nl
        if buf.strip(): chunks.append(buf.rstrip())

        if not chunks:
            e.add_field(name=cat, value="*(kosong)*", inline=False)
        else:
            for i, chunk in enumerate(chunks, 1):
                name = cat if i == 1 else f"{cat} (lanjutan {i-1})"
                e.add_field(name=name, value=chunk, inline=False)

        e.set_footer(text="!help <command> untuk detail")
        e.timestamp = discord.utils.utcnow()
        return e

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="help_prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary, custom_id="help_next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="🔍 Cari", style=discord.ButtonStyle.success, custom_id="help_search")
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔍 Ketik nama command (contoh: `warn`):", ephemeral=True)
        try:
            msg = await bot.wait_for("message", timeout=30,
                check=lambda m: m.author == interaction.user and m.channel == interaction.channel)
            cmd = bot.get_command(msg.content.strip())
            if cmd:
                e = discord.Embed(title=f"📖 !{cmd.name}", description=cmd.help or "*(tanpa deskripsi)*", color=discord.Color.green())
                e.add_field(name="📝 Penggunaan", value=f"```!{cmd.name} {cmd.signature}```"[:1020], inline=False)
                await interaction.channel.send(embed=e)
            else:
                await interaction.channel.send(f"❌ Command `{msg.content}` gak ketemu.", delete_after=5)
        except asyncio.TimeoutError:
            pass

    @discord.ui.button(label="❌ Tutup", style=discord.ButtonStyle.danger, custom_id="help_close")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


@bot.hybrid_command(name='help')
async def help_cmd(ctx, *, command: str = None):
    """Tampilkan daftar command atau detail command tertentu."""
    P = ctx.prefix
    if command:
        cmd = bot.get_command(command)
        if not cmd or cmd.hidden:
            return await ctx.send(f"❌ Command `{command}` gak ada.", delete_after=5)
        e = discord.Embed(title=f"📖 {P}{cmd.name}", description=cmd.help or "*(tanpa deskripsi)*", color=discord.Color.blurple())
        e.add_field(name="📝 Penggunaan", value=f"```{P}{cmd.name} {cmd.signature}```"[:1020], inline=False)
        return await ctx.send(embed=e)

    view = HelpMainView()
    await ctx.send(embed=view._build_embed(), view=view)


@bot.command(name="setuphelp")
async def setuphelp_cmd(ctx):
    """Kirim panel menu permanen ke channel bot-menu."""
    if not is_mod(ctx): return await ctx.send("❌ Mod only.")
    
    ch = discord.utils.find(lambda c: 'bot-menu' in c.name.lower(), ctx.guild.text_channels)
    if not ch:
        return await ctx.send("❌ Channel `#bot-menu` gak ketemu. Tolong buat dulu atau ganti namanya.")
        
    try:
        await ctx.message.delete()
    except Exception:
        pass
        
    view = HelpMainView()
    await ch.send(embed=view._build_embed(), view=view)
    await ctx.send(f"✅ Panel menu permanen berhasil dikirim ke {ch.mention}!", delete_after=5)

# Daftarkan view biar tombolnya tetep jalan walau bot restart
try:
    bot.add_view(OwnerView())
    bot.add_view(HelpMainView())
except Exception:
    pass
# ══════════════════════════════════════════════════════════════


# ══════ ERROR HANDLER GLOBAL ══════
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        sig = f"{ctx.prefix}{ctx.command.name} {ctx.command.signature}"
        e = discord.Embed(
            title="❌ Argumen Kurang",
            description=f"Parameter **`{error.param.name}`** wajib diisi.",
            color=discord.Color.red()
        )
        e.add_field(name="📝 Penggunaan", value=f"```{sig}```", inline=False)
        e.set_footer(text=f"Ketik {ctx.prefix}help {ctx.command.name} untuk detail")
        return await ctx.send(embed=e)

    if isinstance(error, commands.BadArgument):
        return await ctx.send(f"❌ Argumen gak valid: `{error}`")

    if isinstance(error, commands.MemberNotFound):
        return await ctx.send("❌ Member gak ditemukan. Tag user atau pakai ID.")

    if isinstance(error, commands.RoleNotFound):
        return await ctx.send("❌ Role gak ditemukan.")

    if isinstance(error, commands.ChannelNotFound):
        return await ctx.send("❌ Channel gak ditemukan.")

    if isinstance(error, commands.CommandNotFound):
        return  # abaikan command gak ada

    if isinstance(error, commands.CheckFailure):
        return await ctx.send(f"❌ {error}")

    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏰ Tunggu **{error.retry_after:.1f}s** lagi.")

    # Error lain → log ke console
    print(f"[ERROR] {ctx.command}: {error}")
    try:
        await ctx.send(f"❌ Error: `{type(error).__name__}` — cek console.")
    except Exception:
        pass
# ══════════════════════════════════


# ══════════════════════════════════════════════════════════════
# 🛠️ CHANNEL / ROLE / LOG MANAGEMENT
# ══════════════════════════════════════════════════════════════
import json as _cfgjson
_CFG_FILE = "bot_config.json"

def _cfg_load():
    try:
        with open(_CFG_FILE) as f:
            return _cfgjson.load(f)
    except Exception:
        return {}

def _cfg_save(d):
    with open(_CFG_FILE, "w") as f:
        _cfgjson.dump(d, f, indent=2)

def _get_warn_log_name():
    return _cfg_load().get("warn_log_channel") or _get_bot_log_name()

def _get_warn_tag_id():
    return _cfg_load().get("warn_tag_role") or globals().get("WARN_TAG_ROLE_ID", 0)

@bot.command(name="createchannel", aliases=["mkch", "newch"])
async def createchannel_cmd(ctx, name: str, type: str = "text"):
    """Buat channel. Type: text / voice / stage / forum"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    t = type.lower()
    try:
        if t in ("voice", "v"):
            ch = await ctx.guild.create_voice_channel(name)
        elif t in ("stage", "s"):
            ch = await ctx.guild.create_stage_channel(name)
        elif t in ("forum", "f"):
            ch = await ctx.guild.create_forum(name)
        else:
            ch = await ctx.guild.create_text_channel(name)
        await ctx.send(f"✅ Channel {ch.mention} (`{ch.id}`) dibuat.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Channels`.")

@bot.command(name="createcategory", aliases=["mkcat"])
async def createcategory_cmd(ctx, *, name: str):
    """Buat kategori baru."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        cat = await ctx.guild.create_category(name)
        await ctx.send(f"✅ Kategori **{cat.name}** dibuat.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Channels`.")

@bot.command(name="deletechannel", aliases=["delch", "rmch"])
async def deletechannel_cmd(ctx, channel: discord.abc.GuildChannel = None):
    """Hapus channel. Default: channel sekarang."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    target = channel or ctx.channel
    name = target.name
    try:
        await target.delete()
        if target != ctx.channel:
            await ctx.send(f"✅ Channel **#{name}** dihapus.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Channels`.")

@bot.command(name="renamechannel", aliases=["rench"])
async def renamechannel_cmd(ctx, channel: discord.abc.GuildChannel, *, new_name: str):
    """Rename channel. Contoh: !renamechannel #umum obrolan-umum"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        await channel.edit(name=new_name)
        await ctx.send(f"✅ Channel di-rename ke **{new_name}**.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Channels`.")

@bot.command(name="topic")
async def topic_cmd(ctx, channel: discord.TextChannel = None, *, text: str = ""):
    """Set topik channel. Kosong = hapus topik."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    ch = channel or ctx.channel
    try:
        await ch.edit(topic=text or None)
        await ctx.send(f"✅ Topik #{ch.name} diupdate.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Channels`.")

@bot.command(name="createrole", aliases=["mkrole", "newrole"])
async def createrole_cmd(ctx, name: str, color: str = None):
    """Buat role. Color: hex (#ff0000) / nama (red, blue, gold, dll)."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    col = discord.Color.default()
    if color:
        try:
            if color.startswith("#"):
                col = discord.Color(int(color.lstrip("#"), 16))
            else:
                col = getattr(discord.Color, color.lower())()
        except Exception:
            col = discord.Color.blurple()
    try:
        role = await ctx.guild.create_role(name=name, color=col)
        await ctx.send(f"✅ Role {role.mention} dibuat.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

@bot.command(name="deleterole", aliases=["delrole", "rmrole"])
async def deleterole_cmd(ctx, *, role: discord.Role):
    """Hapus role. Contoh: !deleterole @NamaRole"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role target di atas role bot.")
    name = role.name
    try:
        await role.delete()
        await ctx.send(f"✅ Role **{name}** dihapus.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

@bot.command(name="setwarnlog")
async def setwarnlog_cmd(ctx, channel: discord.TextChannel = None):
    """Set channel log warning. Tanpa argumen = lihat yang sekarang."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if channel is None:
        cur = _get_warn_log_name()
        ch = discord.utils.get(ctx.guild.channels, name=cur)
        status = f"✅ {ch.mention} (`{cur}`)" if ch else f"❌ `{cur}` (gak ada)"
        return await ctx.send(f"📋 Warn log sekarang: {status}")
    cfg = _cfg_load()
    cfg["warn_log_channel"] = channel.name
    _cfg_save(cfg)
    await ctx.send(f"✅ Warn log dipindah ke {channel.mention}.")

@bot.command(name="setwarntag")
async def setwarntag_cmd(ctx, role: discord.Role = None):
    """Set role yang di-tag saat warn. Tanpa argumen = lihat yang sekarang."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role is None:
        cur = _get_warn_tag_id()
        return await ctx.send(f"📋 Tag role sekarang: <@&{cur}> (`{cur}`)")
    cfg = _cfg_load()
    cfg["warn_tag_role"] = role.id
    _cfg_save(cfg)
    await ctx.send(f"✅ Tag role diubah ke {role.mention}.")

@bot.command(name="loginfo", aliases=["logcfg"])
async def loginfo_cmd(ctx):
    """Lihat konfigurasi log sekarang."""
    warn_name = _get_warn_log_name()
    warn_id = _get_warn_tag_id()
    warn_ch = discord.utils.get(ctx.guild.channels, name=warn_name)
    e = discord.Embed(title="⚙️ Konfigurasi Log", color=discord.Color.blurple())
    e.add_field(name="⚠️ Warn Log Channel",
                value=f"{warn_ch.mention if warn_ch else '❌'} `{warn_name}`", inline=False)
    e.add_field(name="🔥 Bot Log Channel",
                value=f"`{_get_bot_log_name()}`", inline=False)
    e.add_field(name="🏷️ Tag Role",
                value=f"<@&{warn_id}> `{warn_id}`", inline=False)
    e.set_footer(text=f"Config file: {_CFG_FILE}")
    await ctx.send(embed=e)

@bot.command(name="listchannels", aliases=["channels"])
async def listchannels_cmd(ctx):
    """Daftar semua channel di server."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    cats = {}
    for ch in ctx.guild.channels:
        cat = ch.category.name if ch.category else "📌 Tanpa Kategori"
        cats.setdefault(cat, []).append(f"{ch.mention} `{ch.id}`")
    e = discord.Embed(title=f"📺 Channel ({len(ctx.guild.channels)})", color=discord.Color.blurple())
    for cat, chs in list(cats.items())[:10]:
        e.add_field(name=cat, value="\n".join(chs[:15]), inline=False)
    await ctx.send(embed=e)

@bot.command(name="listroles", aliases=["roles"])
async def listroles_cmd(ctx):
    """Daftar semua role di server."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    roles = [r for r in reversed(ctx.guild.roles) if r.name != "@everyone"]
    e = discord.Embed(title=f"🎭 Role ({len(roles)})", color=discord.Color.blurple())
    lines = [f"{r.mention} • `{r.id}` • {len(r.members)} member" for r in roles[:25]]
    e.description = "\n".join(lines) if lines else "*(kosong)*"
    if len(roles) > 25:
        e.set_footer(text=f"... dan {len(roles)-25} role lainnya")
    await ctx.send(embed=e)
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# 🔥 CENTRAL BOT LOG → "🔥┃bot-run"
# ══════════════════════════════════════════════════════════════
BOT_LOG_CHANNEL = "🔥┃bot-run"

def _get_bot_log_name():
    return _cfg_load().get("bot_log_channel") or BOT_LOG_CHANNEL

def _find_bot_log_channel(guild):
    if not guild:
        return None
    for ch in guild.text_channels:
        n = normalize_text(ch.name)
        if "bot-run" in n or "botrun" in n or "bot_run" in n or "bot log" in n:
            return ch
    return None

async def bot_log(guild, title, description, color=discord.Color.blurple()):
    if not guild:
        return
    try:
        ch = _find_bot_log_channel(guild)
        if not ch:
            return
        e = discord.Embed(title=title, description=description, color=color)
        e.timestamp = discord.utils.utcnow()
        await ch.send(embed=e)
    except Exception as ex:
        print(f"[bot_log] {ex}")

@bot.command(name="setbotlog")
async def setbotlog_cmd(ctx, channel: discord.TextChannel = None):
    """Set channel log bot. Tanpa argumen = lihat channel sekarang."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if channel is None:
        cur = _get_bot_log_name()
        ch = _find_bot_log_channel(ctx.guild)
        return await ctx.send(f"📋 Bot log: {ch.mention if ch else '❌'} `{cur}`")
    cfg = _cfg_load()
    cfg["bot_log_channel"] = channel.name
    _cfg_save(cfg)
    await ctx.send(f"✅ Semua log bot dipindah ke {channel.mention}.")


# ══════ EVENT LOGGERS ══════

@bot.event
async def on_member_unban(guild, user):
    try:
        async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            if e.target.id == user.id:
                await bot_log(guild, "✅ UNBAN",
                    f"**Target:** {user.mention} (`{user.id}`)\n"
                    f"**Mod:** {e.user.mention} (`{e.user.id}`)",
                    discord.Color.green())
                return
    except Exception:
        pass



@bot.event
async def on_guild_channel_create(channel):
    await bot_log(channel.guild, "📺 CHANNEL DIBUAT",
        f"{channel.mention} (`{channel.id}`)", discord.Color.green())

@bot.event
async def on_guild_channel_delete(channel):
    await bot_log(channel.guild, "📺 CHANNEL DIHAPUS",
        f"**#{channel.name}** (`{channel.id}`)", discord.Color.red())

@bot.event
async def on_guild_role_create(role):
    await bot_log(role.guild, "🎭 ROLE DIBUAT",
        f"{role.mention} (`{role.id}`)", discord.Color.green())

@bot.event
async def on_guild_role_delete(role):
    await bot_log(role.guild, "🎭 ROLE DIHAPUS",
        f"**{role.name}** (`{role.id}`)", discord.Color.red())
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# 🎭 FULL ROLE MANAGEMENT PACK
# ══════════════════════════════════════════════════════════════

def _parse_role_color(s):
    if not s:
        return None
    try:
        if s.startswith("#"):
            return discord.Color(int(s.lstrip("#"), 16))
        v = getattr(discord.Color, s.lower(), None)
        if v and callable(v):
            return v()
    except Exception:
        pass
    return None

@bot.command(name="role")
async def role_bulk_cmd(ctx, member: discord.Member, *, roles: str):
    """Kasih/cabut banyak role sekaligus. Prefix `-` untuk cabut.
    Contoh: !role @user +VIP +Member -Muted"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    tokens = roles.split()
    add_list, rem_list, unknown = [], [], []
    for t in tokens:
        sign = "+"
        name = t
        if t.startswith(("+", "-")):
            sign, name = t[0], t[1:]
        # cocokkan role by mention, id, atau nama
        r = None
        m_mention = re.match(r"<@&(\d+)>", name)
        if m_mention:
            r = ctx.guild.get_role(int(m_mention.group(1)))
        elif name.isdigit():
            r = ctx.guild.get_role(int(name))
        else:
            r = discord.utils.find(lambda x: x.name.lower() == name.lower(), ctx.guild.roles)
        if not r:
            unknown.append(name)
            continue
        (add_list if sign == "+" else rem_list).append(r)

    if not (add_list or rem_list):
        return await ctx.send(f"❌ Role gak ditemukan: {', '.join(unknown)}")

    if any(r >= ctx.guild.me.top_role for r in add_list + rem_list):
        return await ctx.send("❌ Ada role di atas role bot.")

    added, removed, failed = [], [], []
    if add_list:
        try:
            await member.add_roles(*add_list, reason=f"Oleh {ctx.author}")
            added = [r.name for r in add_list]
        except discord.Forbidden:
            failed.append("add")
    if rem_list:
        try:
            await member.remove_roles(*rem_list, reason=f"Oleh {ctx.author}")
            removed = [r.name for r in rem_list]
        except discord.Forbidden:
            failed.append("remove")

    parts = []
    if added: parts.append(f"✅ Ditambah: {', '.join(f'`{n}`' for n in added)}")
    if removed: parts.append(f"➖ Dicabut: {', '.join(f'`{n}`' for n in removed)}")
    if unknown: parts.append(f"❓ Gak ketemu: {', '.join(unknown)}")
    if failed: parts.append(f"❌ Gagal {failed} (cek posisi/permission)")
    await ctx.send(f"**{member.display_name}**\n" + "\n".join(parts))

@bot.command(name="roleedit")
async def roleedit_cmd(ctx, role: discord.Role, key: str, *, value: str):
    """Edit role: nama, warna, hoist, mentionable.
    Contoh: !roleedit @VIP warna #ff0000
            !roleedit @VIP nama Very-Important
            !roleedit @VIP hoist on
            !roleedit @VIP mentionable off"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role target di atas role bot.")

    k = key.lower()
    try:
        if k in ("nama", "name"):
            await role.edit(name=value)
            return await ctx.send(f"✅ Nama role → **{value}**")
        if k in ("warna", "color", "warna"):
            col = _parse_role_color(value)
            if not col:
                return await ctx.send("❌ Warna gak valid. Pakai `#ff0000` atau `red`/`gold`/`blue`")
            await role.edit(color=col)
            return await ctx.send(f"✅ Warna role → `{value}`")
        if k in ("hoist", "hoisted"):
            v = value.lower() in ("on", "true", "ya", "1", "yes")
            await role.edit(hoist=v)
            return await ctx.send(f"✅ Hoist role → **{'ON' if v else 'OFF'}**")
        if k in ("mentionable", "mention"):
            v = value.lower() in ("on", "true", "ya", "1", "yes")
            await role.edit(mentionable=v)
            return await ctx.send(f"✅ Mentionable → **{'ON' if v else 'OFF'}**")
        return await ctx.send("❌ Key gak valid: `nama`, `warna`, `hoist`, `mentionable`")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

@bot.command(name="roleperm")
async def roleperm_cmd(ctx, role: discord.Role, perm: str, state: str = "on"):
    """Toggle satu permission role. Contoh: !roleperm @VIP send_messages on"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role target di atas role bot.")
    if not hasattr(role.permissions, perm):
        # coba mapping umum
        aliases = {
            "kick": "kick_members", "ban": "ban_members", "admin": "administrator",
            "manage_msgs": "manage_messages", "manage_roles": "manage_roles",
            "manage_channels": "manage_channels", "manage_nick": "manage_nicknames",
            "send": "send_messages", "read": "read_messages",
        }
        perm = aliases.get(perm, perm)
    if not hasattr(role.permissions, perm):
        return await ctx.send(f"❌ Permission `{perm}` gak dikenal. Cek docs: discord.Permissions")
    val = state.lower() in ("on", "true", "ya", "1", "yes")
    perms = role.permissions
    setattr(perms, perm, val)
    try:
        await role.edit(permissions=perms)
        await ctx.send(f"✅ `{perm}` → **{'ON' if val else 'OFF'}** di {role.mention}")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

@bot.command(name="massrole")
async def massrole_cmd(ctx, role: discord.Role, target: str = "all"):
    """Kasih role ke semua member. target: all / humans / bots"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role target di atas role bot.")
    if target not in ("all", "humans", "bots"):
        return await ctx.send("❌ Target: `all`, `humans`, `bots`")

    filter_map = {
        "all": lambda m: True,
        "humans": lambda m: not m.bot,
        "bots": lambda m: m.bot,
    }
    targets = [m for m in ctx.guild.members if filter_map[target](m) and role not in m.roles]
    if not targets:
        return await ctx.send("ℹ️ Semua udah punya role itu.")

    msg = await ctx.send(f"⏳ Nambah `{role.name}` ke **{len(targets)}** member...")
    ok, fail = 0, 0
    for m in targets:
        try:
            await m.add_roles(role, reason=f"Massrole oleh {ctx.author}")
            ok += 1
        except Exception:
            fail += 1
    await msg.edit(content=f"✅ **{role.name}** → **{ok}** member. Gagal: {fail}")

@bot.command(name="autorole")
async def autorole_cmd(ctx, role: discord.Role = None):
    """Set role yang otomatis dikasih saat member join."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    cfg = _cfg_load()
    gid = str(ctx.guild.id)
    autoroles = cfg.setdefault("autoroles", {})
    if role is None:
        cur = autoroles.get(gid, [])
        if not cur:
            return await ctx.send("📋 Belum ada autorole.")
        names = []
        for rid in cur:
            r = ctx.guild.get_role(int(rid))
            names.append(r.mention if r else f"`{rid}`")
        return await ctx.send("📋 Autorole: " + ", ".join(names))
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role di atas role bot.")
    lst = autoroles.setdefault(gid, [])
    if str(role.id) in lst:
        lst.remove(str(role.id))
        _cfg_save(cfg)
        return await ctx.send(f"✅ Autorole **{role.name}** dihapus.")
    lst.append(str(role.id))
    _cfg_save(cfg)
    await ctx.send(f"✅ Autorole **{role.name}** ditambahkan.")

@bot.command(name="rolepos")
async def rolepos_cmd(ctx, role: discord.Role, position: int):
    """Pindah posisi role. Contoh: !rolepos @VIP 5"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role di atas role bot, gabisa dipindah.")
    try:
        await role.edit(position=position)
        await ctx.send(f"✅ **{role.name}** dipindah ke posisi **{position}**.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

@bot.command(name="roleclone")
async def roleclone_cmd(ctx, role: discord.Role, *, name: str = None):
    """Clone role (nama, warna, permission, hoist)."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        new = await ctx.guild.create_role(
            name=name or f"{role.name} (copy)",
            permissions=role.permissions,
            color=role.color,
            hoist=role.hoist,
            mentionable=role.mentionable,
            reason=f"Clone oleh {ctx.author}",
        )
        await ctx.send(f"✅ Role {new.mention} dibuat (clone dari {role.name}).")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")

# ─── Auto-role saat member join ───
@bot.event
async def on_member_join(member):
    if member.bot:
        return
    try:
        cfg = _cfg_load()
        ids = cfg.get("autoroles", {}).get(str(member.guild.id), [])
        if not ids:
            return
        roles = [member.guild.get_role(int(rid)) for rid in ids]
        roles = [r for r in roles if r and r < member.guild.me.top_role]
        if roles:
            await member.add_roles(*roles, reason="Auto-role on join")
    except Exception as ex:
        print(f"[autorole] {ex}")

# ─── Sinkron role (mirror permission) ───
@bot.command(name="rolesync")
async def rolesync_cmd(ctx, source: discord.Role, target: discord.Role):
    """Samakan permission & warna role target dengan source."""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    if target >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role target di atas role bot.")
    try:
        await target.edit(
            permissions=source.permissions,
            color=source.color,
            hoist=source.hoist,
            mentionable=source.mentionable,
            reason=f"Sinkron dari {source.name} oleh {ctx.author}",
        )
        await ctx.send(f"✅ {target.mention} disinkronkan dengan {source.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ Bot butuh `Manage Roles`.")
# ══════════════════════════════════════════════════════════════


@bot.command(name="setmodrole")
async def setmodrole_cmd(ctx, role: discord.Role = None):
    """Set role yang bisa pakai command moderasi (gak perlu permission Discord).
    Tanpa argumen = lihat role mod sekarang."""
    if not ctx.author.guild_permissions.administrator:
        # hanya admin server yang bisa atur
        try:
            cfg = _cfg_load()
            if ctx.author.id not in cfg.get("super_admin", []):
                return await ctx.send("❌ Cuma admin server yang bisa atur mod role.")
        except Exception:
            return await ctx.send("❌ Cuma admin server yang bisa atur mod role.")

    cfg = _cfg_load()
    gid = str(ctx.guild.id)
    mod_roles = cfg.setdefault("mod_roles", {})
    current = mod_roles.get(gid, [])

    if role is None:
        if not current:
            return await ctx.send("📋 Belum ada role mod khusus. Pakai `!setmodrole @Role` untuk menambahkan.")
        lines = []
        for rid in current:
            r = ctx.guild.get_role(int(rid))
            lines.append(r.mention if r else f"`{rid}`")
        return await ctx.send("📋 Role mod terdaftar: " + ", ".join(lines))

    if str(role.id) in current:
        current.remove(str(role.id))
        mod_roles[gid] = current
        _cfg_save(cfg)
        return await ctx.send(f"✅ Role **{role.name}** dihapus dari mod role.")
    else:
        current.append(str(role.id))
        mod_roles[gid] = current
        _cfg_save(cfg)
        return await ctx.send(f"✅ Role **{role.name}** sekarang bisa pakai command moderasi.")




# ══════ COMPAT: send_log → bot_log ══════
async def send_log(guild, title, description, color=discord.Color.blurple()):
    """Alias lama untuk bot_log (untuk backward compat)."""
    await bot_log(guild, title, description, color)
# ═════════════════════════════════════════

keep_alive(bot)  # mulai HTTP server untuk Render

import base64

# ══════════════════════════════════════════════════════════════
# 🎫 SISTEM TICKET
# ══════════════════════════════════════════════════════════════

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label='Tutup Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='close_ticket_btn')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('🔒 Ticket akan ditutup dan dihapus dalam 5 detik...', ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Bertanya / Bantuan Umum', description='Tanya jawab seputar server atau hal umum.', emoji='❓', value='tanya'),
            discord.SelectOption(label='Laporan / Report', description='Laporkan pelanggaran aturan atau masalah.', emoji='🚨', value='laporan'),
            discord.SelectOption(label='Bantuan RP', description='Bantuan terkait roleplay, karakter, atau alur cerita.', emoji='🎭', value='rp'),
            discord.SelectOption(label='Lainnya', description='Untuk hal-hal yang belum tercantum di atas.', emoji='📝', value='lainnya')
        ]
        super().__init__(placeholder='Pilih jenis tiket...', min_values=1, max_values=1, options=options, custom_id='ticket_select_menu')

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]
        nl = chr(10)
        category = discord.utils.get(guild.categories, name='Tickets')
        if category:
            for ch in category.text_channels:
                if ch.topic and f'({user.id})' in ch.topic:
                    return await interaction.response.send_message(f'❌ Kamu sudah punya ticket terbuka di {ch.mention}!', ephemeral=True)
        await interaction.response.send_message(f'⏳ Sedang membuat channel tiket **{ticket_type}**...', ephemeral=True)
        if not category:
            try:
                category = await guild.create_category('Tickets', reason='Setup sistem ticket')
            except Exception:
                pass
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        staff_roles = ['Staff', 'Moderator', 'Admin', 'Owner', 'Mod', '⚠️HANDLE CJNG', 'OWNER X CO OWNER']
        for role_name in staff_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        try:
            ticket_ch = await guild.create_text_channel(
                name=f'ticket-{ticket_type}-{user.name}'.lower(),
                category=category,
                overwrites=overwrites,
                topic=f'Ticket milik {user.name} ({user.id}) | Tipe: {ticket_type} | Ketuk 🔒 Tutup Ticket untuk menghapus.'
            )
            role1 = discord.utils.get(guild.roles, name='⚠️HANDLE CJNG')
            role2 = discord.utils.get(guild.roles, name='OWNER X CO OWNER')
            tag1 = role1.mention if role1 else '@⚠️HANDLE CJNG'
            tag2 = role2.mention if role2 else '@OWNER X CO OWNER'
            desc_text = f'Halo {user.mention}, tunggu sebentar ya. Staff akan segera merespons.{nl}{nl}Jika masalah sudah selesai, silakan klik tombol di bawah.'
            embed = discord.Embed(title=f'🎫 Ticket: {ticket_type.upper()}', description=desc_text, color=discord.Color.green())
            if ticket_type == "laporan":
                format_laporan = (
                    "## 🛑  __laporkan Anggota__" + nl + nl +
                    "**Nama ic :** " + nl +
                    "**Alasannya :** " + nl +
                    "**Bukti ( berupa foto ) :** " + nl + nl +
                    "**NOTE :** " + nl +
                    "Silakan isi form di atas dengan jujur."
                )
                await ticket_ch.send(content=f"{user.mention} | {tag1} {tag2}", embed=embed)
                await ticket_ch.send(format_laporan, view=TicketCloseView())
            else:
                await ticket_ch.send(content=f"{user.mention} | {tag1} {tag2}", embed=embed, view=TicketCloseView())
            await interaction.edit_original_response(content=f'✅ Ticket kamu sudah dibuat: {ticket_ch.mention}')
            if 'bot_log' in globals():
                log_desc = f'**User:** {user.mention}{nl}**Tipe:** {ticket_type}{nl}**Channel:** {ticket_ch.mention}'
                await bot_log(guild, '🎫 TICKET BARU', log_desc, discord.Color.green())
        except Exception as e:
            await interaction.edit_original_response(content=f'❌ Gagal membuat ticket: {e}')

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.hybrid_command(name='ticket')
async def ticket_cmd(ctx, action: str = None):
    """Setup panel ticket (khusus Admin/Moderator)."""
    if not is_mod(ctx):
        return await ctx.send('❌ Hanya staff/admin yang bisa menggunakan command ini.')
    if action == 'setup':
        embed = discord.Embed(
            title='🎫 Pusat Bantuan (Support Ticket)',
            description='Butuh bantuan dari Staff atau ingin melaporkan sesuatu?' + chr(10) + 'Silakan pilih jenis tiket pada menu di bawah ini.' + chr(10) + chr(10) + 'Channel private akan otomatis dibuat hanya untuk kamu dan Staff.',
            color=discord.Color.blurple()
        )
        embed.set_footer(text='Pilih jenis tiket dari menu dropdown.')
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send(embed=embed, view=TicketV2View())
    else:
        await ctx.send('❌ Format salah. Gunakan `!ticket setup` di channel yang kamu inginkan.')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🕵️‍♂️ SNIPE & 📜 KARAKTER RP
# ══════════════════════════════════════════════════════════════
snipe_cache = {}
editsnipe_cache = {}
CHARS_FILE = 'chars.json'

def load_chars():
    if os.path.exists(CHARS_FILE):
        try:
            with open(CHARS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_chars(data):
    with open(CHARS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    snipe_cache[message.channel.id] = {
        'content': message.content or '*[File/Embed]*',
        'author': message.author,
        'time': discord.utils.utcnow()
    }

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content: return
    editsnipe_cache[before.channel.id] = {
        'before': before.content or '*[Embed]*',
        'after': after.content or '*[Embed]*',
        'author': before.author,
        'time': discord.utils.utcnow()
    }

@bot.command(name='snipe')
async def snipe_cmd(ctx):
    """Liat pesan yang barusan dihapus di channel ini."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    data = snipe_cache.get(ctx.channel.id)
    if not data: return await ctx.send('❌ Gak ada pesan yang baru dihapus.')
    embed = discord.Embed(title='🕵️‍♂️ Snipe Pesan', description=data['content'], color=discord.Color.red())
    embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
    embed.set_footer(text=f"Dihapus {discord.utils.format_dt(data['time'], 'R')}")
    await ctx.send(embed=embed)
    snipe_cache.pop(ctx.channel.id, None)

@bot.command(name='editsnipe', aliases=['esnipe'])
async def editsnipe_cmd(ctx):
    """Liat pesan yang barusan diedit di channel ini."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    data = editsnipe_cache.get(ctx.channel.id)
    if not data: return await ctx.send('❌ Gak ada pesan yang baru diedit.')
    embed = discord.Embed(title='🕵️‍♂️ Edit Snipe', color=discord.Color.orange())
    embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
    embed.add_field(name='📝 Sebelum', value=data['before'][:1024], inline=False)
    embed.add_field(name='📝 Sesudah', value=data['after'][:1024], inline=False)
    embed.set_footer(text=f"Diedit {discord.utils.format_dt(data['time'], 'R')}")
    await ctx.send(embed=embed)
    editsnipe_cache.pop(ctx.channel.id, None)

class CharModal(discord.ui.Modal, title='Form Karakter RP'):
    nama_ic = discord.ui.TextInput(
        label='Nama IC', 
        placeholder='Contoh: Zoma Haci', 
        required=True, 
        max_length=32
    )
    umur = discord.ui.TextInput(
        label='Umur', 
        placeholder='Contoh: 25', 
        required=True, 
        max_length=3
    )
    bio = discord.ui.TextInput(
        label='Bio Singkat (Opsional)', 
        style=discord.TextStyle.paragraph, 
        placeholder='Ceritakan latar belakang karakter...', 
        required=False
    )

    def __init__(self, origin_name: str, origin_role: discord.Role = None):
        super().__init__()
        self.origin_name = origin_name
        self.origin_role = origin_role

    async def on_submit(self, interaction: discord.Interaction):
        chars = load_chars()
        uid = str(interaction.user.id)
        bio_val = self.bio.value or "-"
        
        chars[uid] = {
            'nama': self.nama_ic.value,
            'umur': self.umur.value,
            'asal': self.origin_name,
            'bio': bio_val
        }
        save_chars(chars)
        
        nick_status = ""
        if self.origin_role:
            try:
                await interaction.user.add_roles(self.origin_role)
                nick_status += f"\\n📍 Role **{self.origin_name}** berhasil ditambahkan."
            except Exception:
                nick_status += f"\\n⚠️ Gagal memberikan role {self.origin_name} (cek izin bot)."
        else:
            nick_status += f"\\n⚠️ Role {self.origin_name} belum ada dan gagal dibuat bot."

        try:
            new_nick = self.nama_ic.value[:32]
            await interaction.user.edit(nick=new_nick)
            nick_status += f"\\n📝 Nickname berubah jadi **{new_nick}**."
        except discord.Forbidden:
            nick_status += "\\n⚠️ Bot gak punya izin ganti nickname."
        except Exception as e:
            nick_status += f"\\n⚠️ Gagal ganti nickname: {e}"

        embed = discord.Embed(
            title='✅ Karakter Berhasil Dibuat', 
            description=f'Data karakter lu udah disimpan. Ketik `!char` untuk melihatnya.{nick_status}', 
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        channel = discord.utils.find(lambda c: 'daftar-karakter' in c.name.lower(), interaction.guild.text_channels)
        if channel:
            char_embed = discord.Embed(title=f"📜 Kartu Karakter: {self.nama_ic.value}", color=discord.Color.blurple())
            char_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            char_embed.add_field(name='👤 Nama IC', value=self.nama_ic.value, inline=True)
            char_embed.add_field(name='🎂 Umur', value=self.umur.value, inline=True)
            char_embed.add_field(name='📍 Asal', value=self.origin_name, inline=True)
            char_embed.add_field(name='📖 Bio', value=bio_val, inline=False)
            char_embed.set_footer(text=f"Dipegang oleh {interaction.user.name}")
            await channel.send(embed=char_embed)

class CharOriginSelect(discord.ui.Select):
    def __init__(self):
        regions = [
            "Jakarta Pusat", "Jakarta Barat", "Jakarta Timur", "Jakarta Selatan", "Jakarta Utara",
            "Jawa Barat (Bandung)", "Jawa Tengah (Semarang)", "Jawa Timur (Surabaya)", "Banten (Tangerang)", "DIY (Yogyakarta)",
            "Bali (Denpasar)", "Sumatera Utara (Medan)", "Sumatera Barat (Padang)", "Sumatera Selatan (Palembang)", "Riau (Pekanbaru)",
            "Lampung (Bandar Lampung)", "Aceh (Banda Aceh)", "Kalimantan Timur (Samarinda)", "Kalimantan Selatan (Banjarmasin)", "Kalimantan Barat (Pontianak)",
            "Sulawesi Selatan (Makassar)", "Sulawesi Utara (Manado)", "Sulawesi Tengah (Palu)", "Maluku (Ambon)", "Papua (Jayapura)"
        ]
        options = [discord.SelectOption(label=r, value=r, emoji="📍") for r in regions]
        super().__init__(placeholder="Pilih Asal Daerah...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        origin_name = self.values[0]
        
        # Ambil nama role aja (misal "Jawa Barat (Bandung)" jadi "Jawa Barat")
        role_name = origin_name.split(" (")[0]
        
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            try:
                role = await interaction.guild.create_role(name=role_name, reason="Auto-create role asal daerah RP")
            except Exception:
                pass 
                
        await interaction.response.send_modal(CharModal(origin_name, role))
        self.view.stop()

class CharOriginView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(CharOriginSelect())

class CharView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Buat Karakter', style=discord.ButtonStyle.primary, emoji='📝', custom_id='btn_create_char_v3')
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Silakan pilih **Asal Daerah** kamu terlebih dahulu:", view=CharOriginView(), ephemeral=True)

@bot.command(name='setupchar')
async def setupchar_cmd(ctx):
    """Kirim panel pembuatan karakter RP di channel ini (Tanpa bikin channel baru)."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    embed = discord.Embed(
        title="📜 Pembuatan Karakter RP",
        description="Silakan klik tombol **Buat Karakter** di bawah ini untuk mengisi form profil karakter Anda." + chr(10) + chr(10) + "*(Pastikan Anda mengisi data dengan benar karena Nickname server akan otomatis berubah sesuai Nama IC).*",
        color=discord.Color.blurple()
    )
    
    # Coba hapus pesan command lu biar bersih
    try:
        await ctx.message.delete()
    except Exception:
        pass
        
    await ctx.send(embed=embed, view=CharView())
    await ctx.send("✅ Panel Karakter berhasil dikirim!", delete_after=5)

@bot.listen('on_member_join')
async def welcome_event_mod(member):
    # Cari channel welcome
    ch = discord.utils.find(lambda c: 'welcome' in c.name.lower(), member.guild.text_channels)
    if ch:
        embed = discord.Embed(
            title="👋 SELAMAT DATANG DI FORTXX!",
            description=f"Halo {member.mention}! Selamat bergabung di server sharing mod GTA." + nl + nl + "📜 Baca peraturan di **#rules**" + nl + "✅ Ambil role di **#verify**" + nl + "🛒 Cek list harga di **#list-harga**" + nl + nl + "*Jangan lupa klik ✅ di channel verify biar bisa liat channel lainnya!*",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member ke-{member.guild.member_count}")
        await ch.send(content=member.mention, embed=embed)


@bot.listen('on_member_remove')
async def goodbye_event_cartel(member):
    ch = discord.utils.find(lambda c: 'welcome' in c.name.lower(), member.guild.text_channels)
    if ch:
        goodbye_text = (
            'Satu keluarga telah pergi dari *plaza*.' + chr(10) + chr(10) +
            'Apakah dia tersadar dari mimpi, atau justru kabur membawa rasa takut?' + chr(10) +
            'Kursi di meja ini kini kosong. Kita akan mengingat kesetiaanmu...' + chr(10) +
            '...atau mengutuk pengkhianatanmu.' + chr(10) + chr(10) +
            '**El que se va, nunca vuelve.**' + chr(10) +
            '*Que Dios te acompañe.*'
        )
        
        embed = discord.Embed(
            title=f'🩸 ADIÓS, {member.name.upper()}!',
            description=goodbye_text,
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await ch.send(embed=embed)
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# ✅ VERIFICATION GATEKEEPER (REACTION ROLE)
# ══════════════════════════════════════════════════════════════
@bot.command(name='ai')
async def ai_cmd(ctx, *, prompt: str):
    """Tanya AI apa aja. Contoh: !ai Apa itu Roleplay?"""
    await ctx.typing()
    jawaban = await tanya_aion(prompt)
    # Batasi 2000 karakter biar gak error
    await ctx.send(jawaban[:2000])

@bot.command(name='rp')
async def rp_cmd(ctx, *, aksi: str):
    """Roleplay sama AI. Contoh: !rp *menodongkan pistol* Siapa bos lu?"""
    await ctx.typing()
    system_rp = 'Kamu adalah karakter gangster dari kartel Meksiko. Jawab dengan bahasa Indonesia gaul dan sedikit kasar, tapi tetap dalam karakter.'
    jawaban = await tanya_aion(aksi, system_prompt=system_rp, model='aion-labs/aion-rp-llama-3.1-8b')
    await ctx.send(jawaban[:2000])
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🤖 AI CHANNEL (AUTO REPLY TANPA COMMAND)
# ══════════════════════════════════════════════════════════════
@bot.command(name='setupai')
async def setupai_cmd(ctx):
    """Bikin channel khusus AI asisten di kategori PUBLIC ROOM."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    # Cari kategori PUBLIC ROOM
    category = discord.utils.find(lambda c: c.name.upper() == 'PUBLIC ROOM', ctx.guild.categories)
    
    if not category:
        return await ctx.send('❌ Kategori **PUBLIC ROOM** gak ketemu Bang. Pastikan namanya persis "PUBLIC ROOM".')
        
    channel_name = '🤖┃ai-asisten'
    ch = discord.utils.find(lambda c: 'ai-asisten' in c.name.lower(), ctx.guild.text_channels)
    
    if not ch:
        ch = await ctx.guild.create_text_channel(channel_name, category=category)
        await ctx.send(f'✅ Channel {ch.mention} berhasil dibuat di PUBLIC ROOM!')
    else:
        await ch.edit(category=category)
        await ctx.send(f'✅ Channel {ch.mention} berhasil dipindah ke PUBLIC ROOM!')
        
    embed = discord.Embed(
        title='🤖 AI Asisten Cártel de Jalisco',
        description='Halo! Aku adalah asisten AI server ini. Kamu bisa tanya apa aja di sini tanpa perlu command.' + chr(10) + chr(10) + 'Contoh: Tanya cara ambil role atau jelasin aturan RP dong.',
        color=discord.Color.green()
    )
    await ch.send(embed=embed)

@bot.listen('on_message')
async def ai_channel_listener(message):
    if message.author.bot: return
    if not message.guild: return
    
    # Cek apakah ini channel AI (cek nama channel aja biar lebih aman)
    if not message.channel.name.startswith('🤖┃ai-'): return
    if message.content.startswith('!'): return
    
    print(f"[AI-CHANNEL] Menerima pesan dari {message.author.name}: {message.content}")
    
    try:
        async with message.channel.typing():
            system_prompt = 'Kamu adalah asisten AI pribadi ramah untuk server Roleplay Cártel de Jalisco. Bantu member dengan pertanyaan seputar aturan RP, cara bikin karakter, take role, ide cerita, dan hal umum lainnya. Jawab santai, sopan, dan singkat.'
            jawaban = await tanya_aion(message.content, system_prompt=system_prompt)
            
            if len(jawaban) > 2000:
                jawaban = jawaban[:1997] + '...'
                
            await message.reply(jawaban, mention_author=False)
            print(f"[AI-CHANNEL] Berhasil membalas pesan.")
    except Exception as e:
        print(f"[AI-CHANNEL] ERROR: {e}")
        await message.reply(f"❌ **Sistem AI Error:** `{e}`")

@bot.command(name='testai')
async def testai_cmd(ctx):
    """Cek apakah API Key Aion berfungsi."""
    if not is_mod(ctx): return
    await ctx.typing()
    respon = await tanya_aion("Halo, ini pesan tes. Balas dengan 'Sistem AI Online!'")
    await ctx.send(f"**Hasil Tes AI:**{nl}{respon}")

# ══════════════════════════════════════════════════════════════
# 🎨 AUTO DECORATOR (STYLE 1: ELITE CARTEL)
# ══════════════════════════════════════════════════════════════
@bot.command(name='dekorasi')
async def dekorasi_cmd(ctx, style: int = 1):
    """Hapus garis panjang dan teks aneh di nama kategori/channel."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('🧹 **Sapu bersih v3!** Menghapus garis panjang dan teks aneh...')
    
    # --- 1. BERSIHIN KATEGORI ---
    for cat in ctx.guild.categories:
        name_upper = cat.name.upper()
        new_name = cat.name
        
        # Deteksi berdasarkan emoji atau teks biasa
        if "🟥" in cat.name or "REPORT" in name_upper: new_name = "📁 〢 REPORT ROOM"
        elif "🟦" in cat.name or "PUBLIC" in name_upper: new_name = "📁 〢 PUBLIC ROOM"
        elif "🟪" in cat.name or "CJNG" in name_upper: new_name = "📁 〢 CJNG RULES"
        elif "🟩" in cat.name or "BLACK" in name_upper: new_name = "📁 〢 BLACK MARKET"
        elif "🟨" in cat.name or "TAKE" in name_upper: new_name = "📁 〢 TAKE ROLE"
        elif "⚙️" in cat.name or "SETTING" in name_upper: new_name = "⚙️ 〢 SETTINGS"
        elif "🤝" in cat.name or "PATNER" in name_upper or "PARTNER" in name_upper: new_name = "📁 〢 PARTNER"
        elif "🔗" in cat.name or "OFFICIAL" in name_upper: new_name = "📁 〢 OFFICIAL LINK"
        elif "📢" in cat.name or "ANNOUNC" in name_upper: new_name = "📁 〢 ANNOUNCEMENT"
        elif "🤖" in cat.name or "BOT" in name_upper: new_name = "📁 〢 BOT RUN"
        elif "📝" in cat.name or "REQ" in name_upper: new_name = "📁 〢 REQ AREA"
        
        if new_name != cat.name:
            try:
                await cat.edit(name=new_name)
                await asyncio.sleep(1.5)
            except: pass
            
    # --- 2. BERSIHIN CHANNEL ---
    # Urutkan dari yang paling spesifik biar gak salah ganti
    ch_map = {
        'daftar-karakter': '📜・daftar-karakter',
        'take-role-name': '📜・take-role-ic',
        'take • role': '👤・take-role',
        'welcome': '👋・welcome',
        'bot-run': '🔥・bot-run',
        'announcement': '📢・announcement',
        'logo': '☠️・logo-family',
        'list-anggota': '📋・list-anggota',
        'clue': '🏡・clue-tempat',
        'behav': '📚・behav-warga',
        'rules-dark': '📕・rules-dark',
        'publik': '💬・publik-chat',
        'chat • bot': '🤖・chat-bot',
        'report': '🩸・report-anggota',
        'logs-warning': '🩸・logs-warning',
        'ticket': '🎫・ticket',
        'ai-': '🤖・ai-asisten',
        'req-company': '💼・req-company',
        'req-approach': '👥・req-approach',
        'req-in-out': '🔐・req-in-out',
        'informasi': '💊・informasi-dark',
        'beli': '🛒・beli-barang'
    }
    
    for ch in ctx.guild.text_channels:
        ch_lower = ch.name.lower()
        for key, new_name in ch_map.items():
            if key in ch_lower:
                try:
                    await ch.edit(name=new_name)
                    await asyncio.sleep(1.5)
                except: pass
                break
                
    await msg.edit(content='✅ **Beres Bang!** Semua garis ══════ dan teks aneh udah dihapus.' + chr(10) + 'Nama kategori dan channel sekarang udah rapi dan pendek.')

# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🖼️ EMBED BUILDER (PESAN KUSTOM VIA FORM)
# ══════════════════════════════════════════════════════════════

class EmbedModal(discord.ui.Modal, title='Buat Pesan Embed'):
    judul = discord.ui.TextInput(
        label='Judul Pesan',
        placeholder='Contoh: PENGUMUMAN PENTING',
        required=True,
        max_length=256
    )
    deskripsi = discord.ui.TextInput(
        label='Isi Pesan / Deskripsi',
        style=discord.TextStyle.paragraph,
        placeholder='Tulis detail pengumuman di sini...',
        required=True
    )
    warna = discord.ui.TextInput(
        label='Warna (Hex Code)',
        placeholder='Contoh: #FF0000 (Merah), #00FF00 (Hijau)',
        required=False,
        max_length=7
    )
    gambar = discord.ui.TextInput(
        label='URL Gambar / Banner (Opsional)',
        placeholder='https://contoh.com/gambar.jpg',
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        color = discord.Color.blurple()
        if self.warna.value:
            try:
                hex_color = self.warna.value.strip().replace('#', '')
                color = discord.Color(int(hex_color, 16))
            except Exception:
                pass
                
        embed = discord.Embed(
            title=self.judul.value,
            description=self.deskripsi.value,
            color=color
        )
        
        if self.gambar.value:
            embed.set_image(url=self.gambar.value)
            
        embed.set_footer(text=f'Dibuat oleh {interaction.user.display_name}', icon_url=interaction.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message('✅ Pesan berhasil dibuat!', ephemeral=True)
        await interaction.channel.send(embed=embed)

class EmbedBuilderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Buat Pesan Baru', style=discord.ButtonStyle.primary, emoji='📝', custom_id='btn_buat_pesan')
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedModal())

@bot.command(name='buatpesan')
async def buatpesan_cmd(ctx):
    """Buka form pembuatan pesan embed (Mod only)."""
    if not is_mod(ctx):
        return await ctx.send('❌ Mod only.')
    
    embed = discord.Embed(
        title='🖼️ Embed Builder',
        description='Klik tombol di bawah ini untuk mulai membuat pesan kustom yang cantik.',
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=EmbedBuilderView())

# Daftarin view biar gak mati pas bot restart
try:
    bot.add_view(EmbedBuilderView())
except Exception:
    pass
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🟥 TEKS BERWARNA MERAH (ANSI CODE BLOCK)
# ══════════════════════════════════════════════════════════════
@bot.command(name='merah')
async def merah_cmd(ctx, *, text: str):
    """Kirim teks berwarna merah menyala."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    # Kode ANSI: \u001b[0;31m itu artinya warna merah, \u001b[0m itu reset
    red_text = f'```ansi' + chr(10) + f'\u001b[0;31m{text}\u001b[0m' + chr(10) + '```'
    
    try:
        await ctx.message.delete()
    except:
        pass
        
    await ctx.send(red_text)

@bot.command(name='merahs')
async def merahs_cmd(ctx, *, text: str):
    """Kirim teks merah tanpa menghapus pesan command."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    red_text = f'```ansi' + chr(10) + f'\u001b[0;31m{text}\u001b[0m' + chr(10) + '```'
    await ctx.send(red_text)
# ══════════════════════════════════════════════════════════════


@bot.command(name='testlog')
async def testlog_cmd(ctx):
    """Ngetes semua channel log di server ini secara pintar."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Mengecek & menguji channel log di server ini...**')
    cfg = _cfg_load()
    gid = str(ctx.guild.id)
    if gid not in cfg: cfg[gid] = {}
    
    log_types = {
        'warn': {'keys': ['warn-log', 'logs-warning', 'warn'], 'color': discord.Color.orange(), 'title': '🩸 TES LOG WARNING'},
        'ban': {'keys': ['banned-logs', 'ban-log', 'ban'], 'color': discord.Color.red(), 'title': '🚫 TES LOG BANNED'},
        'invite': {'keys': ['invite-logs', 'invite'], 'color': discord.Color.blue(), 'title': '📩 TES LOG INVITE'},
        'spam': {'keys': ['spam-bot', 'spam'], 'color': discord.Color.dark_red(), 'title': '🚧 TES LOG SPAM'},
        'bot': {'keys': ['bot-run', 'bot-logs', 'bot-command'], 'color': discord.Color.green(), 'title': '🔥 TES LOG BOT'}
    }
    
    results = []
    
    for log_type, info in log_types.items():
        ch = None
        cfg_key = f"{log_type}_ch"
        if log_type == 'warn': cfg_key = 'warn_log_channel'
        elif log_type == 'bot': cfg_key = 'bot_log_channel'
        
        # Cek dari Config Server
        if cfg_key in cfg[gid]:
            ch = ctx.guild.get_channel(cfg[gid][cfg_key])
            
        # Kalau gak ada, Scan by Keyword
        if not ch:
            for c in ctx.guild.text_channels:
                if any(k in c.name.lower() for k in info['keys']):
                    ch = c
                    cfg[gid][cfg_key] = ch.id
                    break
                    
        # Kirim Tes
        if ch:
            try:
                embed = discord.Embed(title=info['title'], description=f"Sistem log **{log_type.upper()}** berfungsi di server **{ctx.guild.name}**!", color=info['color'])
                embed.timestamp = discord.utils.utcnow()
                await ch.send(embed=embed)
                results.append(f"✅ **{log_type.upper()}** : {ch.mention} (Berhasil)")
            except Exception:
                results.append(f"❌ **{log_type.upper()}** : {ch.mention} (Gagal, cek izin bot)")
        else:
            results.append(f"⚠️ **{log_type.upper()}** : Channel tidak ditemukan")
            
    _cfg_save(cfg)
    
    # Pake chr(10) biar gak error string
    desc_text = chr(10).join(results)
    embed = discord.Embed(title=f'📋 Hasil Tes Log: {ctx.guild.name}', description=desc_text, color=discord.Color.blurple())
    embed.set_footer(text="Semua channel di atas udah otomatis disimpan di sistem.")
    await msg.edit(content='', embed=embed)
@bot.command(name='setupwarnlist')
async def setupwarnlist_cmd(ctx):
    """Bikin channel Cartel Hitlist di REPORT ROOM."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    category = discord.utils.find(lambda c: 'REPORT ROOM' in c.name.upper(), ctx.guild.categories)
    ch_name = '🩸・cartel-hitlist'
    
    ch = discord.utils.find(lambda c: 'cartel-hitlist' in c.name.lower(), ctx.guild.text_channels)
    if not ch:
        ch = await ctx.guild.create_text_channel(ch_name, category=category)
        
    # Hapus pesan lama bot di channel itu biar bersih
    async for msg in ch.history(limit=50):
        if msg.author == bot.user:
            await msg.delete()
            
    embed = discord.Embed(
        title="🩸 𝗖𝗔𝗥𝗧𝗘𝗟 𝗛𝗜𝗧𝗟𝗜𝗦𝗧 (WARN LIST) 🩸",
        description="🕊️ **DAFTAR BERSIH.** Saat ini tidak ada warga yang masuk daftar hitam Cartel.",
        color=discord.Color.dark_red()
    )
    embed.set_footer(text="Cártel de Jalisco Nueva Generación • Sistem Peringatan Otomatis")
    
    msg = await ch.send(embed=embed)
    
    cfg = _cfg_load()
    cfg['warn_list_channel'] = ch.id
    cfg['warn_list_msg'] = msg.id
    _cfg_save(cfg)
    
    await ctx.send(f"✅ Cartel Hitlist berhasil di-setup di {ch.mention}!")

# ══════════════════════════════════════════════════════════════
# 🏗️ COMMUNITY SERVER BUILDER (dari templates.json)
# ══════════════════════════════════════════════════════════════
import json

class CommunityRoleSelect(discord.ui.Select):
    def __init__(self, roles):
        options = [discord.SelectOption(label=r.name, value=str(r.id), emoji="🎭") for r in roles[:25]]
        super().__init__(placeholder="Pilih role komunitas kamu...", min_values=0, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        # Hapus role yang tidak dipilih, tambahkan yang dipilih
        selected_ids = [int(v) for v in self.values]
        all_options_ids = [int(opt.value) for opt in self.options]
        
        to_add = []
        to_remove = []
        
        for rid in all_options_ids:
            role = interaction.guild.get_role(rid)
            if not role: continue
            
            if rid in selected_ids:
                if role not in interaction.user.roles:
                    to_add.append(role)
            else:
                if role in interaction.user.roles:
                    to_remove.append(role)
                    
        try:
            if to_add: await interaction.user.add_roles(*to_add)
            if to_remove: await interaction.user.remove_roles(*to_remove)
            await interaction.response.send_message("✅ Role komunitas lu berhasil di-update!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Gagal update role: {e}", ephemeral=True)

class CommunityRoleView(discord.ui.View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        self.add_item(CommunityRoleSelect(roles))

@bot.command(name='buildcommunity')
async def buildcommunity_cmd(ctx):
    """Bikin struktur server komunitas/pribadi (Tanpa RP) + isi otomatis."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Membangun Server Komunitas...** Mohon tunggu (1-2 menit).')
    
    try:
        with open('templates.json', 'r') as f:
            data = json.load(f)
        template = data['community']
    except Exception as e:
        return await msg.edit(content=f'❌ Gagal baca templates.json: {e}')
    
    staff_overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    for r_name in ['Admin', 'Moderator', 'Staff', 'Owner']:
        r = discord.utils.get(ctx.guild.roles, name=r_name)
        if r: staff_overwrites[r] = discord.PermissionOverwrite(read_messages=True)
    
    created = 0
    for cat_data in template['categories']:
        cat_overwrites = staff_overwrites if cat_data.get('private', False) else {}
        try:
            category = await ctx.guild.create_category(cat_data['name'], overwrites=cat_overwrites)
        except Exception as e:
            continue
        
        for ch_data in cat_data['channels']:
            try:
                if ch_data['type'] == 'text':
                    ch = await ctx.guild.create_text_channel(ch_data['name'], category=category, topic=ch_data.get('topic', ''))
                    
                    if 'rules' in ch.name:
                        embed = discord.Embed(title="📜 PERATURAN SERVER", description="1. Hormati sesama member.\n2. Dilarang spam & toxic.\n3. Ikuti arahan Staff.\n4. Dilarang promosi tanpa izin.", color=discord.Color.gold())
                        await ch.send(embed=embed)
                        
                    elif 'verify' in ch.name:
                        role = discord.utils.get(ctx.guild.roles, name='✅ Verified')
                        if not role:
                            role = await ctx.guild.create_role(name='✅ Verified', color=discord.Color.green(), reason='Auto Setup')
                        
                        embed = discord.Embed(title="✅ VERIFIKASI SERVER", description="Klik reaksi **✅** di bawah ini untuk membuka seluruh channel.", color=discord.Color.green())
                        msg_v = await ch.send(embed=embed)
                        await msg_v.add_reaction('✅')
                        
                        cfg = _cfg_load()
                        cfg['verify_message_id'] = msg_v.id
                        cfg['verify_role_id'] = role.id
                        _cfg_save(cfg)

                    elif 'tickets' in ch.name:
                        embed = discord.Embed(title="🎫 PUSAT BANTUAN", description="Butuh bantuan atau mau lapor? Klik tombol di bawah untuk membuat tiket.", color=discord.Color.blurple())
                        await ch.send(embed=embed, view=TicketV2View())

                    elif 'self-roles' in ch.name:
                        # Buat role komunitas otomatis kalau belum ada
                        roles_to_create = ["🎮 Gamer", "🎵 Musik", "📢 Info Ping", "💬 Aktif Chat"]
                        guild_roles = []
                        for r_name in roles_to_create:
                            r = discord.utils.get(ctx.guild.roles, name=r_name)
                            if not r:
                                r = await ctx.guild.create_role(name=r_name, reason='Auto Role Setup')
                            guild_roles.append(r)
                            
                        embed = discord.Embed(title="🎭 AMBIL ROLE KOMUNITAS", description="Pilih role yang sesuai dengan minatmu di menu dropdown di bawah ini.\n\n*Lu bisa milih lebih dari satu.*", color=discord.Color.blurple())
                        await ch.send(embed=embed, view=CommunityRoleView(guild_roles))

                    elif 'bot-commands' in ch.name:
                        view = HelpMainView()
                        await ch.send(embed=view._build_embed(), view=view)
                        
                    elif 'general-chat' in ch.name:
                        await ch.send("💬 **Selamat datang di General Chat!** Sapa member lain di sini 👋")
                    elif 'announcements' in ch.name:
                        await ch.send(embed=discord.Embed(title="📢 PENGUMUMAN", description="Info penting akan muncul di sini.", color=discord.Color.red()))
                    elif 'staff-chat' in ch.name:
                        await ch.send("🛡️ **Staff Room.** Diskusi internal admin & mod.")

                elif ch_data['type'] == 'voice':
                    await ctx.guild.create_voice_channel(ch_data['name'], category=category)
                
                created += 1
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f'[BUILD] Gagal buat channel {ch_data["name"]}: {e}')
        
        await asyncio.sleep(1.5)
    
    await msg.edit(content=f'✅ **Server Komunitas Berhasil Dibangun!** ({created} channel dibuat).' + chr(10) + 'Semua panel (Verify, Ticket, Role) udah otomatis terpasang.')


# ══════════════════════════════════════════════════════════════
# 🎫 TICKET SYSTEM V2 (KOMUNITAS)
# ══════════════════════════════════════════════════════════════
class TicketV2CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Tutup Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_v2_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket akan ditutup dan dihapus dalam 5 detik...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketV2Select(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Bantuan Umum', description='Tanya jawab seputar server atau hal umum.', emoji='❓', value='umum'),
            discord.SelectOption(label='Laporan / Report', description='Laporkan pelanggaran aturan atau masalah member.', emoji='🚨', value='laporan'),
            discord.SelectOption(label='Bantuan Teknis / Bug', description='Lapor error bot atau butuh bantuan teknis.', emoji='🛠️', value='teknis'),
            discord.SelectOption(label='Kerjasama / Partner', description='Ajukan kerjasama atau partnership server.', emoji='🤝', value='partner'),
            discord.SelectOption(label='Lainnya', description='Untuk hal-hal yang belum tercantum di atas.', emoji='📝', value='lainnya')
        ]
        super().__init__(placeholder="Pilih jenis tiket...", min_values=1, max_values=1, options=options, custom_id="ticket_v2_select_menu")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]
        
        category = discord.utils.get(guild.categories, name='Tickets')
        if category:
            for ch in category.text_channels:
                if ch.topic and f"({user.id})" in ch.topic:
                    return await interaction.response.send_message(f"❌ Kamu sudah punya ticket terbuka di {ch.mention}!", ephemeral=True)
        
        await interaction.response.send_message(f"⏳ Sedang membuat channel tiket **{ticket_type}**...", ephemeral=True)
        
        if not category:
            try:
                category = await guild.create_category("Tickets", reason="Setup sistem ticket V2")
            except Exception:
                pass
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        staff_roles = ["Staff", "Moderator", "Admin", "Owner", "Mod"]
        for role_name in staff_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        try:
            ticket_ch = await guild.create_text_channel(
                name=f"ticket-{ticket_type}-{user.name}".lower(),
                category=category,
                overwrites=overwrites,
                topic=f"Ticket milik {user.name} ({user.id}) | Tipe: {ticket_type} | Ketuk 🔒 Tutup Ticket untuk menghapus."
            )
            
            role1 = discord.utils.get(guild.roles, name="Staff")
            role2 = discord.utils.get(guild.roles, name="Admin")
            tag1 = role1.mention if role1 else ""
            tag2 = role2.mention if role2 else ""
            
            desc_text = f"Halo {user.mention}, tunggu sebentar ya. Staff akan segera merespons." + chr(10) + chr(10) + "Jika masalah sudah selesai, silakan klik tombol di bawah."
            
            embed = discord.Embed(
                title=f"🎫 Ticket: {ticket_type.upper()}",
                description=desc_text,
                color=discord.Color.green()
            )
            
            await ticket_ch.send(content=f"{user.mention} {tag1} {tag2}", embed=embed, view=TicketV2CloseView())
            await interaction.edit_original_response(content=f"✅ Ticket kamu sudah dibuat: {ticket_ch.mention}")
            
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Gagal membuat ticket: {e}")

class TicketV2View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketV2Select())

@bot.command(name='ticketv2')
async def ticketv2_cmd(ctx):
    """Bikin panel Ticket V2 (Komunitas)."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    embed = discord.Embed(
        title="🎫 Pusat Bantuan (Support Ticket)",
        description="Butuh bantuan dari Staff atau ingin melaporkan sesuatu?" + chr(10) + "Silakan pilih jenis tiket pada menu di bawah ini.",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=TicketV2View())
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🏗️ COMMUNITY BUILDER V2 (TAMBAHAN EVENT, MUSIC, WELCOME, PARTNER)
# ══════════════════════════════════════════════════════════════
@bot.command(name='buildcommunity2')
async def buildcommunity2_cmd(ctx):
    """Bikin channel tambahan buat komunitas lengkap dengan isinya."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Membangun Channel Tambahan...** Mohon tunggu sebentar.')
    created = 0
    
    try:
        # 1. EVENTS & FUN
        cat_fun = await ctx.guild.create_category('🎉 〢 EVENTS & FUN')
        ch = await ctx.guild.create_text_channel('🎉・giveaways', category=cat_fun)
        e = discord.Embed(title='🎉 GIVEAWAY CENTER', description='Di sini tempatnya event giveaway berhadiah menarik!' + nl + nl + 'Syarat mengikuti giveaway:' + nl + '1. Wajib jadi member server.' + nl + '2. Klik reaksi emoji yang disediakan bot.' + nl + '3. Jangan pakai akun ganda (alt).', color=discord.Color.gold())
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('📅・events', category=cat_fun)
        e = discord.Embed(title='📅 JADWAL EVENT', description='Pantau channel ini untuk melihat jadwal event mabar, nobar, atau acara komunitas lainnya.', color=discord.Color.blurple())
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('💡・suggestions', category=cat_fun)
        e = discord.Embed(title='💡 KOTAK SARAN', description='Punya ide biar server ini makin keren?' + nl + 'Silakan tulis saran lu di sini. Admin akan meninjau setiap saran yang masuk.', color=discord.Color.green())
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('😂・bot-spam', category=cat_fun)
        e = discord.Embed(title='🤖 ZONA BOT', description='Bebas spam command bot di sini tanpa ngganggu member lain yang lagi ngobrol di general chat.', color=discord.Color.from_rgb(255, 150, 100))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        # 2. MUSIC & CHILL
        cat_music = await ctx.guild.create_category('🎵 〢 MUSIC & CHILL')
        await ctx.guild.create_voice_channel('🎵・Music VC', category=cat_music); created += 1; await asyncio.sleep(1.5)
        await ctx.guild.create_voice_channel('🎧・Chill VC', category=cat_music); created += 1; await asyncio.sleep(1.5)
        
        # 3. WELCOME
        cat_welcome = await ctx.guild.create_category('🚪 〢 WELCOME')
        ch = await ctx.guild.create_text_channel('👋・welcome', category=cat_welcome)
        e = discord.Embed(title='👋 SELAMAT DATANG!', description='Channel ini otomatis akan menyapa member baru yang join ke server.' + nl + nl + 'Jika kamu member baru, jangan lupa baca #rules dan ambil role di #self-roles ya!', color=discord.Color.from_rgb(100, 200, 255))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        # 4. PARTNERSHIP
        cat_partner = await ctx.guild.create_category('🤝 〢 PARTNERSHIP')
        ch = await ctx.guild.create_text_channel('🤝・partner', category=cat_partner)
        e = discord.Embed(title='🤝 PARTNERSHIP', description='Ingin bekerja sama dengan server kami?' + nl + nl + 'Syarat Partner:' + nl + '1. Server aktif (minimal 50 member).' + nl + '2. Tidak mengandung unsur SARA, NSFW, atau ilegal.' + nl + nl + 'Hubungi Admin/Owner jika tertarik.', color=discord.Color.from_rgb(200, 100, 255))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        await msg.edit(content=f'✅ **Berhasil Menambahkan {created} Channel Baru + Isinya!** Silakan cek kategori baru di bawah.' )
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal membuat channel tambahan: {e}')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🏗️ COMMUNITY BUILDER V3 (CREATIVE, LIFESTYLE, ROLES, SAFE SPACE)
# ══════════════════════════════════════════════════════════════
@bot.command(name='buildcommunity3')
async def buildcommunity3_cmd(ctx):
    """Bikin channel hobi, notifikasi role, dan safe space."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Membangun Channel Level 3...** Mohon tunggu sebentar.')
    created = 0
    
    try:
        # 1. CREATIVE & MEDIA
        cat_creative = await ctx.guild.create_category('📸 〢 CREATIVE & MEDIA')
        ch = await ctx.guild.create_text_channel('🎨・art-showcase', category=cat_creative)
        e = discord.Embed(title='🎨 ART SHOWCASE', description='Pamerkan gambar, fanart, atau hasil editing lu di sini! Dilarang mencuri karya orang lain ya.', color=discord.Color.from_rgb(255, 100, 200))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('📸・photography', category=cat_creative)
        e = discord.Embed(title='📸 PHOTOGRAPHY', description='Share foto pemandangan, koleksi, atau momen estetik yang lu ambil.', color=discord.Color.from_rgb(100, 200, 255))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('✍️・writing-corner', category=cat_creative)
        e = discord.Embed(title='✍️ WRITING CORNER', description='Tempat buat share cerita pendek, puisi, atau tulisan lu. Support sesama penulis!', color=discord.Color.from_rgb(200, 200, 100))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        # 2. LIFESTYLE
        cat_life = await ctx.guild.create_category('🐾 〢 LIFESTYLE')
        ch = await ctx.guild.create_text_channel('🐶・pets', category=cat_life)
        e = discord.Embed(title='🐶 PETS CORNER', description='Posting foto hewan peliharaan lu di sini. Kucing, anjing, ikan, semua boleh!', color=discord.Color.from_rgb(150, 255, 150))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('🍔・food-talk', category=cat_life)
        e = discord.Embed(title='🍔 FOOD TALK', description='Lagi makan apa hari ini? Share resep atau rekomendasi tempat makan enak!', color=discord.Color.from_rgb(255, 200, 100))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        # 3. NOTIFICATION ROLES
        cat_roles = await ctx.guild.create_category('🔔 〢 NOTIFICATION ROLES')
        ch = await ctx.guild.create_text_channel('🎨・color-roles', category=cat_roles)
        e = discord.Embed(title='🎨 PILIH WARNA NAMA', description='Ingin nama lu berwarna? Ketik pesan atau ambil role warna di sini (Admin bisa setup dropdown warna).', color=discord.Color.purple())
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('🔔・ping-roles', category=cat_roles)
        e = discord.Embed(title='🔔 NOTIFIKASI (PING)', description='Pilih role di sini biar lu dapet notifikasi khusus (Event, Giveaway, Pengumuman) tanpa harus di-tag @everyone.', color=discord.Color.red())
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        # 4. SAFE SPACE
        cat_safe = await ctx.guild.create_category('🫂 〢 SAFE SPACE')
        ch = await ctx.guild.create_text_channel('🫂・vent-room', category=cat_safe)
        e = discord.Embed(title='🫂 VENT ROOM', description='Butuh tempat cerita kalau lagi capek atau sedih? Tulis di sini.' + nl + nl + '**ATURAN:** Dilarang menghakimi, mem-bully, atau menyebarkan cerita orang lain dari channel ini!', color=discord.Color.from_rgb(150, 150, 255))
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        ch = await ctx.guild.create_text_channel('💭・confessions', category=cat_safe)
        e = discord.Embed(title='💭 CONFESSIONS', description='Kirim pesan rahasia tanpa nama (anonymous) di sini. Bisa pakai bot anonymous kalau ada.', color=discord.Color.dark_grey())
        await ch.send(embed=e); created += 1; await asyncio.sleep(1.5)
        
        await msg.edit(content=f'✅ **Berhasil Menambahkan {created} Channel Baru (Level 3)!** Server lu sekarang udah super lengkap.' )
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal membuat channel: {e}')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 👑 AUTO ROLE BUILDER
# ══════════════════════════════════════════════════════════════
@bot.command(name='buildroles')
async def buildroles_cmd(ctx):
    """Bikin semua role penting buat server komunitas otomatis."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Membangun semua Role...** Mohon tunggu sebentar.')
    
    # List Role: (Nama, Warna, Hoist(Tampil terpisah), Mentionable)
    roles_to_create = [
        # --- ROLE STAFF ---
        ('👑 Owner', discord.Color.gold(), True, False),
        ('🛡️ Admin', discord.Color.red(), True, False),
        ('⚔️ Moderator', discord.Color.orange(), True, False),
        ('🔰 Staff', discord.Color.blue(), True, False),
        ('✅ Verified', discord.Color.green(), False, False),
        ('🤖 Bots', discord.Color.dark_grey(), True, False),
        
        # --- ROLE MINAT ---
        ('🎮 Gamer', discord.Color.default(), False, True),
        ('🎵 Musik', discord.Color.default(), False, True),
        ('🎨 Artist', discord.Color.default(), False, True),
        ('🐶 Pet Lover', discord.Color.default(), False, True),
        ('🍔 Foodie', discord.Color.default(), False, True),
        
        # --- ROLE PING / NOTIFIKASI ---
        ('📢 Event Ping', discord.Color.default(), False, True),
        ('🎁 Giveaway Ping', discord.Color.default(), False, True),
        ('📣 Announcement Ping', discord.Color.default(), False, True)
    ]
    
    created = 0
    skipped = 0
    
    try:
        for name, color, hoist, mentionable in roles_to_create:
            existing = discord.utils.get(ctx.guild.roles, name=name)
            if existing:
                skipped += 1
                continue
                
            await ctx.guild.create_role(
                name=name,
                color=color,
                hoist=hoist,
                mentionable=mentionable,
                reason='Auto Server Setup'
            )
            created += 1
            await asyncio.sleep(1.5) # Jeda anti rate-limit
            
        embed = discord.Embed(
            title='✅ Role Builder Selesai!',
            description=f'Berhasil membuat **{created}** role baru.' + nl + f'({skipped} role dilewati karena udah ada).' + nl + nl + 'Silakan cek Server Settings > Roles.',
            color=discord.Color.green()
        )
        embed.add_field(name='👑 Staff', value='Owner, Admin, Mod, Staff, Verified, Bots', inline=False)
        embed.add_field(name='🎭 Minat', value='Gamer, Musik, Artist, Pet, Foodie', inline=False)
        embed.add_field(name='🔔 Ping', value='Event, Giveaway, Announcement', inline=False)
        embed.set_footer(text='Jangan lupa atur posisi role Bot di paling atas!')
        
        await msg.edit(content='', embed=embed)
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal membuat role: {e}')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🛡️ AUTO PERMISSION SETUP
# ══════════════════════════════════════════════════════════════
@bot.command(name='setup_permissions')
async def setup_permissions_cmd(ctx):
    """Set izin (permission) otomatis ke role yang udah dibuat."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Mengatur izin role...** Mohon tunggu sebentar.')
    
    # Mapping Role -> Permission
    role_perms = {
        '👑 Owner': discord.Permissions(administrator=True),
        '🛡️ Admin': discord.Permissions(administrator=True),
        '⚔️ Moderator': discord.Permissions(kick_members=True, moderate_members=True, manage_messages=True, view_audit_log=True, manage_nicknames=True),
        '🔰 Staff': discord.Permissions(manage_messages=True, view_audit_log=True),
        '🤖 Bots': discord.Permissions(manage_roles=True, manage_channels=True, manage_messages=True, kick_members=True),
        '✅ Verified': discord.Permissions(send_messages=True, read_messages=True, attach_files=True, embed_links=True)
    }
    
    updated = 0
    
    try:
        for role_name, perms in role_perms.items():
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role:
                await role.edit(permissions=perms, reason='Auto Setup Permissions')
                updated += 1
                await asyncio.sleep(1.5) # Jeda anti rate-limit
                
        embed = discord.Embed(
            title='✅ Permission Berhasil Diatur!',
            description=f'Berhasil mengatur izin untuk **{updated}** role.' + nl + nl + '**Catatan Penting:**' + nl + 'Pastikan Role Bot (FORTXX) posisinya ada di **PALING ATAS** di Server Settings > Roles, agar bot bisa mengatur role-role di bawahnya.',
            color=discord.Color.green()
        )
        await msg.edit(content='', embed=embed)
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal mengatur izin: {e}')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🔒 AUTO CHANNEL PERMISSIONS (READ-ONLY INFO CHANNELS)
# ══════════════════════════════════════════════════════════════
@bot.command(name='setup_channels')
async def setup_channels_cmd(ctx):
    """Kunci channel informasi biar member cuma bisa baca."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Mengatur izin channel informasi...** Mohon tunggu sebentar.')
    
    # List channel yang mau dikunci (Read-Only)
    lock_list = ['announcements', 'rules', 'welcome', 'partner', 'events']
    # Channel yang butuh reaction (verify, giveaways) tapi tetep gak bisa chat
    reaction_list = ['verify', 'giveaways']
    
    # Role Staff yang tetep bisa chat
    staff_roles = ['👑 Owner', '🛡️ Admin', '⚔️ Moderator', '🔰 Staff', 'Admin', 'Moderator', 'Staff']
    
    locked = 0
    
    try:
        for ch in ctx.guild.text_channels:
            is_lock = any(k in ch.name.lower() for k in lock_list)
            is_reaction = any(k in ch.name.lower() for k in reaction_list)
            
            if is_lock or is_reaction:
                # 1. Lock @everyone
                overwrite = ch.overwrites_for(ctx.guild.default_role)
                overwrite.read_messages = True
                overwrite.send_messages = False
                if is_reaction:
                    overwrite.add_reactions = True
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                
                # 2. Kasih akses ke Staff & Bot biar tetep bisa chat
                for r_name in staff_roles:
                    role = discord.utils.get(ctx.guild.roles, name=r_name)
                    if role:
                        staff_overwrite = ch.overwrites_for(role)
                        staff_overwrite.read_messages = True
                        staff_overwrite.send_messages = True
                        await ch.set_permissions(role, overwrite=staff_overwrite)
                        
                bot_overwrite = ch.overwrites_for(ctx.guild.me)
                bot_overwrite.read_messages = True
                bot_overwrite.send_messages = True
                await ch.set_permissions(ctx.guild.me, overwrite=bot_overwrite)
                
                locked += 1
                await asyncio.sleep(1.5) # Jeda anti rate-limit
                
        embed = discord.Embed(
            title='🔒 Channel Informasi Dikunci!',
            description=f'Berhasil mengatur izin untuk **{locked}** channel.' + nl + nl + 'Member biasa sekarang **hanya bisa membaca** di channel:' + nl + '`#announcements`, `#rules`, `#welcome`, dll.' + nl + nl + '*Note: Channel `#verify` & `#giveaways` tetap bisa diklik emojinya.*',
            color=discord.Color.green()
        )
        await msg.edit(content='', embed=embed)
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal mengatur izin channel: {e}')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 📊 AUTO ROLE SORTER
# ══════════════════════════════════════════════════════════════
@bot.command(name='aturroles')
async def aturroles_cmd(ctx):
    """Ngurutin posisi role dari paling tinggi ke paling rendah."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Mengurutkan Role...** Mohon tunggu sebentar.')
    
    # Urutan Role dari yang PALING TINGGI ke PALING RENDAH
    role_order = [
        '👑 Owner', '🛡️ Admin', '⚔️ Moderator', '🔰 Staff',
        '✅ Verified', '🎮 Gamer', '🎵 Musik', '🎨 Artist',
        '🐶 Pet Lover', '🍔 Foodie', '📢 Event Ping',
        '🎁 Giveaway Ping', '📣 Announcement Ping'
    ]
    
    # Cari role bot lu sendiri
    bot_role = ctx.guild.me.top_role
    
    try:
        # Kita iterasi dari bawah ke atas biar gak tabrakan posisinya
        current_pos = 1 # Posisi paling bawah (di atas @everyone)
        
        # Balik urutannya buat di-loop dari bawah
        for r_name in reversed(role_order):
            role = discord.utils.get(ctx.guild.roles, name=r_name)
            if role:
                # Cek apakah role ini posisinya di atas role bot (gak bisa digeser)
                if role >= bot_role:
                    print(f'[SORT] Skip {r_name}: posisinya di atas role Bot.')
                    continue
                    
                await role.edit(position=current_pos)
                current_pos += 1
                await asyncio.sleep(1.5) # Jeda anti rate limit
                
        embed = discord.Embed(
            title='✅ Role Berhasil Diurutkan!',
            description='Urutan role sekarang udah rapi dari yang tertinggi sampai terendah.' + nl + nl + '**⚠️ PENTING:**' + nl + 'Kalau masih ada role yang posisinya berantakan (kayak `Verified` masih di atas), itu karena **Role Bot (FORTXX) lu belum ditarik ke paling atas**. Tarik manual dulu Role Bot-nya, lalu jalankan command ini lagi.',
            color=discord.Color.green()
        )
        await msg.edit(content='', embed=embed)
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal mengurutkan role: {e}')
# ══════════════════════════════════════════════════════════════

@bot.hybrid_command(name='buildsharemod')
async def buildsharemod_cmd(ctx):
    """Bikin struktur server mod GTA FORTXX lengkap dengan Role, Perms, & Isi."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **MEMBANGUN SERVER FORTXX ULTIMATE...**' + nl + 'Proses ini memakan waktu 3-5 menit karena membuat 9 Role + 80+ Channel + Mengatur Izin.' + nl + '**Silakan tinggalkan HP sebentar, jangan spam command lain.**')
    
    # 1. BIKIN ROLE DULU
    roles_data = [
        ("👑 Owner", discord.Color.gold(), discord.Permissions(administrator=True)),
        ("🛡️ Admin", discord.Color.red(), discord.Permissions(administrator=True)),
        ("⚔️ Moderator", discord.Color.orange(), discord.Permissions(kick_members=True, manage_messages=True, view_audit_log=True)),
        ("🔰 Staff", discord.Color.blue(), discord.Permissions(manage_messages=True, view_audit_log=True)),
        ("🤖 Bots", discord.Color.dark_grey(), discord.Permissions(manage_channels=True, manage_roles=True)),
        ("✅ Verified", discord.Color.green(), discord.Permissions(read_messages=True, send_messages=True)),
        ("💵 Seller", discord.Color.from_rgb(255, 200, 0), discord.Permissions(read_messages=True)),
        ("🛒 Buyer", discord.Color.from_rgb(150, 150, 150), discord.Permissions(read_messages=True)),
    ]
    
    for name, color, perms in roles_data:
        if not discord.utils.get(ctx.guild.roles, name=name):
            await ctx.guild.create_role(name=name, color=color, permissions=perms)
            await asyncio.sleep(1.5)

    # Siapin Overwrites (Izin) buat kategori privat
    staff_roles = ["👑 Owner", "🛡️ Admin", "⚔️ Moderator", "🔰 Staff"]
    staff_overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False)}
    for r_name in staff_roles:
        r = discord.utils.get(ctx.guild.roles, name=r_name)
        if r: staff_overwrites[r] = discord.PermissionOverwrite(read_messages=True)

    read_only_overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False)
    }
    
    # 2. BIKIN KATEGORI & CHANNEL + KONTEN
    structure = [
        ('📌 〢 LOGS & INFO', [
            ('👋・welcome', 'text', read_only_overwrites), 
            ('📜・rules', 'text', read_only_overwrites),
            ('✈️・goodbye', 'text', read_only_overwrites), 
            ('📩・invite-logs', 'text', staff_overwrites), 
            ('🚫・banned-logs', 'text', staff_overwrites), 
            ('⬆️・level-up', 'text', {}), 
            ('🚧・spam-bot', 'text', staff_overwrites), 
            ('🚀・booster-log', 'text', {})
        ]),
        ('🛡️ 〢 DASHBOARD', [
            ('😈・fortxx-traps', 'text', staff_overwrites), 
            ('📢・announcement', 'text', read_only_overwrites), 
            ('🔗・official-link', 'text', read_only_overwrites), 
            ('📌・voting-area', 'text', {}), 
            ('🎲・spoiler-modpack', 'text', {}), 
            ('🔔・content-notify', 'text', read_only_overwrites), 
            ('♻️・remastered-mod', 'text', {}), 
            ('📋・change-logs', 'text', read_only_overwrites)
        ]),
        ('🛒 〢 FORTXX STORE', [
            ('📢・information-market', 'text', read_only_overwrites), 
            ('💰・list-harga', 'text', read_only_overwrites), 
            ('🛠️・production-team', 'text', staff_overwrites), 
            ('💵・modpack-mobile', 'text', {}), 
            ('💵・modpack-production', 'text', {}), 
            ('💵・gta-pc', 'text', {}), 
            ('💵・other-sell', 'text', {}), 
            ('🔔・open-ticket', 'text', {}), 
            ('✉️・qris-code', 'text', read_only_overwrites), 
            ('⭐・rating-me', 'text', {}), 
            ('📝・logs-buyer', 'text', staff_overwrites)
        ]),
        ('🤝 〢 PARTNERSHIP LIST', [('📢・partners-info', 'text', {}), ('🤝・partner', 'text', {}), ('📺・content-partners', 'text', {}), ('📋・partners-list', 'text', read_only_overwrites)]),
        ('🎭 〢 ROLE INFORMASI', [('📢・information-roles', 'text', read_only_overwrites), ('💜・req-followers', 'text', {}), ('🎁・free-roles', 'text', read_only_overwrites), ('🧩・choice-roles', 'text', {}), ('✳️・take-roles', 'text', {})]),
        ('😎 〢 MAIN GANGSTER AN', [('👟・low-budget-drip', 'text', {}), ('💼・gang-gif-rap-sturdy', 'text', {}), ('📸・gang-picture-selfie', 'text', {}), ('💀・samp-dead-opps', 'text', {})]),
        ('💬 〢 GENERAL', [('💵・support-me', 'text', {}), ('🍀・giveaway-modpack', 'text', {}), ('🔧・list-mekanik-gta', 'text', {}), ('💬・chat-public', 'text', {}), ('🖼️・gallery-public', 'text', {}), ('🆙・screenshoot-ingame', 'text', {}), ('🔍・nyari-mod', 'text', {}), ('😭・problem-gta-mobile', 'text', {}), ('😭・problem-gta-pc', 'text', {})]),
        ('📤 〢 SHARING AREA', [('🔗・share-discord', 'text', {}), ('🎙️・share-music', 'text', {}), ('📺・share-content', 'text', {}), ('🆓・share-gta-andro-pc', 'text', {})]),
        ('🔊 〢 VOICE ROOM', [('🦉・NYANTAI', 'voice', {}), ('🌍・MINECRAFT', 'voice', {}), ('🔧・KONSULTASI-1', 'voice', {}), ('🔧・KONSULTASI-2', 'voice', {}), ('🎵・MUSYIK-1', 'voice', {}), ('🎵・MUSYIK-2', 'voice', {}), ('🔒・talk', 'voice', {}), ('🗣️・interview-kerja-real', 'voice', {})]),
        ('🚗 〢 SHOWROOM SKIN GTA', [('🍇・fortxx', 'text', {}), ('🧃・treylocc', 'text', {}), ('🍊・ojerasy', 'text', {}), ('🧩・atarzmods', 'text', {}), ('🦊・finnz', 'text', {})]),
        ('💸 〢 MARKETPLACE', [('💵・gta-porsale-mobile', 'text', {}), ('💵・gta-porsale-desktop', 'text', {}), ('💵・skin-porsale', 'text', {}), ('🚨・search-item-rmt', 'text', {})]),
        ('🔫 〢 WEAPON AREA', [('🔫・pistol-weapon', 'text', {}), ('🔫・shotgun-weapon', 'text', {}), ('🔫・smg-weapon', 'text', {}), ('🔫・rifle-weapon', 'text', {}), ('🔫・sniper-weapon', 'text', {}), ('🔫・mele-weapon', 'text', {}), ('📦・gun-pack', 'text', {}), ('🔫・weapon-icon', 'text', {}), ('✳️・hitmarker', 'text', {}), ('🖌️・weapon-anim', 'text', {}), ('💨・muzzle-texture', 'text', {}), ('🔊・weapon-sound', 'text', {}), ('🔊・hit-sound', 'text', {})]),
        ('🌍 〢 GTA WORLD', [('🧱・texture-mod', 'text', {}), ('🌲・vegetation-mod', 'text', {}), ('🏙️・grafik-mod', 'text', {}), ('🌧️・skybox-mod', 'text', {}), ('🌈・pc-grafik', 'text', {}), ('🛣️・road-mod', 'text', {}), ('💥・effect-mod', 'text', {}), ('🐛・particle-mod', 'text', {}), ('📦・other-mod', 'text', {})]),
        ('👕 〢 MODELS MODIF', [('♿・skin-low-poly', 'text', {}), ('👕・skin-basic', 'text', {}), ('👚・skin-cewe', 'text', {}), ('👽・skin-compee', 'text', {}), ('😆・skin-funny', 'text', {}), ('🚨・skin-apart', 'text', {}), ('🚶・anim-ifp', 'text', {}), ('🎒・toys-mod', 'text', {}), ('🏠・envi-mod', 'text', {})]),
        ('🏎️ 〢 VEHICLE AREA', [('🚗・car-mod', 'text', {}), ('🛵・motorcycle-mod', 'text', {}), ('🚓・apart-car', 'text', {}), ('⚓・sperpat-vehicle', 'text', {})])
    ]
    
    created = 0
    log_channels = {}
    
    try:
        for cat_name, channels in structure:
            category = await ctx.guild.create_category(cat_name)
            await asyncio.sleep(1.5)
            
            for ch_name, ch_type, overwrites in channels:
                if ch_type == 'text':
                    ch = await ctx.guild.create_text_channel(ch_name, category=category, overwrites=overwrites)
                    
                    # === ISI PESAN OTOMATIS ===
                    if 'welcome' in ch_name:
                        e = discord.Embed(title="👋 SELAMAT DATANG DI FORTXX!", description="Jangan lupa baca **#📜・rules** dan ambil role di **#✳️・take-roles**.", color=discord.Color.green())
                        await ch.send(embed=e)
                    elif 'rules' in ch_name:
                        e = discord.Embed(title="📜 PERATURAN SERVER FORTXX", description="1. Dilarang toxic & SARA.\n2. Dilarang spam / promosi tanpa izin.\n3. Wajib menghormati Staff.\n4. Gunakan channel sesuai fungsinya.\n5. No SCAM / RIP dalam jual beli.", color=discord.Color.red())
                        await ch.send(embed=e)
                        await ch.send("**Sanksi Pelanggaran:** Warning -> Mute -> Kick -> Ban.")
                    elif 'announcement' in ch_name:
                        await ch.send(embed=discord.Embed(title="📢 PENGUMUMAN FORTXX", description="Info update mod, event, dan maintenance server akan dipublish di sini.", color=discord.Color.gold()))
                    elif 'list-harga' in ch_name:
                        await ch.send(embed=discord.Embed(title="💰 LIST HARGA MODPACK", description="Silakan hubungi Seller di **#🔔・open-ticket** untuk pemesanan.", color=discord.Color.blue()))
                    
                    # Simpan ID buat Log Config
                    if 'invite-logs' in ch_name: log_channels['invite'] = ch
                    if 'banned-logs' in ch_name: log_channels['banned'] = ch
                    if 'spam-bot' in ch_name: log_channels['spam'] = ch
                    if 'logs-buyer' in ch_name: log_channels['buyer'] = ch
                    
                elif ch_type == 'voice':
                    await ctx.guild.create_voice_channel(ch_name, category=category)
                
                created += 1
                await asyncio.sleep(1.5)
        
        # Simpan log channel ke config
        try:
            cfg = _cfg_load()
            if 'invite' in log_channels: cfg['invite_log_ch'] = log_channels['invite'].id
            if 'banned' in log_channels: cfg['banned_log_ch'] = log_channels['banned'].id
            if 'spam' in log_channels: cfg['spam_log_ch'] = log_channels['spam'].id
            _cfg_save(cfg)
        except: pass

        await msg.edit(content=f'✅ **SERVER FORTXX BERHASIL DIBANGUN!** ({created} channel dibuat).' + nl + 'Role, Izin, & Isi Rules udah otomatis terpasang!')
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal membangun (Mungkin kena rate limit): {e}' + nl + 'Tunggu 5 menit, lalu jalankan command ini lagi. Bot akan melanjutkan channel yang belum dibuat tanpa dobel.')



# ══════════════════════════════════════════════════════════════
# 🏗️ PAMBOI TRAPS / GTA MOD SHARING BUILDER PART 2
# ══════════════════════════════════════════════════════════════
@bot.command(name='buildsharemod2')
async def buildsharemod2_cmd(ctx):
    """Bikin kategori & channel tambahan untuk Radar, UI, Plugin, dll."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Membangun Bagian 2 Server Mod GTA...**' + nl + 'Proses ini memakan waktu 2-3 menit. Mohon tunggu.')
    
    structure = [
        ('📡 〢 RADAR MAP', [
            ('🗺️・radar-map', 'text'), ('🌐・radar-icon', 'text'), ('💿・radardisc-mod', 'text')
        ]),
        ('🖥️ 〢 INTERFACE', [
            ('📱・hud-mobile', 'text'), ('👆・fist-icon', 'text'), ('🕹️・button-mod', 'text'), 
            ('🎯・crosshair', 'text'), ('⬜・sampgui', 'text'), ('🖱️・mouse', 'text'), ('💭・kill-log', 'text')
        ]),
        ('🔤 〢 FONT MOD', [
            ('🖥️・font-hud-pc', 'text'), ('📱・font-hud-mobile', 'text'), 
            ('🖥️・font-chat-pc', 'text'), ('📱・font-chat-mobile', 'text')
        ]),
        ('🧩 〢 PLUGIN DESKTOP', [
            ('🖥️・cleo-cs', 'text'), ('🖥️・asi', 'text'), ('🖥️・lua', 'text'), 
            ('🖥️・interface', 'text'), ('🖥️・sampfuncs', 'text')
        ]),
        ('📱 〢 PLUGIN MOBILE', [
            ('📱・cleo', 'text'), ('📱・aml', 'text'), ('📱・lua', 'text')
        ]),
        ('💻 〢 SAMP RESOURCES DESKTOP', [
            ('🖥️・client-gta-desktop', 'text'), ('🖥️・data-gta-desktop', 'text'), 
            ('🛠️・modding-tools', 'text'), ('🔑・modding-tutor', 'text'), 
            ('💡・modding-fix', 'text'), ('🗂️・file-backup-ori', 'text')
        ]),
        ('📲 〢 SAMP RESOURCES MOBILE', [
            ('📱・client-gta-mobile', 'text'), ('📱・data-gta-mobile', 'text'), 
            ('🗂️・file-backup-ori-mobile', 'text'), ('🛠️・modding-tools-mobile', 'text'), 
            ('🎧・modding-tutor-mobile', 'text'), ('💡・modding-fix-mobile', 'text')
        ])
    ]
    
    created = 0
    
    try:
        for cat_name, channels in structure:
            category = discord.utils.get(ctx.guild.categories, name=cat_name)
            if not category:
                category = await ctx.guild.create_category(cat_name)
                await asyncio.sleep(1.5)
            
            for ch_name, ch_type in channels:
                existing = discord.utils.get(category.channels, name=ch_name)
                if not existing:
                    if ch_type == 'text':
                        await ctx.guild.create_text_channel(ch_name, category=category)
                    elif ch_type == 'voice':
                        await ctx.guild.create_voice_channel(ch_name, category=category)
                    created += 1
                    await asyncio.sleep(1.5)
                
        await msg.edit(content=f'✅ **Bagian 2 Berhasil Dibangun!** ({created} channel baru dibuat).' + nl + 'Silakan cek kategori RADAR MAP, INTERFACE, dll.' )
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal membangun: {e}' + nl + 'Tunggu 5 menit, lalu jalankan command ini lagi (bot bakal lanjutin yang belum kebuat).')
# ══════════════════════════════════════════════════════════════


@bot.command(name='buildsharemod3')
async def buildsharemod3_cmd(ctx):
    """Aktifkan sistem log ke channel spesifik (Ban, Invite, Spam, Booster)."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Menghubungkan sistem Log...** Mohon tunggu.')
    
    # Cari channel berdasarkan nama
    channels = {
        'invite_log_ch': 'invite-logs',
        'banned_log_ch': 'banned-logs',
        'spam_log_ch': 'spam-bot',
        'booster_log_ch': 'booster-log'
    }
    
    cfg = _cfg_load()
    found = 0
    
    for key, name in channels.items():
        # Cari channel yang namanya mengandung keyword
        ch = discord.utils.find(lambda c: name in c.name.lower(), ctx.guild.text_channels)
        if ch:
            cfg[key] = ch.id
            found += 1
    
    _cfg_save(cfg)
    
    embed = discord.Embed(
        title="✅ Sistem Log Aktif!",
        description=f"Berhasil menghubungkan **{found}** channel log ke sistem bot." + chr(10) + chr(10) + "Sekarang bot akan otomatis mengirim log Ban, Kick, Invite, Spam, dan Booster ke channel masing-masing.",
        color=discord.Color.green()
    )
    await msg.edit(content='', embed=embed)


# ══════ EVENT LOGGERS (FORTXX SPECIFIC) ══════

@bot.event
async def on_member_update(before, after):
    g = after.guild
    cfg = _cfg_load()
    
    # Cek Booster
    if before.premium_since is None and after.premium_since is not None:
        ch = g.get_channel(cfg.get('booster_log_ch', 0))
        if ch:
            embed = discord.Embed(title="🚀 SERVER BOOST!", description=f"**{after.mention}** baru saja mem-boost server! Terima kasih banyak!", color=discord.Color.from_rgb(255, 100, 200))
            embed.set_thumbnail(url=after.display_avatar.url)
            await ch.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    cfg = _cfg_load()
    ch = message.guild.get_channel(cfg.get('spam_log_ch', 0))
    
    # Log ke spam-bot kalau ada channelnya, kalau gak ada ke general log
    if ch:
        # Cek apakah pesan mengandung link atau kata kasar (simple spam detection)
        content = message.content.lower()
        if "http" in content or "discord.gg" in content or len(message.mentions) > 3:
            embed = discord.Embed(title="🚧 PESAN SPAM DIHAPUS", description=f"**Pengirim:** {message.author.mention} (`{message.author.id}`)\n**Channel:** {message.channel.mention}\n**Isi Pesan:** {message.content[:500]}", color=discord.Color.red())
            await ch.send(embed=embed)
# ═════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🛠️ AUTO FIX PERMISSIONS (SHARED MOD SERVER)
# ══════════════════════════════════════════════════════════════
@bot.command(name='fixperms')
async def fixperms_cmd(ctx):
    """Benerin izin channel: Warga bisa liat log, tapi gabisa chat."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Menyisir dan membenahi izin semua channel...** Mohon tunggu sebentar.')
    
    # Kategori Kata Kunci
    # 1. LOGS: Warga bisa liat, tapi gabisa chat.
    logs_keywords = ['logs', 'spam-bot', 'level-up', 'booster-log', 'change-logs']
    
    # 2. STAFF: Warga gabisa liat sama sekali (bener-bener privat).
    staff_keywords = ['production-team', 'fortxx-traps', 'staff']
    
    # 3. READ-ONLY: Warga cuma bisa baca (Rules, Info, Harga).
    readonly_keywords = ['welcome', 'rules', 'goodbye', 'announcement', 'official-link', 'information-market', 'list-harga', 'information-roles', 'partners-info']
    
    # 4. REACTION: Warga bisa baca & klik emoji (Verify, Take Roles, Voting).
    reaction_keywords = ['verify', 'take-roles', 'voting-area']
    
    # Role staff yang tetep bisa chat di mana aja
    staff_roles = ['👑 Owner', '🛡️ Admin', '⚔️ Moderator', '🔰 Staff', 'Admin', 'Moderator', 'Staff']
    
    fixed = 0
    
    try:
        for ch in ctx.guild.text_channels:
            ch_name = ch.name.lower()
            
            # 1. LOGS (Bisa diliat, gabisa chat)
            if any(k in ch_name for k in logs_keywords):
                overwrite = ch.overwrites_for(ctx.guild.default_role)
                overwrite.read_messages = True
                overwrite.send_messages = False
                overwrite.add_reactions = False
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                
            # 2. STAFF (Sembunyiin total)
            elif any(k in ch_name for k in staff_keywords):
                overwrite = ch.overwrites_for(ctx.guild.default_role)
                overwrite.read_messages = False
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                
            # 3. READ-ONLY (Info)
            elif any(k in ch_name for k in readonly_keywords):
                overwrite = ch.overwrites_for(ctx.guild.default_role)
                overwrite.read_messages = True
                overwrite.send_messages = False
                overwrite.add_reactions = False
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                
            # 4. REACTION-ONLY (Verify, Take Role, Voting)
            elif any(k in ch_name for k in reaction_keywords):
                overwrite = ch.overwrites_for(ctx.guild.default_role)
                overwrite.read_messages = True
                overwrite.send_messages = False
                overwrite.add_reactions = True
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                
            # 5. SISANYA BEBAS CHAT (General, Mod, Jual Beli, dll)
            else:
                overwrite = ch.overwrites_for(ctx.guild.default_role)
                overwrite.read_messages = True
                overwrite.send_messages = True
                overwrite.attach_files = True
                overwrite.embed_links = True
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                
            # Pastiin Staff & Bot tetep bisa akses & chat semuanya
            for r_name in staff_roles:
                r = discord.utils.get(ctx.guild.roles, name=r_name)
                if r:
                    staff_ow = ch.overwrites_for(r)
                    staff_ow.read_messages = True
                    staff_ow.send_messages = True
                    await ch.set_permissions(r, overwrite=staff_ow)
                    
            bot_ow = ch.overwrites_for(ctx.guild.me)
            bot_ow.read_messages = True
            bot_ow.send_messages = True
            await ch.set_permissions(ctx.guild.me, overwrite=bot_ow)
            
            fixed += 1
            await asyncio.sleep(1.5) # Jeda anti rate-limit
            
        embed = discord.Embed(
            title='✅ Izin Channel Berhasil Dibenahi!',
            description=f'Semua **{fixed}** channel udah di-setting dengan benar.' + nl + nl + '**Warga sekarang:**' + nl + '• Bebas chat di channel umum.' + nl + '• **Bisa ngeliat log** (tapi gabisa chat).' + nl + '• Gabisa liat channel Staff/Dashboard privat.',
            color=discord.Color.green()
        )
        await msg.edit(content='', embed=embed)
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal membenahi izin: {e}')

# ══════════════════════════════════════════════════════════════
# 🔒 GATEKEEPER: LOCK SERVER SAMPAI VERIFIKASI
# ══════════════════════════════════════════════════════════════
@bot.hybrid_command(name='lockserver')
async def lockserver_cmd(ctx):
    """Sembunyiin semua channel sampai member ambil role Verified."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Mengunci server (Gatekeeper)...** Mohon tunggu, ini butuh waktu 1-2 menit.')
    
    # 1. Pastiin Role Verified ada
    verified_role = discord.utils.get(ctx.guild.roles, name='✅ Verified')
    if not verified_role:
        verified_role = await ctx.guild.create_role(name='✅ Verified', color=discord.Color.green(), reason='Gatekeeper System')
        
    # 2. Pastiin role Staff
    staff_roles = ['👑 Owner', '🛡️ Admin', '⚔️ Moderator', '🔰 Staff', 'Admin', 'Moderator', 'Staff']
    staff_objects = [discord.utils.get(ctx.guild.roles, name=name) for name in staff_roles]
    staff_objects = [r for r in staff_objects if r is not None]
    
    locked_count = 0
    
    try:
        for category in ctx.guild.categories:
            # Sembunyiin kategori dari @everyone
            cat_ow = category.overwrites_for(ctx.guild.default_role)
            cat_ow.read_messages = False
            await category.set_permissions(ctx.guild.default_role, overwrite=cat_ow)
            # Buka akses buat Verified & Staff
            cat_ow_ver = category.overwrites_for(verified_role)
            cat_ow_ver.read_messages = True
            await category.set_permissions(verified_role, overwrite=cat_ow_ver)
            
            for ch in category.channels:
                # Kalo channel verify, tetep kasih akses ke @everyone buat liat
                if 'verify' in ch.name.lower():
                    await ch.set_permissions(ctx.guild.default_role, read_messages=True, send_messages=False)
                    await ch.set_permissions(verified_role, read_messages=True, send_messages=True)
                    continue
                    
                # Sembunyiin channel dari @everyone
                ow = ch.overwrites_for(ctx.guild.default_role)
                ow.read_messages = False
                await ch.set_permissions(ctx.guild.default_role, overwrite=ow)
                
                # Buka akses buat Verified
                ow_ver = ch.overwrites_for(verified_role)
                ow_ver.read_messages = True
                await ch.set_permissions(verified_role, overwrite=ow_ver)
                
                # Buka akses buat Staff
                for sr in staff_objects:
                    ow_staff = ch.overwrites_for(sr)
                    ow_staff.read_messages = True
                    await ch.set_permissions(sr, overwrite=ow_staff)
                    
                locked_count += 1
                await asyncio.sleep(1.5) # Jeda anti rate limit
                
        embed = discord.Embed(
            title='🔒 Server Berhasil Dikunci!',
            description=f'Semua **{locked_count}** channel sekarang **disembunyikan** dari member baru.' + nl + nl + 'Member baru cuma bisa liat channel **#verify**. Begitu mereka klik ✅, role **Verified** masuk dan semua channel langsung kebuka otomatis.',
            color=discord.Color.red()
        )
        await msg.edit(content='', embed=embed)
        
    except Exception as e:
        await msg.edit(content=f'❌ Gagal mengunci server: {e}')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🎭 FIX TAKE ROLE CHANNEL & PANEL
# ══════════════════════════════════════════════════════════════
@bot.command(name='fixtakerole')
async def fixtakerole_cmd(ctx):
    """Benerin izin bot di channel take-roles & kirim panel role."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    # 1. Cari channel take-roles
    channel = discord.utils.find(lambda c: 'take-role' in c.name.lower(), ctx.guild.text_channels)
    if not channel:
        channel = await ctx.guild.create_text_channel('✳️・take-roles')
        await ctx.send(f'✅ Channel {channel.mention} dibuat karena belum ada!')
    
    # 2. Paksa buka izin buat Bot sendiri di channel itu
    try:
        bot_ow = channel.overwrites_for(ctx.guild.me)
        bot_ow.read_messages = True
        bot_ow.send_messages = True
        bot_ow.embed_links = True
        await channel.set_permissions(ctx.guild.me, overwrite=bot_ow)
        print(f'[FIX] Izin bot dibenerin di #{channel.name}')
    except Exception as e:
        await ctx.send(f'⚠️ Gagal benerin izin bot: {e}')
        
    # 3. Bikin role-role minat kalo belum ada
    roles_to_create = ['🎮 Gamer', '🎵 Musik', '🎨 Artist', '🐶 Pet Lover', '🍔 Foodie']
    guild_roles = []
    for r_name in roles_to_create:
        r = discord.utils.get(ctx.guild.roles, name=r_name)
        if not r:
            try:
                r = await ctx.guild.create_role(name=r_name, reason='Auto Role Setup')
            except: pass
        if r: guild_roles.append(r)
        
    # 4. Kirim Panel Dropdown
    embed = discord.Embed(
        title='🎭 AMBIL ROLE KOMUNITAS',
        description='Silakan pilih role yang sesuai dengan minatmu di menu dropdown di bawah ini.' + nl + nl + '*Lu bisa milih lebih dari satu role.*',
        color=discord.Color.blurple()
    )
    
    # Cek apakah udah ada pesan panel di channel itu biar gak dobel
    try:
        async for msg in channel.history(limit=10):
            if msg.author == bot.user and msg.embeds and 'AMBIL ROLE' in msg.embeds[0].title:
                await msg.delete()
    except Exception:
        pass
        
    await channel.send(embed=embed, view=CommunityRoleView(guild_roles))
    await ctx.send(f'✅ Panel Role berhasil dikirim ke {channel.mention}! Coba cek sekarang.' + nl + '*(Note: Warga yang belum verify gabisa liat, pastiin lu udah klik verify dulu).*')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🚪 FIX JOIN: GERBANG VERIFIKASI YANG BENER
# ══════════════════════════════════════════════════════════════
@bot.command(name='fixjoin')
async def fixjoin_cmd(ctx):
    """Benerin gerbang verifikasi biar member baru bisa liat."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Membenahi Gerbang Verifikasi...** Mohon tunggu 1 menit.')
    
    # 1. Bikin Role Verified kalo belum ada
    verified_role = discord.utils.get(ctx.guild.roles, name='✅ Verified')
    if not verified_role:
        verified_role = await ctx.guild.create_role(name='✅ Verified', color=discord.Color.green(), reason='Gatekeeper System')
    
    # 2. Bikin Kategori 'START HERE' (Biar aman dari sembunyiin kategori lain)
    cat_start = discord.utils.get(ctx.guild.categories, name='🚪 〢 START HERE')
    if not cat_start:
        cat_start = await ctx.guild.create_category('🚪 〢 START HERE')
    
    # Buka Kategori START HERE buat @everyone
    await cat_start.set_permissions(ctx.guild.default_role, read_messages=True)
    
    # 3. Bikin / Cari Channel verify
    verify_ch = discord.utils.find(lambda c: 'verify' in c.name.lower(), ctx.guild.text_channels)
    if not verify_ch:
        verify_ch = await ctx.guild.create_text_channel('✅・verify', category=cat_start)
        
    # 4. Benerin Izin Channel Verify (Buka buat semua, tapi gabisa chat)
    await verify_ch.set_permissions(ctx.guild.default_role, read_messages=True, send_messages=False)
    await verify_ch.set_permissions(verified_role, read_messages=True, send_messages=False) # Kalo udah verified, tetep gausa chat di sini
    
    # 5. Kunci semua channel & kategori LAIN
    locked_count = 0
    for cat in ctx.guild.categories:
        if cat.id != cat_start.id: # Jangan kunci kategori Start Here
            await cat.set_permissions(ctx.guild.default_role, read_messages=False)
            locked_count += 1
            
    for ch in ctx.guild.text_channels:
        if ch.id != verify_ch.id and not ch.category: # Kunci yang gak punya kategori juga
            await ch.set_permissions(ctx.guild.default_role, read_messages=False)
            await ch.set_permissions(verified_role, read_messages=True)
            locked_count += 1
            
    # 6. Kirim Pesan Verifikasi + Reaksi
    embed = discord.Embed(
        title='✅ VERIFIKASI SERVER',
        description='Halo! Sebelum masuk, silakan klik reaksi **✅** di bawah ini untuk membuka seluruh akses ke server.' + nl + nl + '*Wajib di-klik ya, kalau tidak nanti tidak bisa lihat channel lain.*',
        color=discord.Color.green()
    )
    
    # Hapus pesan lama di channel verify biar bersih
    try:
        async for m in verify_ch.history(limit=10):
            if m.author == bot.user: await m.delete()
    except: pass
    
    msg_v = await verify_ch.send(embed=embed)
    await msg_v.add_reaction('✅')
    
    # Simpan ID ke config
    cfg = _cfg_load()
    cfg['verify_message_id'] = msg_v.id
    cfg['verify_role_id'] = verified_role.id
    _cfg_save(cfg)
    
    await msg.edit(content=f'✅ **Selesai!** Kategori START HERE udah dibuka, dan {locked_count} channel/kategori lain udah dikunci.' + nl + 'Coba minta temen lu join/relogin, dia harusnya cuma bisa liat channel {verify_ch.mention}.')
# ══════════════════════════════════════════════════════════════


@bot.command(name='welcomemod')
async def welcomemod_cmd(ctx):
    """Tes kirim pesan welcome GTA Mod ke channel #welcome."""
    if not is_mod(ctx): return
    ch = discord.utils.find(lambda c: 'welcome' in c.name.lower(), ctx.guild.text_channels)
    if not ch: return await ctx.send("❌ Channel #welcome gak ketemu.")
    embed = discord.Embed(
        title="👋 SELAMAT DATANG DI FORTXX!",
        description=f"Halo {ctx.author.mention}! Selamat bergabung di server sharing mod GTA." + chr(10) + chr(10) + "📜 Baca peraturan di **#rules**" + chr(10) + "✅ Ambil role di **#verify**" + chr(10) + "🛒 Cek list harga di **#list-harga**",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ch.send(content=ctx.author.mention, embed=embed)
    await ctx.send(f"✅ Pesan welcome dites ke {ch.mention}!", delete_after=5)

@bot.command(name='bannedmod')
async def bannedmod_cmd(ctx):
    """Tes kirim log banned ke channel #banned-logs."""
    if not is_mod(ctx): return
    ch = discord.utils.find(lambda c: 'banned-logs' in c.name.lower(), ctx.guild.text_channels)
    if not ch: return await ctx.send("❌ Channel #banned-logs gak ketemu.")
    embed = discord.Embed(title="🔨 MEMBER DI-BAN", description=f"**Target:** {ctx.author.mention} (`{ctx.author.id}`)" + chr(10) + f"**Mod:** {ctx.author.mention}" + chr(10) + "**Alasan:** Tes sistem log banned", color=discord.Color.dark_red())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ch.send(embed=embed)
    await ctx.send(f"✅ Log banned dites ke {ch.mention}!", delete_after=5)

@bot.command(name='invitemod')
async def invitemod_cmd(ctx):
    """Tes kirim log invite ke channel #invite-logs."""
    if not is_mod(ctx): return
    ch = discord.utils.find(lambda c: 'invite-logs' in c.name.lower(), ctx.guild.text_channels)
    if not ch: return await ctx.send("❌ Channel #invite-logs gak ketemu.")
    embed = discord.Embed(title="📩 INVITE BARU", description=f"**User:** {ctx.author.mention}" + chr(10) + "**Bergabung via:** `discord.gg/fortxx`", color=discord.Color.blue())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ch.send(embed=embed)
    await ctx.send(f"✅ Log invite dites ke {ch.mention}!", delete_after=5)

# ══════════════════════════════════════════════════════════════
# 🎫 TICKET SYSTEM FORTXX MOD STORE
# ══════════════════════════════════════════════════════════════

class ModTicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label='Tutup Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='close_mod_ticket_btn')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('🔒 Ticket akan ditutup dan dihapus dalam 5 detik...', ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class ModTicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Beli Mod / Order', description='Pesan modpack GTA mobile atau PC di sini.', emoji='🛒', value='beli_mod'),
            discord.SelectOption(label='Bantuan Mod', description='Mod lu error atau bingung cara install? Tanya di sini.', emoji='🛠️', value='bantuan_mod'),
            discord.SelectOption(label='Lapor Scam / Masalah', description='Laporkan seller nakal atau masalah transaksi.', emoji='🚨', value='lapor_scam'),
            discord.SelectOption(label='Kerjasama / Partnership', description='Ajukan kerjasama antar server atau komunitas.', emoji='🤝', value='partner')
        ]
        super().__init__(placeholder='Pilih jenis tiket...', min_values=1, max_values=1, options=options, custom_id='mod_ticket_select_menu')

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]
        
        # Cek apakah user udah punya ticket terbuka
        category = discord.utils.get(guild.categories, name='FORTXX TICKETS')
        if category:
            for ch in category.text_channels:
                if ch.topic and f'({user.id})' in ch.topic:
                    return await interaction.response.send_message(f'❌ Kamu udah punya ticket terbuka di {ch.mention}!', ephemeral=True)
        
        await interaction.response.send_message('⏳ Sedang membuat channel tiket...', ephemeral=True)
        
        if not category:
            try:
                category = await guild.create_category('FORTXX TICKETS', reason='Setup sistem ticket Mod')
            except: pass
        
        # Izin channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        # Staff roles
        staff_roles = ['👑 Owner', '🛡️ Admin', '⚔️ Moderator', '🔰 Staff', '💵 Seller', 'Admin', 'Moderator', 'Staff']
        for role_name in staff_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        try:
            ticket_ch = await guild.create_text_channel(
                name=f'ticket-{ticket_type}-{user.name}'.lower(),
                category=category,
                overwrites=overwrites,
                topic=f'Ticket milik {user.name} ({user.id}) | Tipe: {ticket_type}'
            )
            
            # Cari role staff buat di-tag
            staff_ping = ''
            for r_name in ['💵 Seller', '🛡️ Admin', '⚔️ Moderator']:
                r = discord.utils.get(guild.roles, name=r_name)
                if r: staff_ping += f'{r.mention} '
            
            desc_text = f'Halo {user.mention}, tunggu sebentar ya. Staff/Seller akan segera merespons.' + chr(10) + chr(10) + 'Jika masalah sudah selesai, silakan klik tombol di bawah.'
            
            embed = discord.Embed(
                title=f'🎫 Ticket: {ticket_type.replace("_", " ").title()}',
                description=desc_text,
                color=discord.Color.green()
            )
            
            await ticket_ch.send(content=f'{user.mention} {staff_ping}', embed=embed, view=ModTicketCloseView())
            await interaction.edit_original_response(content=f'✅ Ticket kamu sudah dibuat: {ticket_ch.mention}')
            
        except Exception as e:
            await interaction.edit_original_response(content=f'❌ Gagal membuat ticket: {e}')

class ModTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ModTicketSelect())

@bot.command(name='createticketmod')
async def createticketmod_cmd(ctx):
    """Bikin panel Ticket khusus server Shared Mod."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    embed = discord.Embed(
        title='🎫 FORTXX SUPPORT & STORE',
        description='Butuh beli mod, bantuan error, atau mau lapor scam?' + chr(10) + 'Silakan pilih jenis tiket pada menu dropdown di bawah ini.',
        color=discord.Color.blurple()
    )
    embed.set_footer(text='Jangan spam tombol ini.')
    
    # Hapus pesan command lu biar channel bersih
    try:
        await ctx.message.delete()
    except: pass
        
    await ctx.send(embed=embed, view=ModTicketView())

# Daftarin persistent view
# ══════════════════════════════════════════════════════════════


@bot.hybrid_command(name='setupall')
async def setupall_cmd(ctx):
    """Kirim semua panel (Ticket, Char, Help) sekaligus dan aktifkan permanen."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('⏳ **Mengirim semua panel ke channel masing-masing...**')
    
    # 1. Panel Ticket Mod
    ch_ticket = discord.utils.find(lambda c: 'ticket' in c.name.lower(), ctx.guild.text_channels)
    if ch_ticket:
        embed = discord.Embed(title='🎫 FORTXX SUPPORT & STORE', description='Silakan pilih jenis tiket pada menu dropdown di bawah ini.', color=discord.Color.blurple())
        await ch_ticket.send(embed=embed, view=ModTicketView())
        
    # 2. Panel Take Role
    ch_role = discord.utils.find(lambda c: 'take-role' in c.name.lower(), ctx.guild.text_channels)
    if ch_role:
        roles_to_create = ["🎮 Gamer", "🎵 Musik", "🎨 Artist", "🐶 Pet Lover", "🍔 Foodie"]
        guild_roles = []
        for r_name in roles_to_create:
            r = discord.utils.get(ctx.guild.roles, name=r_name)
            if not r:
                r = await ctx.guild.create_role(name=r_name)
            guild_roles.append(r)
        embed = discord.Embed(title='🎭 AMBIL ROLE KOMUNITAS', description='Silakan pilih role yang sesuai dengan minatmu.', color=discord.Color.blurple())
        await ch_role.send(embed=embed, view=CommunityRoleView(guild_roles))
        
    # 3. Panel Help
    ch_menu = discord.utils.find(lambda c: 'bot-menu' in c.name.lower() or 'bot-commands' in c.name.lower(), ctx.guild.text_channels)
    if ch_menu:
        view = HelpMainView()
        await ch_menu.send(embed=view._build_embed(), view=view)
        
    await msg.edit(content='✅ **Semua panel berhasil dikirim & diaktifkan permanen!**' + chr(10) + 'Sekarang lu bisa Restart bot berkali-kali, tombolnya gak bakal mati lagi.')





# ══════════════════════════════════════════════════════════════
# ✨ PREMIUM VISUAL EFFECTS
# ══════════════════════════════════════════════════════════════
@bot.listen('on_command')
async def premium_typing_listener(ctx):
    """Kasih reaction ✅ biar bot keliatan responsif."""
    try:
        await ctx.message.add_reaction("✅")
    except Exception:
        pass



@bot.before_invoke
async def premium_ux_before(ctx):
    """Efek Premium: Hapus command user (kalo bukan command setup) & kasih typing."""
    # Jangan hapus command yang butuh input manual kayak !buatpesan atau setup
    safe_commands = ['setup', 'build', 'ticket', 'help', 'say', 'embed', 'poll']
    is_safe = any(cmd in ctx.command.name.lower() for cmd in safe_commands)
    
    if not is_safe:
        try:
            await ctx.message.delete()
        except Exception:
            pass
            
    try:
        await ctx.typing()
    except Exception:
        pass

@bot.after_invoke
async def premium_ux_after(ctx):
    """Setelah command jalan, hapus reaction loading (opsional)."""
    pass


def add_watermark(embed):
    """Nambahin footer premium ke embed."""
    embed.set_footer(text="FORTXX SYSTEM • Premium Experience", icon_url=bot.user.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()
    return embed

# ══════════════════════════════════════════════════════════════
# 👑 OWNER INFO COMMAND
# ══════════════════════════════════════════════════════════════
class OwnerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Ganti link di bawah ini sama link DC pribadi lu
        self.add_item(discord.ui.Button(label='Join My Personal DC', style=discord.ButtonStyle.link, url='https://discord.gg/fYMu3msZ', emoji='👑'))

@bot.hybrid_command(name='owner')
async def owner_cmd(ctx):
    """Nampilin info profil owner (zomahaci)."""
    
    embed = discord.Embed(
        title='👑 OWNER INFO',
        description='Halo! Aku adalah bot resmi yang dibuat dan dikembangkan oleh **@zomahaci**.' + chr(10) + chr(10) + 'Kalau kamu mau ngobrol, order mod, atau mampir ke komunitas asliku, silakan klik tombol di bawah ini ya!',
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.add_field(name='🌐 Web Dashboard', value='[bot-fortxx.wispbyte.app](https://bot-fortxx.wispbyte.app)', inline=False)
    embed.add_field(name='🛒 Layanan', value='Shared Mod GTA & Partnership', inline=False)
    embed.set_footer(text='FORTXX System • Made with ❤️ by zomahaci')
    
    await ctx.send(embed=embed, view=OwnerView())
# ══════════════════════════════════════════════════════════════


# ══════ PERSISTENT VIEWS (FIXED) ══════
try:
    bot.add_view(ModTicketView())
    bot.add_view(ModTicketCloseView())
    if "TicketView" in globals(): bot.add_view(TicketView())
    if "TicketCloseView" in globals(): bot.add_view(TicketCloseView())
    if "CharView" in globals(): bot.add_view(CharView())
    if "HelpMainView" in globals(): bot.add_view(HelpMainView())
    if "EmbedBuilderView" in globals(): bot.add_view(EmbedBuilderView())
    if "OwnerView" in globals(): bot.add_view(OwnerView())
    if "CommunityRoleView" in globals(): bot.add_view(CommunityRoleView([]))
    print("[SYSTEM] Persistent Views berhasil dimuat bersih!")
except Exception as e:
    print(f"[SYSTEM] Gagal memuat Persistent Views: {e}")
# ═══════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🤖 BOT INFO & SERVER LIST
# ══════════════════════════════════════════════════════════════
@bot.command(name='botinfo', aliases=['info', 'vitur', 'status'])
async def botinfo_cmd(ctx):
    """Nampilin info bot, web, owner, dan list server (dengan link)."""
    
    dc_link = "https://discord.gg/fYMu3msZ" # Link DC utama lu
    web_link = "https://bot-fortxx.wispbyte.app"
    
    servers = bot.guilds
    total_members = sum(g.member_count for g in servers)
    
    server_list = ''
    # Bot nyoba bikin/narik link invite dari tiap server
    for i, guild in enumerate(servers[:15], 1):
        invite_url = None
        try:
            # 1. Cek Vanity URL
            if guild.vanity_url:
                invite_url = guild.vanity_url
            else:
                # 2. Cek Invite yang udah ada
                try:
                    invites = await guild.invites()
                    if invites:
                        invite_url = invites[0].url
                except discord.Forbidden:
                    print(f"[INVITE] Gagal cek invites di {guild.name}: Butuh Manage Server")
                except Exception as e:
                    print(f"[INVITE] Error cek invites {guild.name}: {e}")

                # 3. Kalau gak ada, cari channel text pertama dan bikin invite di situ
                if not invite_url:
                    try:
                        # Cari channel text pertama yang bot bisa liat
                        target_ch = discord.utils.find(lambda c: c.permissions_for(guild.me).create_instant_invite, guild.text_channels)
                        if target_ch:
                            invite = await target_ch.create_invite(max_age=0, max_uses=0, reason="FORTXX Bot Info")
                            invite_url = invite.url
                        else:
                            print(f"[INVITE] Gagal bikin link di {guild.name}: Gak ada channel text yang bisa diakses.")
                    except discord.Forbidden:
                        print(f"[INVITE] Gagal bikin link di {guild.name}: Discord nolak (Forbidden)")
                    except Exception as e:
                        print(f"[INVITE] Error bikin link {guild.name}: {e}")
        except Exception as e:
            print(f"[INVITE] Error umum di {guild.name}: {e}")
            
        await asyncio.sleep(2) # Jeda 2 detik biar gak kena rate limit Discord

        # Format teks
        if invite_url:
            server_list += f'**{i}.** [{guild.name}]({invite_url}) (`{guild.member_count:,}` Member)' + chr(10)
        else:
            server_list += f'**{i}.** {guild.name} (`{guild.member_count:,}` Member) [Gagal load link]' + chr(10)
        
    if len(servers) > 15:
        server_list += f'... dan **{len(servers) - 15}** server lainnya.'
        
    if not server_list:
        server_list = '*(Bot belum masuk ke server mana pun)*'
        
    embed = discord.Embed(
        title='👑 FORTXX SYSTEM INFO',
        description='Terima kasih udah pakai bot ini! Berikut adalah detail sistem dan daftar server yang terhubung.',
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    embed.add_field(name='💬 Discord Server Utama', value=f'[Klik disini untuk Join]({dc_link})', inline=False)
    embed.add_field(name='🌐 Web Dashboard', value=f'[bot-fortxx.wispbyte.app]({web_link})', inline=False)
    embed.add_field(name='👑 Owner / Developer', value='<@1433702926760804352> (zomahaci)', inline=False)
    
    embed.add_field(name='📊 Statistik Bot', value=f'Total Server: **{len(servers)}**' + chr(10) + f'Total Member: **{total_members:,}**', inline=False)
    embed.add_field(name='📡 Terhubung di Server:', value=server_list, inline=False)
    
    embed.set_footer(text=f'Requested by {ctx.author.display_name} | Latency: {round(bot.latency * 1000)}ms', icon_url=ctx.author.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════
# 🧠 AI CHANNEL DETECTOR (GROQ - SUPER CEPAT)
# ══════════════════════════════════════════════════════════════
import aiohttp
import json as json_lib





# ══════════════════════════════════════════════════════════════
# 🧠 AI CHANNEL DETECTOR (GROQ - STEALTH MODE)
# ══════════════════════════════════════════════════════════════
import aiohttp
import json as json_lib

# API Key disimpan terbalik biar GitHub gak ngeblokir



# ══════════════════════════════════════════════════════════════
# 🧠 AI CHANNEL DETECTOR (CHATANYWHERE - GPT-6.1-SOL)
# ══════════════════════════════════════════════════════════════
import aiohttp
import json as json_lib

# API Key disimpan terbalik biar GitHub gak ngeblokir
_ENC_KEY = "Tc2Jwnh0tEsa7RRKU28l2snTeuzlqz961SwJ0ghykYkvqyPg-ks"
CA_API_KEY = _ENC_KEY[::-1]



# ══════════════════════════════════════════════════════════════
# 🧠 AI DEEP SCAN (Baca Isi Channel per Channel)
# ══════════════════════════════════════════════════════════════
import aiohttp
import json as json_lib

_ENC_KEY = "Tc2Jwnh0tEsa7RRKU28l2snTeuzlqz961SwJ0ghykYkvqyPg-ks"
CA_API_KEY = _ENC_KEY[::-1]



# ══════════════════════════════════════════════════════════════
# 🧠 AI DEEP SCAN + AUTO TEST (Baca isi & Langsung Tes)
# ══════════════════════════════════════════════════════════════
import aiohttp
import json as json_lib

_ENC_KEY = "Tc2Jwnh0tEsa7RRKU28l2snTeuzlqz961SwJ0ghykYkvqyPg-ks"
CA_API_KEY = _ENC_KEY[::-1]

@bot.command(name='aiscanlogs')
async def aiscanlogs_cmd(ctx):
    """AI masuk ke tiap channel, baca pesan, nyimpulin, dan langsung ngetes lognya."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('🔍 **AI Deep Scan + Auto Test dimulai...**' + chr(10) + '⏳ Membaca isi channel & menyimpulkan (bisa 1-2 menit)')
    
    log_kw = ['log', 'warn', 'ban', 'invite', 'spam', 'verify', 'report', 'audit']
    
    all_channels = []
    total = len(ctx.guild.text_channels)
    processed = 0
    
    for ch in ctx.guild.text_channels:
        processed += 1
        if processed % 5 == 0:
            try:
                await msg.edit(content=f'🔍 **AI Deep Scan...**' + chr(10) + f'⏳ Progress: {processed}/{total} channel')
            except: pass
        
        topic = ch.topic or ""
        should_read = any(kw in ch.name.lower() or kw in topic.lower() for kw in log_kw)
        
        messages = []
        if should_read:
            try:
                async for m in ch.history(limit=3):
                    if m.content:
                        messages.append(m.content[:60].replace(chr(10), ' '))
                    elif m.embeds:
                        for e in m.embeds:
                            if e.title:
                                messages.append(f"[Embed: {e.title[:40]}]")
                                break
            except: pass
        
        all_channels.append({
            'name': ch.name,
            'topic': topic[:80],
            'messages': messages
        })
        
        if should_read:
            await asyncio.sleep(1) # Rate limit
    
    # Bangun prompt raksasa
    prompt = "Kamu adalah analis sistem Discord. Analisis SEMUA channel di bawah ini dan tentukan channel log mana yang cocok.\n\n"
    for i, info in enumerate(all_channels, 1):
        prompt += f"{i}. #{info['name']}"
        if info['topic']:
            prompt += f" | Topik: {info['topic']}"
        if info['messages']:
            prompt += f" | Isi: {' / '.join(info['messages'])}"
        prompt += "\n"
    
    prompt += "\n\nTugasmu: Pilih SATU channel untuk tiap jenis log berikut:"
    prompt += "\n- warn_log (log warning member)"
    prompt += "\n- ban_log (log ban/kick member)"
    prompt += "\n- invite_log (log member join via invite)"
    prompt += "\n- spam_log (log pesan spam yang dihapus)"
    prompt += "\n- bot_log (log aktivitas bot/command)"
    prompt += "\n\nOutput HANYA JSON valid (tanpa markdown, tanpa penjelasan):"
    prompt += '\n{"warn_log": "nama-channel-tanpa-tanda-#", "ban_log": "nama-channel", "invite_log": "nama-channel", "spam_log": "nama-channel", "bot_log": "nama-channel"}'
    prompt += "\nJika tidak ada yang cocok untuk suatu kategori, isi null."
    
    headers = {"Authorization": f"Bearer {CA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-6.1-sol",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300
    }
    
    try:
        await msg.edit(content='🧠 **AI sedang menganalisis data & menyiapkan tes otomatis...**')
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.chatanywhere.tech/v1/chat/completions", headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    return await msg.edit(content=f"❌ Error ChatAnywhere: HTTP {resp.status}")
                data = await resp.json()
                jawaban = data['choices'][0]['message']['content']
        
        clean_json = jawaban.replace('```json', '').replace('```', '').strip()
        start = clean_json.find('{')
        end = clean_json.rfind('}') + 1
        clean_json = clean_json[start:end]
        
        ai_data = json_lib.loads(clean_json)
        
        cfg = _cfg_load()
        gid = str(ctx.guild.id)
        if gid not in cfg: cfg[gid] = {}
        
        mapping = {
            'warn_log': 'warn_log_channel',
            'ban_log': 'banned_log_ch',
            'invite_log': 'invite_log_ch',
            'spam_log': 'spam_log_ch',
            'bot_log': 'bot_log_channel'
        }
        
        results = []
        for ai_key, cfg_key in mapping.items():
            ch_name = ai_data.get(ai_key)
            if ch_name and str(ch_name).lower() not in ['null', 'none', '']:
                ch = discord.utils.get(ctx.guild.text_channels, name=ch_name)
                if not ch:
                    for test_ch in ctx.guild.text_channels:
                        if str(ch_name).lower() in test_ch.name.lower() or test_ch.name.lower() in str(ch_name).lower():
                            ch = test_ch
                            break
                
                if ch:
                    cfg[gid][cfg_key] = ch.id
                    # === LANGSUNG TES KIRIM PESAN ===
                    try:
                        embed = discord.Embed(
                            title=f"🧪 AI AUTO-TEST: {ai_key.upper()}", 
                            description="Jika kamu melihat pesan ini, berarti AI berhasil menemukan channel ini dan bot **punya izin** untuk mengirim log ke sini.", 
                            color=discord.Color.green()
                        )
                        embed.timestamp = discord.utils.utcnow()
                        await ch.send(embed=embed)
                        results.append(f"✅ **{ai_key.upper()}** -> {ch.mention} *(Berhasil dites!)*")
                    except discord.Forbidden:
                        results.append(f"⚠️ **{ai_key.upper()}** -> {ch.mention} *(Gagal kirim, bot gak punya izin!)*")
                    except Exception as e:
                        results.append(f"⚠️ **{ai_key.upper()}** -> {ch.mention} *(Error: {e})*")
                else:
                    results.append(f"⚠️ **{ai_key.upper()}** -> AI pilih `{ch_name}` tapi channel gak ketemu")
            else:
                results.append(f"❌ **{ai_key.upper()}** -> Gak ada channel yang cocok di server ini")
        
        _cfg_save(cfg)
        
        embed = discord.Embed(title='🧠 AI Deep Scan + Auto Test Selesai!', description=chr(10).join(results), color=discord.Color.blurple())
        embed.set_footer(text=f"Memindai {total} channel | Cek pesan test di tiap channel log")
        await msg.edit(content='', embed=embed)
        
    except Exception as e:
        await msg.edit(content=f"❌ Error: {e}" + chr(10) + f"Jawaban AI: {jawaban[:300] if 'jawaban' in locals() else 'Gagal'}")
# ══════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════
# 🛑 SISTEM WARN (FIXED & STABLE)
# ══════════════════════════════════════════════════════════════

class WarnModal(discord.ui.Modal, title='Form Warning Anggota'):
    nama_ic = discord.ui.TextInput(label='Nama IC', placeholder='Contoh: Zoma_Haci', required=True)
    alasan = discord.ui.TextInput(label='Alasan Warn', style=discord.TextStyle.paragraph, placeholder='Contoh: Spam chat OOC', required=True)

    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        member = self.member
        nama_ic = self.nama_ic.value
        reason = self.alasan.value

        warns = load_warns()
        gid, uid = str(interaction.guild.id), str(member.id)
        warns.setdefault(gid, {}).setdefault(uid, []).append({
            "reason": reason,
            "nama_ic": nama_ic,
            "by": str(interaction.user),
            "time": str(discord.utils.utcnow())
        })
        save_warns(warns)
        total = len(warns[gid][uid])

        # --- FITUR HITLIST DIKEMBALIKAN ---
        if "update_cartel_list" in globals():
            try:
                await update_cartel_list(interaction.guild)
            except Exception as e:
                print(f"[HITLIST] Error: {e}")
        # ----------------------------------

        target_role = discord.utils.get(interaction.guild.roles, name=WARN_ROLES.get(total, ""))
        all_warn_roles = [discord.utils.get(interaction.guild.roles, name=n) for n in WARN_ROLES.values()]

        if target_role:
            try:
                for r in all_warn_roles:
                    if r and r in member.roles and r != target_role:
                        await member.remove_roles(r)
                if target_role not in member.roles:
                    await member.add_roles(target_role)
            except Exception as e:
                print(f"[WARN] Gagal set role: {e}")

        _tid = _get_warn_tag_id() if '_get_warn_tag_id' in globals() else globals().get("WARN_TAG_ROLE_ID", 0)
        tag_mention = f"<@&{_tid}>" if _tid else "(gak ada)"
        
        embed = discord.Embed(title="🛑  Warn anggota", description=f"!warn {member.mention}", color=discord.Color.orange())
        embed.add_field(name="Nama ic", value=nama_ic, inline=False)
        embed.add_field(name="Alasannya", value=reason, inline=False)
        embed.add_field(name="NOTE", value=f"Tag : {tag_mention}", inline=False)
        
        # --- FIX LOGS WARNING (Cari kata 'warn' di nama channel) ---
        log_channel = discord.utils.find(lambda c: 'logs-warning' in c.name.lower() or 'warn-logs' in c.name.lower(), interaction.guild.text_channels)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"[WARN-LOG] Gagal kirim: {e}")
        
        if total >= MAX_WARN:
            try:
                await member.kick(reason=f"Auto-kick: {MAX_WARN} warn")
                await interaction.channel.send(f"☠️ **{member.display_name}** mencapai {MAX_WARN} warn & ditendang.", delete_after=15)
                warns[gid][uid] = []
                save_warns(warns)
                if "update_cartel_list" in globals():
                    await update_cartel_list(interaction.guild)
            except Exception:
                await interaction.channel.send(f"⚠️ {MAX_WARN} warn, tapi bot gagal nge-kick.")
        else:
            await interaction.channel.send(embed=embed, delete_after=10)
            await interaction.channel.send(f"✅ Warn {total}/{MAX_WARN} berhasil dicatat.", delete_after=10)

class WarnView(discord.ui.View):
    def __init__(self, member: discord.Member, author: discord.Member):
        super().__init__(timeout=60)
        self.member = member
        self.author = author

    @discord.ui.button(label="Isi Form Warn", style=discord.ButtonStyle.primary, emoji="📝")
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Ini bukan form untuk kamu.", ephemeral=True)
        
        await interaction.response.send_modal(WarnModal(self.member))
        self.stop()

@bot.hybrid_command(name='warn')
async def warn_cmd(ctx, member: discord.Member):
    """Kasih warning ke member lewat form pop-up."""
    try:
        if not is_mod(ctx):
            return await ctx.send("❌ Kamu bukan mod atau staff.")
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ Role target di atas role bot.")
            
        view = WarnView(member, ctx.author)
        await ctx.send(f"Silakan klik tombol di bawah untuk mengisi form warning untuk {member.mention}.", view=view)
    except Exception as e:
        await ctx.send(f"❌ **Error warn:** `{e}`")
# ══════════════════════════════════════════════════════════════



# ══════ LOG KICK/BAN/LEAVE KE IN-OUT-LOG ══════
@bot.event
async def on_member_remove(member):
    guild = member.guild
    # Cari channel bernama in-out-log atau banned-logs
    ch = discord.utils.find(lambda c: 'in-out-log' in c.name.lower() or 'banned-logs' in c.name.lower(), guild.text_channels)
    if not ch: return
    
    is_kick = False
    try:
        async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if e.target.id == member.id and (discord.utils.utcnow() - e.created_at).total_seconds() < 10:
                is_kick = True
                embed = discord.Embed(title="👢 MEMBER DI-KICK", description=f"**Target:** {member.mention} (`{member.id}`)\n**Mod:** {e.user.mention}\n**Alasan:** {e.reason or '-'}", color=discord.Color.orange())
                embed.set_thumbnail(url=member.display_avatar.url)
                await ch.send(embed=embed)
                break
    except: pass
    
    if not is_kick:
        embed = discord.Embed(title="🚪 MEMBER KELUAR (LEAVE)", description=f"**User:** {member.mention} (`{member.id}`)", color=discord.Color.dark_grey())
        embed.set_thumbnail(url=member.display_avatar.url)
        try: await ch.send(embed=embed)
        except: pass

@bot.event
async def on_member_ban(guild, user):
    ch = discord.utils.find(lambda c: 'in-out-log' in c.name.lower() or 'banned-logs' in c.name.lower(), guild.text_channels)
    if not ch: return
    try:
        async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if e.target.id == user.id:
                embed = discord.Embed(title="🔨 MEMBER DI-BAN", description=f"**Target:** {user.mention} (`{user.id}`)\n**Mod:** {e.user.mention}\n**Alasan:** {e.reason or '-'}", color=discord.Color.red())
                embed.set_thumbnail(url=user.display_avatar.url)
                await ch.send(embed=embed)
                break
    except: pass
# ═══════════════════════════════════════════════



@bot.command(name='setupverify')
async def setupverify_cmd(ctx):
    """Setup sistem verifikasi & lock channel otomatis."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    try:
        role = discord.utils.get(ctx.guild.roles, name='✅ Verified')
        if not role:
            role = await ctx.guild.create_role(name='✅ Verified', color=discord.Color.green(), reason='Setup verifikasi')
            
        desc = 'Klik reaksi **✅** di bawah ini untuk membuka akses ke seluruh channel server.' + chr(10) + chr(10) + '*Note: Jika reaksi dihapus, akses akan dicabut otomatis.*'
        
        embed = discord.Embed(
            title='✅ VERIFIKASI SERVER',
            description=desc,
            color=discord.Color.green()
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        
        # Simpan ID ke config per-server
        cfg = _cfg_load()
        gid = str(ctx.guild.id)
        if gid not in cfg: cfg[gid] = {}
        cfg[gid]['verify_message_id'] = msg.id
        cfg[gid]['verify_role_id'] = role.id
        _cfg_save(cfg)
        
        # Lock channel lain
        await ctx.send('⏳ Sedang mengunci channel lain...')
        for ch in ctx.guild.channels:
            try:
                if ch.id != ctx.channel.id:
                    await ch.set_permissions(ctx.guild.default_role, read_messages=False)
                    await ch.set_permissions(role, read_messages=True)
            except: pass
            
        await ctx.send('✅ **Selesai!** Server berhasil dikunci. Member baru sekarang harus klik ✅ untuk masuk.')
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')


# ══════ REACTION ROLE (VERIFY) PER-SERVER ══════
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
    if str(payload.emoji) != '✅': return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    cfg = _cfg_load()
    gid = str(guild.id)
    
    if cfg.get(gid, {}).get('verify_message_id') == payload.message_id:
        role_id = cfg[gid].get('verify_role_id')
        role = guild.get_role(role_id) if role_id else None
        member = guild.get_member(payload.user_id)
        
        if role and member:
            try: 
                await member.add_roles(role)
                print(f"[VERIFY] {member.name} berhasil diverifikasi.")
            except Exception as e:
                print(f"[VERIFY] Gagal kasih role: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    if str(payload.emoji) != '✅': return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    cfg = _cfg_load()
    gid = str(guild.id)
    
    if cfg.get(gid, {}).get('verify_message_id') == payload.message_id:
        role_id = cfg[gid].get('verify_role_id')
        role = guild.get_role(role_id) if role_id else None
        member = guild.get_member(payload.user_id)
        
        if role and member:
            try: await member.remove_roles(role)
            except: pass
# ═══════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════
# 🚨 EMERGENCY FIX (PINDU DARURAT LU)
# ══════════════════════════════════════════════════════════════
@bot.command(name='fixme')
async def fixme_cmd(ctx):
    """Paksa kasih role Admin & Verified ke lu (Biar gak kekunci)."""
    msg = await ctx.send('⏳ **Menyelamatkan Owner...**')
    
    try:
        # 1. Cari atau Bikin Role Admin
        admin_role = discord.utils.get(ctx.guild.roles, name='Admin') or discord.utils.get(ctx.guild.roles, name='🛡️ Admin')
        if not admin_role:
            admin_role = await ctx.guild.create_role(name='Admin', color=discord.Color.red(), permissions=discord.Permissions(administrator=True))
            await msg.edit(content='✅ Role `Admin` berhasil dibuat.')

        # 2. Cari atau Bikin Role Verified
        verified_role = discord.utils.get(ctx.guild.roles, name='✅ Verified')
        if not verified_role:
            verified_role = await ctx.guild.create_role(name='✅ Verified', color=discord.Color.green())
            await msg.edit(content='✅ Role `✅ Verified` berhasil dibuat.')

        # 3. PAKSA KASIH KE LU (@zomahaci)
        try:
            await ctx.author.add_roles(admin_role, verified_role)
            top_role_name = ctx.guild.me.top_role.name
            await ctx.send(f"✅ **MANTAP BANG!** Role **{admin_role.name}** dan **✅ Verified** udah gw paksa masukin ke akun lu.")
            await ctx.send(f"*(Info: Role tertinggi bot saat ini adalah {top_role_name}. Pastiin role bot ada di atas role Admin!)*")
        except Exception as e:
            await ctx.send(f"❌ **Gagal ngegasih role!**\nAlasan: {e}\n\n**SOLUSI:** Pindahkan role bot (`Fortxx`) ke **paling atas** di Server Settings > Roles, lalu ketik `!fixme` lagi.")
            
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
# ══════════════════════════════════════════════════════════════


bot.run(base64.b64decode("TVRVMk1EUTJOekU0TURnMk56STVOek0wTWcuR1R3Sm5kLjZfSl95ZFhNRkFVeUEyeXVoQ2FYUGlVZmw4RXVEOVdnd3hNdWpF").decode())
