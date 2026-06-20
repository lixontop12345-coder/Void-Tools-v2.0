"""ZIP dictionary cracker — shared engine."""
import os
import threading
import time
import zipfile

try:
    import pyzipper
except ImportError:
    pyzipper = None

from lib import constants as C

password_found = None
stop_search = threading.Event()
stats = {"tested": 0, "speed": 0, "start_time": 0, "current_pwd": "..."}
_stats_lock = threading.Lock()


def _target_names(zf):
    names = [n for n in zf.namelist() if n and not n.endswith("/")]
    return names or [n for n in zf.namelist() if n][:1]


def is_encrypted(filepath):
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            for info in zf.infolist():
                if info.flag_bits & 0x1:
                    return True
    except Exception:
        pass
    if pyzipper:
        try:
            with pyzipper.AESZipFile(filepath, "r") as zf:
                for info in zf.infolist():
                    if info.flag_bits & 0x1:
                        return True
        except Exception:
            pass
    return False


def _try_password(filepath, password):
    pwd = password.encode("utf-8", errors="ignore")
    classes = [zipfile.ZipFile]
    if pyzipper:
        classes.insert(0, pyzipper.AESZipFile)
    for cls in classes:
        try:
            with cls(filepath, "r") as zf:
                targets = _target_names(zf)
                if not targets:
                    return False
                for name in targets:
                    with zf.open(name, "r", pwd=pwd) as fp:
                        fp.read(1)
            return True
        except Exception:
            continue
    return False


def crack_worker(filepath, passwords_chunk, advance_cb=None):
    global password_found
    for pwd in passwords_chunk:
        if stop_search.is_set():
            return
        with _stats_lock:
            stats["current_pwd"] = pwd
        if _try_password(filepath, pwd):
            password_found = pwd
            stop_search.set()
            return
        with _stats_lock:
            stats["tested"] += 1
            elapsed = time.time() - stats["start_time"]
            if elapsed > 0:
                stats["speed"] = stats["tested"] / elapsed
        if advance_cb:
            advance_cb(1)


def ensure_combolists():
    os.makedirs(C.COMBOLIST_DIR, exist_ok=True)
    sample = os.path.join(C.COMBOLIST_DIR, "common.txt")
    if not os.path.isfile(sample):
        with open(sample, "w", encoding="utf-8") as f:
            f.write("\n".join([
                "password", "123456", "12345678", "1234", "qwerty", "admin",
                "letmein", "welcome", "monkey", "dragon", "master", "000000", "abc123",
            ]))


def load_passwords():
    ensure_combolists()
    legacy = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "Void - Input", "Combolist")
    )
    dirs = [d for d in (legacy, C.COMBOLIST_DIR) if os.path.isdir(d)] or [C.COMBOLIST_DIR]
    passwords = set()
    for combolist_dir in dirs:
        for f_name in os.listdir(combolist_dir):
            file_path = os.path.join(combolist_dir, f_name)
            if not os.path.isfile(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            passwords.add(line)
            except Exception:
                pass
    return list(passwords)


def load_passwords_from_dir(folder):
    out = set()
    if not folder or not os.path.isdir(folder):
        return []
    for f_name in os.listdir(folder):
        file_path = os.path.join(folder, f_name)
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        out.add(line)
        except Exception:
            pass
    return list(out)


def reset_search():
    global password_found
    password_found = None
    stop_search.clear()
    stats["tested"] = 0
    stats["speed"] = 0
    stats["start_time"] = time.time()
    stats["current_pwd"] = "..."
