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

bot = commands.Bot(command_prefix='!', intents=intents)



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



@bot.event
async def on_member_remove(member):
    if member.bot:
        return
    channel = discord.utils.find(lambda c: WELCOME_KEYWORD in c.name.lower(), member.guild.channels)
    if channel is None:
        return
    embed = discord.Embed(
        title=f"🩸 OTRO CAÍDO...",
        description=(
            f"**{member.display_name}** telah meninggalkan familia.\n\n"
            f"🥀 Kursi di meja keluarga kini kosong.\n"
            f"Jalan yang kau pilih adalah jalan keluar dari ikatan darah.\n\n"
            f"**Que Dios te acompañe.**\n"
            f"*Adiós... o hasta nunca.*"
        ),
        color=discord.Color.from_rgb(60, 0, 0)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"☠️ Miembro sisa: {member.guild.member_count} | CJNG")
    await channel.send(embed=embed)

# ══════════════════════════════════════════════════
# SETUP ROLE WARN (OTOMATIS)
# ══════════════════════════════════════════════════
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
@bot.command()
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

@bot.command()
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

class WarnModal(discord.ui.Modal, title='Form Warning Anggota'):
    nama_ic = discord.ui.TextInput(
        label='Nama IC',
        placeholder='Contoh: Zoma_Haci',
        required=True
    )
    alasan = discord.ui.TextInput(
        label='Alasan Warn',
        style=discord.TextStyle.paragraph,
        placeholder='Contoh: Spam chat OOC',
        required=True
    )
    note = discord.ui.TextInput(
        label='Note Tambahan',
        style=discord.TextStyle.short,
        placeholder='Contoh: Warn pertama / Opsional',
        required=False
    )

    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        member = self.member
        nama_ic = self.nama_ic.value
        reason = self.alasan.value
        note_val = self.note.value or '-'

        warns = load_warns()
        gid, uid = str(interaction.guild.id), str(member.id)
        warns.setdefault(gid, {}).setdefault(uid, []).append({
            "reason": reason,
            "nama_ic": nama_ic,
            "note": note_val,
            "by": str(interaction.user),
            "time": str(discord.utils.utcnow())
        })
        save_warns(warns)
        total = len(warns[gid][uid])

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
        tag_mention = f"<@&{_tid}>" if _tid else ""
        
        # Tentukan warna dan status berdasarkan total warn
        if total >= MAX_WARN:
            warna = discord.Color.red()
            status = "🚨 BATAS MAKSIMAL (AUTO-KICK)"
        elif total == MAX_WARN - 1:
            warna = discord.Color.dark_orange()
            status = "⚠️ PERINGATAN KERAS"
        else:
            warna = discord.Color.orange()
            status = "🔔 PERINGATAN"

        embed = discord.Embed(
            title=f"🛑  Warning System: {status}",
            description=f"**{member.mention}** telah menerima peringatan dari staff.",
            color=warna
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📛 Nama IC", value=f"`{nama_ic}`", inline=True)
        embed.add_field(name="📊 Total Warn", value=f"**{total} / {MAX_WARN}**", inline=True)
        embed.add_field(name="👮 Oleh", value=interaction.user.mention, inline=True)
        embed.add_field(name="📝 Alasan", value=f"> {reason}", inline=False)
        embed.add_field(name="📝 Note", value=f"> {note_val}", inline=False)
        
        footer_text = f"Target ID: {member.id}"
        if tag_mention:
             footer_text += f" | Tag: {tag_mention}"
        embed.set_footer(text=footer_text)
        embed.timestamp = discord.utils.utcnow()
        
        log_name = _get_warn_log_name() if '_get_warn_log_name' in globals() else "logs-warning"
        log_channel = discord.utils.get(interaction.guild.channels, name=log_name)
        if log_channel:
            try:
                await log_channel.send(content=tag_mention, embed=embed)
            except Exception:
                pass
            except Exception:
                pass
        
        if total >= MAX_WARN:
            try:
                await member.kick(reason=f"Auto-kick: {MAX_WARN} warn")
                await interaction.channel.send(f"☠️ **{member.display_name}** mencapai {MAX_WARN} warn & ditendang.")
                warns[gid][uid] = []
                save_warns(warns)
            except Exception:
                await interaction.channel.send(f"⚠️ {MAX_WARN} warn, tapi bot gagal nge-kick.")
        else:
            await interaction.channel.send(embed=embed)
            await interaction.channel.send(f"✅ Warn {total}/{MAX_WARN} berhasil dicatat.")

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

@bot.command()
async def warn(ctx, member: discord.Member):
    """Kasih warning ke member lewat form pop-up."""
    if not is_mod(ctx) or member.top_role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Kamu bukan mod ATAU role target di atas role bot.")

    view = WarnView(member, ctx.author)
    await ctx.send(f"Silakan klik tombol di bawah untuk mengisi form warning untuk {member.mention}.", view=view)

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
    print(f'✅ Bot {bot.user} udah online!')

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

@bot.command(name="ping")
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

@bot.command(name="avatar", aliases=["av"])
async def avatar_cmd(ctx, member: discord.Member = None):
    """Tampilkan avatar user (default: kamu)."""
    member = member or ctx.author
    e = discord.Embed(title=f"🖼️ Avatar {member.display_name}", color=discord.Color.blurple())
    e.set_image(url=member.display_avatar.url)
    e.add_field(name="📥 Download", value=f"[PNG]({member.display_avatar.replace(format='png', size=1024).url}) • [JPG]({member.display_avatar.replace(format='jpg', size=1024).url})")
    await ctx.send(embed=e)

@bot.command(name="userinfo", aliases=["ui", "whois"])
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

@bot.command(name="serverinfo", aliases=["si"])
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

@bot.command(name="timeout", aliases=["to"])
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

@bot.command(name="say")
async def say_cmd(ctx, *, text: str):
    """Bot bilang sesuatu. Contoh: !say Halo semua!"""
    if not is_mod(ctx):
        return await ctx.send("❌ Gak punya izin.")
    try:
        await ctx.message.delete()
    except Exception:
        pass
    await ctx.send(text)

@bot.command(name="embed")
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

@bot.command(name="poll")
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
        "🎫 Ticket & RP": (
            "ticket", "char", "setupchar", "setupwelcome"
        ),
        "🎭 Role & Channel": (
            "role", "addrole", "removerole", "createrole", "deleterole",
            "massrole", "autorole", "rolepos", "rolesync", "roleclone",
            "roleinfo", "listroles", "roleedit", "roleperm",
            "createchannel", "deletechannel", "renamechannel",
            "createcategory", "topic", "listchannels", "channelinfo"
        ),
        "🔥 Logs": (
            "setbotlog", "setwarnlog", "setwarntag", "loginfo"
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
    # Inisialisasi semua key
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
    def __init__(self, ctx, categories, prefix):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.categories = categories
        self.prefix = prefix
        self.page = 0
        self.cat_names = list(categories.keys())
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page >= len(self.cat_names) - 1

    def _build_embed(self):
        cat = self.cat_names[self.page]
        cmds = sorted(self.categories[cat], key=lambda x: x.name)
        total = sum(len(v) for v in self.categories.values())
        e = discord.Embed(
            title="📚 DAFTAR COMMAND",
            description=(f"Prefix: **`{self.prefix}`** • Total: **{total}** command\n"
                         f"Halaman **{self.page+1}/{len(self.cat_names)}** — {cat}"),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        # Bangun semua baris per command
        lines = []
        for cmd in cmds:
            short = (cmd.help or "").split("\n")[0] or "(tanpa deskripsi)"
            if len(short) > 80:
                short = short[:77] + "..."
            lines.append(f"`{self.prefix}{cmd.name}` • {short}")

        # Split ke chunk <=1000 karakter
        LIMIT = 1000
        chunks = []
        buf = ""
        for line in lines:
            if len(buf) + len(line) + 1 > LIMIT:
                chunks.append(buf.rstrip())
                buf = ""
            buf += line + "\n"
        if buf.strip():
            chunks.append(buf.rstrip())

        if not chunks:
            e.add_field(name=cat, value="*(kosong)*", inline=False)
        else:
            for i, chunk in enumerate(chunks, 1):
                name = cat if i == 1 else f"{cat} (lanjutan {i-1})"
                e.add_field(name=name, value=chunk, inline=False)

        e.set_footer(text=f"{self.ctx.author.display_name} • {self.prefix}help <command> untuk detail",
                     icon_url=self.ctx.author.display_avatar.url)
        e.timestamp = discord.utils.utcnow()
        return e

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Ini bukan help kamu.", ephemeral=True)
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Ini bukan help kamu.", ephemeral=True)
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="🔍 Cari", style=discord.ButtonStyle.success)
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Bukan help kamu.", ephemeral=True)
        await interaction.response.send_message("🔍 Ketik nama command (contoh: `warn`):", ephemeral=True)
        try:
            msg = await bot.wait_for("message", timeout=30,
                check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel)
            cmd = bot.get_command(msg.content.strip())
            if cmd:
                e = discord.Embed(title=f"📖 {self.prefix}{cmd.name}",
                                  description=cmd.help or "*(tanpa deskripsi)*",
                                  color=discord.Color.green())
                e.add_field(name="📝 Penggunaan",
                            value=f"```{self.prefix}{cmd.name} {cmd.signature}```", inline=False)
                if cmd.aliases:
                    e.add_field(name="🔀 Alias",
                                value=", ".join(f"`{a}`" for a in cmd.aliases), inline=False)
                await self.ctx.send(embed=e)
            else:
                await self.ctx.send(f"❌ Command `{msg.content}` gak ketemu.")
        except asyncio.TimeoutError:
            await self.ctx.send("⏰ Timeout.")

    @discord.ui.button(label="❌ Tutup", style=discord.ButtonStyle.danger)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Bukan help kamu.", ephemeral=True)
        await interaction.message.delete()


@bot.command(name="help", aliases=["h", "bantuan"])
async def help_cmd(ctx, *, command: str = None):
    """Tampilkan daftar command (interaktif) atau detail command tertentu."""
    P = ctx.prefix

    if command:
        cmd = bot.get_command(command)
        if not cmd or cmd.hidden:
            return await ctx.send(f"❌ Command `{command}` gak ada. Coba `{P}help`")
        e = discord.Embed(title=f"📖 {P}{cmd.name}",
                          description=cmd.help or "*(tanpa deskripsi)*",
                          color=discord.Color.blurple())
        e.add_field(name="📝 Penggunaan", value=f"```{P}{cmd.name} {cmd.signature}```"[:1020], inline=False)
        if cmd.aliases:
            e.add_field(name="🔀 Alias", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=True)
        e.set_footer(text=f"Ketik {P}help untuk daftar semua command")
        return await ctx.send(embed=e)

    cats = _build_categories()
    view = HelpMainView(ctx, cats, P)
    await ctx.send(embed=view._build_embed(), view=view)
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
    name = _get_bot_log_name()
    ch = discord.utils.get(guild.text_channels, name=name)
    if ch:
        return ch
    for c in guild.text_channels:
        n = c.name.lower()
        if "bot-run" in n or "botrun" in n or "bot_run" in n:
            return c
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
async def on_member_ban(guild, user):
    try:
        async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if e.target.id == user.id:
                await bot_log(guild, "🔨 BAN",
                    f"**Target:** {user.mention} (`{user.id}`)\n"
                    f"**Mod:** {e.user.mention} (`{e.user.id}`)\n"
                    f"**Alasan:** {e.reason or '-'}",
                    discord.Color.dark_red())
                return
    except Exception:
        pass

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
async def on_member_remove(member):
    g = member.guild
    try:
        async for e in g.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if e.target.id == member.id and (discord.utils.utcnow() - e.created_at).total_seconds() < 10:
                return
    except Exception:
        pass
    try:
        async for e in g.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if e.target.id == member.id and (discord.utils.utcnow() - e.created_at).total_seconds() < 10:
                await bot_log(g, "👢 KICK",
                    f"**Target:** {member} (`{member.id}`)\n"
                    f"**Mod:** {e.user.mention} (`{e.user.id}`)\n"
                    f"**Alasan:** {e.reason or '-'}",
                    discord.Color.orange())
                return
    except Exception:
        pass
    await bot_log(g, "🚪 LEAVE", f"**{member}** (`{member.id}`) keluar server", discord.Color.greyple())

@bot.event
async def on_member_update(before, after):
    g = after.guild
    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            await bot_log(g, "⏳ TIMEOUT",
                f"**Target:** {after.mention} (`{after.id}`)\n"
                f"**Sampai:** {discord.utils.format_dt(after.timed_out_until, 'R')}",
                discord.Color.orange())
        else:
            await bot_log(g, "🔓 TIMEOUT CABUT",
                f"**Target:** {after.mention} (`{after.id}`)",
                discord.Color.green())
    added = set(after.roles) - set(before.roles)
    removed = set(before.roles) - set(after.roles)
    if not (added or removed):
        return
    WARN_NAMES = {"Warned 1", "Warned 2", "Warned 3"}
    if added and removed and all(r.name in WARN_NAMES for r in added) and all(r.name in WARN_NAMES for r in removed):
        return
    parts = [f"**Target:** {after.mention} (`{after.id}`)"]
    if added:
        parts.append("➕ " + " ".join(r.mention for r in added))
    if removed:
        parts.append("➖ " + " ".join(r.mention for r in removed))
    await bot_log(g, "🎭 ROLE UPDATE", "\n".join(parts), discord.Color.blurple())

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

keep_alive()  # mulai HTTP server untuk Render

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

@bot.command(name='ticket')
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
        await ctx.send(embed=embed, view=TicketView())
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
    """Kirim panel pembuatan karakter RP di channel ini."""
    if not is_mod(ctx): 
        return await ctx.send('❌ Mod only.')
    
    try:
        category = discord.utils.get(ctx.guild.categories, name='TAKE ROLE')
        if not category:
            category = await ctx.guild.create_category('TAKE ROLE')
            
        channel_name = '📜┃take-role-name-ic'
        channel = discord.utils.find(lambda c: 'take-role-name-ic' in c.name.lower(), ctx.guild.text_channels)
        
        if not channel:
            channel = await ctx.guild.create_text_channel(channel_name, category=category, position=0)
            await ctx.send(f"✅ Channel {channel.mention} berhasil dibuat di kategori TAKE ROLE!")
            
        # Bikin channel daftar-karakter kalau belum ada
        char_list_ch = discord.utils.find(lambda c: 'daftar-karakter' in c.name.lower(), ctx.guild.text_channels)
        if not char_list_ch:
            char_list_ch = await ctx.guild.create_text_channel('📜┃daftar-karakter', category=category, position=1)
            await ctx.send(f"✅ Channel {char_list_ch.mention} berhasil dibuat untuk menampung kartu karakter!")
        else:
            await channel.edit(category=category, position=0)
            await ctx.send(f"✅ Channel {channel.mention} berhasil dipindahkan ke paling atas kategori TAKE ROLE!")
            
        embed = discord.Embed(
            title="📜 Pembuatan Karakter RP",
            description="Silakan klik tombol **Buat Karakter** di bawah ini untuk mengisi form profil karakter Anda." + chr(10) + chr(10) + "*(Pastikan Anda mengisi data dengan benar karena Nickname server akan otomatis berubah sesuai Nama IC).*",
            color=discord.Color.blurple()
        )
        
        await channel.send(embed=embed, view=CharView())
        
    except Exception as e:
        await ctx.send(f"❌ **Error Detail:** `{e}`")

# ══════════════════════════════════════════════════════════════
# 👋 WELCOME MESSAGE (CÁRTEL DE JALISCO)
# ══════════════════════════════════════════════════════════════
@bot.listen('on_member_join')
async def welcome_event_cartel(member):
    ch = discord.utils.find(lambda c: 'welcome' in c.name.lower(), member.guild.text_channels)
    if ch:
        take_role_ch = discord.utils.find(lambda c: 'take-role-name-ic' in c.name.lower(), member.guild.text_channels)
        take_role_mention = take_role_ch.mention if take_role_ch else '`#📜┃take-role-name-ic`'
        
        welcome_text = (
            'Kamu baru saja menginjakkan kaki di wilayah **Cártel de Jalisco Nueva Generación.**' + chr(10) + chr(10) +
            '⚔️ **PROTOKOL KARTEL:**' + chr(10) +
            '1️⃣ Hormati **El Jefe** & **La Jefa** tanpa terkecuali.' + chr(10) +
            '2️⃣ Jaga rahasia *plaza*. Jangan pernah khianati keluarga.' + chr(10) +
            f'3️⃣ Ambil identitasmu di {take_role_mention}.' + chr(10) +
            '4️⃣ **Wajib pakai nama IC (In Character) di dalam server.**' + chr(10) + chr(10) +
            '☕ Meja sudah disiapkan. Kopi sudah dituang.' + chr(10) +
            'Mulai sekarang, darahmu adalah darah kami.' + chr(10) +
            '**Bienvenido a la familia.**'
        )
        
        embed = discord.Embed(
            title=f'🩸 BIENVENIDO, {member.name.upper()}!',
            description=welcome_text,
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await ch.send(content=member.mention, embed=embed)
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🩸 GOODBYE MESSAGE (CÁRTEL DE JALISCO)
# ══════════════════════════════════════════════════════════════
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
@bot.command(name='setupverify')
async def setupverify_cmd(ctx):
    """Setup sistem verifikasi & lock channel otomatis."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    try:
        # 1. Bikin Role Verified
        role = discord.utils.get(ctx.guild.roles, name='WARGA CJNG')
        if not role:
            role = await ctx.guild.create_role(name='WARGA CJNG', color=discord.Color.dark_red(), reason='Setup verifikasi CJNG')
            
        # 2. Kirim pesan reaksi
        embed = discord.Embed(
            title='🩸 VERIFIKASI CÁRTEL DE JALISCO',
            description='Klik reaksi **✅** di bawah ini untuk membuka akses ke seluruh channel server.' + chr(10) + chr(10) + '*Note: Jika reaksi dihapus, akses akan dicabut otomatis.*',
            color=discord.Color.green()
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        
        # 3. Simpan ID ke config
        cfg = _cfg_load()
        cfg['verify_message_id'] = msg.id
        cfg['verify_role_id'] = role.id
        _cfg_save(cfg)
        
        # 4. Lock semua channel kecuali channel ini
        await ctx.send('⏳ Sedang mengunci channel lain...')
        for ch in ctx.guild.channels:
            try:
                if ch.id != ctx.channel.id:
                    await ch.set_permissions(ctx.guild.default_role, read_messages=False)
                    await ch.set_permissions(role, read_messages=True)
            except: pass
        
        await ctx.send('✅ **Selesai!** Server berhasil dikunci. Member baru sekarang harus klik ✅ untuk masuk.' + chr(10) + '⚠️ **PENTING:** Pindahkan Role `WARGA CJNG` ke atas role member lain agar sistem berjalan sempurna.')
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
    cfg = _cfg_load()
    if cfg.get('verify_message_id') == payload.message_id and str(payload.emoji) == '✅':
        guild = bot.get_guild(payload.guild_id)
        if not guild: return
        role = guild.get_role(int(cfg.get('verify_role_id', 0)))
        member = guild.get_member(payload.user_id)
        
        if role and member:
            try: 
                await member.add_roles(role)
                
                # --- BIKIN CHANNEL AI PRIVAT OTOMATIS ---
                has_ch = False
                for ch in guild.text_channels:
                    if ch.topic and f'AI_CHANNEL_OWNER:{member.id}' in ch.topic:
                        has_ch = True
                        break
                
                if not has_ch:
                    category = discord.utils.find(lambda c: c.name.upper() == 'PUBLIC ROOM', guild.categories)
                    if not category:
                        category = await guild.create_category('SETTINGS')
                        
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
                        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
                    }
                    staff_roles = ["Staff", "Moderator", "Admin", "Owner", "Mod", "⚠️HANDLE CJNG", "OWNER X CO OWNER"]
                    for role_name in staff_roles:
                        r = discord.utils.get(guild.roles, name=role_name)
                        if r:
                            overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                            
                    ai_ch = await guild.create_text_channel(
                        name=f'🤖┃ai-{member.name}',
                        category=category,
                        overwrites=overwrites,
                        topic=f'AI_CHANNEL_OWNER:{member.id} | Channel AI pribadi milik {member.name}.'
                    )
                    
                    embed = discord.Embed(
                        title='🤖 AI Asisten Pribadi',
                        description=f'Halo {member.mention}! Ini channel AI pribadimu. Ketik apa aja di sini **tanpa command** buat ngobrol sama AI.',
                        color=discord.Color.green()
                    )
                    await ai_ch.send(content=member.mention, embed=embed)
                    
            except Exception as e:
                print(f"Error di reaction add: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    cfg = _cfg_load()
    if cfg.get('verify_message_id') == payload.message_id and str(payload.emoji) == '✅':
        guild = bot.get_guild(payload.guild_id)
        if not guild: return
        role = guild.get_role(int(cfg.get('verify_role_id', 0)))
        member = guild.get_member(payload.user_id)
        if role and member:
            try: await member.remove_roles(role)
            except: pass
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🔄 PERSISTENT VIEWS (BIAR TOMBOL GAK MATI PAS RESTART)
# ══════════════════════════════════════════════════════════════
try:
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView())
    bot.add_view(CharView())
    print('[SYSTEM] Persistent views berhasil dimuat!')
except Exception as e:
    print(f'[SYSTEM] Gagal muat persistent views: {e}')
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 🤖 AI DENGAN AION LABS (ROLEPLAY & CHAT)
# ══════════════════════════════════════════════════════════════
import aiohttp

AION_API_KEY = base64.b64decode("YWx2Ml9kd19PMldlblN2UEtlOGMtLW1tREtfZjE4di16WVNwLXhIMU1wUG1WLWRr").decode()
AION_BASE_URL = 'https://api.aionlabs.ai/v1'

async def tanya_aion(prompt: str, system_prompt: str = None, model: str = 'aion-labs/aion-2.0'):
    if not AION_API_KEY:
        return '❌ API Key Aion Labs belum diset di Environment Variables (AION_API_KEY).'
    
    headers = {
        'Authorization': f'Bearer {AION_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})
    
    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{AION_BASE_URL}/chat/completions', headers=headers, json=payload) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    return f'❌ Error API Aion: HTTP {resp.status} - {err_text[:100]}'
                data = await resp.json()
                return data['choices'][0]['message']['content']
    except Exception as e:
        return f'❌ Gagal konek ke Aion: {e}'

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
    """Rapihin nama channel & kategori biar bersih."""
    if not is_mod(ctx): return await ctx.send('❌ Mod only.')
    
    msg = await ctx.send('🧹 **Membersihkan nama channel...** Tunggu sebentar ya.')
    
    # Nama Kategori Baru (Pendek, Bersih, Gak Ada Warna)
    cat_map = {
        'PUBLIC ROOM': '📁 〢 PUBLIC ROOM',
        'CJNG RULES': '📁 〢 CJNG RULES',
        'REPORT ROOM': '📁 〢 REPORT ROOM',
        'BLACK MARKET': '📁 〢 BLACK MARKET',
        'TAKE ROLE': '📁 〢 TAKE ROLE',
        'SETTINGS': '⚙️ 〢 SETTINGS',
        'PATNER': '📁 〢 PARTNER',
        'OFFICIAL LINK': '📁 〢 OFFICIAL LINK',
        'ANNOUNCEMENT': '📁 〢 ANNOUNCEMENT',
        'BOT RUN': '📁 〢 BOT RUN',
        'REQ AREA': '📁 〢 REQ AREA'
    }
    
    # Rename Kategori
    for cat in ctx.guild.categories:
        for key, new_name in cat_map.items():
            if key in cat.name.upper():
                try:
                    await cat.edit(name=new_name)
                    await asyncio.sleep(1.5)
                except: pass
                break
            
    # Mapping Channel (Bersih tanpa sisa - || -)
    ch_map = {
        'publik': '💬・publik-chat',
        'chat • bot': '🤖・chat-bot',
        'share': '🎬・share-content',
        'ask-room': '💋・ask-room',
        'take-role-name-ic': '📜・take-role-ic',
        'daftar-karakter': '📜・daftar-karakter',
        'take • role': '👤・take-role',
        'welcome': '👋・welcome',
        'bot-run': '🔥・bot-run',
        'report • anggota': '🩸・report-anggota',
        'logs-warning': '🩸・logs-warning',
        'ticket': '🎫・ticket',
        'announcement': '📢・announcement',
        'official-link': '🔗・official-link',
        'informasi': '💊・informasi-dark',
        'beli': '🛒・beli-barang',
        'rules-dark': '📕・rules-dark',
        'req-company': '💼・req-company',
        'req-approach': '👥・req-approach',
        'req-in-out': '🔐・req-in-out',
        'ai-': '🤖・ai-asisten'
    }
    
    # Rename Channel
    for ch in ctx.guild.text_channels:
        ch_name_lower = ch.name.lower()
        for key, new_name in ch_map.items():
            if key in ch_name_lower:
                try:
                    await ch.edit(name=new_name)
                    await asyncio.sleep(1.5)
                except: pass
                break
                
    await msg.edit(content='✅ **Beres Bang!** Semua nama kategori dan channel udah dirapikan.' + chr(10) + 'Sekarang pendek, bersih, dan gak bakal kepotong di HP.')

# ══════════════════════════════════════════════════════════════

bot.run(base64.b64decode("TVRVMk1EUTJOekU0TURnMk56STVOek0wTWcuR1R3Sm5kLjZfSl95ZFhNRkFVeUEyeXVoQ2FYUGlVZmw4RXVEOVdnd3hNdWpF").decode())
