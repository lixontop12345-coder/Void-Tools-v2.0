"""Void Tools UI — Rich console boot + Discord ANSI panels."""
from __future__ import annotations

import asyncio
import ctypes
import os
import sys
from typing import TYPE_CHECKING, Any

import pyfiglet
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    pass

_console: Console | None = None


def _ensure_utf8_console() -> None:
    if os.name != "nt":
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_console() -> Console:
    global _console
    if _console is None:
        _ensure_utf8_console()
        _console = Console(force_terminal=True, highlight=False, legacy_windows=False)
    return _console


def _figlet_logo(text: str = "VOID") -> str:
    try:
        return pyfiglet.figlet_format(text, font="slant")
    except Exception:
        return pyfiglet.figlet_format(text, font="standard")


def _set_title(title: str) -> None:
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass


async def play_void_splash(
    brand_name: str,
    version: str,
    tier: str,
) -> None:
    """Animated boot sequence (Rich Live + progress)."""
    _ensure_utf8_console()
    console = get_console()
    _set_title(f"{brand_name} | Boot")
    os.system("cls")

    logo = _figlet_logo("VOID")
    stages = [
        (18, "Syncing void core"),
        (36, "Loading modules"),
        (54, "Validating license tier"),
        (72, "Arming command stack"),
        (88, "Opening void link"),
        (100, "Online"),
    ]

    progress = Progress(
        SpinnerColumn("dots", style="bold red"),
        TextColumn("[bold white]{task.description:<22}"),
        BarColumn(
            bar_width=36,
            complete_style="red",
            finished_style="bold green",
            pulse_style="red",
        ),
        TextColumn("[bold]{task.percentage:>5.1f}%"),
        expand=True,
    )
    task_id = progress.add_task(stages[0][1], total=100)

    with Live(Group(_header_panel(logo, brand_name, version, tier), progress), console=console, refresh_per_second=20, screen=False) as live:
        stage_idx = 0
        for target, label in stages:
            while progress.tasks[task_id].completed < target:
                progress.update(task_id, advance=1.8, description=label)
                live.update(Group(_header_panel(logo, brand_name, version, tier), progress))
                await asyncio.sleep(0.035)
            stage_idx += 1

        done = Panel(
            Align.center(
                Text.assemble(
                    ("BETA TEST", "bold yellow"),
                    ("\n", ""),
                    ("ONLINE", "bold green"),
                    ("\n", ""),
                    (f"{brand_name} {version}", "bold white"),
                    ("  |  ", "dim"),
                    (tier, "bold yellow" if tier == "FREE" else "bold red"),
                    ("\n", ""),
                    ("discord.gg/voidv2", "cyan"),
                    (" · ", "dim"),
                    ("t.me/v0idtool", "cyan"),
                    ("\n", ""),
                    (".menu", "cyan"),
                    (" · ", "dim"),
                    (".help", "cyan"),
                ),
                vertical="middle",
            ),
            title=f"[bold red]{brand_name}[/]",
            border_style="green",
            padding=(1, 4),
        )
        live.update(done)
        _set_title(f"{brand_name} | {tier} | Online")
        await asyncio.sleep(0.65)


def _header_panel(logo: str, brand: str, version: str, tier: str) -> Panel:
    tier_style = "bold red" if tier == "VIP" else "bold yellow"
    body = Align.center(
        Text(logo, style="bold red"),
        vertical="middle",
    )
    return Panel(
        body,
        title=f"[bold white]{brand}[/] [dim]{version}[/]",
        subtitle=Text.assemble(("Plan ", "dim"), (tier, tier_style)),
        border_style="red",
        padding=(0, 2),
    )


def render_void_banner(
    user_name: str,
    prefix: str,
    guilds: int,
    friends: int,
    tokens: int,
    brand_name: str,
    version: str,
    tier: str,
) -> str:
    """Plain-text banner (for .cls replay)."""
    console = get_console()
    with console.capture() as capture:
        _print_banner_table(
            console,
            user_name,
            prefix,
            guilds,
            friends,
            tokens,
            brand_name,
            version,
            tier,
        )
    return capture.get()


def print_void_banner(
    user_name: str,
    prefix: str,
    guilds: int,
    friends: int,
    tokens: int,
    brand_name: str,
    version: str,
    tier: str,
) -> str:
    console = get_console()
    _print_banner_table(
        console,
        user_name,
        prefix,
        guilds,
        friends,
        tokens,
        brand_name,
        version,
        tier,
    )
    return render_void_banner(
        user_name,
        prefix,
        guilds,
        friends,
        tokens,
        brand_name,
        version,
        tier,
    )


def _print_banner_table(
    console: Console,
    user_name: str,
    prefix: str,
    guilds: int,
    friends: int,
    tokens: int,
    brand_name: str,
    version: str,
    tier: str,
) -> None:
    logo = _figlet_logo("VOID")
    tier_style = "bold red" if tier == "VIP" else "bold yellow"

    table = Table(show_header=False, box=None, pad_edge=False, padding=(0, 1))
    table.add_column(style="dim white", width=10)
    table.add_column(style="bold white")
    table.add_row("User", user_name[:28])
    table.add_row("Prefix", str(prefix))
    table.add_row("Plan", Text(tier, style=tier_style))
    table.add_row("Guilds", str(guilds))
    table.add_row("Friends", str(friends))
    table.add_row("Tokens", str(tokens))

    layout = Group(
        Align.center(Text(logo, style="bold red")),
        Panel(
            table,
            title=f"[bold green]ONLINE[/]  [dim]|[/]  [bold white]{brand_name} {version}[/]",
            border_style="red",
            padding=(0, 2),
        ),
        Align.center(
            Text.assemble(
                (".menu", "cyan bold"),
                ("  ", ""),
                (".help", "cyan bold"),
                ("  ", ""),
                (".info", "cyan bold"),
                ("  ", ""),
                (".vip", "cyan bold"),
            )
        ),
    )
    console.print(layout)


# ── Discord messages (selfbot: no embed= support) ─────────────────
DISCORD_W = 40
DISCORD_MAX = 1990

_A = "\033[0m"
_R = "\033[31m"
_G = "\033[32m"
_Y = "\033[33m"
_C = "\033[36m"
_W = "\033[37m"
_M = "\033[35m"
_D = "\033[90m"
_P = "\033[95m"


def _plain(text: str) -> str:
    for code in (_R, _G, _Y, _C, _W, _M, _D, _P, _A):
        text = text.replace(code, "")
    return text


def _fit(text: str, width: int) -> str:
    plain = _plain(text)
    if len(plain) <= width:
        return text + (" " * (width - len(plain)))
    return plain[:width]


def discord_panel(title: str, lines: list[str]) -> str:
    top = f"{_R}╭{'─' * DISCORD_W}╮{_A}"
    mid = f"{_R}│{_A}{_P}{_fit(title, DISCORD_W)}{_A}{_R}│{_A}"
    sep = f"{_R}├{'─' * DISCORD_W}┤{_A}"
    rows = [top, mid, sep]
    for line in lines:
        if not line:
            rows.append(f"{_R}│{' ' * DISCORD_W}│{_A}")
            continue
        content = _fit(line, DISCORD_W - 1)
        plain_len = len(_plain(content))
        pad = max(0, DISCORD_W - 1 - plain_len)
        rows.append(f"{_R}│{_A} {content}{' ' * pad}{_R}│{_A}")
    rows.append(f"{_R}╰{'─' * DISCORD_W}╯{_A}")
    out = "```ansi\n" + "\n".join(rows) + "\n```"
    return out[:DISCORD_MAX] if len(out) > DISCORD_MAX else out


def _pair(left: str, right: str) -> str:
    return f"{_fit(left, 18)}{_D}|{_A} {right}"


def text_main_menu(is_vip: bool, version: str, brand: str = "Void Tools", *, vip_enabled: bool = True) -> str:
    import void_pages

    vip_pages = set() if not vip_enabled else {1, 6, 7, 10, 12, 13, 15}
    unlocked = is_vip or not vip_enabled
    return text_main_menu_v2(
        unlocked,
        version,
        brand,
        void_pages.NAV_LABELS,
        vip_pages,
        vip_enabled=vip_enabled,
    )


def text_info_stats(
    user: str,
    prefix: str,
    brand: str,
    version: str,
    tier: str,
    guilds: int,
    friends: int,
    tokens: int,
    uptime: str,
) -> str:
    tier_col = _G if tier == "VIP" else _Y
    body = [
        f"{_W}User{_A}     {_C}{user[:28]:<28}{_A}",
        f"{_W}Prefix{_A}   {_C}{prefix:<28}{_A}",
        f"{_W}Version{_A}  {_C}{brand} {version}{_A}",
        f"{_W}Plan{_A}     {tier_col}{tier:<28}{_A}",
        f"{_W}Guilds{_A}   {_C}{guilds:<8}{_A}{_W}Friends{_A} {_C}{friends}{_A}",
        f"{_W}Tokens{_A}   {_C}{tokens:<8}{_A}{_W}Uptime{_A}  {_C}{uptime}{_A}",
        "",
        f"{_W}Discord{_A}  {_C}discord.gg/voidv2{_A}",
        f"{_W}Telegram{_A} {_C}t.me/v0idtool{_A}",
    ]
    return discord_panel("YOUR STATS", body)


def text_vip_status(vip: Any) -> str:
    if vip.is_active():
        key_hint = vip.license_key[:12] + "..." if len(vip.license_key) > 12 else vip.license_key
        body = [
            f"{_G}VIP ACTIVE{_A}",
            f"{_W}Key{_A}       {_C}{key_hint}{_A}",
            f"{_W}Unlocked{_A} Multi · Nuke · Spotify · PC · Auto beef · Advanced",
        ]
        return discord_panel("PLANS & LICENSE", body)

    body = [
        f"{_Y}FREE PLAN{_A}  {_D}|{_A}  {_W}VIP unlocks premium modules{_A}",
        "",
    ]
    for i, step in enumerate(vip.ticket_steps, 1):
        body.append(f"{_W}{i}.{_A} {step}")
    body += [
        "",
        f"{_C}{vip.discord_invite}{_A}",
        f"{_C}t.me/v0idtool{_A}",
        f"{_W}Activate:{_A} {_C}.license <key>{_A}",
        f"{_D}{vip.price_label}{_A}",
    ]
    return discord_panel("PLANS & LICENSE", body)


def text_vip_lock(vip: Any) -> str:
    body = [
        f"{_Y}VIP required{_A}  {_D}({vip.price_label}){_A}",
        "",
    ]
    for i, step in enumerate(vip.ticket_steps, 1):
        body.append(f"{_W}{i}.{_A} {step}")
    body += [
        "",
        f"{_C}{vip.discord_invite}{_A}",
        f"{_C}t.me/v0idtool{_A}",
        f"{_W}Then:{_A} {_C}.license <key>{_A}",
    ]
    return discord_panel("VIP REQUIRED", body)


def text_notice(title: str, message: str, *, success: bool = True) -> str:
    col = _G if success else _R
    return discord_panel(title.upper(), [f"{col}{message}{_A}"])


# ── Help pages (.p1 – .p15) ───────────────────────────────────────
HELP_MAX = 1990
HELP_CMD_W = 20
HELP_DESC_W = 28


def _trunc(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return text[:max_len]
    return text[: max_len - 1] + "…"


def _cmd_line(cmd: str, desc: str, accent: str) -> list[str]:
    """One or two lines; never exceeds Discord-friendly width."""
    cmd_plain = cmd.strip()
    desc_plain = _trunc(desc.strip(), HELP_DESC_W)

    if len(cmd_plain) <= HELP_CMD_W:
        pad = HELP_CMD_W - len(cmd_plain)
        return [f"  {accent}{cmd_plain}{_A}{' ' * pad}{_D}{desc_plain}{_A}"]

    return [
        f"  {accent}{cmd_plain}{_A}",
        f"    {_D}{desc_plain}{_A}",
    ]


def build_help_page(
    page_num: int,
    total: int,
    page_data: dict,
    *,
    accent: str = _C,
    highlight: str = _M,
    text: str = _W,
) -> str:
    title = page_data["title"]
    subtitle = page_data.get("subtitle", "")
    vip = page_data.get("vip", False)
    badge = f" {_Y}[VIP]{_A}" if vip else ""

    lines: list[str] = [
        f"{_R}{_P}{'─' * 44}{_A}",
        f"{_P}  P{page_num} · {title}{badge}{_A}",
        f"{_R}{'─' * 44}{_A}",
    ]
    if subtitle:
        lines.append(f"{_D}  {subtitle}{_A}")
        lines.append("")

    for section_name, commands in page_data.get("sections", []):
        lines.append(f"{highlight}  ▸ {section_name}{_A}")
        for cmd, desc in commands:
            lines.extend(_cmd_line(cmd, desc, accent))
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    prev_p = page_num - 1 if page_num > 1 else total
    next_p = page_num + 1 if page_num < total else 1
    lines += [
        f"{_R}{'─' * 44}{_A}",
        (
            f"{_D}  Page {page_num}/{total}{_A}  "
            f"{accent}.p{prev_p}{_A}{_D} | {_A}{accent}.p{next_p}{_A}  "
            f"{_D}|{_A}  {accent}.menu{_A}  {accent}.help <cmd>{_A}"
        ),
    ]

    msg = "```ansi\n" + "\n".join(lines) + "\n```"
    return msg[:HELP_MAX] if len(msg) > HELP_MAX else msg


def text_command_help(
    cmd: str,
    usage: str,
    category: str,
    description: str,
    example: str,
    *,
    accent: str = _C,
    highlight: str = _M,
) -> str:
    body = [
        f"{_R}{'─' * 44}{_A}",
        f"{_P}  .{cmd}{_A}",
        f"{_R}{'─' * 44}{_A}",
        f"  {highlight}Usage{_A}     {accent}{usage}{_A}",
        f"  {highlight}Category{_A}  {_W}{category}{_A}",
        f"  {highlight}Info{_A}      {_W}{description}{_A}",
        f"  {highlight}Example{_A}   {accent}{example}{_A}",
    ]
    return f"```ansi\n" + "\n".join(body) + "\n```"


def text_main_menu_v2(
    is_vip: bool,
    version: str,
    brand: str,
    nav_labels: dict[int, str],
    vip_pages: set[int],
    *,
    vip_enabled: bool = True,
) -> str:
    locked = vip_enabled and not is_vip
    plan = f"{_Y}FREE{_A}" if not vip_enabled else (f"{_G}VIP{_A}" if is_vip else f"{_Y}FREE{_A}")
    vip_tag = f"{_Y}*{_A}" if locked else ""

    rows: list[str] = []
    nums = sorted(nav_labels.keys())
    for i in range(0, len(nums), 2):
        a, b = nums[i], nums[i + 1] if i + 1 < len(nums) else None
        tag_a = vip_tag if a in vip_pages else ""
        left = f"{_C}.p{a:<2}{_A} {nav_labels[a]:<10}{tag_a}"
        if b is not None:
            tag_b = vip_tag if b in vip_pages else ""
            right = f"{_C}.p{b:<2}{_A} {nav_labels[b]:<10}{tag_b}"
            rows.append(f"{_fit(left, 22)}{_D}|{_A} {right}")
        else:
            rows.append(left)

    body = [
        f"{_W}Plan {_A}{plan}  {_D}|{_A} 260+ cmds  {_D}|{_A} prefix {_C}.{_A}",
        f"{_Y}BETA TEST{_A}  {_D}|{_A}  bugs possibles — feedback sur Discord",
        "",
        f"{_M}Navigation{_A}" + (f"  {_D}(* = VIP page){_A}" if locked else ""),
        *rows,
        "",
        f"{_M}Quick{_A}",
        f"{_C}.help <cmd>{_A}  {_C}.info{_A}  {_C}.theme{_A}  {_C}.reload{_A}",
    ]
    if vip_enabled:
        body[-1] = f"{_C}.help <cmd>{_A}  {_C}.info{_A}  {_C}.vip{_A}  {_C}.theme{_A}"
        body.append(f"{_C}.license{_A}  {_C}.reload{_A}")
    if locked:
        body.append(f"{_D}Unlock: ticket + .license key{_A}")
    body.append(f"{_C}discord.gg/voidv2{_A}  {_C}t.me/v0idtool{_A}")
    return discord_panel(f"{brand} {version}", body)

