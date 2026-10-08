#!/usr/bin/env python3
"""Wrapper que ejecuta el analizador apuntando a packages/shared."""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGES_DIR = Path(__file__).resolve().parents[1] / "packages"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

# Re-enruta al analyze.py raíz que ahora usa packages/shared
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analyze import main  # noqa: E402


if __name__ == "__main__":
    main()
