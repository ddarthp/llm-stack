"""Punto de entrada: `python3 -m llmstack [clave-de-modelo]`.

Sin argumentos abre el selector; con una clave arranca ese modelo directamente.
"""
from __future__ import annotations

import sys

from . import config, runner


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        return runner.run(args[0])
    from . import selector
    return selector.main()


if __name__ == "__main__":
    sys.exit(main())
