from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from models import (
    SupplierCreate,
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


@router.get("/suppliers")
def list_suppliers(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> JSONResponse:
    try:
        validated_country = validate_filter_country(country)
        validated_category = validate_filter_category(category)
        validated_status = validate_filter_status(status)
    except ValueError as error:
        logger.warning("Parámetros de filtro inválidos: %s", error)
        raise HTTPException(status_code=400, detail="Parámetros de filtro inválidos. Verifica los valores enviados.") from error

    suppliers = store.list(
        country=validated_country,
        category=validated_category,
        status=validated_status,
    )
    return JSONResponse(content={"items": suppliers, "total": len(suppliers)})


@router.get("/suppliers/{supplier_id}")
def get_supplier_detail(supplier_id: str) -> JSONResponse:
    supplier = store.get(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return JSONResponse(content=supplier)


@router.post("/suppliers", status_code=201)
def create_supplier(payload: SupplierCreate) -> JSONResponse:
    created = store.create(payload)
    return JSONResponse(status_code=201, content=created)


@router.patch("/suppliers/{supplier_id}/rate")
def update_supplier_rate(supplier_id: str, payload: SupplierRateUpdate) -> JSONResponse:
    updated = store.update_rate(supplier_id=supplier_id, new_rate=payload.rate_per_unit)
    if updated is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return JSONResponse(content=updated)


@router.patch("/suppliers/{supplier_id}/status")
def update_supplier_status(supplier_id: str, payload: SupplierStatusUpdate) -> JSONResponse:
    updated = store.update_status(supplier_id=supplier_id, new_status=payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return JSONResponse(content=updated)


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: str) -> JSONResponse:
    deleted = store.delete(supplier_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return JSONResponse(content={"message": "Proveedor eliminado"})
