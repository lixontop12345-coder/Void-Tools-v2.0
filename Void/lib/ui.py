"""Dashboard UI — Rich panels, theme colors, no blink."""
import math
import time

from rich.align import Align
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from rich import box

from . import constants as C
from .void_common import count_free_premium, fmt_label, is_premium


def _phase():
    return (time.time() * 0.25) % 1.0 if C.is_rainbow() else 0.0


def _lerp_hex(c1, c2, t):
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _breath(t=None):
    if t is None:
        t = time.time()
    return (math.sin(t * 2.4) + 1.0) / 2.0


def make_online_text(phase=None, breath=None):
    """Indicateur ONLINE — pulsation respiration (couleur + point)."""
    t = time.time()
    breath = _breath(t) if breath is None else breath
    phase = _phase() if phase is None else phase
    pal = C.palette(phase)
    color = _lerp_hex(C.C_DIM, pal["neon"], 0.05 + 0.95 * breath)
    dot = "●" if breath >= 0.5 else "○"
    bold = breath >= 0.55
    dim = breath < 0.3
    txt = Text()
    txt.append(f"{dot} ", style=Style(color=color, bold=bold, dim=dim))
    txt.append("ONLINE", style=Style(color=color, bold=bold, dim=dim))
    return txt


def make_title_text(text="VOID-TOOLS", phase=None):
    phase = _phase() if phase is None else phase
    txt = Text()
    if C.is_rainbow():
        for i, char in enumerate(text):
            txt.append(char, style=C.rainbow_hex(phase + i * 0.045))
        return txt
    p = C.palette(phase)
    for i, char in enumerate(text):
        c = p["neon"] if i % 2 == 0 else p["bright"]
        txt.append(char, style=c)
    return txt


def make_card_cell(key, label, is_selected, phase=None):
    if not key or not str(key).strip() or key == "  ":
        return Text("")

    phase = _phase() if phase is None else phase
    p = C.palette(phase)
    prem = is_premium(label)
    gold = p["neon"] if C.is_rainbow() else C.C_GOLD
    gold2 = p["bright"] if C.is_rainbow() else C.C_GOLD2
    dim = p["dark"] if C.is_rainbow() else C.C_DIM
    white = p["bright"] if C.is_rainbow() else C.C_WHITE
    color = p["neon"] if is_selected else (gold if prem else p["blood"])
    border = C.C_WHITE if is_selected else (gold if prem else dim)
    style = p["neon"] if is_selected else (gold2 if prem else white)
    text = fmt_label(label, max_len=26)
    inner = Text.from_markup(
        f"[{style} bold] {text} [/]" if is_selected else f"   [{style}]{text}[/]   "
    )
    return Panel(
        Align.center(inner),
        title=f"[{color} bold]{key}[/]",
        title_align="left",
        border_style=border,
        box=box.HEAVY if is_selected else box.ROUNDED,
        padding=(1, 1),
    )


def monitor_block(cat_label, n_tools, items, username, nuker=(False, False), remote_badge="", phase=None):
    from .i18n import t

    phase = _phase() if phase is None else phase
    p = C.palette(phase)
    gold = p["neon"] if C.is_rainbow() else C.C_GOLD
    gold2 = p["bright"] if C.is_rainbow() else C.C_GOLD2
    silver = p["bright"] if C.is_rainbow() else C.C_SILVER
    free, prem = count_free_premium(items)
    tok = "OK" if nuker[0] else "--"
    srv = "OK" if nuker[1] else "--"
    user = (username or "Op")[:14]
    cat = (cat_label or "?")[:12]
    badge = f"│ [{gold} bold]! {remote_badge}[/]\n" if remote_badge else ""
    return Text.from_markup(
        f"\n\n[{p['blood']}]┌─ MONITOR\n"
        f"{badge}"
        f"│ [bold {p['neon']}]{user}[/]\n"
        f"│ [{gold}]{free}[/] {t('free', 'free')} · [{gold2}]{prem}[/] vip\n"
        f"│ NUKER {tok}/{srv}\n"
        f"│ [{silver}]{cat}[/] · [{gold}]{n_tools}[/] {t('outils', 'tools')}\n"
        f"└─ [{p['neon']}]{t('PRÊT', 'READY')}[/]"
    )
