"""Fail if legacy community invite links remain in the repo."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {".git", "Void - Output", "__pycache__", ".cursor", "data"}
BAD = (
    "discord.gg/v0id",
    "https://discord.gg/v0id",
    "discord.gg/dawa",
    "https://discord.gg/dawa",
    "join v0id",
)


def main():
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            if not name.endswith((".py", ".json", ".md", ".bat", ".txt", ".html")):
                continue
            if name == "check_discord_link.py":
                continue
            path = os.path.join(dirpath, name)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read().lower()
            except OSError:
                continue
            for needle in BAD:
                if needle in text:
                    hits.append((path, needle))
                    break
    if hits:
        print("LEGACY COMMUNITY LINK FOUND:")
        for path, needle in hits:
            print(f"  {needle} -> {path}")
        return 1
    print("OK — no legacy Discord community links in source files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
