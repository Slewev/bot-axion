import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

# ================= INTENTS =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= STOCKAGE =================
staff_roles = {}
logs_channels = {}

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Connecté : {bot.user}")

# 🔥 SYNC ULTRA FIABLE
@bot.event
async def setup_hook():
    try:
        synced = await bot.tree.sync()
        print(f"🌍 {len(synced)} commandes synchronisées")
        print("COMMANDES :", [c.name for c in bot.tree.get_commands()])
    except Exception as e:
        print("SYNC ERROR :", e)

# ================= UTIL =================
def is_staff(member: discord.Member):
    role_id = staff_roles.get(str(member.guild.id))
    if not role_id:
        return False
    return any(r.id == role_id for r in member.roles)

async def send_log(guild, text):
    channel_id = logs_channels.get(str(guild.id))
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(f"📌 {text}")

# ======================================================
# ⚙️ SETSTAFF
# ======================================================
@bot.tree.command(name="setstaff")
async def setstaff(interaction: discord.Interaction, role: discord.Role):
    staff_roles[str(interaction.guild.id)] = role.id
    await interaction.response.send_message("✅ Staff défini", ephemeral=True)

# ======================================================
# 📡 SETLOGS
# ======================================================
@bot.tree.command(name="setlogs")
async def setlogs(interaction: discord.Interaction, channel: discord.TextChannel):
    logs_channels[str(interaction.guild.id)] = channel.id
    await interaction.response.send_message("📡 Logs définis", ephemeral=True)

# ======================================================
# 🔨 BAN
# ======================================================
@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member} banni", ephemeral=True)
    await send_log(interaction.guild, f"BAN {member} | {reason}")

# ======================================================
# ♻️ UNBAN
# ======================================================
@bot.tree.command(name="unban")
async def unban(interaction: discord.Interaction, user_id: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"♻️ Unban {user}", ephemeral=True)
    await send_log(interaction.guild, f"UNBAN {user}")

# ======================================================
# 👢 KICK
# ======================================================
@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member} kick", ephemeral=True)
    await send_log(interaction.guild, f"KICK {member} | {reason}")

# ======================================================
# 🔇 MUTE
# ======================================================
@bot.tree.command(name="mute")
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes))
    await interaction.response.send_message(f"🔇 {member} mute {minutes}min", ephemeral=True)
    await send_log(interaction.guild, f"MUTE {member} {minutes}min")

# ======================================================
# 🔊 UNMUTE
# ======================================================
@bot.tree.command(name="unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    await member.timeout(None)
    await interaction.response.send_message(f"🔊 {member} unmute", ephemeral=True)
    await send_log(interaction.guild, f"UNMUTE {member}")

# ======================================================
# ⚠️ WARN
# ======================================================
warns = {}

@bot.tree.command(name="warn")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    warns.setdefault(str(member.id), []).append(reason)
    await interaction.response.send_message(f"⚠️ Warn {member}", ephemeral=True)

# ======================================================
# ♻️ UNWARN
# ======================================================
@bot.tree.command(name="unwarn")
async def unwarn(interaction: discord.Interaction, member: discord.Member):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    warns[str(member.id)] = []
    await interaction.response.send_message(f"♻️ Warn reset {member}", ephemeral=True)

# ======================================================
# 🎛 PANEL ADMIN
# ======================================================
class Panel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger)
    async def ban_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Utilise /ban", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary)
    async def kick_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Utilise /kick", ephemeral=True)

    @discord.ui.button(label="Warn", style=discord.ButtonStyle.primary)
    async def warn_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Utilise /warn", ephemeral=True)

@bot.tree.command(name="panel")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message("🛠 Panel Admin", view=Panel(), ephemeral=True)

# ================= RUN =================
bot.run(TOKEN)