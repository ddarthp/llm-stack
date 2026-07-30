"""Menu de seleccion de modelo.

Un solo icono y un solo puerto: eliges modelo, arranca, y al pararlo vuelves
aqui para cambiar sin salir. Pensado para funcionar sin teclado en Modo Juego.
"""
from __future__ import annotations

import os
import select
import signal
import struct
import subprocess
import sys
import time

from . import config, paths, runner

R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
GRN = "\033[38;5;77m"; YEL = "\033[38;5;221m"; RED = "\033[38;5;203m"
CYA = "\033[38;5;80m"; MAG = "\033[38;5;176m"; GRY = "\033[38;5;244m"

PORT = os.environ.get("LLM_PORT", "8090")
AUTOSTART = int(os.environ.get("LLM_AUTOSTART", "15"))


class Pads:
    """Mandos via /dev/input/js*, solo en Linux.

    En macOS y Windows no existe ese interfaz; ahi el menu funciona con teclado
    y con la cuenta atras. Portarlo pasaria por pygame o por las APIs nativas.
    """

    def __init__(self) -> None:
        self.fds: list[int] = []
        if not paths.IS_LINUX:
            return
        for n in range(8):
            try:
                self.fds.append(os.open(f"/dev/input/js{n}", os.O_RDONLY | os.O_NONBLOCK))
            except OSError:
                pass
        self._last = 0.0

    def poll(self) -> str | None:
        if not self.fds:
            return None
        r, _, _ = select.select(self.fds, [], [], 0)
        for fd in r:
            while True:
                try:
                    data = os.read(fd, 8)
                except (BlockingIOError, OSError):
                    break
                if len(data) != 8:
                    break
                _, val, typ, num = struct.unpack("<IhBB", data)
                if typ & 0x80:
                    continue
                if typ & 0x01 and val == 1:
                    if num == 0:
                        return "ok"
                    if num == 1:
                        return "back"
                elif typ & 0x02 and num in (1, 7) and abs(val) > 16000:
                    now = time.time()
                    if now - self._last < 0.25:
                        continue
                    self._last = now
                    return "up" if val < 0 else "down"
        return None

    def close(self) -> None:
        for fd in self.fds:
            try:
                os.close(fd)
            except OSError:
                pass


def read_key(timeout: float) -> str | None:
    if os.name == "nt":                       # Windows: consola, no termios
        import msvcrt
        end = time.time() + timeout
        while time.time() < end:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):    # tecla extendida (flechas)
                    return {"H": "up", "P": "down"}.get(msvcrt.getwch())
                return _map_char(ch)
            time.sleep(0.02)
        return None
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    if not r:
        return None
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        r, _, _ = select.select([sys.stdin], [], [], 0.05)
        if r:
            return {"[A": "up", "[B": "down"}.get(sys.stdin.read(2))
        return "back"
    return _map_char(ch)


def _map_char(ch: str) -> str | None:
    low = ch.lower()
    if low in ("w", "k"):
        return "up"
    if low in ("s", "j"):
        return "down"
    if ch in ("\r", "\n", " "):
        return "ok"
    if low == "q":
        return "back"
    if ch.isdigit():
        return f"#{ch}"
    return None


def draw(models, sel, remaining, pads_ok, busy) -> None:
    out = ["\033[H\033[J",
           f"\n  {B}{MAG}MODELOS LOCALES{R}   {D}puerto {PORT} para todos{R}\n",
           f"  {GRY}{'─' * 66}{R}\n"]
    for i, m in enumerate(models):
        cur = i == sel
        falta = "" if m.installed() else f"  {RED}(sin descargar){R}"
        name = f"{B}{CYA}{m.name}{R}" if cur else f"{GRY}{m.name}{R}"
        bullet = f"{GRN}▸{R}" if cur else " "
        out.append(f"\n   {bullet} {name}   {D}{m.specs()}{R}{falta}\n")
        out.append(f"     {D}{m.tag}{R}\n")
        if cur and m.note:
            out.append(f"     {GRY}{m.note}{R}\n")
    out.append(f"\n  {GRY}{'─' * 66}{R}\n")
    if busy:
        out.append(f"\n  {RED}El puerto {PORT} ya esta ocupado por otro proceso.{R}\n")
    elif remaining is not None:
        out.append(f"\n  {YEL}Arrancando {models[sel].name} en {remaining}s…{R}"
                   f"  {D}(pulsa algo para elegir){R}\n")
    else:
        out.append("\n")
    ctrl = "cruceta  A elegir  B salir" if pads_ok else "flechas  Enter elegir  Q salir"
    if os.environ.get("LLM_EXIT_HINT"):
        ctrl += f"   ·   salir del todo: {os.environ['LLM_EXIT_HINT']}"
    out.append(f"  {D}{ctrl}{R}\033[J")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def launch(m) -> None:
    os.system("cls" if os.name == "nt" else "clear")
    prev = signal.signal(signal.SIGINT, signal.SIG_IGN)
    child = subprocess.Popen([sys.executable, "-m", "llmstack", m.key],
                             cwd=str(paths.repo_root()))
    try:
        child.wait()
    finally:
        signal.signal(signal.SIGINT, prev)


def main() -> int:
    models = config.load_all()
    if not models:
        print("no hay modelos definidos en models/*/model.toml", file=sys.stderr)
        return 1
    sel = 0
    st = paths.state_file()
    if st.is_file():
        last = st.read_text(encoding="utf-8").strip()
        sel = next((i for i, m in enumerate(models) if m.key == last), 0)

    pads = Pads()
    raw_ok = False
    old = None
    if os.name != "nt":
        import termios, tty
        try:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            raw_ok = True
        except (termios.error, ValueError):
            pass
    else:
        raw_ok = True

    sys.stdout.write("\033[?25l")
    deadline = time.time() + AUTOSTART if AUTOSTART > 0 else None
    try:
        while True:
            busy = runner.port_in_use(int(PORT))
            remaining = None
            if deadline and not busy:
                remaining = max(0, int(deadline - time.time()))
                if remaining == 0:
                    launch(models[sel])
                    deadline = None
                    continue
            draw(models, sel, remaining, bool(pads.fds), busy)

            ev = pads.poll()
            if ev is None and raw_ok:
                ev = read_key(0.15)
            elif ev is None:
                time.sleep(0.15)
            if ev is None:
                continue
            deadline = None
            if ev == "up":
                sel = (sel - 1) % len(models)
            elif ev == "down":
                sel = (sel + 1) % len(models)
            elif ev.startswith("#"):
                i = int(ev[1:]) - 1
                if 0 <= i < len(models):
                    sel, ev = i, "ok"
            if ev == "ok" and not busy:
                st.parent.mkdir(parents=True, exist_ok=True)
                st.write_text(models[sel].key, encoding="utf-8")
                launch(models[sel])
            elif ev == "back":
                break
    finally:
        sys.stdout.write("\033[?25h\n")
        if old is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
        pads.close()
    return 0
