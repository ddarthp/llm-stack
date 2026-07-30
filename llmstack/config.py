"""Lectura de los model.toml.

Antes cada modelo tenia un model.conf que se hacia `source` desde bash: comodo en
Linux, inservible en Windows. TOML lo lee Python en los tres sistemas y ademas
permite declarar de donde se descargan los pesos, que es lo que hace posible el
instalador.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import paths


@dataclass
class Model:
    key: str
    name: str
    tag: str = ""
    note: str = ""
    model: str = ""
    mmproj: str = ""
    ctx: int = 32768
    min_size: int = 100_000_000
    runtime: str = "llamacpp"
    sampling: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    think: str = ""
    env: dict[str, str] = field(default_factory=dict)
    download_repo: str = ""
    download_files: list[str] = field(default_factory=list)
    bench: dict[str, float] = field(default_factory=dict)

    # ── rutas derivadas ────────────────────────────────────────────────────
    @property
    def dir(self) -> Path:
        return paths.models_dir() / self.key

    @property
    def model_path(self) -> Path:
        return self.dir / self.model

    @property
    def mmproj_path(self) -> Path | None:
        return self.dir / self.mmproj if self.mmproj else None

    @property
    def runtime_path(self) -> Path:
        return paths.runtime_dir() / self.runtime

    @property
    def log_path(self) -> Path:
        return paths.logs_dir() / f"{self.key}.log"

    def installed(self) -> bool:
        p = self.model_path
        try:
            return p.is_file() and p.stat().st_size >= self.min_size
        except OSError:
            return False

    def specs(self) -> str:
        """Linea de rendimiento para el menu; honesta si no se ha medido."""
        b = self.bench
        if not b.get("tg"):
            return "sin medir"
        out = f"{b['tg']:.1f} tok/s"
        if b.get("pp"):
            out += f" · prefill {b['pp']:.0f} tok/s"
        if b.get("vram_gb"):
            out += f" · {b['vram_gb']:.1f} GB"
        return out


def definitions_dir() -> Path:
    return paths.repo_root() / "models"


def load_all() -> list[Model]:
    """Lee todos los models/*/model.toml, en el orden que fija `order`."""
    out: list[Model] = []
    for d in sorted(definitions_dir().iterdir()):
        f = d / "model.toml"
        if not f.is_file():
            continue
        with open(f, "rb") as fh:
            raw = tomllib.load(fh)
        dl = raw.pop("download", {}) or {}
        bench = raw.pop("bench", {}) or {}
        order = raw.pop("order", 100)
        m = Model(
            key=d.name,
            download_repo=dl.get("repo", ""),
            download_files=dl.get("files", []),
            bench=bench,
            **{k: v for k, v in raw.items() if k in Model.__annotations__},
        )
        out.append((order, m))
    out.sort(key=lambda t: (t[0], t[1].name))
    return [m for _, m in out]


def find(key: str) -> Model | None:
    for m in load_all():
        if m.key == key:
            return m
    return None
