from __future__ import annotations

import sys
import os
from pathlib import Path

SERVICES_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SERVICES_DIR.parent
API_DIR = SERVICES_DIR / "api"

# `database.py` belongs to the existing API package. Put it first so its
# `models` import continues to resolve to services/api/models.py (TinyDB).
for directory in (str(REPOSITORY_ROOT), str(API_DIR)):
    if directory in sys.path:
        sys.path.remove(directory)
    sys.path.insert(0, directory)

from sqlmodel import Session, select  # noqa: E402

from database import get_engine  # noqa: E402
from init_db import initialize_database  # noqa: E402
from services.models import Ingredient, IngredientEntry, IngredientExit  # noqa: E402

# Set BRASALAND_SEED_USER_ID to the authenticated TinyDB user's actual `id`.
USER_UUID = os.getenv("BRASALAND_SEED_USER_ID", "").strip()

INGREDIENTS = [
    {
        "name": "Falda de ternera",
        "sku": "BRS-BEEF-001",
        "unit": "kg",
        "category": "meat",
        "country": "CO",
    },
    {
        "name": "Costilla de cerdo",
        "sku": "BRS-PORK-001",
        "unit": "kg",
        "category": "meat",
        "country": "US",
    },
    {
        "name": "Chimichurri",
        "sku": "BRS-SAUCE-001",
        "unit": "litro",
        "category": "sauce",
        "country": "CO",
    },
    {
        "name": "Salsa BBQ de la casa",
        "sku": "BRS-SAUCE-002",
        "unit": "litro",
        "category": "sauce",
        "country": "US",
    },
    {
        "name": "Yuca",
        "sku": "BRS-PROD-001",
        "unit": "kg",
        "category": "produce",
        "country": "CO",
    },
    {
        "name": "Caja para llevar (M)",
        "sku": "BRS-PKG-001",
        "unit": "unidad",
        "category": "packaging",
        "country": "CO",
    },
]


def seed() -> None:
    if not USER_UUID:
        raise RuntimeError(
            "Configura BRASALAND_SEED_USER_ID con el id de un usuario local antes de ejecutar el seed."
        )

    initialize_database()

    with Session(get_engine()) as db:
        existing = db.exec(select(Ingredient)).first()
        if existing:
            print("Ya hay ingredientes cargados. No se ejecutó el seed.")
            return

        ingredients = [Ingredient(**data) for data in INGREDIENTS]
        db.add_all(ingredients)
        db.commit()

        for ingredient in ingredients:
            db.refresh(ingredient)

        by_sku = {ingredient.sku: ingredient for ingredient in ingredients}
        entries = [
            IngredientEntry(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=50,
                supplier_name="Carnes del Valle S.A.",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=30,
                supplier_name="Carnes del Valle S.A.",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=by_sku["BRS-PORK-001"].id,
                quantity=40,
                supplier_name="MiamiMeat Co.",
                location_id=2,
                user_uuid=USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=by_sku["BRS-SAUCE-001"].id,
                quantity=20,
                supplier_name="Salsas Artesanales Ltda.",
                location_id=3,
                user_uuid=USER_UUID,
            ),
        ]
        db.add_all(entries)
        db.commit()

        exits = [
            IngredientExit(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=10,
                reason="consumption",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientExit(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=5,
                reason="waste",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientExit(
                ingredient_id=by_sku["BRS-PORK-001"].id,
                quantity=8,
                reason="consumption",
                location_id=2,
                user_uuid=USER_UUID,
            ),
        ]
        db.add_all(exits)
        db.commit()

    print("Seed de Brasaland cargado correctamente.")


if __name__ == "__main__":
    seed()
