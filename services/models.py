from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Ingredient(SQLModel, table=True):  # type: ignore[call-arg]
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str = Field(index=True, unique=True)
    unit: str
    category: str
    country: str

    entries: list["IngredientEntry"] = Relationship(back_populates="product")
    exits: list["IngredientExit"] = Relationship(back_populates="product")


class IngredientEntry(SQLModel, table=True):  # type: ignore[call-arg]
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id")
    quantity: float
    supplier_name: str
    location_id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str

    product: Optional[Ingredient] = Relationship(back_populates="entries")


class IngredientExit(SQLModel, table=True):  # type: ignore[call-arg]
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id")
    quantity: float
    reason: str
    location_id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str

    product: Optional[Ingredient] = Relationship(back_populates="exits")
