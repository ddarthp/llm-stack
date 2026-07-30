#!/usr/bin/env python3
"""Instalador: detecta el sistema, baja el llama.cpp adecuado y los pesos.

    python3 install.py                 muestra que hay y que falta
    python3 install.py --runtime       instala solo el runtime detectado
    python3 install.py qwen-a1         instala el runtime y los pesos de un modelo
    python3 install.py --all           todos los modelos (decenas de GB)
    python3 install.py --backend cpu   fuerza un backend en vez de autodetectar

Descarga con reanudacion y verifica el tamano contra la API de Hugging Face.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llmstack import config, paths          # noqa: E402

HF = "https://huggingface.co"
GH_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"

# Sufijo del asset de llama.cpp por (sistema, backend).
ASSETS = {
    ("Linux", "vulkan"): "bin-ubuntu-vulkan-x64.tar.gz",
    ("Linux", "cuda"): "bin-ubuntu-cuda",          # coincide por prefijo
    ("Linux", "rocm"): "bin-ubuntu-rocm",
    ("Linux", "cpu"): "bin-ubuntu-x64.tar.gz",
    ("Darwin", "metal"): "bin-macos-arm64.zip",
    ("Darwin", "cpu"): "bin-macos-x64.zip",
    ("Windows", "vulkan"): "bin-win-vulkan-x64.zip",
    ("Windows", "cuda"): "bin-win-cuda",
    ("Windows", "cpu"): "bin-win-cpu-x64.zip",
}


def detect_backend() -> str:
    """Elige backend por lo que haya instalado, no por lo que la GPU soporte."""
    if paths.IS_MAC:
        import platform
        return "metal" if platform.machine() == "arm64" else "cpu"
    if shutil.which("nvidia-smi"):
        return "cuda"
    if paths.IS_LINUX and Path("/opt/rocm").exists():
        return "rocm"
    if shutil.which("vulkaninfo") or shutil.which("vulkaninfoSDK"):
        return "vulkan"
    if paths.IS_WINDOWS:
        return "vulkan"          # el runtime de Vulkan viene con los drivers
    return "cpu"


def _get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def download(url: str, dest: Path, expected: int | None = None) -> None:
    """Descarga con reanudacion y barra de progreso."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    have = dest.stat().st_size if dest.exists() else 0
    if expected and have == expected:
        print(f"    ya estaba completo ({have / 1e9:.2f} GB)")
        return
    headers = {"Range": f"bytes={have}-"} if have else {}
    req = urllib.request.Request(url, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        if e.code == 416:                     # ya estaba entero
            return
        raise
    total = int(r.headers.get("Content-Length", 0)) + have
    mode = "ab" if have and r.status == 206 else "wb"
    if mode == "wb":
        have = 0
    done = have
    with open(dest, mode) as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = 100 * done / total
                sys.stdout.write(f"\r    {pct:5.1f}%  {done / 1e9:.2f} / {total / 1e9:.2f} GB")
                sys.stdout.flush()
    print()
    if expected and dest.stat().st_size != expected:
        raise SystemExit(f"    tamano incorrecto: {dest.stat().st_size} != {expected}")


def hf_sizes(repo: str) -> dict[str, int]:
    data = json.loads(_get(f"{HF}/api/models/{repo}/tree/main"))
    return {f["path"]: (f.get("lfs") or {}).get("size") or f.get("size") or 0
            for f in data}


def install_runtime(backend: str, name: str = "llamacpp") -> Path:
    dest = paths.runtime_dir() / name
    if paths.server_binary(dest).is_file():
        print(f"  runtime '{name}' ya instalado")
        return dest
    key = (paths.SYSTEM, backend)
    if key not in ASSETS:
        raise SystemExit(f"no hay build conocida para {paths.SYSTEM} + {backend}")
    rel = json.loads(_get(GH_API, {"Accept": "application/vnd.github+json"}))
    want = ASSETS[key]
    asset = next((a for a in rel["assets"] if want in a["name"]), None)
    if asset is None:
        raise SystemExit(f"la release {rel['tag_name']} no trae un asset '{want}'")
    print(f"  llama.cpp {rel['tag_name']} · {asset['name']}")
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / asset["name"]
        download(asset["browser_download_url"], pkg)
        dest.mkdir(parents=True, exist_ok=True)
        if pkg.suffix == ".zip":
            with zipfile.ZipFile(pkg) as z:
                z.extractall(dest)
        else:
            with tarfile.open(pkg) as t:
                t.extractall(dest, filter="data")
    # Las releases meten todo bajo build/bin o similar: se aplana.
    exe = next((p for p in dest.rglob("llama-server*") if p.is_file()), None)
    if exe and exe.parent != dest:
        for f in exe.parent.iterdir():
            shutil.move(str(f), dest / f.name)
    for p in dest.rglob("llama-*"):
        if p.is_file():
            p.chmod(0o755)
    print(f"  instalado en {dest}")
    return dest


def install_model(m: config.Model) -> None:
    if not m.download_repo:
        print(f"  {m.name}: sin origen de descarga declarado, saltado")
        return
    print(f"\n== {m.name} ==")
    if m.runtime == "llamacpp-prismml":
        print("  ATENCION: este modelo necesita el fork de PrismML, que no se")
        print("  descarga automaticamente. Ver models/bonsai/README.md")
        return
    sizes = hf_sizes(m.download_repo)
    for fname in m.download_files:
        exp = sizes.get(fname)
        dest = m.dir / fname
        print(f"  {fname}  ({(exp or 0) / 1e9:.2f} GB)")
        download(f"{HF}/{m.download_repo}/resolve/main/{fname}?download=true", dest, exp)


def status() -> None:
    print(f"sistema : {paths.SYSTEM}")
    print(f"backend : {detect_backend()}")
    print(f"datos   : {paths.data_dir()}\n")
    for m in config.load_all():
        rt = paths.server_binary(m.runtime_path).is_file()
        print(f"  {'OK ' if m.installed() else '-- '} {m.name:15s} "
              f"{m.specs():42s} runtime:{'si' if rt else 'NO'}")
    print("\ninstala uno con:  python3 install.py <clave>")
    print("claves:", ", ".join(m.key for m in config.load_all()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="*", help="claves de modelo a instalar")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--runtime", action="store_true", help="solo el runtime")
    ap.add_argument("--backend", help="vulkan | cuda | rocm | metal | cpu")
    a = ap.parse_args()

    paths.ensure_dirs()
    if not a.models and not a.all and not a.runtime:
        status()
        return 0

    backend = a.backend or detect_backend()
    print(f"sistema {paths.SYSTEM}, backend {backend}")
    install_runtime(backend)
    if a.runtime:
        return 0

    todos = config.load_all()
    elegidos = todos if a.all else [m for m in todos if m.key in a.models]
    desconocidos = set(a.models) - {m.key for m in todos}
    if desconocidos:
        print("claves desconocidas:", ", ".join(sorted(desconocidos)), file=sys.stderr)
        return 1
    for m in elegidos:
        install_model(m)
    print("\nlisto. Arranca con:  python3 -m llmstack <clave>   o el selector 'llm'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
