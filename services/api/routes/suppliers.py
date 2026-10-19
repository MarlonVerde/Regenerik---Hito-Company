from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from cache import TTLMemoryCache
from models import (
    ApiMessageResponse,
    Supplier,
    SupplierCreate,
    SupplierListResponse,
    SupplierRateUpdate,
    SupplierStatusUpdate,
    validate_filter_category,
    validate_filter_country,
    validate_filter_status,
)
from stores import supplier_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["suppliers"])
store = supplier_store
SUPPLIER_LIST_TTL_SECONDS = 60
SUPPLIER_DETAIL_TTL_SECONDS = 120
supplier_list_cache = TTLMemoryCache(ttl_seconds=SUPPLIER_LIST_TTL_SECONDS)
supplier_detail_cache = TTLMemoryCache(ttl_seconds=SUPPLIER_DETAIL_TTL_SECONDS)


@router.get("/suppliers", response_model=SupplierListResponse)
def list_suppliers(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> SupplierListResponse:
    try:
        validated_country = validate_filter_country(country)
        validated_category = validate_filter_category(category)
        validated_status = validate_filter_status(status)
    except ValueError as error:
        logger.warning("Parámetros de filtro inválidos: %s", error)
        raise HTTPException(status_code=400, detail="Parámetros de filtro inválidos. Verifica los valores enviados.") from error

    cache_key = (validated_country or "*", validated_category or "*", validated_status or "*")
    suppliers = supplier_list_cache.get_or_set(
        cache_key,
        lambda: store.list(
            country=validated_country,
            category=validated_category,
            status=validated_status,
        ),
    )
    return {"items": suppliers, "total": len(suppliers)}


@router.get("/suppliers/{supplier_id}", response_model=Supplier)
def get_supplier_detail(supplier_id: str) -> Supplier:
    supplier = supplier_detail_cache.get_or_set(supplier_id, lambda: store.get(supplier_id))
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return supplier


@router.post("/suppliers", status_code=201, response_model=Supplier)
def create_supplier(payload: SupplierCreate) -> Supplier:
    created = store.create(payload)
    supplier_list_cache.invalidate_all()
    supplier_detail_cache.invalidate(created["id"])
    return created


@router.patch("/suppliers/{supplier_id}/rate", response_model=Supplier)
def update_supplier_rate(supplier_id: str, payload: SupplierRateUpdate) -> Supplier:
    updated = store.update_rate(supplier_id=supplier_id, new_rate=payload.rate_per_unit)
    if updated is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    supplier_list_cache.invalidate_all()
    supplier_detail_cache.invalidate(supplier_id)
    return updated


@router.patch("/suppliers/{supplier_id}/status", response_model=Supplier)
def update_supplier_status(supplier_id: str, payload: SupplierStatusUpdate) -> Supplier:
    updated = store.update_status(supplier_id=supplier_id, new_status=payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    supplier_list_cache.invalidate_all()
    supplier_detail_cache.invalidate(supplier_id)
    return updated


@router.delete("/suppliers/{supplier_id}", response_model=ApiMessageResponse)
def delete_supplier(supplier_id: str) -> ApiMessageResponse:
    deleted = store.delete(supplier_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    supplier_list_cache.invalidate_all()
    supplier_detail_cache.invalidate(supplier_id)
    return {"message": "Proveedor eliminado"}
