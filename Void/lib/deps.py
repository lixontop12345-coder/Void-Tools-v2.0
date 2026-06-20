"""Check and optionally install Python dependencies."""
import importlib
import os
import subprocess
import sys

REQUIRED = [
    ("colorama", "colorama"),
    ("rich", "rich"),
    ("discord", "discord.py-self==2.1.0"),
]

OPTIONAL = [
    ("dns.resolver", "dnspython"),
    ("requests", "requests"),
    ("pyzipper", "pyzipper"),
    ("aiofiles", "aiofiles"),
    ("pyfiglet", "pyfiglet"),
    ("plyer", "plyer"),
    ("pystyle", "pystyle"),
    ("tls_client", "tls-client"),
    ("spotipy", "spotipy"),
    ("pypresence", "pypresence"),
    ("PIL", "Pillow"),
    ("pyautogui", "pyautogui"),
]

if sys.platform == "win32":
    OPTIONAL.append(("win32api", "pywin32"))


def _requirements_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")


def _discord_ok() -> bool:
    try:
        import discord  # noqa: F401
        from discord.ext import commands  # noqa: F401

        return bool(getattr(discord, "__version__", None))
    except ImportError:
        return False


def _repair_discord() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "discord", "discord.py", "discord.py-self"],
            capture_output=True,
            check=False,
        )
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "discord.py-self==2.1.0", "-q"],
            capture_output=True,
            check=False,
        )
        return r.returncode == 0 and _discord_ok()
    except Exception:
        return False


def check_deps(auto_install=True) -> bool:
    if not _discord_ok() and auto_install:
        _repair_discord()

    missing = []
    for mod, pkg in REQUIRED + OPTIONAL:
        mod_root = mod.split(".")[0] if "." in mod else mod
        try:
            importlib.import_module(mod_root)
        except ImportError:
            missing.append(pkg)

    if not missing and _discord_ok():
        return True

    req_path = _requirements_path()
    if auto_install and os.path.isfile(req_path):
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req_path, "-q"],
                check=False,
                capture_output=True,
            )
            if not _discord_ok():
                _repair_discord()
            missing_after = []
            for mod, pkg in REQUIRED + OPTIONAL:
                mod_root = mod.split(".")[0] if "." in mod else mod
                try:
                    importlib.import_module(mod_root)
                except ImportError:
                    missing_after.append(pkg)
            required_only = {x[1] for x in REQUIRED}
            return all(p not in required_only for p in missing_after) and _discord_ok()
        except Exception:
            pass

    required_missing = [p for p in missing if p in {x[1] for x in REQUIRED}]
    return len(required_missing) == 0 and _discord_ok()
