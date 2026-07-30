"""Estadisticas de CPU, RAM y GPU con un backend por sistema.

Es la parte que ataba el panel a Linux: leia /proc y /sys directamente. Aqui se
aisla detras de una interfaz comun para que el panel sea igual en los tres.

CPU y RAM salen de psutil si esta disponible, y si no de /proc en Linux.
La GPU es el caso irregular: cada plataforma expone cosas distintas y algunas no
exponen nada, asi que se devuelve None y el panel lo pinta como "n/d" en vez de
inventar un numero.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import paths

try:
    import psutil
except ImportError:                      # opcional
    psutil = None


@dataclass
class Stats:
    cpu_pct: float | None = None
    cpu_temp: float | None = None
    ram_used_mb: int | None = None
    ram_total_mb: int | None = None
    gpu_pct: float | None = None
    gpu_temp: float | None = None
    vram_used_mb: int | None = None
    vram_total_mb: int | None = None


def _run(cmd: list[str], timeout: float = 2.0) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


# ── CPU y RAM ──────────────────────────────────────────────────────────────
class _CpuLinux:
    """Lectura directa de /proc/stat, por si no hay psutil."""

    def __init__(self) -> None:
        self._prev = (0, 0)

    def read(self) -> float | None:
        try:
            with open("/proc/stat") as f:
                parts = f.readline().split()
        except OSError:
            return None
        vals = [int(v) for v in parts[1:]]
        total, idle = sum(vals), vals[3] + vals[4]
        pt, pi = self._prev
        self._prev = (total, idle)
        dt, di = total - pt, idle - pi
        return None if dt <= 0 else 100.0 * (dt - di) / dt


_cpu_linux = _CpuLinux()


def _cpu_ram(st: Stats) -> None:
    if psutil is not None:
        st.cpu_pct = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        st.ram_total_mb = vm.total // 1048576
        st.ram_used_mb = (vm.total - vm.available) // 1048576
        return
    if paths.IS_LINUX:
        st.cpu_pct = _cpu_linux.read()
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k] = int(v.split()[0])
            st.ram_total_mb = info["MemTotal"] // 1024
            st.ram_used_mb = (info["MemTotal"] - info["MemAvailable"]) // 1024
        except (OSError, KeyError, ValueError):
            pass


# ── temperatura de CPU ─────────────────────────────────────────────────────
_HWMON: dict[str, Path] = {}


def _hwmon_scan() -> None:
    """Localiza una sola vez los sensores; sus indices no cambian en caliente."""
    base = Path("/sys/class/hwmon")
    if not base.exists():
        return
    for h in base.glob("hwmon*"):
        try:
            name = (h / "name").read_text().strip()
        except OSError:
            continue
        t = h / "temp1_input"
        if t.exists() and name in ("k10temp", "coretemp", "cpu_thermal", "zenpower"):
            _HWMON.setdefault("cpu", t)
        if t.exists() and name in ("amdgpu", "nouveau", "i915"):
            _HWMON.setdefault("gpu", t)


def _cpu_temp(st: Stats) -> None:
    if paths.IS_LINUX:
        if not _HWMON:
            _hwmon_scan()
        p = _HWMON.get("cpu")
        if p:
            try:
                st.cpu_temp = int(p.read_text()) / 1000
            except (OSError, ValueError):
                pass
        return
    if psutil is not None and hasattr(psutil, "sensors_temperatures"):
        try:
            for entries in psutil.sensors_temperatures().values():
                if entries:
                    st.cpu_temp = entries[0].current
                    return
        except Exception:
            pass


# ── GPU: un backend por plataforma ─────────────────────────────────────────
_AMD_DRM = Path("/sys/class/drm/card0/device")


def _gpu_amd_sysfs(st: Stats) -> bool:
    """AMD en Linux: uso y memoria via sysfs. Es el caso de la Legion Go S."""
    busy = _AMD_DRM / "gpu_busy_percent"
    if not busy.exists():
        return False
    try:
        st.gpu_pct = float(busy.read_text().strip())
        st.vram_used_mb = int((_AMD_DRM / "mem_info_vram_used").read_text()) // 1048576
        st.vram_total_mb = int((_AMD_DRM / "mem_info_vram_total").read_text()) // 1048576
    except (OSError, ValueError):
        return False
    if not _HWMON:
        _hwmon_scan()
    p = _HWMON.get("gpu")
    if p:
        try:
            st.gpu_temp = int(p.read_text()) / 1000
        except (OSError, ValueError):
            pass
    return True


def _gpu_nvidia(st: Stats) -> bool:
    """NVIDIA en Linux y Windows. Sin verificar en Windows todavia."""
    if not shutil.which("nvidia-smi"):
        return False
    out = _run(["nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits"])
    line = out.strip().split("\n")[0] if out.strip() else ""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 4:
        return False
    try:
        st.gpu_pct = float(parts[0])
        st.vram_used_mb = int(parts[1])
        st.vram_total_mb = int(parts[2])
        st.gpu_temp = float(parts[3])
    except ValueError:
        return False
    return True


def _gpu_macos(st: Stats) -> bool:
    """Apple Silicon: memoria unificada, no hay VRAM separada que reportar.

    El uso de GPU solo lo da powermetrics, que exige root, asi que se deja sin
    dato en vez de pedir privilegios para pintar una barra.
    """
    if not paths.IS_MAC:
        return False
    st.vram_total_mb = st.ram_total_mb
    st.vram_used_mb = None
    return True


def _gpu_windows(st: Stats) -> bool:
    """Windows sin NVIDIA. Pendiente de verificar en una maquina real."""
    if not paths.IS_WINDOWS:
        return False
    return False


def collect() -> Stats:
    st = Stats()
    _cpu_ram(st)
    _cpu_temp(st)
    for backend in (_gpu_amd_sysfs, _gpu_nvidia, _gpu_macos, _gpu_windows):
        try:
            if backend(st):
                break
        except Exception:
            continue
    return st


if __name__ == "__main__":
    import json

    collect()                            # ceba el delta de CPU
    import time

    time.sleep(0.5)
    print(json.dumps(collect().__dict__, indent=2))
