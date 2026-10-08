from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from sqlmodel import SQLModel

import services.models  # noqa: F401
from database import get_engine


def initialize_database() -> None:
    SQLModel.metadata.create_all(get_engine())


if __name__ == "__main__":
    initialize_database()
    print("Tablas de inventario inicializadas.")
