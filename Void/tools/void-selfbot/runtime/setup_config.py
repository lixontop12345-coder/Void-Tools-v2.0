"""Configuration Discord — interactif, fichier, ou argument."""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(ROOT, "config")
os.makedirs(CFG, exist_ok=True)
CONFIG = os.path.join(CFG, "settings.json")
EXAMPLE = os.path.join(CFG, "settings.example.json")
TOKEN_FILE = os.path.join(CFG, "token.txt")
TOKENS_FILE = os.path.join(CFG, "tokens.txt")


def load_cfg() -> dict:
    if not os.path.exists(CONFIG):
        if os.path.exists(EXAMPLE):
            shutil.copy(EXAMPLE, CONFIG)
        else:
            print("[ERREUR] config/settings.example.json introuvable.")
            sys.exit(1)
    with open(CONFIG, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_cfg(cfg: dict) -> None:
    with open(CONFIG, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=4, ensure_ascii=False)
        handle.write("\n")


def read_token_file(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().strip('"').strip("'")
            if line and not line.startswith("#") and line != "TON_TOKEN_ICI":
                return line
    return ""


def write_token_files(token: str) -> None:
    with open(TOKEN_FILE, "w", encoding="utf-8") as handle:
        handle.write(token + "\n")


def main() -> int:
    cfg = load_cfg()

    token = ""
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()

    if not token:
        token = read_token_file(TOKEN_FILE)

    if not token and sys.stdin.isatty():
        print()
        print("Colle ton TOKEN Discord (clic droit dans cette fenetre pour coller)")
        token = input("Token: ").strip()

    if not token or token == "TON_TOKEN_ICI":
        print()
        print("[ERREUR] Token vide.")
        print("         Colle-le dans config\\token.txt puis relance start.bat")
        print("         OU: python setup_config.py TON_TOKEN_ICI")
        if not os.path.isfile(TOKEN_FILE):
            open(TOKEN_FILE, "w", encoding="utf-8").close()
        return 1

    if sys.stdin.isatty():
        print()
        print("Colle ton ID Discord (Entree = garder la valeur actuelle)")
        user_id = input("User ID: ").strip()
        if user_id:
            cfg["NukeServerBypass"] = user_id

    cfg["token"] = token
    save_cfg(cfg)
    write_token_files(token)

    if not os.path.exists(TOKENS_FILE):
        open(TOKENS_FILE, "w", encoding="utf-8").close()

    print("[OK] Token enregistre dans config/settings.json et config/token.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
