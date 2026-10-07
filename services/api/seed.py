from __future__ import annotations

import os
from pathlib import Path

from database import SUPPLIERS_SEED, SupplierStore


def main() -> None:
    storage_dir = Path(
        os.environ.get("BRASALAND_DATA_DIR", Path(__file__).resolve().parent / "data" / "local")
    )
    storage_path = storage_dir / "suppliers.json"
    store = SupplierStore(storage_path=storage_path)

    inserted, skipped = store.seed_suppliers(SUPPLIERS_SEED)
    total = len(store.list())

    print(f"Seed completado. Insertados: {inserted}. Omitidos: {skipped}. Total actual: {total}.")


if __name__ == "__main__":
    main()
