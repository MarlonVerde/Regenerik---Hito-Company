from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from database import get_db
from services.models import Ingredient, IngredientEntry, IngredientExit
from schemas import (
    IngredientCreate,
    IngredientResponse,
    IngredientEntryCreate,
    IngredientEntryResponse,
    IngredientExitCreate,
    IngredientExitResponse,
)

# Ajustá solamente este import a la ubicación REAL de tu auth existente.
from auth import get_current_user

router = APIRouter(prefix="/inventory", tags=["inventory"])


def calculate_stock(
    db: Session,
    ingredient_id: int,
) -> float:
    inbound_statement = (
        select(func.coalesce(func.sum(IngredientEntry.quantity), 0))
        .where(IngredientEntry.ingredient_id == ingredient_id)
    )
    outbound_statement = (
        select(func.coalesce(func.sum(IngredientExit.quantity), 0))
        .where(IngredientExit.ingredient_id == ingredient_id)
    )
    total_in = db.exec(inbound_statement).one()
    total_out = db.exec(outbound_statement).one()

    return total_in - total_out


@router.get("/products", response_model=list[IngredientResponse])
def get_products(db: Session = Depends(get_db)) -> list[IngredientResponse]:
    products = db.exec(select(Ingredient)).all()
    response = []

    for product in products:
        if product.id is None:
            continue

        current_stock = calculate_stock(db, product.id)
        response.append(
            IngredientResponse(
                id=product.id,
                name=product.name,
                sku=product.sku,
                unit=product.unit,
                category=product.category,
                country=product.country,
                current_stock=current_stock,
            )
        )

    return response


@router.post("/products", response_model=IngredientResponse)
def create_product(
    payload: IngredientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngredientResponse:
    product = Ingredient(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    if product.id is None:
        raise HTTPException(status_code=500, detail="Could not create product")

    return IngredientResponse(
        id=product.id,
        **payload.model_dump(),
        current_stock=0,
    )


@router.get("/products/{product_id}", response_model=IngredientResponse)
def get_product(product_id: int, db: Session = Depends(get_db)) -> IngredientResponse:
    product = db.get(Ingredient, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.id is None:
        raise HTTPException(status_code=500, detail="Product has no identifier")

    current_stock = calculate_stock(db, product.id)
    return IngredientResponse(
        id=product.id,
        name=product.name,
        sku=product.sku,
        unit=product.unit,
        category=product.category,
        country=product.country,
        current_stock=current_stock,
    )


@router.post("/orders/inbound", response_model=IngredientEntryResponse)
def create_inbound_order(
    payload: IngredientEntryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngredientEntryResponse:
    product = db.get(Ingredient, payload.ingredient_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # The authenticated TinyDB user has an `id` (not a `uuid` attribute).
    order = IngredientEntry(
        **payload.model_dump(),
        user_uuid=str(current_user["id"]),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return IngredientEntryResponse.model_validate(order)


@router.post("/orders/outbound", response_model=IngredientExitResponse)
def create_outbound_order(
    payload: IngredientExitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngredientExitResponse:
    product = db.get(Ingredient, payload.ingredient_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.id is None:
        raise HTTPException(status_code=500, detail="Product has no identifier")

    available = calculate_stock(db, product.id)
    if payload.quantity > available:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient stock for ingredient '{product.name}'. "
                f"Available: {available}, requested: {payload.quantity}."
            ),
        )

    # The available-stock check occurs before adding anything to the session.
    order = IngredientExit(
        **payload.model_dump(),
        user_uuid=str(current_user["id"]),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return IngredientExitResponse.model_validate(order)


@router.get("/orders")
def get_orders(db: Session = Depends(get_db)) -> list[dict]:
    entry_statement = (
        select(IngredientEntry, Ingredient)
        .join(Ingredient, IngredientEntry.ingredient_id == Ingredient.id)
    )
    exit_statement = (
        select(IngredientExit, Ingredient)
        .join(Ingredient, IngredientExit.ingredient_id == Ingredient.id)
    )

    entries = db.exec(entry_statement).all()
    exits = db.exec(exit_statement).all()
    movements = []

    for entry, ingredient in entries:
        movements.append(
            {
                "id": entry.id,
                "movement_type": "inbound",
                "quantity": entry.quantity,
                "created_at": entry.created_at,
                "user_uuid": entry.user_uuid,
                "ingredient": {
                    "id": ingredient.id,
                    "name": ingredient.name,
                    "sku": ingredient.sku,
                    "unit": ingredient.unit,
                    "category": ingredient.category,
                    "country": ingredient.country,
                },
            }
        )

    for exit_order, ingredient in exits:
        movements.append(
            {
                "id": exit_order.id,
                "movement_type": "outbound",
                "quantity": exit_order.quantity,
                "created_at": exit_order.created_at,
                "user_uuid": exit_order.user_uuid,
                "ingredient": {
                    "id": ingredient.id,
                    "name": ingredient.name,
                    "sku": ingredient.sku,
                    "unit": ingredient.unit,
                    "category": ingredient.category,
                    "country": ingredient.country,
                },
            }
        )

    movements.sort(key=lambda movement: movement["created_at"])
    return movements
