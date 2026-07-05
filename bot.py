import discord
from discord import app_commands
import asyncio
import os

# Bot configuration
TOKEN = os.getenv("TOKEN", "MTUyMzEzMjAyODk3Mzc0ODM1Nw.GN-M7n.mUO0IUr3wRX6xS3J6y2SWJHz2oJReZLECYoIAQ")
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
    print(f"✅ Connected to {len(bot.guilds)} servers:")
    for guild in bot.guilds:
        print(f"   - {guild.name} (ID: {guild.id})")
    # Sync commands globally (works in all servers)
    await tree.sync()
    print(f"✅ Slash commands synced globally")

@bot.event
async def on_presence_update(before, after):
    """Triggered when a user's status changes."""
    for guild in bot.guilds:
        member = guild.get_member(after.id)
        if not member:
            continue

        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if not role:
            continue

        custom_status = None
        for activity in after.activities:
            if isinstance(activity, discord.CustomActivity):
                custom_status = activity.name
                break

        has_invite = custom_status and INVITE_LINK in custom_status

        if has_invite and role not in member.roles:
            try:
                await member.add_roles(role)
                print(f"➕ Gave '{ROLE_NAME}' to {member.name} in {guild.name}")
            except Exception as e:
                print(f"❌ Could not add role in {guild.name}: {e}")
        elif not has_invite and role in member.roles:
            try:
                await member.remove_roles(role)
                print(f"➖ Removed '{ROLE_NAME}' from {member.name} in {guild.name}")
            except Exception as e:
                print(f"❌ Could not remove role in {guild.name}: {e}")

@bot.event
async def on_member_update(before, after):
    """Also check when member data updates."""
    if before.activities != after.activities:
        await on_presence_update(before, after)

@bot.event
async def on_guild_join(guild):
    """When the bot joins a new server."""
    print(f"✅ Joined new server: {guild.name} (ID: {guild.id})")
    # Check all members in the new server who already have the invite in their status
    for member in guild.members:
        if member.bot:
            continue
        custom_status = None
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity):
                custom_status = activity.name
                break
        if custom_status and INVITE_LINK in custom_status:
            role = discord.utils.get(guild.roles, name=ROLE_NAME)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role)
                    print(f"➕ Gave '{ROLE_NAME}' to {member.name} in new server {guild.name}")
                except Exception as e:
                    print(f"❌ Could not add role in {guild.name}: {e}")

@tree.command(
    name="check",
    description="Check if a user has the invite in their status"
)
async def check(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)

    role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
    if not role:
        await interaction.followup.send(f"❌ Role '{ROLE_NAME}' not found in this server! Create a role with that name first.", ephemeral=True)
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
    description="See what the bot detects in your custom status"
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

@tree.command(
    name="setup",
    description="Explain how to set up the bot in this server"
)
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"**How to set up the Rep Bot:**\n\n"
        f"1. Create a role named **'{ROLE_NAME}'** (Server Settings → Roles → Create Role)\n"
        f"2. Make sure my role is **above** '{ROLE_NAME}' in the role list\n"
        f"3. That's it! Anyone who puts `{INVITE_LINK}` in their custom status will get the role automatically\n\n"
        f"Commands:\n"
        f"`/check @user` — Manually check someone\n"
        f"`/mystatus` — See your own custom status",
        ephemeral=True
    )

bot.run(TOKEN)