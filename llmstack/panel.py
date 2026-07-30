"""Panel en vivo del servidor: tokens, velocidad, CPU, GPU, RAM y VRAM.

Antes era bash leyendo /proc y /sys; ahora las estadisticas vienen de
sysinfo, que tiene un backend por sistema, y lo demas es igual en los tres.
Los datos del servidor salen de su endpoint /metrics, no de parsear el log.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request

R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
GRN = "\033[38;5;77m"; YEL = "\033[38;5;221m"; RED = "\033[38;5;203m"
CYA = "\033[38;5;80m"; MAG = "\033[38;5;176m"; GRY = "\033[38;5;244m"

BAR_FULL = "━" * 14
BAR_EMPTY = "─" * 14
SPIN = "|/-\\"          # ASCII: los glifos braille no estan en todas las fuentes
RULE = "─" * 66


def bar(pct: float | None, width: int = 14) -> str:
    if pct is None:
        return f"{GRY}{'·' * width}{R}"
    p = max(0, min(100, int(pct)))
    f = p * width // 100
    c = RED if p >= 85 else YEL if p >= 60 else GRN
    return f"{c}{BAR_FULL[:f]}{GRY}{BAR_EMPTY[:width - f]}{R}"


def _fmt(v, unit="", nd=0):
    return "n/d" if v is None else f"{v:.{nd}f}{unit}"


class Metrics:
    """Lee el endpoint Prometheus del servidor. Sin dependencias externas."""

    def __init__(self, url: str, key: str):
        self.url, self.key = url, key
        self.gen = self.prompt = 0
        self.tps = self.pps = 0.0
        self.active = 0
        self.served = 0
        self._prev_active = 0

    def poll(self) -> None:
        req = urllib.request.Request(
            self.url, headers={"Authorization": f"Bearer {self.key}"})
        try:
            with urllib.request.urlopen(req, timeout=1) as r:
                body = r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError, TimeoutError):
            return
        vals = {}
        for line in body.splitlines():
            if line.startswith("llamacpp:"):
                try:
                    k, v = line[9:].split(None, 1)
                    vals[k] = float(v)
                except ValueError:
                    continue
        self.gen = int(vals.get("tokens_predicted_total", self.gen))
        self.prompt = int(vals.get("prompt_tokens_total", self.prompt))
        self.tps = vals.get("predicted_tokens_seconds", self.tps)
        self.pps = vals.get("prompt_tokens_seconds", self.pps)
        act = int(vals.get("requests_processing", 0))
        if self._prev_active > 0 and act == 0:
            self.served += self._prev_active
        self._prev_active = act
        self.active = act


_LIVE = re.compile(r"n_decoded\s*=\s*(\d+), tg\s*=\s*([\d.]+)")


def tail_progress(log_path, tail_bytes: int = 8192) -> tuple[int, float] | None:
    """Ultimo progreso de generacion que el servidor haya escrito en el log."""
    try:
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - tail_bytes))
            chunk = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    hits = _LIVE.findall(chunk)
    if not hits:
        return None
    n, tg = hits[-1]
    return int(n), float(tg)


def tail_lines(log_path, n: int = 6, width: int = 66) -> list[str]:
    try:
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 8192))
            raw = f.read().decode("utf-8", "replace")
    except OSError:
        return []
    out, prev = [], None
    for line in raw.splitlines():
        line = re.sub(r"^[\d.]+ [A-Z] ", "", line).rstrip()
        if not line or line == prev:
            continue
        prev = line
        out.append(line[:width])
    return out[-n:]


def render(*, name, tag, ctx, port, ip, key, ready, uptime, stats, met,
           live, clients, exit_hint, tick) -> str:
    a = ["\033[H"]
    status = f"{GRN}● ACTIVO{R}" if ready else f"{YEL}◐ CARGANDO MODELO{R}"
    h, rem = divmod(int(uptime), 3600)
    m, s = divmod(rem, 60)
    a.append(f"\n  {B}{MAG}{name}{R} {D}{tag} · {ctx // 1024}K ctx{R}  {status}"
             f"  {GRY}up {h:02d}:{m:02d}:{s:02d}{R}\n")
    a.append(f"  {GRY}{RULE}{R}\n")
    a.append(f"   {GRY}API{R}     {CYA}{B}http://{ip}:{port}/v1{R}  {D}(OpenAI-compatible){R}\n")
    a.append(f"   {GRY}WebUI{R}   {CYA}http://{ip}:{port}{R}\n")
    a.append(f"   {GRY}Key{R}     {D}{key}{R}\n")
    a.append(f"  {GRY}{RULE}{R}\n")

    ram_pct = (100 * stats.ram_used_mb / stats.ram_total_mb) if stats.ram_total_mb else None
    vram_pct = (100 * stats.vram_used_mb / stats.vram_total_mb) if stats.vram_total_mb and stats.vram_used_mb else None
    a.append(f"   {GRY}CPU {R}  {bar(stats.cpu_pct)}  {_fmt(stats.cpu_pct, '%'):>5}"
             f"   {D}{_fmt(stats.cpu_temp, '°C')}{R}\n")
    a.append(f"   {GRY}GPU {R}  {bar(stats.gpu_pct)}  {_fmt(stats.gpu_pct, '%'):>5}"
             f"   {D}{_fmt(stats.gpu_temp, '°C')}{R}\n")
    a.append(f"   {GRY}RAM {R}  {bar(ram_pct)}  {_fmt(ram_pct, '%'):>5}"
             f"   {D}{stats.ram_used_mb or '?'} / {stats.ram_total_mb or '?'} MB{R}\n")
    if stats.vram_total_mb:
        vu = stats.vram_used_mb if stats.vram_used_mb is not None else "compartida"
        a.append(f"   {GRY}VRAM{R}  {bar(vram_pct)}  {_fmt(vram_pct, '%'):>5}"
                 f"   {D}{vu} / {stats.vram_total_mb} MB{R}\n")
    a.append(f"  {GRY}{RULE}{R}\n")

    a.append(f"   {GRY}req{R}   activas {B}{YEL}{met.active}{R} · atendidas {B}{met.served}{R}"
             f"   {GRY}gen{R} {GRN}{met.tps:.2f} t/s{R} {D}prompt {met.pps:.1f} t/s{R}\n")
    a.append(f"   {GRY}tok{R}   prompt {D}{met.prompt}{R} · generados {D}{met.gen}{R}\n")
    if met.active and live:
        a.append(f"   {YEL}{SPIN[tick % 4]} generando{R}  {B}{GRN}{live[0]} tokens{R}"
                 f"  {GRY}a {live[1]:.2f} t/s{R}{'':18}\n")
    else:
        a.append(f"   {D}· en reposo{R}{'':46}\n")
    a.append(f"   {GRY}red{R}   {CYA}{(clients or 'sin clientes conectados')[:56]:<56}{R}\n")
    a.append(f"  {GRY}{RULE}{R}\n")
    return "".join(a)
