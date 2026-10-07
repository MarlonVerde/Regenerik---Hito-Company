from __future__ import annotations

import os
from pathlib import Path

from database import ProfileStore, SupplierStore, UserStore

DATA_DIR = Path(
	os.environ.get("BRASALAND_DATA_DIR", Path(__file__).resolve().parent / "data" / "local")
)

supplier_store = SupplierStore(storage_path=DATA_DIR / "suppliers.json")
user_store = UserStore(storage_path=DATA_DIR / "auth.json")
profile_store = ProfileStore(storage_path=DATA_DIR / "auth.json")
