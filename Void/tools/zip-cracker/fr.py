import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import os
import time
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

_VOID = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _VOID not in sys.path:
    sys.path.insert(0, _VOID)

from lib import constants as C
from lib.void_common import open_premium_links

_ZIP_DIR = os.path.dirname(os.path.abspath(__file__))
if _ZIP_DIR not in sys.path:
    sys.path.insert(0, _ZIP_DIR)
import engine as zip_engine

crack_worker = zip_engine.crack_worker
is_encrypted = zip_engine.is_encrypted
load_passwords = zip_engine.load_passwords
load_passwords_from_dir = zip_engine.load_passwords_from_dir
reset_search = zip_engine.reset_search
stats = zip_engine.stats
stop_search = zip_engine.stop_search


def _password_found():
    return zip_engine.password_found

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

try:
    from tkinter import Tk, filedialog
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

console = Console()

ASCII = r"""
   ███████╗██╗██████╗      ██████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗ 
   ╚══███╔╝██║██╔══██╗    ██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
     ███╔╝ ██║██████╔╝    ██║     ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝
    ███╔╝  ██║██╔═══╝     ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
   ███████╗██║██║         ╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
   ╚══════╝╚═╝╚═╝          ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
"""

SUBTITLE = " V O I D   Z I P   -   B R U T E F O R C E   S Y S T E M   V 2 "


def boot():
    if sys.platform.startswith("win"):
        os.system("title VOID ZIP // BRUTEFORCE ENGINE")
    os.system("cls" if os.name == "nt" else "clear")
    sys.stdout.write("\033[?25l")
    lines = ASCII.strip("\n").split("\n")
    t0 = time.time()
    try:
        while time.time() - t0 < 1.4:
            t = time.time() - t0
            sys.stdout.write("\033[H\n")
            for line in lines:
                sys.stdout.write("  ")
                for c, ch in enumerate(line):
                    if ch == " ":
                        sys.stdout.write(" ")
                    else:
                        v = max(40, min(255, int(100 + 155 * math.sin(t * 10 - c * 0.2))))
                        sys.stdout.write(f"\033[38;2;{v};0;0m{ch}")
                sys.stdout.write("\033[0m\n")
            sys.stdout.write(f"\n  \033[38;2;80;0;0m{SUBTITLE}\033[0m\n")
            sys.stdout.flush()
            time.sleep(0.025)
    finally:
        sys.stdout.write("\033[?25h\033[0m")
    os.system("cls" if os.name == "nt" else "clear")


def ask_file():
    if TK_AVAILABLE and os.name == "nt":
        try:
            root = Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            f = filedialog.askopenfilename(
                title="VOID-TOOLS - Select ZIP file",
                filetypes=[("ZIP Archives", "*.zip"), ("All files", "*.*")],
            )
            root.destroy()
            return f
        except Exception:
            pass
    console.print("\n [bold red]┌─[[/][bold white] Chemin du fichier cible (.zip) [/][bold red]][/]")
    return console.input(" [bold red]└─▶[/] [bold white]").strip().strip('"')


def premium_screen():
    os.system("cls")
    with Progress(
        SpinnerColumn(spinner_name="dots2", style="gold1"),
        TextColumn("[bold gold1]VÉRIFICATION DE LA LICENCE..."),
        console=console,
        transient=True,
    ) as p:
        p.add_task("", total=None)
        time.sleep(2)

    console.print("\n" * 2)
    pnl = Panel(
        Align.center(Group(
            Text.from_markup("\n[bold #FFD700]DÉSOLÉ ! ACCÈS RÉSERVÉ[/]"),
            Text.from_markup(
                "\n[white]L'option [bold #FFD700]RAR CRACKER[/] est un module avancé\n"
                "nécessitant une licence [bold #FFD700]VOID PREMIUM[/]."
            ),
            Text.from_markup("\n[dim]Shop · Discord[/]"),
            Text.from_markup(f"\n[bold #5865F2]{C.SHOP}[/]"),
            Text.from_markup(f"\n[dim #5865F2]{C.DISCORD}[/]"),
            Text.from_markup("\n[dim white]Ouverture shop + Discord...[/]"),
        )),
        border_style="#FFD700",
        box=box.DOUBLE_EDGE,
        padding=(1, 5),
        title="[bold #FFD700]LICENSE_MISSING_ERROR",
    )
    console.print(Align.center(pnl))
    open_premium_links()
    console.print("\n")


def run_dictionary_attack(filepath, passwords, workers):
    if not is_encrypted(filepath):
        console.print("\n [bold yellow][!][/] Ce ZIP ne semble pas protégé par mot de passe.")
        ans = console.input(" [bold red]└─▶[/] [white]Continuer quand même ? (o/n) >> ").strip().lower()
        if ans not in ("o", "oui", "y", "yes"):
            return

    reset_search()
    chunk_size = max(100, len(passwords) // max(workers * 4, 1))
    chunks = [passwords[i:i + chunk_size] for i in range(0, len(passwords), chunk_size)]

    with Progress(
        SpinnerColumn(spinner_name="point", style="red"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(complete_style="red", bar_width=40),
        TextColumn("[bold red]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Initialisation...", total=len(passwords))

        def advance(n=1):
            progress.advance(task, n)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(crack_worker, filepath, chunk, advance)
                for chunk in chunks
            ]
            while any(not f.done() for f in futures) and not stop_search.is_set():
                cur = stats["current_pwd"][:24]
                progress.update(
                    task,
                    description=(
                        f"Cracking {stats['tested']}/{len(passwords)} "
                        f"({int(stats['speed'])}/s) · {cur}"
                    ),
                )
                time.sleep(0.08)
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass


def main():
    boot()

    console.print(Align.center(Panel(
        Text.from_markup(
            "[bold red]VOID-TOOLS[/]  [dim]//[/]  [white]BRUTEFORCE ENGINE[/]  "
            "[dim]//[/]  [red]ZIP CRACKER[/]"
        ),
        border_style="red",
        padding=(0, 6),
    )))
    console.print()

    filepath = ask_file()
    if not filepath or not os.path.exists(filepath):
        console.print("\n [bold red][x][/] Aucun fichier sélectionné.")
        time.sleep(2)
        return

    if not zipfile_is_valid(filepath):
        console.print("\n [bold red][x][/] Fichier ZIP invalide ou corrompu.")
        time.sleep(2)
        return

    console.print(f"\n [dim]Cible :[/] [bold white]{os.path.basename(filepath)}[/]")
    console.print(Panel(
        Group(
            Text.from_markup(" [bold red]01  » [/][bold white]Attaque par Dictionnaire (Combolist)"),
            Text.from_markup(" [bold red]02  » [/][bold white]Bruteforce Aléatoire"),
            Text.from_markup(" [bold #FFD700]07  » [/][bold #FFD700]RAR Cracker [PREMIUM]"),
        ),
        title="[bold red]MODULES D'ATTAQUE",
        border_style="red",
        box=box.ROUNDED,
        padding=(1, 2),
    ))

    choice = console.input("\n [bold red]└─▶[/] [bold white]choix >> ").strip()

    if choice == "7":
        premium_screen()
        return
    if choice == "2":
        console.print("\n [bold red][!][/] Option en cours de développement.")
        time.sleep(2)
        return
    if choice != "1":
        return

    passwords = load_passwords()
    if not passwords:
        custom = console.input("\n [bold red]└─▶[/] [white]Dossier combolist >> ").strip().strip('"')
        passwords = load_passwords_from_dir(custom)
    if not passwords:
        console.print("\n [bold red][x][/] Aucune combolist chargée.")
        console.print(f" [dim]Place des .txt dans:[/] [white]{C.COMBOLIST_DIR}[/]")
        time.sleep(2)
        return

    console.print(f"\n [bold green][✓][/] {len(passwords)} mots de passe chargés.")

    default_threads = min(32, (os.cpu_count() or 4) + 4)
    console.print(
        f" [bold red]┌─[[/][bold white] Threads (1-100) [/][bold red]][/] "
        f"[dim](Défaut: {default_threads})[/]"
    )
    t_input = console.input(" [bold red]└─▶[/] [bold white]").strip()
    try:
        workers = max(1, min(100, int(t_input)))
    except ValueError:
        workers = default_threads

    run_dictionary_attack(filepath, passwords, workers)

    console.print()
    if _password_found():
        console.print(Panel(
            Align.center(Text.from_markup(
                f"[bold green]SUCCESS: PASSWORD CAPTURED[/]\n\n[bold #00FF00]{_password_found()}"
            )),
            border_style="green",
            box=box.HEAVY,
            padding=(1, 4),
        ))
    else:
        console.print(" [bold red][x][/] Échec : mot de passe introuvable dans la wordlist.")
    time.sleep(2)


def zipfile_is_valid(filepath):
    import zipfile
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            if not zf.namelist():
                return False
            if is_encrypted(filepath):
                return True
            return zf.testzip() is None
    except zipfile.BadZipFile:
        return False
    except Exception:
        return False


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_search.set()
        console.print("\n [bold red][!][/] Interrompu.")
