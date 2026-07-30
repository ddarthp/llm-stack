"""Rutas por sistema operativo.

Nada de rutas fijas: todo se deriva de donde esta el repositorio y de la carpeta
de datos que corresponde a cada sistema. Se puede forzar con LLM_DATA_DIR.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

SYSTEM = platform.system()          # 'Linux' | 'Darwin' | 'Windows'
IS_LINUX = SYSTEM == "Linux"
IS_MAC = SYSTEM == "Darwin"
IS_WINDOWS = SYSTEM == "Windows"


def repo_root() -> Path:
    """Raiz del repositorio, deducida de la ubicacion de este fichero."""
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Donde viven pesos, binarios, logs y estado. Configurable y por sistema."""
    env = os.environ.get("LLM_DATA_DIR")
    if env:
        return Path(env).expanduser()
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "llm-stack"
    if IS_MAC:
        return Path.home() / "Library" / "Application Support" / "llm-stack"
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "llm-stack"


def models_dir() -> Path:
    return data_dir() / "models"


def runtime_dir() -> Path:
    """Binarios de llama.cpp, uno por backend (vulkan, cuda, metal, cpu...)."""
    return data_dir() / "runtimes"


def logs_dir() -> Path:
    return data_dir() / "logs"


def key_file() -> Path:
    return data_dir() / "apikey"


def state_file() -> Path:
    return data_dir() / "last"


def server_binary(runtime: Path) -> Path:
    exe = "llama-server.exe" if IS_WINDOWS else "llama-server"
    for cand in (runtime / exe, runtime / "bin" / exe):
        if cand.exists():
            return cand
    return runtime / exe


def library_path_var() -> str:
    """Nombre de la variable de rutas de bibliotecas segun el sistema."""
    if IS_WINDOWS:
        return "PATH"
    if IS_MAC:
        return "DYLD_LIBRARY_PATH"
    return "LD_LIBRARY_PATH"


def ensure_dirs() -> None:
    for d in (data_dir(), models_dir(), runtime_dir(), logs_dir()):
        d.mkdir(parents=True, exist_ok=True)


def lan_ip() -> str:
    """IP de este equipo en la red local, sin depender de comandos externos."""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))      # no envia nada, solo elige la interfaz
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    print(f"sistema      : {SYSTEM}")
    print(f"repositorio  : {repo_root()}")
    print(f"datos        : {data_dir()}")
    print(f"modelos      : {models_dir()}")
    print(f"runtimes     : {runtime_dir()}")
    print(f"variable libs: {library_path_var()}")
    print(f"IP local     : {lan_ip()}")
    sys.exit(0)
