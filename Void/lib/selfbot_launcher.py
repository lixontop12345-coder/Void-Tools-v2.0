"""Void Selfbot — launcher intégré Void-Tools v2."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

from . import constants as C
from .config import get_settings
from .i18n import reload_settings, t
from .void_common import cls, console, error_box, panel, pause, success_box

SELFBOT_TOOL_DIR = os.path.join(C.VOID_DIR, "tools", "void-selfbot")
SELFBOT_RUNTIME_DIR = os.path.join(SELFBOT_TOOL_DIR, "runtime")

_COPY_FILES = (
    "main.py",
    "void_ui.py",
    "void_pages.py",
    "void_cogs.py",
    "check_deps.py",
    "setup_config.py",
    "requirements.txt",
)
_COPY_DIRS = ("config", "data")


def _candidate_roots() -> list[str]:
    roots = [
        SELFBOT_RUNTIME_DIR,
        os.path.normpath(os.path.join(C.ROOT_DIR, "..", "Void-Selfbot-main")),
        os.path.normpath(os.path.join(C.VOID_DIR, "..", "..", "Void-Selfbot-main")),
    ]
    env = os.environ.get("VOID_SELFBOT_DIR", "").strip()
    if env:
        roots.insert(0, os.path.normpath(env))
    seen: set[str] = set()
    out: list[str] = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            out.append(root)
    return out


def _has_main(root: str) -> bool:
    return os.path.isfile(os.path.join(root, "main.py"))


def _sync_runtime(source: str, target: str) -> None:
    os.makedirs(target, exist_ok=True)
    for name in _COPY_FILES:
        src = os.path.join(source, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(target, name))
    for name in _COPY_DIRS:
        src = os.path.join(source, name)
        dst = os.path.join(target, name)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)


def resolve_selfbot_root(*, allow_sync: bool = True) -> str:
    """Return folder containing selfbot main.py (bundled runtime first)."""
    if _has_main(SELFBOT_RUNTIME_DIR):
        return SELFBOT_RUNTIME_DIR

    for root in _candidate_roots()[1:]:
        if _has_main(root):
            if allow_sync:
                try:
                    _sync_runtime(root, SELFBOT_RUNTIME_DIR)
                    if _has_main(SELFBOT_RUNTIME_DIR):
                        return SELFBOT_RUNTIME_DIR
                except OSError:
                    pass
            return root

    raise FileNotFoundError(
        t(
            "Void Selfbot introuvable.\n"
            f"Attendu: {SELFBOT_RUNTIME_DIR}\n"
            "Lance: python tools/void-selfbot/bundle_selfbot.py",
            "Void Selfbot not found.\n"
            f"Expected: {SELFBOT_RUNTIME_DIR}\n"
            "Run: python tools/void-selfbot/bundle_selfbot.py",
        )
    )


def _cfg_path(root: str, name: str) -> str:
    return os.path.join(root, "config", name)


def _load_settings(root: str) -> dict:
    path = _cfg_path(root, "settings.json")
    example = _cfg_path(root, "settings.example.json")
    if not os.path.isfile(path) and os.path.isfile(example):
        shutil.copy2(example, path)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_saved_token(root: str) -> str:
    settings_path = _cfg_path(root, "settings.json")
    if os.path.isfile(settings_path):
        try:
            token = (_load_settings(root).get("token") or "").strip()
            if token and token != "TON_TOKEN_ICI":
                return token
        except (json.JSONDecodeError, OSError):
            pass
    for name in ("token.txt", "tokens.txt"):
        path = _cfg_path(root, name)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip().strip('"').strip("'")
                if line and not line.startswith("#") and line != "TON_TOKEN_ICI":
                    return line
    return ""


def _save_token(root: str, token: str) -> None:
    config_dir = os.path.join(root, "config")
    os.makedirs(config_dir, exist_ok=True)
    settings = _load_settings(root)
    settings["token"] = token
    settings_path = _cfg_path(root, "settings.json")
    with open(settings_path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=4, ensure_ascii=False)
        handle.write("\n")
    with open(_cfg_path(root, "token.txt"), "w", encoding="utf-8") as handle:
        handle.write(token + "\n")
    tokens_path = _cfg_path(root, "tokens.txt")
    if not os.path.isfile(tokens_path):
        open(tokens_path, "a", encoding="utf-8").close()


def _prompt_token(existing: str) -> str:
    reload_settings()
    cls()
    panel(
        "SELFBOT",
        t(
            "VOID SELFBOT v2.0 BETA · discord.gg/voidv2 · t.me/v0idtool\n\n"
            "Colle ton token Discord (compte user).\n"
            "Entrée seule = réutiliser le token enregistré.",
            "VOID SELFBOT v2.0 BETA · discord.gg/voidv2 · t.me/v0idtool\n\n"
            "Paste your Discord token (user account).\n"
            "Press Enter = reuse saved token.",
        ),
    )
    console.print()
    if existing:
        console.print(
            f"  [dim]{t('Token actuel', 'Current token')} :[/] "
            f"{existing[:10]}...{existing[-4:]}"
        )
        console.print()
    token = input(
        f"  {C.C_MID}► {t('Token Discord', 'Discord token')} >> \033[0m"
    ).strip()
    if not token:
        if existing:
            return existing
        error_box(t("Token manquant", "Missing token"), t("Aucun token saisi.", "No token entered."))
        pause()
        raise SystemExit(1)
    if token == "TON_TOKEN_ICI":
        error_box(
            t("Token invalide", "Invalid token"),
            t("Remplace le placeholder par ton vrai token.", "Replace the placeholder with your real token."),
        )
        pause()
        raise SystemExit(1)
    return token


def _ensure_deps(root: str) -> None:
    check = os.path.join(root, "check_deps.py")
    if not os.path.isfile(check):
        return
    console.print(f"\n  [dim]{t('Vérification discord.py-self…', 'Checking discord.py-self…')}[/]")
    result = subprocess.run([sys.executable, check], cwd=root, shell=False)
    if result.returncode != 0:
        req = os.path.join(root, "requirements.txt")
        if os.path.isfile(req):
            console.print(f"  [dim]{t('Installation des dépendances selfbot…', 'Installing selfbot dependencies…')}[/]")
            pip = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req],
                cwd=root,
                shell=False,
            )
            if pip.returncode != 0:
                error_box(
                    t("Dépendances", "Dependencies"),
                    t("pip install a échoué.", "pip install failed."),
                    req,
                )
                pause()
                raise SystemExit(1)
            result = subprocess.run([sys.executable, check], cwd=root, shell=False)
        if result.returncode != 0:
            error_box(
                "discord.py-self",
                t("Installation impossible.", "Installation failed."),
                t("Utilise Python 3.11 ou 3.12 puis relance.", "Use Python 3.11 or 3.12 and retry."),
            )
            pause()
            raise SystemExit(1)


def launch_void_selfbot(*, reuse_token: bool = True) -> None:
    """Prompt token (if needed) and run Void Selfbot until disconnect."""
    reload_settings()
    try:
        root = resolve_selfbot_root()
    except FileNotFoundError as exc:
        error_box(t("Selfbot absent", "Selfbot missing"), str(exc))
        pause()
        return

    saved = _read_saved_token(root) if reuse_token else ""
    token = saved
    if not saved:
        token = _prompt_token("")
    else:
        token = _prompt_token(saved)

    _save_token(root, token)
    _ensure_deps(root)

    cls()
    success_box(
        t("Connexion", "Connecting"),
        t("Lancement du selfbot — Ctrl+C pour quitter.", "Starting selfbot — Ctrl+C to quit."),
    )
    console.print(f"  [dim]{t('Source', 'Source')} :[/] {root}\n")

    main_py = os.path.join(root, "main.py")
    try:
        result = subprocess.run([sys.executable, main_py], cwd=root, shell=False)
        if result.returncode not in (0, None):
            error_box("Selfbot", t(f"Arrêt avec code {result.returncode}", f"Exit code {result.returncode}"))
            pause()
    except KeyboardInterrupt:
        console.print(f"\n  [{C.C_DIM}]{t('Selfbot arrêté.', 'Selfbot stopped.')}[/]")
        pause()
    except Exception as exc:
        error_box("Selfbot", str(exc))
        pause()
