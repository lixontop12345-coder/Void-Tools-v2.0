"""One-shot: bundle Void-Selfbot into Void-Tools runtime (for git push)."""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SELFBOT_SRC = os.environ.get(
    "VOID_SELFBOT_SRC",
    os.path.normpath(os.path.join(ROOT, "..", "..", "Void-Selfbot-main")),
)
RUNTIME = os.path.join(ROOT, "tools", "void-selfbot", "runtime")

FILES = (
    "main.py",
    "void_ui.py",
    "void_pages.py",
    "void_cogs.py",
    "check_deps.py",
    "setup_config.py",
    "requirements.txt",
)
DIRS = ("config", "data")


def main() -> int:
    if not os.path.isfile(os.path.join(SELFBOT_SRC, "main.py")):
        print(f"[ERREUR] Source introuvable: {SELFBOT_SRC}")
        return 1
    os.makedirs(RUNTIME, exist_ok=True)
    for name in FILES:
        shutil.copy2(os.path.join(SELFBOT_SRC, name), os.path.join(RUNTIME, name))
        print(f"  + {name}")
    for name in DIRS:
        src = os.path.join(SELFBOT_SRC, name)
        dst = os.path.join(RUNTIME, name)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
            print(f"  + {name}/")
    # Safe defaults for git (no user tokens)
    token_txt = os.path.join(RUNTIME, "config", "token.txt")
    with open(token_txt, "w", encoding="utf-8") as handle:
        handle.write("# Colle ton token Discord sur la ligne suivante :\n")
    example = os.path.join(RUNTIME, "config", "settings.example.json")
    settings = os.path.join(RUNTIME, "config", "settings.json")
    if os.path.isfile(example):
        shutil.copy2(example, settings)
    print(f"[OK] Selfbot bundle -> {RUNTIME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
