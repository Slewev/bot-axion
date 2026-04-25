import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import asyncio
import datetime

# ================= CONFIG =================
load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

staff_roles = {}
logs_channels = {}
warns = {}

# ================= READY =================
@bot.event
async def setup_hook():
    synced = await bot.tree.sync()
    print(f"🌍 {len(synced)} commandes synchronisées")

@bot.event
async def on_ready():
    print(f"✅ Connecté : {bot.user}")

# ================= UTILS =================
def is_staff(member):
    role_id = staff_roles.get(str(member.guild.id))
    return role_id and any(r.id == role_id for r in member.roles)

async def send_log(guild, msg):
    channel_id = logs_channels.get(str(guild.id))
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(msg)

async def delete_category_if_empty(category):
    await asyncio.sleep(2)
    if category and len(category.channels) == 0:
        await category.delete()

# ================= ADMIN =================
@bot.tree.command(name="setstaff")
async def setstaff(interaction: discord.Interaction, role: discord.Role):
    staff_roles[str(interaction.guild.id)] = role.id
    await interaction.response.send_message("✅ Staff défini", ephemeral=True)

@bot.tree.command(name="setlogs")
async def setlogs(interaction: discord.Interaction, channel: discord.TextChannel):
    logs_channels[str(interaction.guild.id)] = channel.id
    await interaction.response.send_message("📡 Logs définis", ephemeral=True)

# ================= MODERATION =================
@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member} banni")
    await send_log(interaction.guild, f"BAN {member} | {reason}")

@bot.tree.command(name="unban")
async def unban(interaction: discord.Interaction, user_id: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)
    user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"♻️ Unban {user}")
    await send_log(interaction.guild, f"UNBAN {user}")

@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member} kick")
    await send_log(interaction.guild, f"KICK {member} | {reason}")

@bot.tree.command(name="mute")
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
    await member.timeout(until)

    await interaction.response.send_message(f"🔇 {member} mute {minutes} min")
    await send_log(interaction.guild, f"MUTE {member} {minutes}min")

@bot.tree.command(name="unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    await member.timeout(None)
    await interaction.response.send_message(f"🔊 {member} unmute")
    await send_log(interaction.guild, f"UNMUTE {member}")

@bot.tree.command(name="warn")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    warns.setdefault(str(member.id), []).append(reason)
    await interaction.response.send_message(f"⚠️ Warn ajouté")
    await send_log(interaction.guild, f"WARN {member} | {reason}")

@bot.tree.command(name="unwarn")
async def unwarn(interaction: discord.Interaction, member: discord.Member):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

    warns[str(member.id)] = []
    await interaction.response.send_message(f"♻️ Warn reset")
    await send_log(interaction.guild, f"UNWARN {member}")

# ================= TRANSCRIPT =================
async def create_transcript(channel):
    messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]

    filename = f"transcript-{channel.id}.pdf"
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph(f"Transcript - {channel.name}", styles["Title"]))
    content.append(Spacer(1, 12))

    for msg in messages:
        content.append(Paragraph(f"{msg.author}: {msg.content}", styles["Normal"]))
        content.append(Spacer(1, 6))

    doc.build(content)
    return filename

# ================= TICKETS =================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Question / Aide", emoji="❓"),
            discord.SelectOption(label="Report", emoji="🚨"),
            discord.SelectOption(label="Partenariat", emoji="🤝"),
            discord.SelectOption(label="Autre", emoji="📝"),
        ]
        super().__init__(placeholder="📩 Choisis une raison", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        choice = self.values[0]
        guild = interaction.guild

        category = discord.utils.get(guild.categories, name=choice)
        if not category:
            category = await guild.create_category(choice)

        role_id = staff_roles.get(str(guild.id))
        staff_role = guild.get_role(role_id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        await channel.send(
            f"{interaction.user.mention}",
            view=TicketButtons(interaction.user)
        )

        await interaction.followup.send("✅ Ticket créé", ephemeral=True)

# ================= BOUTONS =================
class TicketButtons(discord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=None)
        self.owner = owner

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Staff uniquement", ephemeral=True)

        role_id = staff_roles.get(str(interaction.guild.id))
        staff_role = interaction.guild.get_role(role_id)

        for member in interaction.guild.members:
            if staff_role in member.roles and member != interaction.user:
                await interaction.channel.set_permissions(member, view_channel=False)

        await interaction.channel.send(f"📌 Claim par {interaction.user.mention}")
        await interaction.response.send_message("✅ Claim", ephemeral=True)

    @discord.ui.button(label="Add", style=discord.ButtonStyle.secondary)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("🆔 ID ?", ephemeral=True)

        def check(m): return m.author == interaction.user
        msg = await bot.wait_for("message", check=check)

        member = await interaction.guild.fetch_member(int(msg.content))
        await interaction.channel.set_permissions(member, view_channel=True)

        await interaction.channel.send(f"➕ {member.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("📝 Raison ?", ephemeral=True)

        def check(m): return m.author == interaction.user
        msg = await bot.wait_for("message", check=check)

        reason = msg.content
        category = interaction.channel.category

        file_path = await create_transcript(interaction.channel)

        try:
            await self.owner.send(f"🔒 Fermé : {reason}")
            await self.owner.send(file=discord.File(file_path))
        except:
            pass

        await send_log(interaction.guild, f"Ticket fermé | {reason}")

        await interaction.channel.delete()
        await delete_category_if_empty(category)

# ================= PANELS =================
class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.tree.command(name="ticketpanel")
async def ticketpanel(interaction: discord.Interaction):
    await interaction.response.send_message("🎫 Ouvre un ticket :", view=TicketPanel())

class AdminPanel(discord.ui.View):
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger)
    async def ban_btn(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("Utilise /ban", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary)
    async def kick_btn(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("Utilise /kick", ephemeral=True)

@bot.tree.command(name="adminpanel")
async def adminpanel(interaction: discord.Interaction):
    await interaction.response.send_message("🛡 Panel Admin", view=AdminPanel())

# ================= RUN =================
bot.run(TOKEN)
