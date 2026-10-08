from __future__ import annotations

from enum import Enum
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VALID_CATEGORIES = [
    "carne",
    "verduras_y_hortalizas",
    "salsas_y_condimentos",
    "bebidas",
    "packaging",
    "productos_limpieza",
    "lacteos",
    "carbon_y_combustible",
]

VALID_STATUSES = ["active", "suspended"]
VALID_COUNTRIES = ["Colombia", "USA"]
COUNTRY_CURRENCY = {"Colombia": "COP", "USA": "USD"}


class SupplierBase(BaseModel):
    name: str = Field(min_length=1)
    country: str
    categories: list[str]
    rate_per_unit: float
    currency: str
    status: str = "active"
    contact_email: str | None = None
    notes: str | None = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        if value not in VALID_COUNTRIES:
            raise ValueError(f"country invalido: {value}. Debe ser uno de {VALID_COUNTRIES}")
        return value

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("categories debe tener al menos una categoria")

        normalized = []
        for category in value:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"categoria invalida: {category}")
            if category not in normalized:
                normalized.append(category)

        return normalized

    @field_validator("rate_per_unit")
    @classmethod
    def validate_rate(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("rate_per_unit debe ser mayor que 0")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if value not in ("COP", "USD"):
            raise ValueError("currency debe ser COP o USD")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError(f"status invalido: {value}. Debe ser uno de {VALID_STATUSES}")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name no puede estar vacio")
        return normalized

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("contact_email invalido")

        return normalized

    @model_validator(mode="after")
    def validate_country_currency(self) -> "SupplierBase":
        expected_currency = COUNTRY_CURRENCY[self.country]
        if self.currency != expected_currency:
            raise ValueError(f"Moneda inconsistente: para {self.country} se espera {expected_currency}")
        return self


class SupplierCreate(SupplierBase):
    pass


class SupplierRateUpdate(BaseModel):
    rate_per_unit: float

    @field_validator("rate_per_unit")
    @classmethod
    def validate_rate(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("rate_per_unit debe ser mayor que 0")
        return value


class SupplierStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError(f"status invalido: {value}. Debe ser uno de {VALID_STATUSES}")
        return value


class Supplier(SupplierBase):
    model_config = ConfigDict(extra="forbid")

    id: str
    updated_at: str


def validate_filter_country(country: str | None) -> str | None:
    if country is None:
        return None
    if country not in VALID_COUNTRIES:
        raise ValueError(f"country invalido: {country}. Debe ser uno de {VALID_COUNTRIES}")
    return country


def validate_filter_category(category: str | None) -> str | None:
    if category is None:
        return None
    if category not in VALID_CATEGORIES:
        raise ValueError(f"category invalida: {category}. Debe ser una de {VALID_CATEGORIES}")
    return category


def validate_filter_status(status: str | None) -> str | None:
    if status is None:
        return None
    if status not in VALID_STATUSES:
        raise ValueError(f"status invalido: {status}. Debe ser uno de {VALID_STATUSES}")
    return status


EMAIL_REGEX = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class UserRole(str, Enum):
    admin = "admin"
    manager = "manager"
    user = "user"


class UserBase(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_REGEX.fullmatch(normalized):
            raise ValueError("email invalido")
        return normalized


class UserCreate(UserBase):
    password: str = Field(min_length=8)
    role: UserRole = UserRole.user
    name: str | None = None
    phone: str | None = None
    address: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[0-9+\-()\s]{7,20}", normalized):
            raise ValueError("phone invalido")
        return normalized

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class UserUpdate(BaseModel):
    email: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not EMAIL_REGEX.fullmatch(normalized):
            raise ValueError("email invalido")
        return normalized

    @model_validator(mode="after")
    def require_one_field(self) -> "UserUpdate":
        if self.email is None and self.role is None and self.is_active is None:
            raise ValueError("Debes enviar al menos un campo para actualizar")
        return self


class User(UserBase):
    model_config = ConfigDict(extra="forbid")

    id: str
    hashed_password: str
    is_active: bool
    role: UserRole
    created_at: str
    updated_at: str


class UserPublic(UserBase):
    id: str
    is_active: bool
    role: UserRole
    created_at: str
    updated_at: str


class ProfileBase(BaseModel):
    name: str = Field(min_length=1)
    phone: str | None = None
    address: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name no puede estar vacio")
        return normalized

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[0-9+\-()\s]{7,20}", normalized):
            raise ValueError("phone invalido")
        return normalized

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProfileCreate(ProfileBase):
    user_id: str


class ProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("name no puede estar vacio")
        return normalized

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[0-9+\-()\s]{7,20}", normalized):
            raise ValueError("phone invalido")
        return normalized

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_one_field(self) -> "ProfileUpdate":
        if self.name is None and self.phone is None and self.address is None:
            raise ValueError("Debes enviar al menos un campo para actualizar")
        return self


class Profile(ProfileBase):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    created_at: str
    updated_at: str


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_REGEX.fullmatch(normalized):
            raise ValueError("email invalido")
        return normalized


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str


class AuthMeResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    profile: Profile | None


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_REGEX.fullmatch(normalized):
            raise ValueError("email invalido")
        return normalized


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
