from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, func, select

from cache import TTLMemoryCache
from database import get_db
from services.models import Ingredient, IngredientEntry, IngredientExit
from schemas import (
    IngredientCreate,
    IngredientEntryCreate,
    IngredientEntryResponse,
    IngredientExitCreate,
    IngredientExitResponse,
    IngredientOrderItem,
    IngredientResponse,
    OrderResponse,
)

# Ajustá solamente este import a la ubicación REAL de tu auth existente.
from auth import get_current_user

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(get_current_user)],
)

INVENTORY_PRODUCTS_TTL_SECONDS = 20
INVENTORY_ORDERS_TTL_SECONDS = 15
products_cache = TTLMemoryCache(ttl_seconds=INVENTORY_PRODUCTS_TTL_SECONDS)
product_detail_cache = TTLMemoryCache(ttl_seconds=INVENTORY_PRODUCTS_TTL_SECONDS)
orders_cache = TTLMemoryCache(ttl_seconds=INVENTORY_ORDERS_TTL_SECONDS)


def invalidate_inventory_caches(product_id: int | None = None) -> None:
    products_cache.invalidate_all()
    orders_cache.invalidate_all()
    if product_id is None:
        product_detail_cache.invalidate_all()
    else:
        product_detail_cache.invalidate(product_id)


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


def get_product(db: Session, product_id: int, *, lock: bool = False) -> Ingredient:
    statement = select(Ingredient).where(Ingredient.id == product_id)
    if lock:
        statement = statement.with_for_update()
    product = db.exec(statement).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database operation failed") from error


@router.get("/products", response_model=list[IngredientResponse])
def get_products(db: Session = Depends(get_db)) -> list[IngredientResponse]:
    def build_products_response() -> list[IngredientResponse]:
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

    return products_cache.get_or_set("inventory.products", build_products_response)


@router.post("/products", response_model=IngredientResponse)
def create_product(
    payload: IngredientCreate,
    db: Session = Depends(get_db),
) -> IngredientResponse:
    product = Ingredient(**payload.model_dump())
    db.add(product)
    commit_or_conflict(db, "A product with this SKU already exists")
    db.refresh(product)

    if product.id is None:
        raise HTTPException(status_code=500, detail="Could not create product")

    invalidate_inventory_caches(product.id)

    return IngredientResponse(
        id=product.id,
        **payload.model_dump(),
        current_stock=0,
    )


@router.get("/products/{product_id}", response_model=IngredientResponse)
def get_product_detail(product_id: int, db: Session = Depends(get_db)) -> IngredientResponse:
    def build_product_detail() -> IngredientResponse:
        product = get_product(db, product_id)

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

    return product_detail_cache.get_or_set(product_id, build_product_detail)


@router.post("/orders/inbound", response_model=IngredientEntryResponse)
def create_inbound_order(
    payload: IngredientEntryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IngredientEntryResponse:
    get_product(db, payload.ingredient_id, lock=True)

    # The authenticated TinyDB user has an `id` (not a `uuid` attribute).
    order = IngredientEntry(
        **payload.model_dump(),
        user_uuid=str(current_user["id"]),
    )
    db.add(order)
    commit_or_conflict(db, "Unable to save inbound inventory order")
    db.refresh(order)
    invalidate_inventory_caches(payload.ingredient_id)
    return IngredientEntryResponse.model_validate(order)


@router.post("/orders/outbound", response_model=IngredientExitResponse)
def create_outbound_order(
    payload: IngredientExitCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IngredientExitResponse:
    product = get_product(db, payload.ingredient_id, lock=True)

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
    commit_or_conflict(db, "Unable to save outbound inventory order")
    db.refresh(order)
    invalidate_inventory_caches(payload.ingredient_id)
    return IngredientExitResponse.model_validate(order)


@router.get("/orders", response_model=list[OrderResponse])
def get_orders(db: Session = Depends(get_db)) -> list[OrderResponse]:
    def build_orders_response() -> list[OrderResponse]:
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
        movements: list[OrderResponse] = []

        for entry, ingredient in entries:
            if entry.id is None or ingredient.id is None:
                continue
            movements.append(
                OrderResponse(
                    id=entry.id,
                    movement_type="inbound",
                    quantity=entry.quantity,
                    created_at=entry.created_at,
                    user_uuid=entry.user_uuid,
                    ingredient=IngredientOrderItem(
                        id=ingredient.id,
                        name=ingredient.name,
                        sku=ingredient.sku,
                        unit=ingredient.unit,
                        category=ingredient.category,
                        country=ingredient.country,
                    ),
                )
            )

        for exit_order, ingredient in exits:
            if exit_order.id is None or ingredient.id is None:
                continue
            movements.append(
                OrderResponse(
                    id=exit_order.id,
                    movement_type="outbound",
                    quantity=exit_order.quantity,
                    created_at=exit_order.created_at,
                    user_uuid=exit_order.user_uuid,
                    ingredient=IngredientOrderItem(
                        id=ingredient.id,
                        name=ingredient.name,
                        sku=ingredient.sku,
                        unit=ingredient.unit,
                        category=ingredient.category,
                        country=ingredient.country,
                    ),
                )
            )

        movements.sort(key=lambda movement: movement.created_at)
        return movements

    return orders_cache.get_or_set("inventory.orders", build_orders_response)
