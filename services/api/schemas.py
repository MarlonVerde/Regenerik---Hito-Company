from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

INGREDIENT_CATEGORIES = {"meat", "produce", "sauce", "beverage", "packaging", "cleaning"}
INGREDIENT_COUNTRIES = {"CO", "US"}


def normalize_required_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Este campo no puede estar vacío")
    return normalized


class IngredientCreate(BaseModel):
    name: str
    sku: str
    unit: str
    category: str
    country: str

    @field_validator("name", "sku", "unit")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        normalized = normalize_required_text(value)
        if normalized not in INGREDIENT_CATEGORIES:
            raise ValueError("Categoría de inventario inválida")
        return normalized

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        normalized = normalize_required_text(value)
        if normalized not in INGREDIENT_COUNTRIES:
            raise ValueError("El país debe ser CO o US")
        return normalized


class IngredientResponse(IngredientCreate):
    id: int
    current_stock: float


class IngredientEntryCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    supplier_name: str
    location_id: int = Field(ge=1, le=14)

    @field_validator("supplier_name")
    @classmethod
    def validate_supplier_name(cls, value: str) -> str:
        return normalize_required_text(value)


class IngredientExitCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    reason: str
    location_id: int = Field(ge=1, le=14)

    @model_validator(mode="after")
    def validate_reason(self):
        if self.reason not in {"consumption", "waste"}:
            raise ValueError("reason must be 'consumption' or 'waste'")
        return self


class IngredientEntryResponse(IngredientEntryCreate):
    id: int
    created_at: datetime
    user_uuid: str

    model_config = ConfigDict(from_attributes=True)


class IngredientExitResponse(IngredientExitCreate):
    id: int
    created_at: datetime
    user_uuid: str

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    movement_type: str
    quantity: float
    created_at: datetime
    user_uuid: str
    product: IngredientResponse
