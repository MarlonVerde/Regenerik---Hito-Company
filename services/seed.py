from __future__ import annotations

import sys
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

from sqlmodel import Session, SQLModel, select  # noqa: E402

from database import engine  # noqa: E402
from services.models import Ingredient, IngredientEntry, IngredientExit  # noqa: E402

# Set this to the authenticated TinyDB user's actual `id` from
# services/api/data/auth.json. The API stores `id`, not a `uuid` attribute.
USER_UUID = "PEGA_ACA_EL_ID_REAL_DE_TINYDB"

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
    if USER_UUID == "PEGA_ACA_EL_ID_REAL_DE_TINYDB" or not USER_UUID.strip():
        raise RuntimeError(
            "Configurá USER_UUID con el id real de un usuario existente en "
            "services/api/data/auth.json antes de ejecutar el seed."
        )

    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
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
