import discord
from discord import app_commands
import asyncio
import os

# Bot configuration
TOKEN = os.getenv("TOKEN", "MTUyMzEzMjAyODk3Mzc0ODM1Nw.GsEkwE.mWiIPbB7H8WLuGjd_WU48K5WlMakaIQoxoU2k8")
SERVER_ID = 1523132533838053507  # ← Replace with your server ID (numbers only)
INVITE_LINK = "https://discord.gg/8WeGnsnGnD"
ROLE_NAME = "Pic Perms"

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    await tree.sync(guild=discord.Object(id=SERVER_ID))
    print(f"✅ Slash commands synced for server {SERVER_ID}")

@bot.event
async def on_presence_update(before, after):
    guild = bot.get_guild(SERVER_ID)
    if not guild:
        return

    member = guild.get_member(after.id)
    if not member:
        return

    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if not role:
        print(f"❌ Role '{ROLE_NAME}' not found in server!")
        return

    custom_status = None
    for activity in after.activities:
        if isinstance(activity, discord.CustomActivity):
            custom_status = activity.name
            break

    has_invite = custom_status and INVITE_LINK in custom_status

    if has_invite and role not in member.roles:
        await member.add_roles(role)
        print(f"➕ Gave '{ROLE_NAME}' to {member.name}")
    elif not has_invite and role in member.roles:
        await member.remove_roles(role)
        print(f"➖ Removed '{ROLE_NAME}' from {member.name}")

@bot.event
async def on_member_update(before, after):
    if before.activities != after.activities:
        await on_presence_update(before, after)

@tree.command(
    name="check",
    description="Check if a user has the invite in their status",
    guild=discord.Object(id=SERVER_ID)
)
async def check(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)

    role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
    if not role:
        await interaction.followup.send(f"❌ Role '{ROLE_NAME}' not found!", ephemeral=True)
        return

    member = interaction.guild.get_member(member.id)
    if not member:
        await interaction.followup.send("❌ Member not found.", ephemeral=True)
        return

    custom_status = None
    for activity in member.activities:
        if isinstance(activity, discord.CustomActivity):
            custom_status = activity.name
            break

    has_invite = custom_status and INVITE_LINK in custom_status

    if has_invite and role not in member.roles:
        await member.add_roles(role)
        await interaction.followup.send(f"✅ {member.mention} has the invite — gave '{ROLE_NAME}'!", ephemeral=True)
    elif not has_invite and role in member.roles:
        await member.remove_roles(role)
        await interaction.followup.send(f"❌ {member.mention} doesn't have the invite — removed '{ROLE_NAME}'!", ephemeral=True)
    elif has_invite and role in member.roles:
        await interaction.followup.send(f"✅ {member.mention} already has '{ROLE_NAME}'!", ephemeral=True)
    else:
        await interaction.followup.send(f"ℹ️ {member.mention} doesn't have the invite and doesn't have the role.", ephemeral=True)

@tree.command(
    name="mystatus",
    description="See what the bot detects in your custom status",
    guild=discord.Object(id=SERVER_ID)
)
async def mystatus(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    member = interaction.guild.get_member(interaction.user.id)

    custom_status = None
    for activity in member.activities:
        if isinstance(activity, discord.CustomActivity):
            custom_status = activity.name
            break

    if custom_status:
        await interaction.followup.send(f"Your custom status is: **{custom_status}**", ephemeral=True)
    else:
        await interaction.followup.send("You don't have a custom status set.", ephemeral=True)

bot.run(TOKEN)