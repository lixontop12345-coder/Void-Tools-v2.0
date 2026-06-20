"""Verify discord.py-self before launching Void Tools."""
from __future__ import annotations

import subprocess
import sys


def ok() -> bool:
    try:
        import discord  # noqa: F401
        from discord.ext import commands  # noqa: F401

        if not getattr(discord, "__version__", None):
            return False
        return True
    except ImportError:
        return False


def repair() -> int:
    print("[..] Reinstallation de discord.py-self...")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "uninstall",
            "-y",
            "discord",
            "discord.py",
            "discord.py-self",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "discord.py-self==2.1.0",
            "--force-reinstall",
            "--no-cache-dir",
        ]
    )


def main() -> int:
    if ok():
        import discord

        print(f"[OK] discord.py-self {discord.__version__}")
        return 0

    print("[ERREUR] discord.py-self absent ou installe incorrectement.")
    print("         (souvent: mauvais package 'discord' ou install cassee)")
    if repair() != 0:
        print("[ERREUR] pip install a echoue. Lance setup.bat")
        return 1
    if not ok():
        print("[ERREUR] discord.ext.commands toujours indisponible.")
        print("         Utilise Python 3.10 - 3.12 si le probleme persiste.")
        return 1
    import discord

    print(f"[OK] discord.py-self {discord.__version__} repare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
