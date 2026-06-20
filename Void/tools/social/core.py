#!/usr/bin/env python3
"""Void-Tools — Social free tools."""
import sys, json, os, re, shutil, webbrowser
from datetime import datetime, timezone
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import urllib.request
import urllib.error
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.padding import Padding
from rich import box

console = Console(highlight=False)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
GITHUB_UA = "Void-Tools"
C_BRAND = "#FF0050"
C_OK, C_ERR, C_GOLD, C_DIM = "#00FF88", "#FF4444", "#FFD700", "#888888"
L = {}

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from lib import constants as C  # noqa: E402


def set_language(s):
    global L
    L = s


def t(k):
    return L.get(k, k)


def _tw():
    return max(52, min(70, shutil.get_terminal_size((80, 24)).columns - 4))


def _ask(p):
    return input(f"\033[38;2;255;0;80m  {p} \033[38;2;180;180;200m>>\033[0m ").strip()


def _pause():
    console.print()
    input(f"\033[38;2;100;100;120m  {t('pause')} \033[0m")


def _panel(title, desc):
    console.print()
    console.print(Panel(
        Align.center(Text.from_markup(f"[bold {C_GOLD}]{title}[/]\n[{C_DIM}]{desc}[/]")),
        border_style=C_BRAND, box=box.ROUNDED, padding=(1, 2), width=_tw(),
    ))


def _fail(msg, detail=None):
    body = Text.from_markup(f"[bold {C_ERR}]{msg}[/]")
    if detail:
        body.append("\n")
        body.append(Text.from_markup(f"[{C_DIM}]{detail}[/]"))
    console.print(Panel(body, border_style=C_ERR, box=box.ROUNDED, padding=(1, 2), width=_tw()))


def _get(url, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json,text/html"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status, r.read().decode(errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="ignore")
    except Exception as ex:
        return 0, str(ex)


def _show_table(title, rows):
    tbl = Table(box=box.SIMPLE, border_style=C_BRAND, show_header=False, padding=(0, 1))
    tbl.add_column("K", style="dim", width=14)
    tbl.add_column("V", overflow="fold")
    for k, v in rows:
        tbl.add_row(k, str(v))
    console.print(Padding(Panel(tbl, title=f"[bold {C_GOLD}]{title}[/]", border_style=C_BRAND, box=box.ROUNDED, width=_tw()), (1, 0)))


def _export_dir():
    path = os.path.join(C.DATA_DIR, "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _save_json(name, payload):
    path = os.path.join(_export_dir(), name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def _hint(text):
    console.print(Padding(f"  [{C_DIM}]{text}[/]", (0, 1)))


def _print_clickable_url(label, url):
    url = (url or "").strip()
    if not url or url == "-":
        return
    console.print(f"  [{C_DIM}]{label}[/]")
    console.print(f"  [link={url}]{url}[/link]", soft_wrap=False, overflow="ignore", crop=False)


def _og(html, prop):
    m = re.search(rf'property="og:{prop}" content="([^"]*)"', html)
    return m.group(1).strip() if m else "-"


PLATFORMS = [
    ("GitHub", "https://github.com/{}"),
    ("X / Twitter", "https://x.com/{}"),
    ("Instagram", "https://instagram.com/{}"),
    ("TikTok", "https://tiktok.com/@{}"),
    ("YouTube", "https://youtube.com/@{}"),
    ("Reddit", "https://reddit.com/u/{}"),
    ("Twitch", "https://twitch.tv/{}"),
    ("Steam", "https://steamcommunity.com/id/{}"),
    ("Snapchat", "https://snapchat.com/add/{}"),
    ("Telegram", "https://t.me/{}"),
]


def username_check():
    _panel(t("uc_title"), t("uc_desc"))
    u = _ask(t("username"))
    if not u:
        return
    tbl = Table(box=box.SIMPLE, border_style=C_BRAND)
    tbl.add_column("Platform", style=C_GOLD)
    tbl.add_column("URL", style="white")
    for name, tmpl in PLATFORMS:
        tbl.add_row(name, tmpl.format(u))
    console.print(Padding(Panel(tbl, title=f"@{u}", border_style=C_BRAND), (1, 0)))
    if input(f"\n  {t('open_links')} (y/n) >> ").strip().lower() in ("y", "yes", "o", "oui"):
        for _, url in PLATFORMS:
            webbrowser.open(url.format(u))


def youtube_channel():
    _panel(t("ytc_title"), t("ytc_desc"))
    raw = _ask(t("channel_id"))
    if not raw:
        return
    cid = raw.strip()
    if cid.startswith("@"):
        url = f"https://www.youtube.com/{cid}"
        code, body = _get(url)
        _show_table("YouTube", [("URL", url), ("Status", f"HTTP {code}"), ("Tip", t("yt_tip"))])
        return
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&id={cid}&key=AIzaSyDummy"
    code, body = _get(f"https://www.youtube.com/channel/{cid}")
    _show_table("YouTube Channel", [
        ("Channel ID", cid),
        ("Link", f"https://youtube.com/channel/{cid}"),
        ("Status", f"HTTP {code}"),
        ("Note", t("yt_api_note")),
    ])


def youtube_video():
    _panel(t("ytv_title"), t("ytv_desc"))
    vid = _ask(t("video_id"))
    if not vid:
        return
    vid = vid.split("v=")[-1].split("&")[0].split("/")[-1]
    code, _ = _get(f"https://www.youtube.com/watch?v={vid}")
    _show_table("Video", [
        ("ID", vid),
        ("URL", f"https://youtube.com/watch?v={vid}"),
        ("HTTP", code),
        ("Thumb", f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"),
    ])


def x_profile():
    _panel(t("x_title"), t("x_desc"))
    u = _ask(t("username")).lstrip("@")
    if not u:
        return
    mirrors = [
        f"https://nitter.poast.org/{u}",
        f"https://x.com/{u}",
    ]
    for url in mirrors:
        code, _ = _get(url)
        if code == 200:
            _show_table(f"@{u}", [("Mirror", url), ("Status", "OK"), ("Profile", url)])
            return
    _show_table(f"@{u}", [("X", f"https://x.com/{u}"), ("Nitter", mirrors[0]), ("Status", t("check_manual"))])


def tiktok_profile():
    _panel(t("tt_title"), t("tt_desc"))
    u = _ask(t("username")).lstrip("@")
    if not u:
        return
    url = f"https://www.tiktok.com/@{u}"
    code, body = _get(url)
    found = code == 200 and "user" in body.lower()
    _show_table(f"@{u}", [
        ("URL", url),
        ("HTTP", code),
        ("Likely", t("yes") if found else t("unknown")),
    ])


def instagram_profile():
    _panel(t("ig_title"), t("ig_desc"))
    u = _ask(t("username")).lstrip("@")
    if not u:
        return
    url = f"https://www.instagram.com/{u}/"
    code, body = _get(url)
    priv = "private" in body.lower() or code == 200
    _show_table(f"@{u}", [
        ("URL", url),
        ("HTTP", code),
        ("Exists", t("maybe") if code == 200 else t("no")),
        ("Note", t("ig_note")),
    ])


def snapchat_check():
    _panel(t("sc_title"), t("sc_desc"))
    u = _ask(t("username"))
    if not u:
        return
    url = f"https://www.snapchat.com/add/{u}"
    code, _ = _get(url)
    _show_table(f"@{u}", [("Add URL", url), ("HTTP", code), ("Tip", t("sc_tip"))])


def telegram_channel():
    _panel(t("tg_title"), t("tg_desc"))
    ch = _ask(t("channel")).strip().lstrip("@")
    ch = ch.replace("https://t.me/", "").split("/")[0]
    if not ch:
        return
    code, body = _get(f"https://t.me/{ch}")
    if code != 200:
        _fail(t("tg_not_found"), f"HTTP {code}")
        return
    title = _og(body, "title")
    description = _og(body, "description")
    image = _og(body, "image")
    members_m = re.search(r"([\d\s]+)\s+subscribers", body)
    members = members_m.group(1).replace(" ", "") if members_m else "-"
    link = f"https://t.me/{ch}"
    _show_table(f"@{ch}", [
        (t("tg_channel"), f"@{ch}"),
        ("Title", title),
        ("Description", description[:120]),
        (t("tg_members"), members),
        (t("tg_preview"), t("tg_see_below") if image.startswith("http") else image),
        ("Link", t("tg_see_below")),
        (t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"),
    ])
    if image.startswith("http"):
        _print_clickable_url(t("tg_image_link"), image)
    _print_clickable_url(t("tg_open_link"), link)
    report = _save_json(f"telegram_{ch}.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel": ch, "title": title, "description": description,
        "members": members, "image": image, "link": link,
    })
    _hint(f"+ report → {report}")


def github_profile():
    _panel(t("gh_title"), t("gh_desc"))
    user = _ask(t("username")).strip().lstrip("@")
    if not user:
        return
    headers = {"User-Agent": GITHUB_UA, "Accept": "application/vnd.github+json"}
    try:
        r = requests.get(f"https://api.github.com/users/{user}", headers=headers, timeout=12)
        if r.status_code != 200:
            _fail(t("gh_not_found"), f"HTTP {r.status_code}")
            return
        u = r.json()
        repos_r = requests.get(
            u.get("repos_url", ""), headers=headers, timeout=12,
            params={"per_page": 5, "sort": "updated"},
        )
        repos = repos_r.json() if repos_r.status_code == 200 else []
        orgs_r = requests.get(f"https://api.github.com/users/{user}/orgs", headers=headers, timeout=12)
        orgs = orgs_r.json() if orgs_r.status_code == 200 else []
    except requests.RequestException as ex:
        _fail(t("network"), str(ex))
        return
    top_repos = ", ".join(x.get("name", "?") for x in repos[:5]) or "-"
    org_names = ", ".join(o.get("login", "?") for o in orgs[:5]) or "-"
    _show_table(f"GitHub — {user}", [
        ("Name", u.get("name") or "-"),
        ("Bio", (u.get("bio") or "-")[:120]),
        ("Company", u.get("company") or "-"),
        ("Location", u.get("location") or "-"),
        (t("gh_repos"), str(u.get("public_repos", "?"))),
        (t("gh_followers"), str(u.get("followers", "?"))),
        (t("gh_following"), str(u.get("following", "?"))),
        (t("gh_created"), (u.get("created_at") or "?")[:10]),
        (t("gh_top_repos"), top_repos),
        (t("gh_orgs"), org_names),
        ("Profile", u.get("html_url", "-")),
        (t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"),
    ])
    report = _save_json(f"github_{user}.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": u, "repos": repos, "orgs": orgs,
    })
    _hint(f"+ report → {report}")


def kick_profile():
    _panel(t("kick_title"), t("kick_desc"))
    user = _ask(t("username")).strip().lstrip("@")
    if not user:
        return
    try:
        r = requests.get(
            f"https://kick.com/api/v2/channels/{user}",
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=12,
        )
        if r.status_code != 200:
            _fail(t("kick_not_found"), f"HTTP {r.status_code}")
            return
        data = r.json()
    except requests.RequestException as ex:
        _fail(t("network"), str(ex))
        return
    kick_user = data.get("user") or {}
    live = data.get("livestream") or {}
    profile = f"https://kick.com/{user}"
    banner = kick_user.get("banner_image") or data.get("banner_image") or ""
    _show_table(f"Kick — {user}", [
        ("Username", kick_user.get("username", user)),
        ("Bio", (kick_user.get("bio") or "-")[:120]),
        (t("kick_followers"), str(data.get("followers_count", "?"))),
        (t("kick_live"), t("yes") if live else t("no")),
        (t("kick_stream"), (live.get("session_title") or "-")[:80]),
        (t("kick_viewers"), str(live.get("viewer_count", "-")) if live else "-"),
        (t("kick_verified"), t("yes") if kick_user.get("verified") else t("no")),
        ("Profile", t("tg_see_below")),
        (t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"),
    ])
    _print_clickable_url(t("kick_profile_link"), profile)
    if isinstance(banner, str) and banner.startswith("http"):
        _print_clickable_url(t("kick_banner_link"), banner)
    report = _save_json(f"kick_{user}.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "username": user, "profile": profile, "banner": banner, "data": data,
    })
    _hint(f"+ report → {report}")


def minecraft_profile():
    _panel(t("mc_title"), t("mc_desc"))
    name = _ask(t("mc_username")).strip()
    if not name:
        return
    try:
        r = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}", timeout=12)
        if r.status_code != 200:
            _fail(t("mc_not_found"), f"HTTP {r.status_code}")
            return
        profile = r.json()
        uid = profile["id"]
        uid_fmt = f"{uid[:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:20]}-{uid[20:]}"
        pr = requests.get(
            f"https://sessionserver.mojang.com/session/minecraft/profile/{uid_fmt}",
            timeout=12,
        )
        session = pr.json() if pr.status_code == 200 else {}
    except requests.RequestException as ex:
        _fail(t("network"), str(ex))
        return
    skin_url = f"https://visage.surgeplay.com/full/512/{uid}"
    namemc_url = f"https://namemc.com/profile/{uid_fmt}"
    _show_table(f"Minecraft — {name}", [
        ("Username", profile.get("name", name)),
        ("UUID", uid_fmt),
        ("Skin", t("tg_see_below")),
        (t("mc_textures"), t("mc_custom") if session.get("properties") else t("mc_default")),
        ("NameMC", t("tg_see_below")),
        (t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"),
    ])
    _print_clickable_url(t("mc_skin_link"), skin_url)
    _print_clickable_url(t("mc_namemc_link"), namemc_url)
    report = _save_json(f"minecraft_{name}.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile, "session": session,
        "skin_url": skin_url, "namemc_url": namemc_url,
    })
    _hint(f"+ report → {report}")


TOOLS = {
    "username-check": username_check,
    "youtube-channel": youtube_channel,
    "youtube-video": youtube_video,
    "x-profile": x_profile,
    "tiktok-profile": tiktok_profile,
    "instagram-profile": instagram_profile,
    "snapchat-check": snapchat_check,
    "telegram-channel": telegram_channel,
    "github-profile": github_profile,
    "kick-profile": kick_profile,
    "minecraft-profile": minecraft_profile,
}


def run_tool(key):
    os.system("cls" if os.name == "nt" else "clear")
    fn = TOOLS.get(key)
    if not fn:
        _fail(f"{t('unknown')} {key}")
        _pause()
        return
    try:
        fn()
    except KeyboardInterrupt:
        console.print(f"\n  [{C_DIM}]{t('cancelled')}[/]")
    except Exception as ex:
        _fail(type(ex).__name__, str(ex))
    _pause()
