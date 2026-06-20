"""Void Tools v2.0 BETA — selfbot FREE."""
import discord

# compat discord.py-self 2.1
if not hasattr(discord, "Intents"):
    class Intents:
        @staticmethod
        def default():
            return Intents()

        def __init__(self):
            self.members = True
            self.reactions = True
            self.messages = True
            self.message_content = True
            self.guilds = True
            self.dm_messages = True
            self.guild_messages = True

    discord.Intents = Intents

import aiofiles
import asyncio
import base64
import cgi
import ctypes
import io
import json
import os
import platform
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from collections import defaultdict
from datetime import timedelta
from io import BytesIO
from random import choice, randint, uniform
from typing import Union
from urllib.parse import quote

import aiohttp
import pyautogui
import requests
import spotipy
import tls_client
from colorama import Fore, Style
from discord.ext import commands, tasks
from googletrans import LANGUAGES, Translator
from PIL import Image, ImageGrab
from plyer import notification
from pypresence import Presence
from pystyle import *
from spotipy.oauth2 import SpotifyOAuth
from tls_client import Session
from ctypes import wintypes
import win32con
import win32gui

import void_ui
import void_pages
from void_cogs import RonMessageCog, load_event_react_data

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(ROOT, "config")
DATA = os.path.join(ROOT, "data")
os.makedirs(CFG, exist_ok=True)
os.makedirs(DATA, exist_ok=True)


def cfg(name: str) -> str:
    return os.path.join(CFG, name)


def ensure_runtime_config() -> None:
    """Create missing config from examples (safe for fresh / shared installs)."""
    settings = cfg("settings.json")
    example = cfg("settings.example.json")
    if not os.path.isfile(settings) and os.path.isfile(example):
        shutil.copy2(example, settings)

    tokens = cfg("tokens.txt")
    if not os.path.isfile(tokens):
        open(tokens, "a", encoding="utf-8").close()

    token_file = cfg("token.txt")
    if not os.path.isfile(token_file):
        with open(token_file, "w", encoding="utf-8") as handle:
            handle.write("# Colle ton token Discord sur la ligne suivante :\n")

    vip_keys = cfg("vip_keys.json")
    vip_example = cfg("vip_keys.example.json")
    if not os.path.isfile(vip_keys) and os.path.isfile(vip_example):
        shutil.copy2(vip_example, vip_keys)


ensure_runtime_config()


def read_token_from_file(name: str) -> str:
    path = cfg(name)
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip().strip('"').strip("'")
                if line and not line.startswith("#") and line != "TON_TOKEN_ICI":
                    return line
    except OSError:
        return ""
    return ""


def resolve_user_token(settings: dict) -> str:
    token = (settings.get("token") or "").strip()
    if token and token != "TON_TOKEN_ICI":
        return token
    for name in ("token.txt", "tokens.txt"):
        token = read_token_from_file(name)
        if token:
            return token
    return ""


def data(name: str) -> str:
    return os.path.join(DATA, name)


DEFAULT_AUTOREPLIES = ["?", "what", "cry", "ok", "and?", "stay mad"]
DEFAULT_KILL_MESSAGES = ["cope", "mad?", "L", "ratio", "stay down"]

# --- Void Tools promo links ---
VOID_DISCORD = "discord.gg/voidv2"
VOID_TELEGRAM = "t.me/v0idtool"
VOID_PROMO_TAG = f"{VOID_DISCORD} | {VOID_TELEGRAM}"
VOID_PROMO_FULL = f"@everyone JOIN {VOID_PROMO_TAG}"
NUKE_PROMO_MESSAGES = [
    f"@everyone JOIN {VOID_DISCORD}",
    f"@everyone {VOID_TELEGRAM} — Void Tools v2.0",
    f"@everyone {VOID_PROMO_TAG}",
    f"@everyone VOID TOOLS → {VOID_DISCORD}",
    f"@everyone TELEGRAM → {VOID_TELEGRAM}",
    f"@everyone BEST SB → {VOID_DISCORD} + {VOID_TELEGRAM}",
]

def _pick_lines(items, defaults: list) -> list:
    if isinstance(items, list) and items:
        return [str(x) for x in items if str(x).strip()]
    return list(defaults)


async def resolve_target_user(ctx, arg: str | None = None):
    """Resolve @mention or user id — more reliable than discord.User on selfbot."""
    if ctx.message.mentions:
        return ctx.message.mentions[0]
    raw = (arg or "").strip()
    if not raw:
        return None
    if raw.startswith("<@") and raw.endswith(">"):
        raw = raw.replace("<@!", "").replace("<@", "").replace(">", "")
    try:
        return await ctx.bot.fetch_user(int(raw))
    except (ValueError, TypeError, discord.HTTPException):
        return None


# --- ANSI colors (shared) ---
black = "\033[30m"
red = "\033[31m"
green = "\033[32m"
yellow = "\033[33m"
blue = "\033[34m"
magenta = "\033[35m"
cyan = "\033[36m"
white = "\033[37m"
reset = "\033[0m"
pink = "\033[38;2;255;192;203m"
light_green = "\033[92m"
light_yellow = "\033[93m"
light_magenta = "\033[95m"
light_cyan = "\033[96m"
light_red = "\033[91m"
light_blue = "\033[94m"


# ========== VOID TOOLS VIP SYSTEM ==========
# Mettre a False = tout gratuit, aucun lock VIP
VIP_ENABLED = False


class VoidVIP:
    """Free vs VIP — deblocage via ticket Discord + cle .license"""

    def __init__(self):
        self.tier = "free"
        self.license_key = ""
        self.discord_invite = "https://discord.gg/voidv2"
        self.telegram_invite = "https://t.me/v0idtool"
        self.ticket_channel = "#achat-vip"
        self.ticket_steps = []
        self.price_label = "VIP Lifetime"
        self.vip_pages = {1, 6, 7, 10, 12, 13, 15}
        self.vip_commands = set()
        self.free_commands = set()
        self.load()

    def load(self):
        path = cfg("vip.json")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = {}
        self.tier = str(data.get("tier", "free")).lower()
        self.license_key = str(data.get("license_key", "") or "")
        self.discord_invite = data.get("discord_invite", self.discord_invite)
        self.telegram_invite = data.get("telegram_invite", self.telegram_invite)
        self.ticket_channel = data.get("ticket_channel", self.ticket_channel)
        self.ticket_steps = data.get("ticket_steps") or [
            "Rejoins le Discord Void Tools",
            f"Ouvre un ticket dans {self.ticket_channel}",
            "Paie la licence VIP",
            "Recois ta cle -> .license <cle>",
        ]
        self.price_label = data.get("price_label", self.price_label)
        self.vip_pages = set(data.get("vip_pages", list(self.vip_pages)))
        self.vip_commands = {c.lower() for c in data.get("vip_commands", [])}
        self.free_commands = {c.lower() for c in data.get("free_commands", [])}
        if self.tier == "vip" and self.license_key and not self._key_valid(self.license_key):
            self.tier = "free"
            self.license_key = ""

    def save(self):
        path = cfg("vip.json")
        payload = {
            "tier": self.tier,
            "license_key": self.license_key,
            "discord_invite": self.discord_invite,
            "ticket_channel": self.ticket_channel,
            "ticket_steps": self.ticket_steps,
            "price_label": self.price_label,
            "vip_pages": sorted(self.vip_pages),
            "vip_commands": sorted(self.vip_commands),
            "free_commands": sorted(self.free_commands),
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
            handle.write("\n")

    def _load_valid_keys(self):
        keys_path = cfg("vip_keys.json")
        if not os.path.exists(keys_path):
            example = cfg("vip_keys.example.json")
            if os.path.exists(example):
                shutil.copy2(example, keys_path)
        try:
            with open(keys_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            raw = data.get("keys", [])
            return {str(k).strip().upper() for k in raw if str(k).strip()}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return set()

    def _key_valid(self, key: str) -> bool:
        if not key:
            return False
        return key.strip().upper() in self._load_valid_keys()

    def is_active(self) -> bool:
        if not VIP_ENABLED:
            return True
        return self.tier == "vip"

    def tier_label(self) -> str:
        if not VIP_ENABLED:
            return "FREE"
        return "VIP" if self.tier == "vip" else "FREE"

    def activate(self, key: str):
        normalized = key.strip().upper()
        if not self._key_valid(normalized):
            return False, "Cle invalide ou expiree."
        self.tier = "vip"
        self.license_key = normalized
        self.save()
        return True, "VIP active — toutes les fonctions premium debloquees."

    def command_names(self, cmd):
        names = set()
        current = cmd
        while current is not None:
            if current.name:
                names.add(current.name.lower())
            current = current.parent
        return names

    def is_vip_command(self, cmd) -> bool:
        if not VIP_ENABLED:
            return False
        if cmd is None:
            return False
        names = self.command_names(cmd)
        if names & self.free_commands:
            return False
        if names & self.vip_commands:
            return True
        return False

    def is_vip_page(self, page_num: int) -> bool:
        if not VIP_ENABLED:
            return False
        return int(page_num) in self.vip_pages

    def lock_message(self) -> str:
        if not VIP_ENABLED:
            return void_ui.text_notice("Access", "Toutes les commandes sont gratuites.", success=True)
        return void_ui.text_vip_lock(self)

    def status_message(self) -> str:
        if not VIP_ENABLED:
            return void_ui.text_notice(
                "Plans",
                "VIP desactive — toutes les commandes sont FREE pour l'instant.",
                success=True,
            )
        return void_ui.text_vip_status(self)


void_vip = VoidVIP()


def refresh_void_branding():
    global BRAND_TAGLINE, BRAND_VERSION
    BRAND_VERSION = "v2.0 BETA"
    BRAND_TAGLINE = "Free"


def sync_rpc_tier():
    global RpcState, Rpcdetails
    RpcState = "Void Tools"
    Rpcdetails = "Free | .menu"


async def void_vip_check(ctx):
    if not VIP_ENABLED or void_vip.is_active():
        return True
    cmd = ctx.command
    if cmd is None:
        return True
    if not void_vip.is_vip_command(cmd):
        return True
    try:
        await ctx.send(void_vip.lock_message(), delete_after=25)
    except Exception:
        pass
    return False


MENU_PAGE_COUNT = void_pages.PAGE_COUNT
HELP_TIMEOUT = 120


def parse_help_page_number(content: str):
    if not content:
        return None
    normalized = content.strip().lower()
    if normalized.startswith("."):
        normalized = normalized[1:]
    if normalized.startswith("p") and normalized[1:].isdigit():
        page_num = int(normalized[1:])
        if 1 <= page_num <= MENU_PAGE_COUNT:
            return page_num
    return None


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_help_channels = set()
        self.auto_snipe_settings = {}
        self.auto_csnipe_settings = {}
        self.user_themes = self.load_themes()
        self.default_colors = {
            "text": blue,
            "highlight": magenta,
            "accent": red
        }
        self.command_help = {
        "outlast": {
        "usage": "outlast <@user>",
        "description": "Outlast @user in channel",
        "example": ".outlast @user",
        "category": "Multi Token Management"
    },
    "stopoutlast": {
        "usage": "stopoutlast",
        "description": "Stop outlast command",
        "example": ".stopoutlast",
        "category": "Multi Token Management"
    },
    "multilast": {
        "usage": "multilast <@user>",
        "description": "Multiple token outlast",
        "example": ".multilast @user",
        "category": "Multi Token Management"
    },
    "stopmultilast": {
        "usage": "stopmultilast",
        "description": "Stop multilast command",
        "example": ".stopmultilast",
        "category": "Multi Token Management"
    },
    "tok": {
        "usage": "tok",
        "description": "Showcases all tokens",
        "example": ".tok",
        "category": "Multi Token Management"
    },
    "multivc": {
        "usage": "multivc",
        "description": "Connects all tokens to VC",
        "example": ".multivc",
        "category": "Multi Token Management"
    },
    "ar": {
        "usage": "ar <@user>",
        "description": "Autoresponds to @user",
        "example": ".ar @user",
        "category": "Auto Response"
    },
    "arend": {
        "usage": "arend",
        "description": "Stop autoresponse",
        "example": ".arend",
        "category": "Auto Response"
    },
    "arm": {
        "usage": "arm <@user>",
        "description": "Autoreply multi token",
        "example": ".arm @user",
        "category": "Auto Response"
    },
    "armend": {
        "usage": "armend",
        "description": "Stop multi token autoreply",
        "example": ".armend",
        "category": "Auto Response"
    },
    "kill": {
        "usage": "kill <@user>",
        "description": "Spams @user until rate limit",
        "example": ".kill @user",
        "category": "Spam & Control"
    },
    "killend": {
        "usage": "killend",
        "description": "Stop kill command",
        "example": ".killend",
        "category": "Spam & Control"
    },
    "gcfill": {
        "usage": "gcfill",
        "description": "Fills gc with tokens",
        "example": ".gcfill",
        "category": "Spam & Control"
    },
    "gc": {
        "usage": "gc",
        "description": "Changes gc with tokens",
        "example": ".gc",
        "category": "Spam & Control"
    },
    "gcend": {
        "usage": "gcend",
        "description": "Stop gc command",
        "example": ".gcend",
        "category": "Spam & Control"
    },
    "mping": {
        "usage": "mping",
        "description": "Mass ping the server with tokens",
        "example": ".mping",
        "category": "Spam & Control"
    },
    "mpingoff": {
        "usage": "mpingoff",
        "description": "Turns off mass ping",
        "example": ".mpingoff",
        "category": "Spam & Control"
    },
    "invis": {
        "usage": "invis",
        "description": "Mass spam invis text",
        "example": ".invis",
        "category": "Spam & Control"
    },
    "invisoff": {
        "usage": "invisoff",
        "description": "Turns off invis spam",
        "example": ".invisoff",
        "category": "Spam & Control"
    },
    "popout": {
        "usage": "popout",
        "description": "Auto Press",
        "example": ".popout",
        "category": "Spam & Control"
    },
    "bold": {
        "usage": "bold",
        "description": "Turns all messages bold",
        "example": ".bold",
        "category": "Message Formatting"
    },
    "unbold": {
        "usage": "unbold",
        "description": "Turns off bold messages",
        "example": ".unbold",
        "category": "Message Formatting"
    },
    "cord": {
        "usage": "cord",
        "description": "Pings user while making message bold",
        "example": ".cord",
        "category": "Message Formatting"
    },
    "cordoff": {
        "usage": "cordoff",
        "description": "Turns off cord command",
        "example": ".cordoff",
        "category": "Message Formatting"
    },
    "translate": {
        "usage": "translate <language>",
        "description": "Translates your message",
        "example": ".translate spanish",
        "category": "Message Formatting"
    },
    "translateoff": {
        "usage": "translateoff",
        "description": "Turns off translate",
        "example": ".translateoff",
        "category": "Message Formatting"
    },
    "mreact": {
        "usage": "mreact",
        "description": "Mass reacts with specific emoji",
        "example": ".mreact",
        "category": "Reactions & Status"
    },
    "reactoff": {
        "usage": "reactoff",
        "description": "Turns off mass react",
        "example": ".reactoff",
        "category": "Reactions & Status"
    },
    "autoreact": {
        "usage": "autoreact",
        "description": "Auto react to messages globally",
        "example": ".autoreact",
        "category": "Reactions & Status"
    },
    "autoreactoff": {
        "usage": "autoreactoff",
        "description": "Turns off autoreact",
        "example": ".autoreactoff",
        "category": "Reactions & Status"
    },
    "rpcall": {
        "usage": "rpcall",
        "description": "Custom status for all tokens",
        "example": ".rpcall",
        "category": "Reactions & Status"
    },
    "stoprpc": {
        "usage": "stoprpc",
        "description": "Stop custom status",
        "example": ".stoprpc",
        "category": "Reactions & Status"
    },
    "inviteinfo": {
        "usage": "inviteinfo <code>",
        "description": "Displays invite information",
        "example": ".inviteinfo abc123",
        "category": "Server & User Info"
    },
    "serverinfo": {
        "usage": "serverinfo",
        "description": "Get server information",
        "example": ".serverinfo",
        "category": "Server & User Info"
    },
    "userinfo": {
        "usage": "userinfo",
        "description": "Get info off a user",
        "example": ".userinfo",
        "category": "Server & User Info"
    },
    "nickname": {
        "usage": "nickname",
        "description": "Change your server nickname",
        "example": ".nickname",
        "category": "Utility"
    },
    "mimic": {
        "usage": "mimic @user | mimic off",
        "description": "Copy messages from a user",
        "example": ".mimic @user",
        "category": "Utility"
    },
    "mimicoff": {
        "usage": "mimic off",
        "description": "Stop mimicking",
        "example": ".mimic off",
        "category": "Utility"
    },
    "emojisteal": {
        "usage": "emojisteal",
        "description": "Steal emoji and add to server",
        "example": ".emojisteal",
        "category": "Utility"
    },
    "reload": {
        "usage": "reload",
        "description": "Reload the selfbot",
        "example": ".reload",
        "category": "Utility"
    },
    "say": {
        "usage": "say #optional <num>",
        "description": "Send specific message with tokens",
        "example": ".say #general 5",
        "category": "Utility"
    },
    "pfpscrape": {
        "usage": "pfpscrape <num>",
        "description": "Scrapes server for <number> of members pfp",
        "example": ".pfpscrape 10",
        "category": "User Interaction"
    },
    "triggertyping": {
        "usage": "triggertyping <duration>",
        "description": "Set user typing for specific duration",
        "example": ".triggertyping 30",
        "category": "User Interaction"
    },
    "triggertypingoff": {
        "usage": "triggertypingoff",
        "description": "Turn off trigger typing",
        "example": ".triggertypingoff",
        "category": "User Interaction"
    },
    "ghostping": {
        "usage": "ghostping <@user>",
        "description": "Double Ghost ping a user",
        "example": ".ghostping @user",
        "category": "User Interaction"
    },
    "antigcspam": {
        "usage": "antigcspam",
        "description": "Toggle autogroupchat leaver",
        "example": ".antigcspam",
        "category": "User Interaction"
    },
    "token": {
        "usage": "token",
        "description": "Get a users token ( HAHA U THOUGHT )",
        "example": ".token",
        "category": "User Interaction"
    },
    "forcedc": {
        "usage": "forcedc",
        "description": "Force disconnect a user from vcs",
        "example": ".forcedc",
        "category": "User Interaction"
    },
    "dreact": {
        "usage": "dreact",
        "description": "Auto react to messages with alternating emojis",
        "example": ".dreact",
        "category": "Message & Reaction"
    },
    "mspam": {
        "usage": "mspam",
        "description": "Spam a message with all your tokens",
        "example": ".mspam",
        "category": "Message & Reaction"
    },
    "webhookcopy": {
        "usage": "webhookcopy",
        "description": "Send messages as a webhook",
        "example": ".webhookcopy",
        "category": "Message & Reaction"
    },
    "webhookcopyoff": {
        "usage": "webhookcopyoff",
        "description": "Turn off Webhook copying",
        "example": ".webhookcopyoff",
        "category": "Message & Reaction"
    },
    "avatar": {
        "usage": "avatar",
        "description": "Get avatar of user or yourself",
        "example": ".avatar",
        "category": "Message & Reaction"
    },
    "tempchannel": {
        "usage": "tempchannel <name>",
        "description": "Create a temp text channel",
        "example": ".tempchannel general",
        "category": "Server Management"
    },
    "tempvc": {
        "usage": "tempvc <name>",
        "description": "Create a temp voice channel",
        "example": ".tempvc voice",
        "category": "Server Management"
    },
    "roblox": {
        "usage": "roblox <username>",
        "description": "Get info from a roblox user",
        "example": ".roblox username",
        "category": "Server Management"
    },
    "servername": {
        "usage": "servername <name>",
        "description": "Change the guild's name",
        "example": ".servername New Server",
        "category": "Server Management"
    },
    "pin": {
        "usage": "pin",
        "description": "Pin the most recent message",
        "example": ".pin",
        "category": "Server Management"
    },
    "createchannel": {
        "usage": "createchannel",
        "description": "Create a channel",
        "example": ".createchannel",
        "category": "Server Management"
    },
    "createvc": {
        "usage": "createvc",
        "description": "Create a Voice Channel",
        "example": ".createvc",
        "category": "Server Management"
    },
    "createrole": {
        "usage": "createrole",
        "description": "Create a role",
        "example": ".createrole",
        "category": "Server Management"
    },
    "cls": {
        "usage": "cls",
        "description": "Clear cmd prompt ui",
        "example": ".cls",
        "category": "Utility & Backup"
    },
    "backupserver": {
        "usage": "backupserver",
        "description": "Backup your server and save to json",
        "example": ".backupserver",
        "category": "Utility & Backup"
    },
    "pasteserver": {
        "usage": "pasteserver",
        "description": "Paste your backup json into your new server",
        "example": ".pasteserver",
        "category": "Utility & Backup"
    },
    "clearbackup": {
        "usage": "clearbackup",
        "description": "Clear ALL backup jsons",
        "example": ".clearbackup",
        "category": "Utility & Backup"
    },
    "clearchannels": {
        "usage": "clearchannels",
        "description": "Clear all channels and categories",
        "example": ".clearchannels",
        "category": "Utility & Backup"
    },
    "kiss": {
        "usage": "kiss <@user>",
        "description": "Kiss a user",
        "example": ".kiss @user",
        "category": "Friendly Actions"
    },
    "pat": {
        "usage": "pat <@user>",
        "description": "Pat a user",
        "example": ".pat @user",
        "category": "Friendly Actions"
    },
    "hug": {
        "usage": "hug <@user>",
        "description": "Hug a user",
        "example": ".hug @user",
        "category": "Friendly Actions"
    },
    "wave": {
        "usage": "wave <@user>",
        "description": "Wave at a user",
        "example": ".wave @user",
        "category": "Friendly Actions"
    },
    "cuddle": {
        "usage": "cuddle <@user>",
        "description": "Cuddle a user",
        "example": ".cuddle @user",
        "category": "Friendly Actions"
    },
    "handhold": {
        "usage": "handhold <@user>",
        "description": "Hold hands with a user",
        "example": ".handhold @user",
        "category": "Friendly Actions"
    },
    "highfive": {
        "usage": "highfive <@user>",
        "description": "High-five a user",
        "example": ".highfive @user",
        "category": "Friendly Actions"
    },
    "poke": {
        "usage": "poke <@user>",
        "description": "Poke a user",
        "example": ".poke @user",
        "category": "Friendly Actions"
    },
    "nom": {
        "usage": "nom <@user>",
        "description": "Nom on a user",
        "example": ".nom @user",
        "category": "Playful Actions"
    },
    "wink": {
        "usage": "wink",
        "description": "Wink i guess",
        "example": ".wink",
        "category": "Playful Actions"
    },
    "dance": {
        "usage": "dance",
        "description": "Dance",
        "example": ".dance",
        "category": "Playful Actions"
    },
    "smug": {
        "usage": "smug",
        "description": "Show a smug expression",
        "example": ".smug",
        "category": "Playful Actions"
    },
    "cry": {
        "usage": "cry",
        "description": ":( aww cry baby",
        "example": ".cry",
        "category": "Playful Actions"
    },
    "slap": {
        "usage": "slap <@user>",
        "description": "Slap a user",
        "example": ".slap @user",
        "category": "Aggressive Actions"
    },
    "bite": {
        "usage": "bite <@user>",
        "description": "Bite a user",
        "example": ".bite @user",
        "category": "Aggressive Actions"
    },
    "lick": {
        "usage": "lick <@user>",
        "description": "Lick a user",
        "example": ".lick @user",
        "category": "Aggressive Actions"
    },
    "bully": {
        "usage": "bully <@user>",
        "description": "Bully a user",
        "example": ".bully @user",
        "category": "Aggressive Actions"
    },
    "hurt": {
        "usage": "hurt <@user>",
        "description": "Kill a user",
        "example": ".hurt @user",
        "category": "Aggressive Actions"
    },
    "bonk": {
        "usage": "bonk <@user>",
        "description": "Bonk a user",
        "example": ".bonk @user",
        "category": "Aggressive Actions"
    },
    "yeet": {
        "usage": "yeet <@user>",
        "description": "Yeet a user",
        "example": ".yeet @user",
        "category": "Aggressive Actions"
    },
    "emojiexport": {
        "usage": "emojiexport",
        "description": "Download all emojis from server",
        "example": ".emojiexport",
        "category": "Emoji Management"
    },
    "pastemoji": {
        "usage": "pastemoji",
        "description": "Add all your exported emojis",
        "example": ".pastemoji",
        "category": "Emoji Management"
    },
    "wipemojis": {
        "usage": "wipemojis",
        "description": "Clear all exported emojis",
        "example": ".wipemojis",
        "category": "Emoji Management"
    },
    "leavegroups": {
        "usage": "leavegroups",
        "description": "Leave all of your groups",
        "example": ".leavegroups",
        "category": "Server & Group Actions"
    },
    "firstmessage": {
        "usage": "firstmessage <channel>",
        "description": "See the first message in the channel",
        "example": ".firstmessage #general",
        "category": "Server & Group Actions"
    },
    "fakeactive": {
        "usage": "fakeactive",
        "description": "Use your tokens to make server active",
        "example": ".fakeactive",
        "category": "Server & Group Actions"
    },
    "fakeactiveoff": {
        "usage": "fakeactiveoff",
        "description": "Turn off fake activity",
        "example": ".fakeactiveoff",
        "category": "Server & Group Actions"
    },
    "info": {
        "usage": "info",
        "description": "Show Cmd Prmpt Info but in chat",
        "example": ".info",
        "category": "Server & Group Actions"
    },

    "pingresponse": {
        "usage": "pingresponse [toggle/list/clear] [response]",
        "description": "Reply to pings with a custom response",
        "example": ".pingresponse toggle \"your a skid!\"",
        "category": "Ping Response System"
    },
    "pinginsult": {
        "usage": "pinginsult [toggle/list/clear]",
        "description": "Reply to pings by insulting the user",
        "example": ".pinginsult toggle",
        "category": "Ping Response System"
    },
    "pingreact": {
        "usage": "pingreact [toggle reaction/list/clear]",
        "description": "Reply to pings by adding a reaction",
        "example": ".pingreact toggle 👋",
        "category": "Ping Response System"
    },
    "mcountdown": {
        "usage": "mcountdown <@user> <num>",
        "description": "Afk check someone with tokens",
        "example": ".mcountdown @user 60",
        "category": "AFK Check Systems"
    },
    "mcountdownoff": {
        "usage": "mcountdownoff",
        "description": "Stop Multi countdown",
        "example": ".mcountdownoff",
        "category": "AFK Check Systems"
    },
    "countdown": {
        "usage": "countdown <@user> <num>",
        "description": "Afk Check someone",
        "example": ".countdown @user 30",
        "category": "AFK Check Systems"
    },
    "countdownoff": {
        "usage": "countdownoff",
        "description": "Stop Countdown",
        "example": ".countdownoff",
        "category": "AFK Check Systems"
    },
    "autotrap": {
        "usage": "autotrap [toggle <user>/list/clear]",
        "description": "Manage users who cannot leave the group chat",
        "example": ".autotrap toggle @user",
        "category": "User Control Systems"
    },
    "autonick": {
        "usage": "autonick [toggle <@user> <nickname>/list/clear]",
        "description": "Force change a user's nickname",
        "example": ".autonick toggle @user NewNick",
        "category": "User Control Systems"
    },
    "forcepurge": {
        "usage": "forcepurge [toggle <@user>/list/clear]",
        "description": "Force delete a user's messages",
        "example": ".forcepurge toggle @user",
        "category": "User Control Systems"
    },
    "autokick": {
        "usage": "autokick [toggle <@user>/list/clear]",
        "description": "Automatically kick users",
        "example": ".autokick toggle @user",
        "category": "User Control Systems"
    },
    "autovclock": {
        "usage": "autovclock",
        "description": "Auto lock a voice channel when you join",
        "example": ".autovclock",
        "category": "User Control Systems"
    },
    "destroy": {
        "usage": "destroy",
        "description": "Perform destructive actions on the server",
        "example": ".destroy",
        "category": "Nuke Configuration"
    },
    "nukehook": {
        "usage": "nukehook",
        "description": "Change the webhook message for the nuke process",
        "example": ".nukehook",
        "category": "Nuke Configuration"
    },
    "nukename": {
        "usage": "nukename",
        "description": "Change the Discord server name for the nuke process",
        "example": ".nukename",
        "category": "Nuke Configuration"
    },
    "nukedelay": {
        "usage": "nukedelay",
        "description": "Change the delay between webhook messages",
        "example": ".nukedelay",
        "category": "Nuke Configuration"
    },
    "nukechannel": {
        "usage": "nukechannel",
        "description": "Change the channel name used for the webhook",
        "example": ".nukechannel",
        "category": "Nuke Configuration"
    },
    "nukeconfig": {
        "usage": "nukeconfig",
        "description": "Show the current configuration for the nuke process",
        "example": ".nukeconfig",
        "category": "Nuke Configuration"
    },
    "nukeconfigwipe": {
        "usage": "nukeconfigwipe",
        "description": "Delete the nuke config file and reset all data",
        "example": ".nukeconfigwipe",
        "category": "Nuke Configuration"
    },
    "massrole": {
        "usage": "massrole <name>",
        "description": "Creates mass roles with the given name",
        "example": ".massrole NewRole",
        "category": "Mass Server Actions"
    },
    "massroledel": {
        "usage": "massroledel",
        "description": "Deletes all roles except the default ones",
        "example": ".massroledel",
        "category": "Mass Server Actions"
    },
    "masschannel": {
        "usage": "masschannel <name> <number>",
        "description": "Creates mass channels",
        "example": ".masschannel general 5",
        "category": "Mass Server Actions"
    },
    "massban": {
        "usage": "massban",
        "description": "Bans everyone from the server",
        "example": ".massban",
        "category": "Mass Server Actions"
    },
    "masskick": {
        "usage": "masskick",
        "description": "Kicks everyone from the server",
        "example": ".masskick",
        "category": "Mass Server Actions"
    },
    "massdelemoji": {
        "usage": "massdelemoji",
        "description": "Delete all emojis from server",
        "example": ".massdelemoji",
        "category": "Mass Server Actions"
    },
    "spotify": {
        "usage": "spotify [command] [options]",
        "description": "Control your Spotify playback",
        "example": ".spotify play songname",
        "category": "Spotify Control System",
        "subcommands": {
            "unpause": "Resume playback if paused",
            "pause": "Pause the current playback",
            "next": "Skip to the next track",
            "prev": "Revert to the previous track",
            "play": "Search for and play a specific song",
            "current": "Show current track info",
            "addqueue": "Add a song to the queue",
            "volume": "Set volume level (0-100)",
            "shuffle": "Toggle shuffle mode",
            "repeat": "Set repeat mode (track/context/off)"
        }
    },
    "rotatepfp": {
        "usage": "rotatepfp <hours>",
        "description": "Starts profile picture rotation",
        "example": ".rotatepfp 24",
        "category": "Profile Customization"
    },
    "stoprandomizepfp": {
        "usage": "stoprandomizepfp",
        "description": "Stops profile picture rotation",
        "example": ".stoprandomizepfp",
        "category": "Profile Customization"
    },
    "setpfp": {
        "usage": "setpfp <url>",
        "description": "Set avatar with url",
        "example": ".setpfp https://example.com/image.png",
        "category": "Profile Customization"
    },
    "setbanner": {
        "usage": "setbanner <url>",
        "description": "Set banner with url",
        "example": ".setbanner https://example.com/banner.png",
        "category": "Profile Customization"
    },
    "stealpfp": {
        "usage": "stealpfp <user>",
        "description": "Steal a user's avatar",
        "example": ".stealpfp @user",
        "category": "Profile Customization"
    },
    "stealbanner": {
        "usage": "stealbanner <user>",
        "description": "Steal user's banner",
        "example": ".stealbanner @user",
        "category": "Profile Customization"
    },
    "rotatebio": {
        "usage": "rotatebio <text>",
        "description": "Rotate your bio each hour",
        "example": ".rotatebio Hello World",
        "category": "Bio & Status Management"
    },
    "stoprotatebio": {
        "usage": "stoprotatebio",
        "description": "Stop bio rotation",
        "example": ".stoprotatebio",
        "category": "Bio & Status Management"
    },
    "setbio": {
        "usage": "setbio <custom>",
        "description": "Set your bio",
        "example": ".setbio My Custom Bio",
        "category": "Bio & Status Management"
    },
    "stealbio": {
        "usage": "stealbio <user>",
        "description": "Snatch a user's About Me",
        "example": ".stealbio @user",
        "category": "Bio & Status Management"
    },
    "rstatus": {
        "usage": "rstatus",
        "description": "Rotate your custom status",
        "example": ".rstatus",
        "category": "Bio & Status Management"
    },
    "rstatusend": {
        "usage": "rstatusend",
        "description": "Cancel your rotate status",
        "example": ".rstatusend",
        "category": "Bio & Status Management"
    },
    "nickloop": {
        "usage": "nickloop <nicknames>",
        "description": "Rotates through nicknames",
        "example": ".nickloop Nick1 Nick2 Nick3",
        "category": "Name & Pronouns"
    },
    "stopnickloop": {
        "usage": "stopnickloop",
        "description": "Stops nickname rotation",
        "example": ".stopnickloop",
        "category": "Name & Pronouns"
    },
    "setpronoun": {
        "usage": "setpronoun <custom>",
        "description": "Set a custom pronoun",
        "example": ".setpronoun they/them",
        "category": "Name & Pronouns"
    },
    "rotatepronoun": {
        "usage": "rotatepronoun <custom>",
        "description": "Rotate your pronouns",
        "example": ".rotatepronoun he/him they/them",
        "category": "Name & Pronouns"
    },
    "stoprotatepronoun": {
        "usage": "stoprotatepronoun",
        "description": "Stop pronoun rotate",
        "example": ".stoprotatepronoun",
        "category": "Name & Pronouns"
    },
    "setname": {
        "usage": "setname <custom>",
        "description": "Set a custom display name",
        "example": ".setname NewName",
        "category": "Name & Pronouns"
    },
    "stealpronoun": {
        "usage": "stealpronoun <user>",
        "description": "Snatch a user's pronoun",
        "example": ".stealpronoun @user",
        "category": "Name & Pronouns"
    },
    "stealname": {
        "usage": "stealname <user>",
        "description": "Steal user's display name",
        "example": ".stealname @user",
        "category": "Name & Pronouns"
    },
    "channelinfo": {
        "usage": "channelinfo <id>",
        "description": "Display channel information",
        "example": ".channelinfo 123456789",
        "category": "Server Information"
    },
    "channels": {
        "usage": "channels <serverid>",
        "description": "Shows all channels",
        "example": ".channels 123456789",
        "category": "Server Information"
    },
    "roles": {
        "usage": "roles <serverid>",
        "description": "Shows all roles",
        "example": ".roles 123456789",
        "category": "Server Information"
    },
    "mutualinfo": {
        "usage": "mutualinfo",
        "description": "Shows Mutual info between users",
        "example": ".mutualinfo",
        "category": "Server Information"
    },
    "spamregion": {
        "usage": "spamregion <channel>",
        "description": "Changes voice channel region",
        "example": ".spamregion General",
        "category": "Voice Channel Management"
    },
    "stopspamregion": {
        "usage": "stopspamregion",
        "description": "Stops region spam",
        "example": ".stopspamregion",
        "category": "Voice Channel Management"
    },
    "ronmessage": {
        "usage": "ronmessage [add/list/remove/clear/on/off] [message] [reaction]",
        "description": "Automatic reactions to messages",
        "example": ".ronmessage add \"hello\" 👋",
        "category": "Message Reaction System",
        "subcommands": {
            "add": "Add reaction to message",
            "list": "List message reactions",
            "remove": "Remove message reaction",
            "clear": "Clear all reactions",
            "on/off": "Toggle reaction"
        }
    },
    "sonmessage": {
        "usage": "sonmessage [add/list/remove/clear/on/off] [message] [response]",
        "description": "Automatic responses to messages",
        "example": ".sonmessage add \"hi\" \"hello!\"",
        "category": "Message Response System",
        "subcommands": {
            "add": "Add custom response",
            "list": "List responses",
            "remove": "Remove response",
            "clear": "Clear responses",
            "on/off": "Toggle response"
        }
    },
    "eonmessage": {
        "usage": "eonmessage [add/list/remove/clear/on/off] [message] [edit]",
        "description": "Automatic message editing",
        "example": ".eonmessage add \"original\" \"edited\"",
        "category": "Message Edit System",
        "subcommands": {
            "add": "Add auto-edit",
            "list": "List edits",
            "remove": "Remove edit",
            "clear": "Clear edits",
            "on/off": "Toggle edit"
        }
    },
    "nonping": {
        "usage": "nonping [on/off/status]",
        "description": "Get notifications when pinged",
        "example": ".nonping on",
        "category": "Notification Systems",
        "subcommands": {
            "on/off": "Toggle notifications",
            "status": "Check status"
        }
    },
    "nondm": {
        "usage": "nondm [on/off/status]",
        "description": "Get DM notifications",
        "example": ".nondm on",
        "category": "Notification Systems",
        "subcommands": {
            "on/off": "Toggle DM alerts",
            "status": "Check status"
        }
    },
    "nonreaction": {
        "usage": "nonreaction [on/off/status]",
        "description": "Get reaction notifications",
        "example": ".nonreaction on",
        "category": "Notification Systems",
        "subcommands": {
            "on/off": "Toggle alerts",
            "status": "Check status"
        }
    },
    "wscreenshot": {
        "usage": "wscreenshot",
        "description": "Takes a full screen screenshot",
        "example": ".wscreenshot",
        "category": "Screenshot Management"
    },
    "pscreenshot": {
        "usage": "pscreenshot",
        "description": "Takes a screenshot of active window",
        "example": ".pscreenshot",
        "category": "Screenshot Management"
    },
    "sendss": {
        "usage": "sendss",
        "description": "Sends the most recent screenshot",
        "example": ".sendss",
        "category": "Screenshot Management"
    },
    "openss": {
        "usage": "openss",
        "description": "Opens the most recent screenshot",
        "example": ".openss",
        "category": "Screenshot Management"
    },
    "bsearch": {
        "usage": "bsearch <name>",
        "description": "Search using default browser",
        "example": ".bsearch discord",
        "category": "Windows Utilities"
    },
    "opencalc": {
        "usage": "opencalc",
        "description": "Opens Windows Calculator",
        "example": ".opencalc",
        "category": "Windows Utilities"
    },
    "openpad": {
        "usage": "openpad",
        "description": "Opens Windows Notepad",
        "example": ".openpad",
        "category": "Windows Utilities"
    },
    "dfolder": {
        "usage": "dfolder <name>",
        "description": "Creates Desktop folder",
        "example": ".dfolder NewFolder",
        "category": "Windows Utilities"
    },
    "cleartemp": {
        "usage": "cleartemp",
        "description": "Clear %temp% folder",
        "example": ".cleartemp",
        "category": "Windows Utilities"
    },
    "byoutube": {
        "usage": "byoutube <name>",
        "description": "Search YouTube",
        "example": ".byoutube music",
        "category": "Social Media Search"
    },
    "btwitter": {
        "usage": "btwitter <name>",
        "description": "Search Twitter",
        "example": ".btwitter username",
        "category": "Social Media Search"
    },
    "btiktok": {
        "usage": "btiktok <name>",
        "description": "Search TikTok",
        "example": ".btiktok username",
        "category": "Social Media Search"
    },
    "broblox": {
        "usage": "broblox <name>",
        "description": "Search Roblox",
        "example": ".broblox username",
        "category": "Social Media Search"
    },







    "mdm": {
        "usage": "mdm <num> <message>",
        "description": "Mass DMs a number of friends",
        "example": ".mdm 5 Hello!",
        "category": "Main Commands"
    },
    "theme": {
        "usage": "theme",
        "description": "Change theme colors",
        "example": ".theme",
        "category": "Main Commands"
    },
    "info": {
        "usage": "info",
        "description": "Shows bot info",
        "example": ".info",
        "category": "Main Commands"
    },
    "clear": {
        "usage": "clear",
        "description": "Clear console",
        "example": ".clear",
        "category": "Utility Commands"
    },
    "reload": {
        "usage": "reload",
        "description": "Restart the bot",
        "example": ".reload",
        "category": "Utility Commands"
    },
    "shutdown": {
        "usage": "shutdown",
        "description": "Shutdown the bot",
        "example": ".shutdown",
        "category": "Utility Commands"
    },
    "clearconfigs": {
        "usage": "clearconfigs",
        "description": "Clear all configs",
        "example": ".clearconfigs",
        "category": "Utility Commands"
    },
    "autobump": {
        "usage": "autobump",
        "description": "Auto Bump your server every 2hrs",
        "example": ".autobump",
        "category": "Utility Commands"
    },
    "autobumpoff": {
        "usage": "autobumpoff",
        "description": "Disable autobump",
        "example": ".autobumpoff",
        "category": "Utility Commands"
    },
    "blocked": {
        "usage": "blocked",
        "description": "Show blocked users",
        "example": ".blocked",
        "category": "Utility Commands"
    },
    "pending": {
        "usage": "pending",
        "description": "Show pending friend users",
        "example": ".pending",
        "category": "Utility Commands"
    },
    "outgoing": {
        "usage": "outgoing",
        "description": "Show outgoing friend requests",
        "example": ".outgoing",
        "category": "Utility Commands"
    },
    "tnickname": {
        "usage": "tnickname <server id>",
        "description": "Change token's server nickname",
        "example": ".tnickname 123456789",
        "category": "Token Utility"
    },
    "tpronoun": {
        "usage": "tpronoun <name>",
        "description": "Change token's pronoun",
        "example": ".tpronoun they/them",
        "category": "Token Utility"
    },
    "tbio": {
        "usage": "tbio <custom>",
        "description": "Change token's bio",
        "example": ".tbio New Bio Text",
        "category": "Token Utility"
    },
    "tstatus": {
        "usage": "tstatus <status>",
        "description": "Change token's online status",
        "example": ".tstatus playing games",
        "category": "Token Utility"
    },
    "tstatusoff": {
        "usage": "tstatusoff",
        "description": "Turn off token's custom status",
        "example": ".tstatusoff",
        "category": "Token Utility"
    },
    "tinfo": {
        "usage": "tinfo",
        "description": "Get token account info",
        "example": ".tinfo",
        "category": "Token Utility"
    },
    "tjoin": {
        "usage": "tjoin <invite>",
        "description": "Join server with token",
        "example": ".tjoin voidv2",
        "category": "Token Utility"
    },
    "tleave": {
        "usage": "tleave <server id>",
        "description": "Leave server with token",
        "example": ".tleave 123456789",
        "category": "Token Utility"
    },
    "autopress": {
        "usage": "autopress [command] [options]",
        "description": "Auto press messages in channel",
        "example": ".autopress add \"Hello\"",
        "category": "Auto Press Commands",
        "subcommands": {
            "user": "Auto press messages in channel",
            "stop": "Turn off autopress",
            "list": "List all autopress channels",
            "add": "Add a message to autopress",
            "remove": "Remove a message from autopress",
            "clear": "Clear all autopress messages"
        }
    },

    "autokill": {
        "usage": "autokill [command] [options]",
        "description": "Auto kill user in all channels",
        "example": ".autokill @user",
        "category": "Auto Kill Commands",
        "subcommands": {
            "user": "Auto kill user in all channels",
            "stop": "Turn off autokill",
            "list": "List all autokill users",
            "clear": "Clear all autokill users",
            "add": "Add a word to autokill",
            "remove": "Remove a word from autokill"
        }
    },
    "manual": {
        "usage": "manual [command] [options]",
        "description": "Enable manual mode",
        "example": ".manual @user",
        "category": "Manual Mode Commands",
        "subcommands": {
            "user": "Enable manual mode",
            "stop": "Turn off manual mode",
            "list": "List all manual msgs",
            "clear": "Clear all manual msgs",
            "add": "Add a message to manual mode",
            "remove": "Remove a message from manual mode"
        }
    },
    "vcjoin": {
        "usage": "vcjoin [command] [options]",
        "description": "Voice channel join commands",
        "example": ".vcjoin r 123456789",
        "category": "Multi/Vc Commands",
        "subcommands": {
            "r": "Rotate join a voice channel",
            "s": "Join a voice channel",
            "status": "Shows the current voice channel status",
            "list": "List all available voice channels",
            "leave": "Leave voice channel"
        }
    },
    "dripcheck": {
        "usage": "dripcheck <user>",
        "description": "Check user's drip level",
        "example": ".dripcheck @user",
        "category": "Random Beef Commands"
    },
    "discordreport": {
        "usage": "discordreport <user>",
        "description": "Generate a report card for user",
        "example": ".discordreport @user",
        "category": "Random Beef Commands"
    },
    "relationship": {
        "usage": "relationship <user>",
        "description": "Check user's relationship potential",
        "example": ".relationship @user",
        "category": "Random Beef Commands"
    },
    "stats": {
        "usage": "stats <user>",
        "description": "Get user's stats",
        "example": ".stats @user",
        "category": "Random Beef Commands"
    },
    "unfriend": {
        "usage": "unfriend <user>",
        "description": "Send friend request to user",
        "example": ".unfriend @user",
        "category": "Friend & Block Utility"
    },
    "block": {
        "usage": "block <user>",
        "description": "Block user",
        "example": ".block @user",
        "category": "Friend & Block Utility"
    },
    "unblock": {
        "usage": "unblock <user>",
        "description": "Unblock user",
        "example": ".unblock @user",
        "category": "Friend & Block Utility"
    },
    "friend": {
        "usage": "friend <user id>",
        "description": "Send friend request to user",
        "example": ".friend 123456789",
        "category": "Friend & Block Utility"
    },
    "fnote": {
        "usage": "fnote <user id>",
        "description": "Send friend note to user",
        "example": ".fnote 123456789",
        "category": "Friend & Block Utility"
    },
    "fnick": {
        "usage": "fnick <user id>",
        "description": "Change friend nickname",
        "example": ".fnick 123456789",
        "category": "Friend & Block Utility"
    },
    "autogc": {
        "usage": "autogc [command] [options]",
        "description": "Auto add tokens to any group chat your added to",
        "example": ".autogc whitelist @user",
        "category": "Auto Multi Commands",
        "subcommands": {
            "whitelist": "Whitelist a user to auto add to gc",
            "whitelist remove": "Remove a user from the whitelist",
            "list": "List all whitelisted users"
        }
    },
    "autogcstop": {
        "usage": "autogcstop",
        "description": "Turn off autogc",
        "example": ".autogcstop",
        "category": "Auto Multi Commands"
    },
    "autogcleave": {
        "usage": "autogcleave [stop]",
        "description": "Auto leave any group chat you leave",
        "example": ".autogcleave",
        "category": "Auto Gc Leave Commands",
        "subcommands": {
            "stop": "Turn off autogcleave"
        }
    },
    "autoserverleave": {
        "usage": "autoserverleave [stop]",
        "description": "Auto leave any server you leave",
        "example": ".autoserverleave",
        "category": "Auto Server Leave Commands",
        "subcommands": {
            "stop": "Turn off autoserverleave"
        }
    },
    "repeat": {
        "usage": "repeat [command] [options]",
        "description": "Auto repeat commands",
        "example": ".repeat start",
        "category": "Auto Repeat Commands",
        "subcommands": {
            "start": "Start auto repeat",
            "stop": "Turn off auto repeat",
            "delay": "Set the delay between repeats",
            "status": "Check auto repeat status"
        }
    },
    "ladder": {
        "usage": "ladder [command] [options]",
        "description": "Auto ladder system",
        "example": ".ladder start",
        "category": "Auto Ladder Commands",
        "subcommands": {
            "start": "Start auto ladder",
            "stop": "Turn off auto ladder",
            "delay": "Set the delay between ladders",
            "add": "Add a message to auto ladder",
            "remove": "Remove a message from auto ladder",
            "clear": "Clear all auto ladder messages",
            "list": "List all auto ladder messages",
            "reset": "Reset auto ladder",
            "status": "Show all ladder messages"
        }
    },
    "antigcspam": {
        "usage": "antigcspam [command] [options]",
        "description": "Anti group chat spam protection",
        "example": ".antigcspam whitelist @user",
        "category": "Anti Gc Spam",
        "subcommands": {
            "toggle": "Toggle protection & show status",
            "whitelist": "Add user to whitelist",
            "unwhitelist": "Remove user from whitelist",
            "blacklist": "Add user to blacklist",
            "unblacklist": "Remove user from blacklist",
            "silent": "Toggle silent mode",
            "message": "Set leave message",
            "autoremove": "Toggle auto-remove of blacklisted",
            "webhook": "Set webhook for logging",
            "autoblock": "Toggle auto-block feature",
            "list": "Show white/blacklisted users"
        }
    },
    "rotateguild": {
        "usage": "rotateguild [command] [options]",
        "description": "Guild badge rotation system",
        "example": ".rotateguild start",
        "category": "Rotate Guild",
        "subcommands": {
            "start": "Start rotating guild badges",
            "stop": "Stop rotating guild badges",
            "delay": "Set the delay between guild badge rotations",
            "status": "Show current guild rotation status"
        }
    },
    "protection": {
        "usage": "protection [command] [options]",
        "description": "GC Protection Spam",
        "example": ".protection start",
        "category": "GC Protection Spam",
        "subcommands": {
            "start": "Start protection",
            "stop": "Stop protection",
            "message": "Set protection message",
            "status": "Show protection status"
        }
    },
    "dmsnipe": {
        "usage": "dmsnipe [command] [options]",
        "description": "Message sniper system",
        "example": ".dmsnipe start",
        "category": "Message Sniper System",
        "subcommands": {
            "toggle": "Toggle message sniping",
            "edit": "Toggle edit sniping",
            "ignore": "Toggle ignoring a user",
            "ignore": "Toggle ignoring a channel",
            "status": "Show current settings",
            "clear": "Clear all ignore lists"
        }
    },
    "antilast": {
        "usage": "antilast [command] [options]",
        "description": "Anti last word system",
        "example": ".antilast toggle",
        "category": "Anti Last Word",
        "subcommands": {
            "toggle": "Toggle anti last word system",
            "whitelist": "Add user to whitelist",
            "channel": "Add channel to whitelist",
            "webhook": "Set webhook for logging",
            "config": "Show current config"
        }
    },
    "spam": {
        "usage": "spam [user] [user 2]",
        "description": "Send a message to a user",
        "example": ".spam @user @user2",
        "category": "Spam Commands"
    },
    "hypesquad": {
        "usage": "hypesquad [house]",
        "description": "Change your HypeSquad house",
        "example": ".hypesquad bravery",
        "category": "HypeSquad Commands"
    },
    "setspfp": {
        "usage": "setspfp <url>",
        "description": "Set server-specific profile picture",
        "example": ".setspfp https://example.com/image.png",
        "category": "Server Edit Commands"
    },
    "setsbanner": {
        "usage": "setsbanner <url>",
        "description": "Set server-specific banner",
        "example": ".setsbanner https://example.com/image.png",
        "category": "Server Edit Commands"
    },
    "setsbio": {
        "usage": "setsbio <text>",
        "description": "Set server-specific bio",
        "example": ".setsbio Hello, world!",
        "category": "Server Edit Commands"
    },
    "setspronoun": {
        "usage": "setspronoun <text>",
        "description": "Set server-specific pronouns",
        "example": ".setspronoun He/Him",
        "category": "Server Edit Commands"
    },
    "srotate": {
        "usage": "srotate [command] [options]",
        "description": "Server rotation system",
        "example": ".srotate start",
        "category": "Server Rotate Commands",
        "subcommands": {
            "pfp": "Start rotating server profile pictures",
            "banner": "Start rotating server banners",
            "bio": "Start rotating server bios",
            "pronouns": "Start rotating server pronouns",
            "delay": "Set the delay between rotations",
            "stop": "Stop rotation",
            "status": "Show current rotation status"
        }
    },
    "imgdump": {
        "usage": "imgdump",
        "description": "Dump a user's image",
        "example": ".imgdump",
        "category": "Image Dumping"
    },
    "gifdump": {
        "usage": "gifdump",
        "description": "Dump a user's gif",
        "example": ".gifdump",
        "category": "Image Dumping"
    },
    "movdump": {
        "usage": "movdump",
        "description": "Dump a user's video",
        "example": ".movdump",
        "category": "Image Dumping"
    },
    "mp4dump": {
        "usage": "mp4dump",
        "description": "Dump all videos in a channel",
        "example": ".mp4dump",
        "category": "Image Dumping"
    }       
        }
    def load_themes(self):
        try:
            with open(cfg('themes.json'), 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_themes(self):
        with open(cfg('themes.json'), 'w') as f:
            json.dump(self.user_themes, f, indent=4)

    @commands.command()
    async def theme(self, ctx, color=None):
        if color and not color.startswith('t'):
            color = color.lower()
            valid_colors = {
                "red": red,
                "blue": blue, 
                "cyan": cyan,
                "green": green,
                "yellow": yellow,
                "magenta": magenta
            }
            
            if color not in valid_colors:
                await ctx.send("```ansi\nInvalid theme color. Use .theme to see available options```")
                return
                
            self.user_themes[str(ctx.author.id)] = color
            self.save_themes()
            
            self.default_colors = {
                "text": valid_colors[color],
                "highlight": valid_colors[color], 
                "accent": valid_colors[color]
            }
            
            await ctx.send(f"```ansi\nTheme set to {color}```")
            return

        pages = {
            "t1": f"""```ansi
    Current theme: {self.user_themes.get(str(ctx.author.id), 'default')}
{blue}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    {blue}Blue Theme Example{reset}
    [ {blue}1{reset} ] Void Tools online 
    [ {blue}2{reset} ] Are you a skid ?
    [ {blue}3{reset} ] VOID TOOLS PREMIUM
{blue}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}

    Use {blue}tselect blue{reset} to select this theme
    Page 1/6 - Use t1-t7```""",

            "t2": f"""```ansi
    Current theme: {self.user_themes.get(str(ctx.author.id), 'default')}
{red}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    {red}Red Theme Example{reset}
    [ {red}1{reset} ] Void Tools online 
    [ {red}2{reset} ] Are you a skid ?
    [ {red}3{reset} ] VOID TOOLS PREMIUM
{red}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    Use {red}tselect red{reset} to select this theme
    Page 2/6 - Use t1-t7```""",

            "t3": f"""```ansi
    Current theme: {self.user_themes.get(str(ctx.author.id), 'default')}
{magenta}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    {magenta}Magenta Theme Example{reset}
    [ {magenta}1{reset} ] Void Tools online 
    [ {magenta}2{reset} ] Are you a skid ?
    [ {magenta}3{reset} ] VOID TOOLS PREMIUM
{magenta}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    Use {magenta}tselect magenta{reset} to select this theme
    Page 3/6 - Use t1-t7```""",

            "t4": f"""```ansi
    Current theme: {self.user_themes.get(str(ctx.author.id), 'default')}
{cyan}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    {cyan}Cyan Theme Example{reset}
    [ {cyan}1{reset} ] Void Tools online 
    [ {cyan}2{reset} ] Are you a skid ?
    [ {cyan}3{reset} ] VOID TOOLS PREMIUM
{cyan}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    Use {cyan}tselect cyan{reset} to select this theme
    Page 4/6 - Use t1-t7```""",

            "t5": f"""```ansi
    Current theme: {self.user_themes.get(str(ctx.author.id), 'default')}
{green}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    {green}Green Theme Example{reset}
    [ {green}1{reset} ] Void Tools online 
    [ {green}2{reset} ] Are you a skid ?
    [ {green}3{reset} ] VOID TOOLS PREMIUM
{green}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    Use {green}tselect green{reset} to select this theme
    Page 5/6 - Use t1-t7```""",

            "t6": f"""```ansi
    Current theme: {self.user_themes.get(str(ctx.author.id), 'default')}
{yellow}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    {yellow}Yellow Theme Example{reset}
    [ {yellow}1{reset} ] Void Tools online 
    [ {yellow}2{reset} ] Are you a skid ?
    [ {yellow}3{reset} ] VOID TOOLS PREMIUM
{yellow}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    Use {yellow}tselect yellow{reset} to select this theme
    Page 6/6 - Use t1-t7```""",
            "t7": f"""```ansi
    Current theme: {self.user_themes.get(str(ctx.author.id), 'default')}
    \u001b[35;1m─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    \u001b[35;1mPurple Theme Example{reset}
    [ \u001b[35;1m1{reset} ] Void Tools online 
    [ \u001b[35;1m2{reset} ] Are you a skid ?
    [ \u001b[35;1m3{reset} ] VOID TOOLS PREMIUM
    \u001b[35;1m─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
    Use \u001b[35;1mtselect purple{reset} to select this theme
    Page 7/10 - Use t1-t10```"""
    }
        msg = await ctx.send(pages["t1"])
        self.theme_message = msg

        def check(m):
            return (m.author == ctx.author and 
                    (m.content.startswith('t') and m.content[1:].isdigit() and 
                    1 <= int(m.content[1:]) <= 10) or 
                    m.content.startswith('tselect'))

        while True:
            try:
                user_msg = await ctx.bot.wait_for('message', timeout=20.0, check=check)
                await user_msg.delete() 

                if user_msg.content.startswith('tselect'):
                    parts = user_msg.content.split()
                    if len(parts) < 2: 
                        continue  
                        
                    selected_color = parts[1].lower()
                    if selected_color in ["red", "blue", "magenta", "cyan", "green", "yellow"]:
                        self.user_themes[str(ctx.author.id)] = selected_color
                        self.save_themes()
                        confirm = await ctx.send(f"```ansi\nTheme set to {selected_color}```")
                        await asyncio.sleep(3)
                        await confirm.delete()
                        await self.theme_message.delete()
                        break

                elif user_msg.content.startswith('t'):
                    page_num = f"t{user_msg.content[1]}"
                    if page_num in pages:
                        await self.theme_message.edit(content=pages[page_num])

            except asyncio.TimeoutError:
                print(" Timed out")
                break

    def get_theme_colors(self, user_id):
        theme = self.user_themes.get(str(user_id), None)
        if theme:
            color = globals()[theme]
            return color, color, color
        return (
            self.default_colors["text"],
            self.default_colors["highlight"],
            self.default_colors["accent"],
        )

    def format_menu_page(self, page_num: int, text_color: str, highlight_color: str, accent_color: str) -> str:
        page_data = void_pages.get_page(page_num)
        if page_data is None:
            return None
        if not VIP_ENABLED:
            page_data = {**page_data, "vip": False}
        return void_ui.build_help_page(
            page_num,
            MENU_PAGE_COUNT,
            page_data,
            accent=text_color,
            highlight=highlight_color,
            text=text_color,
        )

    def build_menu_page_message(self, page_num: int, user_id) -> str:
        text_color, highlight_color, accent_color = self.get_theme_colors(user_id)
        return self.format_menu_page(page_num, text_color, highlight_color, accent_color)

    def should_skip_page_command(self, message) -> bool:
        if message.author.id != self.bot.user.id:
            return False
        if message.channel.id not in self.active_help_channels:
            return False
        return parse_help_page_number(message.content) is not None

    async def send_menu_page(self, ctx, page_num: int):
        if void_vip.is_vip_page(page_num) and not void_vip.is_active():
            await ctx.send(void_vip.lock_message(), delete_after=25)
            return
        message_content = self.build_menu_page_message(page_num, ctx.author.id)
        if message_content is None:
            await ctx.send(f"```Page {page_num} invalide. Utilise .p1 a .p{MENU_PAGE_COUNT}```", delete_after=5)
            return
        await ctx.send(message_content)

    @commands.command()
    async def help(self, ctx, command_name: str = None):
        if command_name:
            theme = self.user_themes.get(str(ctx.author.id), None)
            if theme:
                text_color = highlight_color = accent_color = globals()[theme]
            else:
                text_color = self.default_colors["text"]
                highlight_color = self.default_colors["highlight"]
                accent_color = self.default_colors["accent"]

            command_info = self.command_help.get(command_name.lower())
            if command_info:
                text_color, highlight_color, accent_color = self.get_theme_colors(ctx.author.id)
                await ctx.send(
                    void_ui.text_command_help(
                        command_name.lower(),
                        command_info["usage"],
                        command_info["category"],
                        command_info["description"],
                        command_info["example"],
                        accent=accent_color,
                        highlight=highlight_color,
                    )
                )
                return

        text_color, highlight_color, accent_color = self.get_theme_colors(ctx.author.id)
        intro = void_ui.text_main_menu(void_vip.is_active(), BRAND_VERSION, BRAND_NAME, vip_enabled=VIP_ENABLED)
        await ctx.send(intro)
        self.active_help_channels.add(ctx.channel.id)

        def check(message):
            return (
                message.author == ctx.author and
                message.channel.id == ctx.channel.id and
                parse_help_page_number(message.content) is not None
            )

        try:
            while True:
                user_message = await self.bot.wait_for("message", timeout=HELP_TIMEOUT, check=check)
                new_page = parse_help_page_number(user_message.content)
                await self.send_menu_page(ctx, new_page)

                try:
                    await user_message.delete()
                except Exception:
                    pass

        except asyncio.TimeoutError:
            pass
        finally:
            self.active_help_channels.discard(ctx.channel.id)



    @commands.group()
    async def autosnipe(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"```ansi\n{blue}Invalid autosnipe command. Use {red}.autosnipe toggle on/off, .autosnipe custom <message>, .autosnipe clear, or .autosnipe list.```")

    @autosnipe.command()
    async def toggle(self, ctx, option: str):
        channel_id = ctx.channel.id
        if option.lower() not in ["on", "off"]:
            await ctx.send(f"```ansi\n{blue}Invalid Use {red}.autosnipe toggle on or .autosnipe toggle off.")
            return

        if channel_id not in self.auto_snipe_settings:
            self.auto_snipe_settings[channel_id] = {"enabled": False, "custom_message": None}

        self.auto_snipe_settings[channel_id]["enabled"] = option.lower() == "on"
        status = "enabled" if option.lower() == "on" else "disabled"
        await ctx.send(f"```auto snipe is now {status} in this channel.```")

    @autosnipe.command()
    async def custom(self, ctx, *, message: str):
        channel_id = ctx.channel.id
        if channel_id not in self.auto_snipe_settings:
            self.auto_snipe_settings[channel_id] = {"enabled": False, "custom_message": None}

        self.auto_snipe_settings[channel_id]["custom_message"] = message
        await ctx.send(f"```ansi\nauto snipe message set to: {red}{message}```")

    @autosnipe.command()
    async def clear(self, ctx):
        channel_id = ctx.channel.id
        if channel_id in self.auto_snipe_settings:
            self.auto_snipe_settings[channel_id]["custom_message"] = None
            await ctx.send("Custom auto-snipe message cleared.")
        else:
            await ctx.send("```Auto snipe is not set up in this channel.```")

    @autosnipe.command()
    async def list(self, ctx):
        channel_id = ctx.channel.id
        if channel_id in self.auto_snipe_settings:
            settings = self.auto_snipe_settings[channel_id]
            custom_message = settings["custom_message"] or "Default: `,s`"
            status = "enabled" if settings["enabled"] else "disabled"
            await ctx.send(f"```ansi\nAuto snipe status: {red}{status}\n{white}Custom message: {red}{custom_message}```")
        else:
            await ctx.send("```No auto snipe settings found for this channel.```")


    @commands.command()
    async def autocsnipe(self, ctx, action: str, *, content=None):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id

        if guild_id not in self.auto_csnipe_settings:
            self.auto_csnipe_settings[guild_id] = {}

        if channel_id not in self.auto_csnipe_settings[guild_id]:
            self.auto_csnipe_settings[guild_id][channel_id] = {
                "enabled": False,
                "custom_message": ",cs",
                "user_id": ctx.author.id 
            }

        if action == "toggle":
            if content == "on":
                self.auto_csnipe_settings[guild_id][channel_id]["enabled"] = True
                await ctx.send("```auto cs enabled for this channel.```")
            elif content == "off":
                self.auto_csnipe_settings[guild_id][channel_id]["enabled"] = False
                await ctx.send("```auto cs disabled for this channel.```")
            else:
                await ctx.send("```Usage: .autocsnipe toggle on/off```")

        elif action == "custom":
            if content:
                self.auto_csnipe_settings[guild_id][channel_id]["custom_message"] = content
                await ctx.send(f"```auto cs message set to: {content}```")
            else:
                await ctx.send("```Please provide a custom message. Usage: .autocsnipe custom <message>```")

        elif action == "clear":
            self.auto_csnipe_settings[guild_id][channel_id]["custom_message"] = "cs"
            await ctx.send("```auto cs message cleared. Reverted to default: 'cs'```")

        elif action == "list":
            current_settings = self.auto_csnipe_settings[guild_id][channel_id]
            status = "Enabled" if current_settings["enabled"] else "Disabled"
            message = current_settings["custom_message"]
            await ctx.send(f"```auto cs Status: {status}\nCustom Message: {message}```")

        else:
            await ctx.send("```Invalid action. Use toggle, custom, clear, or list.```")


    @commands.command()
    async def clearconfigs(self, ctx):
        confirmation_msg = await ctx.send("```ansi\n Are you sure you want to clear all config files?```")
        await confirmation_msg.add_reaction("✅")
        await confirmation_msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message == confirmation_msg

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10.0, check=check)
            
            if str(reaction.emoji) == "✅":
                config_dir = "configs"
                if not os.path.isdir(config_dir):
                    os.makedirs(config_dir, exist_ok=True)
                for filename in os.listdir(config_dir):
                    if filename.endswith('.json') and filename != "config.json":
                        filepath = os.path.join(config_dir, filename)
                        with open(filepath, 'w') as f:
                            f.write('{}')
                
                main_config = os.path.join(config_dir, "config.json")
                if os.path.exists(main_config):
                    with open(main_config, 'r') as f:
                        existing_config = json.load(f)
                        
                    cleared_config = {key: "" for key in existing_config.keys()}
                    
                    with open(main_config, 'w') as f:
                        json.dump(cleared_config, f, indent=4)
                        
                await ctx.send("```ansi\n All config files have been cleared.```")
            else:
                await ctx.send("```ansi\n Config clear operation cancelled```")

        except TimeoutError:
            await ctx.send("```ansi\n Config clear operation timed out```")

    @commands.command()
    async def shutdown(self, ctx):
        await ctx.send("```ansi\n Shutting down the bot...```")
        await self.bot.close()

    """@commands.Cog.listener()
    async def on_message_delete(self, message):
        channel_id = message.channel.id
        guild_id = message.guild.id
        if channel_id in self.auto_snipe_settings and self.auto_snipe_settings[channel_id]["enabled"]:
            custom_message = self.auto_snipe_settings[channel_id]["custom_message"] or ",s"
            await message.channel.send(custom_message)


        if guild_id in self.auto_csnipe_settings and channel_id in self.auto_csnipe_settings[guild_id]:
            settings = self.auto_csnipe_settings[guild_id][channel_id]


            if settings["enabled"] and message.author.id == settings["user_id"]:
                custom_message = settings["custom_message"]
                await message.channel.send(custom_message)"""

# ========== NOTIFICATIONS ==========
class PingNotification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notifications_enabled = {}
        self.dm_notifications = {}
        self.dm_notifications_enabled = {}
        self.reaction_notifications_enabled = {}

        self.load_data()
        self.loadd_data()
        self.load_reaction_data()

    def loadd_data(self):
        try:
            with open(data('nondm.json'), "r") as f:
                self.dm_notifications = json.load(f)
        except FileNotFoundError:
            self.dm_notifications = {}

    def saves_data(self):
        with open(data('nondm.json'), "w") as f:
            json.dump(self.dm_notifications, f, indent=4)

    def load_data(self):
        try:
            with open(data('nonping.json'), "r") as f:
                self.notifications_enabled = json.load(f)
        except FileNotFoundError:
            self.notifications_enabled = {}

    def save_data(self):
        with open(data('nonping.json'), "w") as f:
            json.dump(self.notifications_enabled, f, indent=4)


    def load_reaction_data(self):
        try:
            with open(data('nonreaction.json'), "r") as f:
                self.reaction_notifications_enabled = json.load(f)
        except FileNotFoundError:
            self.reaction_notifications_enabled = {}

    def save_reaction_data(self):
        with open(data('nonreaction.json'), "w") as f:
            json.dump(self.reaction_notifications_enabled, f, indent=4)




    @commands.group(name="nonping", invoke_without_command=True)
    async def nonping(self, ctx):
        await ctx.send("""```ansi
[ nonping ] Notification system when you are pinged.
    Usage:
        nonping on  - Enable ping notifications.
        nonping off - Disable ping notifications.
        nonping status - Check your notification status.
```""")

    @nonping.command(name="on")
    async def nonping_on(self, ctx):
        user_id = str(ctx.author.id)
        self.notifications_enabled[user_id] = True
        self.save_data()
        await ctx.send(f"```Ping notifications enabled for.```")

    @nonping.command(name="off")
    async def nonping_off(self, ctx):
        user_id = str(ctx.author.id)
        self.notifications_enabled[user_id] = False
        self.save_data()
        await ctx.send(f"```Ping notifications disabled for.```")

    @nonping.command(name="status")
    async def nonping_status(self, ctx):
        user_id = str(ctx.author.id)
        status = self.notifications_enabled.get(user_id, False)
        await ctx.send(
            f"```Ping notifications are {'enabled' if status else 'disabled'}.```"
        )
    @commands.group(name="nondm", invoke_without_command=True)
    async def nondm(self, ctx):
        await ctx.send("""```ansi
[ nondm ] Notification system for direct messages.
    Usage:
        nondm on  - Enable DM notifications.
        nondm off - Disable DM notifications.
        nondm status - Check your DM notification status.
```""")

    @nondm.command(name="on")
    async def nondm_on(self, ctx):
        self.dm_notifications_enabled = True
        await ctx.send(f"```DM notifications enabled globally.```")

    @nondm.command(name="off")
    async def nondm_off(self, ctx):
        self.dm_notifications_enabled = False
        await ctx.send(f"```DM notifications disabled globally.```")

    @nondm.command(name="status")
    async def nondm_status(self, ctx):
        status = "enabled" if self.dm_notifications_enabled else "disabled"
        await ctx.send(f"```DM notifications are currently {status}.```")

    @commands.group(name="nonreaction", invoke_without_command=True)
    async def nonreaction(self, ctx):
        await ctx.send("""```ansi
[ nonreaction ] Notification system for reactions to your messages.
    Usage:
        nonreaction on  - Enable reaction notifications.
        nonreaction off - Disable reaction notifications.
        nonreaction status - Check your reaction notification status.
```""")

    @nonreaction.command(name="on")
    async def nonreaction_on(self, ctx):
        user_id = str(ctx.author.id)
        self.reaction_notifications_enabled[user_id] = True
        self.save_reaction_data()
        await ctx.send(f"```Reaction notifications enabled.```")

    @nonreaction.command(name="off")
    async def nonreaction_off(self, ctx):
        user_id = str(ctx.author.id)
        self.reaction_notifications_enabled[user_id] = False
        self.save_reaction_data()
        await ctx.send(f"```Reaction notifications disabled.```")

    @nonreaction.command(name="status")
    async def nonreaction_status(self, ctx):
        user_id = str(ctx.author.id)
        status = self.reaction_notifications_enabled.get(user_id, False)
        await ctx.send(f"```Reaction notifications are {'enabled' if status else 'disabled'}.```")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return 

        for mentioned_user in message.mentions:
            user_id = str(mentioned_user.id)
            if self.notifications_enabled.get(user_id, False):
                content = message.content or "You were mentioned."
                author_name = message.author.name

                try:
                    notification.notify(
                        title=f"pinged by @{author_name} >.<!",
                        message=content,
                        app_name="Void Tools",
                        timeout=5,
                        app_icon="695eb4bbf96291ef0813969a32fd4776.ico",  
                    )
                except Exception as e:
                    print(f"Failed to send notification: {e}")

        if message.guild is None: 
            if self.dm_notifications_enabled: 
                if message.author.id == self.bot.user.id:
                    return 

                content = message.content or "No content"
                author_name = message.author.name
                try:
                    print(f"Sending DM notification for {author_name}")
                    notification.notify(
                        title=f"@{author_name} dmed you >.< !",
                        message=content,
                        app_name="Void Tools",
                        timeout=5,
                        app_icon="695eb4bbf96291ef0813969a32fd4776.ico"
                    )
                except Exception as e:
                    print(f"Failed to send DM notification: {e}")



    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.id == self.bot.user.id:  
            return
            
        if reaction.message.author.id == self.bot.user.id:
            user_id = str(reaction.message.author.id)
            if not self.reaction_notifications_enabled.get(user_id, False):
                return
                
            content = f"Your message got a reaction from {user.name}!"
            message_author = reaction.message.author.name
            
            try:
                notification.notify(
                    title=f"Reaction from @{message_author} >.<!",
                    message=content,
                    app_name="Void Tools",
                    timeout=5,
                    app_icon="695eb4bbf96291ef0813969a32fd4776.ico"
                )
            except Exception as e:
                print(f"Failed to send notification: {e}")

# ========== TOKEN JOINER ==========
class TokenJoiner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.joined_tokens_lock = threading.Lock()
        self.client = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True
        )
        self.tokens = []
        self.proxies = []
        self.joined_count = 0
        self.not_joined_count = 0
        self.done_event = threading.Event()

    def headers(self, token: str):
        return {
            'authority': 'discord.com',
            'accept': '*/*',
            'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'authorization': token,
            'content-type': 'application/json',
            'origin': 'https://discord.com',
            'referer': 'https://discord.com/channels/@me',
            'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'x-context-properties': 'eyJsb2NhdGlvbiI6IkpvaW4gR3VpbGQiLCJsb2NhdGlvbl9ndWlsZF9pZCI6IjExMDQzNzg1NDMwNzg2Mzc1OTEiLCJsb2NhdGlvbl9jaGFubmVsX2lkIjoiMTEwNzI4NDk3MTkwMDYzMzIzMCIsImxvY2F0aW9uX2NoYW5uZWxfdHlwZSI6MH0=',
            'x-debug-options': 'bugReporterEnabled',
            'x-discord-locale': 'en-GB',
            'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6Iml0LUlUIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExMi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTEyLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjE5MzkwNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbCwiZGVzaWduX2lkIjowfQ=='
        }

    def get_cookies(self):
        cookies = {}
        try:
            response = self.client.get('https://discord.com')
            for cookie in response.cookies:
                if cookie.name.startswith('__') and cookie.name.endswith('uid'):
                    cookies[cookie.name] = cookie.value
            return cookies
        except Exception as e:
            print(f'Failed to obtain cookies ({e})')
            return cookies

    async def accept_invite(self, token: str, invite: str, proxy_: str, status_message):
        try:
            payload = {
                'session_id': ''.join(random.choice(string.ascii_lowercase) + random.choice(string.digits) for _ in range(16))
            }

            proxy = {
                "http": f"http://{proxy_}",
                "https": f"https://{proxy_}"
            } if proxy_ else None

            response = self.client.post(
                url=f'https://discord.com/api/v10/invites/{invite}',
                headers=self.headers(token=token),
                json=payload,
                cookies=self.get_cookies(),
                proxy=proxy
            )
            
            response_json = response.json()
            status_text = ""

            if response.status_code == 200:
                self.joined_count += 1
                status_text = f"Token {token[:10]}... joined successfully"
            else:
                self.not_joined_count += 1
                status_text = f"Token {token[:10]}... failed to join ({response.status_code})"

            await status_message.edit(content=f"```\nJoining progress:\nSuccessful: {self.joined_count}\nFailed: {self.not_joined_count}\nLast action: {status_text}```")

        except Exception as e:
            self.not_joined_count += 1
            await status_message.edit(content=f"```\nError with token {token[:20]}...: {str(e)}```")

        if self.joined_count + self.not_joined_count >= len(self.tokens):
            self.done_event.set()

    def load_tokens(self):
        path = cfg('tokens.txt')
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]

    def load_proxies(self):
        try:
            with open(cfg("proxies.txt"), "r", encoding="utf-8") as file:
                return [line.strip() for line in file if line.strip()]
        except:
            return []

    @commands.command()
    async def tjoin(self, ctx, invite_link: str, token_count: int):

        self.joined_count = 0
        self.not_joined_count = 0
        self.done_event.clear()
        

        invite_code = invite_link.split('/')[-1]
        
        self.tokens = self.load_tokens()[:token_count]
        self.proxies = self.load_proxies()
        
        if not self.tokens:
            await ctx.send("```No tokens found in token.txt```")
            return

        status_message = await ctx.send("```Starting join process...```")
        
        proxy_iter = iter(self.proxies) if self.proxies else iter([None] * len(self.tokens))
        
        tasks = []
        for token in self.tokens:
            proxy = next(proxy_iter, None)
            task = asyncio.create_task(self.accept_invite(token, invite_code, proxy, status_message))
            tasks.append(task)
            await asyncio.sleep(0.5)
        
        await asyncio.gather(*tasks)
        

        await status_message.edit(content=f"```Join process completed:\nSuccessful joins: {self.joined_count}\nFailed joins: {self.not_joined_count}```")

# ========== TOKEN MANAGER ==========
black = "\u001b[30m"
red = "\u001b[31m"
green = "\u001b[32m"
yellow = "\u001b[33m"
blue = "\u001b[34m"
magenta = "\u001b[35m"
cyan = "\u001b[36m"
white = "\u001b[37m"
reset = "\u001b[0m"
pink = "\u001b[38;2;255;192;203m"
light_green = "\u001b[92m"
light_yellow = "\u001b[93m"
light_magenta = "\u001b[95m"
light_cyan = "\u001b[96m"
light_red = "\u001b[91m"
light_blue = "\u001b[94m"

class TokenManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def validate_token(self, token):
        client = discord.Client(intents=discord.Intents.default())
        token_status = {"active": False, "username": None}

        @client.event
        async def on_ready():
            token_status["username"] = f"{client.user.name}#{client.user.discriminator}"
            token_status["active"] = True
            await client.close()

        try:
            await client.start(token, bot=False)
        except discord.errors.LoginFailure:
            return False, "Invalid token"
        except Exception as e:
            return False, f"Error: {str(e)}"

        if token_status["active"]:
            return True, token_status["username"]
        return False, "Failed to validate token"

    @commands.command(name="addtoken")
    async def add_token(self, ctx, token: str):
        try:
            await ctx.message.delete()
        except:
            pass

        token = token.strip()
        
        is_valid, details = await self.validate_token(token)
        
        if is_valid:
            tokens = []
            if os.path.exists(cfg('tokens.txt')):
                with open(cfg('tokens.txt'), 'r') as f:
                    tokens = [t.strip() for t in f.readlines() if t.strip()]
                    
                if token in tokens:
                    await ctx.send(f"```ansi\n{yellow}Token already exists in the file{reset}```", delete_after=5)
                    return

            tokens.append(token)
            
            with open(cfg('tokens.txt'), 'w') as f:
                f.write('\n'.join(tokens))
                if tokens: 
                    f.write('\n')
                    
            await ctx.send(f"```ansi\n{green}Token added successfully User: {details}{reset}```", delete_after=5)
        else:
            await ctx.send(f"```ansi\n{red}Invalid token! Error: {details}{reset}```", delete_after=5)

    @commands.command(name="removetoken")
    async def remove_token(self, ctx, token: str):
        try:
            await ctx.message.delete()
        except:
            pass

        token = token.strip()
        
        if os.path.exists(cfg('tokens.txt')):
            with open(cfg('tokens.txt'), 'r') as f:
                tokens = [t.strip() for t in f.readlines() if t.strip()]
            
            if token in tokens:
                tokens.remove(token)
                with open(cfg('tokens.txt'), 'w') as f:
                    f.write('\n'.join(tokens))
                    if tokens:
                        f.write('\n')
                await ctx.send(f"```ansi\n{green}  Token removed successfully!{reset}```", delete_after=5)
            else:
                await ctx.send(f"```ansi\n{red}  Token not found in the file!{reset}```", delete_after=5)
        else:
            await ctx.send(f"```ansi\n{red}  No token file exists!{reset}```", delete_after=5)

    @commands.command(name="listtokens")
    async def list_tokens(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

        if os.path.exists(cfg('tokens.txt')):
            with open(cfg('tokens.txt'), 'r') as f:
                tokens = [t.strip() for t in f.readlines() if t.strip()]
            
            if tokens:
                tokens_text = f"```ansi\n{cyan}Current tokens:\n" + "\n".join(f"{i+1}. {token}" for i, token in enumerate(tokens)) + f"{reset}```"
                await ctx.send(tokens_text, delete_after=10)
            else:
                await ctx.send(f"```ansi\n{yellow}No tokens found in the file!{reset}```", delete_after=5)
        else:
            await ctx.send(f"```ansi\n{red}  No token file exists!{reset}```", delete_after=5)

    @commands.command(name="cleartoken")
    async def clear_tokens(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

        if os.path.exists(cfg('tokens.txt')):
            with open(cfg('tokens.txt'), 'w') as f:
                f.write('')
            await ctx.send(f"```ansi\n{green}  All tokens have been cleared!{reset}```", delete_after=5)
        else:
            await ctx.send(f"```ansi\n{red}  No token file exists!{reset}```", delete_after=5)

# ========== PC / BROWSER ==========
black = "\033[30m"
red = "\033[31m"
green = "\033[32m"
yellow = "\033[33m"
blue = "\033[34m"
magenta = "\033[35m"
cyan = "\033[36m"
white = "\033[37m"
reset = "\033[0m"  
pink = "\033[38;2;255;192;203m"
white = "\033[37m"
blue = "\033[34m"
black = "\033[30m"
light_green = "\033[92m" 
light_yellow = "\033[93m" 
light_magenta = "\033[95m" 
light_cyan = "\033[96m"  
light_red = "\033[91m"  
light_blue = "\033[94m"  
class BrowserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_screenshot = os.path.join(DATA, "last_screenshot.png")

    def _save_screenshot(self, image) -> str:
        os.makedirs(DATA, exist_ok=True)
        image.save(self.last_screenshot)
        return self.last_screenshot

    @commands.command()
    async def wscreenshot(self, ctx):
        try:
            self._save_screenshot(ImageGrab.grab())
            await ctx.send("```Full screen screenshot captured.```", file=discord.File(self.last_screenshot))
        except Exception as exc:
            await ctx.send(f"```Screenshot failed: {exc}```")

    @commands.command()
    async def pscreenshot(self, ctx):
        try:
            self._save_screenshot(pyautogui.screenshot())
            await ctx.send("```Active window screenshot captured.```", file=discord.File(self.last_screenshot))
        except Exception as exc:
            await ctx.send(f"```Screenshot failed: {exc}```")

    @commands.command()
    async def sendss(self, ctx):
        if not os.path.exists(self.last_screenshot):
            await ctx.send("```No screenshot yet — use .wscreenshot or .pscreenshot first.```")
            return
        await ctx.send("```Last screenshot:```", file=discord.File(self.last_screenshot))

    @commands.command()
    async def openss(self, ctx):
        if not os.path.exists(self.last_screenshot):
            await ctx.send("```No screenshot yet — use .wscreenshot or .pscreenshot first.```")
            return
        if os.name == "nt":
            os.startfile(self.last_screenshot)
        else:
            webbrowser.open(self.last_screenshot)
        await ctx.send("```Opened last screenshot.```")

    @commands.command()
    async def bsearch(self, ctx, *, query: str):
        if platform.system() == "Windows":
            chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
            if not os.path.exists(chrome_path):
                await ctx.send("```ansi\n Google Chrome is not installed on this system.```")
                return
            url = f"https://www.google.com/search?q={query}"
            webbrowser.get(f'"{chrome_path}" %s').open(url)
            await ctx.send(f"```ansi\n {blue}Searching for {query} using Chrome.```")
        else:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            await ctx.send(f"```ansi\n {blue}Searching for {query} using your default browser.```")

    @commands.command()
    async def opencalc(self, ctx):
        if platform.system() == "Windows":
            try:
                subprocess.run('calc')
                await ctx.send(f"```ansi\n {blue}Opened Windows Calculator.```")
            except Exception as e:
                await ctx.send(f"```ansi\n {red}Error opening calculator: {e}```")
        else:
            await ctx.send(f"```{red}ansi\n Calculator is only available on Windows.```")

    @commands.command()
    async def openpad(self, ctx):
        if platform.system() == "Windows":
            try:
                subprocess.run('notepad')
                await ctx.send(f"```ansi\n {blue}Opened Windows Notepad.```")
            except Exception as e:
                await ctx.send(f"```ansi\n {red}Error opening Notepad: {e}```")
        else:
            await ctx.send(f"```ansi\n{red} Notepad is only available on Windows.```")

    @commands.command()
    async def dfolder(self, ctx, *, name: str):
        desktop_path = os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop")
        folder_path = os.path.join(desktop_path, name)

        if os.path.exists(folder_path):
            await ctx.send(f"```ansi\n {red}The folder {blue}{name} {red}already exists.```")
        else:
            try:
                os.makedirs(folder_path)
                await ctx.send(f"```ansi\n {blue}Folder {name} has been created on your Desktop.```")
            except Exception as e:
                await ctx.send(f"```ansi\n {red}Error creating folder: {e}```")

        
    @commands.command()
    async def cleartemp(self, ctx):
        temp_folder = tempfile.gettempdir()
        
        msg = await ctx.send("```Clearing temp folder...```")

        try:
            files = os.listdir(temp_folder)
            total_files = len(files)
            deleted_files = 0

            update_interval = 5

            for filename in files:
                file_path = os.path.join(temp_folder, filename)
                
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                    
                    deleted_files += 1
                    progress = (deleted_files / total_files) * 100

                    if deleted_files % update_interval == 0 or deleted_files == total_files:
                        await msg.edit(content=f"```ansi\n {blue}Clearing temp folder...\n {red}{progress:.2f}% completed.\n {blue}Deleting: {red}{filename}```")

                except Exception as e:
                    print("Error")
                    continue

            await msg.edit(content=f"```ansi\n {blue} Temp folder has been cleared successfully!```")

        except Exception as e:
            await msg.edit(content=f"```ansi\n {red}Error clearing temp folder: {e}```")

    @commands.command()
    async def byoutube(self, ctx, *, search: str):
        try:
            search_query = quote(search)

            youtube_url = f"https://www.youtube.com/results?search_query={search_query}"

            webbrowser.open(youtube_url)

            await ctx.send(f"```ansi\n {blue}YouTube search for {red}{search} {blue}has been opened.```")
        except Exception as e:
            await ctx.send(f"```ansi\n {red}An error occurred: {e}```")

    @commands.command()
    async def btiktok(self, ctx, *, search: str):
        try:
            search_query = quote(search)
            tiktok_url = f"https://www.tiktok.com/search?q={search_query}"
            webbrowser.open(tiktok_url)
            await ctx.send(f"```ansi\n {blue} TikTok search for {red}{search}{blue} has been opened.```")
        except Exception as e:
            await ctx.send(f"```ansi\n {red} An error occurred: {e}```")

    @commands.command()
    async def btwitter(self, ctx, *, search: str):
        try:
            search_query = quote(search)
            twitter_url = f"https://twitter.com/search?q={search_query}"
            webbrowser.open(twitter_url)
            await ctx.send(f"```ansi\n {blue} Twitter search for {red}{search}{blue} has been opened.```")
        except Exception as e:
            await ctx.send(f"```ansi\n {red} An error occurred: {e}```")

    @commands.command()
    async def broblox(self, ctx, *, search: str):
        try:
            search_query = quote(search)
            roblox_url = f"https://www.roblox.com/search/users/?keyword={search_query}"
            webbrowser.open(roblox_url)
            await ctx.send(f"```ansi\n {blue} Roblox search for user {red}{search}{blue} has been opened.```")
        except Exception as e:
            await ctx.send(f"```ansi\n {red} An error occurred: {e}```")

# ========== CORE BOT ==========
def make_console_transparent(transparency=0.7): 
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    style |= win32con.WS_EX_LAYERED
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    
    alpha = int(255 * (1 - transparency))  
    win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, win32con.LWA_ALPHA)

try:
    make_console_transparent(0.3)
except Exception:
    pass
def load_tokens(file_path=cfg('tokens.txt')):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []
tokens = ()
gc_tasks = {}
manual_message_ids = set()
kill_tasks = {}
autoreply_tasks = {}
arm_tasks = {}
outlast_tasks = {}
outlast_running = False
status_changing_task = None
bold_mode = False
cord_user = False
cord_mode = False
autopress_messages = {}
autopress_status = {}
autoreact_users = {}
dreact_users = {} 
autokill_messages = {}
autokill_status = {}

status_messages = [
    f"Void Tools | {VOID_DISCORD}",
    f"Void Tools | {VOID_TELEGRAM}",
    f"Void Tools | {VOID_PROMO_TAG}",
    "Void Tools | .menu",
]

autogc_enabled = False
autoleave_enabled = False 
autosleave_enabled = False
gc_whitelist = set()



def save_whitelist():
    with open(data('gc_whitelist.json'), 'w') as f:
        json.dump(list(gc_whitelist), f)

def load_whitelist():
    global gc_whitelist
    try:
        with open(data('gc_whitelist.json'), 'r') as f:
            gc_whitelist = set(json.load(f))
    except FileNotFoundError:
        gc_whitelist = set()

spamming = False
spam_messages = f"""
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** 
** ** \n\nVoid Tools → {VOID_DISCORD} | {VOID_TELEGRAM}
"""
conversation_flow = [
    ("Hey, what’s up?", "Not much, just contemplating the meaning of life... and snacks."),
    ("You ever think about how weird humans are?", "All the time! Like, why do we put round pizzas in square boxes?"),
    ("I just finished binge-watching a series.", "Which one? Let me guess, it’s about people making bad decisions?"),
    ("I tried cooking the other day.", "How’d that go? Did you end up with a Michelin star or just a smoke alarm?"),
    ("I really need to exercise.", "Same. My couch is starting to feel like my best friend."),
    ("What’s your favorite pizza topping?", "Pineapple. It’s the ultimate rebel topping!"),
    ("Do you believe in aliens?", "Of course! They probably look at us and think, ‘What are they doing?’"),
    ("Why do people always say ‘break a leg’?", "Because that’s how you get a standing ovation!"),
    ("I want to travel the world.", "Me too! But I also want to travel from my bed to the couch."),
    ("Why do we park in driveways and drive on parkways?", "Honestly, that’s the biggest mystery of our time."),
    ("I wish I could teleport.", "Right? Imagine skipping traffic and just appearing at the beach."),
    ("Ever notice how cats act like they own the place?", "Definitely! They’re like furry little dictators."),
    ("Why do we call it ‘rush hour’ when nothing moves?", "It’s basically a time for collective frustration."),
    ("I really need to stop procrastinating.", "Same. I’ve been meaning to do that since 2019."),
    ("What would you do with a million dollars?", "Probably buy a lifetime supply of tacos and regret nothing."),
    ("You got any hidden talents?", "I can eat an entire pizza by myself. Does that count?"),
    ("What’s your spirit animal?", "Definitely a sloth. I live life in the slow lane."),
    ("I love naps.", "Naps are like time travel, but with more drool."),
    ("What’s your favorite childhood memory?", "Sneaking cookies when my parents weren’t looking!"),
    ("Why do we even bother with alarm clocks?", "They’re just tiny robots whose sole purpose is to ruin our dreams."),
    ("I heard laughter is the best medicine.", "That explains why my doctor is a stand-up comedian."),
    ("What’s your go-to karaoke song?", "Anything that lets me scream my feelings out!"),
    ("You think social media is real?", "Of course! Just like unicorns and that guy who claims he can cook."),
    ("What’s your dream job?", "Professional ice cream taster. Who wouldn’t want that?"),
    ("I can’t believe it’s already November.", "I know, right? Time flies when you’re having fun—or when you’re lost on the internet."),
    ("Do you remember when we thought 2020 was going to be the best year ever?", "Yeah, I think we all need a refund for that one."),
    ("What’s your favorite way to waste time?", "Scrolling through memes. It’s basically an art form."),
    ("Why is it so hard to get out of bed?", "Because it’s the ultimate trap of comfort and denial."),
    ("What do you think about online dating?", "It’s like shopping for relationships. Returns not accepted."),
    ("What’s your favorite meme?", "Anything with dogs. They’re just so relatable!"),
    ("Why do I feel like adulting is a scam?", "Because it totally is! Where’s my magical money tree?"),
    ("You ever notice how coffee is just a hug in a mug?", "Absolutely! And without it, I’m basically a zombie."),
    ("What’s the most ridiculous thing you’ve ever done?", "Probably trying to be an adult. What was I thinking?"),
    ("You ever talk to yourself?", "Only when I need expert advice. Turns out I’m not very reliable."),
    ("Why do I feel like everyone on Instagram is a liar?", "Because they are! That’s not a ‘no filter’ face; that’s Photoshop."),
    ("What’s your guilty pleasure?", "Eating an entire pint of ice cream while crying. It’s therapeutic."),
    ("Do you think I could survive in the wild?", "Only if there are drive-thrus and Wi-Fi."),
    ("Why do we have to adult?", "Can’t we just be kids with credit cards?"),
    ("What’s your ideal way to die?", "Laughing while eating pizza. I want my last meal to be glorious."),
    ("Do you ever feel like life is just a video game?", "Totally! I’m just waiting for the cheat codes."),
    ("You think I could get famous on TikTok?", "Only if your life is a continuous fail compilation."),
    ("What’s the weirdest thing you’ve ever eaten?", "That questionable sushi from a gas station. Never again."),
    ("If you could be any fictional character, who would you be?", "Probably the one with the least responsibilities. Hello, Patrick Star!"),
    ("Do you think pets judge us?", "Of course! They’re just better at hiding their judgment."),
    ("What’s your spirit vegetable?", "Definitely a potato. I’m just as versatile, but way less attractive."),
    ("Why do we call it a ‘building’ if it’s already built?", "That’s deep, man. Mind blown."),
    ("Do you ever think about how little we know?", "All the time. Ignorance is bliss, right?"),
    ("Why do people always say ‘YOLO’?", "Because they need a reason to justify their bad decisions."),
    ("What’s your biggest fear?", "Getting caught in a never-ending scroll of TikTok."),
    ("Do you believe in ghosts?", "Of course! They’re just hanging out, judging our life choices."),
    ("What’s the best way to start a Monday?", "With a strong coffee and a weak excuse to call in sick."),
    ("Why do I feel like I’m always late?", "Because time is just a social construct, and I refuse to participate."),
    ("Do you think we’ll ever have flying cars?", "Only if the world is ready for that level of chaos."),
    ("Why do people always say ‘live, laugh, love’?", "Because they need something to put on their wall decor."),
    ("What’s your idea of a perfect weekend?", "Not leaving my house and binge-watching until I forget who I am."),
    ("What’s your go-to excuse for skipping plans?", "I have to wash my hair. Every. Single. Time."),
    ("Do you think aliens are out there?", "Definitely! They’re probably watching us and laughing."),
    ("What’s the most embarrassing thing you’ve done?", "Tried to impress someone and tripped over air. Classic."),
    ("If you could time travel, where would you go?", "Back to when my metabolism was faster."),
    ("Why do they call it ‘fast food’?", "Because waiting in line for 20 minutes feels like eternity."),
    ("What’s your favorite type of humor?", "Sarcasm. It’s the only thing keeping me sane."),
    ("Do you think we’ll ever have robot overlords?", "Only if they promise to keep the Wi-Fi running."),
    ("What’s your favorite conspiracy theory?", "That birds aren’t real. They’re just government drones."),
    ("Ever get that feeling you’re being watched?", "Only when I forget to close the curtains. Thanks, nosy neighbors."),
    ("Why do we always forget where we put our keys?", "Because they’re conspiring against us, obviously."),
    ("What’s the worst haircut you ever had?", "The one that made me look like a confused mushroom."),
    ("Do you think social media is ruining relationships?", "Only if you count comparing your love life to everyone else’s highlight reel."),
    ("What’s your biggest regret?", "Not taking that chance to eat dessert for breakfast."),
    ("Why do we call it ‘adulting’?", "Because ‘faking it till you make it’ sounded too easy."),
    ("What’s your favorite drink?", "Anything with caffeine and a dash of desperation."),
    ("Do you believe in love at first sight?", "Nah, that’s just a trick of the light. It’s called lust."),
    ("Ever had a crush on a fictional character?", "Isn’t that basically a rite of passage?"),
    ("Why do people make fun of dad jokes?", "Because they’re secretly hilarious and we all know it."),
    ("What’s your worst habit?", "Probably not taking my own advice. Who would listen to me anyway?"),
    ("What’s your favorite ice cream flavor?", "Anything with chocolate. I’m basically a chocoholic."),
    ("Why do we even have rules?", "To make breaking them feel more exciting, obviously."),
    ("Do you think we could live without phones?", "Only if we were ready to revert to cave-dwelling."),
    ("What’s your favorite way to chill?", "Ignoring responsibilities while snuggled up with snacks."),
    ("Why is it so hard to find good memes?", "Because the internet is vast, and I’m just one person."),
    ("If you could live anywhere, where would it be?", "Somewhere with endless pizza and no responsibilities."),
    ("Why does adulting feel like a scam?", "Because no one told me I’d have to pay bills for being alive."),
    ("What’s your ultimate comfort food?", "Anything deep-fried. Because health is overrated."),
    ("Do you think we’ll ever find out what cats are thinking?", "Probably not. They’re secretive little ninjas."),
    ("What’s the most random thing you’ve ever Googled?", "‘How to train a cat to do backflips’. It was a dark time."),
    ("Do you believe in karma?", "Definitely! That’s why I’m always nice to pizza delivery people."),
    ("What’s your guilty pleasure song?", "Anything by Justin Bieber. Don’t judge me."),
    ("Why do we call it ‘the great outdoors’?", "Because ‘the place where mosquitoes feast on your blood’ sounds less appealing."),
    ("What’s your idea of a perfect party?", "One where everyone brings snacks and no one judges my dance moves."),
    ("Do you think we’ll ever have a world without hate?", "Only if we can make ‘free pizza for all’ a law."),
    ("What’s the weirdest dream you’ve ever had?", "Something about flying llamas and ice cream. I still don’t understand it."),
    ("Why do we even need sleep?", "To dream of all the pizza we wish we could eat."),
    ("If you could invent something, what would it be?", "A device that makes snacks appear with a button press."),
    ("What’s your favorite quote?", "‘Just keep swimming.’ – Dory. It’s motivational and fishy."),
    ("Do you think people ever change?", "Only if they run out of snacks. Then they become desperate."),
    ("What’s your biggest pet peeve?", "People who chew loudly. It’s a crime against humanity."),
    ("Why do we always forget passwords?", "Because the universe wants us to suffer in silence."),
    ("What’s your favorite movie genre?", "Anything with explosions and questionable plot lines."),
    ("Do you believe in fate?", "Only when it leads to free food. Then it’s definitely destiny."),
    ("What’s your ideal vacation?", "Somewhere with sun, sand, and no responsibilities."),
    ("Do you think we’ll ever colonize Mars?", "Only if they have Wi-Fi and good pizza delivery."),
    ("What’s the most absurd thing you’ve ever heard?", "Someone said they don’t like pizza. How is that even possible?"),
    ("Why do we even have rules for grammar?", "To make writing more complicated than it needs to be."),
    ("What’s your go-to excuse for being late?", "‘Traffic was terrible!’ works every time, trust me."),
    ("If you could have any superpower, what would it be?", "The power to eat pizza without gaining weight."),
    ("Why do we need friends?", "To validate our terrible decisions and share snacks."),
    ("What’s the funniest thing you’ve ever seen?", "A cat trying to catch its tail. Pure comedy gold."),
    ("Do you think we’ll ever figure out what life is all about?", "Probably not. We’re all just winging it."),
    ("What’s your worst habit?", "Procrastinating until the last minute. It’s an art form."),
    ("What’s your favorite way to celebrate?", "Eating cake. It’s the only acceptable excuse for gluttony."),
    ("Why do we need breaks?", "To recharge and pretend we’re working hard."),
    ("What’s the most ridiculous trend you’ve seen?", "That one where people wore socks with sandals. Like, why?"),
    ("Do you think we’ll ever find a cure for boredom?", "Probably not. We’re destined to be bored forever."),
    ("What’s your ultimate dream?", "To live in a world where calories don’t count."),
    ("Why do people say ‘money can’t buy happiness’?", "Because they’ve never had an unlimited pizza budget."),
    ("What’s your secret talent?", "I can eat an entire pizza by myself. I’m basically a champion."),
    ("Do you think we’ll ever have peace on Earth?", "Only if we make pizza the universal currency."),
    ("What’s your favorite way to relax?", "Binge-watching anything that distracts me from life."),
    ("Why do we even have weekends?", "To recuperate from the chaos of weekdays. It’s a cruel cycle."),
    ("What’s your biggest dream?", "To have a never-ending supply of pizza and Netflix."),
    ("Do you think we’ll ever understand women?", "Only if we start taking notes. Seriously."),
    ("What’s your favorite type of weather?", "Anything that lets me stay indoors without guilt."),
    ("Why do we even have chores?", "To remind us that adulthood is a scam."),
    ("What’s your favorite thing to do when you’re bored?", "Start a deep dive into the rabbit hole of YouTube."),
    ("Do you think aliens would find us fascinating?", "Probably! They’d be like, ‘What are they doing with their lives?’"),
    ("What’s the most absurd thing you’ve ever done?", "Attempted to cook while following a Pinterest recipe. Spoiler: It was a disaster."),
    ("Why do people complain about Mondays?", "Because they just want to sleep in and ignore responsibilities."),
    ("What’s your biggest pet peeve?", "When people don’t return my Tupperware. It’s like they’ve stolen a piece of my soul."),
    ("What’s your idea of a perfect day?", "Waking up to pizza and realizing it’s a holiday."),
    ("Do you believe in ghosts?", "Definitely! They’re just hanging around, judging our life choices."),
    ("What’s your go-to drink?", "Anything that’s caffeinated and potentially life-saving."),
    ("What’s your favorite conspiracy theory?", "That the government is secretly run by cats. It explains everything."),
    ("Why do we even need rules?", "To make breaking them feel like an exciting adventure."),
    ("What’s your secret to happiness?", "Pizza. Lots and lots of pizza."),
    ("Do you think we’ll ever discover the meaning of life?", "Probably not. We’re just here for the pizza."),
    ("What’s your favorite thing about being an adult?", "Nothing. I prefer the simplicity of childhood."),
    ("Why do we have to deal with adult problems?", "Because we made bad life choices in our youth."),
    ("What’s your ultimate goal in life?", "To be able to eat pizza guilt-free every day."),
    ("Do you think life is unfair?", "Absolutely! Pizza should be a basic human right."),
    ("What’s the weirdest thing you’ve ever eaten?", "That questionable mystery meat at school lunch. Never again."),
    ("Why do we even bother with social norms?", "To make life more complicated than it needs to be."),
    ("What’s your favorite way to unwind?", "Eating snacks while scrolling through my phone."),
    ("Do you think we’ll ever live in harmony?", "Only if pizza is involved in the peace treaty."),
    ("What’s your favorite way to spend a rainy day?", "Cuddled up with pizza and a good movie."),
    ("Why do we need dreams?", "To escape the harsh reality of our lives, even if just for a moment."),
    ("What’s your biggest insecurity?", "That I’ll never find pizza that’s good enough."),
    ("Do you think we’ll ever figure out the meaning of love?", "Only if it’s pizza-related. Then we might have a chance."),
    ("What’s your go-to karaoke song?", "Anything that lets me belt out my feelings."),
    ("Why do we call it ‘fast food’?", "Because waiting in line for an hour feels like a lifetime."),
    ("What’s the most embarrassing thing you’ve done in public?", "Tripped over nothing and looked like a fool. Classic."),
    ("Do you think we’ll ever have a world without stress?", "Only if we live on a tropical island with unlimited pizza."),
    ("What’s your secret for a happy life?", "Always have snacks on hand and never forget the pizza."),
    ("Why do we even bother trying?", "Because we have to keep pretending we know what we’re doing."),
    ("What’s your biggest dream?", "To find a magical place where pizza never runs out."),
    ("Do you think we’ll ever have robots that do everything for us?", "Only if they come equipped with a pizza function."),
    ("What’s your ultimate fantasy?", "Living in a world where calories don’t exist."),
    ("Why do we even need friends?", "To share snacks and validate our questionable life choices."),
    ("What’s your favorite way to be lazy?", "Binge-watching shows while lying on the couch."),
    ("Do you think we’ll ever achieve world peace?", "Only if pizza becomes the universal currency."),
    ("What’s your biggest fear?", "Running out of snacks during a Netflix marathon."),
    ("Why do we have to deal with adult problems?", "Because we didn’t take our childhood seriously."),
    ("What’s your favorite childhood memory?", "Sneaking cookies when no one was looking."),
    ("Do you think we’ll ever find a cure for boredom?", "Only if it involves unlimited pizza and Netflix."),
    ("What’s the funniest thing you’ve ever seen?", "A cat trying to catch its tail. Instant comedy gold."),
    ("Why do we call it ‘fast food’?", "Because waiting 20 minutes for a burger feels like forever."),
    ("What’s your ultimate dream job?", "Professional pizza taster. It’s basically my calling."),
    ("Do you think we’ll ever understand women?", "Only if we start taking notes and paying attention."),
    ("What’s your idea of a perfect party?", "One where everyone brings pizza and we laugh until we cry."),
    ("Why do we even bother with relationships?", "To have someone to blame for our bad life choices."),
    ("What’s your favorite ice cream flavor?", "Anything that’s cold, creamy, and full of chocolate."),
    ("Do you believe in love at first sight?", "Only if pizza is involved. Then it’s definitely true."),
    ("What’s your favorite way to express yourself?", "Through pizza-themed memes and questionable dance moves."),
    ("Why do we even have to work?", "To afford our pizza addiction, of course."),
    ("What’s the most absurd thing you’ve ever heard?", "Someone said they don’t like pizza. Unbelievable!"),
    ("Why do we even bother trying to understand life?", "Because pizza makes everything better, even confusion."),
    ("What’s your secret to happiness?", "Pizza. Lots and lots of pizza."),
    ("Do you think we’ll ever understand why we exist?", "Only if it involves pizza. Then we might have a shot."),
    ("What’s your favorite way to spend a Saturday?", "Cuddled up with pizza and a movie marathon."),
    ("Do you think aliens exist?", "Definitely! They’re probably watching us eat pizza."),
    ("What’s your idea of a perfect vacation?", "Sitting on a beach with pizza and no responsibilities."),
    ("Do you think we’ll ever figure out the meaning of happiness?", "Only if it leads to pizza. Then we might be on to something."),
    ("What’s your biggest regret?", "Not eating enough pizza in my life."),
    ("What’s your ultimate goal?", "To become a pizza connoisseur and travel the world eating pizza."),
    ("Do you think we’ll ever understand what it means to be human?", "Only if pizza is part of the definition."),
    ("What’s your favorite childhood TV show?", "Anything that had snacks as a central theme."),
    ("Why do we even have to face our fears?", "To eat pizza afterward as a reward."),
    ("What’s your secret talent?", "I can eat an entire pizza in one sitting. It’s a gift."),
    ("Do you think we’ll ever find out what makes us happy?", "Only if it involves pizza. Then we’ll have a clue."),
    ("What’s your favorite way to cope with stress?", "Pizza. Always pizza."),
    ("What’s your ultimate fantasy?", "Living in a world where pizza is the only food group."),
    ("Why do we even need to learn?", "To know how to make the perfect pizza, obviously."),
    ("What’s your favorite thing about your job?", "Eating pizza during lunch breaks."),
    ("Do you think we’ll ever achieve total world peace?", "Only if pizza is the solution."),
    ("What’s your biggest struggle?", "Choosing between too many pizza toppings."),
    ("What’s your favorite guilty pleasure?", "Binge-watching cheesy reality TV while eating pizza."),
    ("Why do we even have to deal with disappointment?", "So we can appreciate pizza even more."),
    ("What’s your ultimate dream?", "To open a pizza shop that never closes."),
    ("Do you believe in love?", "Only if it involves pizza. Then it’s real."),
    ("What’s your idea of a perfect night out?", "Dinner at a pizza place followed by a movie marathon."),
    ("What’s your secret to staying motivated?", "Pizza. Always pizza."),
    ("Why do we even have to deal with heartbreak?", "To remind us that pizza will always be there for us."),
    ("What’s your favorite thing about fall?", "Pumpkin spice lattes and the promise of pizza season."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your biggest challenge?", "Resisting the urge to eat pizza at all times."),
    ("What’s your favorite thing to do with friends?", "Pizza parties and movie marathons."),
    ("Why do we even have to deal with loss?", "So we can appreciate pizza even more."),
    ("What’s your ultimate goal in life?", "To eat pizza in every country."),
    ("Do you think we’ll ever find the meaning of love?", "Only if it’s pizza-related. Then we might have a shot."),
    ("What’s your idea of a perfect date?", "Pizza and a cozy movie night."),
    ("Why do we even bother trying?", "Because pizza makes it worth it."),
    ("What’s your biggest wish?", "To have pizza as the only food option."),
    ("Do you think we’ll ever live in harmony?", "Only if pizza is involved in the peace treaty."),
    ("What’s your favorite thing about winter?", "Hot chocolate and pizza by the fire."),
    ("What’s your biggest regret in life?", "Not eating more pizza when I had the chance."),
    ("What’s your ultimate dream job?", "Pizza taster, obviously."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your idea of a perfect Saturday?", "Cuddled up with pizza and my favorite show."),
    ("What’s your biggest fear?", "Running out of pizza during a movie marathon."),
    ("Why do we even have to deal with disappointment?", "So we can appreciate pizza even more."),
    ("What’s your favorite thing about being single?", "Unlimited pizza and no sharing."),
    ("Do you think we’ll ever find the meaning of life?", "Only if it involves pizza."),
    ("What’s your idea of a perfect family gathering?", "Pizza and laughter until we cry."),
    ("Why do we even have to deal with stress?", "To remind us that pizza is the answer."),
    ("What’s your favorite way to celebrate an achievement?", "Pizza party, obviously."),
    ("What’s your biggest pet peeve about social media?", "When people post photos of their food, but it’s not pizza."),
    ("Do you think we’ll ever figure out what makes us happy?", "Only if it’s pizza-related."),
    ("What’s your ultimate dream vacation?", "Eating pizza in every country."),
    ("Why do we even have to face challenges?", "So we can appreciate pizza even more."),
    ("What’s your biggest wish for the future?", "To live in a world where pizza is the only food."),
    ("What’s your idea of a perfect evening?", "Pizza and a good movie."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your favorite childhood memory?", "Eating pizza with friends."),
    ("What’s your biggest struggle in life?", "Choosing between too many pizza toppings."),
    ("What’s your ultimate goal in life?", "To eat pizza in every country."),
    ("Do you think we’ll ever figure out what it means to be human?", "Only if pizza is part of the definition."),
    ("What’s your favorite way to spend a lazy day?", "Binge-watching shows with pizza."),
    ("What’s your biggest regret?", "Not eating enough pizza in my life."),
    ("Do you think we’ll ever find the secret to true happiness?", "Only if it involves pizza."),
    ("What’s your favorite way to unwind?", "Pizza and Netflix."),
    ("What’s your ultimate dream?", "To open a pizza shop that never closes."),
    ("Why do we even have to deal with adult problems?", "Because we made bad life choices."),
    ("What’s your biggest fear?", "Running out of pizza during a movie marathon."),
    ("What’s your idea of a perfect Saturday?", "Cuddled up with pizza and a movie marathon."),
    ("Do you think we’ll ever achieve total world peace?", "Only if pizza becomes the universal currency."),
    ("What’s your ultimate fantasy?", "Living in a world where pizza is the only food group."),
    ("What’s your favorite childhood TV show?", "Anything that had snacks as a central theme."),
    ("Why do we even bother with relationships?", "To have someone to blame for our bad life choices."),
    ("What’s your biggest insecurity?", "That I’ll never find pizza that’s good enough."),
    ("Do you think we’ll ever figure out what makes us happy?", "Only if it involves pizza."),
    ("What’s your go-to comfort food?", "Pizza, obviously."),
    ("What’s your idea of a perfect vacation?", "Sitting on a beach with pizza and no responsibilities."),
    ("Why do we even have to face our fears?", "To eat pizza afterward as a reward."),
    ("What’s your biggest dream?", "To find a magical place where pizza never runs out."),
    ("Do you think we’ll ever find the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your favorite way to cope with stress?", "Pizza. Always pizza."),
    ("Why do we even bother trying to understand life?", "Because pizza makes everything better, even confusion."),
    ("What’s your ultimate goal?", "To become a pizza connoisseur and travel the world eating pizza."),
    ("What’s your idea of a perfect date?", "Pizza and a cozy movie night."),
    ("Why do we even have to deal with heartbreak?", "To remind us that pizza will always be there for us."),
    ("What’s your favorite thing about fall?", "Pumpkin spice lattes and the promise of pizza season."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your biggest challenge?", "Resisting the urge to eat pizza at all times."),
    ("What’s your favorite way to be lazy?", "Binge-watching shows while lying on the couch."),
    ("Do you think we’ll ever live in harmony?", "Only if pizza is involved in the peace treaty."),
    ("What’s your favorite way to spend a rainy day?", "Cuddled up with pizza and a good movie."),
    ("Why do we need dreams?", "To escape the harsh reality of our lives, even if just for a moment."),
    ("What’s your biggest insecurity?", "That I’ll never find pizza that’s good enough."),
    ("What’s your favorite guilty pleasure?", "Binge-watching cheesy reality TV while eating pizza."),
    ("What’s your idea of a perfect night out?", "Dinner at a pizza place followed by a movie marathon."),
    ("What’s your ultimate dream job?", "Pizza taster, obviously."),
    ("Why do we even need to learn?", "To know how to make the perfect pizza, obviously."),
    ("What’s your secret to staying motivated?", "Pizza. Always pizza."),
    ("What’s your biggest wish?", "To have pizza as the only food option."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your favorite way to celebrate an achievement?", "Pizza party, obviously."),
    ("What’s your idea of a perfect family gathering?", "Pizza and laughter until we cry."),
    ("Why do we even have to deal with disappointment?", "So we can appreciate pizza even more."),
    ("What’s your ultimate dream vacation?", "Eating pizza in every country."),
    ("What’s your biggest pet peeve about social media?", "When people post photos of their food, but it’s not pizza."),
    ("What’s your ultimate goal in life?", "To eat pizza in every country."),
    ("Do you think we’ll ever find the meaning of love?", "Only if it’s pizza-related. Then we might have a shot."),
    ("What’s your biggest regret?", "Not eating more pizza when I had the chance."),
    ("What’s your favorite thing about being single?", "Unlimited pizza and no sharing."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your idea of a perfect evening?", "Pizza and a good movie."),
    ("Why do we even bother trying?", "Because pizza makes it worth it."),
    ("What’s your biggest fear?", "Running out of pizza during a movie marathon."),
    ("Do you think we’ll ever find out what makes us happy?", "Only if it’s pizza-related."),
    ("What’s your favorite thing to do with friends?", "Pizza parties and movie marathons."),
    ("What’s your biggest wish for the future?", "To live in a world where pizza is the only food."),
    ("What’s your ultimate fantasy?", "Living in a world where pizza is the only food group."),
    ("What’s your idea of a perfect Saturday?", "Cuddled up with pizza and a movie marathon."),
    ("What’s your biggest struggle in life?", "Choosing between too many pizza toppings."),
    ("Do you think we’ll ever figure out what it means to be human?", "Only if pizza is part of the definition."),
    ("What’s your favorite childhood memory?", "Eating pizza with friends."),
    ("What’s your idea of a perfect date?", "Pizza and a cozy movie night."),
    ("Why do we even bother with relationships?", "To have someone to blame for our bad life choices."),
    ("What’s your biggest regret?", "Not eating more pizza when I had the chance."),
    ("What’s your ultimate goal in life?", "To eat pizza in every country."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your go-to comfort food?", "Pizza, obviously."),
    ("What’s your idea of a perfect vacation?", "Sitting on a beach with pizza and no responsibilities."),
    ("Why do we even have to face our fears?", "To eat pizza afterward as a reward."),
    ("What’s your biggest dream?", "To find a magical place where pizza never runs out."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your favorite way to cope with stress?", "Pizza. Always pizza."),
    ("Why do we even bother trying to understand life?", "Because pizza makes everything better, even confusion."),
    ("What’s your ultimate goal?", "To become a pizza connoisseur and travel the world eating pizza."),
    ("What’s your idea of a perfect date?", "Pizza and a cozy movie night."),
    ("Why do we even have to deal with heartbreak?", "To remind us that pizza will always be there for us."),
    ("What’s your favorite thing about fall?", "Pumpkin spice lattes and the promise of pizza season."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your biggest challenge?", "Resisting the urge to eat pizza at all times."),
    ("What’s your favorite way to be lazy?", "Binge-watching shows while lying on the couch."),
    ("Do you think we’ll ever live in harmony?", "Only if pizza is involved in the peace treaty."),
    ("What’s your favorite way to spend a rainy day?", "Cuddled up with pizza and a good movie."),
    ("Why do we need dreams?", "To escape the harsh reality of our lives, even if just for a moment."),
    ("What’s your biggest insecurity?", "That I’ll never find pizza that’s good enough."),
    ("What’s your favorite guilty pleasure?", "Binge-watching cheesy reality TV while eating pizza."),
    ("What’s your idea of a perfect night out?", "Dinner at a pizza place followed by a movie marathon."),
    ("What’s your ultimate dream job?", "Pizza taster, obviously."),
    ("Why do we even need to learn?", "To know how to make the perfect pizza, obviously."),
    ("What’s your secret to staying motivated?", "Pizza. Always pizza."),
    ("What’s your biggest wish?", "To have pizza as the only food option."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your favorite way to celebrate an achievement?", "Pizza party, obviously."),
    ("What’s your idea of a perfect family gathering?", "Pizza and laughter until we cry."),
    ("Why do we even have to deal with disappointment?", "So we can appreciate pizza even more."),
    ("What’s your ultimate dream vacation?", "Eating pizza in every country."),
    ("What’s your biggest pet peeve about social media?", "When people post photos of their food, but it’s not pizza."),
    ("What’s your ultimate goal in life?", "To eat pizza in every country."),
    ("Do you think we’ll ever find the meaning of love?", "Only if it’s pizza-related. Then we might have a shot."),
    ("What’s your biggest regret?", "Not eating more pizza when I had the chance."),
    ("What’s your favorite thing about being single?", "Unlimited pizza and no sharing."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your idea of a perfect evening?", "Pizza and a good movie."),
    ("Why do we even bother trying?", "Because pizza makes it worth it."),
    ("What’s your biggest fear?", "Running out of pizza during a movie marathon."),
    ("Do you think we’ll ever find out what makes us happy?", "Only if it’s pizza-related."),
    ("What’s your favorite thing to do with friends?", "Pizza parties and movie marathons."),
    ("What’s your biggest wish for the future?", "To live in a world where pizza is the only food."),
    ("What’s your ultimate fantasy?", "Living in a world where pizza is the only food group."),
    ("What’s your idea of a perfect Saturday?", "Cuddled up with pizza and a movie marathon."),
    ("What’s your biggest struggle in life?", "Choosing between too many pizza toppings."),
    ("Do you think we’ll ever figure out what it means to be human?", "Only if pizza is part of the definition."),
    ("What’s your favorite childhood memory?", "Eating pizza with friends."),
    ("What’s your idea of a perfect date?", "Pizza and a cozy movie night."),
    ("Why do we even bother with relationships?", "To have someone to blame for our bad life choices."),
    ("What’s your biggest regret?", "Not eating more pizza when I had the chance."),
    ("What’s your ultimate goal in life?", "To eat pizza in every country."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your go-to comfort food?", "Pizza, obviously."),
    ("What’s your idea of a perfect vacation?", "Sitting on a beach with pizza and no responsibilities."),
    ("Why do we even have to face our fears?", "To eat pizza afterward as a reward."),
    ("What’s your biggest dream?", "To find a magical place where pizza never runs out."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your favorite way to cope with stress?", "Pizza. Always pizza."),
    ("Why do we even bother trying to understand life?", "Because pizza makes everything better, even confusion."),
    ("What’s your ultimate goal?", "To become a pizza connoisseur and travel the world eating pizza."),
    ("What’s your idea of a perfect date?", "Pizza and a cozy movie night."),
    ("Why do we even have to deal with heartbreak?", "To remind us that pizza will always be there for us."),
    ("What’s your favorite thing about fall?", "Pumpkin spice lattes and the promise of pizza season."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your biggest challenge?", "Resisting the urge to eat pizza at all times."),
    ("What’s your favorite way to be lazy?", "Binge-watching shows while lying on the couch."),
    ("Do you think we’ll ever live in harmony?", "Only if pizza is involved in the peace treaty."),
    ("What’s your favorite way to spend a rainy day?", "Cuddled up with pizza and a good movie."),
    ("Why do we need dreams?", "To escape the harsh reality of our lives, even if just for a moment."),
    ("What’s your biggest insecurity?", "That I’ll never find pizza that’s good enough."),
    ("What’s your biggest wish for the future?", "To live in a world where pizza is the only food."),
    ("What’s your ultimate goal in life?", "To eat pizza in every country."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it involves pizza."),
    ("What’s your idea of a perfect date?", "Pizza and a cozy movie night."),
    ("Why do we even have to deal with heartbreak?", "To remind us that pizza will always be there for us."),
    ("What’s your favorite thing about fall?", "Pumpkin spice lattes and the promise of pizza season."),
    ("Do you think we’ll ever discover the secret to happiness?", "Only if it’s pizza-related."),
    ("What’s your biggest challenge?", "Resisting the urge to eat pizza at all times."),
    ("What’s your favorite way to be lazy?", "Binge-watching shows while lying on the couch."),
    ("Do you think we’ll ever live in harmony?", "Only if pizza is involved in the peace treaty."),
    ("What’s your favorite way to spend a rainy day?", "Cuddled up with pizza and a good movie."),
    ("Why do we need dreams?", "To escape the harsh reality of our lives, even if just for a moment."),
    ("What’s your biggest insecurity?", "That I’ll never find pizza that’s good enough."),
]

conversation_flows = [
    ("yo ngl im horny asf", "same but my bf is sleep :("),
    ("yo should i go kill birds for fun?!", "NIGGA ARE YOU FUCKING CRAZY?"),
    ("yo this nigga above me is a pedophile", "lets act like it was me above you.."),
    ("i miss my bf", "no one gaf bitch"),
    ("yo my house just got raided", "shouldnt of been fucking on little kids :skull:"),
    ("YIM HUNGRY ASF", "yeah we know....."),
    ("yo why is my ex still texting me?", "cuz they miss the best thing that ever happened to them."),
    ("i just got dumped", "congrats, you’re free to be miserable alone now!"),
    ("im in jail lol", "guess you can’t say you’re bored now, huh?"),
    ("i cant sleep", "maybe if you stopped scrolling through your ex's posts..."),
    ("i hate my job", "quit, then cry about it later."),
    ("my life is a mess", "at least it’s entertaining for us."),
    ("why do people think im weird?", "because you are."),
    ("my crush doesn't like me back", "join the club, we're accepting new members."),
    ("i just found out my friend is a liar", "that's rich coming from you."),
    ("my cat just knocked over my drink", "sounds like it hates you."),
    ("im broke asf", "welcome to the club, we have hoodies."),
    ("my parents are annoying", "that’s just them being parents."),
    ("why does everyone hate me?", "maybe take a look in the mirror."),
    ("im so tired of life", "just wait until you get older; it only gets worse."),
    ("i have no friends", "because you scare everyone away."),
    ("school is dumb", "it’s training for real life—more dumb stuff."),
    ("i need to lose weight", "start by cutting the toxic people out of your life."),
    ("i can’t find my phone", "check your hand; it’s usually there."),
    ("i have no motivation", "just fake it till you make it."),
    ("my life is boring", "get a hobby or some drama, your choice."),
    ("i keep messing up", "some people are just destined to fail."),
    ("my dog hates me", "maybe it’s just tired of your drama."),
    ("im lonely", "get a dog; they don’t judge."),
    ("i want to be famous", "good luck, you need talent for that."),
    ("my friends are fake", "maybe they’re just reflecting your energy."),
    ("i hate socializing", "then why are you complaining about being alone?"),
    ("i have trust issues", "you shouldn't; nobody wants your secrets."),
    ("im scared of commitment", "that's why you're alone."),
    ("i just want to sleep all day", "we all do, but bills don’t pay themselves."),
    ("i feel like a failure", "join the club, membership is free."),
    ("my phone battery is dying", "sounds like your social life."),
    ("i think my partner is cheating", "welcome to paranoia 101."),
    ("im always broke", "maybe stop buying useless crap."),
    ("i wish i could disappear", "then do it, you’ll get attention."),
    ("my ex is dating someone else", "good, they deserve each other."),
    ("i can't take this anymore", "then don't. Make a change."),
    ("im sick of this drama", "then get off social media."),
    ("i can't believe i got ghosted", "happens to the best of us, deal with it."),
    ("why is everyone so fake?", "because they’re scared of being real."),
    ("im just here for the snacks", "and that’s why we love you."),
    ("i wish i was more confident", "then stop being a coward."),
    ("i just want to be happy", "stop expecting it to come to you."),
    ("why does life suck?", "it doesn’t; you just make it suck."),
    ("my crush is dating someone else", "and you thought you had a chance?"),
    ("i need a vacation", "from your own life, huh?"),
    ("i can’t believe they said that", "you can’t change what others think."),
    ("i’m always tired", "maybe stop staying up all night."),
    ("i can’t cook", "that’s what takeout is for."),
    ("why is dating so hard?", "maybe you should lower your standards."),
    ("i have too many regrets", "welcome to adulthood."),
    ("i’m scared of change", "change is the only constant; get used to it."),
    ("my friends don’t support me", "maybe because you don’t support them."),
    ("i miss the good old days", "they weren’t that good; you just remember them that way."),
    ("i’m too busy for friends", "then you’re too busy for fun."),
    ("everyone is so judgmental", "maybe because you give them something to judge."),
    ("i feel like giving up", "then just do it; nobody will notice."),
    ("why am i always the last to know?", "because you don’t pay attention."),
    ("my partner is so annoying", "then why are you still with them?"),
    ("i want to be a millionaire", "start by budgeting your current money."),
    ("i can’t find love", "you can’t find it if you’re looking for it."),
    ("i hate when people ignore me", "maybe try being less annoying."),
    ("i have no idea what to do with my life", "that’s your problem, not ours."),
    ("why can’t i get a break?", "because life isn’t fair."),
    ("i want to travel the world", "and you expect that to happen when?"),
    ("everyone is so fake these days", "maybe you’re just too real for them."),
    ("i feel so empty", "good, you might need a reset."),
    ("my family is so toxic", "and you still hang around them?"),
    ("why can’t i stick to a plan?", "because you lack discipline."),
    ("im tired of waiting", "then do something about it."),
    ("i can’t believe this is my life", "then change it; nobody else will."),
    ("why is everyone so sensitive?", "because they care about their feelings."),
    ("my dreams are unrealistic", "that’s why they’re called dreams."),
    ("i’m too shy to talk to anyone", "then don’t complain about being alone."),
    ("i hate my face", "then stop looking in the mirror."),
    ("i want to give up", "good, less competition for the rest of us."),
    ("im always in my head", "maybe stop overthinking everything."),
    ("i can’t handle this pressure", "welcome to adulting; it’s not easy."),
    ("i just want to be understood", "maybe try expressing yourself better."),
    ("my plans keep falling through", "that’s life; adapt."),
    ("im so bored", "then go do something; anything."),
    ("i feel like nobody cares", "that’s because you’re not that interesting."),
        ("why the fuck can't I catch a break?", "because life is a bitch, and so are you."),
    ("my friends are so fucking fake", "welcome to the club; everyone is a fraud."),
    ("i just got fired, fuck my life", "should’ve done your job instead of slacking off."),
    ("im tired of this shit", "then stop whining and do something."),
    ("why do i bother with these idiots?", "because you secretly love the drama."),
    ("everyone is pissing me off", "maybe it’s you that’s the problem."),
    ("i’m sick of my family’s bullshit", "then move the fuck out already."),
    ("im broke as hell", "stop wasting money on dumb shit."),
    ("i can't stand my coworkers", "just wait till you have to find new ones."),
    ("i want to punch my ex in the face", "at least it would be more fun than your breakup."),
    ("im always fucking tired", "maybe if you didn't stay up all night scrolling."),
    ("my life is a complete disaster", "join the fucking club; we meet on Wednesdays."),
    ("i hate everyone", "but you still hang around them, don’t you?"),
    ("i can't believe i trusted them", "that's on you for being so naive."),
    ("im just here for the drama", "because your life is too boring without it."),
    ("i want to disappear", "go ahead; nobody will miss your whiny ass."),
    ("why does everyone else get what they want?", "because they’re not sitting around crying like you."),
    ("im sick of playing nice", "then stop pretending to be something you're not."),
    ("i can't handle this shit anymore", "then just fucking quit; it’s that simple."),
    ("why do people keep lying to me?", "because you’re an easy target."),
    ("my life is a never-ending shitshow", "welcome to the real world."),
    ("i can't believe they ghosted me", "guess they couldn’t stand your bullshit."),
    ("i feel like a total loser", "that’s because you are."),
    ("im tired of being the nice one", "then stop being a doormat."),
    ("why can't i find someone decent?", "because decent people avoid your vibe."),
    ("im always getting hurt", "maybe stop trusting assholes."),
    ("my crush is dating someone else", "tough luck, you should’ve made a move."),
    ("i miss the good times", "they weren’t that great; you’re just reminiscing."),
    ("everyone is so fucking annoying", "and you’re not part of the problem?"),
    ("i can't believe how stupid i am", "well, at least you know it."),
    ("i feel like a burden", "because you are one."),
    ("im done with this shit", "then do something about it, stop whining."),
    ("my life is a joke", "and you're the punchline."),
    ("i wish people would just be real", "good luck finding that unicorn."),
    ("why do i keep screwing up?", "because you're a screw-up, deal with it."),
    ("i’m always the one to apologize", "stop being a fucking pushover."),
    ("everyone always leaves me", "because you’re exhausting."),
    ("i hate that bitch", "join the line, we all do."),
    ("im too fucking nice", "that’s your problem; grow a backbone."),
    ("i want to scream", "then do it; nobody gives a shit."),
    ("i feel so fucking alone", "maybe because you push people away."),
    ("why can't i just be happy?", "because happiness doesn’t come to crybabies."),
    ("i can’t stand these losers", "and yet you still hang around them."),
    ("im tired of this bullshit drama", "then why are you in the middle of it?"),
    ("i hate this fucking job", "then quit and find a new one."),
    ("everyone is a fucking idiot", "and you’re the biggest one."),
    ("i just want to punch something", "your pillow isn’t going to fight back."),
    ("i hate my life", "then change it instead of complaining."),
    ("why does everyone act like they care?", "because pretending is easier than facing reality."),
    ("im sick of pretending", "then stop being a coward and show your true self."),
    ("why can’t i just fit in?", "because you’re too weird."),
    ("im always getting let down", "that’s your life; get used to it."),
    ("my heart is always breaking", "that’s what happens when you fall for losers."),
    ("why do i have to deal with this?", "because you chose to be here."),
    ("i can't believe they said that shit to me", "you probably deserved it."),
    ("my head is spinning from all this drama", "then stop being in the middle of it."),
    ("i just want to escape", "then stop making excuses."),
    ("everyone else is having fun", "and you’re stuck complaining."),
    ("i wish i could be someone else", "you’ll just fuck that up too."),
    ("im tired of being used", "stop being such an easy target."),
    ("why am i always the one crying?", "because you need to toughen up."),
    ("i feel like shit", "maybe it’s because you’re acting like it."),
    ("my friends are toxic as fuck", "then why do you keep them around?"),
    ("i can’t trust anyone", "that’s because you can’t even trust yourself."),
    ("my love life is a disaster", "that’s what happens when you date idiots."),
    ("im so over this", "then do something about it."),
    ("everyone keeps talking shit", "that’s because you give them a reason."),
    ("i just want to be left alone", "then stop crying for attention."),
    ("i can’t believe they’re dating", "you should’ve made a move when you had the chance."),
    ("why do i even bother anymore?", "because you’re a masochist."),
    ("i hate being alone", "then stop pushing people away."),
    ("my life is a train wreck", "and you’re the conductor."),
    ("i want to be happy", "but you won’t put in the effort, will you?"),
    ("why can't i just have one good day?", "because you’re your own worst enemy."),
    ("i feel like im losing my mind", "that’s called reality hitting."),
]


black = "\033[30m"
red = "\033[31m"
green = "\033[32m"
yellow = "\033[33m"
blue = "\033[34m"
magenta = "\033[35m"
cyan = "\033[36m"
white = "\033[37m"
reset = "\033[0m"  
pink = "\033[38;2;255;192;203m"
white = "\033[37m"
blue = "\033[34m"
black = "\033[30m"
light_green = "\033[92m" 
light_yellow = "\033[93m" 
light_magenta = "\033[95m" 
light_cyan = "\033[96m"  
light_red = "\033[91m"  
light_blue = "\033[94m"  



www = Fore.WHITE
mkk = Fore.BLUE
b = Fore.BLACK
ggg = Fore.LIGHTGREEN_EX
y = Fore.LIGHTYELLOW_EX 
pps = Fore.LIGHTMAGENTA_EX
c = Fore.LIGHTCYAN_EX
lr = Fore.LIGHTRED_EX
qqq = Fore.MAGENTA
lbb = Fore.LIGHTBLUE_EX
mll = Fore.LIGHTBLUE_EX
mjj = Fore.RED
yyy = Fore.YELLOW

BRAND_NAME = "VOID TOOLS"
BRAND_TAGLINE = "BETA | discord.gg/voidv2"
BRAND_VERSION = "v2.0 BETA"
refresh_void_branding()

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(arg) for arg in args)
        end = kwargs.get("end", "\n")
        flush = kwargs.get("flush", False)
        cleaned = text.encode("ascii", errors="replace").decode()
        print(cleaned, end=end, flush=flush)

def _load_bot_messages():
    try:
        with open(cfg("messages.json"), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            payload = {}
        return (
            _pick_lines(payload.get("autoreplies"), DEFAULT_AUTOREPLIES),
            _pick_lines(payload.get("autoreplies_multi"), DEFAULT_AUTOREPLIES),
            _pick_lines(payload.get("outlast"), ["keep crying", "stay mad", "L"]),
            _pick_lines(payload.get("kill_messages"), DEFAULT_KILL_MESSAGES),
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return (
            list(DEFAULT_AUTOREPLIES),
            list(DEFAULT_AUTOREPLIES),
            ["keep crying", "stay mad", "L"],
            list(DEFAULT_KILL_MESSAGES),
        )


intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.messages = True
bot = commands.Bot(command_prefix=".", self_bot=True, intents=intents)
bot.remove_command('help')
bot.add_check(void_vip_check)
help_cog = HelpCog(bot)
autoreplies, autoreplies_multi, outlast_messages, kill_messages = _load_bot_messages()

async def _void_setup_hook():
    load_event_react_data()
    await bot.add_cog(help_cog)
    await bot.add_cog(RonMessageCog(bot))
    await bot.add_cog(PingNotification(bot))
    await bot.add_cog(TokenJoiner(bot))
    await bot.add_cog(TokenManager(bot))
    await bot.add_cog(BrowserCommands(bot))

bot.setup_hook = _void_setup_hook


try:
    with open(cfg('settings.json'), 'r', encoding='utf-8') as config_file:
        configsss = json.load(config_file)
        usertoken = resolve_user_token(configsss)
        RpcClientID = configsss.get("RpcClientID")
        RpcState = configsss.get("Rpcstate")
        Rpcdetails = configsss.get("Rpcdetails")
        RpcLargeimg = configsss.get("large_image")
        RpcLargetxt = configsss.get("large_text")
        RpcSmallimg = configsss.get("small_image")
        RpcParty = configsss.get("party_id")
        RpcButtonLabel = configsss.get("ButtonLabel")
        RpcButton1Url = configsss.get("ButtonLabel1url")
        RpcButtonLabel2 = configsss.get("ButtonLabel2")
        RpcButton2Url = configsss.get("ButtonLabel2url")
        NukeBypass = configsss.get("NukeServerBypass")
        if not usertoken:
            raise ValueError(
                "Token manquant — setup.bat OU colle ton token dans config\\token.txt"
            )
        if usertoken != configsss.get("token"):
            configsss["token"] = usertoken
            with open(cfg("settings.json"), "w", encoding="utf-8") as out:
                json.dump(configsss, out, indent=4, ensure_ascii=False)
                out.write("\n")
    sync_rpc_tier()
    refresh_void_branding()
except FileNotFoundError:
    print("[ERREUR] config/settings.json introuvable.")
    print("         Lance setup.bat pour configurer le bot.")
    sys.exit(1)
except ValueError as e:
    print(f"[ERREUR] {e}")
    sys.exit(1)
except json.JSONDecodeError:
    print("[ERREUR] config/settings.json invalide (JSON casse).")
    print("         Supprime-le et relance setup.bat")
    sys.exit(1)


rpc = Presence(RpcClientID) 

async def update_presence():
    await asyncio.to_thread(rpc.connect)

    while True:
        discord_presence = {
            "state": RpcState,  
            "details": Rpcdetails,           
            "start": int(time.time()),    
            "end": None,                  
            "large_image": RpcLargeimg, 
            "large_text": RpcLargetxt,    
            "small_image": "jjejjdjdj", 
            "small_text": RpcSmallimg,
            "party_id": RpcParty,  
            "party_size": [1, 1],  
            "buttons": [
                {
                    "label": RpcButtonLabel,  
                    "url": RpcButton1Url  
                },
                {
                    "label": RpcButtonLabel2, 
                    "url": RpcButton2Url
                }
            ]
        }


        await asyncio.to_thread(rpc.update, **discord_presence)
        await asyncio.sleep(30000000000)




kuromiiart = f"""
⠀⠀⠀⠀⣠⡶⠶⢶⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣤⣤⡀⠀⠀⠀⠀
⠀⠀⠀⠀⢿⣇⠀⢸⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡟⠀⠈⣿⡆⠀⠀⠀
⠀⠀⠀⠀⠀⠙⢻⡟⠙⠻⢶⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣈⣿⢶⣾⠛⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢸⣧⠀⠀⠀⠉⠻⢶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⠟⠁⠀⢻⣆⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠈⣿⠀⠀⠀⠀⠀⠀⠈⠙⠻⣦⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⠟⠁⠀⠀⠀⠀⢿⡆⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠻⢶⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⠟⠁⠀⠀⠀⠀⠀⠀⠈⢿⡄⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣇⣀⣠⣤⣴⡶⠶⠶⠶⠶⣼⣧⣄⣀⠀⠀⠀⠀⠀⠀⠀⠈⣿⡀⠀
⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡟⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠻⢷⣦⡀⠀⠀⠀⠀⠸⣷⠀
⠀⠀⠀⠀⠀⠀⠀⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⣷⣄⠀⠀⣠⡿⠀
⠀⠀⠀⠀⠀⠀⠀⢸⣧⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣶⡾⠋⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠛⠿⣦⣤⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{pps}⢀⣤⣶⣶⣶⣶⣄{qqq}⠀⠀⠀⠘⢷⣄⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⠟⠁⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{pps}⣴⣿⣿⣿⣿⣿⣿⣿⣿⡄{qqq}⠀⠀⠀⢻⣆⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{pps}⣿⡏⠀⢸⣿⣿⡏⠀⢹⣿{qqq}⠀⠀⠀⠀⣿⡄
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣤⣄⣀{pps}⠘⠷⣤⣾⣿⣿⣷⣤⡾⠃{qqq}⣀⠀⠀⠀⢸⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣶⠾⠋⠉⠀⠉⠙⠷⣦{pps}⡸⠛⠛⠛⢏{qqq}⣠⡷⠟⠛⢷⣄⠀⢸⡧
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡆⠀⠀⠀⠀⠀⠀⠀⢀⣴⡿⠋{mjj}⢀⡀⣀⣀⣀{qqq}⠀⠀⠀⠈⠛⠷⣦⡶⠟⠉⠀⠀⠀⢀⠹⣷⣸⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⡀⠀⠀⠀⠀⠀⠀⣾⠋⠀{mjj}⠈⣳⢟⠉⠉⠙⣷⡀{qqq}⠀⠀⠀⠀⠀⠀⠀{mjj}⢀⡴⠚⠛{qqq}⣾⠆⢸⣿⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣄⠀⠀⠀⠀⢸⡏⠀⠀⣠⢅⣤⡤⡠⠀{mjj}⠙⠁{qqq}⠀⠀⠀⢰⡋⠉⣷{mjj}⠘⠃⠀{qqq}⢠⣿⢀⣾⠃⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣦⡀⠀⠘⣷⡀⠼⢡⢫⢎⡜⠀⠀⠀⠀⠀⠀⠠⡖⠛⠭⡆⠀⠀⢠⢻⣷⡟⠁⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢀⡾⣄⠀⠀⠀⠀⠀⠈⢛⣷⣶⣽⣷⣄⣀⠀⠈⠀⠀⠀⠀⠀⠀⠀⣀⣷⣠⣎⠀⣀⣤⡿⠟⠁⠀⠀⠀⠀
⠀⠀⠀⠀⣠⠀⢀⡼⠀⠙⢶⡄⠀⡞⠉⢱⣿⣯⣤⣤⣭⣽⣿⡟⠛⠛⢿⣶⡶⠞⠛⠻⣯⠁⠈⠻⣿⠋⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢠⠞⠁⡰⣿⣥⡄⠀⢶⠛⠂⠉⠛⠉⠉⣩⣿⠋⠀⠀⠙⢷⣄⣴⠿⠋⠀⠀⠀⠀⢹⡇⠀⣠⡿⢻⠀⠀⠀⠀⠀⠀⠀⠀
⠀⣰⠃⢠⠞⡠⡇⠈⢷⡀⠈⢷⡀⠀⠀⣠⡾⠋⠁⠀⠀⠀⢰⡏⠉⢳⠀⠀⠀⠀⠀⢠⣿⠁⢸⡟⠒⠋⠀⠀⠀⠀⠀⠀⠀⠀
⢠⠇⣠⠟⠋⠀⠓⠒⠒⠳⣄⠀⠙⢦⣼⡋⠀⠀⠀⠀⠀⠀⠈⠙⠒⠋⠀⠀⠸⣷⡀⠀⢀⣴⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢸⠀⢹⠳⣄⠀⡞⠉⠓⠲⠬⣙⣶⣤⣀⣉⣻⠆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢻⡾⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣸⠀⢸⠀⠈⠑⠇⢀⡤⠒⠋⣉⡿⠾⣯⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢶⣤⣴⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠹⡀⠈⢦⠀⢸⠓⠋⢀⡴⠋⠁⠀⠀⠹⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⢳⡀⠀⠀⢸⠀⠀⢘⣦⠄⠀⠀⠀⠀⢻⡆⠀⠀⠸⣦⠀⠀⠀⠀⠀⠀⠀⠸⠿⣦⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠉⠀⠀⠸⠔⠊⠁⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⢹⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢷⣤⣤⣤⣬⣿⣤⣤⣤⣤⣤⣤⣤⣤⣤⣾⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""
start_time = time.time()

def getuptime():
    seconds = int(time.time() - start_time)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours}:{minutes:02}:{seconds:02}"
from ctypes import windll, create_string_buffer
@bot.command()
async def transparency(ctx, level: float):
    if 0 <= level <= 1:
        make_console_transparent(level)
        await ctx.send(f"```transparency set to {level * 100}%```")
    else:
        await ctx.send("```provide a num between 0 and 1```")
@bot.event
async def on_ready():
    global outlast_running
    outlast_running = False
    await void_ui.play_void_splash(BRAND_NAME, BRAND_VERSION, void_vip.tier_label())

    try:
        with open(cfg('tokens.txt'), "r") as token_file:
            tokens = token_file.readlines()
            active_token_count = len(tokens)
    except FileNotFoundError:
        active_token_count = 0
        safe_print("token.txt file not found.")

    os.system("cls")
    user_display = str(bot.user)[:25]
    void_ui.print_void_banner(
        user_display,
        str(bot.command_prefix),
        len(bot.guilds),
        len(bot.friends),
        active_token_count,
        BRAND_NAME,
        BRAND_VERSION,
        void_vip.tier_label(),
    )





    """while True:
        for status in status_messages:
            activity = discord.Streaming(
                name=status, 
                url='https://www.twitch.tv/ex'
            )
            await bot.change_presence(activity=activity)
            await asyncio.sleep(200)"""

try:
    with open(cfg('tokens.txt'), "r") as token_file:
        tokens = token_file.readlines()
        active_token_count = len(tokens)
except FileNotFoundError:
    active_token_count = 0
    print("token.txt file not found. Please ensure it is in the correct directory.")


@bot.command()
async def vip(ctx):
    await ctx.send(void_vip.status_message())

@bot.command()
async def license(ctx, key: str = None):
    if not VIP_ENABLED:
        await ctx.send(
            void_ui.text_notice("License", "VIP desactive — tout est gratuit, pas besoin de cle."),
            delete_after=10,
        )
        return
    if void_vip.is_active():
        await ctx.send(
            void_ui.text_notice("VIP", "Deja actif — profite de toutes les fonctions."),
            delete_after=8,
        )
        return
    if not key:
        await ctx.send(void_vip.status_message())
        return
    ok, msg = void_vip.activate(key)
    if ok:
        refresh_void_branding()
        sync_rpc_tier()
        await ctx.send(void_ui.text_notice("License", msg), delete_after=10)
    else:
        await ctx.send(
            void_ui.text_notice(
                "License",
                f"{msg}\nOuvre un ticket sur {void_vip.discord_invite}",
                success=False,
            ),
            delete_after=15,
        )

@bot.command()
async def info(ctx):
    await ctx.send(
        void_ui.text_info_stats(
            str(bot.user),
            str(bot.command_prefix),
            BRAND_NAME,
            BRAND_VERSION,
            void_vip.tier_label(),
            len(bot.guilds),
            len(bot.friends),
            active_token_count,
            getuptime(),
        )
    )

@bot.command()
async def menu(ctx):
    await ctx.send(void_ui.text_main_menu(void_vip.is_active(), BRAND_VERSION, BRAND_NAME, vip_enabled=VIP_ENABLED))

@tasks.loop(seconds=1.0)
async def spam_loop(channel):
    if spamming:
        await channel.send(spam_messages)
@bot.command()
async def invis(ctx):
    global spamming, spam_message
    if spamming:
        await ctx.send("```Already spamming.```")
        return
    
    spam_message = spam_messages
    spamming = True
    await ctx.send(f"```Started spamming invis.```")
    spam_loop.start(ctx.channel)  

@bot.command()
async def cls(ctx):
    os.system('cls')
    void_ui.print_void_banner(
        str(bot.user)[:25],
        str(bot.command_prefix),
        len(bot.guilds),
        len(bot.friends),
        active_token_count,
        BRAND_NAME,
        BRAND_VERSION,
        void_vip.tier_label(),
    )
    await ctx.send(f"```Cleared Display UI```")

@bot.command()
async def invisoff(ctx):
    global spamming
    if not spamming:
        await ctx.send("```Not currently spamming.```")
        return


    spamming = False
    spam_loop.stop()   
    await ctx.send("```Stopped spamming.```")
outlast_running = False
outlast_tasks = {}

@bot.command()
async def outlast(ctx, *, target: str = ""):
    global outlast_running, outlast_messages

    user = await resolve_target_user(ctx, target)
    if not user:
        await ctx.send("```Usage: .outlast @user```")
        return
    if not outlast_messages:
        await ctx.send("```No outlast messages — edit config/messages.json```")
        return

    counter = 1

    if outlast_running:
        await ctx.send("```An outlast session is already running```")
        return
        
    outlast_running = True

    async def outlast_loop():
        nonlocal counter
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        while outlast_running:
            try:
                message = random.choice(outlast_messages)
                try:
                    await ctx.send(f"{user.mention} {message}\n```{counter}```")
                    counter += 1
                    consecutive_failures = 0  
                    await asyncio.sleep(0.66)  
                    
                except discord.errors.HTTPException as e:
                    if e.status == 429:  
                        retry_after = e.retry_after
                        print(f"Rate limited, waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after + 0.5)  
                    else:
                        consecutive_failures += 1
                        print(f"HTTP Error: {e}")
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    consecutive_failures += 1
                    print(f"Error sending message: {e}")
                    await asyncio.sleep(1)
                    
                if consecutive_failures >= max_consecutive_failures:
                    print("Too many consecutive failures, stopping outlast")
                    outlast_running = False
                    await ctx.send("```Outlast stopped due to too many errors```")
                    break
                    
            except Exception as e:
                print(f"Error in outlast loop: {e}")
                await asyncio.sleep(1)
                continue

    try:
        task = bot.loop.create_task(outlast_loop())
        outlast_tasks[(user.id, ctx.channel.id)] = task
        await ctx.send(f"```Started outlast on {user.name}```")
    except Exception as e:
        outlast_running = False
        print(f"Failed to start outlast: {e}")
        await ctx.send("```Failed to start outlast```")
@bot.command()
async def stopoutlast(ctx):
    global outlast_running
    if outlast_running:
        outlast_running = False
        channel_id = ctx.channel.id
        tasks_to_stop = [key for key in outlast_tasks.keys() if key[1] == channel_id]
        
        for task_key in tasks_to_stop:
            task = outlast_tasks.pop(task_key)
            task.cancel()
            
        await ctx.send("```The outlast session has been stopped```")
    else:
        await ctx.send("```No outlast session is currently running```")

CONFIG_FILE_PATH = "multilast_config.json"


default_multilast_config = {
    "token_count": None,  
    "delay": 0.003        
}


def load_multilast_config():
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as file:
            return json.load(file)
    return default_multilast_config


def save_multilast_config():
    with open(CONFIG_FILE_PATH, "w") as file:
        json.dump(multilast_config, file)




outlast_running = False
TOKEN_FILE_PATH = cfg('tokens.txt')
tokens = load_tokens()
multilast_config = load_multilast_config()


async def get_token_settings():
    token_count = multilast_config.get("token_count", 10)  
    delay = multilast_config.get("delay", 0.1)


    with open(cfg('tokens.txt'), 'r') as f:
        tokens = [line.strip() for line in f if line.strip()]
    

    if token_count is None:
        token_count = len(tokens)
    
    selected_tokens = tokens[:token_count] 
    return selected_tokens, delay
@bot.command()
async def mconfig(ctx, setting: str = None, value: str = None):
    if setting is None:

        if multilast_config.get("token_count") is None:
            with open(cfg('tokens.txt'), 'r') as f:
                tokens = [line.strip() for line in f if line.strip()]
            token_count = len(tokens) 
        else:
            token_count = multilast_config.get("token_count", 10)

        configs_display = "\n".join(f"{blue}[ {white}{key} {blue}]: {white}{multilast_config[key]}" for key in multilast_config if key != "token_count")
        configs_display += f"\n                                                            {blue}[ {white}Tokens {blue}]: {white}{token_count}"  

        await ctx.send(f"""```ansi

            {blue}[30m─────────────────────────────────────────────────── [31mDont RUN [30m─────────────────────────────────────────────────── 
                                                        {red}Current {blue}Configuration.
            {blue}[30m─────────────────────────────────────────────────── [31mDont RUN [30m─────────────────────────────────────────────────── 

                                                            {configs_display}
    ```""")
    else:
        if setting.lower() == "token":
            if value.lower() == "all":
                multilast_config["token_count"] = None  
                await ctx.send("```Token count set to use all tokens from token.txt.```")
            else:
                try:
                    multilast_config["token_count"] = int(value)
                    await ctx.send(f"```Token count set to {multilast_config['token_count']}.```")
                except ValueError:
                    await ctx.send("```Invalid token count. Please enter a valid number or 'all'.```")
        elif setting.lower() == "delay":
            try:
                multilast_config["delay"] = float(value)
                await ctx.send(f"```Delay set to {multilast_config['delay']} seconds.```")
            except ValueError:
                await ctx.send("```Invalid delay value. Please enter a valid number.```")

        save_multilast_config()


multilast_config = load_multilast_config()



@bot.command()
async def multilast(ctx, user: discord.User):
    global outlast_running, tokens
    
    if outlast_running:
        await ctx.send("```A multilast session is already running```")
        return
        
    outlast_running = True

    try:
        valid_tokens = []
        async with aiohttp.ClientSession() as session:
            for token in tokens:
                headers = {
                    'Authorization': token,
                    'Content-Type': 'application/json'
                }
                try:
                    async with session.get(f'https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me', headers=headers) as resp:
                        if resp.status == 200:
                            valid_tokens.append(token)
                except Exception as e:
                    print(f"Error validating token {token[-4:]}: {e}")
                    continue

        if not valid_tokens:
            await ctx.send("```No valid tokens found in this server```")
            outlast_running = False
            return
        
        await ctx.send(f"```Found {len(valid_tokens)} valid tokens in this server.\nHow many tokens do you want to use? (1-{len(valid_tokens)}) or 'all' for all tokens```")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            token_response = await bot.wait_for('message', timeout=30.0, check=check)
            if token_response.content.lower() == 'all':
                selected_tokens = valid_tokens
            else:
                try:
                    token_count = int(token_response.content)
                    if token_count < 1 or token_count > len(valid_tokens):
                        await ctx.send(f"```Invalid number. Please choose between 1 and {len(valid_tokens)}```")
                        outlast_running = False
                        return
                    selected_tokens = valid_tokens[:token_count]
                except ValueError:
                    await ctx.send("```Invalid input. Please enter a number or 'all'```")
                    outlast_running = False
                    return
        except asyncio.TimeoutError:
            await ctx.send("```Token selection timed out```")
            outlast_running = False
            return

        await ctx.send(f"```Starting multilast with {len(selected_tokens)} tokens```")

        class SharedCounter:
            def __init__(self, total_tokens):
                self.value = 1
                self.current_token_index = 0
                self.total_tokens = total_tokens
                self.lock = asyncio.Lock()
                self.token_ready = {i: True for i in range(total_tokens)}
                self.active_tokens = total_tokens

            async def get_next(self, token_index):
                async with self.lock:
                    if token_index == self.current_token_index and self.token_ready[token_index]:
                        current = self.value
                        return current
                    return None

            async def increment(self, token_index, success):
                async with self.lock:
                    if success and token_index == self.current_token_index:
                        self.value += 1
                        self.current_token_index = (self.current_token_index + 1) % self.total_tokens
                        while not self.token_ready[self.current_token_index]:
                            self.current_token_index = (self.current_token_index + 1) % self.total_tokens

            async def mark_invalid(self, token_index):
                async with self.lock:
                    if self.token_ready[token_index]:
                        self.token_ready[token_index] = False
                        self.active_tokens -= 1

        shared_counter = SharedCounter(len(selected_tokens))

        async def send_message(token, token_index):
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json',
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-US,en;q=0.9',
                'origin': 'https://discord.com',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            consecutive_failures = 0
            max_consecutive_failures = 5

            while outlast_running and consecutive_failures < max_consecutive_failures:
                message = random.choice(outlast_messages)
                current_number = await shared_counter.get_next(token_index)

                if current_number is None:
                    await asyncio.sleep(0.001)
                    continue

                payload = {
                    'content': f"{user.mention} {message}\n```{current_number}```"
                }

                success = False
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(f'https://discord.com/api/v9/channels/{ctx.channel.id}/messages', 
                                              headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                success = True
                                consecutive_failures = 0
                                print(f"Message {current_number} sent with token: {token[-4:]}")
                            elif resp.status == 429:
                                retry_after = float((await resp.json()).get('retry_after', 1))
                                print(f"Rate limited with token: {token[-4:]}, waiting {retry_after}s")
                                await asyncio.sleep(retry_after + 0.5)
                            else:
                                consecutive_failures += 1
                                print(f"Failed with token: {token[-4:]}. Status code: {resp.status}")
                                await asyncio.sleep(1)
                except Exception as e:
                    consecutive_failures += 1
                    print(f"Error with token {token[-4:]}: {e}")
                    await asyncio.sleep(1)

                if consecutive_failures >= max_consecutive_failures:
                    print(f"Token {token[-4:]} marked as invalid after too many failures")
                    await shared_counter.mark_invalid(token_index)
                    break

                await shared_counter.increment(token_index, success)
                await asyncio.sleep(0.001)

        tasks = [send_message(token, i) for i, token in enumerate(selected_tokens)]
        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"Error in multilast: {e}")
        await ctx.send(f"```An error occurred: {str(e)}```")
    finally:
        outlast_running = False
        await ctx.send("```Multilast session has ended```")
@bot.command()
async def stopmultilast(ctx):
    global outlast_running
    if outlast_running:
        outlast_running = False  
        await ctx.send("The multilast session has been stopped.")
    else:
        await ctx.send("No multilast session is currently running.")





cutie_tasks = {}


cutiem_running = False
autoreply_tasks = {}

@bot.command()
async def cutie(ctx, user: discord.User):
    global cutiem_running, tokens
    if cutiem_running:
        await ctx.send("```A cutie session is already running```")
        return
    cutiem_running = True

    cutie_replies = {
        1: """                                                              ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢲⢄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠄⠂⢉⠤⠐⠋⠈⠡⡈⠉⠐⠠⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⠀⠀⠀⢀⡀⢠⣤⠔⠁⢀⠀⠀⠀⠀⠀⠀⠀⠈⢢⠀⠀⠈⠱⡤⣤⠄⣀⠀⠀⠀⠀⠀
                                                ⠀⠀⠰⠁⠀⣰⣿⠃⠀⢠⠃⢸⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠈⢞⣦⡀⠈⡇⠀⠀⠀
                                                ⠀⠀⠀⢇⣠⡿⠁⠀⢀⡃⠀⣈⠀⠀⠀⠀⢰⡀⠀⠀⠀⠀⢢⠰⠀⠀⢺⣧⢰⠀⠀⠀⠀
                                                ⠀⠀⠀⠈⣿⠁⡘⠀⡌⡇⠀⡿⠸⠀⠀⠀⠈⡕⡄⠀⠐⡀⠈⠀⢃⠀⠀⠾⠇⠀⠀⠀⠀
                                                ⠀⠀⠀⠀⠇⡇⠃⢠⠀⠶⡀⡇⢃⠡⡀⠀⠀⠡⠈⢂⡀⢀⠀⡁⠸⠀⡆⠘⡀⠀⠀⠀⠀
                                                ⠀⠀⠀⠸⠀⢸⠀⠘⡜⠀⣑⢴⣀⠑⠯⡂⠄⣀⣣⢀⣈⢺⡜⢣⠀⡆⡇⠀⢣⠀⠀⠀⠀
                                                ⠀⠀⠀⠇⠀⢸⠀⡗⣰⡿⡻⠿⡳⡅⠀⠀⠀⠀⠈⡵⠿⠿⡻⣷⡡⡇⡇⠀⢸⣇⠀⠀⠀
                                                ⠀⠀⢰⠀⠀⡆⡄⣧⡏⠸⢠⢲⢸⠁⠀⠀⠀⠀⠐⢙⢰⠂⢡⠘⣇⡇⠃⠀⠀⢹⡄⠀⠀
                                                ⠀⠀⠟⠀⠀⢰⢁⡇⠇⠰⣀⢁⡜⠀⠀⠀⠀⠀⠀⠘⣀⣁⠌⠀⠃⠰⠀⠀⠀⠈⠰⠀⠀
                                                ⠀⡘⠀⠀⠀⠀⢊⣤⠀⠀⠤⠄⠀⠀socials⠀⠀⠀⠀⠀⠀⠀⠤⠄⠀⢸⠃⠀⠀⠀⠀⠀⠃⠀
                                                ⢠⠁⢀⠀⠀⠀⠈⢿⡀⠀⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⢀⠏⠀⠀⠀⠀⠀⠀⠸⠀
                                                ⠘⠸⠘⡀⠀⠀⠀⠀⢣⠀⠀⠀⠀⠀⠀⠁⠀⠃⠀⠀⠀⠀⢀⠎⠀⠀⠀⠀⠀⢠⠀⠀⡇
                                                ⠀⠇⢆⢃⠀⠀⠀⠀⠀⡏⢲⢤⢀⡀⠀⠀⠀⠀⠀⢀⣠⠄⡚⠀⠀⠀⠀⠀⠀⣾⠀⠀⠀
                                                ⢰⠈⢌⢎⢆⠀⠀⠀⠀⠁⣌⠆⡰⡁⠉⠉⠀⠉⠁⡱⡘⡼⠇⠀⠀⠀⠀⢀⢬⠃⢠⠀⡆
                                                ⠀⢢⠀⠑⢵⣧⡀⠀⠀⡿⠳⠂⠉⠀⠀⠀⠀⠀⠀⠀⠁⢺⡀⠀⠀⢀⢠⣮⠃⢀⠆⡰⠀
                                                ⠀⠀⠑⠄⣀⠙⡭⠢⢀⡀⠀⠁⠄⣀⣀⠀⢀⣀⣀⣀⡀⠂⢃⡀⠔⠱⡞⢁⠄⣁⠔⠁⠀
                                                ⠀⠀⠀⠀⠀⢠⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⠉⠁⠀⠀⠀⠀
                                                ⠀⠀⠀⠀⠀⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀
         """,
        2: """
                                                ⢀⠴⣂⣀⠒⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⠔⠢⢄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⣾⢺⣿⣿⣷⣌⡒⠢⠤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠤⠴⠋⣴⣿⣷⡆⢡⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠘⢌⢻⣿⣿⣿⣿⣿⣷⣦⣬⣙⠢⡄⠀⢀⣀⣀⣀⣀⣀⡀⠀⢀⡤⢒⣉⣥⣴⣾⣾⣿⣿⣿⡿⢃⠎⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⢸⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⣨⣥⣤⣤⣤⣶⣤⣤⣤⣬⣉⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⡟⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⢰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⡇⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⢧⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠁⠀⠀⠉⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⡸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⠈⠒⠎⣽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣁⣴⡄⠀⠀⣤⣄⢹⣿⣿⣿⣿⣿⣿⣿⣿⡟⢉⠔⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⠀⣸⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⣟⠁⢀⡀⢙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠸⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⠀⡇⣼⣿⣿⣿⣿⣿⣿⣿⡿⠛⠉⠁⠈⠙⠛⠷⣾⣷⣾⠿⠛⠉⠈⠙⠻⣿⣿⣿⣿⣿⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                                ⠀⠀⡇⢿⣿⣿⣿⣿⣿⡟⠁⢸⣷⣀⠀⠀⠀⠀Void     ⠀⣀⣴⡌⢿⣿⣿⣿⠄⣇⠤⢒⡂⠩⠍⠍⠉⢁⣐⠢⢄⡀⣀⠤⢒⣂⣒⢦⡀
                                                ⠀⠀⢳⢸⣿⣿⣿⣿⡿⠀⠀⢈⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⢰⣾⣿⣿⠁⠈⣿⣿⡟⠒⠦⠊⠁⠀⠀⠀⠀⠀⠀⠀⠉⠲⢍⠥⠒⢁⠤⡈⡆⡇
                                                ⠀⠀⠈⣆⢿⣿⣿⣿⣇⠀⠀⠘⢿⣿⡿⠁⠀⠀⠀⣀⣀⠀⠀⠀⠸⣿⣿⡿⠀⠀⣿⡿⠁⠙⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣶⠥⢔⡵⢣⠇
                                                ⠀⠀⠀⠈⢦⡙⢿⣿⣿⣄⠀⠀⠀⠀⠀⠀⠀⠀⣌⠓⢊⡤⠀⠀⠀⠀⠀⠀⠀⣼⠛⠀⡜⡠⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡉⡥⠒⠁⠀
                                                ⠀⠀⠀⠀⠀⠙⣦⢈⡛⠻⣷⣤⣀⠀⠀⠀⢠⡴⠿⢿⡿⠶⣤⡀⢀⣀⠤⠒⠉⠀⢠⡜⠁⠣⣀⣹⠆⢀⣤⡀⠀⠠⡒⠉⣸⠀⠀⠀⠀⡇⣧⠀⠀⠀
                                                ⠀⠀⣰⢉⣌⠓⠁⣇⣸⠿⣿⣿⣿⣿⣿⣿⡏⠀⠀⠀⣿⠀⠀⣿⣿⣶⣤⠒⢦⠀⢄⣇⠀⠀⠀⠀⠀⠈⣲⠃⠀⠀⠈⠉⠀⠀⠀⠀⠀⡇⢸⠀⠀⠀
                                                ⠀⠀⡏⣸⣿⣷⣤⠀⠐⠀⡴⠲⣿⣿⠿⠟⠃⠀⢠⡾⢿⡄⠀⠈⢻⠛⠉⠒⠉⠀⠀⢨⣢⠀⠀⠀⠀⠠⠌⠄⣀⣀⢀⡄⠀⠀⠀⠀⠀⢧⢸⠀⠀⠀
                                                ⠀⠀⡇⠿⢿⣿⣍⡄⠀⠀⡗⠊⠀⠻⢦⣄⣤⠶⠟⠀⠈⠷⣤⣀⠼⠀⠀⠀⠀⠄⡞⢩⠋⠀⠀⠀⠀⠀⠀⠀⠀⢨⠏⠀⠀⢀⡖⡠⠐⠚⠈⡄⠀⠀
                                                ⠀⠀⠈⠑⢦⡛⢿⣷⣶⣾⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠏⠀⠀⠀⠀⠀⢀⡽⠿⢄⡀⠀⠀⠀⠀⠀⠀⠀⠡⣂⡀⡤⣊⠴⠁⠀⠀⡆⢇⣀⡀
                                                ⠀⠀⠀⠀⠀⠉⠒⠀⠀⠄⢌⣧⠀⠀⠀⠀⠀⠀⢠⡄⠀⠀⢹⠀⠀⠀⠀⠀⡰⠙⢦⠀⠀⠈⠙⢲⡆⠂⠀⠀⠀⠀⠀⠁⠤⠠⠀⠠⢄⠊⣧⠤⢢⢹
                                                ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡎⠞⠀⠀⠀⠀⠀⠀⠛⢳⡄⠀⠈⢳⠀⠀⣀⠀⢣⠀⣸⠀⠀⠀⠀⡏⠁⠻⡄⠀⠀⠀⠀⠀⠀⠀⠀⣠⠏⢀⠯⠔⣃⠏
                                                ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢧⢠⡀⠀⠀⠀⠀⠀⠀⢸⡇⠀⣀⠞⡴⠁⠀⠉⢎⡓⠥⠅⠤⠤⠅⡧⠀⣠⡇⠀⠀⠀⠀⠀⠀⠐⠊⣡⣶⣿⠗⠈⠁⠀
                                                ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠳⠍⣐⣒⣒⣒⣒⣂⠩⠭⠭⠗⠊⠀⠀⠀⠀⠀⠈⠁⠀⠀⠁⠒⢌⡛⠮⠄⠐⢂⣀⣐⠂⣒⣂⠿⠟⠋⠀⠀⠀⠀⠀
                                                ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠁⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
""",
        3: "Test",
        4: "Hey"
    }


    try:
        try:
            with open(cfg('tokens.txt'), "r") as file:
                all_tokens = [line.strip() for line in file if line.strip()]
        except Exception as e:
            await ctx.send("```Error reading token.txt file```")
            cutiem_running = False
            return
        
        if not all_tokens:
            await ctx.send("```No tokens found in token.txt```")
            cutiem_running = False
            return

        valid_tokens = []
        async with aiohttp.ClientSession() as session:
            for token in all_tokens:
                headers = {
                    'Authorization': token,
                    'Content-Type': 'application/json',
                    'accept': '*/*',
                    'accept-encoding': 'gzip, deflate, br',
                    'accept-language': 'en-US,en;q=0.9',
                    'origin': 'https://discord.com',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                try:
                    async with session.get(f'https://discord.com/api/v9/users/@me/guilds/{ctx.guild.id}/member', headers=headers) as resp:
                        if resp.status == 200:
                            valid_tokens.append(token)
                            print(f"Token {token[-4:]} is valid")
                        else:
                            print(f"Token {token[-4:]} failed with status {resp.status}")
                except Exception as e:
                    print(f"Error validating token {token[-4:]}: {e}")
                    continue

        if not valid_tokens:
            print("No valid tokens found. Total tokens checked:", len(all_tokens))
            await ctx.send("```No valid tokens found in this server. Please check your token.txt file and ensure the tokens are in the server.```")
            cutiem_running = False
            return

        await ctx.send(f"```Found {len(valid_tokens)} valid tokens in this server.\nHow many tokens do you want to use? (1-{len(valid_tokens)}) or 'all' for all tokens```")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            token_response = await bot.wait_for('message', timeout=30.0, check=check)
            if token_response.content.lower() == 'all':
                tokens = valid_tokens
            else:
                try:
                    token_count = int(token_response.content)
                    if token_count < 1 or token_count > len(valid_tokens):
                        await ctx.send(f"```Invalid number. Please choose between 1 and {len(valid_tokens)}```")
                        cutiem_running = False
                        return
                    tokens = valid_tokens[:token_count]
                except ValueError:
                    await ctx.send("```Invalid input. Please enter a number or 'all'```")
                    cutiem_running = False
                    return
        except asyncio.TimeoutError:
            await ctx.send("```Token selection timed out```")
            cutiem_running = False
            return

        await ctx.send(f"```Using {len(tokens)} tokens```")

        msg = await ctx.send("```Please select a cutie by typing a number (1, 2, 3, 4)```")
        
        try:
            selection_msg = await bot.wait_for('message', timeout=30.0, check=check)
            cutie_number = int(selection_msg.content)
        except asyncio.TimeoutError:
            await ctx.send("```Selection timed out```")
            cutiem_running = False
            return
        except ValueError:
            await ctx.send("```Invalid input. Please enter a number```")
            cutiem_running = False
            return

        if cutie_number in [1, 2, 3, 4]:
            await msg.edit(content=f"Selected cutie {cutie_number}: ```{cutie_replies[cutie_number]}``` ```Are you sure? Type 'yes' to confirm or 'cancel' to cancel```")
            
            try:
                confirmation_msg = await bot.wait_for('message', timeout=30.0, check=check)
                if confirmation_msg.content.lower() == 'yes':
                    await ctx.send(f"```Cutie {cutie_number} has been selected. Starting the session with {len(tokens)} tokens```")
                    cutie_content = cutie_replies.get(cutie_number, "Default cutie message")
                    
                    async def send_cutie_message(token):
                        headers = {
                            'Authorization': token,
                            'Content-Type': 'application/json',
                            'accept': '*/*',
                            'accept-encoding': 'gzip, deflate, br',
                            'accept-language': 'en-US,en;q=0.9',
                            'origin': 'https://discord.com',
                            'sec-fetch-dest': 'empty',
                            'sec-fetch-mode': 'cors',
                            'sec-fetch-site': 'same-origin',
                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        }
                        payload = {
                            'content': cutie_content.replace("socials", user.mention)
                        }

                        max_retries = 5
                        retry_count = 0

                        while retry_count < max_retries:
                            try:
                                async with aiohttp.ClientSession() as session:
                                    async with session.post(f'https://discord.com/api/v9/channels/{ctx.channel.id}/messages', 
                                                          headers=headers, json=payload) as resp:
                                        if resp.status == 200:
                                            print(f"Message sent with token {token[-4:]}")
                                            return True
                                        elif resp.status == 429:
                                            retry_after = float((await resp.json()).get('retry_after', 1))
                                            print(f"Rate limited with token {token[-4:]}, waiting {retry_after}s")
                                            await asyncio.sleep(retry_after + 0.5)
                                        else:
                                            print(f"Failed with token {token[-4:]}: Status {resp.status}")
                                            retry_count += 1
                                            await asyncio.sleep(1)
                            except Exception as e:
                                print(f"Error with token {token[-4:]}: {e}")
                                retry_count += 1
                                await asyncio.sleep(1)
                        return False

                    tasks = [send_cutie_message(token) for token in tokens]
                    results = await asyncio.gather(*tasks)
                    
                    successful = sum(1 for r in results if r)
                    await ctx.send(f"```Cutie messages sent successfully with {successful}/{len(tokens)} tokens```")

                elif confirmation_msg.content.lower() == 'cancel':
                    await ctx.send("```Cutie selection has been canceled```")
            except asyncio.TimeoutError:
                await ctx.send("```Confirmation timed out```")
        else:
            await ctx.send("```Invalid selection. Please choose a number between 1 and 4```")

    except Exception as e:
        print(f"Error in cutie command: {e}")
        await ctx.send(f"```An error occurred: {str(e)}```")
    finally:
        cutiem_running = False
@bot.command()
async def cutieoff(ctx):
    global cutiem_running
    if cutiem_running:
        cutiem_running = False
        await ctx.send("The cutiem session has been stopped.")
    else:
        await ctx.send("No cutiem session is currently running.")

try:
    with open(cfg('tokens.txt')) as f:
        tokens = [line.strip() for line in f.readlines() if line.strip()]
except FileNotFoundError:
    tokens = []




mping_running = False
MAX_RETRIES = 3
BASE_DELAY = 1.5
JITTER = 0.5

@bot.command()
async def mping(ctx):
    global mping_running
    if mping_running:
        await ctx.send("```An mping session is already running.```")
        return
    
    mping_running = True
    await ctx.send("```Starting mping session. Use .mpingoff to stop.```")

    try:
        members = [member for member in ctx.guild.members if not member.bot]
        total_members = len(members)
        index = 0

        tokens, _ = await get_token_settings()
        active_tokens = set(tokens)
        failed_tokens = {}

        async def send_ping(token, message):
            nonlocal active_tokens
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json'
            }
            payload = {
                'content': message
            }

            retry_count = 0
            async with aiohttp.ClientSession() as session:
                while mping_running and token in active_tokens:
                    try:
                        current_delay = BASE_DELAY + random.uniform(0, JITTER)
                        
                        async with session.post(f'https://discord.com/api/v9/channels/{ctx.channel.id}/messages', 
                                                headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                print(f"Message sent with token: {token[-4:]}")
                                retry_count = 0
                            elif resp.status == 429:
                                retry_after = float(resp.headers.get("Retry-After", "1.0"))
                                print(f"Rate limited with token: {token[-4:]}. Retrying after {retry_after} seconds...")
                                await asyncio.sleep(retry_after + random.uniform(0.1, 0.5))
                                continue
                            else:
                                print(f"Failed to send message with token: {token[-4:]}. Status code: {resp.status}")
                                retry_count += 1
                                
                                if retry_count >= MAX_RETRIES:
                                    print(f"Token {token[-4:]} failed {MAX_RETRIES} times, deactivating.")
                                    active_tokens.remove(token)
                                    failed_tokens[token] = retry_count
                                    break
                                
                                await asyncio.sleep(current_delay * 2)
                                continue

                        await asyncio.sleep(current_delay)
                        
                    except Exception as e:
                        print(f"Unexpected error with token {token[-4:]}: {str(e)}")
                        retry_count += 1
                        if retry_count >= MAX_RETRIES:
                            print(f"Token {token[-4:]} failed {MAX_RETRIES} times, deactivating.")
                            active_tokens.remove(token)
                            failed_tokens[token] = retry_count
                            break
                        await asyncio.sleep(current_delay * 2)

        async def start_spamming():
            nonlocal index
            while mping_running and active_tokens:
                tasks = []
                for token in list(active_tokens):  
                    message = ""
                    for _ in range(20):
                        if index < total_members:
                            message += f"{members[index].mention} "
                            index += 1
                        else:
                            index = 0
                    
                    if message.strip():
                        tasks.append(send_ping(token, message))

                await asyncio.gather(*tasks)

                if index == 0:
                    print("All members have been pinged in this round.")
                
                if not active_tokens:
                    await ctx.send("```All tokens have failed. Stopping mping.```")
                    break

        await start_spamming()

    except Exception as e:
        await ctx.send(f"```Error in mping command: {str(e)}```")
    finally:
        mping_running = False
        failed_count = len(failed_tokens)
        active_count = len(active_tokens)
        await ctx.send(f"```mping session ended. {active_count} tokens active, {failed_count} tokens failed.```")

@bot.command()
async def mpingoff(ctx):
    global mping_running
    if mping_running:
        mping_running = False
        await ctx.send("```The mping session is being stopped. Please wait...```")
    else:
        await ctx.send("```No mping session is currently running.```")

@bot.command()
async def ar(ctx, *, target: str = ""):
    channel_id = ctx.channel.id

    user = await resolve_target_user(ctx, target)
    if not user:
        await ctx.send("```Usage: .ar @user```")
        return
    if not autoreplies:
        await ctx.send("```No autoreplies — edit config/messages.json```")
        return

    await ctx.send(f"```Autoreply for {user.mention} has started. Use .arend to stop.```")

    async def send_autoreply(message):
        while True:  
            try:
                random_reply = random.choice(autoreplies)
                await message.reply(random_reply)
                print(f"Successfully replied to {user.name}")
                break  
            except discord.errors.HTTPException as e:
                if e.status == 429:  
                    try:
                        response_data = await e.response.json()
                        retry_after = response_data.get('retry_after', 1)
                    except:
                        retry_after = 1 
                    print(f"Rate limited, waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                else:
                    print(f"HTTP Error: {e}, retrying...")
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"Error sending message: {e}, retrying...")
                await asyncio.sleep(1)

    async def reply_loop():
        def check(m):
            return m.author == user and m.channel == ctx.channel

        while True:
            try:
                message = await bot.wait_for('message', check=check)
                asyncio.create_task(send_autoreply(message))
                await asyncio.sleep(0.1)  
            except Exception as e:
                print(f"Error in reply loop: {e}")
                await asyncio.sleep(1)
                continue


    task = bot.loop.create_task(reply_loop())
    autoreply_tasks[(user.id, channel_id)] = task

@bot.command()
async def arend(ctx):
    channel_id = ctx.channel.id
    tasks_to_stop = [key for key in autoreply_tasks.keys() if key[1] == channel_id]
    
    if tasks_to_stop:
        for user_id in tasks_to_stop:
            task = autoreply_tasks.pop(user_id)
            task.cancel()
        await ctx.send("```Autoreply has been stopped.```")
    else:
        await ctx.send("```No active autoreply tasks in this channel.```")




@bot.command()
async def arm(ctx, user: discord.User):
    channel_id = ctx.channel.id
    

    all_tokens, delay = await get_token_settings()
    if not all_tokens:
        await ctx.send("```No tokens found in token.txt```")
        return

    await ctx.send(f"```How many tokens do you want to use? (1-{len(all_tokens)}) or 'all' for all tokens```")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        token_response = await bot.wait_for('message', timeout=30.0, check=check)
        if token_response.content.lower() == 'all':
            tokens = all_tokens
        else:
            try:
                token_count = int(token_response.content)
                if token_count < 1 or token_count > len(all_tokens):
                    await ctx.send(f"```Invalid number. Please choose between 1 and {len(all_tokens)}```")
                    return
                tokens = all_tokens[:token_count]
            except ValueError:
                await ctx.send("```Invalid input. Please enter a number or 'all'```")
                return
    except asyncio.TimeoutError:
        await ctx.send("```Timeout: No response received```")
        return

    await ctx.send(f"```Autoreply Multi for {user.mention} has started with {len(tokens)} tokens```")

    async def send_arm_reply(token, message):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://discord.com',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        while True:  
            try:
                random_reply = random.choice(autoreplies_multi)
                payload = {
                    'content': random_reply,
                    'message_reference': {
                        'message_id': str(message.id),
                        'channel_id': str(channel_id),
                        'guild_id': str(message.guild.id)
                    }
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(f'https://discord.com/api/v9/channels/{channel_id}/messages', 
                                          headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            print(f"Token {token[-4:]} replied successfully")
                            break  
                        elif resp.status == 429:
                            retry_after = float((await resp.json()).get('retry_after', 1))
                            print(f"Rate limited with token {token[-4:]}, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                        else:
                            print(f"Failed to send with token {token[-4:]}: Status {resp.status}")
                            await asyncio.sleep(1)
            except Exception as e:
                print(f"Error with token {token[-4:]}: {e}")
                await asyncio.sleep(1)

    async def reply_loop():
        def check(m):
            return m.author == user and m.channel == ctx.channel

        while True:
            try:
                message = await bot.wait_for('message', check=check)
                tasks = []
                for token in tokens:  
                    task = asyncio.create_task(send_arm_reply(token, message))
                    tasks.append(task)
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error in reply loop: {e}")
                await asyncio.sleep(1)
                continue

    task = bot.loop.create_task(reply_loop())
    arm_tasks[(user.id, channel_id)] = task
@bot.command()
async def armend(ctx):
    channel_id = ctx.channel.id
    tasks_to_stop = [key for key in arm_tasks.keys() if key[1] == channel_id]
    
    if tasks_to_stop:
        for user_id in tasks_to_stop:
            task = arm_tasks.pop(user_id)
            task.cancel()
        await ctx.send("```Autoreply multi has been stopped.```")
    else:
        await ctx.send("```No active autoreply multi tasks in this channel.```")

@bot.command()
async def kill(ctx, *, target: str = ""):
    user = await resolve_target_user(ctx, target)
    if not user:
        await ctx.send("```Usage: .kill @user```")
        return

    selected_tokens, delay = await get_token_settings()
    if not selected_tokens:
        await ctx.send("```No tokens in config/tokens.txt```")
        return

    channel_id = ctx.channel.id
    user_id = user.mention

    async def send_message(token, index):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.7',
            'origin': 'https://discord.com',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

        last_request_time = 0
        base_delay = 1.0
        backoff_multiplier = 1.0
        max_backoff = 30.0
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                current_time = time.time()
                time_since_last = current_time - last_request_time
                if time_since_last < (base_delay * backoff_multiplier):
                    await asyncio.sleep(base_delay * backoff_multiplier - time_since_last)

                token_delay = 0.2 * index + random.uniform(0.1, 0.3)
                await asyncio.sleep(token_delay)

                random_sentence = random.choice(kill_messages)
                payload = {
                    'content': f"# {user_id} {random_sentence}"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f'https://discord.com/api/v9/channels/{channel_id}/messages',
                        headers=headers,
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            print(f"Message sent with token {token[-4:]}")
                            backoff_multiplier = max(1.0, backoff_multiplier * 0.75)
                            return True
                        elif resp.status == 429:
                            retry_after = float((await resp.json()).get('retry_after', 1))
                            print(f"Rate limited with token {token[-4:]}, waiting {retry_after}s")
                            backoff_multiplier = min(max_backoff, backoff_multiplier * 2)
                            await asyncio.sleep(retry_after + random.uniform(0.1, 1.0))
                            retry_count += 1
                        else:
                            print(f"Failed with token {token[-4:]}: Status {resp.status}")
                            backoff_multiplier = min(max_backoff, backoff_multiplier * 1.5)
                            await asyncio.sleep(base_delay * backoff_multiplier)
                            retry_count += 1

                last_request_time = time.time()

            except Exception as e:
                print(f"Error with token {token[-4:]}: {str(e)}")
                backoff_multiplier = min(max_backoff, backoff_multiplier * 1.5)
                await asyncio.sleep(base_delay * backoff_multiplier)
                retry_count += 1

        return False

    async def kill_loop():
        while True:
            batch_size = 5
            for i in range(0, len(selected_tokens), batch_size):
                batch = selected_tokens[i:i+batch_size]
                tasks = []
                for idx, token in enumerate(batch):
                    task = asyncio.create_task(send_message(token, idx))
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                
                if not all(results):
                    await asyncio.sleep(2.0)  
                else:
                    await asyncio.sleep(delay)

            await asyncio.sleep(delay + random.uniform(0.5, 1.5))

    task = bot.loop.create_task(kill_loop())
    kill_tasks[(user_id, channel_id)] = task

    await ctx.send(f"""```ansi
\u001b[0;32mKill started with:
\u001b[0;34m• {len(selected_tokens)} tokens
\u001b[0;34m• {delay}s cycle delay
\u001b[0;34m• Dynamic delay between tokens```""")

@bot.command()
async def killend(ctx):
    channel_id = ctx.channel.id
    tasks_to_stop = [key for key in kill_tasks.keys() if key[1] == channel_id]
    
    if tasks_to_stop:
        for user_id in tasks_to_stop:
            task = kill_tasks.pop(user_id)
            task.cancel()
            await ctx.send("```Ended Kill```")

@bot.command()
async def gc(ctx):
    channel_id = ctx.channel.id
    names = ["dont fold", "come outlast", "dont fold to social LMFAO", "why r u so ass LMFAOOOOO", "im ur owner", "my jr LOL", "why r u folding to me", "ur so fucking ass", "come die LOL", "10 WPM warrior"]
    counters = {token: idx + 1 for idx, token in enumerate(tokens)}

    async def change_name(token):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        current_counter = counters[token]
        name_index = (current_counter - 1) % len(names)
        new_name = f"{names[name_index]} {current_counter}"

        payload = {
            'name': new_name
        }

        async with aiohttp.ClientSession() as session:
            async with session.patch(f'https://discord.com/api/v9/channels/{channel_id}', headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"{token} changed the channel name to: {new_name}")
                    counters[token] += 1
                elif resp.status == 429:
                    print(f"Rate limited with token: {token}. Retrying...")
                    await asyncio.sleep(1)
                else:
                    print(f"Failed to change name with token: {token}. Status code: {resp.status}")

    async def gc_loop():
        while True:
            tasks = [change_name(token) for token in tokens]
            await asyncio.gather(*tasks)
            await asyncio.sleep(0.5)

    task = bot.loop.create_task(gc_loop())
    gc_tasks[channel_id] = task

@bot.command()
async def gcend(ctx):
    channel_id = ctx.channel.id

    if channel_id in gc_tasks:
        task = gc_tasks[channel_id]
        task.cancel()
        del gc_tasks[channel_id]



protection_running = False
protection_tasks = {}
active_tokens = []  


@bot.command()
async def gcfill(ctx):
    tokens_file_path = cfg('tokens.txt')
    tokens = load_tokens(tokens_file_path)

    if not tokens:
        await ctx.send("```No tokens found in the file. Please check the token file.```")
        return

    limited_tokens = tokens[:12]
    group_channel = ctx.channel

    async def add_token_to_gc(token):
        try:
            user_client = discord.Client(intents=intents)
            
            @user_client.event
            async def on_ready():
                try:
                    await group_channel.add_recipients(user_client.user)
                    print(f'Added {user_client.user} to the group chat')
                except Exception as e:
                    print(f"Error adding user with token {token[-4:]}: {e}")
                finally:
                    await user_client.close()

            await user_client.start(token, bot=False)
            
        except Exception as e:
            print(f"Failed to process token {token[-4:]}: {e}")

    tasks = [add_token_to_gc(token) for token in limited_tokens]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    await ctx.send(f"```Attempted to add {len(limited_tokens)} tokens to the group chat```")

@bot.command()
async def gcleave(ctx):
    tokens_file_path = cfg('tokens.txt')
    tokens = load_tokens(tokens_file_path)
    
    if not tokens:
        await ctx.send("```No tokens found in the file```")
        return
        
    channel_id = ctx.channel.id

    async def leave_gc(token):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f'https://discord.com/api/v9/channels/{channel_id}'
                async with session.delete(url, headers=headers) as response:
                    if response.status == 200:
                        print(f'Token {token[-4:]} left the group chat successfully')
                    elif response.status == 429:
                        retry_after = float((await response.json()).get('retry_after', 1))
                        print(f"Rate limited for token {token[-4:]}, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                    else:
                        print(f"Error for token {token[-4:]}: Status {response.status}")
                        
            except Exception as e:
                print(f"Failed to process token {token[-4:]}: {e}")
            
            await asyncio.sleep(0.5) 

    tasks = [leave_gc(token) for token in tokens]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    await ctx.send("```Attempted to make all tokens leave the group chat```")
@bot.command()
async def gcleaveall(ctx):
    tokens_file_path = cfg('tokens.txt')
    tokens = load_tokens(tokens_file_path)
    
    if not tokens:
        await ctx.send("```No tokens found in the file```")
        return

    async def leave_all_gcs(token):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        left_count = 0
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://discord.com/api/v9/users/@me/channels', headers=headers) as resp:
                    if resp.status == 200:
                        channels = await resp.json()
                        group_channels = [channel for channel in channels if channel.get('type') == 3]
                        
                        for channel in group_channels:
                            try:
                                channel_id = channel['id']
                                async with session.delete(f'https://discord.com/api/v9/channels/{channel_id}', headers=headers) as leave_resp:
                                    if leave_resp.status == 200:
                                        left_count += 1
                                        print(f'Token {token[-4:]} left group chat {channel_id}')
                                    elif leave_resp.status == 429:
                                        retry_after = float((await leave_resp.json()).get('retry_after', 1))
                                        print(f"Rate limited for token {token[-4:]}, waiting {retry_after}s")
                                        await asyncio.sleep(retry_after)
                                    else:
                                        print(f"Error leaving GC {channel_id} for token {token[-4:]}: Status {leave_resp.status}")
                                
                                await asyncio.sleep(0.5)  
                                
                            except Exception as e:
                                print(f"Error processing channel for token {token[-4:]}: {e}")
                                continue
                                
                        return left_count
                    else:
                        print(f"Failed to get channels for token {token[-4:]}: Status {resp.status}")
                        return 0
                        
            except Exception as e:
                print(f"Failed to process token {token[-4:]}: {e}")
                return 0

    status_msg = await ctx.send("```Starting group chat leave operation...```")
    
    tasks = [leave_all_gcs(token) for token in tokens]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_left = sum(r for r in results if isinstance(r, int))
    
    await status_msg.edit(content=f"""```ansi
Group Chat Leave Operation Complete
Total tokens processed: {len(tokens)}
Total group chats left: {total_left}```""")


@bot.group(invoke_without_command=True)
async def protection(ctx):
    await ctx.send("```Use subcommands: start, stop, message, status```")

@protection.command()
async def start(ctx, user: discord.User):
    global protection_running
    protection_running = True
    channel_id = ctx.channel.id

    with open(cfg('tokens.txt'), 'r') as f:
        tokens = [line.strip() for line in f if line.strip()]

    tokens = tokens[:10]

    active_tokens = []
    async def check_token_presence(token):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://discord.com/api/v9/channels/{channel_id}', headers=headers) as resp:
                if resp.status == 200:
                    active_tokens.append(token)
                else:
                    print(f"Token {token[-4:]} is not in the group chat.")

    await asyncio.gather(*[check_token_presence(token) for token in tokens])
    if not active_tokens:
        await ctx.send("```No active tokens found in the group chat.```")
        return

    class SharedCounter:
        def __init__(self, total_tokens):
            self.value = 1
            self.current_token_index = 0
            self.total_tokens = total_tokens
            self.lock = asyncio.Lock()
            self.token_ready = {i: True for i in range(total_tokens)}
        
        async def get_next(self, token_index):
            async with self.lock:
                if token_index == self.current_token_index and self.token_ready[token_index]:
                    current = self.value
                    return current
                return None
                
        async def increment(self, token_index, success):
            async with self.lock:
                if success and token_index == self.current_token_index:
                    self.value += 1
                    self.current_token_index = (self.current_token_index + 1) % self.total_tokens
                    while not self.token_ready[self.current_token_index]:
                        self.current_token_index = (self.current_token_index + 1) % self.total_tokens
                        
        async def mark_invalid(self, token_index):
            async with self.lock:
                self.token_ready[token_index] = False
                if self.current_token_index == token_index:
                    self.current_token_index = (self.current_token_index + 1) % self.total_tokens
                    while not self.token_ready[self.current_token_index]:
                        self.current_token_index = (self.current_token_index + 1) % self.total_tokens

    shared_counter = SharedCounter(len(active_tokens))

    async def send_message(token, token_index):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        last_send_time = 0
        backoff_time = 0.1
        
        while protection_running:
            try:
                current_time = time.time()
                time_since_last = current_time - last_send_time
                
                if time_since_last < backoff_time:
                    await asyncio.sleep(backoff_time - time_since_last)
                
                current_number = await shared_counter.get_next(token_index)
                
                if current_number is None:
                    await asyncio.sleep(0.1)
                    continue
                    
                message = random.choice(protection_messages)
                payload = {
                    'content': f"{user.mention} {message}\n```{current_number}```"
                }

                success = False
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f'https://discord.com/api/v9/channels/{ctx.channel.id}/messages', 
                        headers=headers, 
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            success = True
                            print(f"Protection message {current_number} sent with token: {token[-4:]}")

                            backoff_time = max(0.1, backoff_time * 0.95)
                            last_send_time = time.time()
                        elif resp.status == 429:
                            retry_after = float((await resp.json()).get('retry_after', 1))
                            print(f"Rate limited with token: {token[-4:]}. Waiting {retry_after}s...")
                            backoff_time = min(2.0, backoff_time * 1.5)
                            await asyncio.sleep(retry_after)
                        else:
                            print(f"Failed to send message with token: {token[-4:]}. Status: {resp.status}")
                            await shared_counter.mark_invalid(token_index)
                            await asyncio.sleep(1)

                await shared_counter.increment(token_index, success)
                await asyncio.sleep(random.uniform(0.05, 0.1))
                
            except Exception as e:
                print(f"Error in send_message for token {token[-4:]}: {str(e)}")
                await shared_counter.mark_invalid(token_index)
                await asyncio.sleep(1)

    async def change_name(token, token_index):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        last_change_time = 0
        backoff_time = 0.5
        
        while protection_running:
            try:
                current_time = time.time()
                time_since_last = current_time - last_change_time
                
                if time_since_last < backoff_time:
                    await asyncio.sleep(backoff_time - time_since_last)
                
                current_number = await shared_counter.get_next(token_index)
                
                if current_number is None:
                    await asyncio.sleep(0.1)
                    continue
                    
                gc_name = random.choice(protection_groupchat)
                payload = {
                    'name': f"{gc_name} {current_number}"
                }

                success = False
                async with aiohttp.ClientSession() as session:
                    async with session.patch(
                        f'https://discord.com/api/v9/channels/{channel_id}', 
                        headers=headers, 
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            success = True
                            print(f"GC name {current_number} changed with token: {token[-4:]}")

                            backoff_time = max(0.5, backoff_time * 0.95)
                            last_change_time = time.time()
                        elif resp.status == 429:
                            retry_after = float((await resp.json()).get('retry_after', 1))
                            print(f"Rate limited with token: {token[-4:]}. Waiting {retry_after}s...")
                            backoff_time = min(5.0, backoff_time * 1.5)
                            await asyncio.sleep(retry_after)
                        else:
                            print(f"Failed to change GC name with token: {token[-4:]}. Status: {resp.status}")
                            await shared_counter.mark_invalid(token_index)
                            await asyncio.sleep(1)

                await shared_counter.increment(token_index, success)
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
            except Exception as e:
                print(f"Error in change_name for token {token[-4:]}: {str(e)}")
                await shared_counter.mark_invalid(token_index)
                await asyncio.sleep(1)

    message_tasks = [send_message(token, i) for i, token in enumerate(active_tokens)]
    name_tasks = [change_name(token, i) for i, token in enumerate(active_tokens)]
    all_tasks = message_tasks + name_tasks
    
    combined_task = asyncio.gather(*all_tasks)
    protection_tasks[channel_id] = combined_task
    
    await ctx.send("```Protection mode enabled with active tokens.```")

@protection.command()
async def stop(ctx):
    global protection_running
    protection_running = False
    channel_id = ctx.channel.id

    if channel_id in protection_tasks:
        task = protection_tasks.pop(channel_id)
        task.cancel()
        await ctx.send("```Protection mode disabled```")
    else:
        await ctx.send("```No protection running in this channel```")

@protection.command()
async def message(ctx, *, new_message: str):
    global protection_messages
    protection_messages.append(new_message)
    await ctx.send(f"```Added new protection message: {new_message}```")

@protection.command()
async def status(ctx):
    if protection_running:
        await ctx.send("```Protection mode is currently running```")
    else:
        await ctx.send("```Protection mode is not running```")


@bot.command()
async def protectionoff(ctx):
    global protection_running
    channel_id = ctx.channel.id
    
    if channel_id in protection_tasks:
        protection_running = False
        task = protection_tasks.pop(channel_id)
        task.cancel()
        await ctx.send("```Protection mode disabled```")
    else:
        await ctx.send("```No protection running in this channel```")

async def read_tokens():  
    try:
        with open(cfg('tokens.txt'), 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

async def update_presence1(token, details):
    if token.strip() == "":
        print("Skipping empty token")
        return

    client = discord.Client()

    @client.event
    async def on_ready():
        activity = discord.Streaming(
            name=details, 
            url='https://www.twitch.tv/ex'
        )
        await client.change_presence(activity=activity)

    try:
        await client.start(token, bot=False)  
    except discord.LoginFailure:
        print(f"Failed to login with token: {token} - Invalid token")
    except Exception as e:
        print(f"An error occurred with token: {token} - {e}")

async def streamall(ctx, messages):
    tokens = await read_tokens()  
    if not tokens:
        await ctx.send("```No tokens found in token.txt```")
        return
        
    details = [random.choice(messages) for _ in range(len(tokens))]
    tasks = [update_presence1(token, detail) for token, detail in zip(tokens, details)]
    await asyncio.gather(*tasks)
    await ctx.send("```Statuses updated for all tokens```")

@bot.command()
async def rpcall(ctx, *, message: str):  
    messages = message.split(', ')  
    await streamall(ctx, messages)

light_magenta = "\033[38;5;13m"

import sys
bye = f"""
{light_magenta}
⠀⠀⠀⠀⠀⠀⠀⢀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⡀⣰⡿⠛⠛⠿⢶⣦⣀⠀⢀⣀⣀⣀⣀⣠⡾⠋⠀⠀⠹⣷⣄⣤⣶⡶⠿⠿⣷⡄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢰⣿⠁⠀⠀⠀⠀⠈⠙⠛⠛⠋⠉⠉⢹⡟⠁⠀⠀⣀⣀⠘⣿⠉⠀⠀⠀⠀⠘⣿⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠁⠀⠀⣾⡋⣽⠿⠛⠿⢶⣤⣤⣤⣤⣿⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⣿⡴⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣄⡀⠀⢈⣻⡏⠀⠀⠀⠀⣿⣀⠀⠈⠙⣷⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣰⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠛⠛⠛⠙⢷⣄⣀⣀⣼⣏⣿⠀⠀⢀⣿⠀⠀⠀⠀
⠀⠀⠀⠀⢸⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⣿⡉⠉⠁⢀⣠⣿⡇⠀⠀⠀⠀
⠀⠀⠀⠀⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠗⠾⠟⠋⢹⣷⠀⠀⠀⠀
⢀⣤⣤⣤⣿⣤⣄⠀⠀⠀{red}⠴⠚⠲⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{red}⣠⣶⡆{light_magenta}⠀⠀⠀⠀⢀⣈⣿⣀⣀⡀⠀
⠀⠀⠀⠈⣿⣠⣾⠟⠛⢷⡄⠀⠀⠀⠀⠀⠀⠀{cyan}⡤⠶⢦⡀⠀⠀⠀⠀{red}⠹⠯⠃{light_magenta}⠀⠀⠀⠈⠉⢩⡿⠉⠉⠉⠁
⠀⠀⣤⡶⠿⣿⣇⠀⠀⠸⣷⠀⠀⠀⠀⠀⠀⠀{cyan}⠓⠶⠞⠃{light_magenta}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢤⣼⣯⣀⣀⠀⠀
⠀⢰⣯⠀⠀⠈⠻⠀⠀⠀⣿⣶⣤⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⡿⠁⠉⠉⠁⠀
⠀⠀⠙⣷⣄⠀⠀⠀⠀⠀⢀⣀⣀⠙⢿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢈⣿⡿⢷⣄⡀⠀⠀⠀
⠀⠀⠀⠈⠙⣷⠀⠀⠀⣴⠟⠉⠉⠀⠀⣿⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣠⣤⣾⠟⠉⠀⠀⠈⠉⠀⠀⠀
⠀⠀⠀⠀⠰⣿⠀⠀⠀⠙⢧⣤⡶⠟⢀⣿⠛⢟⡟⡯⠽⢶⡶⠾⢿⣻⣏⣹⡏⣁⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠹⣷⣄⠀⠀⠀⠀⠀⣠⣾⠏⠀⠀⠙⠛⠛⠋⠀⠀⢀⣽⠟⠛⠖⠛⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠙⠻⠷⠶⠿⠟⠋⠹⣷⣤⣀⡀⠄⣡⣀⣠⣴⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠳⣍⣉⣻⣏⣉⣡⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{red}Restarting Selfbot⠀⠀⠀
{cyan}─────────────────────────────────────────────────────────────────────────────────────────────────────────────


"""

@bot.command()
async def reload(ctx):
    # void tools module
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    themed_bye = bye.replace(light_magenta, text_color)
    themed_bye = themed_bye.replace(red, accent_color)
    themed_bye = themed_bye.replace(cyan, highlight_color)

    try:
        message = await ctx.send(f"```ansi\n{themed_bye}```")

        with open('message_id.json', 'w') as f:
            json.dump({"id": message.id, "channel_id": ctx.channel.id}, f)

        await asyncio.sleep(2)

        updated_bye = themed_bye.replace('Restarting Selfbot', f'{text_color}Selfbot Restarted ( loading all data. )')
        await message.edit(content=f"```ansi\n{updated_bye}```")

        notification.notify(
            title="Selfbot Restarted.",
            message=f"You have restarted {BRAND_NAME} !",
            app_name=BRAND_NAME,
            timeout=2,
            app_icon="695eb4bbf96291ef0813969a32fd4776.ico"
        )
        await asyncio.sleep(1)

        os.execv(sys.executable, ['python'] + sys.argv)

    except Exception as e:
        await ctx.send("Failed to restart the selfbot. Please restart manually.")
        print(f"Error restarting selfbot: {e}")


async def change_status():
    await bot.wait_until_ready()
    while True:
        for status in statuses:
            await bot.change_presence(activity=discord.Streaming(name=status, url="https://www.twitch.tv/ex"))
            await asyncio.sleep(10) 





@bot.command()
async def stream(ctx, *, statuses_list: str):
    global status_changing_task
    global statuses
    
    statuses = statuses_list.split(',')
    statuses = [status.strip() for status in statuses]
    
    if status_changing_task:
        status_changing_task.cancel()
    
    status_changing_task = bot.loop.create_task(change_status())
    await ctx.send(f"```Set Status to {statuses_list}```")

@bot.command()
async def stoprpc(ctx):
    global status_changing_task
    
    if status_changing_task:
        status_changing_task.cancel()
        status_changing_task = None
        await bot.change_presence(activity=None)  
        await ctx.send(f'status rotation stopped')
    else:
        await ctx.send(f'status rotation is not running')





active_clients = []

@bot.command()
async def multivc(ctx, channel_id: int):
    await vcmulti(ctx, channel_id)


@bot.command()
async def vcmulti(ctx, channel_id: int):
    tokens = load_tokens()
    
    async def connect_voice(token):
        try:
            intents = discord.Intents.default()
            intents.voice_states = True
            client = commands.Bot(command_prefix='.', self_bot=True, intents=intents)

            @client.event
            async def on_ready():
                try:
                    channel = client.get_channel(channel_id)
                    if channel:
                        voice = await channel.connect()
                        active_clients.append(client)
                        print(f"Connected to voice with token ending in {token[-4:]}")
                except Exception as e:
                    print(f"Error connecting: {e}")

            await client.start(token, bot=False)

        except Exception as e:
            print(f"Error with token {token[-4:]}: {e}")

    tasks = [connect_voice(token) for token in tokens]
    await ctx.send(f"```Connecting {len(tasks)} tokens to voice channel {channel_id}```")
    await asyncio.gather(*tasks, return_exceptions=True)

@bot.command()
async def vcend(ctx, channel_id: int):
    tokens = load_tokens()
    
    async def disconnect_voice(token):
        try:
            intents = discord.Intents.default()
            intents.voice_states = True
            client = commands.Bot(command_prefix='.', self_bot=True, intents=intents)

            @client.event
            async def on_ready():
                try:
                    channel = client.get_channel(channel_id)
                    if channel:
                        for vc in client.voice_clients:
                            if vc.channel.id == channel_id:
                                await vc.disconnect()
                        print(f"Disconnected token ending in {token[-4:]}")
                except Exception as e:
                    print(f"Error disconnecting: {e}")
                finally:
                    await client.close()

            await client.start(token, bot=False)

        except Exception as e:
            print(f"Error with token {token[-4:]}: {e}")

    tasks = [disconnect_voice(token) for token in tokens]
    await ctx.send(f"```Disconnecting {len(tasks)} tokens from voice channel {channel_id}```")
    await asyncio.gather(*tasks, return_exceptions=True)



active_reaction_tasks = []




reactm_running = {}
reactm_tasks = {}



reactm_running = {}
reactm_tasks = {}

@bot.command()
async def reactm(ctx, emoji: str, user: discord.Member):
    global reactm_running
    channel_id = ctx.channel.id
    user_id = user.id

    if (user_id, channel_id) in reactm_running:
        await ctx.send("```A reaction session is already running for this user.```")
        return

    try:
        with open(cfg('tokens.txt'), 'r') as f:
            all_tokens = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await ctx.send("```No tokens found in token.txt```")
        return

    active_tokens = []

    async def check_token_presence(token):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://discord.com/api/v9/channels/{channel_id}', headers=headers) as resp:
                if resp.status == 200:
                    active_tokens.append(token)
                    print(f"Token {token[-4:]} is active in the server")
                else:
                    print(f"Token {token[-4:]} is not in the server")

    await asyncio.gather(*[check_token_presence(token) for token in all_tokens])

    if not active_tokens:
        await ctx.send("```No active tokens found in this server.```")
        return

    await ctx.send(f"```Found {len(active_tokens)} active tokens. How many do you want to use? (1-{len(active_tokens)}) or 'all'```")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        token_response = await bot.wait_for('message', timeout=30.0, check=check)
        if token_response.content.lower() == 'all':
            tokens = active_tokens
        else:
            try:
                token_count = int(token_response.content)
                if token_count < 1 or token_count > len(active_tokens):
                    await ctx.send(f"```Invalid number. Please choose between 1 and {len(active_tokens)}```")
                    return
                tokens = active_tokens[:token_count]
            except ValueError:
                await ctx.send("```Invalid input. Please enter a number or 'all'```")
                return
    except asyncio.TimeoutError:
        await ctx.send("```Timeout: No response received```")
        return

    async def reaction_task(token):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://discord.com',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        async def add_reaction(message_id):
            try:
                url = f'https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me'
                async with aiohttp.ClientSession() as session:
                    async with session.put(url, headers=headers) as resp:
                        if resp.status == 204:  
                            print(f"Token {token[-4:]} reacted to message")
                            return True
                        elif resp.status == 429: 
                            retry_after = float((await resp.json()).get('retry_after', 1))
                            print(f"Rate limited with token {token[-4:]}, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            return False
                        else:
                            print(f"Failed to react with token {token[-4:]}: Status {resp.status}")
                            await asyncio.sleep(1)
                            return False
            except Exception as e:
                print(f"Error adding reaction with token {token[-4:]}: {e}")
                await asyncio.sleep(1)
                return False

        while (user_id, channel_id) in reactm_running:
            try:
                async for message in ctx.channel.history(limit=1):
                    if message.author.id == user_id and message.id:
                        success = await add_reaction(message.id)
                        if not success: 
                            await asyncio.sleep(0.5)
                await asyncio.sleep(0.5) 
            except Exception as e:
                print(f"Error in reaction loop for token {token[-4:]}: {e}")
                await asyncio.sleep(1)

    reactm_running[(user_id, channel_id)] = True
    tasks = []
    
    for token in tokens:
        task = asyncio.create_task(reaction_task(token))
        tasks.append(task)
        active_reaction_tasks.append(task)
    
    reactm_tasks[(user_id, channel_id)] = tasks
    
    await ctx.send(f"```Now reacting with {emoji} to messages from {user.name} using {len(tokens)} tokens```")

@bot.command()
async def reactoff(ctx):
    channel_id = ctx.channel.id
    stopped = False

    for (user_id, chan_id), tasks in list(reactm_tasks.items()):
        if chan_id == channel_id:
            reactm_running.pop((user_id, chan_id), None)
            for task in tasks:
                task.cancel()
            reactm_tasks.pop((user_id, chan_id))
            stopped = True

    if stopped:
        await ctx.send("```Stopped all reaction sessions in this channel```")
    else:
        await ctx.send("```No reaction sessions are currently running in this channel```")






cutiess = f"""
 {blue}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
{white}
⢠⣤⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣶⣦
⠘⢿⣷⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣶⣾⡟⠁
⠀⠘⣿⣿⣿⣿⣶⣦⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣴⣾⣿⣿⣿⣿⠇⠀
⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣶⠀⠀⢀⠀⣀⠀⡀⠀⣶⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀
⠀⠀⢹⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀
⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀
⠀⠀⠘⠿⣿⣿⣿⣿⣿⣿⣿⣿⡟⢀⠀⠀⣀⠙⣿⣿⣿⣿⣿⣿⣿⡟⠋⠁⠀⠀
⠀⠀⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣧⡛⡁⢀⢙⣣⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀
⠀⠀⠀⠀⢸⣿⣿⣿⣿⢟⠋⠁⠉⠛⠳⠿⠚⠋⠁⠈⠙⣿⣿⣿⣿⣿⠆⠀⠀⠀
⠀⠀⠀⠀⢸⣿⣿⡿⠁{red}⢸⣷⣤{white}⠀⠀⠀⠀⠀⠀⠀{red}⣴⣿{white}⠀⢻⣿⣿⡿⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠻⣿⣇⠀{red}⠘⠿⠋{white}⠀⠀⢠⢤⠀⠀⠀{red}⠻⠟{white}⠀⢸⣿⡿⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠈⠻⢦⣀⠀⠀⠀⠀⠒⠤⠖⠀⠀⠀⢀⣠⠟⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⢤⣴⣿⣿⣿⣿⣷⣶⣶⣶⣶⣶⣿⣿⣿⣷⣤⠤⡀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠘⠚⠁⡏⠀⡞⣿⡿⠟⠋⠙⠻⢿⣿⠹⡀⢹⠘⠛⠁⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠐⡛⢠⠹⠼⠀⠀⠀⠀⠀⠸⠴⠃⡇⠈⡇⣠⣤⣤⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⣆⠀⠀⠀⠀⠀⠀⠀⠀⢀⣏⢉⣠⣿⣿⡏⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⠃⠀⠀⠀⢰⣦⠀⠀⠀⠐⢿⠿⠛⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠧⣀⣀⣀⡀⠼⠳⢄⣀⣀⣀⠼⠀⠀⠀⠀⠀⠀⠀⠀⠀
 {blue}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
"""

@bot.command()
async def tok(ctx):
    tokens_list = load_tokens()
    if not tokens_list:
        await ctx.send("No tokens found in token.txt")
        return

    async def get_token_status(token):
        try:
            intents = discord.Intents.default()
            client = commands.Bot(command_prefix='.', self_bot=True, intents=intents)
            
            token_status = {"username": None, "active": False}

            @client.event
            async def on_ready():
                token_status["username"] = f"{client.user.name}#{client.user.discriminator}"
                token_status["active"] = True
                await client.close()

            await client.start(token, bot=False)
            return token_status
            
        except discord.LoginFailure:
            return {"username": f"Invalid token ending in {token[-4:]}", "active": False}
        except Exception as e:
            return {"username": f"Error with token {token[-4:]}: {str(e)}", "active": False}

    loading_message = await ctx.send("```Fetching token statuses...```")
    
    usernames = []
    active_count = 0

    page_char_limit = 2000

    for i, token in enumerate(tokens_list, 1):
        status = await get_token_status(token)
        username = status["username"]
        token_state = f"{green}(active){reset}" if status["active"] else f"{red}(locked){reset}"
        
        if status["active"]:
            active_count += 1
            
        usernames.append(f"[ {i} ] {username} {token_state}")

        page_content = "\n".join(usernames[-(page_char_limit // 50):])  
        progress_message = f"Fetching token statuses...\n\n{page_content}\n\nActive tokens: {active_count}/{len(tokens_list)}"
        
        await loading_message.edit(content=f"```ansi\n{progress_message}```")
        await asyncio.sleep(0.9)

    final_message = f"T O K E N S\n" + "\n".join(usernames) + f"\n\nTotal active tokens: {active_count}/{len(tokens_list)}\n{cutiess}"
    for part in [final_message[i:i+page_char_limit] for i in range(0, len(final_message), page_char_limit)]:
        await loading_message.edit(content=f"```ansi\n{part}```")




@bot.command()
async def pfpscrape(ctx, amount: int = None):
    if ctx.guild is None:
        await ctx.send("```Use this command in a server.```")
        return
    try:
        base_dir = os.path.join(os.getcwd(), "pfps")
        os.makedirs(base_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_path = os.path.join(base_dir, f"scrape_{timestamp}")
        os.makedirs(folder_path, exist_ok=True)

        guild = ctx.guild
        members = list(guild.members)
        if len(members) <= 1:
            try:
                await guild.chunk()
                await asyncio.sleep(2)
            except Exception:
                pass
            members = list(guild.members)

        if len(members) <= 1:
            seen = {}
            async for msg in ctx.channel.history(limit=500):
                author = msg.author
                if author and author.id not in seen:
                    seen[author.id] = author
            members = list(seen.values())

        if not members:
            await ctx.send("```No members loaded — open the server member list in Discord, wait a few seconds, then retry.```")
            return

        if amount is None or amount > len(members):
            amount = len(members)

        selected_members = random.sample(members, amount)
        success_count = 0
        failed_count = 0

        status_message = await ctx.send("```Starting profile picture scraping...```")

        async def download_pfp(session, member):
            try:
                avatar = member.display_avatar.replace(size=1024)
                avatar_url = str(avatar.url)
                file_extension = ".gif" if avatar.is_animated() else ".png"
                safe_name = "".join(x for x in member.name if x.isalnum() or x in (" ", "-", "_")) or str(member.id)
                file_name = f"{safe_name}_{member.id}{file_extension}"
                file_path = os.path.join(folder_path, file_name)

                async with session.get(avatar_url) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.read()
                with open(file_path, "wb") as handle:
                    handle.write(data)
                return True
            except Exception as exc:
                print(f"Error downloading {getattr(member, 'name', member.id)} pfp: {exc}")
                return False

        headers = {"User-Agent": "VoidTools/2.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            chunk_size = 5
            for i in range(0, len(selected_members), chunk_size):
                chunk = selected_members[i : i + chunk_size]
                results = await asyncio.gather(*[download_pfp(session, member) for member in chunk])
                success_count += sum(1 for r in results if r)
                failed_count += sum(1 for r in results if not r)
                progress = (i + len(chunk)) / len(selected_members) * 100
                status = (
                    f"```PFP scrape {progress:.0f}%\n"
                    f"OK: {success_count} | Fail: {failed_count}\n"
                    f"Folder: {folder_path}```"
                )
                try:
                    await status_message.edit(content=status)
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(0.3, 0.6))

        await status_message.edit(
            content=(
                f"```Done — {success_count}/{amount} pfps saved\n"
                f"Failed: {failed_count}\n"
                f"{folder_path}```"
            )
        )
    except Exception as e:
        print(f"pfpscrape error: {e}")
        await ctx.send(f"```Error: {e}```")

@bot.command()
async def bold(ctx):
    global bold_mode
    bold_mode = True
    await ctx.send("```enabling boldbess```")

@bot.command()
async def unbold(ctx):
    global bold_mode
    bold_mode = False
    await ctx.send("```disabling bold```")









@bot.command()
async def emojiexport(ctx):
    folder_name = "exported_emojis"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    emojis = ctx.guild.emojis
    if not emojis:
        await ctx.send("No emojis found in this server.")
        return

    exported_count = 0
    for emoji in emojis:
        emoji_url = str(emoji.url)

        response = requests.get(emoji_url)
        if response.status_code == 200:
            with open(os.path.join(folder_name, f"{emoji.name}.png"), 'wb') as f:
                f.write(response.content)
            exported_count += 1
        else:
            print(f"Failed to download {emoji.name}")

    await ctx.send(f"```Exported {exported_count} emojis to folder: {folder_name}.```")

@bot.command()
async def pastemojis(ctx):
    folder_name = "exported_emojis"

    if not os.path.exists(folder_name):
        await ctx.send("```No exported emojis found. Please use the `.emojiexport` command first.```")
        return

    added_count = 0
    for filename in os.listdir(folder_name):
        if filename.endswith(".png") or filename.endswith(".gif"):
            with open(os.path.join(folder_name, filename), 'rb') as f:
                try:
                    emoji_name = filename.rsplit('.', 1)[0]
                    await ctx.guild.create_custom_emoji(name=emoji_name, image=f.read())
                    added_count += 1
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to add emoji `{emoji_name}`: {e}")

    if added_count > 0:
        await ctx.send(f"```Successfully added {added_count} emojis to the server.```")
    else:
        await ctx.send("```No emojis were added.```")



@bot.command()
async def wipemojis(ctx):
    folder_name = "exported_emojis"


    if os.path.exists(folder_name):
        shutil.rmtree(folder_name)  
        await ctx.send("```The exported emojis folder has been deleted successfully.```")
    else:
        await ctx.send("```No exported emojis folder found to delete.```")
                       



protection_messages = [ 
    "ill\nrip\nyour\njaw\nout\nfaggot",
    "nigga gets stepped on my little girls for a living",
    "# YO PEDO STOP FLASHING YOUR NIPS AT LITTLE GIRLS LOL",
    "shut that fucking lip for i punch you in the mouth",
    "nigga ill rip your spine in half",
    "im\nyour\nfucking\ngod\nso\nkeep\nthat\nchin\nup",
    "yo loser ready to die again?",
    "fatass nigga already tired",
    "yo\nbitch\noff\nyour\nknees",
    "nigga is frail and weak",
    "you snap under any pressure",
    "you might aswell fold."
]

protection_groupchat = [
    "nigga is a pedofile discord.gg/voidv2 | t.me/v0idtool",
    "put your nipples away?? LOL discord.gg/voidv2 | t.me/v0idtool",
    "yo pedo wakey wakey discord.gg/voidv2 | t.me/v0idtool",
    "nigga gets cucked by socail and likes it discord.gg/voidv2 | t.me/v0idtool",
    "nigga your a skid discord.gg/voidv2 | t.me/v0idtool",
    "fat frail loser discord.gg/voidv2 | t.me/v0idtool",
    "nigga i broke your ospec discord.gg/voidv2 | t.me/v0idtool",
    "chin up fuckface discord.gg/voidv2 | t.me/v0idtool",
    "yo this nigga slow as shit discord.gg/voidv2 | t.me/v0idtool",
    "nigga ill rip your face off discord.gg/voidv2 | t.me/v0idtool",
    "odd ball pedofile nigga discord.gg/voidv2 | t.me/v0idtool",
    "void tools runs you discord.gg/voidv2 | t.me/v0idtool",
    "nigga eats crickets for fun discord.gg/voidv2 | t.me/v0idtool",
    "ill rape your mom discord.gg/voidv2 | t.me/v0idtool"
]


from discord import Webhook
from asyncio import timeout
gcspam_protection_enabled = False

gc_config = {
    "enabled": False,
    "whitelist": [],
    "blacklist": [],
    "silent": True,
    "leave_message": "Goodbye.",
    "remove_blacklisted": True,
    "webhook_url": None,
    "auto_block": False
}

def save_gc_config():
    with open(cfg('gc.json'), 'w') as f:
        json.dump(gc_config, f, indent=4)

def load_gc_config():
    try:
        with open(cfg('gc.json'), 'r') as f:
            gc_config.update(json.load(f))
    except FileNotFoundError:
        save_gc_config()

load_gc_config()

@bot.group(invoke_without_command=True)
async def antigcspam(ctx):
    if ctx.invoked_subcommand is None:
        gc_config["enabled"] = not gc_config["enabled"]
        save_gc_config()
        
        status = f"""```ansi
Anti GC-Spam Status
Enabled: {blue}{gc_config["enabled"]}{reset}
Silent Mode: {blue}{gc_config["silent"]}{reset}
Auto Remove Blacklisted: {blue}{gc_config["remove_blacklisted"]}{reset}
Auto Block: {blue}{gc_config["auto_block"]}{reset}
Whitelisted Users: {blue}{len(gc_config["whitelist"])}{reset}
Blacklisted Users: {blue}{len(gc_config["blacklist"])}{reset}
Webhook: {blue}{"Set" if gc_config["webhook_url"] else "Not Set"}{reset} 
Leave Message: {blue}{gc_config["leave_message"]}{reset}```"""
        await ctx.send(status)

@antigcspam.command(name="whitelist")
async def gc_whitelist(ctx, user: discord.User):
    if user.id not in gc_config["whitelist"]:
        gc_config["whitelist"].append(user.id)
        save_gc_config()
        await ctx.send(f"```{user.name} can now add you to group chats```")
    else:
        await ctx.send(f"```{user.name} is already allowed to add you to group chats```")

@antigcspam.command(name="unwhitelist")
async def gc_unwhitelist(ctx, user: discord.User):
    if user.id in gc_config["whitelist"]:
        gc_config["whitelist"].remove(user.id)
        save_gc_config()
        await ctx.send(f"```Removed {user.name} from whitelist```")
    else:
        await ctx.send(f"```{user.name} is not whitelisted```")

@antigcspam.command(name="blacklist")
async def gc_blacklist(ctx, user: discord.User):
    if user.id not in gc_config["blacklist"]:
        gc_config["blacklist"].append(user.id)
        save_gc_config()
        headers = {
            'Authorization': bot.http.token,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=',
            'X-Discord-Locale': 'en-US',
            'X-Debug-Options': 'bugReporterEnabled',
            'Origin': 'https://discord.com',
            'Referer': 'https://discord.com/channels/@me'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f'https://discord.com/api/v9/users/@me/relationships/{user.id}',
                    headers=headers
                ) as resp:
                    if resp.status == 204:
                        await ctx.send(f"```Added {user.name} to blacklist and removed friend```")
                        return
                        
        except Exception as e:
            print(f"Error removing friend: {e}")
            
        await ctx.send(f"```Added {user.name} to blacklist```")
    else:
        await ctx.send(f"```{user.name} is already blacklisted```")
@antigcspam.command(name="unblacklist")
async def gc_unblacklist(ctx, user: discord.User):
    if user.id in gc_config["blacklist"]:
        gc_config["blacklist"].remove(user.id)
        save_gc_config()
        await ctx.send(f"```Removed {user.name} from blacklist```")
    else:
        await ctx.send(f"```{user.name} is not blacklisted```")

@antigcspam.command(name="silent")
async def gc_silent(ctx, mode: bool):
    gc_config["silent"] = mode
    save_gc_config()
    await ctx.send(f"```Silent mode {'enabled' if mode else 'disabled'}```")

@antigcspam.command(name="message")
async def gc_message(ctx, *, message: str):
    gc_config["leave_message"] = message
    save_gc_config()
    await ctx.send(f"```Leave message set to: {message}```")

@antigcspam.command(name="autoremove")
async def gc_autoremove(ctx, mode: bool):
    gc_config["remove_blacklisted"] = mode
    save_gc_config()
    await ctx.send(f"```Auto-remove blacklisted users {'enabled' if mode else 'disabled'}```")

@antigcspam.command(name="webhook")
async def gc_webhook(ctx, url: str = None):
    gc_config["webhook_url"] = url
    save_gc_config()
    if url:
        await ctx.send("```Webhook URL set```")
    else:
        await ctx.send("```Webhook removed```")

@antigcspam.command(name="autoblock")
async def gc_autoblock(ctx, mode: bool):
    gc_config["auto_block"] = mode
    save_gc_config()
    await ctx.send(f"```Auto-block {'enabled' if mode else 'disabled'}```")

@antigcspam.command(name="list")
async def gc_list(ctx):
    whitelisted = "\n".join([f"• {bot.get_user(uid).name}" for uid in gc_config["whitelist"] if bot.get_user(uid)])
    blacklisted = "\n".join([f"• {bot.get_user(uid).name}" for uid in gc_config["blacklist"] if bot.get_user(uid)])
    
    status = f"""```ansi
Whitelisted Users:
{whitelisted if whitelisted else "None"}

Blacklisted Users:
{blacklisted if blacklisted else "None"}```"""
    await ctx.send(status)

@bot.event
async def on_private_channel_create(channel):
    if gc_config["enabled"] and isinstance(channel, discord.GroupChannel):
        try:
            await asyncio.sleep(0.5)
            
            headers = {
                'Authorization': bot.http.token,
                'Content-Type': 'application/json'
            }
            params = {
                'silent': str(gc_config["silent"]).lower()
            }

            try:
                async with timeout(2):  
                    async for msg in channel.history(limit=1):
                        creator = msg.author
                        
                        print(f"GC created by: {creator.name} ({creator.id})")

                        if creator.id in gc_config["whitelist"]:
                            print(f"Whitelisted user {creator.name}, allowing GC")
                            return
                            
                        if creator.id in gc_config["blacklist"]:
                            print(f"Blacklisted user {creator.name} detected")
                            
                            try:
                                async with aiohttp.ClientSession() as session:
                                    async with session.delete(
                                        f'https://discord.com/api/v9/users/@me/relationships/{creator.id}',
                                        headers=headers
                                    ) as resp:
                                        if resp.status == 204:
                                            print(f"Removed friend: {creator.name}")
                            except Exception as e:
                                print(f"Failed to remove friend: {e}")

                            if gc_config["remove_blacklisted"]:
                                try:
                                    async with aiohttp.ClientSession() as session:
                                        async with session.put(
                                            f'https://discord.com/api/v9/users/@me/relationships/{creator.id}',
                                            headers=headers,
                                            json={"type": 2}
                                        ) as resp:
                                            if resp.status == 204:
                                                print(f"Blocked user: {creator.name}")
                                except Exception as e:
                                    print(f"Failed to block user: {e}")
            except:
                print("Couldn't get creator info, leaving anyway")

            if not gc_config["silent"]:
                try:
                    await channel.send(gc_config["leave_message"])
                except:
                    print("Failed to send leave message")

            async with aiohttp.ClientSession() as session:
                for _ in range(3):  
                    try:
                        async with session.delete(
                            f'https://discord.com/api/v9/channels/{channel.id}',
                            headers=headers,
                            params=params
                        ) as resp:
                            if resp.status == 200:
                                print(f"Successfully left group chat: {channel.id}")
                                
                                if gc_config["webhook_url"]:
                                    try:
                                        creator_info = f"{creator.name}#{creator.discriminator} (ID: {creator.id})" if 'creator' in locals() else "Unknown"
                                        webhook_data = {
                                            "content": f"Left GC created by {creator_info}\nGC ID: {channel.id}"
                                        }
                                        await session.post(gc_config["webhook_url"], json=webhook_data)
                                    except:
                                        print("Failed to send webhook notification")
                                return
                                
                            elif resp.status == 429:
                                retry_after = int(resp.headers.get("Retry-After", 1))
                                print(f"Rate limited. Waiting {retry_after} seconds...")
                                await asyncio.sleep(retry_after)
                            else:
                                print(f"Failed to leave GC. Status: {resp.status}")
                                await asyncio.sleep(1)
                    except Exception as e:
                        print(f"Error during leave attempt: {e}")
                        await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in GC protection: {e}")

    if not autogc_enabled:
        return

    try:
        async for msg in channel.history(limit=1):
            if msg.author.id in gc_config["whitelist"]:
                return
    except:
        pass

    tokens = load_tokens()
    limited_tokens = tokens[:12]

    async def add_token_to_gc(token):
        try:
            user_client = discord.Client(intents=discord.Intents.default())
            
            @user_client.event
            async def on_ready():
                try:
                    await channel.add_recipients(user_client.user)
                    print(f'Added {user_client.user} to the group chat')
                except Exception as e:
                    print(f"Error adding user with token {token[-4:]}: {e}")
                finally:
                    await user_client.close()

            await user_client.start(token, bot=False)
            
        except Exception as e:
            print(f"Failed to process token {token[-4:]}: {e}")

    tasks = [add_token_to_gc(token) for token in limited_tokens if token != bot.http.token]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    print(f"Attempted to add {len(limited_tokens)} tokens to group chat {channel.id}")

@bot.event
async def on_private_channel_delete(channel):
    if not autoleave_enabled or not isinstance(channel, discord.GroupChannel):
        return
        
    tokens = load_tokens()
    
    async def leave_with_token(token, channel_id):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        params = {'silent': 'true'}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://discord.com/api/v9/channels/{channel_id}',
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return False
                        
                async with session.delete(
                    f'https://discord.com/api/v9/channels/{channel_id}',
                    headers=headers,
                    params=params
                ) as resp:
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 1))
                        print(f"Rate limited. Retrying after {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        return False
                    return resp.status == 200
                    
        except Exception as e:
            print(f"Error leaving group with token: {e}")
            return False

    tasks = []
    for token in tokens:
        if token != bot.http.token:
            task = asyncio.create_task(leave_with_token(token, channel.id))
            tasks.append(task)
            
    results = await asyncio.gather(*tasks)
    left = sum(1 for r in results if r)
    print(f"{left} tokens left group chat {channel.id}")

noleave_users = {}


async def monitor_group_chats(ctx, group_chat_id):
    await bot.wait_until_ready() 

    headers = {
        'Authorization': bot.http.token,
        'Content-Type': 'application/json'
    }

    while not bot.is_closed():
        if group_chat_id in noleave_users:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://discord.com/api/v9/channels/{group_chat_id}', headers=headers) as resp:
                    if resp.status == 200:
                        group_data = await resp.json()
                        current_member_ids = {int(recip['id']) for recip in group_data.get('recipients', [])}

                        for member in list(noleave_users[group_chat_id]):
                            if member.id not in current_member_ids:
                                try:
                                    if member.id == ctx.author.id:  
                                        continue
                                    async with session.put(
                                        f'https://discord.com/api/v9/channels/{group_chat_id}/recipients/{member.id}',
                                        headers=headers
                                    ) as add_resp:
                                        if add_resp.status == 204:
                                            print(f"Re-added {member.username} to group chat")
                                        elif add_resp.status == 429:
                                            retry_after = int(add_resp.headers.get('Retry-After', 1))
                                            await asyncio.sleep(retry_after)
                                except Exception as e:
                                    print(f"Error adding user: {e}")

        await asyncio.sleep(0.1)

class SimpleUser:
    def __init__(self, data):
        self.id = int(data['id'])
        self.username = data['username']
        self.discriminator = data.get('discriminator', '0')

@bot.command(name="autotrap")
async def autotrap(ctx, action: str, user_input: str = None):
    global noleave_users

    group_chat_id = ctx.channel.id

    if group_chat_id not in noleave_users:
        noleave_users[group_chat_id] = set()

    if action == "toggle":
        if user_input:
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = user_input[2:-1].replace('!', '')
            else:
                user_id = user_input

            try:
                user_id = int(user_id)
                headers = {
                    'Authorization': bot.http.token,
                    'Content-Type': 'application/json'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(f'https://discord.com/api/v9/users/{user_id}', headers=headers) as resp:
                        if resp.status == 200:
                            user_data = await resp.json()
                            member_obj = SimpleUser(user_data)
                            
                            if member_obj.id in [u.id for u in noleave_users[group_chat_id]]:
                                noleave_users[group_chat_id] = {u for u in noleave_users[group_chat_id] if u.id != member_obj.id}
                                await ctx.send(f"```{member_obj.username} is now allowed to leave.```")
                            else:
                                noleave_users[group_chat_id].add(member_obj)
                                await ctx.send(f"```{member_obj.username} cannot leave this group chat.```")
                        else:
                            await ctx.send("```User not found.```")
            except ValueError:
                await ctx.send("```Invalid user ID format.```")
            except Exception as e:
                await ctx.send(f"```Error: {str(e)}```")
        else:
            await ctx.send("```Please specify a user (mention or ID).```")

    elif action == "list":
        if noleave_users[group_chat_id]:
            user_list = ", ".join([f"<@{user.id}>" for user in noleave_users[group_chat_id]])
            await ctx.send(f"```Users prevented from leaving: \n{user_list}```")
        else:
            await ctx.send("```No users are prevented from leaving this group chat.```")

    elif action == "clear":
        noleave_users[group_chat_id].clear()
        await ctx.send("```All users are now allowed to leave this group chat.```")
    else:
        await ctx.send("```Invalid action. Use `toggle`, `list`, or `clear`.```")

    if not hasattr(bot, 'monitor_task'):
        bot.monitor_task = bot.loop.create_task(monitor_group_chats(ctx, group_chat_id))
@bot.command()
async def ghostping(ctx, user: discord.User):

    try:

        message = await ctx.send(f"{user.mention}")
        await message.delete()  
        await ctx.message.delete()  

    except Exception as e:
        await ctx.send(f"```Failed: {e}```")

typing_active = {}  

@bot.command()
async def triggertyping(ctx, time: str = "5s", channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel

    total_seconds = 0
    try:
        if time.endswith("s"):
            total_seconds = int(time[:-1])
        elif time.endswith("m"):
            total_seconds = int(time[:-1]) * 60
        elif time.endswith("h"):
            total_seconds = int(time[:-1]) * 3600
        else:
            total_seconds = int(time)
    except ValueError:
        await ctx.send("```Usage: .triggertyping 5s | 2m | 1h```")
        return

    typing_active[channel.id] = True
    try:
        await ctx.send(f"```Typing for {total_seconds}s in #{channel.name}```")
        end = time.time() + total_seconds
        while time.time() < end and typing_active.get(channel.id):
            async with channel.typing():
                await asyncio.sleep(min(8.0, end - time.time()))
    except Exception:
        await ctx.send("```Failed to trigger typing```")
    finally:
        typing_active.pop(channel.id, None)

@bot.command()
async def triggertypingoff(ctx, channel: discord.TextChannel = None):

    
    if channel is None:
        channel = ctx.channel

    if channel.id in typing_active:
        typing_active.pop(channel.id)  
        await ctx.send(f"```Stopped typing in {channel.name}.```")
    else:
        await ctx.send(f"```No typing session is active```")

translator = Translator()


translate_settings = {"active": False, "language": "en"}

LANGUAGE_CODES = {
    'af': 'Afrikaans', 'sq': 'Albanian', 'am': 'Amharic', 'ar': 'Arabic', 'hy': 'Armenian', 'az': 'Azerbaijani',
    'eu': 'Basque', 'be': 'Belarusian', 'bn': 'Bengali', 'bs': 'Bosnian', 'bg': 'Bulgarian', 'ca': 'Catalan',
    'ceb': 'Cebuano', 'ny': 'Chichewa', 'zh-cn': 'Chinese', 'zh-tw': 'Chinese (Traditional)',
    'co': 'Corsican', 'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'nl': 'Dutch', 'en': 'English',
    'eo': 'Esperanto', 'et': 'Estonian', 'tl': 'Filipino', 'fi': 'Finnish', 'fr': 'French', 'fy': 'Frisian',
    'gl': 'Galician', 'ka': 'Georgian', 'de': 'German', 'el': 'Greek', 'gu': 'Gujarati', 'ht': 'Haitian Creole',
    'ha': 'Hausa', 'haw': 'Hawaiian', 'iw': 'Hebrew', 'hi': 'Hindi', 'hmn': 'Hmong', 'hu': 'Hungarian',
    'is': 'Icelandic', 'ig': 'Igbo', 'id': 'Indonesian', 'ga': 'Irish', 'it': 'Italian', 'ja': 'Japanese',
    'jw': 'Javanese', 'kn': 'Kannada', 'kk': 'Kazakh', 'km': 'Khmer', 'rw': 'Kinyarwanda', 'ko': 'Korean',
    'ku': 'Kurdish (Kurmanji)', 'ky': 'Kyrgyz', 'lo': 'Lao', 'la': 'Latin', 'lv': 'Latvian', 'lt': 'Lithuanian',
    'lb': 'Luxembourgish', 'mk': 'Macedonian', 'mg': 'Malagasy', 'ms': 'Malay', 'ml': 'Malayalam', 'mt': 'Maltese',
    'mi': 'Maori', 'mr': 'Marathi', 'mn': 'Mongolian', 'my': 'Myanmar (Burmese)', 'ne': 'Nepali', 'no': 'Norwegian',
    'or': 'Odia (Oriya)', 'ps': 'Pashto', 'fa': 'Persian', 'pl': 'Polish', 'pt': 'Portuguese', 'pa': 'Punjabi',
    'ro': 'Romanian', 'ru': 'Russian', 'sm': 'Samoan', 'gd': 'Scots Gaelic', 'sr': 'Serbian', 'st': 'Sesotho',
    'sn': 'Shona', 'sd': 'Sindhi', 'si': 'Sinhala', 'sk': 'Slovak', 'sl': 'Slovenian', 'so': 'Somali',
    'es': 'Spanish', 'su': 'Sundanese', 'sw': 'Swahili', 'sv': 'Swedish', 'tg': 'Tajik', 'ta': 'Tamil', 
    'tt': 'Tatar', 'te': 'Telugu', 'th': 'Thai', 'tr': 'Turkish', 'tk': 'Turkmen', 'uk': 'Ukrainian', 
    'ur': 'Urdu', 'ug': 'Uyghur', 'uz': 'Uzbek', 'vi': 'Vietnamese', 'cy': 'Welsh', 'xh': 'Xhosa', 
    'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu'
}


LANGUAGE_NAMES = {name.lower(): code for code, name in LANGUAGE_CODES.items()}

@bot.command()
async def translate(ctx, language: str):
    language = language.lower()

    
    if language in LANGUAGE_CODES:
        target_language = language
    elif language in LANGUAGE_NAMES:  
        target_language = LANGUAGE_NAMES[language]
    else:
        available_langs = "\n".join([f"{code}: {name}" for code, name in LANGUAGE_CODES.items()])
        await ctx.send(f"```Invalid language. Please provide a valid language code or language name.\nAvailable languages:\n{available_langs}```")
        return
    
    translate_settings["active"] = True
    translate_settings["language"] = target_language
    await ctx.message.delete()  
    await ctx.send(f"```Translation mode activated. All your messages will be translated to {LANGUAGE_CODES[target_language]}.```")


@bot.command()
async def translateoff(ctx):
    translate_settings["active"] = False
    await ctx.message.delete()  
    await ctx.send("```Translation mode deactivated.```")





@bot.command()
async def autoreact(ctx, user: discord.User, emoji: str):
    autoreact_users[user.id] = emoji
    await ctx.send(f"```Now auto-reacting with {emoji} to {user.name}'s messages```")

@bot.command()
async def autoreactoff(ctx, user: discord.User):
    if user.id in autoreact_users:
        del autoreact_users[user.id]
        await ctx.send(f"```Stopped auto-reacting to {user.name}'s messages```")
    else:
        await ctx.send("```This user doesn't have autoreact enabled```")


def load_tokens():
    with open(cfg('tokens.txt'), 'r') as file:
        return [line.strip() for line in file.readlines() if line.strip()]

tokens = load_tokens()  

@bot.command()
async def say(ctx, *, message: str):
    tokens, delay = await get_token_settings()

    channel_id = ctx.channel.id
    parts = message.split(" ", 1)

    try:
        token_index = int(parts[0])
        if len(parts) < 2:
            await ctx.send("```Please specify a message after the token index!```")
            return

        actual_message = parts[1]  

        if token_index < 1 or token_index > len(tokens):
            await ctx.send("```Invalid token index specified!```")
            return

        token = tokens[token_index - 1]  
        tokens_to_use = [token]  
    except ValueError:
        actual_message = message
        tokens_to_use = tokens

    async def send_message(token, message):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        payload = {
            'content': message
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"Message sent with token: {token[-4:]}")
                elif resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 1))
                    print(f"Rate limited with token: {token[-4:]}. Retrying after {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    await send_message(token, message)
                else:
                    print(f"Failed to send message with token: {token[-4:]}. Status code: {resp.status}")

    tasks = [send_message(token, actual_message) for token in tokens_to_use]
    await asyncio.gather(*tasks)
    
    await ctx.send(f"```Message sent by token {token_index}.```" if len(tokens_to_use) == 1 else "```Message sent by all tokens.```")

spammings = False
MAX_RETRIES = 3
DEFAULT_DELAY = 1.5  
JITTER = 0.5  

@bot.command()
async def mspam(ctx, *, messages: str):
    global spammings
    spammings = True
    channel_id = ctx.channel.id
    await ctx.send("```Spamming started by all tokens. Use .mspamoff to stop.```")

    message_list = [msg.strip() for msg in messages.split(',')]
    tokens, base_delay = await get_token_settings()

    failed_tokens = {}
    active_tokens = set(tokens)

    async def send_message(token, message):
        nonlocal active_tokens
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        payload = {
            'content': message
        }
        
        retry_count = 0
        
        async with aiohttp.ClientSession() as session:
            while spammings and token in active_tokens:
                try:
                    current_delay = base_delay + random.uniform(0, JITTER)
                    
                    async with session.post(
                        f'https://discord.com/api/v9/channels/{channel_id}/messages',
                        headers=headers,
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            print(f"Message sent with token: {token[-4:]} - Content: {message}")
                            retry_count = 0  
                            
                        elif resp.status == 429:  
                            retry_after = float(resp.headers.get("Retry-After", "1.0"))
                            print(f"Rate limited with token: {token[-4:]}. Retrying after {retry_after} seconds...")
                            await asyncio.sleep(retry_after + random.uniform(0.1, 0.5))
                            continue
                            
                        else:
                            print(f"Error with token {token[-4:]}: Status code {resp.status}")
                            retry_count += 1
                            
                            if retry_count >= MAX_RETRIES:
                                print(f"Token {token[-4:]} failed {MAX_RETRIES} times, deactivating.")
                                active_tokens.remove(token)
                                failed_tokens[token] = retry_count
                                break
                                
                            await asyncio.sleep(current_delay * 2) 
                            continue

                    await asyncio.sleep(current_delay)

                except Exception as e:
                    print(f"Unexpected error with token {token[-4:]}: {str(e)}")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        print(f"Token {token[-4:]} failed {MAX_RETRIES} times, deactivating.")
                        active_tokens.remove(token)
                        failed_tokens[token] = retry_count
                        break
                    await asyncio.sleep(current_delay * 2)

    try:
        tasks = [send_message(token, message_list[i % len(message_list)]) 
                for i, token in enumerate(tokens)]
        await asyncio.gather(*tasks)

        if not active_tokens:
            await ctx.send("```All tokens have failed. Stopping spam.```")
            spammings = False
        elif len(failed_tokens) > 0:
            failed_count = len(failed_tokens)
            await ctx.send(f"```Spam continuing with {len(active_tokens)} tokens. {failed_count} tokens failed.```")

    except Exception as e:
        await ctx.send(f"```Error occurred: {str(e)}```")
        spammings = False

    if spammings:
        await ctx.send("```Spamming in progress. Use .mspamoff to stop.```")

@bot.command()
async def mspamoff(ctx):
    global spammings
    spammings = False  
    await ctx.send("```Spamming stopped.```")

spammingss = False

@bot.command()
async def spam(ctx, *, message: str):
    global spammingss
    spammingss = True 
    await ctx.send(f"```Starting spam of '{message}'. Use .spamoff to stop.```")

    while spammingss:  
        await ctx.send(message) 
        await asyncio.sleep(0.05)


@bot.command()
async def spamoff(ctx):
    global spammingss
    spammingss = False 
    await ctx.send("```Spamming stopped.```")
editspamming = False


@bot.command()
async def cord(ctx, user: discord.User):
    global cord_mode, cord_user
    cord_mode = True
    cord_user = user
    await ctx.send(f"```cord mode enabled for {user.name}```")

@bot.command()
async def cordoff(ctx):
    global cord_mode, cord_user
    cord_mode = False
    cord_user = None
    await ctx.send("```cord mode disabled```")

mimic_user = None


@bot.group(invoke_without_command=True)
async def mimic(ctx, *, target: str = ""):
    user = await resolve_target_user(ctx, target)
    if user is None:
        await ctx.send("```Usage: .mimic @user  |  .mimic off```")
        return
    global mimic_user
    mimic_user = user
    await ctx.send(f"```Mimicking {user.display_name}. Use .mimic off to stop.```")


@mimic.command(name="off")
async def mimic_stop(ctx):
    global mimic_user
    if mimic_user is None:
        await ctx.send("```Not mimicking anyone.```")
        return
    mimic_user = None
    await ctx.send("```Mimic stopped.```")


@bot.command(name="mimicoff")
async def mimicoff(ctx):
    await mimic_stop(ctx)





@bot.command()
async def clearmsg(ctx, limit: int):
    
    await ctx.message.delete() 
    

    async for message in ctx.channel.history(limit=limit):
        if message.author == ctx.author:  
            try:
                await message.delete()
            except discord.HTTPException:
                print(f"Failed to delete message {message.id} due to a rate limit or permission issue.")
    

    await ctx.send(f"```Purged {limit} of your messages.```", delete_after=5)


@bot.command()
async def nickname(ctx, *, new_nickname: str):
    
    if ctx.guild:
        try:
            
            await ctx.guild.me.edit(nick=new_nickname)
            await ctx.send(f'```Nickname changed to: {new_nickname}```')
        except discord.Forbidden:
            await ctx.send('```Cannot change nickname```')
    else:
        await ctx.send('```This command can only be used in a server.```')


if not os.path.exists('pfps'):
    os.makedirs('pfps')





from datetime import datetime, timedelta
def time_since(dt):

    now = datetime.utcnow()
    delta = now - dt

    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"
    

bigspace = "                                "

@bot.command(aliases=['si'])
async def serverinfo(ctx, guild_id: int = None):
    guild = bot.get_guild(guild_id) if guild_id else ctx.guild
    if guild is None:
        await ctx.send("```Server not found — use in a server or .serverinfo <id>```")
        return

    try:
        owner = guild.owner
        if owner is None and guild.owner_id:
            owner = await guild.fetch_member(guild.owner_id)
        owner_name = owner.display_name if owner else "Unknown"
    except Exception:
        owner_name = "Unknown"

    text_channels = sum(1 for c in guild.channels if isinstance(c, discord.TextChannel))
    voice_channels = sum(1 for c in guild.channels if isinstance(c, discord.VoiceChannel))
    created = guild.created_at.strftime("%Y-%m-%d")

    msg = (
        f"```ansi\n"
        f"{blue}Server: {white}{guild.name}{reset}\n"
        f"{blue}ID: {white}{guild.id}{reset}\n"
        f"{blue}Owner: {white}{owner_name}{reset}\n"
        f"{blue}Created: {white}{created}{reset}\n"
        f"{blue}Members: {white}{guild.member_count}{reset}\n"
        f"{blue}Channels: {white}{text_channels} text / {voice_channels} voice{reset}\n"
        f"{blue}Roles: {white}{len(guild.roles)}{reset}  "
        f"{blue}Emojis: {white}{len(guild.emojis)}{reset}\n"
        f"{blue}Boosts: {white}{guild.premium_subscription_count or 0}{reset}  "
        f"{blue}Level: {white}{guild.premium_tier}{reset}\n"
        f"```"
    )
    await ctx.send(msg[:2000])



@bot.command(aliases=['ui', 'whois'])
async def userinfo(ctx, member: discord.Member = None):
    # void tools module
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    if not member:
        member = ctx.author

    try:
        member = await ctx.guild.fetch_member(member.id)
        owner_field = f"{white}{member.name}\n{bigspace}{text_color}ID: {white}{member.id}"
    except Exception as e:
        owner_field = f"Error fetching user: {str(e)}"
        print(f"Error fetching user info for {member.name}: {e}")

    creation_date = member.created_at
    formatted_creation = f"{creation_date.strftime('%Y-%m-%d')} (Created {time_since(creation_date)})"

    joined_date = member.joined_at.strftime('%Y-%m-%d') if member.joined_at else "N/A"
   
    response = f"""```ansi
        {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
                                {text_color}User Name: {white}{member.name}
                                {text_color}User ID: {white}{member.id}
                                {text_color}Created On: {white}{formatted_creation}
                                {text_color}Joined On: {white}{joined_date}
        {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 

                        {white}⠤⣤⣤⣤⣄⣀⣀⣀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣠⣤⠤⠤⠤⠤
                        ⢠⣤⣤⡄⣤⣤⣤⠄⣀⠉⣉⣙⠒⠤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠴⠘⣉⢡⣤⡤⠐⣶⡆⢶⠀⣶⣶⡦
                        ⣄⢻⣿⣧⠻⠇⠋⠀⠋⠀⢘⣿⢳⣦⣌⠳⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠞⣡⣴⣧⠻⣄⢸⣿⣿⡟⢁⡻⣸⣿⡿⠁
                        ⠈⠃⠙⢿⣧⣙⠶⣿⣿⡷⢘⣡⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⣷⣝⡳⠶⠶⠾⣛⣵⡿⠋⠀⠀
                        ⠀⠀⠀⠀⠉⠻⣿⣶⠂⠘⠛⠛⠛⢛⡛⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠛⠀⠉⠒⠛⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀{accent_color}⣿⡇⠀⠀⠀⠀⠀⢸⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⣾⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⢻⡁⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠘⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
```"""

    await ctx.send(response)




@bot.command(aliases=['emojisteal'])
async def steal(ctx, emoji: str, name: str = "voidtools"):

    

    custom_emoji_match = re.match(r'<(a)?:\w+:(\d+)>', emoji)
    
    if custom_emoji_match:

        is_animated = bool(custom_emoji_match.group(1))
        emoji_id = custom_emoji_match.group(2)


        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if is_animated else 'png'}"


        async with aiohttp.ClientSession() as session:
            async with session.get(emoji_url) as response:
                if response.status == 200:
                    emoji_data = await response.read()

                    guild = ctx.guild
                    try:
                        new_emoji = await guild.create_custom_emoji(name=name, image=emoji_data)
                        await ctx.send(f"```Emoji stolen successfully as {new_emoji.name}```")
                    except discord.Forbidden:
                        await ctx.send("```You don't have permission to add emojis in this server.```")
                    except discord.HTTPException:
                        await ctx.send("```Failed to add emoji. The server might be at the emoji limit.```")
                else:
                    await ctx.send("```Failed to retrieve the emoji. Make sure it's a valid custom emoji.```")
    else:
        await ctx.send("Missing Emoji.")


@bot.command()
async def tokengrab(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author  


    loading_message = await ctx.send(f"```ansi\nProcessing the token grab for {blue}{user.display_name}...```")
    await asyncio.sleep(1)
    await loading_message.edit(content=f"```ansi\n{user.display_name} : This is real. {red}BE AWARE```")
    await asyncio.sleep(1)
    await loading_message.edit(content=f"```ansi\n{user.display_name} : This is real. {red}BE AWARE..```")
    await asyncio.sleep(1)
    await loading_message.edit(content=f"```ansi\n{user.display_name} : This is real. {red}BE AWARE...```")
    await asyncio.sleep(1)
    await loading_message.edit(content=f"```ansi\n{user.display_name} : This is real. {red}BE AWARE....```")
    await asyncio.sleep(1)
    await loading_message.edit(content=f"```ansi\n{user.display_name} : This is real. {red}BE AWARE.....```")
    await asyncio.sleep(1)
    await loading_message.edit(content=f"```ansi\n{user.display_name} : This is real. {red}BE AWARE......```")
    await asyncio.sleep(1)
    await loading_message.edit(content=f"```ansi\n{user.display_name} : {red}HAHA IM DONE.```")
    await asyncio.sleep(1)
    user_id_str = str(user.id)
    

    encoded_user_id = base64.b64encode(user_id_str.encode()).decode()
    

    await loading_message.edit(content=f"```ansi\n{user.display_name} : {red}{encoded_user_id}```")


forced_disconnections = {}

@bot.command()
async def forcedc(ctx, action: str, user: discord.Member = None):
    if action not in ['toggle', 'list', 'clear']:
        await ctx.send("```Please use.\n[p]forcedc toggle\n[p]forcedc list\n[p]forcedc clear```")
        return

    if action == 'toggle':
        if user is None:
            user = ctx.author 


        if user.id not in forced_disconnections:
            forced_disconnections[user.id] = user
            await ctx.send(f"```{user.display_name} will now be forced disconnected from voice channels.```")
        else:
            del forced_disconnections[user.id]
            await ctx.send(f"```{user.display_name} is no longer forced to be disconnected from voice channels.```")

    elif action == 'list':
        if forced_disconnections:
            user_list = ', '.join([f"<@{user_id}>" for user_id in forced_disconnections.keys()])
            await ctx.send(f"```Currently forced disconnected users:\n{user_list}```")
        else:
            await ctx.send("```No users are currently forced disconnected.```")

    elif action == 'clear':
        forced_disconnections.clear()
        await ctx.send("```All forced disconnections have been cleared.```")







@bot.command()
async def dreact(ctx, user: discord.User, *emojis):
    if not emojis:
        await ctx.send("```Please provide at least one emoji```")
        return
        
    dreact_users[user.id] = [list(emojis), 0]  # [emojis_list, and then current index cuz why not >.<]
    await ctx.send(f"```Now alternating reactions with {len(emojis)} emojis on {user.name}'s messages```")

@bot.command()
async def dreactoff(ctx, user: discord.User):
    if user.id in dreact_users:
        del dreact_users[user.id]
        await ctx.send(f"```Stopped reacting to {user.name}'s messages```")
    else:
        await ctx.send("```This user doesn't have dreact enabled```")





webhookcopy_status = {}
webhook_urls = {}

@bot.command()
async def webhookcopy(ctx):
    avatar_url = str(ctx.author.avatar_url) if ctx.author.avatar else str(ctx.author.default_avatar_url)

    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            if response.status == 200:
                avatar_data = io.BytesIO(await response.read())
                webhook = await ctx.channel.create_webhook(name=ctx.author.display_name, avatar=avatar_data.read())
                

                webhook_urls[ctx.author.id] = webhook.url
                webhookcopy_status[ctx.author.id] = True
                
                await ctx.send("```Webhook has been created and webhook copying is enabled.```")
            else:
                await ctx.send("```Failed to fetch avatar for webhook.```")

@bot.command()
async def webhookcopyoff(ctx):
    webhookcopy_status[ctx.author.id] = False
    await ctx.send("```Webhook copy has been disabled for you.```")

@bot.command(aliases=['av', 'pfp'])
async def avatar(ctx, *, target: str = ""):
    user = await resolve_target_user(ctx, target)
    if user is None:
        user = ctx.author
    avatar_url = user.display_avatar.replace(size=1024).url
    await ctx.send(f"```{user.display_name}'s avatar```\n[Void Tools]({avatar_url})")







@bot.command()
async def tempchannel(ctx, name: str = "Void Tools", duration: int = 5, unit: str = 'm'):
    time_multiplier = {
        's': 1,    # seconds
        'm': 60,   # minutes
        'h': 3600, # hours
        'd': 86400 # days - just incase your a fucking retard
    }

    if unit not in time_multiplier:
        await ctx.send("```Invalid time unit. Use 's' for seconds, 'm' for minutes, 'h' for hours, or 'd' for days.```")
        return

    total_seconds = duration * time_multiplier[unit]
    channel = await ctx.guild.create_text_channel(name)
    await ctx.send(f"```Temporary channel '{name}' created for {duration} {unit}```")
    await asyncio.sleep(total_seconds)  
    await channel.delete()
    await ctx.send(f"```Temporary channel '{name}' deleted after {duration} {unit}```")

@bot.command()
async def createchannel(ctx, name: str = "Void Tools"):
    if ctx.author.guild_permissions.manage_channels:
        await ctx.guild.create_text_channel(name)
        await ctx.send(f"```channel '{name}' created.```")
    else:
        await ctx.send("```You don't have permission to create text channels.```")

@bot.command()
async def createvc(ctx, name: str = "Void Tools VC"):
    if ctx.author.guild_permissions.manage_channels:
        await ctx.guild.create_voice_channel(name)
        await ctx.send(f"```voice channel '{name}' created.```")
    else:
        await ctx.send("```You don't have permission to create voice channels.```")

@bot.command()
async def createrole(ctx, *, name: str = "Void Tools role"):
    guild = ctx.guild
    try:
        role = await guild.create_role(name=name)
        await ctx.send(f"```Role '{role.name}' has been created successfully.```")
    except discord.Forbidden:
        await ctx.send("```You don't have the required permissions to create a role.```")
    except discord.HTTPException as e:
        await ctx.send(f"```An error occurred: {e}```")

@bot.command()
async def createguild(ctx, *, name: str = "Void Tools Server"):
    try:
        new_guild = await bot.create_guild(name=name)
        await ctx.send(f"```Server '{new_guild.name}' has been created successfully.```")
    except discord.HTTPException as e:
        await ctx.send(f"```Failed to create server: {e}```")

@bot.command()
async def tempvc(ctx, name: str = "Void Tools VC", duration: int = 5, unit: str = 'm'):
    time_multiplier = {
        's': 1,    # seconds
        'm': 60,   # minutes
        'h': 3600, # hours
        'd': 86400 # days - just incase your a fucking retard
    }

    if unit not in time_multiplier:
        await ctx.send("```Invalid time unit. Use 's' for seconds, 'm' for minutes, 'h' for hours, or 'd' for days.```")
        return

    total_seconds = duration * time_multiplier[unit]
    channel = await ctx.guild.create_voice_channel(name)
    await ctx.send(f"```Temporary voice channel '{name}' created for {duration} {unit}```")
    await asyncio.sleep(total_seconds)  
    await channel.delete()
    await ctx.send(f"```Temporary voice channel '{name}' deleted after {duration} {unit}```")


async def get_last_online(user_id):
    base_url = "https://presence.roproxy.com/v1/presence/last-online"
    data = {
        "userIds": [user_id]
    }
    

    print("Requesting last online data for user ID:", user_id)
    
    try:
        response = requests.post(base_url, json=data)


        print(f"Response Status: {response.status_code}")
        print("Response Content:", response.text)

        if response.status_code != 200:
            return None  

        return response.json()  

    except Exception as e:
        print("Error fetching last online data:", e)
        return None
    

def calculate_time_ago(timestamp):

    now = datetime.now()
    difference = now - timestamp
    days, seconds = difference.days, difference.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if days > 0:
        return f"{days} days, {hours} hours, {minutes} minutes ago"
    elif hours > 0:
        return f"{hours} hours, {minutes} minutes ago"
    else:
        return f"{minutes} minutes ago"
    
@bot.command()
async def roblox(ctx, *, username: str):

    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    async with ctx.typing():
        import datetime
        import requests

        user_search_url = "https://users.roblox.com/v1/usernames/users"
        response = requests.post(user_search_url, json={"usernames": [username]})

        if response.status_code != 200:
            await ctx.send(f"```Error retrieving user data: {response.status_code} - {response.text}```")
            return

        user_data = response.json()

        if 'data' not in user_data or len(user_data['data']) == 0:
            await ctx.send(f"```No Roblox user found with the username: {username}```")
            return

        roblox_user = user_data['data'][0]
        roblox_id = roblox_user.get('id')
        roblox_name = roblox_user.get('name', "Unknown User")
        roblox_display_name = roblox_user.get('displayName', "Unknown Display Name")

        user_info_url = f"https://users.roblox.com/v1/users/{roblox_id}"
        user_info_response = requests.get(user_info_url)

        if user_info_response.status_code != 200:
            await ctx.send(f"```Error retrieving user information: {user_info_response.status_code} - {user_info_response.text}```")
            return

        user_info = user_info_response.json()
        roblox_bio = user_info.get('description', "No bio available")
        created_at = user_info.get('created', None)

        follower_count_url = f"https://friends.roproxy.com/v1/users/{roblox_id}/followers/count"
        follower_response = requests.get(follower_count_url)

        if follower_response.status_code != 200:
            await ctx.send(f"```Error retrieving follower count: {follower_response.status_code} - {follower_response.text}```")
            return

        follower_data = follower_response.json()
        follower_count = follower_data.get('count', 0)


        following_count_url = f"https://friends.roblox.com/v1/users/{roblox_id}/followings/count"
        following_response = requests.get(following_count_url)

        if following_response.status_code != 200:
            await ctx.send(f"```Error retrieving following count: {following_response.status_code} - {following_response.text}```")
            return

        following_data = following_response.json()
        following_count = following_data.get('count', 0)


        badges_url = f"https://accountinformation.roblox.com/v1/users/{roblox_id}/roblox-badges"
        badges_response = requests.get(badges_url)

        if badges_response.status_code != 200:
            await ctx.send(f"```Error retrieving badges: {badges_response.status_code} - {badges_response.text}```")
            return

        badges = badges_response.json()


        presence_url = "https://presence.roproxy.com/v1/presence/users"
        presence_response = requests.post(presence_url, json={"userIds": [roblox_id]})

        if presence_response.status_code != 200:
            await ctx.send(f"```Error retrieving presence status: {presence_response.status_code} - {presence_response.text}```")
            return

        presence_data = presence_response.json()
        user_presence = presence_data['userPresences'][0]

        presence_status = ["Offline", "Online", "In Game", "In Studio"]
        presence_name = presence_status[user_presence['userPresenceType']]

    last_online_data = await get_last_online(roblox_id)

    last_online = None
    if last_online_data and "lastOnlineTimestamps" in last_online_data:
        last_online = last_online_data['lastOnlineTimestamps'][0]['lastOnline']

    if created_at:
        created_timestamp = datetime.datetime.fromisoformat(created_at[:-1])  
        last_online_timestamp = datetime.datetime.fromisoformat(last_online[:-1]) if last_online else None
        time_difference = datetime.datetime.now() - created_timestamp



        days, seconds = time_difference.days, time_difference.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60


        time_ago = f"{days} days, {hours} hours, {minutes} minutes ago" if days > 0 else f"{hours} hours, {minutes} minutes ago"

        last_online_display = calculate_time_ago(last_online_timestamp) if last_online_timestamp else "Never"
        formatted_date = created_timestamp.strftime('%Y-%m-%d')  


        max_length = max(len("User:"), len("Bio:"), len("Created:"), len("Presence:"), len("Following:"), len("Followers:"), len("Badges:"))
        badge_names = ', '.join(badge['name'] for badge in badges) if badges else "None"
        bio_length = len(roblox_bio)
        bio_padding = (max_length - bio_length) // 2
        centered_bio = " " * bio_padding + roblox_bio

        message = f"""```ansi

                {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
                                    {accent_color}User: {white}{roblox_name} (@{roblox_display_name})
                                    {accent_color}Created: {white}{formatted_date} ({time_ago}).
                                    {accent_color}Presence: {white}{presence_name}
                                    {accent_color}Last Online: {white}{last_online_display}
                                    {accent_color}Following: {white}{following_count}
                                    {accent_color}Followers: {white}{follower_count}
                                    {accent_color}Badges ({len(badges) if badges else 0}): {white}{badge_names}

                {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
{white}
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣤⣤⣤⣤⣄⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⠶⣻⠝⠋⠠⠔⠛⠁⡀⠀⠈⢉⡙⠓⠶⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠞⢋⣴⡮⠓⠋⠀⠀⢄⠀⠀⠉⠢⣄⠀⠈⠁⠀⡀⠙⢶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠞⢁⣔⠟⠁⠀⠀⠀⠀⠀⠈⡆⠀⠀⠀⠈⢦⡀⠀⠀⠘⢯⢢⠙⢦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡼⠃⠀⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠸⠀⠀⠀⠀⠀⢳⣦⡀⠀⠀⢯⠀⠈⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⠆⡄⢠⢧⠀⣸⠀⠀⠀⠀⠀⠀⠀⢰⠀⣄⠀⠀⠀⠀⢳⡈⢶⡦⣿⣷⣿⢉⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣯⣿⣁⡟⠈⠣⡇⠀⠀⢸⠀⠀⠀⠀⢸⡄⠘⡄⠀⠀⠀⠈⢿⢾⣿⣾⢾⠙⠻⣾⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⡿⣮⠇⢙⠷⢄⣸⡗⡆⠀⢘⠀⠀⠀⠀⢸⠧⠀⢣⠀⠀⠀⡀⡸⣿⣿⠘⡎⢆⠈⢳⣽⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⢠⡟⢻⢷⣄⠀⠀⠀⠀⠀⠀⣾⣳⡿⡸⢀⣿⠀⠀⢸⠙⠁⠀⠼⠀⠀⠀⠀⢸⣇⠠⡼⡤⠴⢋⣽⣱⢿⣧⠀⢳⠈⢧⠀⢻⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⢀⡿⣠⡣⠃⣿⠃⠀⠀⠀⠀⣸⣳⣿⠇⣇⢸⣿⢸⣠⠼⠀⠀⠀⡇⠀⡀⠉⠒⣾⢾⣆⢟⣳⡶⠓⠶⠿⢼⣿⣇⠈⡇⠘⢆⠈⢿⡘⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠈⢷⣍⣤⡶⣿⡄⠀⠀⠀⢠⣿⠃⣿⠀⡏⢸⣿⣿⠀⢸⠀⠀⢠⡗⢀⠇⠀⢠⡟⠀⠻⣾⣿⠀⠀⠀⠀⡏⣿⣿⡀⢹⡀⠈⢦⠈⢷⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢁⣤⣄⠁⠀⠀⠀⣼⡏⢰⣟⠀⣇⠘⣿⣿⣾⣾⣆⢀⣾⠃⣼⢠⣶⣿⣭⣷⣶⣾⣿⣤⠀⠀⠀⡇⡯⣍⣧⠀⣷⠄⠈⢳⡀⢻⡁⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠺⣿⡿⠀⠀⠀⠀⡿⢀⣾⣧⠀⡗⡄⢿⣿⡙{accent_color}⣽⣿⣟{white}⠛⠚⠛⠙⠉{accent_color}⢹⣿⣿⣦{white}⠀⢸⡿⠀⠀⠀⢰⡯⣌⢻⡀⢸⢠⢰⡄⠹⡷⣿⣦⣤⠤⣶⡇⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⣇⣾⣿⢸⢠⣧⢧⠘⣿⡇{accent_color}⠸⣿⢿⡆{white}⠀⠀⠀⠀{accent_color}⠘⣯⠇⣿⠂⣸⢰{white}⠀⠀⢀⣸⡧⣊⣼⡇⢸⣼⣸⣷⢣⢻⣄⠉⠙⠛⠉⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣳⣤⣴⣿⣏⣿⣾⢸⣿⡘⣧⣘⢿⣀{accent_color}⡙⣞⠁{white}⠀⠀⠀⠀{accent_color}⢀⡬⢀⣉⢠⣧⡏{white}⠀⠀⡎⣿⣿⣿⣿⠃⣸⡏⣿⣿⡎⢿⡘⡆⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⣠⣼⣿⣿⣿⣼⣿⣧⢿⣿⣿⣯⡻⠟⠀⠀⠀⠀⠀{accent_color}⠐⢯⠣⡽⢟⣽{white}⠀⠀⢘⡇⣿⣿⣿⡟⣴⣿⣷⣿⣿⣧⣿⣷⡽⠀⠀⠀⠀⠀⠀⠀{white}
                    ⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣼⣹⣿⣇⣸⣿⣿⣿⣻⣚⣿⡿⣿⣿⣦⣤⣀⡉⠃⠀⢀⣀⣤⡶⠛⡏⠀⢀⣼⢸⣿⣿⣿⣿⣿⣿⣿⢋⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀
                    ⣿⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠒⠒⠒⢭⢻⣽⣿⣿⣿⣿⣿⣿⢿⠿⣿⡏⠀⡼⠁⣀⣾⣿⣿⣿⣿⡿⣿⣿⣟⡻⣿⣿⡿⠣⠟⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠸⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢧⢿⣯⡽⠿⠛⠋⣵⢟⣋⣿⣶⣞⣤⣾⣿⣿⡟⢉⡿⢋⠻⢯⡉⢻⡟⢿⡅⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⢻⡄⠀⠀{blue}Void Tools was here{white}    ⠘⡞⣿⣆⡀⠀⡼⡏⠉⠚⠭⢉⣠⠬⠛⠛⢁⡴⣫⠖⠁⠀⠀⣩⠟⠁⣸⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠈⢷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣽⣿⣿⣾⠳⡙⣦⡤⠜⠊⠁⠀⣀⡴⠯⠾⠗⠒⠒⠛⠛⠛⠛⠛⠓⠿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠘⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢷⣻⣿⣿⠔⢪⠓⠬⢍⠉⣩⣽⢻⣤⣶⣦⠀⠀⠀⢀⣀⣤⣴⣾⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠹⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣾⡏⢦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣯⣿⣿⠀⠀⣇⠀⣠⠎⠁⢹⡎⡟⡏⣷⣶⠿⠛⡟⠛⠛⣫⠟⠉⢿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⢻⡄⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣷⠈⢷⡤⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣾⣷⡀⣀⣀⣷⡅⠀⠀⠈⣷⢳⡇⣿⠀⠀⣸⠁⢠⡾⣟⣛⣻⣟⡿⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⢷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢯⢻⣏⡵⠿⠿⢤⣄⠀⢀⣿⢸⣹⣿⣀⣴⣿⣴⣿⣛⠋⠉⠉⡉⠛⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠘⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⡎⣿⣥⣶⠖⢉⣿⡿⣿⣿⡿⣿⣟⠿⠿⣿⣿⣿⡯⠻⣿⣿⣿⣷⡽⣿⡗⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠸⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡘⣿⣩⠶⣛⣋⡽⠿⣷⢬⣙⣻⣿⣿⣿⣯⣛⠳⣤⣬⡻⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀
                    ⠀⣿⣛⣻⣿⡿⠿⠟⠗⠶⠶⠶⠶⠤⠤⢤⠤⡤⢤⣤⣤⣤⣤⣄⣀⣀⣀⣀⣀⣀⣀⣀⣣⢹⣷⣶⣿⣿⣦⣴⣟⣛⣯⣤⣿⣿⣿⣿⣿⣷⣌⣿⣿⣿⣿⣿⣿⣿⣤⣤⣤⣤⣤⣤⣄
                    ⠀⠉⠙⠛⠛⠛⠛⠛⠻⠿⠿⠿⠷⠶⠶⢶⣶⣶⣶⣶⣤⣤⣤⣤⣤⣥⣬⣭⣭⣉⣩⣍⣙⣏⣉⣏⣽⣶⣶⣶⣤⣤⣬⣤⣤⣾⣿⠶⠾⠿⠿⠿⠿⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠃
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠉⠉⠉⠛⠛⠛⠛⠛⠛⠋⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
```
"""

    await ctx.send(message)


@bot.command()
async def pin(ctx):

    if ctx.message.reference:
        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    else:

        async for msg in ctx.channel.history(limit=2):
            if msg.id != ctx.message.id: 
                message = msg
                break
        else:
            await ctx.send("```Could not find a message to pin.```")
            return


    try:
        await message.pin()
        await ctx.send("```Message pinned successfully.```")
    except discord.Forbidden:
        await ctx.send("```I do not have permission to pin messages in this channel.```")
    except discord.HTTPException as e:
        await ctx.send(f"```An error occurred: {e}```")


@bot.command()
async def servername(ctx, *, new_name: str = None):

    guild = ctx.guild
    if guild is None:
        await ctx.send("```This command can only be used in a server.```")
        return
    
    if guild.me.guild_permissions.manage_guild:
        if new_name:
            try:
                await guild.edit(name=new_name)
                await ctx.send(f"```Server name changed to: {new_name}```")
            except discord.Forbidden:
                await ctx.send("```Failed to change the server name due to insufficient permissions.```")
            except discord.HTTPException as e:
                await ctx.send(f"```An error occurred: {e}```")
        else:
            await ctx.send("```Please provide a new server name.```")
    else:
        await ctx.send("```I do not have permission to change the server name.```")







@bot.command()
async def backupserver(ctx):
    if ctx.guild is None:
        await ctx.send("```Use in a server.```")
        return
    try:
        guild = ctx.guild
        server_data = {
            "name": guild.name,
            "id": guild.id,
            "icon_url": guild.icon.url if guild.icon else None,
            "roles": {},
            "channels": [],
            "categories": [],
            "voice_channels": [],
        }

        for role in guild.roles:
            if role.name != "@everyone":
                server_data["roles"][str(role.id)] = {
                    "name": role.name,
                    "permissions": role.permissions.value,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "position": role.position,
                    "mentionable": role.mentionable,
                }

        for category in guild.categories:
            server_data["categories"].append({
                "name": category.name,
                "position": category.position,
                "permissions": [
                    {
                        "id": str(target.id),
                        "allow": overwrite.pair()[0].value,
                        "deny": overwrite.pair()[1].value,
                    }
                    for target, overwrite in category.overwrites.items()
                ],
            })

        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                channel_data = {
                    "name": channel.name,
                    "type": str(channel.type),
                    "position": channel.position,
                    "category": channel.category.name if channel.category else None,
                    "permissions": [
                        {
                            "id": str(target.id),
                            "allow": overwrite.pair()[0].value,
                            "deny": overwrite.pair()[1].value,
                        }
                        for target, overwrite in channel.overwrites.items()
                    ],
                }
                if isinstance(channel, discord.TextChannel):
                    channel_data.update({
                        "topic": channel.topic,
                        "nsfw": channel.nsfw,
                        "slowmode_delay": channel.slowmode_delay,
                    })
                    server_data["channels"].append(channel_data)
                else:
                    channel_data.update({
                        "bitrate": channel.bitrate,
                        "user_limit": channel.user_limit,
                    })
                    server_data["voice_channels"].append(channel_data)

        backup_file_name = f"{guild.id}_backup.json"
        with open(backup_file_name, "w", encoding="utf-8") as handle:
            json.dump(server_data, handle, indent=4)

        await ctx.send(
            f"```Backup saved: {backup_file_name}\n"
            f"Roles: {len(server_data['roles'])}\n"
            f"Text: {len(server_data['channels'])} | Voice: {len(server_data['voice_channels'])}\n"
            f"Categories: {len(server_data['categories'])}```"
        )
    except Exception as exc:
        await ctx.send(f"```Backup failed: {exc}```")

@bot.command()
async def pasteserver(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]
    guild = ctx.guild
    any_text_channel = None

    backup_files = [f for f in os.listdir() if f.endswith("_backup.json")]
    await ctx.send("```Attempting to restore server.```")

    if not backup_files:
        await ctx.send("```No backup file found. Please run `.restoreserver` first.```")
        return

    if len(backup_files) > 1:

        backup_file_list = "\n".join([f"{i + 1}: {file}" for i, file in enumerate(backup_files)])
        await ctx.send(f"```Multiple backup files found:\n{backup_file_list}\nPlease select a file by typing the number.```")
        

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and 1 <= int(m.content) <= len(backup_files)
        
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            selected_index = int(msg.content) - 1
            backup_file = backup_files[selected_index]
        except Exception:
            await ctx.send("```No valid selection made. Aborting the restore operation.```")
            return
    else:

        backup_file = backup_files[0]


    try:
        with open(backup_file, "r") as f:
            server_data = json.load(f)
    except json.JSONDecodeError:
        await ctx.send("```Backup file is empty or invalid JSON. Please create a valid backup first.```")
        return

    for role in guild.roles:
        if role.name != "@everyone":
            try:
                await role.delete()
                await asyncio.sleep(1)
            except discord.Forbidden:
                continue

    for channel in guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(1)
        except discord.Forbidden:
            continue

    if server_data.get("name"):
        await guild.edit(name=server_data["name"])
    if server_data.get("icon_url"):
        async with aiohttp.ClientSession() as session:
            async with session.get(server_data["icon_url"]) as resp:
                if resp.status == 200:
                    icon_bytes = await resp.read()
                    await guild.edit(icon=icon_bytes)

    role_map = {} 
    for role_id, role_data in server_data.get("roles", {}).items():
        role = await guild.create_role(
            name=role_data["name"],
            permissions=discord.Permissions(role_data["permissions"]),
            color=discord.Color(role_data["color"]),
            hoist=role_data["hoist"],
            mentionable=role_data["mentionable"]
        )
        role_map[role_id] = role
        await asyncio.sleep(1)

    for category_data in server_data.get("categories", []):
        overwrites = {}
        for perm in category_data.get("permissions", []):
            target_id = perm["id"]
            target = role_map.get(target_id) or guild.get_member(int(target_id))
            if target:
                overwrites[target] = discord.PermissionOverwrite.from_pair(
                    discord.Permissions(perm["allow"]),
                    discord.Permissions(perm["deny"])
                )

        category = await guild.create_category(
            name=category_data["name"],
            overwrites=overwrites,
            position=category_data.get("position", 0)
        )
        await asyncio.sleep(1)

    for channel_data in server_data.get("channels", []):
        category = discord.utils.get(guild.categories, name=channel_data.get("category"))
        
        overwrites = {}
        for perm in channel_data.get("permissions", []):
            target_id = perm["id"]
            target = role_map.get(target_id) or guild.get_member(int(target_id))
            if target:
                overwrites[target] = discord.PermissionOverwrite.from_pair(
                    discord.Permissions(perm["allow"]),
                    discord.Permissions(perm["deny"])
                )

        channel_settings = {
            "name": channel_data["name"],
            "overwrites": overwrites,
            "category": category,
            "position": channel_data.get("position", 0),
            "topic": channel_data.get("topic"),
            "nsfw": channel_data.get("nsfw", False),
            "slowmode_delay": channel_data.get("slowmode_delay", 0)
        }

        await guild.create_text_channel(**channel_settings)
        await asyncio.sleep(1)

    for channel_data in server_data.get("voice_channels", []):
        category = discord.utils.get(guild.categories, name=channel_data.get("category"))
        
        overwrites = {}
        for perm in channel_data.get("permissions", []):
            target_id = perm["id"]
            target = role_map.get(target_id) or guild.get_member(int(target_id))
            if target:
                overwrites[target] = discord.PermissionOverwrite.from_pair(
                    discord.Permissions(perm["allow"]),
                    discord.Permissions(perm["deny"])
                )

        channel_settings = {
            "name": channel_data["name"],
            "overwrites": overwrites,
            "category": category,
            "position": channel_data.get("position", 0),
            "bitrate": channel_data.get("bitrate", 64000),
            "user_limit": channel_data.get("user_limit", 0)
        }

        await guild.create_voice_channel(**channel_settings)
        await asyncio.sleep(1)


    restored_role_count = len(server_data.get("roles", []))
    restored_channel_count = len(server_data.get("channels", []))
    restored_category_count = len(server_data.get("categories", []))
    restored_voice_channel_count = len(server_data.get("voice_channels", []))

    if any_text_channel is None:
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                any_text_channel = channel
                break

    if any_text_channel is not None:
        await any_text_channel.send(f"""```ansi
                {blue}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
                                                            {highlight_color}RESTORE COMPLETE
                                            
                                            {text_color}Server configuration has been {white}restored
                                            {text_color}Roles restored: {white}{restored_role_count}
                                            {text_color}Channels restored: {white}{restored_channel_count}
                                            {text_color}Categories restored: {white}{restored_category_count} 
                                            {text_color}Voice Channels restored: {white}{restored_voice_channel_count}.

                {blue}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
{white}
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣤⣤⣤⣤⣄⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⠶⣻⠝⠋⠠⠔⠛⠁⡀⠀⠈⢉⡙⠓⠶⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠞⢋⣴⡮⠓⠋⠀⠀⢄⠀⠀⠉⠢⣄⠀⠈⠁⠀⡀⠙⢶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠞⢁⣔⠟⠁⠀⠀⠀⠀⠀⠈⡆⠀⠀⠀⠈⢦⡀⠀⠀⠘⢯⢢⠙⢦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡼⠃⠀⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠸⠀⠀⠀⠀⠀⢳⣦⡀⠀⠀⢯⠀⠈⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⠆⡄⢠⢧⠀⣸⠀⠀⠀⠀⠀⠀⠀⢰⠀⣄⠀⠀⠀⠀⢳⡈⢶⡦⣿⣷⣿⢉⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣯⣿⣁⡟⠈⠣⡇⠀⠀⢸⠀⠀⠀⠀⢸⡄⠘⡄⠀⠀⠀⠈⢿⢾⣿⣾⢾⠙⠻⣾⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⡿⣮⠇⢙⠷⢄⣸⡗⡆⠀⢘⠀⠀⠀⠀⢸⠧⠀⢣⠀⠀⠀⡀⡸⣿⣿⠘⡎⢆⠈⢳⣽⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⢠⡟⢻⢷⣄⠀⠀⠀⠀⠀⠀⣾⣳⡿⡸⢀⣿⠀⠀⢸⠙⠁⠀⠼⠀⠀⠀⠀⢸⣇⠠⡼⡤⠴⢋⣽⣱⢿⣧⠀⢳⠈⢧⠀⢻⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⢀⡿⣠⡣⠃⣿⠃⠀⠀⠀⠀⣸⣳⣿⠇⣇⢸⣿⢸⣠⠼⠀⠀⠀⡇⠀⡀⠉⠒⣾⢾⣆⢟⣳⡶⠓⠶⠿⢼⣿⣇⠈⡇⠘⢆⠈⢿⡘⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠈⢷⣍⣤⡶⣿⡄⠀⠀⠀⢠⣿⠃⣿⠀⡏⢸⣿⣿⠀⢸⠀⠀⢠⡗⢀⠇⠀⢠⡟⠀⠻⣾⣿⠀⠀⠀⠀⡏⣿⣿⡀⢹⡀⠈⢦⠈⢷⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢁⣤⣄⠁⠀⠀⠀⣼⡏⢰⣟⠀⣇⠘⣿⣿⣾⣾⣆⢀⣾⠃⣼⢠⣶⣿⣭⣷⣶⣾⣿⣤⠀⠀⠀⡇⡯⣍⣧⠀⣷⠄⠈⢳⡀⢻⡁⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠺⣿⡿⠀⠀⠀⠀⡿⢀⣾⣧⠀⡗⡄⢿⣿⡙{accent_color}⣽⣿⣟{white}⠛⠚⠛⠙⠉{accent_color}⢹⣿⣿⣦{white}⠀⢸⡿⠀⠀⠀⢰⡯⣌⢻⡀⢸⢠⢰⡄⠹⡷⣿⣦⣤⠤⣶⡇⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⣇⣾⣿⢸⢠⣧⢧⠘⣿⡇{accent_color}⠸⣿⢿⡆{white}⠀⠀⠀⠀{accent_color}⠘⣯⠇⣿⠂⣸⢰{white}⠀⠀⢀⣸⡧⣊⣼⡇⢸⣼⣸⣷⢣⢻⣄⠉⠙⠛⠉⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣳⣤⣴⣿⣏⣿⣾⢸⣿⡘⣧⣘⢿⣀{accent_color}⡙⣞⠁{white}⠀⠀⠀⠀{accent_color}⢀⡬⢀⣉⢠⣧⡏{white}⠀⠀⡎⣿⣿⣿⣿⠃⣸⡏⣿⣿⡎⢿⡘⡆⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⣠⣼⣿⣿⣿⣼⣿⣧⢿⣿⣿⣯⡻⠟⠀⠀⠀⠀⠀{accent_color}⠐⢯⠣⡽⢟⣽{white}⠀⠀⢘⡇⣿⣿⣿⡟⣴⣿⣷⣿⣿⣧⣿⣷⡽⠀⠀⠀⠀⠀⠀⠀
                    ⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣼⣹⣿⣇⣸⣿⣿⣿⣻⣚⣿⡿⣿⣿⣦⣤⣀⡉⠃⠀⢀⣀⣤⡶⠛⡏⠀⢀⣼⢸⣿⣿⣿⣿⣿⣿⣿⢋⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀
                    ⣿⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠒⠒⠒⢭⢻⣽⣿⣿⣿⣿⣿⣿⢿⠿⣿⡏⠀⡼⠁⣀⣾⣿⣿⣿⣿⡿⣿⣿⣟⡻⣿⣿⡿⠣⠟⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠸⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢧⢿⣯⡽⠿⠛⠋⣵⢟⣋⣿⣶⣞⣤⣾⣿⣿⡟⢉⡿⢋⠻⢯⡉⢻⡟⢿⡅⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⢻⡄⠀⠀{blue}Void Tools was here{white}    ⠘⡞⣿⣆⡀⠀⡼⡏⠉⠚⠭⢉⣠⠬⠛⠛⢁⡴⣫⠖⠁⠀⠀⣩⠟⠁⣸⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠈⢷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣽⣿⣿⣾⠳⡙⣦⡤⠜⠊⠁⠀⣀⡴⠯⠾⠗⠒⠒⠛⠛⠛⠛⠛⠓⠿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠘⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢷⣻⣿⣿⠔⢪⠓⠬⢍⠉⣩⣽⢻⣤⣶⣦⠀⠀⠀⢀⣀⣤⣴⣾⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠹⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣾⡏⢦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣯⣿⣿⠀⠀⣇⠀⣠⠎⠁⢹⡎⡟⡏⣷⣶⠿⠛⡟⠛⠛⣫⠟⠉⢿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⢻⡄⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣷⠈⢷⡤⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣾⣷⡀⣀⣀⣷⡅⠀⠀⠈⣷⢳⡇⣿⠀⠀⣸⠁⢠⡾⣟⣛⣻⣟⡿⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⢷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢯⢻⣏⡵⠿⠿⢤⣄⠀⢀⣿⢸⣹⣿⣀⣴⣿⣴⣿⣛⠋⠉⠉⡉⠛⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠘⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⡎⣿⣥⣶⠖⢉⣿⡿⣿⣿⡿⣿⣟⠿⠿⣿⣿⣿⡯⠻⣿⣿⣿⣷⡽⣿⡗⠀⠀⠀⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠸⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡘⣿⣩⠶⣛⣋⡽⠿⣷⢬⣙⣻⣿⣿⣿⣯⣛⠳⣤⣬⡻⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀
                    ⠀⣿⣛⣻⣿⡿⠿⠟⠗⠶⠶⠶⠶⠤⠤⢤⠤⡤⢤⣤⣤⣤⣤⣄⣀⣀⣀⣀⣀⣀⣀⣀⣣⢹⣷⣶⣿⣿⣦⣴⣟⣛⣯⣤⣿⣿⣿⣿⣿⣷⣌⣿⣿⣿⣿⣿⣿⣿⣤⣤⣤⣤⣤⣤⣄
                    ⠀⠉⠙⠛⠛⠛⠛⠛⠻⠿⠿⠿⠷⠶⠶⢶⣶⣶⣶⣶⣤⣤⣤⣤⣤⣥⣬⣭⣭⣉⣩⣍⣙⣏⣉⣏⣽⣶⣶⣶⣤⣤⣬⣤⣤⣾⣿⠶⠾⠿⠿⠿⠿⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠃
                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠉⠉⠉⠛⠛⠛⠛⠛⠛⠋⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
```
""")
        
@bot.command()
async def clearbackup(ctx):
    guild_id = str(ctx.guild.id)
    json_file = f"{guild_id}_backup.json"


    initial_message = await ctx.send("Processing...")


    if os.path.exists(json_file):
        os.remove(json_file)
        response = f"```ansi\n{blue}Backup file {json_file} deleted successfully!```"
    else:
        response = f"```ansi\n{red}No backup file found for this server!```"


    files_deleted = False
    for file in os.listdir():
        if file.endswith("_backup.json"):
            os.remove(file)
            files_deleted = True

    if files_deleted:
        response += f"\n```ansi\n{blue}All backup JSON files deleted!```"


    await initial_message.edit(content=response)



@bot.command()
async def clearchannels(ctx):
    guild = ctx.guild
    

    confirm_message = await ctx.send("```Are you sure you want to delete all channels and categories? Type 'yes' to confirm.```")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:

        response = await bot.wait_for('message', check=check, timeout=30)
        if response.content.lower() != 'yes':
            await ctx.send("```Confirmation failed. No channels or categories were deleted.```")
            return
    except asyncio.TimeoutError:
        await ctx.send("```Confirmation timed out. No channels or categories were deleted.```")
        return
    

    for channel in guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(0.50)  
        except discord.Forbidden:
            await ctx.send(f"```ansi\n{red}I do not have permission to delete {channel.name}.```")
        except discord.HTTPException:
            await ctx.send(f"```ansi\n{red}Failed to delete {channel.name}.```")
    
    print("All channels and categories have been deleted!")




async def fetch_anime_gif(action):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.waifu.pics/sfw/{action}") as r:
            if r.status == 200:
                data = await r.json()
                return data['url']  
            else:
                return None
                
@bot.command(name="kiss")
async def kiss(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to kiss!```")
        return

    gif_url = await fetch_anime_gif("kiss")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} sends an anime kiss to {member.display_name}! 💋```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime kiss GIF right now, try again later!```")
@bot.command(name="slap")
async def slap(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to slap!```")
        return

    gif_url = await fetch_anime_gif("slap")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} slaps {member.display_name}! 👋```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime slap GIF right now, try again later!```")


@bot.command(name="hurt")
async def hurt(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to kill!```")
        return

    gif_url = await fetch_anime_gif("kill")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} kills {member.display_name}! ☠```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime kill GIF right now, try again later!```")

@bot.command(name="pat")
async def pat(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to pat!```")
        return

    gif_url = await fetch_anime_gif("pat")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} pats {member.display_name}! 🖐```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime pat GIF right now, try again later!```")

@bot.command(name="wave")
async def wave(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to wave at!```")
        return

    gif_url = await fetch_anime_gif("wave")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} waves at {member.display_name}! 👋```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime wave GIF right now, try again later!```")

@bot.command(name="hug")
async def hug(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to hug!```")
        return

    gif_url = await fetch_anime_gif("hug")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} hugs {member.display_name}! 🤗```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime hug GIF right now, try again later!```")

@bot.command(name="cuddle")
async def cuddle(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to cuddle!```")
        return

    gif_url = await fetch_anime_gif("cuddle")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} cuddles {member.display_name}! 🤗```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime cuddle GIF right now, try again later!```")

@bot.command(name="lick")
async def lick(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to lick!```")
        return

    gif_url = await fetch_anime_gif("lick")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} licks {member.display_name}! 😋```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime lick GIF right now, try again later!```")

@bot.command(name="bite")
async def bite(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to bite!```")
        return

    gif_url = await fetch_anime_gif("bite")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} bites {member.display_name}! 🐍```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime bite GIF right now, try again later!```")

@bot.command(name="bully")
async def bully(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to bully!```")
        return

    gif_url = await fetch_anime_gif("bully")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} bullies {member.display_name}! 😠```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime bully GIF right now, try again later!```")

@bot.command(name="poke")
async def poke(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to poke!```")
        return

    gif_url = await fetch_anime_gif("poke")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} pokes {member.display_name}! 👉👈```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime poke GIF right now, try again later!```")


@bot.command(name="dance")
async def dance(ctx):
    gif_url = await fetch_anime_gif("dance")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} dances! 💃```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime dance GIF right now, try again later!```")

@bot.command(name="cry")
async def cry(ctx):
    gif_url = await fetch_anime_gif("cry")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} is crying! 😢```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime cry GIF right now, try again later!```")

@bot.command(name="sleep")
async def sleep(ctx):
    gif_url = await fetch_anime_gif("sleep")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} is sleeping! 😴```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime sleep GIF right now, try again later!```")

@bot.command(name="blush")
async def blush(ctx):
    gif_url = await fetch_anime_gif("blush")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} just blushed.! 😊```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime blush GIF right now, try again later!```")

@bot.command(name="wink")
async def wink(ctx):
    gif_url = await fetch_anime_gif("wink")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} winks! 😉```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime wink GIF right now, try again later!```")

@bot.command(name="smile")
async def smile(ctx):
    gif_url = await fetch_anime_gif("smile")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} smiles! 😊```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime smile GIF right now, try again later!```")


@bot.command(name="highfive")
async def highfive(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to high-five!```")
        return

    gif_url = await fetch_anime_gif("highfive")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} high-fives {member.display_name}! 🙌```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime high-five GIF right now, try again later!```")

@bot.command(name="handhold")
async def handhold(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to hold hands with!```")
        return

    gif_url = await fetch_anime_gif("handhold")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} holds hands with {member.display_name}! 🤝```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime handhold GIF right now, try again later!```")

@bot.command(name="nom")
async def nom(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to nom!```")
        return

    gif_url = await fetch_anime_gif("nom")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} noms on {member.display_name}! 😋```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime nom GIF right now, try again later!```")

@bot.command(name="smug")
async def smug(ctx):
    gif_url = await fetch_anime_gif("smug")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} has a smug look! 😏```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime smug GIF right now, try again later!```")

@bot.command(name="bonk")
async def bonk(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to bonk!```")
        return

    gif_url = await fetch_anime_gif("bonk")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} bonks {member.display_name}! 🤭```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime bonk GIF right now, try again later!```")

@bot.command(name="yeet")
async def yeet(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("```You need to mention someone to yeet!```")
        return

    gif_url = await fetch_anime_gif("yeet")

    if gif_url:
        await ctx.send(f"```{ctx.author.display_name} yeets {member.display_name}! 💨```\n[Void Tools]({gif_url})")
    else:
        await ctx.send("```Couldn't fetch an anime yeet GIF right now, try again later!```")

@bot.command(name="ero")
async def ero(ctx, member: discord.Member = None):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=ero&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares some ero content```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later```")

@bot.command(name="ecchi")
async def ecchi(ctx, member: discord.Member = None):
    
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=ecchi&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares some ecchi```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")

@bot.command(name="hentai")
async def hentai(ctx, member: discord.Member = None):
    
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=hentai&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares some hentai```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")

@bot.command(name="uniform")
async def uniform(ctx, member: discord.Member = None):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=uniform&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares some uniform content```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")

@bot.command(name="maid")
async def maid(ctx, member: discord.Member = None):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=maid&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares some maid content```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")

@bot.command(name="oppai")
async def oppai(ctx, member: discord.Member = None):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=oppai&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares some oppai content```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")

@bot.command(name="selfies")
async def selfies(ctx, member: discord.Member = None):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=selfies&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares some selfies```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")

@bot.command(name="raiden")
async def raiden(ctx, member: discord.Member = None):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=raiden-shogun&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares Raiden content```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")

@bot.command(name="marin")
async def marin(ctx, member: discord.Member = None):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=marin-kitagawa&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"```{ctx.author.display_name} shares Marin content```\n[Void Tools]({image_url})")
            else:
                await ctx.send("```Failed to fetch image, try again later!```")
@bot.command()
async def leavegroups(ctx):
    left_count = 0
    for channel in ctx.bot.private_channels:
        if isinstance(channel, discord.GroupChannel):
            try:
                await channel.leave()
                left_count += 1
            except discord.HTTPException as e:
                await ctx.send(f"Failed to leave group {channel.name}: {e}")

    if left_count > 0:
        await ctx.send(f"Successfully left {left_count} groups.")
    else:
        await ctx.send("No groups found to leave.")


@bot.command()
async def firstmessage(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel  
    try:

        msg = None
        async for message in channel.history(limit=1, oldest_first=True):
            msg = message
            break
        if msg:
            await msg.reply("here.")
        else:
            await ctx.send("```No messages found in this channel.```")
    except Exception as e:
        await ctx.send(f"```Error: {str(e)}```")

ping_responses = {}

@bot.command()
async def pingresponse(ctx, action: str = None, *, response: str = None):
    global ping_responses
    if action is None:
        await ctx.send("```Usage: .pingresponse <message> | toggle | list | clear```")
        return

    action_lower = action.lower()
    if action_lower not in ("toggle", "list", "clear"):
        ping_responses[ctx.channel.id] = action if response is None else f"{action} {response}"
        await ctx.send(f"```Ping response set to: {ping_responses[ctx.channel.id]}```")
        return

    action = action_lower
    if action == "toggle":
        if ctx.channel.id in ping_responses:
            del ping_responses[ctx.channel.id]
            await ctx.send("```Ping response disabled for this channel.```")
        else:
            if response:
                ping_responses[ctx.channel.id] = response
                await ctx.send(f"```Ping response set to: {response}```")
            else:
                await ctx.send("```Please provide a response to set for pings.```")
    
    elif action == "list":
        if ctx.channel.id in ping_responses:
            await ctx.send(f"```Current ping response: {ping_responses[ctx.channel.id]}```")
        else:
            await ctx.send("```No custom ping response set for this channel.```")
    
    elif action == "clear":
        if ctx.channel.id in ping_responses:
            del ping_responses[ctx.channel.id]
            await ctx.send("```Ping response cleared for this channel.```")
        else:
            await ctx.send("```No custom ping response to clear for this channel.```")
    
    else:
        await ctx.send("```Invalid action. Use toggle, list, or clear.```")


insults_enabled = False  
autoinsults = [
    "your a skid",
    "stfu",
    "your such a loser",
    "fuck up boy",
    "no.",
    "why are you a bitch",
    "nigga you stink",
    "idk you",
    "LOLSSOL WHO ARE YOUa",
    "stop pinging me boy",
    "if your black stfu"
    
]

@bot.command(name="pinginsult")
async def pinginsult(ctx, action: str = None, *, insult: str = None):
    global insults_enabled

    if action is None:
        await ctx.send("```You need to specify an action: toggle, list, or clear.```")
        return

    if action.lower() == "toggle":
        insults_enabled = not insults_enabled  
        status = "enabled" if insults_enabled else "disabled"
        await ctx.send(f"```Ping insults are now {status}!```")

    elif action.lower() == "list":
        if autoinsults:
            insult_list = "\n".join(f"- {insult}" for insult in autoinsults)
            await ctx.send(f"```Current ping insults:\n{insult_list}```")
        else:
            await ctx.send("```No insults found in the list.```")

    elif action.lower() == "clear":
        autoinsults.clear()
        await ctx.send("```Ping insults cleared!```")

    else:
        await ctx.send("```Invalid action. Use toggle, list, or clear.```")

reactions_enabled = False  
custom_reaction = "😜"  
@bot.command(name="pingreact")
async def pingreact(ctx, action: str = None, reaction: str = None):
    global reactions_enabled, custom_reaction

    if action is None:
        await ctx.send("```You need to specify an action: toggle, list, clear, or set.```")
        return

    if action.lower() == "toggle":

        if reaction:
            custom_reaction = reaction  
            reactions_enabled = not reactions_enabled  
            status = "enabled" if reactions_enabled else "disabled"
            await ctx.send(f"```Ping reactions {status}! Custom reaction set to: {custom_reaction}```")
        else:
            reactions_enabled = not reactions_enabled  
            status = "enabled" if reactions_enabled else "disabled"
            await ctx.send(f"```Ping reactions {status}!```")

    elif action.lower() == "list":
        if reactions_enabled:
            await ctx.send(f"```Ping reactions are currently enabled. Current reaction: {custom_reaction}```")
        else:
            await ctx.send("```Ping reactions are currently disabled.```")

    elif action.lower() == "clear":
        reactions_enabled = False  
        await ctx.send("```Ping reactions cleared!```")

    else:
        await ctx.send("```Invalid action. Use toggle, list, or clear.```")



fake_activity_active = False
tokenss = []  
async def read_tokens():
    try:
        with open('token.txt', 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []

async def send_fake_reply(token, channel_id, message, response, delay):
    await asyncio.sleep(delay)  

    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://discord.com/api/v9/channels/{channel_id}/typing', headers=headers):
            await asyncio.sleep(random.uniform(2, 5))  

        payload = {
            'content': message
        }
        
        async with session.post(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers, json=payload) as resp:
            if resp.status == 200:
                print(f"Message sent successfully with token: {token[-4:]}")
                
                sent_message_data = await resp.json()
                sent_message_id = sent_message_data['id']


                await asyncio.sleep(3)  
                
                async with session.post(f'https://discord.com/api/v9/channels/{channel_id}/typing', headers=headers):
                    await asyncio.sleep(random.uniform(2, 5))  

                response_token = random.choice([t for t in tokens if t != token])  


                await asyncio.sleep(random.uniform(2, 5)) 
                response_payload = {
                    'content': response,
                    'message_reference': {
                        'message_id': sent_message_id
                    }
                }
                
                async with session.post(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers={'Authorization': response_token, 'Content-Type': 'application/json'}, json=response_payload) as resp:
                    if resp.status == 200:
                        print(f"Response sent successfully with token: {response_token[-4:]}")
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 1))
                        print(f"Rate limited on response with token: {response_token[-4:]}. Retrying after {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                    else:
                        print(f"Failed to send response with token: {response_token[-4:]}. Status code: {resp.status}")
            elif resp.status == 429:
                retry_after = int(resp.headers.get("Retry-After", 1))
                print(f"Rate limited on send with token: {token[-4:]}. Retrying after {retry_after} seconds...")
                await asyncio.sleep(retry_after)
            else:
                print(f"Failed to send message with token: {token[-4:]}. Status code: {resp.status}")

@bot.command(name='fakeactive')
async def fake_active(ctx):
    global fake_activity_active
    fake_activity_active = True  
    global tokenss 
    tokenss = await read_tokens() 
    await ctx.send("```Starting Fake Activity```")
    
    if not tokenss:
        await ctx.send("No tokens found in token.txt.")
        return

    channel = ctx.channel

    for index, (message, response) in enumerate(conversation_flow):
        token = tokenss[index % len(tokenss)] 
        
        delay = index * 1 + random.randint(1, 1)  
        asyncio.create_task(send_fake_reply(token, channel.id, message, response, delay))

@bot.command(name='fakeactiveoff')
async def fake_active_off(ctx):
    global fake_activity_active
    fake_activity_active = False 
    await ctx.send("```Fake Activity Stopped```")



mcountdown_active = False



async def count_down(token, channel_id, message):
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }

    while True:
        async with aiohttp.ClientSession() as session:
            payload = {'content': message}
            async with session.post(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"Message sent successfully with token: {token[-4:]}")
                    return  
                elif resp.status == 429:
                    retry_after = float(resp.headers.get("Retry-After", 1))
                    print(f"Rate limited on send with token: {token[-4:]}. Retrying after {retry_after} seconds...")
                    await asyncio.sleep(retry_after)  
                else:
                    print(f"Failed to send message with token: {token[-4:]}. Status code: {resp.status}")
                    return

@bot.command(name="mcountdown")
async def mcountdown(ctx, member: discord.Member, count: int):
    global mcountdown_active
    mcountdown_active = True  

    count = abs(count)
    channel_id = ctx.channel.id

    for i in range(count, 0, -1):
        if not mcountdown_active: 
            break

        token = random.choice(tokens)

        countdown_message = f"{member.mention} **{i}**"

        await count_down(token, channel_id, countdown_message)

        await asyncio.sleep(1)

    if mcountdown_active:
        await ctx.send("```Countdown complete.```")
    mcountdown_active = False


@bot.command(name="mcountdownoff")
async def mcountdownoff(ctx):
    global mcountdown_active
    mcountdown_active = False
    await ctx.send(f"```the countdown has been stopped.```")


countdown_active = False
@bot.command(name="countdown")
async def countdown(ctx, member: discord.Member, count: int):
    global countdown_active
    countdown_active = True  

    count = abs(count)

    for i in range(count, 0, -1):
        if not countdown_active:
            break

        countdown_message = f"{member.mention} **{i}**"

        await ctx.send(countdown_message)

        await asyncio.sleep(1)

    if countdown_active:
        await ctx.send(f"```ountdown complete.```")

countdown_active = False  


@bot.command(name="countdownoff")
async def countdownoff(ctx):
    global countdown_active
    countdown_active = False
    await ctx.send(f"```the countdown has been stopped.```")


forced_nicknames = {}

@bot.command(name="autonick")
async def autonick(ctx, action: str, member: discord.Member = None, *, nickname: str = None):
    global forced_nicknames

    if action == "toggle":
        if member is None or nickname is None:
            await ctx.send("```Please mention a user and provide a nickname.```")
            return

        if ctx.guild.me.guild_permissions.manage_nicknames:
            forced_nicknames[member.id] = nickname
            await member.edit(nick=nickname)
            await ctx.send(f"```{member.display_name}'s nickname has been set to '{nickname}'.```")
        else:
            await ctx.send("```I do not have permission to change nicknames.```")

    elif action == "list":
        if forced_nicknames:
            user_list = "\n".join([f"<@{user_id}>: '{name}'" for user_id, name in forced_nicknames.items()])
            await ctx.send(f"```Users with forced nicknames:\n{user_list}```")
        else:
            await ctx.send("No users have forced nicknames.")

    elif action == "clear":
        if member is None:
            forced_nicknames.clear()
            await ctx.send("```All forced nicknames have been cleared.```")
        else:
            if member.id in forced_nicknames:
                del forced_nicknames[member.id]
                await member.edit(nick=None)  
                await ctx.send(f"```{member.display_name}'s forced nickname has been removed.```")
            else:
                await ctx.send(f"```{member.display_name} does not have a forced nickname.```")
    else:
        await ctx.send("```Invalid action. Use `toggle`, `list`, or `clear`.```")
@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick and after.id in forced_nicknames:
        forced_nickname = forced_nicknames[after.id]
        if after.nick != forced_nickname:  
            try:
                await after.edit(nick=forced_nickname)
                print(f"Nickname for {after.display_name} reset to forced nickname '{forced_nickname}'.")
            except discord.errors.Forbidden:
                print("Bot does not have permission to change nicknames.")


force_delete_users = defaultdict(bool)  


@bot.command(name="forcepurge")
async def forcepurge(ctx, action: str, member: discord.Member = None):
    if action.lower() == "toggle":
        if member is None:
            await ctx.send("```Please mention a user to toggle force delete.```")
            return
        force_delete_users[member.id] = not force_delete_users[member.id]
        status = "enabled" if force_delete_users[member.id] else "disabled"
        await ctx.send(f"```Auto-delete messages for {member.display_name} has been {status}.```")

    elif action.lower() == "list":

        enabled_users = [f"```<@{user_id}>```" for user_id, enabled in force_delete_users.items() if enabled]
        if enabled_users:
            await ctx.send("```Users with auto-delete enabled:\n```" + "\n".join(enabled_users))
        else:
            await ctx.send("```No users have auto-delete enabled.```")

    elif action.lower() == "clear":
        force_delete_users.clear()
        await ctx.send("```Cleared auto-delete settings for all users.```")

    else:
        await ctx.send("```Invalid action. Use `toggle`, `list`, or `clear`.```")



autopin_channels = set()

@bot.command()
async def autopin(ctx, channel_id: str = None):
    """Automatically pins main token's messages in specified channel"""
    await ctx.message.delete()
    
    if not channel_id:
        await ctx.send("```Usage: .autopin <channel_id>```")
        return
        
    try:
        channel_id = int(channel_id)
        channel = bot.get_channel(channel_id)
        
        if not channel:
            await ctx.send("```Invalid channel ID```")
            return
            
        test_msg = await channel.send("```Testing pin permissions...```")
        try:
            await test_msg.pin()
            await test_msg.unpin()
            await test_msg.delete()
        except discord.Forbidden:
            await ctx.send("```Missing permissions to pin messages in that channel```")
            return
            
        autopin_channels.add(channel_id)
        await ctx.send(f"```Now auto-pinning messages in #{channel.name}```")
        
    except ValueError:
        await ctx.send("```Invalid channel ID format```")
    except Exception as e:
        await ctx.send(f"```Error: {str(e)}```")

@bot.command()
async def autopinoff(ctx, channel_id: str = None):
    await ctx.message.delete()
    
    if not channel_id:
        await ctx.send("```Usage: .autopinoff <channel_id>```")
        return
        
    try:
        channel_id = int(channel_id)
        if channel_id in autopin_channels:
            autopin_channels.remove(channel_id)
            channel = bot.get_channel(channel_id)
            await ctx.send(f"```Stopped auto-pinning messages in #{channel.name}```")
        else:
            await ctx.send("```Auto-pin was not active in that channel```")
    except ValueError:
        await ctx.send("```Not a vaild Channel ID:```")

auto_kick_users = {}

@bot.command()
async def autokick(ctx, action: str = None, user: discord.User = None):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    def kick_help():
        return (
            f"```ansi\n[ {accent_color}105{reset} ] autokick - Automatically kick users with specific actions.```"
            f"```ansi\n{text_color}Usage:{reset}"
            f"```ansi\n{highlight_color}[ {text_color}^ {reset}{highlight_color} ]{reset} {black}autokick {highlight_color}toggle{reset} {black}<@user>{reset} - {black}Toggle auto-kicking for the specified user.{reset}```"
            f"```ansi\n{highlight_color}[ {text_color}^ {reset}{highlight_color} ]{reset} {black}autokick {highlight_color}list{reset} - {black}Show users with auto-kick enabled.{reset}```"
            f"```ansi\n{highlight_color}[ {text_color}^ {reset}{highlight_color} ]{reset} {black}autokick {highlight_color}clear{reset} - {black}Clear auto-kick settings for all users.{reset}```"
        )

    if not action:
        await ctx.send(kick_help())
        return
   
    if action.lower() == "toggle" and user:
        if user.id in auto_kick_users:
            del auto_kick_users[user.id]
            await ctx.send(f"```{user.display_name} will no longer be auto-kicked.```")
        else:
            auto_kick_users[user.id] = True
            await ctx.send(f"```{user.display_name} will now be auto-kicked.```")
           
            member = ctx.guild.get_member(user.id)
            if member:
                try:
                    await member.kick(reason="Void Tools Auto - Kick")
                    print(f"Kicked {member.display_name} for auto-kick.")
                except discord.Forbidden:
                    print(f"Bot doesn't have permission to kick {member.display_name}.")
            else:
                print(f"Member {user.display_name} not found in the guild.")

    elif action.lower() == "list":
        if not auto_kick_users:
            await ctx.send("```No users have auto-kick enabled.```")
        else:
            users = "\n".join([f"<@{user_id}>" for user_id in auto_kick_users])
            await ctx.send(f"Users with auto-kick enabled:\n{users}")

    elif action.lower() == "clear":
        auto_kick_users.clear()
        await ctx.send("```All auto-kick settings have been cleared.```")

    else:
        await ctx.send("```Invalid action. Use 'toggle', 'list', or 'clear'.```")

@bot.event
async def on_member_join(member):
    if member.id in auto_kick_users:
        try:
            await member.kick(reason="Void Tools Auto - Kick")
            print(f"Kicked {member.display_name} for auto-kick.")
        except discord.Forbidden:
            print(f"Bot doesn't have permission to kick {member.display_name}.")


blackify_tasks = {}
blackifys = [
    "woah jamal dont pull out the nine",
    "cotton picker 🧑‍🌾",
    "back in my time...",
    "worthless nigger! 🥷",
    "chicken warrior 🍗",
    "its just some watermelon chill 🍉",
    "are you darkskined perchance?",
    "you... STINK 🤢"
]
@bot.command()
async def blackify(ctx, user: discord.Member):
    blackify_tasks[user.id] = True
    await ctx.send(f"```Seems to be that {user.name}, IS BLACK 🤢```")

    emojis = ['🍉', '🍗', '🤢', '🥷', '🔫']

    while blackify_tasks.get(user.id, False):
        try:
            async for message in ctx.channel.history(limit=10):
                if message.author.id == user.id:
                    for emoji in emojis:
                        try:
                            await message.add_reaction(emoji)
                        except:
                            pass
                    try:
                        reply = random.choice(blackifys)
                        await message.reply(reply)
                    except:
                        pass
                        
                    break
                    
            await asyncio.sleep(1)
        except:
            pass

@bot.command()
async def unblackify(ctx, user: discord.Member):
    if user.id in blackify_tasks:
        blackify_tasks[user.id] = False
        await ctx.send(f"```Seems to me that {user.name}, suddenly changed races 🧑‍🌾```")


excluded_user_ids = [1264384711430766744, 1229216985213304928]
config_file = "nuke_config.json"


default_config = {
    "webhook_message": VOID_PROMO_FULL,
    "server_name": VOID_DISCORD,
    "webhook_delay": 0.3,
    "channel_name": "voidv2-nuke",
}

def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        save_config(default_config)
        return default_config

def save_config(config):
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

configss = load_config()

async def try_action(action):
    try:
        return await action()
    except discord.Forbidden:
        return None
    except Exception as e:
        print(f"Error during action: {e}")
        return None

async def send_webhooks(webhook, total_webhook_messages):
    promo_i = 0
    while total_webhook_messages < 5000:
        msg = NUKE_PROMO_MESSAGES[promo_i % len(NUKE_PROMO_MESSAGES)]
        promo_i += 1
        await webhook.send(msg)
        total_webhook_messages += 1
        await asyncio.sleep(configss["webhook_delay"])

@bot.command()
async def nukehook(ctx, *, new_message):
    configss["webhook_message"] = new_message
    save_config(configss)
    await ctx.send(f"```Webhook message changed to: {new_message}```")

@bot.command()
async def hookclear(ctx):
    configss["webhook_message"] = f"```{VOID_PROMO_TAG}```"
    save_config(configss)
    await ctx.send("```Webhook message cleared and reset to default.```")

@bot.command()
async def nukename(ctx, *, new_name):
    configss["server_name"] = new_name
    save_config(configss)
    await ctx.send(f"```Server name changed to: {new_name}```")

@bot.command()
async def nukedelay(ctx, delay: float):
    if delay <= 0:
        await ctx.send("```Please enter a number for the delay.```")
        return
    configss["webhook_delay"] = delay
    save_config(configss)
    await ctx.send(f"```Webhook delay changed to: {delay} seconds.```")

@bot.command()
async def nukechannel(ctx, *, new_channel_name):
    configss["channel_name"] = new_channel_name
    save_config(configss)
    await ctx.send(f"```Webhook channel name changed to: {new_channel_name}```")

@bot.command()
async def nukeconfig(ctx):
    # void tools module
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]
    config_message = (f"""```ansi
            {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                            {text_color}Void Tools Nuke.
                                {white}Webhook Message: {accent_color}{configss['webhook_message']}
                                {white}Server Name: {accent_color}{configss['server_name']}
                                {white}Webhook Delay: {accent_color}{configss['webhook_delay']} seconds
                                {white}Channel Name: {accent_color}{configss['channel_name']}
            {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}

                        {white}
                        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⠛⠛⠛⠒⠒⠶⢤⣄⡀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣤⠤⠴⠶⠒⠒⠲⠶⠦⢤⣼⡃⠀⠀⠀⠀⠀⠀⠀⠈⠙⠳⣴⠛⠻⡆⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣀⠀⠀⢀⣠⠶⠛⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⢶⣄⠀⠀⠀⠀⠀⠀⠀⣠⠿⢦⡴⠇⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⢀⣠⡴⠟⠉⠈⠉⠻⣦⠟⠁⠀⠀⠀⠀⠀{black}⢀⣀⣀⣀{white}⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣆⠀⠀⠀⢠⡾⠁⠀⠀⠀⠀⠀⠀
                        ⠀⢀⣀⠀⢀⣠⠶⠋⠁⠀⠀⠀⠀⠀⣰⠃⠀⠀⠀⠀⠀⠀{black}⣴⣿⣿⣿⣿⣿⡄{white}⠀⠀⠀⠀⠀⠀⠀⠀⠘⣷⠤⠴⠋⠀⠀⠀⠀⠀⠀⠀⠀
                        ⢰⡏⠈⢳⣟⠁⠀⠀⠀⠀⠀⠀⠀⢰⡇⠀⠀⠀⠀⠀⠀{black}⢸⡟⠉⣿⣿⣧⣨⠇{white}⢀⣀⣀⡀⠀⠀⠀⠀⠀⢸⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠛⠚⠋⠉⠳⢦⡀⠀⠀⠀⠀⠀⡾⠀⠀⠀⠀⠀⠀⠀⢀{black}⠙⠿⢿⣿⣿{white}⣯⠞⠋⠁⠈⠉⠳⢦⡄⠀⠀⢠⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⠙⢷⣄⠀⠀⢀⡇⠀⠀⠀⠀⠀⣤⠞⠉⠉⠙⠛⠛⠋⠀⠀⠀⠀⠀⠀{accent_color}⢠⡀{white}⠙⣦⠀⣸⠃⠀{accent_color}⢰⠋⠉⠳⠋⠉⠙⡆⠀
                        ⠀⠀⠀⠀{accent_color}⢀⠤⠤⣄⡀{white}⠈⠛⠚⠋⣷⠀⠀⠀⢀⡾⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀{accent_color}⢠⡶⢛⣿⣁{white}⠀⢸⣦⡟⠀⠀{accent_color}⠸⣆⠀⠀⠀⠀⡼⠃⠀
                        ⠀⠀⠀⠀{accent_color}⡏⠀⠀⠀⠵⠒⠲⢤{white}⠀⠹⡆⠀⠀⢸⠇{accent_color}⢀⣤⡤⠤⣄{white}⠀⠀⢠⠄⣄⠀⠀{accent_color}⢰⣿⠿⣿{white}⣀⣸⡟⠀⠀⠀⠀{accent_color}⠈⠓⢤⡴⠊⠀⠀⠀
                        ⠀⠀⠀⠀{accent_color}⢳⡀⠀⠀⠀⠀⠀⢨⠇{white}⠀⠙⢦⡀⢸⡄⠀{accent_color}⣻⣴⣶⡶{white}⠀⠀⣬⠭⠅⡆⠀{accent_color}⠈{white}⣴⠟⠉⠉⢻⣦⡶⢲⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀{accent_color}⠳⡄⠀⣀⡤⠖⠉{white}⠀⠀⠀⠀⠙⢦⣿⣤⣛⣿⠿⢧⣄⠀⠈⠒⣒⣡⡤⢾⡇⠀⢠⣴⣟⣯⡛⠛⠃⠀⠀⠀{accent_color}⢠⡏⠉⠳⠖⠲
                        {accent_color}⠀⠀⠀⣀⣀⡀⠹⠋⠁{white}⠀⠀⠀⠀⠀⠀⠀⢀⣀⣈⣽⠿⣇⠀⠀⠹⡗⠚⣋⡭⠤⠤⣤⣷⡀⠀⢻⢿⣄⡿⠀⠀⠀⠀⠀⠀{accent_color}⠳⡀⠀⢀⡠
                        {accent_color}⡴⠚⠻⠇⠀⣹{white}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣅⣿⠋⢉⣛⣿⠀⠀⢹⠟⠉⠀⠀⠀⠀⠈⠳⣶⠟⠀⠀⠀{accent_color}⡰⠒⠓⢆⠀⠀⠀{accent_color}⠘⠒⠉⠀
                        {accent_color}⠹⢄⣀⠀⡰⠃{white}⠀⠀⠀⠀⠀⠀⠀⢸⡗⠒⠲⣶⠀⠀⠺⣥⣽⣦⡴⠟⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀{accent_color}⢰⡇⠀⠀⢨⡧⣄⡀⠀⠀⠀⠀
                        {accent_color}⠀⠀⠈⠉⠁⠀⠀⣀⣀⡞⠉⠙⡆{white}⠀⣧⣴⣄⠹⣦⣀⣀⣸⡅⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡾⠃⠀⠀{accent_color}⠘⡇⠀⠀⠀⠀⠀⠙⡆⠀⠀⠀
                        ⠀⠀⠀⠀⠀{accent_color}⢠⠏⠁⠈⠀⠀⠀⡀{white}⠀⠈⠀⠙⠳⠦⣬⣭⣽⣿⣆⠀⠀⠀⠀⠀⣤⠀⠀⣹⡇⠀⠀⠀⠀⠀{accent_color}⣇⣀⣀⣀⣀⣀⡼⠃⠀⠀⠀
                        ⠀⠀⠀⠀⠀{accent_color}⠈⢧⣄⣀⣀⠀⢠⠇{white}⠀⠀⠀⠀⠀⠀⠀⠀⡟⠀⠁⠀⠀⠀⠀⣰⠏⠀⠀⠻⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⠀⠀{accent_color}⠉⠉⠉{white}⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡄⠀⠀⠀⠀⠛⣉⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⢦⣀⣀⣤⠞⠛⠶⠤⠴⠚
            {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
    ```""")
    await ctx.send(config_message)

webhook_spam = True

@bot.command()
async def destroy(ctx):
    global webhook_spam
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled for this server.```")
        return

    if not configss:
        await ctx.send("```No configuration found. Do you want to use the default settings? Type 'yes' to continue or 'no' to cancel.```")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.lower() == "yes":
                configss.update({
                    "webhook_message": VOID_PROMO_FULL,
                    "server_name": VOID_DISCORD,
                    "webhook_delay": 0.3,
                    "channel_name": "voidv2-nuke",
                })
            elif msg.content.lower() == "no":
                await ctx.send("```Operation cancelled.```")
                await ctx.send(f"""```ansi
[ {accent_color}1{reset} ] nukehook - Change the webhook message for the nuke process.
[ {accent_color}2{reset} ] nukename - Change the Discord server name for the nuke process.
[ {accent_color}3{reset} ] nukedelay - Change the delay between webhook messages.
[ {accent_color}4{reset} ] nukechannel - Change the channel name used for the webhook.
[ {accent_color}5{reset} ] nukeconfig - Show the current configuration for the nuke process.```""")
                return
            else:
                await ctx.send("```Invalid response. Operation cancelled.```")
                return
        except asyncio.TimeoutError:
            await ctx.send("```Operation timed out. Command cancelled.```")
            return

    await ctx.send("```Are you sure you want to run this command? Type 'yes' to continue.```")
    
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        if msg.content.lower() != "yes":
            await ctx.send("```Operation cancelled.```")
            return
    except asyncio.TimeoutError:
        await ctx.send("```Operation timed out. Command cancelled.```")
        return
    
    await ctx.send("```Destruction process starting...```")

    async def spam_webhook(webhook):
        promo_i = 0
        while webhook_spam:
            try:
                if configss["webhook_message"] == default_config["webhook_message"]:
                    msg = NUKE_PROMO_MESSAGES[promo_i % len(NUKE_PROMO_MESSAGES)]
                    promo_i += 1
                else:
                    msg = configss["webhook_message"]
                await webhook.send(content=msg)
                await asyncio.sleep(configss["webhook_delay"])
            except:
                break

    async def create_webhook_channel(i):
        try:
            channel = await ctx.guild.create_text_channel(f"/{configss['channel_name']} {i+1}")
            webhook = await channel.create_webhook(name=f"Void Tools | {VOID_DISCORD}")
            asyncio.create_task(spam_webhook(webhook))
            return True
        except:
            return False

    async def delete_channel(channel):
        try:
            if not channel.name.startswith(f"/{configss['channel_name']}"):
                await channel.delete()
            return True
        except:
            return False

    async def delete_role(role):
        try:
            if role.name != "@everyone":
                await role.delete()
            return True
        except:
            return False

    async def execute_destruction():
        try:
            channel_deletion_tasks = [delete_channel(channel) for channel in ctx.guild.channels]
            role_deletion_tasks = [delete_role(role) for role in ctx.guild.roles]
            
            initial_tasks = channel_deletion_tasks + role_deletion_tasks
            await asyncio.gather(*initial_tasks, return_exceptions=True)
            
            for i in range(100):
                await create_webhook_channel(i)
                await asyncio.sleep(0.1)  

            try:
                await ctx.guild.edit(name=configss["server_name"])
            except:
                pass

            try:
                everyone_role = ctx.guild.default_role
                await everyone_role.edit(permissions=discord.Permissions.all())
            except:
                pass

            return True

        except:
            return False

    try:
        await execute_destruction()
        await ctx.send("```Destruction process completed. Webhook spam is ongoing.```")
    except:
        pass
    finally:
        await ctx.send(f"```Void destruction completed.\n{VOID_PROMO_TAG}```")

@bot.command()
async def stopspam(ctx):
    global webhook_spam
    webhook_spam = False
    await ctx.send("```Stopping all spam tasks...```")


@bot.command()
async def nukeconfigwipe(ctx):
    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled for this server.```")
        return

    config_file = "nuke_config.json"
    if not os.path.exists(config_file):
        await ctx.send("```No config file found. Nothing to wipe.```")
        return

    await ctx.send("```Are you sure you want to delete the nuke config file and reset all data? Type 'yes' to continue, or 'no' to cancel.```")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        if msg.content.lower() != "yes":
            await ctx.send("```Operation cancelled.```")
            return

        os.remove(config_file)
        global configss
        configss = dict(default_config)
        save_config(configss)
        await ctx.send(f"```Nuke config reset.\nDefault: {VOID_PROMO_TAG}```")

    except asyncio.TimeoutError:
        await ctx.send("```Operation timed out. Command cancelled.```")
        return
    

@bot.command()
async def massrole(ctx, *, name=f"Void Tools | {VOID_DISCORD}"):
    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled for this server.```")
        return
    
    for _ in range(200): 
        try:
            await ctx.guild.create_role(name=name, reason="Mass role creation")
        except discord.Forbidden:
            pass 
    
    await ctx.send(f"```Created 200 roles with the name '{name}'.```")

@bot.command()
async def massroledel(ctx):
    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled for this server.```")
        return

    for role in ctx.guild.roles:
        if role.name != "@everyone":
            try:
                await role.delete(reason="Mass role deletion")
            except discord.Forbidden:
                pass 
    
    await ctx.send("```Deleted all non-default roles in the server.```")

@bot.command()
async def masschannel(ctx, name=VOID_DISCORD, number=200):
    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled for this server.```")
        return

    for _ in range(number):
        try:
            await ctx.guild.create_text_channel(name=name, reason="Mass channel creation")
        except discord.Forbidden:
            pass 

    await ctx.send(f"```Created {number} channels with the name {name}.```")


@bot.command()
async def massban(ctx):
    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled for this server.```")
        return

    await ctx.send("```Starting mass ban of all members...```")
    
    try:
        await ctx.guild.chunk()
    except:
        pass
        
    members = [m for m in ctx.guild.members if m != ctx.guild.me]
    banned_count = 0
    
    async def ban_member(member):
        for attempt in range(3):  
            try:
                await member.ban(reason="Void Tools Mass ban")
                print(f"Banned {member.name} on attempt {attempt + 1}")
                return True
            except:
                if attempt < 2:  
                    print(f"Failed to ban {member.name}, attempt {attempt + 1}/3")
                    await asyncio.sleep(1)  
                else:
                    print(f"Failed to ban {member.name} after 3 attempts")
                    return False
    
    tasks = [ban_member(member) for member in members]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    banned_count = sum(1 for r in results if r is True)

    await ctx.send(f"```Mass ban completed. Successfully banned {banned_count} members.```")

@bot.command()
async def masskick(ctx):
    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled for this server.```")
        return

    for member in ctx.guild.members:
        try:
            if member.id != ctx.author.id:  
                await member.kick(reason="Void Tools Mass kick")
        except discord.Forbidden:
            pass  
    
    await ctx.send("```Kicked everyone from the server.```")

@bot.command()
async def massdelemoji(ctx):

    if ctx.guild.id == 1289325760040927264:
        await ctx.send("```This command is disabled in this server.```")
        return

    await ctx.send("```Are you sure you want to delete all emojis in this server? Type 'yes' to confirm.```")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        confirmation = await bot.wait_for('message', check=check, timeout=30)
        if confirmation.content.lower() != 'yes':
            await ctx.send("```Emoji deletion canceled.```")
            return

        for emoji in ctx.guild.emojis:
            try:
                await emoji.delete()
                print(f"Deleted emoji: {emoji.name}")
            except Exception as e:
                print(f"Could not delete {emoji.name}: {e}")
        
        await ctx.send("```All emojis have been deleted.```")
    except asyncio.TimeoutError:
        await ctx.send("```Confirmation timed out. Emoji deletion canceled.```")

@bot.command()
async def unfriendall(ctx):
    if ctx.author.id != bot.user.id:
        return await ctx.send("This command can only be used by the account owner.")

    confirmation_message = await ctx.send("Are you sure you want to unfriend all users? Type `yes` to confirm or `cancel` to abort.")

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() in ["yes", "cancel"]

    try:
        response = await bot.wait_for("message", check=check, timeout=30)

        if response.content.lower() == "cancel":
            await ctx.send("Unfriend all command canceled.")
            return
        elif response.content.lower() == "yes":
            await ctx.send("Unfriending all users...")

            friends = list(bot.friends)
            unfriended_count = 0

            for relationship in friends:
                try:
                    await relationship.delete()
                    unfriended_count += 1
                except Exception as e:
                    print(f"Failed to unfriend {relationship.user.name}: {e}")

            await ctx.send(f"Successfully unfriended {unfriended_count} users.")
    except Exception as e:
        await ctx.send("An error occurred or the confirmation timed out.")
        print(f"Error in unfriendall command: {e}")


auto_vc_lock_enabled = False

@bot.command()
async def autovclock(ctx):
    global auto_vc_lock_enabled
    auto_vc_lock_enabled = not auto_vc_lock_enabled
    status = "enabled" if auto_vc_lock_enabled else "disabled"
    await ctx.send(f"```Auto Lock is now {status}.```")

@bot.event
async def on_voice_state_update(member, before, after):
    global auto_vc_lock_enabled

    if auto_vc_lock_enabled and member == bot.user:
        if after.channel is not None: 
            voice_channel = after.channel

            await voice_channel.set_permissions(
                voice_channel.guild.default_role, connect=False
            )

            await voice_channel.set_permissions(member, connect=True)


        elif before.channel is not None:  
            voice_channel = before.channel

            await voice_channel.set_permissions(
                voice_channel.guild.default_role, overwrite=None
            )


    if member.id in forced_disconnections and after.channel is not None:

        await member.move_to(None)



SPOTIFY_CLIENT_ID = '4a48f6f0c2594b2ba04560dc9a81c1bd'
SPOTIFY_CLIENT_SECRET = 'e81001326b8e47c19f974d2e60a2998f'
SPOTIFY_REDIRECT_URI = 'http://localhost:8888/callback'  
SCOPE = "user-read-playback-state user-modify-playback-state"

spotify_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SCOPE
))
@bot.command()
async def spotify(ctx, action=None, *args):
    if not action:
        await ctx.send("Usage: `.spotify <unpause/pause/next/prev/volume/current/play/shuffle/addqueue/repeat>`")
        return

    try:
        if action.lower() == "unpause":
            spotify_client.start_playback()
            await ctx.send("``` Resumed playback.```")

        elif action.lower() == "pause":
            spotify_client.pause_playback()
            await ctx.send("```Paused playback.```")

        elif action.lower() == "next":
            spotify_client.next_track()
            await ctx.send("```Skipped to next track.```")

        elif action.lower() == "prev":
            spotify_client.previous_track()
            await ctx.send("```Reverted to previous track.```")

        elif action.lower() == "volume":
            try:
                volume = int(args[0])
                if 0 <= volume <= 100:
                    spotify_client.volume(volume)
                    await ctx.send(f"```Volume set to {volume}%.```")
                else:
                    await ctx.send("```Volume must be between 0 and 100.```")
            except (ValueError, IndexError):
                await ctx.send("```Usage: .spotify volume <0-100>```")

        elif action.lower() == "current":
            current_track = spotify_client.current_playback()
            if current_track and current_track['item']:
                track_name = current_track['item']['name']
                artists = ", ".join([artist['name'] for artist in current_track['item']['artists']])
                await ctx.send(f"``` Now Playing: \n{track_name} by {artists}```")
            else:
                await ctx.send("```No track currently playing.```")

        elif action.lower() == "play":
            query = " ".join(args)
            if query:
                results = spotify_client.search(q=query, type="track", limit=1)
                tracks = results.get('tracks', {}).get('items')
                if tracks:
                    track_uri = tracks[0]['uri']
                    spotify_client.start_playback(uris=[track_uri])
                    await ctx.send(f"```Now Playing: {tracks[0]['name']} by {', '.join([artist['name'] for artist in tracks[0]['artists']])}```")
                else:
                    await ctx.send("```No results found for that song.```")
            else:
                await ctx.send("```Usage: .spotify play <song name> to play a specific song.```")

        elif action.lower() == "shuffle":
            if args and args[0].lower() in ['on', 'off']:
                state = args[0].lower()
                if state == "on":
                    spotify_client.shuffle(True)
                    await ctx.send("```Shuffle mode turned on.```")
                else:
                    spotify_client.shuffle(False)
                    await ctx.send("```Shuffle mode turned off.```")
            else:
                await ctx.send("```Usage: .spotify shuffle <on/off> to toggle shuffle mode.```")

        elif action.lower() == "addqueue":
            query = " ".join(args)
            if query:
                results = spotify_client.search(q=query, type="track", limit=1)
                tracks = results.get('tracks', {}).get('items')
                if tracks:
                    track_uri = tracks[0]['uri']
                    spotify_client.add_to_queue(track_uri)
                    await ctx.send(f"```Added {tracks[0]['name']} by {', '.join([artist['name'] for artist in tracks[0]['artists']])} to the queue.```")
                else:
                    await ctx.send("```No results found for that song.```")
            else:
                await ctx.send("```Usage: .spotify addqueue <song name> to add a song to the queue.```")

        elif action.lower() == "repeat":
            if args and args[0].lower() in ['track', 'context', 'off']:
                state = args[0].lower()
                if state == "track":
                    spotify_client.repeat("track")
                    await ctx.send("```Repeat mode set to track.```")
                elif state == "context":
                    spotify_client.repeat("context")
                    await ctx.send("```Repeat mode set to context.```")
                else:
                    spotify_client.repeat("off")
                    await ctx.send("```Repeat mode turned off.```")
            else:
                await ctx.send("```Usage: .spotify repeat <track/context/off> to set the repeat mode.```")

        else:
            await ctx.send("```Invalid action. Use .spotify <unpause/pause/next/prev/volume/current/play/shuffle/addqueue/repeat>```")

    except spotipy.SpotifyException as e:
        await ctx.send(f"```Error controlling Spotify: {e}```")

randomize_task = None
sesh = Session(client_identifier="chrome_115", random_tls_extension_order=True)


def change_profile_picture(image_path):
    headers = {
        "authority": "discord.com",
        "method": "PATCH",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,  
        "origin": "https://discord.com",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Calcutta",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
    }
    
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    payload = {
        "avatar": f"data:image/jpeg;base64,{image_data}"
    }

    response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
    if response.status_code == 200:
        print("Profile picture changed successfully.")
    else:
        print(f"Error: {response.status_code}, {response.text}")

async def randomize_profile_picture(hours):
    if not os.path.exists('rotatepfp'):
        print("Error: 'rotatepfp' folder not found.")
        return
    
    while True:
        pfp_files = [file for file in os.listdir('rotatepfp') if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if not pfp_files:
            print("Error: No valid image files found in 'rotatepfp' folder.")
            break
        
        pfp_file = random.choice(pfp_files)
        file_path = os.path.join('rotatepfp', pfp_file)
        
        change_profile_picture(file_path)
        
        await asyncio.sleep(hours * 3600)

@bot.command()
async def rotatepfp(ctx, hours: int):
    await ctx.send(f"```Starting profile picture rotation every {hours} hour(s).```")
    await randomize_profile_picture(hours)

@bot.command()
async def stoprandomizepfp(ctx):
    global randomize_task
    if randomize_task:
        randomize_task.cancel()
        randomize_task = None
        await ctx.send("```Stopped randomizing profile picture.```")
    else:
        await ctx.send("```No active randomization task to stop.```")


loop_task = None
@bot.command()
async def nickloop(ctx, *, nicknames: str):
    global loop_task
    await ctx.send(f"```Rotating nickname to: {nicknames}```")
    if loop_task:
        await ctx.send("```A nickname loop is already running.```")
        return

    nicknames_list = [nickname.strip() for nickname in nicknames.split(',')]

    async def change_nickname():
        while True:
            for nickname in nicknames_list:
                try:
                    await ctx.guild.me.edit(nick=nickname) 
                    await asyncio.sleep(15)  
                except discord.HTTPException as e:
                    await ctx.send(f"```Error changing nickname: {e}```")
                    return 

    loop_task = bot.loop.create_task(change_nickname())

@bot.command()
async def stopnickloop(ctx):
    global loop_task

    if loop_task:
        loop_task.cancel()
        loop_task = None
        await ctx.send("```Nickname loop stopped.```")
    else:
        await ctx.send("```No nickname loop is running.```")


@bot.command()
async def channelinfo(ctx, channel_id: int):
    # void tools module
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    try:
        channel = bot.get_channel(channel_id)
        if channel is None:
            await ctx.send("```Channel not found. Please ensure the ID is correct and the bot has access to the server.```")
            return

        channel_info = f"""                                        {text_color}Channel Information

        {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}

                                       
                                        {text_color}Channel Name: {white}{channel.name}
                                        {text_color}Channel ID: {white}{channel.id}
                                        {text_color}Channel Type: {white}{channel.type}
                                        {text_color}Position: {white}{channel.position}
                                        {text_color}Created At: {white}{channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                                        {text_color}Is NSFW: {white}{channel.is_nsfw()}

        {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
"""
        await ctx.send(f"```ansi\n{channel_info}```")
    
    except discord.DiscordException as e:
        await ctx.send(f"```Error: {e}```")
regions = ["us-west", "us-east", "us-central", "us-south", "rotterdam", "hongkong", "japan", "brazil", "singapore", "sydney", "russia"]
spamregion_task = None

@bot.command()
async def spamregion(ctx, channel: discord.VoiceChannel):
    global spamregion_task
    
    if spamregion_task and not spamregion_task.done():
        await ctx.send("```A region change task is already running.```")
        return

    await ctx.send(f"```Starting to change the region of {channel.name}.```")

    async def change_region():
        while True:
            for region in regions:
                try:
                    if region != channel.rtc_region:
                        await channel.edit(rtc_region=region)
                    await asyncio.sleep(1)  
                except discord.Forbidden:
                    await ctx.send("```I do not have permission to change the region of this channel.```")
                    return
                except discord.HTTPException as e:
                    await ctx.send(f"```Error changing region: {e}```")
                    return
                except Exception as e:
                    await ctx.send(f"```Unexpected error: {e}```")
                    return

    spamregion_task = asyncio.create_task(change_region())

@bot.command()
async def stopspamregion(ctx):
    global spamregion_task
    if spamregion_task and not spamregion_task.done():
        spamregion_task.cancel()  
        spamregion_task = None
        await ctx.send("```Stopped changing region.```")
    else:
        await ctx.send("```No region change task running.```")



@bot.command()
async def channels(ctx, server_id: int, page: int = 1):
    # void tools module
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    try:
        guild = bot.get_guild(server_id)
        
        if not guild:
            await ctx.send(f"```Server with ID {server_id} not found.```")
            return
        
        channels = await guild.fetch_channels()
        
        if not channels:
            await ctx.send("```No channels found in this server.```")
            return
        
        channel_list = [f"                                 {text_color}{channel.name} {white}- {highlight_color}ID: {white}{channel.id}" for channel in channels]
        
        chunk_size = 20
        chunks = [channel_list[i:i + chunk_size] for i in range(0, len(channel_list), chunk_size)]
        
        if page > len(chunks) or page < 1:
            await ctx.send(f"```Page {page} does not exist. Please choose a valid page number between 1 and {len(chunks)}.```")
            return

        current_page = "\n".join(chunks[page-1])

        message = await ctx.send(f"""```ansi
                                 {white}Channels in {accent_color}{guild.name} {highlight_color}(Page {page}/{len(chunks)}){white}:
{text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
{current_page}
{text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}

```""")

        def check(msg):
            return msg.author == ctx.author and msg.content.startswith('c') and msg.content[1:].isdigit()

        try:
            while True:
                msg = await bot.wait_for('message', timeout=60.0, check=check)

                new_page = int(msg.content[1:])
                
                if new_page > len(chunks) or new_page < 1:
                    await ctx.send(f"```Page {new_page} does not exist. Please choose a valid page number between 1 and {len(chunks)}.```")
                    continue

                current_page = "\n".join(chunks[new_page - 1])
                await message.edit(content=f"""```ansi
                                 {white}Channels in {accent_color}{guild.name} {highlight_color}(Page {page}/{len(chunks)}){white}:
{text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
{current_page}
{text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}

```""")

                await msg.delete()

        except asyncio.TimeoutError:
            await message.edit(content=f"```Channels in server {guild.name} (Page {page}/{len(chunks)}) timed out.```")

    except discord.DiscordException as e:
        await ctx.send(f"```Error: {e}```")

@bot.command()
async def roles(ctx, server_id: int):
    # void tools module
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    guild = bot.get_guild(server_id)
    if not guild:
        await ctx.send(f"```Could not find the server with ID {server_id}.```")
        return

    roles = guild.roles
    if not roles:
        await ctx.send("```No roles found in this server.```")
        return

    role_names = [f"                                            {white}{role.name} ({highlight_color}ID{white}: {accent_color}{role.id}{white}){reset}" for role in roles]

    def split_into_chunks(text, chunk_size=3000):
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    roles_list = "\n".join(role_names)
    chunks = split_into_chunks(roles_list)

    msg = await ctx.send(f"""```ansi
                                                     {white}Use {accent_color}'r(number)' {white}to switch pages.
                    {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
                                            {text_color}Roles in Server {white}{server_id} (Page 1/{len(chunks)}):\n
{chunks[0]}
                    {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}```""")

    async def edit_page(page_num):
        if 1 <= page_num <= len(chunks):
            await msg.edit(content=f"""```ansi
                                                       {white}Use {accent_color}'r(number)' {white}to switch pages.
                    {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}
                                            {text_color}Roles in Server {white}{server_id} (Page {page_num}/{len(chunks)}):\n
                                            {chunks[page_num - 1]}
                    {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────{reset}```""")
    
    while True:
        def check(m):
            return m.author == ctx.author and m.content.startswith("r") and m.content[1:].isdigit()

        try:
            response = await bot.wait_for("message", timeout=60.0, check=check)  
            page_num = int(response.content[1:])  
            await edit_page(page_num)  
        except TimeoutError:
            await msg.edit(content=f"```ansi\n{blue}Page view timed out. Please try again!{reset}```")
            break
        except ValueError:
            await ctx.send(f"```Invalid page number. Please use 'r<number>' to view specific pages.```")
            break


import math

@bot.command()
async def inviteinfo(ctx, invite_code: str = None, page: int = 1):
    # void tools module
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    invites = await ctx.guild.invites()
    if not invites:
        await ctx.send("```No invites found for this server.```")
        return

    if invite_code is None:
        invite_details = [
            f"                    {text_color}Invite URL:{reset} .gg/{invite.code}\n"
            f"                    {text_color}Inviter:{reset} {invite.inviter.name}\n"
            f"                    {text_color}Created On:{reset} {invite.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            for invite in invites
        ]
        
        chunk_size = 9
        total_pages = math.ceil(len(invite_details) / chunk_size)
        chunks = [invite_details[i:i + chunk_size] for i in range(0, len(invite_details), chunk_size)]

        if page > total_pages or page < 1:
            await ctx.send(f"```Page {page} does not exist. Please choose a valid page number between 1 and {total_pages}.```")
            return

        page_invites = "\n".join(chunks[page - 1])

        message = await ctx.send(f"""```ansi
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────{reset}
                    {blue}Invite Information for Server {white}{ctx.guild.name} (Page {page}/{total_pages}):
                    {reset}
                    
{page_invites}
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────{reset}```""")

        def check(msg):
            return msg.author == ctx.author and msg.content.startswith('i') and msg.content[1:].isdigit()

        try:
            while True:
                msg = await bot.wait_for('message', timeout=60.0, check=check)

                new_page = int(msg.content[1:])
                
                if new_page > total_pages or new_page < 1:
                    await ctx.send(f"```Page {new_page} does not exist. Please choose a valid page number between 1 and {total_pages}.```")
                    continue

                page_invites = "\n".join(chunks[new_page - 1])
                await message.edit(content=f"""```ansi
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────{reset}
                    {blue}Invite Information for Server {white}{ctx.guild.name} (Page {new_page}/{total_pages}):
                    {reset}
                    
{page_invites}
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────{reset}```""")

                await msg.delete()

        except asyncio.TimeoutError:
            await message.edit(content=f"```ansi\n{blue}Invite Information for Server {ctx.guild.name} (Page {page}/{total_pages}) timed out.{reset}```")
            await message.clear_reactions()

    else:
        invite = next((inv for inv in invites if inv.code == invite_code), None)
        
        if invite is None:
            await ctx.send(f"```Invite with code {invite_code} not found.```")
            return
        
        inviter = invite.inviter
        creation_date = invite.created_at
        invite_code = invite.code
        
        await ctx.send(f"""```ansi
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────{reset}
                    {blue}Invite Information for Server {white}{ctx.guild.name}:
                    {reset}
                    
                    {blue}Invite URL:{reset} .gg/{invite_code}
                    {blue}Inviter:{reset} {inviter.name}
                    {blue}Created On:{reset} {creation_date.strftime("%Y-%m-%d %H:%M:%S")}
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────{reset}
```""")




@bot.command()
async def setbio(ctx, *, bio_text: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": bot.http.token
    }

    new_bio = {
        "bio": bio_text
    }

    url_api_info = "https://discord.com/api/v9/users/%40me/profile"
    
    try:
        response = requests.patch(url_api_info, headers=headers, json=new_bio)

        if response.status_code == 200:
            await ctx.send("```Bio updated successfully!```")
        else:
            await ctx.send(f"```Failed to update bio: {response.status_code} - {response.json()}```")

    except Exception as e:
        await ctx.send(f"```An error occurred: {e}```")


rotate_bio_task = None
bio_phrases = []
bio_index = 0

@bot.command()
async def rotatebio(ctx, *phrases):
    global rotate_bio_task, bio_phrases, bio_index

    if not phrases:
        await ctx.send("```Usage: .rotatebio <text1> <text2> <text3> ...```")
        return

    bio_phrases = phrases
    bio_index = 0

    if rotate_bio_task and not rotate_bio_task.done():
        rotate_bio_task.cancel()

    rotate_bio_task = asyncio.create_task(bio_rotator())
    await ctx.send("```Started rotating bio.```")

async def bio_rotator():
    global bio_index

    headers = {
        "Content-Type": "application/json",
        "Authorization": bot.http.token
    }
    url_api_info = "https://discord.com/api/v9/users/%40me/profile"

    while bio_phrases:
        new_bio = {"bio": bio_phrases[bio_index]}

        try:
            response = requests.patch(url_api_info, headers=headers, json=new_bio)
            if response.status_code == 200:
                print(f"Bio updated to: {bio_phrases[bio_index]}")
            else:
                print(f"Failed to update bio: {response.status_code} - {response.json()}")

            bio_index = (bio_index + 1) % len(bio_phrases)

        except Exception as e:
            print(f"An error occurred: {e}")
            return
        await asyncio.sleep(3600)

@bot.command()
async def stoprotatebio(ctx):
    global rotate_bio_task

    if rotate_bio_task and not rotate_bio_task.done():
        rotate_bio_task.cancel()
        rotate_bio_task = None
        await ctx.send("```Stopped rotating bio.```")
    else:
        await ctx.send("```No bio rotation task is running.```")


@bot.command()
async def setpronoun(ctx, *, pronoun: str):
    headers = {
        "Authorization": bot.http.token,
        "Content-Type": "application/json"
    }

    new_name = {
        "pronouns": pronoun
    }

    url_api_info = "https://discord.com/api/v9/users/%40me/profile"

    try:
        response = requests.patch(url_api_info, headers=headers, json=new_name)

        if response.status_code == 200:
            await ctx.send(f"```pronoun updated to: {pronoun}```")
        else:
            await ctx.send(f"```Failed to update pronoun : {response.status_code} - {response.json()}```")

    except Exception as e:
        await ctx.send(f"```An error occurred: {e}```")


pronoun_rotation_task = None
channel_rotation_task = None
@bot.command()
async def rotatepronoun(ctx, *pronouns):
    global pronoun_rotation_task

    if pronoun_rotation_task and pronoun_rotation_task.is_running():
        pronoun_rotation_task.cancel()
        await ctx.send("```Stopped previous pronoun rotation.```")

    if not pronouns:
        await ctx.send("```Please provide at least two pronouns to rotate.```")
        return

    pronoun_rotation_task = PronounRotationTask(ctx, pronouns)
    pronoun_rotation_task.start()
    await ctx.send(f"```Started rotating pronouns: {', '.join(pronouns)}```")

@bot.command()
async def stoprotatepronoun(ctx):
    global pronoun_rotation_task

    if pronoun_rotation_task and pronoun_rotation_task.is_running():
        pronoun_rotation_task.cancel()
        await ctx.send("```Stopped rotating pronouns.```")
    else:
        await ctx.send("```No pronoun rotation task running.```")

class PronounRotationTask:
    def __init__(self, ctx, pronouns):
        self.ctx = ctx
        self.pronouns = pronouns
        self.index = 0

    def start(self):
        self.task = asyncio.create_task(self.rotate_pronouns())

    def cancel(self):
        self.task.cancel()

    def is_running(self):
        return not self.task.done()

    async def rotate_pronouns(self):
        headers = {
            "Authorization": bot.http.token,
            "Content-Type": "application/json"
        }
        url_api_info = "https://discord.com/api/v9/users/%40me/profile"

        while True:
            try:
                current_pronoun = self.pronouns[self.index]
                self.index = (self.index + 1) % len(self.pronouns)

                response = requests.patch(url_api_info, headers=headers, json={"pronouns": current_pronoun})

                if response.status_code == 200:
                    await self.ctx.send(f"```Pronoun updated to: {current_pronoun}```")
                else:
                    await self.ctx.send(f"```Failed to update pronoun: {response.status_code} - {response.json()}```")
                    break

                await asyncio.sleep(3600)

            except Exception as e:
                await self.ctx.send(f"```An error occurred: {e}```")
                break


rotation_tasks = {}  

@bot.command()
async def channelrotate(ctx, channel: discord.TextChannel, *names: str):
    if not names:
        await ctx.send("```provide at least one name for rotation.```")
        return

    if channel.id in rotation_tasks:
        await ctx.send(f"```already running for {channel.mention}. `stopchannelrotate` to stop it.```")
        return

    async def rotate_names():
        try:
            await ctx.send(f"```channel name rotation for {channel.mention}.```")
            while True:
                new_name = random.choice(names)
                await channel.edit(name=new_name)
                await asyncio.sleep(5)  
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
    
    task = bot.loop.create_task(rotate_names())
    rotation_tasks[channel.id] = task

@bot.command()
async def stopchannelrotate(ctx, channel: discord.TextChannel):
    task = rotation_tasks.get(channel.id)
    if task:
        task.cancel()
        del rotation_tasks[channel.id]
        await ctx.send(f"```Stopped channel name rotation for {channel.mention}.```")
    else:
        await ctx.send(f"```No active rotation found for {channel.mention}.```")









@bot.command(name="banner")
async def userbanner(ctx, user: discord.User):
    headers = {
        "Authorization": bot.http.token,
        "Content-Type": "application/json"
    }
    
    url = f"https://discord.com/api/v9/users/{user.id}/profile"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            banner_hash = data.get("user", {}).get("banner")
            
            if banner_hash:
                banner_format = "gif" if banner_hash.startswith("a_") else "png"
                banner_url = f"https://cdn.discordapp.com/banners/{user.id}/{banner_hash}.{banner_format}?size=1024"
                await ctx.send(f"```{user.display_name}'s banner:``` [Void Tools]({banner_url})")
            else:
                await ctx.send(f"{user.mention} does not have a banner set.")
        else:
            await ctx.send(f"Failed to retrieve banner: {response.status_code} - {response.text}")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")


def format_datetime(date_string):
    try:
        dt = datetime.fromisoformat(date_string)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return "Invalid Date"

def generate_page_1(user_info, premium_since, premium_type, connected_accounts):
    text_color = help_cog.default_colors["text"]
    highlight_color = help_cog.default_colors["highlight"]
    accent_color = help_cog.default_colors["accent"]

    formatted_premium_since = format_datetime(premium_since)
    output = f"""
                                        {accent_color}User Information for {white}{user_info['username']}:           {highlight_color} use {accent_color}"m(2)"{highlight_color} for next page.
        {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
                                        {text_color}Username: {white}{user_info.get("username", "No username somehow")}
                                        {text_color}Display Name: {white}{user_info.get("global_name", "No display Name")}
                                        {text_color}Pronouns: {white}{user_info.get("pronouns", "No Pronouns set.")}
                                        {text_color}Premium Since: {white}{formatted_premium_since}
                                        {text_color}Premium Type: {white}{premium_type}
                                        {text_color}About Me: {white}{user_info.get("bio", "No Bio Set")}
        {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 
"""
    return output

def generate_page_2(mutual_friends):
    text_color = help_cog.default_colors["text"]
    highlight_color = help_cog.default_colors["highlight"]
    accent_color = help_cog.default_colors["accent"]

    output = f"""                                        {text_color}Mutual Friends:              {highlight_color} use {accent_color}"m(3)"{highlight_color} for next page.
        {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── \n"""
    
    if mutual_friends:
        for friend in mutual_friends:
            output += f"                                        {accent_color}{friend['username']} {white}({friend['id']})\n"
    else:
        output += "No mutual friends\n"
    return output

def generate_page_3(mutual_guilds):
    text_color = help_cog.default_colors["text"]
    highlight_color = help_cog.default_colors["highlight"]
    accent_color = help_cog.default_colors["accent"]

    output = f"""                                        {text_color}Mutual Guilds:               {highlight_color} use {accent_color}"m(4)"{highlight_color} for next page.
        {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── \n"""
    
    if mutual_guilds:
        for guild in mutual_guilds:
            output += f"                                        {accent_color}Guild ID: {white}{guild['id']}, {accent_color}Nickname: {white}{guild.get('nick', 'No Nickname')}\n"
    else:
        output += "No mutual guilds\n"
    return output

def generate_page_4(connected_accounts):
    text_color = help_cog.default_colors["text"]
    highlight_color = help_cog.default_colors["highlight"]
    accent_color = help_cog.default_colors["accent"]

    output = f"""                                        {text_color}Connected Accounts:
        {text_color}───────────────────────────────────────────────────────────────────────────────────────────────────────────── \n"""
    
    if connected_accounts:
        for account in connected_accounts:
            account_type = account.get("type", "Unknown")
            account_name = account.get("name", "No Account Name")
            account_id = account.get("id", "No ID")
            output += f"{accent_color}{account_type}: {white}{account_name} (ID: {account_id})\n"
    else:
        output += "No connected accounts\n"
    return output
@bot.command()
async def mutualinfo(ctx, member: discord.User):
    url = f"https://discord.com/api/v9/users/{member.id}/profile?with_mutual_guilds=true&with_mutual_friends=true&with_mutual_friends_count=false"
    
    headers = {
        "Authorization": bot.http.token
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if response.status_code == 200:
            user_info = data.get("user", {})
            mutual_guilds = data.get("mutual_guilds", [])
            mutual_friends = data.get("mutual_friends", [])
            connected_accounts = data.get("connected_accounts", [])
            premium_since = data.get("premium_since", "N/A")
            premium_type = data.get("premium_type", "N/A")

            formatted_premium_since = format_datetime(premium_since)

            page_1 = generate_page_1(user_info, formatted_premium_since, premium_type, connected_accounts)

            message = await ctx.send(f"```ansi\n{page_1}```")

            total_pages = 4  
            current_page = 1 

            def check(m):
                return m.author == ctx.author and m.content.startswith('m') and (m.content[1:].isdigit() or m.content[1] == '-' and m.content[2:].isdigit())

            while True:
                try:
                    msg = await bot.wait_for('message', check=check, timeout=20.0)

                    page_num = int(msg.content[1:])
                    if page_num < 1 or page_num > total_pages:
                        await ctx.send(f"```Invalid page number.```")
                        continue

                    if page_num == 1:
                        page_1 = generate_page_1(user_info, formatted_premium_since, premium_type, connected_accounts)
                        await message.edit(content=f"```ansi\nPage {current_page}/{total_pages}\n{page_1}```")
                    elif page_num == 2:
                        page_2 = generate_page_2(mutual_friends)
                        await message.edit(content=f"```ansi\nPage {page_num}/{total_pages}\n{page_2}```")
                    elif page_num == 3:
                        page_3 = generate_page_3(mutual_guilds)
                        await message.edit(content=f"```ansi\nPage {page_num}/{total_pages}\n{page_3}```")
                    elif page_num == 4:
                        page_4 = generate_page_4(connected_accounts)
                        await message.edit(content=f"```ansi\nPage {page_num}/{total_pages}\n{page_4}```")

                    current_page = page_num 
                    await msg.delete()
                except asyncio.TimeoutError:
                    await message.edit(content=f"```ansi\n{blue}No response received.```")
                    break
                except Exception as e:
                    await ctx.send(f"```{e}```")
                    break

        else:
            await ctx.send(f"```ansi\n{red}Couldn't fetch data. Please try again later.```")
    except Exception as e:
        await ctx.send(f"```Error: {e}```")

@bot.command()
async def stealbio(ctx, member: discord.User):
    url = f"https://discord.com/api/v9/users/{member.id}/profile?with_mutual_guilds=true&with_mutual_friends=true"
    headers = {
        "Authorization": bot.http.token
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if response.status_code == 200:
            target_bio = data.get("user", {}).get("bio", None)

            if target_bio:
                set_bio_url = "https://discord.com/api/v9/users/@me/profile"
                new_bio = {"bio": target_bio}

                update_response = requests.patch(set_bio_url, headers=headers, json=new_bio)

                if update_response.status_code == 200:
                    await ctx.send("```Bio updated!```")
                else:
                    await ctx.send(f"```Failed: {update_response.status_code} - {update_response.json()}```")
            else:
                await ctx.send("```user does not have a bio to copy.```")
        else:
            await ctx.send(f"```Failed: {response.status_code} - {data}```")

    except Exception as e:
        await ctx.send(f"```{e}```")



@bot.command()
async def stealpronoun(ctx, member: discord.User):
    url = f"https://discord.com/api/v9/users/{member.id}/profile?with_mutual_guilds=true&with_mutual_friends=true"
    headers = {
        "Authorization": bot.http.token
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if response.status_code == 200:
            target_pronouns = data.get("user_profile", {}).get("pronouns", None)

            if target_pronouns:
                set_pronoun_url = "https://discord.com/api/v9/users/%40me/profile"
                new_pronoun = {"pronouns": target_pronouns}

                update_response = requests.patch(set_pronoun_url, headers=headers, json=new_pronoun)

                if update_response.status_code == 200:
                    await ctx.send("```Pronouns stolen successful.```")
                else:
                    await ctx.send(f"```Failed: {update_response.status_code} - {update_response.json()}```")
            else:
                await ctx.send("```user does not have pronouns set to copy.```")
        else:
            await ctx.send(f"```Failed: {response.status_code} - {data}```")

    except Exception as e:
        await ctx.send(f"```{e}```")


ladder_messages = [
    "frail bitch LOL",
    "this nigga is disgusting",
    "tired yet?",
    "yo {username} i can go all day LMFAO",
    "# DONT DOZZ OFF RETARD",
    " 'nice autopaster'🤡 ",
    "did i break your ego yet?",
    "YO {username} YOUR MY BITCH LOL",
    "# DONT GET DROWNED PUSSY",
    "LETS GO FOR HOURS RETARD",
    "nigga we dont fwu?",
    "disgusting fucking slut",
    "# DONT SLIT YOUR WRISTS NOW",
    "faggot loser",
    "come die",
    "ILL RIP YOUR FUCKING JAW OUT",
    "# LOOOOOOOOOOOOL",
    "{username} icl your a bitch",
    "insecure fuck LOL",
    "this nigga was caught using a voice changer",
    "dont stumble when i talk to you",
    "# SPEAK UP FUCKING FAGGOT",
    "soybean smelly ass nigga",
    "whatever you claimK",
    "# LOOOOL DIE IN /ROSTER FAGGOT",
    "COME MEET YOUR MATCH RETARD",
    "BREAK UNDER THE PRESSURE",
    "fat indian ass nigga tryba step?",
    "convert this sluts language to english",
    "# LMAOOOOOOO",
    "{username}",
    "nigga ur ass"
]




status_rotation_active = False
emoji_rotation_active = False
current_status = ""
current_emoji = ""

@bot.command(name='rstatus')
async def rotate_status(ctx, *, statuses: str):
    global status_rotation_active, current_status, current_emoji
    await ctx.message.delete()
    
    status_list = [s.strip() for s in statuses.split(',')]
    
    if not status_list:
        await ctx.send("```Please separate statuses by commas.```", delete_after=3)
        return
    
    current_index = 0
    status_rotation_active = True
    
    async def update_status_emoji():
        json_data = {
            'custom_status': {
                'text': current_status,
                'emoji_name': current_emoji
            }
        }

        custom_emoji_match = re.match(r'<a?:(\w+):(\d+)>', current_emoji)
        if custom_emoji_match:
            name, emoji_id = custom_emoji_match.groups()
            json_data['custom_status']['emoji_name'] = name
            json_data['custom_status']['emoji_id'] = emoji_id
        else:
            json_data['custom_status']['emoji_name'] = current_emoji

        async with aiohttp.ClientSession() as session:
            try:
                async with session.patch(
                    'https://discord.com/api/v9/users/@me/settings',
                    headers={'Authorization': bot.http.token, 'Content-Type': 'application/json'},
                    json=json_data
                ) as resp:
                    await resp.read()
            finally:
                await session.close()

    await ctx.send(f"```Status rotation started```")
    
    try:
        while status_rotation_active:
            current_status = status_list[current_index]
            await update_status_emoji()
            await asyncio.sleep(8)
            current_index = (current_index + 1) % len(status_list)
                
    finally:
        current_status = ""
        await update_status_emoji()
        status_rotation_active = False

@bot.command(name='remoji')
async def rotate_emoji(ctx, *, emojis: str):
    global emoji_rotation_active, current_emoji, status_rotation_active
    await ctx.message.delete()
    

    emoji_list = emojis.split()
    
    if not emoji_list:
        await ctx.send("```Please provide emojis separated by spaces.```", delete_after=3)
        return
    
    current_index = 0
    emoji_rotation_active = True
    
    async def update_status_emoji():
        json_data = {
            'custom_status': {
                'text': current_status,
                'emoji_name': current_emoji
            }
        }
        
        custom_emoji_match = re.match(r'<a?:(\w+):(\d+)>', current_emoji)
        if custom_emoji_match:
            name, emoji_id = custom_emoji_match.groups()
            json_data['custom_status']['emoji_name'] = name
            json_data['custom_status']['emoji_id'] = emoji_id
        else:
            json_data['custom_status']['emoji_name'] = current_emoji

        async with aiohttp.ClientSession() as session:
            try:
                async with session.patch(
                    'https://discord.com/api/v9/users/@me/settings',
                    headers={'Authorization': bot.http.token, 'Content-Type': 'application/json'},
                    json=json_data
                ) as resp:
                    await resp.read()
            finally:
                await session.close()

    await ctx.send(f"```Emoji rotation started```")
    
    try:
        while emoji_rotation_active:
            current_emoji = emoji_list[current_index]
            await update_status_emoji()
            await asyncio.sleep(8)
            current_index = (current_index + 1) % len(emoji_list)
                
    finally:
        current_emoji = ""
        await update_status_emoji()
        emoji_rotation_active = False

@bot.command(name='stopstatus')
async def stop_rotate_status(ctx):
    global status_rotation_active
    status_rotation_active = False
    await ctx.send("```Status rotation stopped.```", delete_after=3)

@bot.command(name='stopemoji')
async def stop_rotate_emoji(ctx):
    global emoji_rotation_active
    emoji_rotation_active = False
    await ctx.send("```Emoji rotation stopped.```", delete_after=3)
# POPOUT / AUTOPASTER MUTLI TOKEN


popout_status = {}

@bot.command()
async def popout(ctx, user: discord.Member):
    await ctx.message.delete()   
    if not user:
        await ctx.send("```Please mention a user```")
        return
        
    popout_status[ctx.author.id] = {
        'running': True,
        'target': user
    }
    
    used_messages = set()
    all_messages = ladder_messages.copy()
    tokens_list = load_tokens()
    active_tokens = []
    
    print("\n=== Starting Popout Command ===")
    print(f"Target User: {user.name}#{user.discriminator}")
    print("Checking tokens...")
    
    for token in tokens_list:
        if len(active_tokens) >= 5:
            print("\nSOCIAL WAS HERE | pop out pussy 😂")
            break
            
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://discord.com/api/v9/channels/{ctx.channel.id}', headers=headers) as resp:
                    if resp.status == 200:
                        await asyncio.sleep(0.5)
                        try:
                            client = discord.Client()
                            await client.login(token, bot=False)
                            channel = await client.fetch_channel(ctx.channel.id)
                            
                            active_tokens.append({
                                'token': token,
                                'client': client,
                                'channel': channel
                            })
                            print(f"[+] Token {token[-4:]} ready ({len(active_tokens)}/5)")                           
                        except:
                            print(f"[-] Token {token[-4:]} failed to initialize")
                            if 'client' in locals():
                                await client.close()
                    else:
                        print(f"[-] Token {token[-4:]} no access")
        except Exception as e:
            print(f"[-] Token {token[-4:]} error: {str(e)}")
            
        await asyncio.sleep(0.5)
            
            
    if not active_tokens:
        await ctx.send("```No valid tokens with channel access available```")
        return

    print(f"\nWorking Tokens: {len(active_tokens)}")
    current_token_index = 0
    messages_sent = 0

    async def send_message_group():
        nonlocal current_token_index, used_messages, messages_sent
        
        messages_to_send = []
        for _ in range(4):
            available_messages = [msg for msg in all_messages if msg not in used_messages]
            if not available_messages:
                used_messages.clear()
                available_messages = all_messages
                print("\n=== Refreshing list. \n")
            
            message = random.choice(available_messages)
            used_messages.add(message)
            messages_to_send.append(message)

        messages_to_send = [msg.replace("{username}", user.display_name) for msg in messages_to_send]

        current_token = active_tokens[current_token_index]
        try:
            print(f"\n=== Using Token {current_token_index + 1}/{len(active_tokens)} ===")
            
            channel = current_token['channel']
            
            for message in messages_to_send:
                await channel.send(message)
                messages_sent += 1
                print(f"Message sent ({messages_sent}/4): {message}")
                await asyncio.sleep(random.uniform(0.55555, .8888888))
            
            if messages_sent >= 4:
                messages_sent = 0
                current_token_index = (current_token_index + 1) % len(active_tokens)
                print(f"\nSOCIAL WAS HERE | Switching to new token {current_token_index + 1}/{len(active_tokens)}")
                
        except Exception as e:
            print(f"\n!!! Unexpected Error {current_token_index + 1}: {str(e)} !!!")
            current_token_index = (current_token_index + 1) % len(active_tokens)
            messages_sent = 0

    try:
        while ctx.author.id in popout_status and popout_status[ctx.author.id]['running']:
            await send_message_group()
            await asyncio.sleep(0.1)
    finally:
        for token_data in active_tokens:
            try:
                if token_data['client']:
                    await token_data['client'].close()
            except:
                pass

    print("\n🔪= killed that hoe ass nigga 😂 =🗡️\n")

    


@bot.command()
async def stealpfp(ctx, user: discord.Member = None):
    if not user:
        await ctx.send("```Please mention a user to steal their profile picture```")
        return

    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6Ik1hYyBPUyBYIiwiYnJvd3NlciI6IlNhZmFyaSIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzYwNS4xLjE1IChLSFRNTCwgbGlrZSBHZWNrbykgVmVyc2lvbi8xNi41IFNhZmFyaS82MDUuMS4xNSIsImJyb3dzZXJfdmVyc2lvbiI6IjE2LjUiLCJvc192ZXJzaW9uIjoiMTAuMTUuNyIsInJlZmVycmVyIjoiIiwicmVmZXJyaW5nX2RvbWFpbiI6IiIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNTA2ODQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
    }
    avatar_format = "gif" if user.is_avatar_animated() else "png"
    avatar_url = str(user.avatar_url_as(format=avatar_format))

    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            if response.status == 200:
                image_data = await response.read()
                image_b64 = base64.b64encode(image_data).decode()

                payload = {
                    "avatar": f"data:image/{avatar_format};base64,{image_b64}"
                }

                response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
                
                if response.status_code == 200:
                    await ctx.send(f"```Successfully stole {user.name}'s profile picture```")
                else:
                    await ctx.send(f"```Failed to update profile picture: {response.status_code}```")
            else:
                await ctx.send("```Failed to download the user's profile picture```")

@bot.command()
async def stealbanner(ctx, user: discord.Member = None):
    if not user:
        await ctx.send("```Please mention a user to steal their banner```")
        return

    headers = {
            "authority": "discord.com",
            "method": "PATCH",
            "scheme": "https",
            "accept": "/",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US",
            "authorization": bot.http.token,
            "origin": "https://discord.com/",
            "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Calcutta",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
        }

    profile_url = f"https://discord.com/api/v9/users/{user.id}/profile"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(profile_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                banner_hash = data.get("user", {}).get("banner")
                
                if not banner_hash:
                    await ctx.send("```This user doesn't have a banner```")
                    return
                
                banner_format = "gif" if banner_hash.startswith("a_") else "png"
                banner_url = f"https://cdn.discordapp.com/banners/{user.id}/{banner_hash}.{banner_format}?size=1024"
                
                async with session.get(banner_url) as banner_response:
                    if banner_response.status == 200:
                        banner_data = await banner_response.read()
                        banner_b64 = base64.b64encode(banner_data).decode()
                        
                        payload = {
                            "banner": f"data:image/{banner_format};base64,{banner_b64}"
                        }
                        
                        response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
                        
                        if response.status_code == 200:
                            await ctx.send(f"```Successfully stole {user.name}'s banner```")
                        else:
                            await ctx.send(f"```Failed to update banner: {response.status_code}```")
                    else:
                        await ctx.send("```Failed to download the user's banner```")
            else:
                await ctx.send("```Failed to fetch user profile```")
@bot.command()
async def setname(ctx, *, name: str = None):
    if not name:
        await ctx.send("```Please provide a name to set```")
        return

    headers = {
            "authority": "discord.com",
            "method": "PATCH",
            "scheme": "https",
            "accept": "/",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US",
            "authorization": bot.http.token,
            "origin": "https://discord.com/",
            "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Calcutta",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
        }

    payload = {
        "global_name": name
    }

    response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
    
    if response.status_code == 200:
        await ctx.send(f"```Successfully set global name to: {name}```")
    else:
        await ctx.send(f"```Failed to update global name: {response.status_code}```")

@bot.command()
async def stealname(ctx, member: discord.User = None):
    if not member:
        await ctx.send("```Please mention a user to steal their display name```")
        return
    stolen = member.global_name or member.display_name or str(member.name)
    await setname(ctx, name=stolen)

@bot.command()
async def copyprofile(ctx, user: discord.Member = None):
    if not user:
        await ctx.send("```Please mention a user to copy their profile```")
        return

    headers = {
        "authority": "discord.com",
        "method": "PATCH",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "origin": "https://discord.com",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Calcutta",
        "Content-Type": "application/json",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
    }

    profile_url = f"https://discord.com/api/v9/users/{user.id}/profile"
    profile_response = sesh.get(profile_url, headers=headers)
    
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        
        avatar_url = str(user.avatar_url)
        avatar_response = sesh.get(avatar_url)
        if avatar_response.status_code == 200:
            image_b64 = base64.b64encode(avatar_response.content).decode()
            
            avatar_payload = {
                "avatar": f"data:image/png;base64,{image_b64}",
                "global_name": profile_data.get('user', {}).get('global_name')
            }
            sesh.patch("https://discord.com/api/v9/users/@me", headers=headers, json=avatar_payload)

            profile_payload = {
                "bio": profile_data.get('bio', ""),
                "pronouns": profile_data.get('pronouns', ""),
                "accent_color": profile_data.get('accent_color')
            }
            sesh.patch("https://discord.com/api/v9/users/@me/profile", headers=headers, json=profile_payload)

            await ctx.send(f"```Successfully copied {user.name}'s complete profile```")
        else:
            await ctx.send("```Failed to download avatar```")
    else:
        await ctx.send("```Failed to fetch profile data```")
@bot.command()
async def pbackup(ctx):
    headers = {
        "authority": "discord.com",
        "method": "PATCH",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "origin": "https://discord.com",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Calcutta",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
    }

    if not hasattr(bot, 'profile_backup'):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://discord.com/api/v9/users/@me', headers=headers) as response:
                if response.status == 200:
                    profile_data = await response.json()
                    
                    avatar_url = str(ctx.author.avatar_url)
                    async with session.get(avatar_url) as avatar_response:
                        if avatar_response.status == 200:
                            image_data = await avatar_response.read()
                            image_b64 = base64.b64encode(image_data).decode()
                            
                            bot.profile_backup = {
                                "avatar": f"data:image/png;base64,{image_b64}",
                                "global_name": profile_data.get('global_name'),
                                "bio": profile_data.get('bio', ""),
                                "pronouns": profile_data.get('pronouns', ""),
                                "accent_color": profile_data.get('accent_color'),
                                "banner": profile_data.get('banner')
                            }
                            
                            await ctx.send("```Successfully backed up your profile```")
                        else:
                            await ctx.send("```Failed to backup avatar```")
                else:
                    await ctx.send("```Failed to fetch profile data for backup```")
    else:
        async with aiohttp.ClientSession() as session:
            response = await session.patch(
                "https://discord.com/api/v9/users/@me",
                json=bot.profile_backup,
                headers=headers
            )
            
            if response.status == 200:
                await ctx.send("```Successfully restored your profile from backup```")
                delattr(bot, 'profile_backup') 
            else:
                await ctx.send(f"```Failed to restore profile: {response.status}```")

DISCORD_HEADERS = {
    "standard": {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-discord-timezone": "America/New_York",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIxLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDY4NCwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
    },

    "client": {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3fQ=="
    },

    "mobile": {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": '"Google Chrome";v="121", "Not A(Brand";v="99", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "user-agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IkFuZHJvaWQiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiUGl4ZWwgNiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChMaW51eDsgQW5kcm9pZCAxMzsgUGl4ZWwgNikgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMS4wLjAuMCBNb2JpbGUgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjEyMS4wLjAuMCIsIm9zX3ZlcnNpb24iOiIxMyIsInJlZmVycmVyIjoiIiwicmVmZXJyaW5nX2RvbWFpbiI6IiIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNTA2ODQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
    },

    "firefox": {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.5",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRmlyZWZveCIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQ7IHJ2OjEyMi4wKSBHZWNrby8yMDEwMDEwMSBGaXJlZm94LzEyMi4wIiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIyLjAiLCJvc192ZXJzaW9uIjoiMTAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUwNjg0LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    },

    "byoass": {
            "authority": "discord.com",
            "method": "PATCH",
            "scheme": "https",
            "accept": "/",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US",
            "authorization": bot.http.token,
            "origin": "https://discord.com/",
            "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Calcutta",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
    },

    "desktop": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108"',
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3fQ=="
    },

    "electron": {
        "authority": "discord.com",
        "method": "PATCH",
        "path": "/api/v9/users/@me",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9021 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIxIiwib3NfdmVyc2lvbiI6IjEwLjAuMjI2MjEiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjEgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzgsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE4fQ=="
    },

    "opera": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": '"Opera GX";v="105", "Chromium";v="119", "Not?A_Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiT3BlcmEgR1giLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIxIiwib3NfdmVyc2lvbiI6IjEwLjAuMjI2MjEiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExOS4wLjAuMCBTYWZhcmkvNTM3LjM2IE9QUi8xMDUuMC4wLjAiLCJicm93c2VyX3ZlcnNpb24iOiIxMDUuMC4wLjAiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzgsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE4fQ=="
    },

    "legacy": {
        "authority": "discord.com",
        "method": "PATCH",
        "scheme": "https",
        "accept": "/",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "origin": "https://discord.com/",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "America/New_York",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3fQ=="
    },

    "brave": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": '"Brave";v="122", "Chromium";v="122", "Not(A:Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQnJhdmUiLCJkZXZpY2UiOiIiLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTIyLjAuMC4wIFNhZmFyaS81MzcuMzYiLCJicm93c2VyX3ZlcnNpb24iOiIxMjIuMC4wLjAiLCJvc192ZXJzaW9uIjoiMTAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUwNjg0LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    },

    "edge": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": '"Microsoft Edge";v="122", "Chromium";v="122", "Not(A:Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiTWljcm9zb2Z0IEVkZ2UiLCJkZXZpY2UiOiIiLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTIyLjAuMC4wIFNhZmFyaS81MzcuMzYgRWRnLzEyMi4wLjAuMCIsImJyb3dzZXJfdmVyc2lvbiI6IjEyMi4wLjAuMCIsIm9zX3ZlcnNpb24iOiIxMCIsInJlZmVycmVyIjoiIiwicmVmZXJyaW5nX2RvbWFpbiI6IiIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNTA2ODQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
    },

    "safari": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6Ik1hYyBPUyBYIiwiYnJvd3NlciI6IlNhZmFyaSIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzYwNS4xLjE1IChLSFRNTCwgbGlrZSBHZWNrbykgVmVyc2lvbi8xNi41IFNhZmFyaS82MDUuMS4xNSIsImJyb3dzZXJfdmVyc2lvbiI6IjE2LjUiLCJvc192ZXJzaW9uIjoiMTAuMTUuNyIsInJlZmVycmVyIjoiIiwicmVmZXJyaW5nX2RvbWFpbiI6IiIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNTA2ODQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
    },


    "ipad": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6ImlPUyIsImJyb3dzZXIiOiJTYWZhcmkiLCJkZXZpY2UiOiJpUGFkIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKGlQYWQ7IENQVSBPUyAxNl81IGxpa2UgTWFjIE9TIFgpIEFwcGxlV2ViS2l0LzYwNS4xLjE1IChLSFRNTCwgbGlrZSBHZWNrbykgVmVyc2lvbi8xNi41IE1vYmlsZS8xNUUxNDggU2FmYXJpLzYwNC4xIiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTYuNSIsIm9zX3ZlcnNpb24iOiIxNi41IiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDY4NCwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
    },

    "android": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "user-agent": "Discord-Android/126021",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IkFuZHJvaWQiLCJicm93c2VyIjoiRGlzY29yZCBBbmRyb2lkIiwiZGV2aWNlIjoiUGl4ZWwgNiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImNsaWVudF92ZXJzaW9uIjoiMTI2LjIxIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiZGV2aWNlX3ZlbmRvcl9pZCI6Ijg4OGJhMTYwLWEwMjAtNDNiYS05N2FmLTYzNTFlNjE5ZjA0MSIsImJyb3dzZXJfdXNlcl9hZ2VudCI6IiIsImJyb3dzZXJfdmVyc2lvbiI6IiIsIm9zX3ZlcnNpb24iOiIzMSIsImNsaWVudF9idWlsZF9udW1iZXIiOjEyNjAyMSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
    },

    "ios": {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "user-agent": "Discord-iOS/126021",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6ImlPUyIsImJyb3dzZXIiOiJEaXNjb3JkIGlPUyIsImRldmljZSI6ImlQaG9uZSAxNCBQcm8iLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJjbGllbnRfdmVyc2lvbiI6IjEyNi4yMSIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImRldmljZV92ZW5kb3JfaWQiOiI5OTkxMTgyNC01NjczLTQxNDQtYTU3NS0xMjM0NTY3ODkwMTIiLCJicm93c2VyX3VzZXJfYWdlbnQiOiIiLCJicm93c2VyX3ZlcnNpb24iOiIiLCJvc192ZXJzaW9uIjoiMTYuNSIsImNsaWVudF9idWlsZF9udW1iZXIiOjEyNjAyMSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
    }
}



@bot.command()
async def setpfp(ctx, url: str):
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6Ik1hYyBPUyBYIiwiYnJvd3NlciI6IlNhZmFyaSIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzYwNS4xLjE1IChLSFRNTCwgbGlrZSBHZWNrbykgVmVyc2lvbi8xNi41IFNhZmFyaS82MDUuMS4xNSIsImJyb3dzZXJfdmVyc2lvbiI6IjE2LjUiLCJvc192ZXJzaW9uIjoiMTAuMTUuNyIsInJlZmVycmVyIjoiIiwicmVmZXJyaW5nX2RvbWFpbiI6IiIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNTA2ODQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                image_b64 = base64.b64encode(image_data).decode()
                
                content_type = response.headers.get('Content-Type', '')
                if 'gif' in content_type:
                    image_format = 'gif'
                else:
                    image_format = 'png'

                payload = {
                    "avatar": f"data:image/{image_format};base64,{image_b64}"
                }

                response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
                
                if response.status_code == 200:
                    await ctx.send("```Successfully set profile picture```")
                else:
                    await ctx.send(f"```Failed to update profile picture: {response.status_code}```")
            else:
                await ctx.send("```Failed to download image from URL```")

@bot.command()
async def setbanner(ctx, url: str):
    headers = {
            "authority": "discord.com",
            "method": "PATCH",
            "scheme": "https",
            "accept": "/",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US",
            "authorization": bot.http.token,
            "origin": "https://discord.com/",
            "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Calcutta",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
        }

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                image_b64 = base64.b64encode(image_data).decode()
                
                content_type = response.headers.get('Content-Type', '')
                if 'gif' in content_type:
                    image_format = 'gif'
                else:
                    image_format = 'png'

                payload = {
                    "banner": f"data:image/{image_format};base64,{image_b64}"
                }

                response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
                
                if response.status_code == 200:
                    await ctx.send("```Successfully set banner```")
                else:
                    await ctx.send(f"```Failed to update banner: {response.status_code}```")
            else:
                await ctx.send("```Failed to download image from URL```")

bump_task = None
@bot.command()
async def autobump(ctx):
    global bump_task
    
    if bump_task is not None:
        await ctx.send("```Auto bump is already running```")
        return
    headers = {
        "authority": "discord.com",
        "method": "PATCH",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "origin": "https://discord.com",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Calcutta",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
    }

    payload = {
        "type": 2,
        "application_id": "302050872383242240", 
        "channel_id": str(ctx.channel.id),
        "guild_id": str(ctx.guild.id),
        "session_id": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        "data": {
            "version": "1051151064008769576", 
            "id": "947088344167366698",
            "name": "bump",
            "type": 1,
            "options": [],
            "application_command": {
                "id": "947088344167366698",
                "application_id": "302050872383242240", 
                "version": "1051151064008769576", 
                "name": "bump",
                "description": "Bump this server.", 
                "description_default": "Pushes your server to the top of all your server's tags and the front page",
                "dm_permission": True,
                "type": 1
            }
        }
    }

    async def bump():
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://discord.com/api/v9/interactions",
                        headers=headers,
                        json=payload
                    ) as resp:
                        if resp.status == 204:
                            print("Successfully bumped server")
                        else:
                            print(f"Failed to bump server: {resp.status}")
                
                await asyncio.sleep(7200) 
            except Exception as e:
                print(f"Error during bump: {e}")
                await asyncio.sleep(60)  

    await ctx.send("```Starting auto bump. run '.autobumpoff' to stop```")
    bump_task = bot.loop.create_task(bump())

@bot.command() 
async def autobumpoff(ctx):
    global bump_task
    
    if bump_task is None:
        await ctx.send("```Auto bump is not currently running```")
        return
        
    bump_task.cancel()
    bump_task = None
    await ctx.send("```Auto bump stopped```")



@bot.command()
async def blocked(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]
    headers = {
        'Authorization': bot.http.token,
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get('https://discord.com/api/v9/users/@me/relationships', headers=headers) as resp:
            if resp.status == 200:
                relations = await resp.json()
                blocked = [f"                                                            {highlight_color}{relation['user']['username']}#{relation['user']['discriminator']}" 
                          for relation in relations if relation['type'] == 2]
                
                response = f"""```ansi
                {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                                        {text_color}B L O C K E D  U S E R S [{len(blocked)}]{reset}
                {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
{white}{chr(10).join(blocked) if blocked else 'None'}
```"""
                await ctx.send(response)

@bot.command()
async def pending(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]
    headers = {
        'Authorization': bot.http.token,
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get('https://discord.com/api/v9/users/@me/relationships', headers=headers) as resp:
            if resp.status == 200:
                relations = await resp.json()
                incoming = [f"                                                            {highlight_color}{relation['user']['username']}#{relation['user']['discriminator']}" 
                          for relation in relations if relation['type'] == 3]
                
                response = f"""```ansi
                        {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                                            {text_color}I N C O M I N G  R E Q U E S T S [{len(incoming)}]{reset}
                        {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
{white}{chr(10).join(incoming) if incoming else 'None'}
```"""
                await ctx.send(response)

@bot.command()
async def outgoing(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]
    headers = {
        'Authorization': bot.http.token,
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get('https://discord.com/api/v9/users/@me/relationships', headers=headers) as resp:
            if resp.status == 200:
                relations = await resp.json()
                outgoing = [f"                                                            {highlight_color}{relation['user']['username']}#{relation['user']['discriminator']}" 
                          for relation in relations if relation['type'] == 4]
                
                response = f"""```ansi
                        {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                                            {text_color}O U T G O I N G  R E Q U E S T S [{len(outgoing)}]{reset}
                        {text_color}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
{white}{chr(10).join(outgoing) if outgoing else 'None'}
```"""
                await ctx.send(response)

@bot.command()
async def tnickname(ctx, server_id: str, *, name: str = None):
    tokens = load_tokens()
    total_tokens = len(tokens)
    
    status_msg = await ctx.send(f"""```ansi
{cyan}Token Nickname Changer{reset}
Total tokens available: {total_tokens}
How many tokens do you want to use? (Type 'all' or enter a number)```""")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        amount_msg = await bot.wait_for('message', timeout=20.0, check=check)
        amount = amount_msg.content.lower()
        
        if amount == 'all':
            selected_tokens = tokens
        else:
            try:
                num = int(amount)
                if num > total_tokens:
                    await status_msg.edit(content="```Not enough tokens available```")
                    return
                selected_tokens = random.sample(tokens, num)
            except ValueError:
                await status_msg.edit(content="```Invalid number```")
                return

        if name is None:
            await status_msg.edit(content=f"""```ansi
Choose nickname mode:
1. {yellow}Random{reset} (generates unique names)
2. {green}List{reset} (uses names from tnickname.txt)```""")
            
            mode_msg = await bot.wait_for('message', timeout=30.0, check=check)
            mode = mode_msg.content
            
            if mode == "1":
                names = [''.join(random.choices(string.ascii_letters, k=8)) for _ in range(len(selected_tokens))]
            elif mode == "2":
                try:
                    with open('tnickname.txt', 'r') as f:
                        name_list = [line.strip() for line in f if line.strip()]
                        names = random.choices(name_list, k=len(selected_tokens))
                except FileNotFoundError:
                    await status_msg.edit(content="```tnickname.txt not found```")
                    return
            else:
                await status_msg.edit(content="```Invalid mode selected```")
                return
        else:
            names = [name] * len(selected_tokens)

        success = 0
        headers = {'Authorization': '', 'Content-Type': 'application/json'}
        
        async with aiohttp.ClientSession() as session:
            for i, (token, nickname) in enumerate(zip(selected_tokens, names), 1):
                headers['Authorization'] = token
                async with session.patch(
                    f'https://discord.com/api/v9/guilds/{server_id}/members/@me/nick',
                    headers=headers,
                    json={'nick': nickname}
                ) as resp:
                    if resp.status == 200:
                        success += 1
                    
                    progress = f"""```ansi
{cyan}Changing Nicknames...{reset}
Progress: {i}/{len(selected_tokens)} ({(i/len(selected_tokens)*100):.1f}%)
Success: {success}
Current name: {nickname}```"""
                    await status_msg.edit(content=progress)
                    await asyncio.sleep(0.5)

        final_msg = f"""```ansi
{green}Nickname Change Complete{reset}
Successfully changed: {success}/{len(selected_tokens)} nicknames```"""
        await status_msg.edit(content=final_msg)

    except asyncio.TimeoutError:
        await status_msg.edit(content="```Command timed out```")

@bot.command()
async def tpronouns(ctx, *, pronouns: str = None):
    tokens = load_tokens()
    total_tokens = len(tokens)
    
    

    status_msg = await ctx.send(f"""```ansi\n
{cyan}Token Pronoun Changer{reset}
Total tokens available: {total_tokens}

How many tokens do you want to use? (Type 'all' or enter a number)```""")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        amount_msg = await bot.wait_for('message', timeout=20.0, check=check)
        amount = amount_msg.content.lower()
        
        if amount == 'all':
            selected_tokens = tokens
        else:
            num = int(amount)
            if num > total_tokens:

                await status_msg.edit(content="```NOT enough tokens available```")
                return
            selected_tokens = random.sample(tokens, num)

        if pronouns is None:
            pronoun_list = ['he/him', 'she/her', 'they/them', 'it/its', 'xe/xem', 'ze/zir']
            pronouns = random.choices(pronoun_list, k=len(selected_tokens))
        else:
            pronouns = [pronouns] * len(selected_tokens)

        success = 0
        headers = {'Authorization': '', 'Content-Type': 'application/json'}
        
        async with aiohttp.ClientSession() as session:
            for i, (token, pronoun) in enumerate(zip(selected_tokens, pronouns), 1):
                headers['Authorization'] = token
                async with session.patch(
                    'https://discord.com/api/v9/users/@me/profile',
                    headers=headers,
                    json={'pronouns': pronoun}
                ) as resp:
                    if resp.status == 200:
                        success += 1
                    

                    progress = f"""```ansi\n
{cyan}Changing Pronouns...{reset}
Progress: {i}/{len(selected_tokens)} ({(i/len(selected_tokens)*100):.1f}%)
Success: {success}

Current pronouns: {pronoun}```"""
                    await status_msg.edit(content=progress)
                    await asyncio.sleep(0.5)


        await status_msg.edit(content=f"""```ansi\n
{green}Pronoun Change Complete{reset}

Successfully changed: {success}/{len(selected_tokens)} pronouns```
""")
    except asyncio.TimeoutError:
        await status_msg.edit(content=" timed out")
    except Exception as e:
        await status_msg.edit(content=f" error occurred: {str(e)}")
@bot.command()
async def tbio(ctx, *, bio: str = None):
    tokens = load_tokens()
    total_tokens = len(tokens)
    
    status_msg = await ctx.send(f"""```ansi
{cyan}Token Bio Changer{reset}
Total tokens available: {total_tokens}
How many tokens do you want to use? (Type 'all' or enter a number)```""")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        amount_msg = await bot.wait_for('message', timeout=20.0, check=check)
        amount = amount_msg.content.lower()
        
        if amount == 'all':
            selected_tokens = tokens
        else:
            num = int(amount)
            if num > total_tokens:
                await status_msg.edit(content="```Not enough tokens available```")
                return
            selected_tokens = random.sample(tokens, num)

        if bio is None:
            await status_msg.edit(content=f"""```ansi
Choose bio mode:
1. {yellow}Random{reset} (generates random bios)
2. {green}List{reset} (uses bios from tbio.txt)```""")
            
            mode_msg = await bot.wait_for('message', timeout=30.0, check=check)
            mode = mode_msg.content
            
            if mode == "1":
                bios = [f"Bio #{i} | " + ''.join(random.choices(string.ascii_letters + string.digits, k=20)) for i in range(len(selected_tokens))]
            elif mode == "2":
                try:
                    with open('tbio.txt', 'r') as f:
                        bio_list = [line.strip() for line in f if line.strip()]
                        bios = random.choices(bio_list, k=len(selected_tokens))
                except FileNotFoundError:
                    await status_msg.edit(content="```tbio.txt not found```")
                    return
        else:
            bios = [bio] * len(selected_tokens)

        success = 0
        headers = {'Authorization': '', 'Content-Type': 'application/json'}
        
        async with aiohttp.ClientSession() as session:
            for i, (token, bio_text) in enumerate(zip(selected_tokens, bios), 1):
                headers['Authorization'] = token
                async with session.patch(
                    'https://discord.com/api/v9/users/@me/profile',
                    headers=headers,
                    json={'bio': bio_text}
                ) as resp:
                    if resp.status == 200:
                        success += 1
                    
                    progress = f"""```ansi
{cyan}Changing Bios...{reset}
Progress: {i}/{len(selected_tokens)} ({(i/len(selected_tokens)*100):.1f}%)
Success: {success}
Current bio: {bio_text[:50]}{'...' if len(bio_text) > 50 else ''}```"""
                    await status_msg.edit(content=progress)
                    await asyncio.sleep(0.5)

        await status_msg.edit(content=f"""```ansi
{green}Bio Change Complete{reset}
Successfully changed: {success}/{len(selected_tokens)} bios```""")

    except asyncio.TimeoutError:
        await status_msg.edit(content="```Command timed out```")


@bot.command()
async def tpfp(ctx, url: str = None):
    tokens = load_tokens()
    total_tokens = len(tokens)
    
    status_msg = await ctx.send(f"""```ansi
\u001b[0;36mToken PFP Changer\u001b[0m
Total tokens available: {total_tokens}
How many tokens do you want to use? (Type 'all' or enter a number)```""")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        amount_msg = await bot.wait_for('message', timeout=20.0, check=check)
        amount = amount_msg.content.lower()
        
        if amount == 'all':
            selected_tokens = tokens
        else:
            try:
                num = int(amount)
                if num > total_tokens:
                    await status_msg.edit(content="```Not enough tokens available```")
                    return
                selected_tokens = random.sample(tokens, num)
            except ValueError:
                await status_msg.edit(content="```Invalid number```")
                return

        if url is None:
            await status_msg.edit(content="```Please provide an image URL```")
            return

        success = 0
        failed = 0
        ratelimited = 0
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as img_response:
                if img_response.status != 200:
                    await status_msg.edit(content="```Failed to fetch image```")
                    return
                image_data = await img_response.read()
                image_b64 = base64.b64encode(image_data).decode()
                
                content_type = img_response.headers.get('Content-Type', '')
                if 'gif' in content_type.lower():
                    image_format = 'gif'
                else:
                    image_format = 'png'

            for i, token in enumerate(selected_tokens, 1):
                headers = {
                    'accept': '*/*',
                    'accept-encoding': 'gzip, deflate, br, zstd',
                    'accept-language': 'en-US,en;q=0.7',
                    'authorization': token,
                    'content-type': 'application/json',
                    'origin': 'https://discord.com',
                    'referer': 'https://discord.com/channels/@me',
                    'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'sec-gpc': '1',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'x-debug-options': 'bugReporterEnabled',
                    'x-discord-locale': 'en-US',
                    'x-discord-timezone': 'America/New_York',
                    'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEzMS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTMxLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiJodHRwczovL3NlYXJjaC5icmF2ZS5jb20vIiwicmVmZXJyaW5nX2RvbWFpbiI6InNlYXJjaC5icmF2ZS5jb20iLCJyZWZlcnJlcl9jdXJyZW50IjoiaHR0cHM6Ly9kaXNjb3JkLmNvbS8iLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiJkaXNjb3JkLmNvbSIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjM0NzY5OSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
                }

                
                payload = {
                    "avatar": f"data:image/{image_format};base64,{image_b64}"
                }
                
                try:
                    async with session.get(
                        'https://discord.com/api/v9/users/@me',
                        headers=headers
                    ) as verify_resp:
                        if verify_resp.status != 200:
                            failed += 1
                            print(f"Invalid token {i}")
                            continue

                    async with session.patch(
                        'https://discord.com/api/v9/users/@me',
                        headers=headers,
                        json=payload
                    ) as resp:
                        response_data = await resp.json()
                        
                        if resp.status == 200:
                            success += 1
                        elif "captcha_key" in response_data:
                            failed += 1
                            print(f"Captcha required for token {i}")
                        elif "AVATAR_RATE_LIMIT" in str(response_data):
                            ratelimited += 1
                            print(f"Rate limited for token {i}, waiting 30 seconds")
                            await asyncio.sleep(30)  
                            i -= 1  
                            continue
                        else:
                            failed += 1
                            print(f"Failed to update token {i}: {response_data}")
                        
                        progress = f"""```ansi
\u001b[0;36mChanging Profile Pictures...\u001b[0m
Progress: {i}/{len(selected_tokens)} ({(i/len(selected_tokens)*100):.1f}%)
Success: {success}
Failed: {failed}
Rate Limited: {ratelimited}```"""
                        await status_msg.edit(content=progress)
                        await asyncio.sleep(2)  
                        
                except Exception as e:
                    failed += 1
                    print(f"Error with token {i}: {str(e)}")
                    continue

        await status_msg.edit(content=f"""```ansi
\u001b[0;32mProfile Picture Change Complete\u001b[0m
Successfully changed: {success}/{len(selected_tokens)} avatars
Failed: {failed}
Rate Limited: {ratelimited}```""")

    except asyncio.TimeoutError:
        await status_msg.edit(content="```Command timed out```")
    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")

@bot.command()
async def tstatus(ctx, *, status_text: str = None):
    tokens = load_tokens()
    total_tokens = len(tokens)
    
    if not status_text:
        await ctx.send("```Please provide a status text```")
        return

    status_msg = await ctx.send(f"""```ansi
\u001b[0;36mToken Status Changer\u001b[0m
Total tokens available: {total_tokens}
How many tokens do you want to use? (Type 'all' or enter a number)```""")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        amount_msg = await bot.wait_for('message', timeout=20.0, check=check)
        amount = amount_msg.content.lower()
        
        if amount == 'all':
            selected_tokens = tokens
        else:
            try:
                num = int(amount)
                if num > total_tokens:
                    await status_msg.edit(content="```Not enough tokens available```")
                    return
                selected_tokens = random.sample(tokens, num)
            except ValueError:
                await status_msg.edit(content="```Invalid number```")
                return

        success = 0
        
        async with aiohttp.ClientSession() as session:
            for i, token in enumerate(selected_tokens, 1):
                online_data = {
                    'status': 'online'
                }
                
                status_data = {
                    'custom_status': {
                        'text': status_text
                    },
                    'status': 'online'  
                }
                
                async with session.patch(
                    'https://discord.com/api/v9/users/@me/settings',
                    headers={
                        'Authorization': token,
                        'Content-Type': 'application/json'
                    },
                    json=online_data
                ) as resp1:
                    
                    async with session.patch(
                        'https://discord.com/api/v9/users/@me/settings',
                        headers={
                            'Authorization': token,
                            'Content-Type': 'application/json'
                        },
                        json=status_data
                    ) as resp2:
                        if resp1.status == 200 and resp2.status == 200:
                            success += 1
                        
                        progress = f"""```ansi
\u001b[0;36mChanging Statuses...\u001b[0m
Progress: {i}/{len(selected_tokens)} ({(i/len(selected_tokens)*100):.1f}%)
Success: {success}
Current status: {status_text}```"""
                        await status_msg.edit(content=progress)
                        await asyncio.sleep(0.5)

        await status_msg.edit(content=f"""```ansi
\u001b[0;32mStatus Change Complete\u001b[0m
Successfully changed: {success}/{len(selected_tokens)} statuses to: {status_text}```""")

    except asyncio.TimeoutError:
        await status_msg.edit(content="```Command timed out```")
    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")

@bot.command()
async def tstatusoff(ctx):
    tokens = load_tokens()
    total_tokens = len(tokens)
    
    status_msg = await ctx.send(f"""```ansi
\u001b[0;36mToken Status Reset\u001b[0m
Total tokens available: {total_tokens}
How many tokens do you want to reset? (Type 'all' or enter a number)```""")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        amount_msg = await bot.wait_for('message', timeout=20.0, check=check)
        amount = amount_msg.content.lower()
        
        if amount == 'all':
            selected_tokens = tokens
        else:
            try:
                num = int(amount)
                if num > total_tokens:
                    await status_msg.edit(content="```Not enough tokens available```")
                    return
                selected_tokens = random.sample(tokens, num)
            except ValueError:
                await status_msg.edit(content="```Invalid number```")
                return

        success = 0
        
        async with aiohttp.ClientSession() as session:
            for i, token in enumerate(selected_tokens, 1):

                reset_data = {
                    'custom_status': None,
                    'status': 'online' 
                }
                
                async with session.patch(
                    'https://discord.com/api/v9/users/@me/settings',
                    headers={
                        'Authorization': token,
                        'Content-Type': 'application/json'
                    },
                    json=reset_data
                ) as resp:
                    if resp.status == 200:
                        success += 1
                    
                    progress = f"""```ansi
\u001b[0;36mResetting Statuses...\u001b[0m
Progress: {i}/{len(selected_tokens)} ({(i/len(selected_tokens)*100):.1f}%)
Success: {success}```"""
                    await status_msg.edit(content=progress)
                    await asyncio.sleep(0.5)

        await status_msg.edit(content=f"""```ansi
\u001b[0;32mStatus Reset Complete\u001b[0m
Successfully reset: {success}/{len(selected_tokens)} statuses```""")

    except asyncio.TimeoutError:
        await status_msg.edit(content="```Command timed out```")
    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")

@bot.command()
async def tinfo(ctx, token_input: str):
    """Get token account information"""
    tokens = load_tokens()
    
    try:
        index = int(token_input) - 1
        if 0 <= index < len(tokens):
            token = tokens[index]
        else:
            await ctx.send("```Invalid token number```")
            return
    except ValueError:
        token = token_input
        if token not in tokens:
            await ctx.send("```Invalid token```")
            return

    status_msg = await ctx.send("```Fetching token information...```")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://discord.com/api/v9/users/@me',
                headers={
                    'Authorization': token,
                    'Content-Type': 'application/json'
                }
            ) as resp:
                if resp.status != 200:
                    await status_msg.edit(content="```Failed to fetch token information```")
                    return
                
                user_data = await resp.json()
                
                async with session.get(
                    'https://discord.com/api/v9/users/@me/connections',
                    headers={
                        'Authorization': token,
                        'Content-Type': 'application/json'
                    }
                ) as conn_resp:
                    connections = await conn_resp.json() if conn_resp.status == 200 else []

                async with session.get(
                    'https://discord.com/api/v9/users/@me/guilds',
                    headers={
                        'Authorization': token,
                        'Content-Type': 'application/json'
                    }
                ) as guild_resp:
                    guilds = await guild_resp.json() if guild_resp.status == 200 else []

                created_at = datetime.fromtimestamp(((int(user_data['id']) >> 22) + 1420070400000) / 1000)
                created_date = created_at.strftime('%Y-%m-%d %H:%M:%S')

                info = f"""```ansi
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                \u001b[0;36mToken Account Information\u001b[0m

                                \u001b[0;33mBasic Information:\u001b[0m
                                Username: {user_data['username']}#{user_data['discriminator']}
                                ID: {user_data['id']}
                                Email: {user_data.get('email', 'Not available')}
                                Phone: {user_data.get('phone', 'Not available')}
                                Created: {created_date}
                                Verified: {user_data.get('verified', False)}
                                MFA Enabled: {user_data.get('mfa_enabled', False)}

                                \u001b[0;33mNitro Status:\u001b[0m
                                Premium: {bool(user_data.get('premium_type', 0))}
                                Type: {['None', 'Classic', 'Full'][user_data.get('premium_type', 0)]}

                                \u001b[0;33mStats:\u001b[0m
                                Servers: {len(guilds)}
                                Connections: {len(connections)}

                                \u001b[0;33mProfile:\u001b[0m
                                Bio: {user_data.get('bio', 'No bio set')}
                                Banner: {'Yes' if user_data.get('banner') else 'No'}
                                Avatar: {'Yes' if user_data.get('avatar') else 'Default'}
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────────────────────

```"""

                await status_msg.edit(content=info)

    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")

@bot.command()
async def unfriend(ctx, user):
    if isinstance(user, str):
        try:
            user_id = int(user)
            user_name = user
        except ValueError:
            await ctx.send("```Invalid user ID```")
            return
    else:
        user_id = user.id
        user_name = user.name

    headers = {
        'Authorization': bot.http.token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=',
        'X-Discord-Locale': 'en-US',
        'X-Debug-Options': 'bugReporterEnabled',
        'Origin': 'https://discord.com',
        'Referer': 'https://discord.com/channels/@me'
    }

    msg = await ctx.send(f"```Removing {user_name} from friends...```")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'https://discord.com/api/v9/users/@me/relationships/{user_id}',
                headers=headers
            ) as resp:
                if resp.status == 204:
                    await msg.edit(content=f"```Successfully removed {user_name} from friends```")
                else:
                    await msg.edit(content=f"```Failed to remove {user_name} from friends. Status: {resp.status}```")
    except Exception as e:
        await msg.edit(content=f"```An error occurred: {str(e)}```")


@bot.command()
async def block(ctx, user):
    if isinstance(user, str):
        try:
            user_id = int(user)
            user_name = user
        except ValueError:
            await ctx.send("```Invalid user ID```")
            return
    else:
        user_id = user.id
        user_name = user.name

    headers = {
        'Authorization': bot.http.token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=',
        'X-Discord-Locale': 'en-US',
        'X-Debug-Options': 'bugReporterEnabled',
        'Origin': 'https://discord.com',
        'Referer': 'https://discord.com/channels/@me'
    }

    msg = await ctx.send(f"```Blocking {user_name}...```")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f'https://discord.com/api/v9/users/@me/relationships/{user_id}',
                headers=headers,
                json={"type": 2}
            ) as resp:
                if resp.status in [200, 204]:
                    await msg.edit(content=f"```Successfully blocked {user_name}```")
                else:
                    await msg.edit(content=f"```Failed to block {user_name}. Status: {resp.status}```")
    except Exception as e:
        await msg.edit(content=f"```An error occurred: {str(e)}```")

@bot.command()
async def unblock(ctx, user):
    if isinstance(user, str):
        try:
            user_id = int(user)
            user_name = user
        except ValueError:
            await ctx.send("```Invalid user ID```")
            return
    else:
        user_id = user.id
        user_name = user.name

    headers = {
        'Authorization': bot.http.token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=',
        'X-Discord-Locale': 'en-US',
        'X-Debug-Options': 'bugReporterEnabled',
        'Origin': 'https://discord.com',
        'Referer': 'https://discord.com/channels/@me'
    }

    msg = await ctx.send(f"```Unblocking {user_name}...```")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'https://discord.com/api/v9/users/@me/relationships/{user_id}',
                headers=headers
            ) as resp:
                if resp.status == 204:
                    await msg.edit(content=f"```Successfully unblocked {user_name}```")
                else:
                    await msg.edit(content=f"```Failed to unblock {user_name}. Status: {resp.status}```")
    except Exception as e:
        await msg.edit(content=f"```An error occurred: {str(e)}```")


@bot.command()
async def clienttheme(ctx, mode: str = None):
    if not mode:
        theme_list = f"""```ansi
                                         Available Themes:
        {blue}─────────────────────────────────────────────────────────────────────────────────────────────────────────────

                    {red}• {white}mint            {black}- Mint Apple theme (Nitro)
                    {red}• {white}citrus          {black}- Citrus Sherbert theme (Nitro)
                    {red}• {white}retro           {black}- Retro Raincloud theme (Nitro)
                    {red}• {white}hanami          {black}- Hanami theme (Nitro)
                    {red}• {white}sunrise         {black}- Sunrise theme (Nitro)
                    {red}• {white}cotton          {black}- Cotton Candy theme (Nitro)
                    {red}• {white}lofi            {black}- Lofi Vibes theme (Nitro)
                    {red}• {white}desert          {black}- Desert Khaki theme (Nitro)
                    {red}• {white}sunset          {black}- Sunset theme (Nitro)
                    {red}• {white}chroma          {black}- Chroma Glow theme (Nitro)
                    {red}• {white}forest          {black}- Forest theme (Nitro)
                    {red}• {white}crimson         {black}- Crimson Moon theme (Nitro)
                    {red}• {white}midnight        {black}- Midnight Blurple theme (Nitro)
                    {red}• {white}mars            {black}- Mars theme (Nitro)
                    {red}• {white}dusk            {black}- Dusk theme (Nitro)
                    {red}• {white}undersea        {black}- Under the Sea theme (Nitro)
                    {red}• {white}retrostorm      {black}- Retro Storm theme (Nitro)
                    {red}• {white}neon            {black}- Neon Lights theme (Nitro)
                    {red}• {white}sepia           {black}- Sepia theme (Nitro)
                    {red}• {white}aurora          {black}- Aurora theme (Nitro)
                    {red}• {white}strawberry      {black}- Strawberry Lemonade theme (Nitro)
                    {red}• {white}blurple         {black}- Blurple Twilight theme (Nitro)

        {blue}───────────────────────────────────────────────────────────────────────────────────────────────────────────── 

                                     Usage: {red}.clienttheme <theme>```"""
        await ctx.send(theme_list)
        return
        
    mode = mode.lower()
    theme_settings = {
        'mint': {'appearance': 2, 'color': 0x4DBA88},
        'citrus': {'appearance': 1, 'color': 0xF5A051},
        'retro': {'appearance': 2, 'color': 0x8B8B8B},
        'hanami': {'appearance': 1, 'color': 0xFFB7D1},
        'sunrise': {'appearance': 1, 'color': 0xFFB6C1},
        'cotton': {'appearance': 1, 'color': 0xFFB0E6},
        'lofi': {'appearance': 2, 'color': 0x5C5C5C},
        'desert': {'appearance': 1, 'color': 0xD2B48C},
        'sunset': {'appearance': 2, 'color': 0xFF7F50},
        'chroma': {'appearance': 2, 'color': 0x00FF00},
        'forest': {'appearance': 2, 'color': 0x228B22},
        'crimson': {'appearance': 2, 'color': 0xDC143C},
        'midnight': {'appearance': 2, 'color': 0x7289DA},
        'mars': {'appearance': 2, 'color': 0xCD5C5C},
        'dusk': {'appearance': 2, 'color': 0x483D8B},
        'undersea': {'appearance': 2, 'color': 0x20B2AA},
        'retrostorm': {'appearance': 2, 'color': 0x4B0082},
        'neon': {'appearance': 2, 'color': 0xFF1493},
        'sepia': {'appearance': 1, 'color': 0xD2691E},
        'aurora': {'appearance': 2, 'color': 0x9400D3},
        'strawberry': {'appearance': 1, 'color': 0xFFB5C5},
        'blurple': {'appearance': 2, 'color': 0x7289DA}
    }

    if mode not in theme_settings:
        await ctx.send(f"```ansi\n{red}Invalid theme. Use {red}.clienttheme to see available themes```")
        return

    settings = theme_settings[mode]
    data = {
        'theme': 'citrus' if settings['appearance'] == 2 else 'light'
    }

    status_msg = await ctx.send(f"```ansi\n{blue}Changing Discord theme to {green}{mode}...```")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                'https://discord.com/api/v9/users/@me/settings',
                headers={
                    'Authorization': bot.http.token,
                    'Content-Type': 'application/json'
                },
                json=data
            ) as resp:
                if resp.status == 200:
                    await status_msg.edit(content=f"```ansi\n{green}Successfully changed Discord theme to {mode}```")
                else:
                    error_data = await resp.json()
                    if 'message' in error_data and 'nitro' in error_data['message'].lower():
                        await status_msg.edit(content=f"```ansi\n{red}This theme requires Discord Nitro```")
                    else:
                        await status_msg.edit(content=f"```ansi\n{red}Failed to change theme. Status: {resp.status}\nError: {await resp.text()}```")
    except Exception as e:
        await status_msg.edit(content=f"```ansi\n{red}An error occurred: {str(e)}```")


self_gcname = [
    "discord.gg/voidv2 | t.me/v0idtool runs you LMFAO",
    "yo {user} wake the fuck up discord.gg/voidv2 | t.me/v0idtool",
    "nigga your a bitch {user} discord.gg/voidv2 | t.me/v0idtool",
    "pedophilic retard {user} discord.gg/voidv2 | t.me/v0idtool",
    "{UPuser} STOP RUBBING YOUR NIPPLES LOL discord.gg/voidv2 | t.me/v0idtool",
    "{UPuser} LOOOL HAILK DO SOMETHING RETARD discord.gg/voidv2 | t.me/v0idtool",
    "{user} come die to prophet nigga discord.gg/voidv2 | t.me/v0idtool",
    "{UPuser} ILL CAVE YOUR SKULL IN discord.gg/voidv2 | t.me/v0idtool",
    "frail bitch discord.gg/voidv2 | t.me/v0idtool",
    "{UPuser} I WILL KILL YOU LMFAO discord.gg/voidv2 | t.me/v0idtool",
    "{user} nigga your slow as shit discord.gg/voidv2 | t.me/v0idtool",
    "YO {user} WAKE THE FUCK UP discord.gg/voidv2 | t.me/v0idtool",
    "DONT FAIL THE CHECK {UPuser} LOL discord.gg/voidv2 | t.me/v0idtool",
    "who let this shitty nigga own a client?? discord.gg/voidv2 | t.me/v0idtool",
    "faggot bitch stop rubbing your nipples to little girls discord.gg/voidv2 | t.me/v0idtool",
    "leave = fold okay {user}? LMFAO discord.gg/voidv2 | t.me/v0idtool",
    "{user} this shit isnt a dream LMFAO discord.gg/voidv2 | t.me/v0idtool"

]


ugc_task = None

@bot.command()
async def ugc(ctx, user: discord.User):
    global ugc_task
    
    if ugc_task is not None:
        await ctx.send("```Group chat name changer is already running```")
        return
        
    if not isinstance(ctx.channel, discord.GroupChannel):
        await ctx.send("```This command can only be used in group chats.```")
        return

    async def name_changer():
        counter = 1
        unused_names = list(self_gcname)
        
        while True:
            try:
                if not unused_names:
                    unused_names = list(self_gcname)
                
                base_name = random.choice(unused_names)
                unused_names.remove(base_name)
                
                formatted_name = base_name.replace("{user}", user.name).replace("{UPuser}", user.name.upper())
                new_name = f"{formatted_name} {counter}"
                
                await ctx.channel._state.http.request(
                    discord.http.Route(
                        'PATCH',
                        '/channels/{channel_id}',
                        channel_id=ctx.channel.id
                    ),
                    json={'name': new_name}
                )
                
                await asyncio.sleep(0.1)
                counter += 1
                
            except discord.HTTPException as e:
                if e.code == 429:
                    retry_after = e.retry_after if hasattr(e, 'retry_after') else 1
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    await ctx.send(f"```Error: {str(e)}```")
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                await ctx.send(f"```Error: {str(e)}```")
                break

    ugc_task = asyncio.create_task(name_changer())
    await ctx.send("```Group chat name changer started```")

@bot.command()
async def ugcend(ctx):
    global ugc_task
    
    if ugc_task is None:
        await ctx.send("```Group chat name changer is not currently running```")
        return
        
    ugc_task.cancel()
    ugc_task = None
    await ctx.send("```Group chat name changer stopped```")
@bot.command()
async def tleave(ctx, server_id: str = None):
    if not server_id:
        await ctx.send("```Please provide a server ID```")
        return
        
    tokens = load_tokens()
    total_tokens = len(tokens)
    
    status_msg = await ctx.send(f"""```ansi
\u001b[0;36mToken Server Leave\u001b[0m
Total tokens available: {total_tokens}
How many tokens do you want to use? (Type 'all' or enter a number)```""")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        amount_msg = await bot.wait_for('message', timeout=20.0, check=check)
        amount = amount_msg.content.lower()
        
        if amount == 'all':
            selected_tokens = tokens
        else:
            try:
                num = int(amount)
                if num > total_tokens:
                    await status_msg.edit(content="```Not enough tokens available```")
                    return
                selected_tokens = random.sample(tokens, num)
            except ValueError:
                await status_msg.edit(content="```Invalid number```")
                return

        success = 0
        failed = 0
        ratelimited = 0
        
        async with aiohttp.ClientSession() as session:
            for i, token in enumerate(selected_tokens, 1):
                headers = {
                    'accept': '*/*',
                    'accept-encoding': 'gzip, deflate, br, zstd',
                    'accept-language': 'en-US,en;q=0.7',
                    'authorization': token,
                    'content-type': 'application/json',
                    'origin': 'https://discord.com',
                    'referer': 'https://discord.com/channels/@me',
                    'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'sec-gpc': '1',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'x-debug-options': 'bugReporterEnabled',
                    'x-discord-locale': 'en-US',
                    'x-discord-timezone': 'America/New_York',
                    'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEzMS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTMxLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiJodHRwczovL3NlYXJjaC5icmF2ZS5jb20vIiwicmVmZXJyaW5nX2RvbWFpbiI6InNlYXJjaC5icmF2ZS5jb20iLCJyZWZlcnJlcl9jdXJyZW50IjoiaHR0cHM6Ly9kaXNjb3JkLmNvbS8iLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiJkaXNjb3JkLmNvbSIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjM0NzY5OSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
                }
                
                try:

                    async with session.delete(
                        f'https://discord.com/api/v9/users/@me/guilds/{server_id}',
                        headers=headers,
                        json={"lurking": False}  
                    ) as resp:
                        response_data = await resp.text()
                        
                        if resp.status in [204, 200]:  
                            success += 1
                        elif resp.status == 429:  
                            ratelimited += 1
                            retry_after = float((await resp.json()).get('retry_after', 5))
                            print(f"Rate limited for token {i}, waiting {retry_after} seconds")
                            await asyncio.sleep(retry_after)
                            i -= 1  
                            continue
                        else:
                            failed += 1
                            print(f"Failed to leave server with token {i}: {response_data}")
                        
                        progress = f"""```ansi
\u001b[0;36mLeaving Server...\u001b[0m
Progress: {i}/{len(selected_tokens)} ({(i/len(selected_tokens)*100):.1f}%)
Success: {success}
Failed: {failed}
Rate Limited: {ratelimited}```"""
                        await status_msg.edit(content=progress)
                        await asyncio.sleep(1)   
                        
                except Exception as e:
                    failed += 1
                    print(f"Error with token {i}: {str(e)}")
                    continue

        await status_msg.edit(content=f"""```ansi
\u001b[0;32mServer Leave Complete\u001b[0m
Successfully left: {success}/{len(selected_tokens)}
Failed: {failed}
Rate Limited: {ratelimited}```""")

    except asyncio.TimeoutError:
        await status_msg.edit(content="```Command timed out```")
    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")
        
@bot.command()
async def friend(ctx, user_id: str = None):
    if not user_id:
        await ctx.send("```Please provide a user ID```")
        return
    
    status_msg = await ctx.send("```Sending friend request...```")
    
    try:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.7',
            'authorization': bot.http.token,
            'content-type': 'application/json',
            'origin': 'https://discord.com',
            'referer': 'https://discord.com/channels/@me',
            'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-debug-options': 'bugReporterEnabled',
            'x-discord-locale': 'en-US',
            'x-discord-timezone': 'America/New_York',
            'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEzMS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTMxLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiJodHRwczovL3NlYXJjaC5icmF2ZS5jb20vIiwicmVmZXJyaW5nX2RvbWFpbiI6InNlYXJjaC5icmF2ZS5jb20iLCJyZWZlcnJlcl9jdXJyZW50IjoiaHR0cHM6Ly9kaXNjb3JkLmNvbS8iLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiJkaXNjb3JkLmNvbSIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjM0NzY5OSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
                }

        async with aiohttp.ClientSession() as session:

            async with session.get(
                f'https://discord.com/api/v9/users/{user_id}/profile?with_mutual_guilds=false',
                headers=headers
            ) as resp:
                if resp.status != 200:
                    await status_msg.edit(content="```Failed to fetch user info```")
                    return
                user_data = await resp.json()
                username = user_data.get('user', {}).get('username', '')


            async with session.put(
                f'https://discord.com/api/v9/users/@me/relationships/{user_id}',
                headers=headers,
                json={}
            ) as resp:
                if resp.status in [204, 200]:
                    await status_msg.edit(content=f"```Successfully sent friend request to {username}```")
                elif resp.status == 429:
                    retry_after = float((await resp.json()).get('retry_after', 5))
                    await status_msg.edit(content=f"```Rate limited. Try again in {retry_after} seconds```")
                elif resp.status == 400:
                    response_data = await resp.text()
                    if "You need to verify your account" in response_data:
                        await status_msg.edit(content="```Account needs verification```")
                    else:
                        await status_msg.edit(content=f"```Failed to send friend request: {response_data}```")
                else:
                    await status_msg.edit(content=f"```Failed to send friend request (Status: {resp.status})```")

    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")

@bot.command()
async def fnick(ctx, user_id: str, *, nickname: str = None):
    if not user_id:
        await ctx.send("```Usage: .fnick <user_id> <nickname>```")
        return
    
    status_msg = await ctx.send("```Setting friend nickname...```")
    
    try:
        try:
            user_id = int(user_id)
        except ValueError:
            await status_msg.edit(content="```Invalid user ID```")
            return

        headers = {
            'Authorization': bot.http.token,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://discord.com/api/v9/users/@me/relationships',
                headers=headers
            ) as resp:
                if resp.status != 200:
                    await status_msg.edit(content="```Failed to fetch relationships```")
                    return
                
                relationships = await resp.json()
                friend = next((r for r in relationships if str(r.get('user', {}).get('id')) == str(user_id)), None)
                
                if not friend:
                    await status_msg.edit(content="```This user is not in your friends list```")
                    return
                
                username = friend.get('user', {}).get('username', 'Unknown')

            payload = {
                "type": 1,
                "nickname": nickname if nickname else None
            }

            async with session.patch(
                f'https://discord.com/api/v9/users/@me/relationships/{user_id}',
                headers=headers,
                json=payload
            ) as resp:
                if resp.status in [200, 204]:
                    action = 'set' if nickname else 'removed'
                    await status_msg.edit(content=f"```Successfully {action} nickname for {username}```")
                elif resp.status == 429:
                    retry_after = float((await resp.json()).get('retry_after', 5))
                    await status_msg.edit(content=f"```Rate limited. Try again in {retry_after} seconds```")
                else:
                    error_text = await resp.text()
                    await status_msg.edit(content=f"```Failed to set nickname: {error_text}```")

    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")
@bot.command()
async def fnote(ctx, user_id: str, *, note: str = None):
    if not user_id:
        await ctx.send("```Usage: .fnote <user_id> <note>```")
        return
    
    status_msg = await ctx.send("```Setting friend note...```")
    
    try:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.7',
            'authorization': bot.http.token,
            'content-type': 'application/json',
            'origin': 'https://discord.com',
            'referer': 'https://discord.com/channels/@me',
            'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-debug-options': 'bugReporterEnabled'
        }

        payload = {"note": note} if note else {"note": ""}

        async with aiohttp.ClientSession() as session:
            async with session.put(
                f'https://discord.com/api/v9/users/@me/notes/{user_id}',
                headers=headers,
                json=payload
            ) as resp:
                if resp.status in [200, 204]:
                    await status_msg.edit(content=f"```Successfully {'set' if note else 'removed'} friend note```")
                else:
                    error_text = await resp.text()
                    await status_msg.edit(content=f"```Failed to set note: {error_text}```")

    except Exception as e:
        await status_msg.edit(content=f"```An error occurred: {str(e)}```")



@bot.group(invoke_without_command=True)
async def autopress(ctx, user: discord.Member = None):
    if ctx.invoked_subcommand is None:
        if not user:
            await ctx.send("```Please mention a user```")
            return
            
        user_id = str(ctx.author.id)
        if user_id not in autopress_messages or not autopress_messages[user_id]:
            await ctx.send("```No messages configured. Use .autopress add <message> to add messages```")
            return
            
        autopress_status[ctx.author.id] = {
            'running': True,
            'target': user
        }
        
        used_messages = set()
        messages_sent = 0
        
        print(f"\n=== Starting Autopress Command ===")
        print(f"Target User: {user.name}")
        
        async def send_message_group():
            nonlocal used_messages, messages_sent
            
            available_messages = [msg for msg in autopress_messages[user_id] if msg not in used_messages]
            if not available_messages:
                used_messages.clear()
                available_messages = autopress_messages[user_id]
                print("\n=== Refreshing message list ===\n")
            
            message = random.choice(available_messages)
            used_messages.add(message)
            
            try:
                full_message = f"{user.mention} {message.replace('{username}', user.display_name)}"
                await ctx.channel.send(full_message)
                messages_sent += 1
                print(f"Message sent ({messages_sent}): {message}")
                
            except Exception as e:
                print(f"\nError sending message: {str(e)}")
        
        try:
            while ctx.author.id in autopress_status and autopress_status[ctx.author.id]['running']:
                await send_message_group()
                await asyncio.sleep(random.uniform(0.5, 3.5))
        finally:
            if ctx.author.id in autopress_status:
                del autopress_status[ctx.author.id]
        
        print("\n=== Autopress Stopped ===\n")

@autopress.command(name="add")
async def add_message(ctx, *, message: str):
    user_id = str(ctx.author.id)
    if user_id not in autopress_messages:
        autopress_messages[user_id] = []
    
    autopress_messages[user_id].append(message)
    await ctx.send(f"```Added message: {message}```")
    save_messages()

@autopress.command(name="remove") 
async def remove_message(ctx, index: int):
    user_id = str(ctx.author.id)
    if user_id not in autopress_messages or not autopress_messages[user_id]:
        await ctx.send("```No messages configured```")
        return
        
    if 1 <= index <= len(autopress_messages[user_id]):
        removed = autopress_messages[user_id].pop(index-1)
        await ctx.send(f"```Removed message: {removed}```")
        save_messages()
    else:
        await ctx.send(f"```Invalid index. Use .autopress list to see message indices```")

@autopress.command(name="list")
async def list_messages(ctx):
    user_id = str(ctx.author.id)
    if user_id not in autopress_messages or not autopress_messages[user_id]:
        await ctx.send("```No messages configured```")
        return
        
    message_list = "\n".join(f"{i+1}. {msg}" for i, msg in enumerate(autopress_messages[user_id]))
    await ctx.send(f"```Your configured messages:\n\n{message_list}```")

@autopress.command(name="clear")
async def clear_messages(ctx):
    user_id = str(ctx.author.id)
    if user_id in autopress_messages:
        autopress_messages[user_id] = []
        await ctx.send("```Cleared all messages```")
        save_messages()
    else:
        await ctx.send("```No messages configured```")

@autopress.command(name="stop")
async def stop_autopress(ctx):
    if ctx.author.id in autopress_status:
        del autopress_status[ctx.author.id]
        await ctx.send("```Stopped autopress```")
    else:
        await ctx.send("```Autopress is not running```")

def save_messages():
    with open(data('autopress.json'), 'w') as f:
        json.dump(autopress_messages, f)

def load_messages():
    global autopress_messages
    try:
        with open(data('autopress.json'), 'r') as f:
            autopress_messages = json.load(f)
    except FileNotFoundError:
        autopress_messages = {}



@bot.group(invoke_without_command=True)
async def autokill(ctx, user: discord.Member = None):
    if ctx.invoked_subcommand is None:
        if not user:
            await ctx.send("```Please mention a user```")
            return
            
        user_id = str(ctx.author.id)
        if user_id not in autokill_messages or not autokill_messages[user_id]:
            await ctx.send("```No messages configured. Use .autokill add <message> to add messages```")
            return
            
        autokill_status[ctx.author.id] = {
            'running': True,
            'target': user
        }
        
        used_messages = set()
        messages_sent = 0
        
        print(f"\n=== Starting Autokill Command ===")
        print(f"Target User: {user.name}")
        
        async def send_message_group(channel):
            nonlocal used_messages, messages_sent
            
            available_messages = [msg for msg in autokill_messages[user_id] if msg not in used_messages]
            if not available_messages:
                used_messages.clear()
                available_messages = autokill_messages[user_id]
                print("\n=== Refreshing message list ===\n")
            
            message = random.choice(available_messages)
            used_messages.add(message)
            
            try:
                full_message = f"{user.mention} {message.replace('{username}', user.display_name)}"
                await channel.send(full_message)
                messages_sent += 1
                print(f"Message sent ({messages_sent}): {message}")
                
            except Exception as e:
                print(f"\nError sending message: {str(e)}")
        
        try:
            while (ctx.author.id in autokill_status and 
                autokill_status[ctx.author.id]['running']):
                
                available_channels = []
                
                for channel in ctx.guild.text_channels:
                    if channel.permissions_for(ctx.guild.me).send_messages:
                        available_channels.append(channel)
                
                if available_channels:
                    random.shuffle(available_channels)
                    
                    for channel in available_channels:
                        await send_message_group(channel)
                        await asyncio.sleep(random.uniform(1.5, 3.5))
                    
                    await asyncio.sleep(random.uniform(5, 10))
                
        finally:
            if ctx.author.id in autokill_status:
                autokill_status[ctx.author.id]['running'] = False
                del autokill_status[ctx.author.id]
        
        print("\n=== Autokill Stopped ===\n")

@autokill.command(name="add")
async def add_kill_message(ctx, *, message: str):
    user_id = str(ctx.author.id)
    if user_id not in autokill_messages:
        autokill_messages[user_id] = []
    
    autokill_messages[user_id].append(message)
    await ctx.send(f"```Added message: {message}```")
    save_kill_messages()

@autokill.command(name="remove")
async def remove_kill_message(ctx, index: int):
    user_id = str(ctx.author.id)
    if user_id not in autokill_messages or not autokill_messages[user_id]:
        await ctx.send("```No messages configured```")
        return
        
    if 1 <= index <= len(autokill_messages[user_id]):
        removed = autokill_messages[user_id].pop(index-1)
        await ctx.send(f"```Removed message: {removed}```")
        save_kill_messages()
    else:
        await ctx.send(f"```Invalid index. Use .autokill list to see message indices```")

@autokill.command(name="list")
async def list_kill_messages(ctx):
    user_id = str(ctx.author.id)
    if user_id not in autokill_messages or not autokill_messages[user_id]:
        await ctx.send("```No messages configured```")
        return
        
    message_list = "\n".join(f"{i+1}. {msg}" for i, msg in enumerate(autokill_messages[user_id]))
    await ctx.send(f"```Your configured messages:\n\n{message_list}```")

@autokill.command(name="clear")
async def clear_kill_messages(ctx):
    user_id = str(ctx.author.id)
    if user_id in autokill_messages:
        autokill_messages[user_id] = []
        await ctx.send("```Cleared all messages```")
        save_kill_messages()
    else:
        await ctx.send("```No messages configured```")

@autokill.command(name="stop")
async def stop_autokill(ctx):
    if ctx.author.id in autokill_status:
        autokill_status[ctx.author.id]['running'] = False
        del autokill_status[ctx.author.id]
        await ctx.send("```Stopped autokill```")
    else:
        await ctx.send("```Autokill is not running```")

def save_kill_messages():
    with open(data('autokill.json'), 'w') as f:
        json.dump(autokill_messages, f)

def load_kill_messages():
    global autokill_messages
    try:
        with open(data('autokill.json'), 'r') as f:
            autokill_messages = json.load(f)
    except FileNotFoundError:
        autokill_messages = {}



STAT_RESPONSES = {
    'rizz_levels': ['-9999', '-∞', 'ERROR: NOT FOUND', 'Below Zero', 'Nonexistent', 'Windows 95'],
    'bitches': ['0', '-1', 'Negative', 'None', 'Error 404', 'Imaginary'],
    'grass_status': ['Never Touched', 'What is Grass?', 'Allergic', 'Grass Blocked', 'Touch Pending'],
    'karma_levels': ['-999', '-∞', 'Rock Bottom', 'Below Sea Level', 'Catastrophic'],
    'cringe_levels': ['Maximum', '∞%', 'Over 9000', 'Critical', 'Terminal', 'Beyond Science'],
    'final_ratings': ['MASSIVE L', 'CRITICAL FAILURE', 'TOUCH GRASS ASAP', 'SYSTEM FAILURE', 'FATAL ERROR'],
    

    'time_spent': ['25/8', '24/7/365', 'Unhealthy Amount', 'Too Much', 'Always Online'],
    'nitro_status': ['Begging for Gifted', 'None (Too Broke)', 'Expired', 'Using Fake Nitro'],
    'friend_types': ['All Bots', 'Discord Kittens', 'Fellow Basement Dwellers', 'Alt Accounts'],
    'pfp_types': ['Anime Girl', 'Genshin Character', 'Stolen Art', 'Discord Default'],
    
    'relationship_status': ['Discord Mod', 'Forever Alone', 'Dating Discord Bot', 'Married to Anime'],
    'dating_success': ['404 Not Found', 'Task Failed', 'Loading... (Never)', 'Error: No Data'],
    'red_flags': ['Too Many to Count', 'Infinite', 'Yes', 'All of Them', 'Database Full'],
    'dm_status': ['Left on Read', 'Blocked', 'Message Failed', 'Seen-zoned']
}

@bot.command()
async def stats(ctx, user: discord.Member):
    loading = await ctx.send(f"```Loading stats for {user.name}...```")
    
    stats = f"""STATS FOR {user.name}:
    
Rizz Level: {choice(STAT_RESPONSES['rizz_levels'])}
Bitches: {choice(STAT_RESPONSES['bitches'])}
Grass Touched: {choice(STAT_RESPONSES['grass_status'])}
Discord Karma: {choice(STAT_RESPONSES['karma_levels'])}
Touch Grass Rating: {randint(0, 2)}/10
Cringe Level: {choice(STAT_RESPONSES['cringe_levels'])}
L's Taken: {randint(999, 9999)}+
W's Taken: {randint(-1, 0)}
    
FINAL RATING: {choice(STAT_RESPONSES['final_ratings'])}"""
    
    await asyncio.sleep(2)
    await loading.edit(content=f"```{stats}```")

@bot.command()
async def discordreport(ctx, user: discord.Member):
    loading = await ctx.send(f"```Generating Discord report card for {user.name}...```")
    
    report = f"""DISCORD REPORT CARD FOR {user.name}:

Time Spent: {choice(STAT_RESPONSES['time_spent'])}
Grass Touched: {choice(STAT_RESPONSES['grass_status'])}
Discord Nitro: {choice(STAT_RESPONSES['nitro_status'])}
Server Count: {randint(100, 999)}
DMs: {choice(['Empty', 'All Blocked', 'Only Bots', 'Bot Spam'])}
Friends: {choice(STAT_RESPONSES['friend_types'])}
Profile Picture: {choice(STAT_RESPONSES['pfp_types'])}
Custom Status: {choice(['Cringe', 'Bot Generated', 'Anime Quote', 'Discord Kitten'])}
    
FINAL GRADE: F{'-' * randint(1, 5)}
NOTE: {choice(['Parents Disowned', 'Touch Grass Immediately', 'Seek Help', 'Grass is Green'])}"""
    
    await asyncio.sleep(2)
    await loading.edit(content=f"```{report}```")

@bot.command()
async def relationship(ctx, user: discord.Member):
    loading = await ctx.send(f"```Analyzing {user.name}'s relationship stats...```")
    
    report = f"""RELATIONSHIP REPORT FOR {user.name}:

Relationship Status: {choice(STAT_RESPONSES['relationship_status'])}
Dating Success: {choice(STAT_RESPONSES['dating_success'])}
Rizz Level: {choice(STAT_RESPONSES['rizz_levels'])}
Red Flags: {choice(STAT_RESPONSES['red_flags'])}
DM Success Rate: {choice(STAT_RESPONSES['dm_status'])}
Dating Pool: {choice(['Discord Kittens', 'Discord Mods', 'Body Pillows', 'AI Chatbots'])}
Last Date: {choice(['Never', 'In Dreams', 'With AI', 'Error 404'])}
    
FINAL RATING: {choice(['MAIDENLESS', 'CRITICALLY SINGLE', 'TOUCH GRASS REQUIRED', 'RELATIONSHIP.EXE NOT FOUND'])}
SUGGESTION: {choice(['DELETE DISCORD', 'GRASS NEEDS TOUCHING', 'SEEK THERAPY', 'RESTART LIFE'])}"""
    
    await asyncio.sleep(2)
    await loading.edit(content=f"```{report}```")


@bot.command()
async def dripcheck(ctx, user: discord.Member):
    loading = await ctx.send(f"```Analyzing {user.name}'s drip...```")
    
    UNSPLASH_ACCESS_KEY = "KOKZn5RF1jHrAUyaj3Q5c2FaKFpGCv5iaZhACmFnWLs"
    search_terms = ["bad fashion", "worst outfit", "terrible clothes", "weird clothing"]
    
    try:
        async with aiohttp.ClientSession() as session:
            search_term = random.choice(search_terms)
            url = f"https://api.unsplash.com/photos/random?query={search_term}&client_id={UNSPLASH_ACCESS_KEY}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    image_url = data['urls']['regular']
                    
                    report = f"""DRIP INSPECTION FOR {user.name}:

Drip Level: Sahara Desert
Style Rating: Windows 95
Outfit Score: Walmart Clearance
Swag Meter: Empty
Freshness: Expired
Trend Rating: Internet Explorer
Fashion Sense: Colorblind
    
DRIP STATUS: CRITICALLY DRY
RECOMMENDATION: FACTORY RESET

Actual Fit Reference: 👇"""
                    
                    await loading.edit(content=f"```{report}```")
                    await ctx.send(image_url)
                else:
                    await loading.edit(content=f"```{report}```")
    except Exception as e:
        print(f"Error fetching image: {e}")
        await loading.edit(content=f"```{report}```")

manual_targets = {}
manual_messages = {}

@bot.group(invoke_without_command=True)
async def manual(ctx, user: discord.Member = None):
    if ctx.invoked_subcommand is None:
        if not user:
            await ctx.send("```Please mention a user```")
            return
            
        user_id = str(ctx.author.id)
        if user_id not in manual_messages or not manual_messages[user_id]:
            await ctx.send("```No messages configured. Use .manual add <message> to add messages```")
            return
        
        manual_targets[ctx.author.id] = {
            'user': user,
            'running': True
        }
        
        used_messages = set()
        messages_sent = 0
        
        async def send_message():
            nonlocal used_messages, messages_sent
            
            available_messages = [msg for msg in manual_messages[user_id] if msg not in used_messages]
            if not available_messages:
                used_messages.clear()
                available_messages = manual_messages[user_id]
            
            message = random.choice(available_messages)
            used_messages.add(message)
            
            try:
                full_message = f"{user.mention} {message.replace('{username}', user.display_name)}"
                sent_message = await ctx.send(full_message)
                manual_message_ids.add(sent_message.id)  
                messages_sent += 1
                print(f"Manual message sent ({messages_sent}): {message}")
            except Exception as e:
                print(f"Error sending manual message: {str(e)}")
        
        await ctx.send(f"```Manual mode enabled for {user.name}. Messages will send every 3 seconds.```")
        
        try:
            while ctx.author.id in manual_targets and manual_targets[ctx.author.id]['running']:
                await send_message()
                await asyncio.sleep(3)
        except Exception as e:
            print(f"Manual mode error: {str(e)}")
        finally:
            if ctx.author.id in manual_targets:
                del manual_targets[ctx.author.id]

@manual.command(name="stop")
async def stop_manual(ctx):
    if ctx.author.id in manual_targets:
        manual_targets[ctx.author.id]['running'] = False
        await ctx.send("```Manual mode stopped```")
    else:
        await ctx.send("```Manual mode is not running```")
@manual.command(name="add")
async def add_manual_message(ctx, *, message: str):
    user_id = str(ctx.author.id)
    if user_id not in manual_messages:
        manual_messages[user_id] = []
    
    manual_messages[user_id].append(message)
    await ctx.send(f"```Added message: {message}```")
    save_manual_messages()

@manual.command(name="remove")
async def remove_manual_message(ctx, index: int):
    user_id = str(ctx.author.id)
    if user_id not in manual_messages or not manual_messages[user_id]:
        await ctx.send("```No messages configured```")
        return
        
    if 1 <= index <= len(manual_messages[user_id]):
        removed = manual_messages[user_id].pop(index-1)
        await ctx.send(f"```Removed message: {removed}```")
        save_manual_messages()
    else:
        await ctx.send(f"```Invalid index. Use .manual list to see message indices```")

@manual.command(name="list")
async def list_manual_messages(ctx):
    user_id = str(ctx.author.id)
    if user_id not in manual_messages or not manual_messages[user_id]:
        await ctx.send("```No messages configured```")
        return
        
    message_list = "\n".join(f"{i+1}. {msg}" for i, msg in enumerate(manual_messages[user_id]))
    await ctx.send(f"```Your configured messages:\n\n{message_list}```")

@manual.command(name="clear")
async def clear_manual_messages(ctx):
    user_id = str(ctx.author.id)
    if user_id in manual_messages:
        manual_messages[user_id] = []
        await ctx.send("```Cleared all messages```")
        save_manual_messages()
    else:
        await ctx.send("```No messages configured```")

def save_manual_messages():
    with open(data('manual.json'), 'w') as f:
        json.dump(manual_messages, f)

def load_manual_messages():
    global manual_messages
    try:
        with open(data('manual.json'), 'r') as f:
            manual_messages = json.load(f)
    except FileNotFoundError:
        manual_messages = {}

ladder_msg1 = [
    "nigga i dont fucking know you? ",
    "{mention} disgusting bitch",
    "# YO {UPuser} TAKE THE HEAT OR DIE LMFAO",
    "dont fail the afk checks LMFAO",
    "honestly id bitch both {user1} and {user2}",
    "# {mention} LMFAOOOO",
    "what the fuck is a {user1} or a {user2}",
    "LMFAO WHO THE FUCK IS {UPuser}",
    "NIGGA WE DONT FWU",
    "STUPID FUCKING SLUT",
    "{mention} sadly your dying and your bf {user2} is dogshit",
    "tbf your boyfriend {user2} is dying LMAO",
    "lets outlast ill be here all day dw",
    "this nigga teary eye typin",
    "DO I KNOW YOU? {UPuser}",
    "who is {user2}",
    "we dont rate you"
]

ladder_msg2 = [
    "WHAT THE FUCK WAS THAT LMFAO",
    "nigga ill rip your spine out {mention}",
    "brainless freak",
    "disgusting slut",
    "{user1} {user2} i don fuck with you?",
    "{mention} dont get teary eyed now",
    "who the fuck is {user1} {user2}",
    "nigga sadly your my bitch lets go forever {mention}",
    "{user1} stop tryna chatpack LMFAO",
    "you might aswell just quit {mention}",
    "na thats crazy 😂",
    "we hoeing the shit out of you",
    "ill beat on you lil nigga {mention}",
    "nigga ill cuck your mom and youd enjoy it {mention}",
    "frail digusting BITCH"
]
        
testimony_running = False
testimony_tasks = {}

@bot.command()
async def testimony(ctx, user1: discord.User, user2: discord.User = None):
    global testimony_running
    testimony_running = True
    channel_id = ctx.channel.id
    
    tokens = load_tokens()
    valid_tokens = set(tokens)  
    
    async def send_messages(token, message_list):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        while testimony_running and token in valid_tokens:
            try:
                message = random.choice(message_list)
                formatted_message = (message
                    .replace("{user}", user1.display_name)
                    .replace("{mention}", user1.mention)
                    .replace("{UPuser}", user1.display_name.upper())
                    .replace("{user1}", user1.display_name)
                    .replace("{user2}", user2.display_name if user2 else "")
                )
                
                payload = {'content': formatted_message}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f'https://discord.com/api/v9/channels/{channel_id}/messages',
                        headers=headers,
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            print(f"Message sent successfully with token: {token[-4:]}")
                            await asyncio.sleep(random.uniform(0.5, 1))
                        elif resp.status == 429:
                            retry_after = random.uniform(3, 5)
                            print(f"Rate limited. Waiting {retry_after:.2f}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        elif resp.status == 403:
                            print(f"Token {token[-4:]} is invalid (403). Removing from rotation.")
                            valid_tokens.remove(token)
                            break
                        else:
                            print(f"Error sending message: Status {resp.status}")
                            await asyncio.sleep(random.uniform(3, 5))
                            continue
                
            except Exception as e:
                print(f"Error in testimony task: {str(e)}")
                await asyncio.sleep(random.uniform(3, 5))
                continue
    
    tasks = []
    for i, token in enumerate(tokens):
        message_list = ladder_msg1 if i % 2 == 0 else ladder_msg2
        task = bot.loop.create_task(send_messages(token, message_list))
        tasks.append(task)
    
    testimony_tasks[channel_id] = tasks
    await ctx.send("```Testimony spam started. Use .testimonyoff to stop.```")


@bot.command()
async def testimonyoff(ctx):
    global testimony_running
    channel_id = ctx.channel.id
    
    if channel_id in testimony_tasks:
        testimony_running = False
        for task in testimony_tasks[channel_id]:
            task.cancel()
        testimony_tasks.pop(channel_id)
        await ctx.send("```Testimony spam stopped.```")
    else:
        await ctx.send("```No testimony spam running in this channel.```")

@bot.group(invoke_without_command=True)
async def vcjoin(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    if ctx.invoked_subcommand is None:
        await ctx.send(f"""```ansi
{text_color}Voice Channel Commands:
{accent_color}• {text_color}.vcjoin stable <channel_id> {highlight_color}- Join and stay in one voice channel
{accent_color}• {text_color}.vcjoin rotate {highlight_color}- Rotate through all available voice channels
{accent_color}• {text_color}.vcjoin random {highlight_color}- Randomly join voice channels
{accent_color}• {text_color}.vcjoin list {highlight_color}- List all available voice channels
{accent_color}• {text_color}.vcjoin leave {highlight_color}- Leave voice channel
{accent_color}• {text_color}.vcjoin status {highlight_color}- Show current VC status```""")

@vcjoin.command(name="stable")
async def vc_stable(ctx, channel_id: int = None):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    if not channel_id:
        await ctx.send(f"```ansi\n{text_color}Please provide a voice channel ID```")
        return
        
    try:
        channel = bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send(f"```ansi\n{text_color}Invalid voice channel ID```")
            return
            
        voice_client = ctx.guild.voice_client
        if voice_client:
            await voice_client.move_to(channel)
        else:
            await channel.connect()
            
        await ctx.send(f"```ansi\n{text_color}Connected to {highlight_color}{channel.name}```")
    except Exception as e:
        await ctx.send(f"```ansi\n{accent_color}Error: {text_color}{str(e)}```")

@vcjoin.command(name="list")
async def vc_list(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    voice_channels = [channel for channel in ctx.guild.channels if isinstance(channel, discord.VoiceChannel)]
    if not voice_channels:
        await ctx.send(f"```ansi\n{text_color}No voice channels available```")
        return
        
    channel_list = "\n".join(f"{accent_color}• {text_color}{channel.id}: {highlight_color}{channel.name}" for channel in voice_channels)
    await ctx.send(f"```ansi\n{text_color}Available Voice Channels:\n\n{channel_list}```")

@vcjoin.command(name="status")
async def vc_status(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.channel:
        await ctx.send(f"""```ansi
{text_color}Current Voice Status:
{accent_color}• {text_color}Connected to: {highlight_color}{voice_client.channel.name}
{accent_color}• {text_color}Channel ID: {highlight_color}{voice_client.channel.id}
{accent_color}• {text_color}Latency: {highlight_color}{round(voice_client.latency * 1000, 2)}ms```""")
    else:
        await ctx.send(f"```ansi\n{text_color}Not connected to any voice channel```")

@vcjoin.command(name="leave")
async def vc_leave(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await ctx.send(f"```ansi\n{text_color}Left voice channel```")
    else:
        await ctx.send(f"```ansi\n{text_color}Not in a voice channel```")

@vcjoin.command(name="rotate")
async def vc_rotate(ctx):
    theme = help_cog.user_themes.get(str(ctx.author.id), None)
    if theme:
        text_color = accent_color = highlight_color = globals()[theme]
    else:
        text_color = help_cog.default_colors["text"]
        highlight_color = help_cog.default_colors["highlight"]
        accent_color = help_cog.default_colors["accent"]

    voice_channels = [channel for channel in ctx.guild.channels if isinstance(channel, discord.VoiceChannel)]
    if not voice_channels:
        await ctx.send(f"```ansi\n{text_color}No voice channels available```")
        return
        
    rotate_active = True
    await ctx.send(f"```ansi\n{text_color}Starting voice channel rotation```")
    
    while rotate_active:
        for channel in voice_channels:
            try:
                voice_client = ctx.guild.voice_client
                if voice_client:
                    await voice_client.move_to(channel)
                else:
                    await channel.connect()
                    
                print(f"{text_color}Moved to channel: {highlight_color}{channel.name}")
                await asyncio.sleep(10)
                
                if not rotate_active:
                    break
                    
            except Exception as e:
                print(f"{accent_color}Error rotating to {channel.name}: {e}")
                continue

@bot.command()
async def mdm(ctx, num_friends: int, *, message: str):
    await ctx.message.delete()
    
    async def send_message_to_friend(friend_id, friend_username):
        headers = {
        "authority": "discord.com",
        "method": "PATCH",
        "scheme": "https",
        "accept": "/",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "origin": "https://discord.com/",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Calcutta",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
    }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://discord.com/api/v9/users/@me/channels",
                    headers=headers,
                    json={"recipient_id": friend_id}
                ) as response:
                    if response.status == 403:
                        data = await response.json()
                        if "captcha_key" in data or "captcha_sitekey" in data:
                            print(f"CAPTCHA detected! Stopping mass DM...")
                            return False, "CAPTCHA"
                            
                    if response.status == 200:
                        dm_channel = await response.json()
                        channel_id = dm_channel["id"]
                        
                        async with session.post(
                            f"https://discord.com/api/v9/channels/{channel_id}/messages",
                            headers=headers,
                            json={"content": message}
                        ) as msg_response:
                            if msg_response.status == 403:
                                data = await msg_response.json()
                                if "captcha_key" in data or "captcha_sitekey" in data:
                                    return False, "CAPTCHA"
                                return False, "BLOCKED"
                            elif msg_response.status == 429:
                                return False, "RATELIMIT"
                            elif msg_response.status == 200:
                                return True, "SUCCESS"
                            else:
                                return False, f"ERROR_{msg_response.status}"
                                
            return False, "FAILED"
        except Exception as e:
            return False, f"ERROR: {str(e)}"

    status_msg = await ctx.send("```ansi\nInitializing Mass DM Operation...```")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://discord.com/api/v9/users/@me/relationships",
            headers={"authorization": bot.http.token}
        ) as response:
            if response.status != 200:
                await status_msg.edit(content="```ansi\nFailed to fetch friends list```")
                return
                
            friends = await response.json()
            friends = [f for f in friends if f.get("type") == 1]
            
            if not friends:
                await status_msg.edit(content="```ansi\nNo friends found```")
                return
                
            friends = friends[:num_friends]
            

            stats = {
                "success": 0,
                "blocked": 0,
                "ratelimited": 0,
                "captcha": 0,
                "failed": 0
            }
            
            start_time = time.time()
            
            for index, friend in enumerate(friends, 1):
                friend_id = friend['user']['id']
                friend_username = f"{friend['user']['username']}#{friend['user']['discriminator']}"
                
                success, status = await send_message_to_friend(friend_id, friend_username)
                
                if success:
                    stats["success"] += 1
                elif status == "BLOCKED":
                    stats["blocked"] += 1
                elif status == "RATELIMIT":
                    stats["ratelimited"] += 1
                elif status == "CAPTCHA":
                    stats["captcha"] += 1
                else:
                    stats["failed"] += 1
                
                elapsed_time = time.time() - start_time
                progress = (index / len(friends)) * 100
                msgs_per_min = (index / elapsed_time) * 60 if elapsed_time > 0 else 0
                eta = (elapsed_time / index) * (len(friends) - index) if index > 0 else 0
                
                bar_length = 20
                filled = int(progress / 100 * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                

                status = f"""```ansi
Mass DM Progress
{red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Progress: {green}[{bar}] {progress:.1f}%
Successful: {blue}{stats['success']} Blocked: {blue}{stats['blocked']} Rate Limited: {blue}{stats['ratelimited']}
Captcha: {blue}{stats['captcha']} Failed: {blue}{stats['failed']}

Messages/min: {red}{msgs_per_min:.1f}
Elapsed Time: {red}{int(elapsed_time)}s
ETA: {red}{int(eta)}s

Current: {blue}{friend_username}
Status: {blue}{status}```"""
                
                await status_msg.edit(content=status)
                
                if index % 5 == 0:
                    delay = random.uniform(30.0, 60.0)
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(random.uniform(8.0, 12.0))
            final_time = time.time() - start_time
            final_status = f"""```ansi
Mass DM Complete
{red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Successful: {blue}{stats['success']}
Blocked: {blue}{stats['blocked']}
Rate Limited: {blue}{stats['ratelimited']}
Captcha: {blue}{stats['captcha']}
Failed: {blue}{stats['failed']}

Total Time: {red}{int(final_time)}s
Avg Speed: {red}{(stats['success'] / final_time * 60):.1f} msgs/min```"""
            
            await status_msg.edit(content=final_status)




@bot.group(invoke_without_command=True)
async def autogc(ctx):
    global autogc_enabled
    autogc_enabled = True
    await ctx.send(f"```ansi\n{blue}Auto group chat enabled```")

@autogc.command(name="stop") 
async def autogc_stop(ctx):
    global autogc_enabled
    autogc_enabled = False
    await ctx.send(f"```ansi\n{red}Auto group chat disabled```")

@autogc.command(name="whitelist")
async def autogc_whitelist(ctx, user: discord.User):
    gc_whitelist.add(user.id)
    save_whitelist()
    await ctx.send(f"```ansi\n{green}Added {user.name} to whitelist```")

@autogc.command(name="whitelistr")
async def autogc_whitelist_remove(ctx, user: discord.User):
    if user.id in gc_whitelist:
        gc_whitelist.remove(user.id)
        save_whitelist()
        await ctx.send(f"```Removed {user.name} from whitelist```")
    else:
        await ctx.send("```ansi\nUser not in whitelist```")

@autogc.command(name="list")
async def autogc_list(ctx):
    if not gc_whitelist:
        await ctx.send(f"```ansi\nNo users in whitelist```")
        return
    
    users = []
    for user_id in gc_whitelist:
        try:
            user = await bot.fetch_user(user_id)
            users.append(f"• {user.name}")
        except:
            users.append(f"• Unknown User ({user_id})")
    
    await ctx.send(f"```Whitelisted Users:\n\n{chr(10).join(users)}```")

@bot.group(invoke_without_command=True)
async def autogcleave(ctx):
    if ctx.invoked_subcommand is None:
        global autoleave_enabled
        autoleave_enabled = True
        await ctx.send(f"```ansi\nAuto leave {blue}enabled```")

@autogcleave.command(name="stop")
async def autogcleave_stop(ctx):
    global autoleave_enabled
    autoleave_enabled = False
    await ctx.send(f"```ansi\nAuto leave {red}disabled```")

@autogcleave.command(name="status")
async def autogcleave_status(ctx):
    status = "enabled" if autoleave_enabled else "disabled"
    await ctx.send(f"```ansi\nAuto leave is currently {status}```")

@bot.group(invoke_without_command=True)
async def autoserverleave(ctx):
    if ctx.invoked_subcommand is None:
        global autosleave_enabled
        autosleave_enabled = True
        await ctx.send(f"```ansi\nAuto server leave {blue}enabled```")

@autoserverleave.command(name="stop")
async def autoserverleave_stop(ctx):
    global autosleave_enabled
    autosleave_enabled = False
    await ctx.send(f"```ansi\nAuto server leave {red}disabled```")

@autoserverleave.command(name="status")
async def autoserverleave_status(ctx):
    status = f"{blue}enabled" if autosleave_enabled else f"{red}disabled"
    await ctx.send(f"```ansi\nAuto server leave is currently {status}```")





@bot.event
async def on_guild_remove(guild):
    if not autosleave_enabled:
        return
        
    tokens = load_tokens()
    
    async def leave_with_token(token):
        try:
            user_client = discord.Client(intents=discord.Intents.default())
            
            @user_client.event
            async def on_ready():
                try:
                    guild_obj = user_client.get_guild(guild.id)
                    if guild_obj:
                        await guild_obj.leave()
                        print(f'Token {user_client.user} left server {guild.name}')
                except Exception as e:
                    print(f"Error leaving server with token {token[-4:]}: {e}")
                finally:
                    await user_client.close()

            await user_client.start(token, bot=False)
            
        except Exception as e:
            print(f"Failed to process token {token[-4:]}: {e}")

    tasks = [leave_with_token(token) for token in tokens if token != bot.http.token]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    print(f"Attempted to make tokens leave server {guild.name}")

repeat_tokens = []
repeat_delay = 1.0
repeat_enabled = False
repeat_folder = "repeat"

@bot.group(invoke_without_command=True)
async def repeat(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("""```ansi
Repeat Command Group
repeat start [num_tokens] - Start auto repeat
repeat stop              - Stop auto repeat
repeat delay <seconds>   - Set message delay
repeat status           - Show current status```""")

@repeat.command(name="start")
async def repeat_start(ctx, num_tokens: int = None):
    global repeat_tokens, repeat_enabled
    
    if repeat_enabled:
        await ctx.send("```Auto repeat is already running```")
        return

    if not os.path.exists(repeat_folder):
        os.makedirs(repeat_folder)

    status_msg = await ctx.send("```Verifying tokens...```")
    
    async def verify_token(token):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://discord.com/api/v9/channels/{ctx.channel.id}",
                    headers={"authorization": token}
                ) as resp:
                    if resp.status == 200:
                        return token
        except:
            return None

    all_tokens = load_tokens()
    tasks = [verify_token(token) for token in all_tokens]
    verified_tokens = await asyncio.gather(*tasks)
    working_tokens = [t for t in verified_tokens if t]

    if not working_tokens:
        await status_msg.edit(content="```No working tokens found```")
        return

    if num_tokens and num_tokens < len(working_tokens):
        repeat_tokens = random.sample(working_tokens, num_tokens)
    else:
        repeat_tokens = working_tokens

    with open(f"{repeat_folder}/active_tokens.txt", "w") as f:
        f.write("\n".join(repeat_tokens))

    repeat_enabled = True
    await status_msg.edit(content=f"```Auto repeat enabled with {len(repeat_tokens)} tokens\nDelay: {repeat_delay}s```")

@repeat.command(name="stop")
async def repeat_stop(ctx):
    global repeat_enabled
    if not repeat_enabled:
        await ctx.send("```Auto repeat is not running```")
        return
    
    repeat_enabled = False
    await ctx.send("```Auto repeat disabled```")

@repeat.command(name="delay")
async def repeat_delay_cmd(ctx, delay: float):
    global repeat_delay
    if delay < 0.1:
        await ctx.send("```Delay must be at least 0.1 seconds```")
        return
    
    repeat_delay = delay
    await ctx.send(f"```Repeat delay set to {delay}s```")

@repeat.command(name="status")
async def repeat_status(ctx):
    status = f"""```ansi
Repeat Status
Enabled: {repeat_enabled}
Active Tokens: {len(repeat_tokens)}
Current Delay: {repeat_delay}s```"""
    await ctx.send(status)
import subprocess

@bot.command()
async def host(ctx, token: str):
    try:
        await ctx.message.delete()
        
        current_dir = os.getcwd()
        mel_host_path = os.path.join(current_dir, "mel host")
        config_path = os.path.join(mel_host_path, cfg('settings.json'))
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        config["token"] = token
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
            
        project_b_path = os.path.join(mel_host_path, "main.py")
        

        os.chdir(mel_host_path)
        
        subprocess.Popen(["python", "main.py"], 
                        cwd=mel_host_path,
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
        

        os.chdir(current_dir)
        
        await ctx.send("```Successfully started host with new token```", delete_after=3)
        
    except FileNotFoundError:
        await ctx.send("```Error: Could not find required files```", delete_after=3)
    except json.JSONDecodeError:
        await ctx.send("```Error: Invalid config file format```", delete_after=3)
    except Exception as e:
        await ctx.send(f"```Error: {str(e)}```", delete_after=3)

default_ladder_messages = [
    "I am above you",
    "You're beneath me",
    "Bow down peasant",
    "Keep climbing",
    "Stay down there",
    "Looking down on you",
    "Higher than you'll ever be",
    "Keep trying to reach me"
]

ladder_messages = default_ladder_messages.copy()
ladder_delay = 0.2
ladder_enabled = False
ladder_task = None
ladder_target = None 

def save_ladder_messages():
    with open('ladder_messages.json', 'w') as f:
        json.dump(ladder_messages, f)

def load_ladder_messages():
    global ladder_messages
    try:
        with open('ladder_messages.json', 'r') as f:
            ladder_messages = json.load(f)
    except FileNotFoundError:
        ladder_messages = default_ladder_messages.copy()
        save_ladder_messages()

load_ladder_messages()

@bot.group(invoke_without_command=True)
async def ladder(ctx, user: discord.User = None):
    global ladder_enabled, ladder_task, ladder_target
    
    if ctx.invoked_subcommand is None:
        if ladder_enabled:
            await ctx.send("```Ladder spam is already running```")
            return
            
        ladder_enabled = True
        ladder_target = user  
        
        async def ladder_spam():
            while ladder_enabled:
                try:
                    message = random.choice(ladder_messages)
                    words = message.split()
                    
                    for word in words:
                        if ladder_target and random.random() < 0.2:
                            await ctx.send(f"{word} {ladder_target.mention}")
                        else:
                            await ctx.send(word)
                        await asyncio.sleep(ladder_delay)
                        
                    await asyncio.sleep(2.0)
                except Exception as e:
                    print(f"Error sending ladder message: {e}")
        
        ladder_task = asyncio.create_task(ladder_spam())
        status = f"Ladder spam started"
        if ladder_target:
            status += f" targeting {ladder_target.name}"
        await ctx.send(f"```{status}```")
@ladder.command(name="stop")
async def ladder_stop(ctx):
    global ladder_enabled, ladder_target
    if not ladder_enabled:
        await ctx.send("```Ladder spam is not running```")
        return
        
    ladder_enabled = False
    ladder_target = None
    if ladder_task:
        ladder_task.cancel()
    await ctx.send("```Ladder spam stopped```")

@ladder.command(name="add")
async def ladder_add(ctx, *, message: str):
    if message in ladder_messages:
        await ctx.send("```This message already exists```")
        return
        
    ladder_messages.append(message)
    save_ladder_messages()
    await ctx.send(f"```Added: {message}```")

@ladder.command(name="remove")
async def ladder_remove(ctx, *, message: str):
    if message not in ladder_messages:
        await ctx.send("```Message not found```")
        return
        
    ladder_messages.remove(message)
    save_ladder_messages()
    await ctx.send(f"```Removed: {message}```")

@ladder.command(name="list")
async def ladder_list(ctx):
    messages = "\n".join(f"{i+1}. {msg}" for i, msg in enumerate(ladder_messages))
    await ctx.send(f"```Ladder Messages:\n\n{messages}```")

@ladder.command(name="delay")
async def ladder_delay_cmd(ctx, delay: float):
    global ladder_delay
    if delay < 0.2:
        await ctx.send("```Delay must be at least 0.2 seconds```")
        return
        
    ladder_delay = delay
    await ctx.send(f"```Ladder delay set to {delay}s```")

@ladder.command(name="reset")
async def ladder_reset(ctx):
    global ladder_messages
    ladder_messages = default_ladder_messages.copy()
    save_ladder_messages()
    await ctx.send("```Reset to default ladder messages```")

@ladder.command(name="clear")
async def ladder_clear(ctx):
    global ladder_messages
    ladder_messages.clear()
    save_ladder_messages()
    await ctx.send("```Cleared all ladder messages```")

@ladder.command(name="status")
async def ladder_status(ctx):
    status = f"""```ansi
Ladder Status
Enabled: {ladder_enabled}
Target: {ladder_target.name if ladder_target else "None"}
Messages Count: {len(ladder_messages)}
Current Delay: {ladder_delay}s```"""
    await ctx.send(status)
guild_rotation_task = None
guild_rotation_delay = 2.0  

@bot.group(invoke_without_command=True)
async def rotateguild(ctx, delay: float = 2.0):
    global guild_rotation_task, guild_rotation_delay
    
    if guild_rotation_task and not guild_rotation_task.cancelled():
        await ctx.send("```tag rotation is already running```")
        return
        
    if delay < 1.0:
        await ctx.send("```tag must be at least 1 second```")
        return
        
    guild_rotation_delay = delay
    
    async def rotate_guilds():
        headers = {
            "authority": "canary.discord.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "authorization": bot.http.token,
            "content-type": "application/json",
            "origin": "https://canary.discord.com",
            "referer": "https://canary.discord.com/channels/@me",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
        }
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    valid_guild_ids = []
                    
                    async with session.get(
                        'https://canary.discord.com/api/v9/users/@me/guilds',
                        headers=headers
                    ) as guild_resp:
                        if guild_resp.status != 200:
                            await ctx.send("```Failed to fetch guilds```")
                            return
                        
                        guilds = await guild_resp.json()
                        
                        for guild in guilds:
                            test_payload = {
                                'identity_guild_id': guild['id'],
                                'identity_enabled': True
                            }
                            
                            async with session.put(
                                'https://canary.discord.com/api/v9/users/@me/clan',
                                headers=headers,
                                json=test_payload
                            ) as test_resp:
                                if test_resp.status == 200:
                                    valid_guild_ids.append(guild['id'])
                        
                        if not valid_guild_ids:
                            await ctx.send("```No guilds with valid clan badges found```")
                            return
                            
                        await ctx.send(f"```Found {len(valid_guild_ids)} guilds```")
                        
                        while True:
                            for guild_id in valid_guild_ids:
                                payload = {
                                    'identity_guild_id': guild_id,
                                    'identity_enabled': True
                                }
                                async with session.put(
                                    'https://canary.discord.com/api/v9/users/@me/clan',
                                    headers=headers,
                                    json=payload
                                ) as put_resp:
                                    if put_resp.status == 200:
                                        await asyncio.sleep(guild_rotation_delay)
                            
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error in guild rotation: {e}")
                await asyncio.sleep(5)
    
    guild_rotation_task = asyncio.create_task(rotate_guilds())
    await ctx.send(f"```Started guild rotation (Delay: {delay}s)```")

@rotateguild.command(name="stop")
async def rotateguild_stop(ctx):    
    global guild_rotation_task
    
    if guild_rotation_task and not guild_rotation_task.cancelled():
        guild_rotation_task.cancel()
        guild_rotation_task = None
        await ctx.send("```Stopped clan rotation```")
    else:
        await ctx.send("```Clan rotation is not running```")

@rotateguild.command(name="delay")
async def rotateguild_delay(ctx, delay: float):
    global guild_rotation_delay
    
    if delay < 1.0:
        await ctx.send("```Delay must be at least 1 second```")
        return
        
    guild_rotation_delay = delay
    await ctx.send(f"```Clan rotation delay set to {delay}s```")

@rotateguild.command(name="status")
async def rotateguild_status(ctx):
    status = "running" if (guild_rotation_task and not guild_rotation_task.cancelled()) else "stopped"
    await ctx.send(f"""```
Guild Rotation Status:
• Status: {status}
• Delay: {guild_rotation_delay}s
```""")


try:
    with open('dmsnipe_config.json', 'r') as f:
        dmsnipe_config = json.load(f)
except FileNotFoundError:
    dmsnipe_config = {
        'webhook_url': None,
        'enabled': False,
        'edit_snipe': False,
        'ignored_users': [],
        'ignored_channels': []
    }

def save_dmsnipe_config():
    with open('dmsnipe_config.json', 'w') as f:
        json.dump(dmsnipe_config, f, indent=4)

@bot.group(invoke_without_command=True)
async def dmsnipe(ctx):
    await ctx.send("```run '.help dmsnipe' for more info```")

@dmsnipe.command()
async def log(ctx, webhook_url: str = None):
    if webhook_url is None:
        await ctx.send("```Please add a webhook URL```")
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(webhook_url) as resp:
                if resp.status == 200:
                    dmsnipe_config['webhook_url'] = webhook_url
                    save_dmsnipe_config()
                    await ctx.send("```Webhook set successfully```")
                else:
                    await ctx.send("```Invalid webhook URL```")
    except:
        await ctx.send("```Invalid webhook URL```")

@dmsnipe.command()
async def toggle(ctx, state: str = None):
    if state not in ['on', 'off']:
        await ctx.send("```Please choose 'on' or 'off'```")
        return
    
    dmsnipe_config['enabled'] = state == 'on'
    save_dmsnipe_config()
    await ctx.send(f"```DMSnipe {state}```")

@dmsnipe.command()
async def edit(ctx, state: str = None):
    if state not in ['on', 'off']:
        await ctx.send("```Please choose 'on' or 'off'```")
        return
    
    dmsnipe_config['edit_snipe'] = state == 'on'
    save_dmsnipe_config()
    await ctx.send(f"```Edit sniping {state}```")

@dmsnipe.command()
async def ignore(ctx, target: Union[discord.User, discord.TextChannel] = None):
    if target is None:
        await ctx.send("```Please mention a user or channel to ignore```")
        return
    
    target_id = target.id
    if isinstance(target, discord.User):
        if target_id not in dmsnipe_config['ignored_users']:
            dmsnipe_config['ignored_users'].append(target_id)
            await ctx.send(f"```Now ignoring user: {target.name}```")
        else:
            dmsnipe_config['ignored_users'].remove(target_id)
            await ctx.send(f"```No longer ignoring user: {target.name}```")
    else:
        if target_id not in dmsnipe_config['ignored_channels']:
            dmsnipe_config['ignored_channels'].append(target_id)
            await ctx.send(f"```Now ignoring channel: {target.name}```")
        else:
            dmsnipe_config['ignored_channels'].remove(target_id)
            await ctx.send(f"```No longer ignoring channel: {target.name}```")
    save_dmsnipe_config()

@dmsnipe.command()
async def status(ctx):
    status_msg = f"""```
DMSnipe Status:
Enabled: {dmsnipe_config['enabled']}
Edit Snipe: {dmsnipe_config['edit_snipe']}
Webhook Set: {'Yes' if dmsnipe_config['webhook_url'] else 'No'}
Ignored Users: {len(dmsnipe_config['ignored_users'])}
Ignored Channels: {len(dmsnipe_config['ignored_channels'])}
```"""
    await ctx.send(status_msg)

@dmsnipe.command()
async def clear(ctx):
    dmsnipe_config['ignored_users'] = []
    dmsnipe_config['ignored_channels'] = []
    save_dmsnipe_config()
    await ctx.send("```Cleared all ignore lists```")


import logging


logging.basicConfig(level=logging.INFO)

@bot.event
async def on_message_delete(message):
    if message.guild is not None:
        return
        
    if not dmsnipe_config['enabled'] or not dmsnipe_config['webhook_url']:
        return
        
    if message.author.bot or message.author.id in dmsnipe_config['ignored_users']:
        return
        
    if message.channel.id in dmsnipe_config['ignored_channels']:
        return

    embed = discord.Embed(
        title="Message Deleted",
        description=message.content,
        color=0x2F3136, 
        timestamp=datetime.utcnow()
    )
    
    channel_type = "Group DM" if isinstance(message.channel, discord.GroupChannel) else "DM"
    
    embed.description = f"""**Content:**
{message.content}

**Author:** {message.author} ({message.author.id})
**Channel Type:** {channel_type}
**Channel:** {message.channel} ({message.channel.id})"""

    try:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(dmsnipe_config['webhook_url'], session=session)
            await webhook.send(embed=embed)
        logging.info(f"Webhook sent successfully for message delete in {channel_type}")
    except Exception as e:
        logging.error(f"Failed to send webhook for message delete: {e}")

@bot.event
async def on_message_edit(before, after):
    if before.guild is not None:
        return
        
    if not dmsnipe_config['enabled'] or not dmsnipe_config['edit_snipe'] or not dmsnipe_config['webhook_url']:
        return
        
    if before.author.bot or before.author.id in dmsnipe_config['ignored_users']:
        return
        
    if before.channel.id in dmsnipe_config['ignored_channels']:
        return
        
    if before.content == after.content:
        return

    channel_type = "Group DM" if isinstance(before.channel, discord.GroupChannel) else "DM"

    embed = discord.Embed(
        title="Message Edited",
        color=0x2F3136,  
        timestamp=datetime.utcnow()
    )
    
    embed.description = f"""**Before:**
{before.content}

**After:**
{after.content}

**Author:** {before.author} ({before.author.id})
**Channel Type:** {channel_type}
**Channel:** {before.channel} ({before.channel.id})"""

    try:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(dmsnipe_config['webhook_url'], session=session)
            await webhook.send(embed=embed)
        logging.info(f"Webhook sent successfully for message edit in {channel_type}")
    except Exception as e:
        logging.error(f"Failed to send webhook for message edit: {e}")

anti_last_words = [
    "LAST WORD FOR",
    "LAST",
    "last word for",
    "Lasts for",
    "L A S T ",
    "L @ S T ",
    "LAASTT",
    "LASSTT",
    "LASTS",
    "LAST WORDED"
]

antilast_enabled = False

antilast_data = {
    "whitelisted_users": set(),
    "whitelisted_channels": set(),
    "webhook_url": None
}

def save_antilast_data():
    with open(cfg('antilast.json'), 'w') as f:
        json.dump({
            "whitelisted_users": list(antilast_data["whitelisted_users"]),
            "whitelisted_channels": list(antilast_data["whitelisted_channels"]),
            "webhook_url": antilast_data["webhook_url"],
            "enabled": antilast_enabled
        }, f, indent=4)

def load_antilast_data():
    global antilast_enabled
    try:
        with open(cfg('antilast.json'), 'r') as f:
            data = json.load(f)
            antilast_data["whitelisted_users"] = set(data.get("whitelisted_users", []))
            antilast_data["whitelisted_channels"] = set(data.get("whitelisted_channels", []))
            antilast_data["webhook_url"] = data.get("webhook_url")
            antilast_enabled = data.get("enabled", False)
    except (FileNotFoundError, json.JSONDecodeError):

        antilast_data["whitelisted_users"] = set()
        antilast_data["whitelisted_channels"] = set()
        antilast_data["webhook_url"] = None
        antilast_enabled = False
        save_antilast_data()


@bot.group(invoke_without_command=True)
async def antilast(ctx):
    await ctx.send("```run '.help antilast' for more info```")

@antilast.command()
async def toggle(ctx, state: str = None):
    global antilast_enabled
    if state not in ['on', 'off']:
        await ctx.send("```Please choose 'on' or 'off'```")
        return
        
    antilast_enabled = state == 'on'
    save_antilast_data()
    await ctx.send(f"```Anti last word {state}```")

@antilast.command()
async def whitelist(ctx, user_id: str):
    antilast_data["whitelisted_users"].add(user_id)
    save_antilast_data()
    await ctx.send(f"```Added user {user_id} to whitelist```")

@antilast.command()
async def channel(ctx, channel_id: str):
    antilast_data["whitelisted_channels"].add(channel_id)
    save_antilast_data()
    await ctx.send(f"```Added channel {channel_id} to whitelist```")

@antilast.command()
async def webhook(ctx, webhook_url: str):
    antilast_data["webhook_url"] = webhook_url
    save_antilast_data()
    await ctx.send("```Updated webhook URL```")

@antilast.command()
async def config(ctx):
    config = f"""```
Antilast Configuration:
Whitelisted Users: {', '.join(antilast_data["whitelisted_users"]) or 'None'}
Whitelisted Channels: {', '.join(antilast_data["whitelisted_channels"]) or 'None'}
Webhook: {'Set' if antilast_data["webhook_url"] else 'Not Set'}```"""
    await ctx.send(config)

load_antilast_data()



laz_wordlist = [
    "# {mention}\n # you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck you fucking suck ",
    "# {mention}\n # I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO I WOULD LOVE TO BEHEAD YOU AGAIN LMFAO ",
    "# {mention}\n # DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED DONT BREAK NOW WE JUST STARTED ",
    "# {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser {name1} idk you fucking loser  ",
    "# {name1} your my fucking bitch {name1} your my fucking bitchyour my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch your my fucking bitch ",
    "# {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard {name2} your a nobody retard ",
    "# {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr {name2} your my weakest jr ",
    "# {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you {name2} i dont fucking know you "
]

laz_tasks = {}
laz_running = {}

async def send_laz_with_token(token, message_index, ctx, user, name1, name2):
    try:
        if message_index >= len(laz_wordlist):
            message_index = 0
            
        message = laz_wordlist[message_index]
        message = message.replace("{mention}", user.mention)
        message = message.replace("{name1}", name1)
        if name2:
            message = message.replace("{name2}", name2)
        else:
            if "{name2}" in message:
                return message_index, None
                
        headers = {"authorization": token}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://discord.com/api/v9/channels/{ctx.channel.id}/messages",
                headers=headers,
                json={"content": message}
            ) as response:
                if response.status == 403:
                    print(f'[ERROR] Token {token[-4:]} is forbidden')
                    return message_index, "forbidden"
                elif response.status == 200:
                    return message_index + 1, "success"
                return message_index, "retry"
                    
    except Exception as e:
        return message_index, "retry"

@bot.command()
async def laz(ctx, user: discord.User, name1: str, name2: str = None):
    await ctx.message.delete()
    
    if ctx.channel.id in laz_running and laz_running[ctx.channel.id]:
        await ctx.send("```Laz command already running in this channel```")
        return
        
    laz_running[ctx.channel.id] = True
    channel_id = ctx.channel.id
    valid_tokens = set(load_tokens())
    valid_tokens.add(bot.http.token)
    
    async def send_laz_messages(token):
        message_index = 0
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        while laz_running.get(channel_id, False) and token in valid_tokens:
            try:
                if message_index >= len(laz_wordlist):
                    message_index = 0
                    
                message = laz_wordlist[message_index]
                formatted_message = (message
                    .replace("{mention}", user.mention)
                    .replace("{name1}", name1)
                    .replace("{name2}", name2 if name2 else "")
                )
                
                payload = {'content': formatted_message}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f'https://discord.com/api/v9/channels/{channel_id}/messages',
                        headers=headers,
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            print(f"Message sent successfully with token: {token[-4:]}")
                            message_index += 1
                            await asyncio.sleep(random.uniform(0.225, 0.555))
                        elif resp.status == 429:
                            retry_after = random.uniform(3, 5)
                            print(f"Rate limited. Waiting {retry_after:.2f}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        elif resp.status == 403:
                            print(f"Token {token[-4:]} is invalid (403). Removing from rotation.")
                            valid_tokens.remove(token)
                            break
                        else:
                            print(f"Error sending message: Status {resp.status}")
                            await asyncio.sleep(random.uniform(3, 5))
                            continue
                            
            except Exception as e:
                print(f"Error in laz task: {str(e)}")
                await asyncio.sleep(random.uniform(3, 5))
                continue
    
    tasks = []
    for token in valid_tokens:
        task = bot.loop.create_task(send_laz_messages(token))
        tasks.append(task)
    
    laz_tasks[channel_id] = tasks
    await ctx.send("```Laz spam started. Use .endlaz to stop.```")

@bot.command()
async def endlaz(ctx):
    channel_id = ctx.channel.id
    
    if channel_id not in laz_running or not laz_running[channel_id]:
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send("```No laz command running in this channel```")
        return
    
    laz_running[channel_id] = False
    
    if channel_id in laz_tasks:
        for task in laz_tasks[channel_id]:
            task.cancel()
        del laz_tasks[channel_id]
    
    try:
        await ctx.message.delete()
    except:
        pass
        
    try:
        await ctx.send("```Stopped laz command```")
    except:
        pass

async def send_laz_with_token(token, message_index, ctx, user, name1, name2):
    try:

        if message_index >= len(laz_wordlist):
            message_index = 0
            
        message = laz_wordlist[message_index]
        message = message.replace("{mention}", user.mention)
        message = message.replace("{name1}", name1)
        if name2:
            message = message.replace("{name2}", name2)
        else:
            if "{name2}" in message:
                return message_index, None
                
        headers = {
            "authorization": token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://discord.com/api/v9/channels/{ctx.channel.id}/messages",
                headers=headers,
                json={"content": message}
            ) as response:
                if response.status == 403:
                    print(f'Token {token[-4:]} is forbidden')
                    return message_index, "forbidden"
                elif response.status == 429:
                    data = await response.json()
                    retry_after = data.get('retry_after', 5)
                    print(f'Token {token[-4:]} rate limited, retry in {retry_after:.2f}s')
                    return message_index, retry_after
                elif response.status == 200:
                    print(f'Token {token[-4:]} sent message: {message[:30]}...')
                    return message_index + 1, "success"
                else:
                    print(f'Token {token[-4:]} failed with status {response.status}')
                    return message_index, "error"
                    
    except Exception as e:
        print(f'[ERROR] Token {token[-4:]} error: {str(e)}')
        return message_index, "error"

@bot.command()
async def hypesquad(ctx, house: str):
    house_ids = {
        "bravery": 1,
        "brilliance": 2,
        "balance": 3
    }

    headers = {
        "Authorization": bot.http.token, 
        "Content-Type": "application/json"
    }

    if house.lower() == "off":
        url = "https://discord.com/api/v9/hypesquad/online"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status == 204:
                    await ctx.send("```HypeSquad house removed.```")
                else:
                    error_message = await response.text()
                    await ctx.send(f"```Failed to remove HypeSquad house: {response.status} - {error_message}```")
        return

    house_id = house_ids.get(house.lower())
    if house_id is None:
        await ctx.send("```Invalid house. Choose from 'bravery', 'brilliance', 'balance', or 'off'.```")
        return

    payload = {"house_id": house_id}
    url = "https://discord.com/api/v9/hypesquad/online"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 204:
                await ctx.send(f"```HypeSquad house changed to {house.capitalize()}.```")
            else:
                error_message = await response.text()
                await ctx.send(f"```Failed to change HypeSquad house: {response.status} - {error_message}```")


@bot.command()
async def setspfp(ctx, url: str):
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6Ik1hYyBPUyBYIiwiYnJvd3NlciI6IlNhZmFyaSIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzYwNS4xLjE1IChLSFRNTCwgbGlrZSBHZWNrbykgVmVyc2lvbi8xNi41IFNhZmFyaS82MDUuMS4xNSIsImJyb3dzZXJfdmVyc2lvbiI6IjE2LjUiLCJvc192ZXJzaW9uIjoiMTAuMTUuNyIsInJlZmVycmVyIjoiIiwicmVmZXJyaW5nX2RvbWFpbiI6IiIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNTA2ODQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                image_b64 = base64.b64encode(image_data).decode()
                
                content_type = response.headers.get('Content-Type', '')
                if 'gif' in content_type:
                    image_format = 'gif'
                else:
                    image_format = 'png'

                payload = {
                    "avatar": f"data:image/{image_format};base64,{image_b64}"
                }

                response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", json=payload, headers=headers)
                
                if response.status_code == 200:
                    await ctx.send("```Successfully set server profile picture```")
                else:
                    await ctx.send(f"```Failed to update server profile picture: {response.status_code}```")
            else:
                await ctx.send("```Failed to download image from URL```")

@bot.command()
async def setsbanner(ctx, url: str):
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                image_b64 = base64.b64encode(image_data).decode()
                
                content_type = response.headers.get('Content-Type', '')
                if 'gif' in content_type:
                    image_format = 'gif'
                else:
                    image_format = 'png'

                payload = {
                    "banner": f"data:image/{image_format};base64,{image_b64}"
                }

                response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", json=payload, headers=headers)
                
                if response.status_code == 200:
                    await ctx.send("```Successfully set server banner```")
                else:
                    await ctx.send(f"```Failed to update server banner: {response.status_code}```")
            else:
                await ctx.send("```Failed to download image from URL```")

@bot.command()
async def setsbio(ctx, *, bio: str):
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me"
    }

    payload = {
        "bio": bio
    }

    response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", json=payload, headers=headers)
    
    if response.status_code == 200:
        await ctx.send("```Successfully set server bio```")
    else:
        await ctx.send(f"```Failed to update server bio: {response.status_code}```")

@bot.command()
async def setspronoun(ctx, *, pronouns: str):
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me"
    }

    payload = {
        "pronouns": pronouns
    }

    response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", json=payload, headers=headers)
    
    if response.status_code == 200:
        await ctx.send("```Successfully set server pronouns```")
    else:
        await ctx.send(f"```Failed to update server pronouns: {response.status_code}```")

server_rotation_tasks = {
    'pfp': None,
    'banner': None,
    'bio': None,
    'pronouns': None
}

server_rotation_data = {
    'pfp': [],
    'banner': [],
    'bio': [],
    'pronouns': []
}

server_rotation_delays = {
    'pfp': 10,
    'banner': 10,
    'bio': 10,
    'pronouns': 10
}

async def rotate_server_pfp(ctx, urls):
    while True:
        for url in urls:
            try:
                headers = {
                    "authorization": bot.http.token,
                    "content-type": "application/json"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            image_b64 = base64.b64encode(image_data).decode()
                            
                            content_type = response.headers.get('Content-Type', '')
                            image_format = 'gif' if 'gif' in content_type else 'png'

                            payload = {
                                "avatar": f"data:image/{image_format};base64,{image_b64}"
                            }

                            response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", 
                                                json=payload, headers=headers)
                            
                            if response.status_code != 200:
                                print(f"Failed to update server pfp: {response.status_code}")
                                
            except Exception as e:
                print(f"Error in server pfp rotation: {str(e)}")
                
            await asyncio.sleep(server_rotation_delays['pfp'])

async def rotate_server_banner(ctx, urls):
    while True:
        for url in urls:
            try:
                headers = {
                    "authorization": bot.http.token,
                    "content-type": "application/json"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            image_b64 = base64.b64encode(image_data).decode()
                            
                            content_type = response.headers.get('Content-Type', '')
                            image_format = 'gif' if 'gif' in content_type else 'png'

                            payload = {
                                "banner": f"data:image/{image_format};base64,{image_b64}"
                            }

                            response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", 
                                                json=payload, headers=headers)
                            
                            if response.status_code != 200:
                                print(f"Failed to update server banner: {response.status_code}")
                                
            except Exception as e:
                print(f"Error in server banner rotation: {str(e)}")
                
            await asyncio.sleep(server_rotation_delays['banner'])

async def rotate_server_bio(ctx, bios):
    while True:
        for bio in bios:
            try:
                headers = {
                    "authorization": bot.http.token,
                    "content-type": "application/json"
                }
                
                payload = {"bio": bio}
                response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", 
                                    json=payload, headers=headers)
                
                if response.status_code != 200:
                    print(f"Failed to update server bio: {response.status_code}")
                    
            except Exception as e:
                print(f"Error in server bio rotation: {str(e)}")
                
            await asyncio.sleep(server_rotation_delays['bio'])

async def rotate_server_pronouns(ctx, pronouns_list):
    while True:
        for pronouns in pronouns_list:
            try:
                headers = {
                    "authorization": bot.http.token,
                    "content-type": "application/json"
                }
                
                payload = {"pronouns": pronouns}
                response = sesh.patch(f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/@me", 
                                    json=payload, headers=headers)
                
                if response.status_code != 200:
                    print(f"Failed to update server pronouns: {response.status_code}")
                    
            except Exception as e:
                print(f"Error in server pronouns rotation: {str(e)}")
                
            await asyncio.sleep(server_rotation_delays['pronouns'])

@bot.group(invoke_without_command=True)
async def rotateserver(ctx):
    await ctx.send("```Available commands: pfp, banner, bio, pronouns, delay, stop, status```")

@rotateserver.command()
async def pfp(ctx, *urls):
    if not urls:
        await ctx.send("```Please provide at least one URL```")
        return
        
    if server_rotation_tasks['pfp']:
        server_rotation_tasks['pfp'].cancel()
    
    server_rotation_data['pfp'] = list(urls)
    server_rotation_tasks['pfp'] = bot.loop.create_task(rotate_server_pfp(ctx, list(urls)))
    await ctx.send("```Server PFP rotation started```")

@rotateserver.command()
async def banner(ctx, *urls):
    if not urls:
        await ctx.send("```Please provide at least one URL```")
        return
        
    if server_rotation_tasks['banner']:
        server_rotation_tasks['banner'].cancel()
    
    server_rotation_data['banner'] = list(urls)
    server_rotation_tasks['banner'] = bot.loop.create_task(rotate_server_banner(ctx, list(urls)))
    await ctx.send("```Server banner rotation started```")

@rotateserver.command()
async def bio(ctx, *bios):
    if not bios:
        await ctx.send("```Please provide at least one bio```")
        return
        
    if server_rotation_tasks['bio']:
        server_rotation_tasks['bio'].cancel()
    
    server_rotation_data['bio'] = list(bios)
    server_rotation_tasks['bio'] = bot.loop.create_task(rotate_server_bio(ctx, list(bios)))
    await ctx.send("```Server bio rotation started```")

@rotateserver.command()
async def pronouns(ctx, *pronouns_list):
    if not pronouns_list:
        await ctx.send("```Please provide at least one set of pronouns```")
        return
        
    if server_rotation_tasks['pronouns']:
        server_rotation_tasks['pronouns'].cancel()
    
    server_rotation_data['pronouns'] = list(pronouns_list)
    server_rotation_tasks['pronouns'] = bot.loop.create_task(rotate_server_pronouns(ctx, list(pronouns_list)))
    await ctx.send("```Server pronouns rotation started```")

@rotateserver.command()
async def delay(ctx, feature: str, seconds: int):
    if feature not in server_rotation_delays:
        await ctx.send("```Invalid feature. Choose from: pfp, banner, bio, pronouns```")
        return
        
    server_rotation_delays[feature] = seconds
    await ctx.send(f"```Delay for server {feature} rotation set to {seconds} seconds```")

@rotateserver.command()
async def stop(ctx, feature: str = None):
    if feature:
        if feature not in server_rotation_tasks:
            await ctx.send("```Invalid feature. Choose from: pfp, banner, bio, pronouns```")
            return
            
        if server_rotation_tasks[feature]:
            server_rotation_tasks[feature].cancel()
            server_rotation_tasks[feature] = None
            await ctx.send(f"```Server {feature} rotation stopped```")
        else:
            await ctx.send(f"```Server {feature} rotation is not running```")
    else:
        for task_name, task in server_rotation_tasks.items():
            if task:
                task.cancel()
                server_rotation_tasks[task_name] = None
        await ctx.send("```All server rotations stopped```")

@rotateserver.command()
async def status(ctx):
    status_msg = "```\nServer Rotation Status:\n"
    for feature in server_rotation_tasks:
        status_msg += f"{feature}: {'Running' if server_rotation_tasks[feature] else 'Stopped'}"
        status_msg += f" (Delay: {server_rotation_delays[feature]}s)\n"
    status_msg += "```"
    await ctx.send(status_msg)


from itertools import islice

async def dump_files(ctx, folder_path, file_type):
    if not os.path.exists(folder_path):
        await ctx.send(f"```Folder not found: {folder_path}```")
        return

    if isinstance(file_type, str):
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(file_type)]
    else:  
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(file_type)]
    
    if not files:
        await ctx.send(f"```No {file_type} files found in the specified folder```")
        return

    process_msgs = []
    current_index = 0

    while current_index < len(files):
        batch = list(islice(files, current_index, current_index + 10))
        
        file_list = []
        for file in batch:
            file_path = os.path.join(folder_path, file)
            try:
                file_list.append(discord.File(file_path))
            except Exception as e:
                process_msg = await ctx.send(f"```Failed to prepare {file}: {str(e)}```")
                process_msgs.append(process_msg)
                continue
        try:
            await ctx.send(files=file_list)
        except Exception as e:
            process_msg = await ctx.send(f"```Failed to send batch: {str(e)}```")
            process_msgs.append(process_msg)

        current_index += 10

        if current_index < len(files):
            continue_msg = await ctx.send(f"```{current_index}/{len(files)} files sent. Type 'yes' to continue...```")
            process_msgs.append(continue_msg)

            try:
                response = await bot.wait_for(
                    'message',
                    timeout=30.0,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                process_msgs.append(response)

                if response.content.lower() != 'yes':
                    break
            except asyncio.TimeoutError:
                timeout_msg = await ctx.send("```Timed out. Dump cancelled.```")
                process_msgs.append(timeout_msg)
                break

    for msg in process_msgs:
        try:
            await msg.delete()
        except:
            pass

    completion_msg = await ctx.send(f"```Dump completed. Sent {min(current_index, len(files))}/{len(files)} files.```")
    await asyncio.sleep(5)
    await completion_msg.delete()

@bot.command()
async def imgdump(ctx):
    ask_msg = await ctx.send("```Please provide the folder path:```")
    try:
        response = await bot.wait_for(
            'message',
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        folder_path = response.content
        await ask_msg.delete()
        await response.delete()
        await dump_files(ctx, folder_path, ('.png', '.jpg', '.jpeg', '.webp'))
    except asyncio.TimeoutError:
        await ask_msg.edit(content="```Timed out. Please try again.```")
        await asyncio.sleep(5)
        await ask_msg.delete()

@bot.command()
async def gifdump(ctx):
    ask_msg = await ctx.send("```Please provide the folder path:```")
    try:
        response = await bot.wait_for(
            'message',
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        folder_path = response.content
        await ask_msg.delete()
        await response.delete()
        await dump_files(ctx, folder_path, '.gif')
    except asyncio.TimeoutError:
        await ask_msg.edit(content="```Timed out. Please try again.```")
        await asyncio.sleep(5)
        await ask_msg.delete()

@bot.command()
async def mp4dump(ctx):
    ask_msg = await ctx.send("```Please provide the folder path:```")
    try:
        response = await bot.wait_for(
            'message',
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        folder_path = response.content
        await ask_msg.delete()
        await response.delete()
        await dump_files(ctx, folder_path, '.mp4')
    except asyncio.TimeoutError:
        await ask_msg.edit(content="```Timed out. Please try again.```")
        await asyncio.sleep(5)
        await ask_msg.delete()

@bot.command()
async def movdump(ctx):
    ask_msg = await ctx.send("```Please provide the folder path:```")
    try:
        response = await bot.wait_for(
            'message',
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        folder_path = response.content
        await ask_msg.delete()
        await response.delete()
        await dump_files(ctx, folder_path, '.mov')
    except asyncio.TimeoutError:
        await ask_msg.edit(content="```Timed out. Please try again.```")
        await asyncio.sleep(5)
        await ask_msg.delete()


@bot.command()
async def jpgdump(ctx):
    ask_msg = await ctx.send("```Please provide the folder path:```")
    try:
        response = await bot.wait_for(
            'message',
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        folder_path = response.content
        await ask_msg.delete()
        await response.delete()
        await dump_files(ctx, folder_path, ('.jpg', '.jpeg'))
    except asyncio.TimeoutError:
        await ask_msg.edit(content="```Timed out. Please try again.```")
        await asyncio.sleep(5)
        await ask_msg.delete()

@bot.command()
async def pngdump(ctx):
    ask_msg = await ctx.send("```Please provide the folder path:```")
    try:
        response = await bot.wait_for(
            'message',
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        folder_path = response.content
        await ask_msg.delete()
        await response.delete()
        await dump_files(ctx, folder_path, '.png')
    except asyncio.TimeoutError:
        await ask_msg.edit(content="```Timed out. Please try again.```")
        await asyncio.sleep(5)
        await ask_msg.delete()

@bot.command()
async def txtdump(ctx):
    ask_msg = await ctx.send("```Please provide the folder path:```")
    try:
        response = await bot.wait_for(
            'message',
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        folder_path = response.content
        await ask_msg.delete()
        await response.delete()
        await dump_files(ctx, folder_path, '.txt')
    except asyncio.TimeoutError:
        await ask_msg.edit(content="```Timed out. Please try again.```")
        await asyncio.sleep(5)
        await ask_msg.delete()


def _register_help_page_commands():
    for page_num in range(1, MENU_PAGE_COUNT + 1):
        async def handler(ctx, page=page_num):
            cog = bot.get_cog("HelpCog")
            if cog is None:
                await ctx.send("```Help indisponible```", delete_after=5)
                return
            await cog.send_menu_page(ctx, page)

        handler.__name__ = f"help_page_{page_num}"
        bot.command(name=f"p{page_num}")(handler)

_register_help_page_commands()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"```Usage: .{ctx.command.name} — missing {error.param.name}```", delete_after=8)
        return
    if isinstance(error, commands.UserInputError):
        await ctx.send(f"```{error}```", delete_after=8)
        return
    if isinstance(error, commands.CommandInvokeError):
        err = error.original
        safe_print(f"Command error ({ctx.command}): {err}")
        await ctx.send(f"```Error: {err}```", delete_after=12)
        return
    safe_print(f"Command error ({ctx.command}): {error}")
    try:
        await ctx.send(f"```Error: {type(error).__name__}```", delete_after=8)
    except Exception:
        pass


@bot.event
async def on_message(message):
    help_cog_instance = bot.get_cog("HelpCog")
    if help_cog_instance and help_cog_instance.should_skip_page_command(message):
        pass
    else:
        await bot.process_commands(message)
    
    if message.author.bot:
        return
    if message.author.id in dreact_users:
        emoji_data = dreact_users[message.author.id]
        emojis, current_index = emoji_data[0], emoji_data[1]
        try:
            await message.add_reaction(emojis[current_index])
            dreact_users[message.author.id][1] = (current_index + 1) % len(emojis)
        except Exception as e:
            print(f"Error adding dreact reaction: {str(e)}")

    if message.author.id in autoreact_users:
        emoji = autoreact_users[message.author.id]
        try:
            await message.add_reaction(emoji)
        except Exception as e:
            print(f"Error adding autoreact reaction: {str(e)}")

    if force_delete_users.get(message.author.id, False):
        try:
            await message.delete()
            print(f"Message from {message.author.display_name} deleted due to force delete setting.")
        except discord.errors.Forbidden:
            print("Bot does not have permission to delete messages.")

    if repeat_enabled and message.author.id == bot.user.id and not message.content.startswith('.repeat'):
        try:
            for token in repeat_tokens:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"https://discord.com/api/v9/channels/{message.channel.id}/messages",
                        headers={"authorization": token},
                        json={"content": message.content}
                    ) as resp:
                        if resp.status == 429:
                            retry_after = (await resp.json()).get('retry_after', 1)
                            await asyncio.sleep(retry_after)
                        elif resp.status not in (200, 204):
                            print(f"Error sending message with token {token[:20]}...")
                await asyncio.sleep(repeat_delay)
        except Exception as e:
            print(f"Error in auto repeat: {str(e)}")

    if message.content.startswith(f"{message.author.mention}"):
        manual_message_ids.add(message.id)
        
    if message.author.id in manual_targets and message.author == bot.user and message.id not in manual_message_ids:
        try:
            user = manual_targets[message.author.id]['user']
            user_id = str(message.author.id)
            if user_id in manual_messages and manual_messages[user_id]:
                original_content = message.content
                if any(msg in original_content for msg in manual_messages[user_id]):
                    message_content = random.choice(manual_messages[user_id])
                    full_message = f"{user.mention} {message_content.replace('{username}', user.display_name)}"
                else:
                    full_message = f"{user.mention} {original_content}"
                await message.edit(content=full_message)
        except Exception as e:
            print(f"Error editing manual message: {str(e)}")

    if message.author.id in popout_status:
        if message.content.lower() == f"ohaii <@{popout_status[message.author.id]['target'].id}>" or message.content.lower() == "ohaii":
            popout_status[message.author.id]['running'] = False  
            return

    if message.channel.id in autopin_channels and message.author.id == bot.user.id:
        try:
            await asyncio.sleep(0.5)
            await message.pin()
        except discord.Forbidden:
            print(f"Lost pin permissions in channel {message.channel.id}")
            autopin_channels.remove(message.channel.id)
        except discord.HTTPException as e:
            if e.code == 30003:
                pins = await message.channel.pins()
                if pins:
                    await pins[-1].unpin()
                    await message.pin()
            else:
                print(f"Error pinning message: {e}")

    if bot.user in message.mentions:
        if reactions_enabled:
            try:
                await message.add_reaction(custom_reaction)
            except Exception as e:
                await message.channel.send(f"```Failed to add reaction: {str(e)}```")

        if insults_enabled and autoinsults:
            insult = random.choice(autoinsults)
            await message.channel.send(insult)

        response = ping_responses.get(message.channel.id)
        if response:
            await message.channel.send(response)

    if message.author.id in webhookcopy_status and webhookcopy_status[message.author.id]:
        webhook_url = webhook_urls.get(message.author.id)
        if webhook_url:
            webhook_id = webhook_url.split('/')[-2]
            webhook_token = webhook_url.split('/')[-1]
            webhook_info = await bot.fetch_webhook(webhook_id)
            if message.channel.id == webhook_info.channel_id:
                data = {
                    "content": message.content,
                    "username": message.author.display_name,
                    "avatar_url": str(message.author.avatar_url) if message.author.avatar else str(message.author.default_avatar_url)
                }
                await message.delete()
                response = requests.post(webhook_url, json=data)
                if response.status_code == 204:
                    print("Message sent via webhook successfully.")
                else:
                    print(f"Failed to send message via webhook: {response.content.decode()}")

    if mimic_user is not None and mimic_user.id == message.author.id:
        content_to_send = message.content
        forbidden_pattern = r'\b(0|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\b'
        if content_to_send.strip() and not re.search(forbidden_pattern, content_to_send, re.IGNORECASE):
            try:
                await message.channel.send((chr(173) + content_to_send))
                print(f"Mimicked message: {content_to_send}")
            except discord.Forbidden:
                print("Insufficient permissions to send messages in this channel.")
            except Exception as e:
                print(f"Error sending message: {e}")

    if message.author == bot.user and translate_settings.get("active"):
        try:
            translated = translator.translate(
                message.content, src="en", dest=translate_settings["language"]
            ).text
            await message.edit(content=f"{translated}")
        except Exception as e:
            print(f"Translation failed: {e}")

    if message.author.id == bot.user.id and not message.content.startswith('.'):
        try:
            content = message.content
            should_edit = False

            if bold_mode and not (content.startswith('#') and content.endswith('#')):
                content = f"# {content}"
                should_edit = True

            if cord_mode and cord_user:
                content = f"{content} {cord_user.mention}"
                should_edit = True

            if should_edit:
                await message.edit(content=content)

        except Exception as e:
            print(f"Failed to edit message: {e}")

    if not antilast_enabled:
        return

    if message.guild is not None:
        return

    if message.author == bot.user:
        return

    if (str(message.author.id) in antilast_data["whitelisted_users"] or 
        str(message.channel.id) in antilast_data["whitelisted_channels"]):
        return
    
    if isinstance(message.channel, discord.DMChannel):
        if any(word.lower() in message.content.lower() for word in anti_last_words):
            try:
                await message.channel.send("LMFAOO LAST WORD FOR SOCIAL")
                
                headers = {
                    "Authorization": bot.http.token,
                    "Content-Type": "application/json"
                }
                async with aiohttp.ClientSession() as session:
                    await session.put(
                        f"https://discord.com/api/v9/users/@me/relationships/{message.author.id}",
                        headers=headers,
                        json={"type": 2}
                    )
                
                    if antilast_data["webhook_url"]:
                        webhook = discord.Webhook.from_url(antilast_data["webhook_url"], session=session)
                        embed = discord.Embed(
                            title="This loser tried to last word you LMFAO",
                            description=f"fucking loser nice try",
                            color=discord.Color.red()
                        )
                        embed.add_field(name="User", value=f"{message.author} ({message.author.id})")
                        embed.add_field(name="Content", value=message.content)
                        await webhook.send(embed=embed)
            except Exception as e:
                print(f"Error in antilast DM handling: {str(e)}")

    elif isinstance(message.channel, discord.GroupChannel):
        if any(word.lower() in message.content.lower() for word in anti_last_words):
            try:
                await message.channel.send("LMFAOO LAST FOR SOCIAL")
                await message.channel.leave()
                
                if antilast_data["webhook_url"]:
                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(antilast_data["webhook_url"], session=session)
                        embed = discord.Embed(
                            title="Anti Last Word Triggered",
                            description=f"User tried to last word in group chat",
                            color=discord.Color.red()
                        )
                        embed.add_field(name="User", value=f"{message.author} ({message.author.id})")
                        embed.add_field(name="Group", value=f"{message.channel}")
                        embed.add_field(name="Content", value=message.content)
                        await webhook.send(embed=embed)
            except Exception as e:
                print(f"Error in antilast GC handling: {str(e)}")

load_kill_messages()
load_messages()
load_manual_messages()
load_whitelist()

try:
    bot.run(usertoken)
except discord.LoginFailure:
    print("[ERREUR] Token Discord invalide ou expire.")
    print("         Regenere ton token (Parametres > Avance > Reinitialiser le token)")
    print("         puis relance setup.bat pour le mettre a jour.")
    sys.exit(1)
except discord.PrivilegedIntentsRequired:
    print("[ERREUR] Intents Discord manquants — verifie ton installation discord.py-self.")
    sys.exit(1)
except KeyboardInterrupt:
    pass




