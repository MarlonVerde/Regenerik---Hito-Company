from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, cast
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy.exc import ArgumentError
from sqlmodel import Session, create_engine
from tinydb import Query, TinyDB

from models import Profile, ProfileCreate, ProfileUpdate, Supplier, SupplierCreate, User, UserCreate, UserUpdate

logger = logging.getLogger(__name__)

SUPPLIERS_SEED: list[dict[str, Any]] = [
    {
        "name": "Carnes del Valle S.A.S.",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 28500.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "ventas@carnesdelvalle.co",
        "notes": "Proveedor principal de res y cerdo para Medellín. Entrega martes y viernes.",
    },
    {
        "name": "Frigorífico Antioqueño",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 27900.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "pedidos@frigorificoa.co",
        "notes": "Proveedor secundario. Usado cuando Carnes del Valle no tiene stock.",
    },
    {
        "name": "Verduras La Cosecha",
        "country": "Colombia",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 3200.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "lacosecha@gmail.com",
        "notes": "Mercado mayorista de Medellín. Entrega diaria antes de las 7am.",
    },
    {
        "name": "Condimentos El Sabor",
        "country": "Colombia",
        "categories": ["salsas_y_condimentos"],
        "rate_per_unit": 12400.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "info@elsabor.co",
    },
    {
        "name": "Distribuidora RefriCol",
        "country": "Colombia",
        "categories": ["bebidas", "lacteos"],
        "rate_per_unit": 4100.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "refricol.pedidos@gmail.com",
    },
    {
        "name": "Empaques y Más",
        "country": "Colombia",
        "categories": ["packaging"],
        "rate_per_unit": 890.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "ventas@empaquesymas.co",
        "notes": "Suministra cajas, bolsas y servilletas para todos los locales de Colombia.",
    },
    {
        "name": "Limpiahogar Profesional",
        "country": "Colombia",
        "categories": ["productos_limpieza"],
        "rate_per_unit": 7600.0,
        "currency": "COP",
        "status": "suspended",
        "contact_email": "limpiahogar@promail.co",
        "notes": "Suspendido por incumplimiento en entregas. En revisión por Lucía.",
    },
    {
        "name": "CarboCo",
        "country": "Colombia",
        "categories": ["carbon_y_combustible"],
        "rate_per_unit": 45000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "pedidos@carboco.co",
        "notes": "Único proveedor homologado de carbón para las brasas. Contrato anual.",
    },
    {
        "name": "Miami Meat Distributors LLC",
        "country": "USA",
        "categories": ["carne"],
        "rate_per_unit": 6.80,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@miamimeat.com",
        "notes": "Proveedor principal de carne para los locales de Florida.",
    },
    {
        "name": "Sunshine Produce FL",
        "country": "USA",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 2.15,
        "currency": "USD",
        "status": "active",
        "contact_email": "sales@sunshineproduce.com",
    },
    {
        "name": "Latin Flavors Inc.",
        "country": "USA",
        "categories": ["salsas_y_condimentos", "bebidas"],
        "rate_per_unit": 4.50,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@latinflavors.com",
        "notes": "Importa salsas colombianas para el mercado de Florida.",
    },
    {
        "name": "PackRight USA",
        "country": "USA",
        "categories": ["packaging"],
        "rate_per_unit": 0.35,
        "currency": "USD",
        "status": "active",
        "contact_email": "info@packright.us",
    },
    {
        "name": "CleanPro Florida",
        "country": "USA",
        "categories": ["productos_limpieza"],
        "rate_per_unit": 12.90,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@cleanproflorida.com",
    },
    {
        "name": "GrillFuel Supply Co.",
        "country": "USA",
        "categories": ["carbon_y_combustible"],
        "rate_per_unit": 38.50,
        "currency": "USD",
        "status": "active",
        "contact_email": "supply@grillfuel.com",
        "notes": "Proveedor de carbón para Florida. Precio sujeto a revisión trimestral.",
    },
    {
        "name": "Bebidas Andinas",
        "country": "Colombia",
        "categories": ["bebidas"],
        "rate_per_unit": 3800.0,
        "currency": "COP",
        "status": "suspended",
        "contact_email": "ventas@bebidasandinas.co",
        "notes": "Suspendido. Precio por encima del mercado tras última renegociación.",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupplierStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._lock = Lock()
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = TinyDB(self.storage_path, ensure_ascii=False, indent=2)
            self._table = self._db.table("suppliers")
            self._query = Query()
            self._ensure_storage_ready()
        except OSError as error:
            logger.error("Error de E/S al inicializar SupplierStore en %s: %s", storage_path, error)
            raise RuntimeError(f"No se pudo inicializar el almacenamiento de proveedores: {error}") from error
        except Exception as error:
            logger.exception("Error inesperado al inicializar SupplierStore en %s", storage_path)
            raise RuntimeError(f"Error inesperado al inicializar proveedores: {error}") from error

    def _ensure_storage_ready(self) -> None:
        try:
            self.seed_suppliers(SUPPLIERS_SEED)
        except Exception as error:
            logger.error("Error al sembrar proveedores: %s", error)
            raise RuntimeError(f"No se pudieron cargar los proveedores iniciales: {error}") from error

    def seed_suppliers(self, suppliers_seed: list[dict[str, Any]]) -> tuple[int, int]:
        inserted = 0
        skipped = 0

        with self._lock:
            for supplier in suppliers_seed:
                payload = SupplierCreate(**supplier).model_dump()
                existing = self._table.get(
                    (self._query.name == payload["name"]) & (self._query.country == payload["country"])
                )

                if existing is not None:
                    skipped += 1
                    continue

                payload["id"] = str(uuid4())
                payload["updated_at"] = now_iso()
                self._table.insert(payload)
                inserted += 1

        return inserted, skipped

    def list(
        self,
        country: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        records = cast(list[dict[str, Any]], self._table.all())
        filtered = []
        for record in records:
            if country and record["country"] != country:
                continue
            if status and record["status"] != status:
                continue
            if category and category not in record["categories"]:
                continue
            filtered.append(record)
        return filtered

    def create(self, payload: SupplierCreate) -> dict[str, Any]:
        with self._lock:
            new_record = payload.model_dump()
            new_record["id"] = str(uuid4())
            new_record["updated_at"] = now_iso()
            self._table.insert(new_record)
            return new_record

    def get(self, supplier_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._table.get(self._query.id == supplier_id))

    def update_rate(self, supplier_id: str, new_rate: float) -> dict[str, Any] | None:
        with self._lock:
            current = self.get(supplier_id)
            if current is None:
                return None

            updated = dict(current)
            updated["rate_per_unit"] = new_rate
            updated["updated_at"] = now_iso()
            Supplier(**updated)

            self._table.update(
                {"rate_per_unit": updated["rate_per_unit"], "updated_at": updated["updated_at"]},
                self._query.id == supplier_id,
            )
            return updated

    def update_status(self, supplier_id: str, new_status: str) -> dict[str, Any] | None:
        with self._lock:
            current = self.get(supplier_id)
            if current is None:
                return None

            updated = dict(current)
            updated["status"] = new_status
            Supplier(**updated)

            self._table.update({"status": updated["status"]}, self._query.id == supplier_id)
            return updated

    def delete(self, supplier_id: str) -> bool:
        with self._lock:
            removed_ids = self._table.remove(self._query.id == supplier_id)
            return bool(removed_ids)


class UserStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._lock = Lock()
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = TinyDB(self.storage_path, ensure_ascii=False, indent=2)
            self._table = self._db.table("users")
            self._query = Query()
        except OSError as error:
            logger.error("Error de E/S al inicializar UserStore en %s: %s", storage_path, error)
            raise RuntimeError(f"No se pudo inicializar el almacenamiento de usuarios: {error}") from error
        except Exception as error:
            logger.exception("Error inesperado al inicializar UserStore en %s", storage_path)
            raise RuntimeError(f"Error inesperado al inicializar usuarios: {error}") from error

    def count(self) -> int:
        return len(self._table)

    def list(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._table.all())

    def get(self, user_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._table.get(self._query.id == user_id))

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._table.get(self._query.email == email.strip().lower()))

    def create(self, payload: UserCreate, hashed_password: str) -> dict[str, Any]:
        with self._lock:
            existing = self.get_by_email(payload.email)
            if existing is not None:
                raise ValueError("Ya existe un usuario con ese email")

            current_time = now_iso()
            record: dict[str, Any] = {
                "id": str(uuid4()),
                "email": payload.email,
                "hashed_password": hashed_password,
                "is_active": True,
                "role": payload.role.value,
                "created_at": current_time,
                "updated_at": current_time,
            }
            User(**record)
            self._table.insert(record)
            return record

    def update(self, user_id: str, payload: UserUpdate) -> dict[str, Any] | None:
        with self._lock:
            current = self.get(user_id)
            if current is None:
                return None

            updated: dict[str, Any] = dict(current)
            if payload.email is not None:
                existing = self.get_by_email(payload.email)
                if existing is not None and existing["id"] != user_id:
                    raise ValueError("Ya existe un usuario con ese email")
                updated["email"] = payload.email

            if payload.role is not None:
                updated["role"] = payload.role.value

            if payload.is_active is not None:
                updated["is_active"] = payload.is_active

            updated["updated_at"] = now_iso()
            User(**updated)

            self._table.update(updated, self._query.id == user_id)
            return updated

    def update_password(self, user_id: str, hashed_password: str) -> dict[str, Any] | None:
        with self._lock:
            current = self.get(user_id)
            if current is None:
                return None

            updated: dict[str, Any] = dict(current)
            updated["hashed_password"] = hashed_password
            updated["updated_at"] = now_iso()
            User(**updated)

            self._table.update(updated, self._query.id == user_id)
            return updated

    def delete(self, user_id: str) -> bool:
        with self._lock:
            removed_ids = self._table.remove(self._query.id == user_id)
            return bool(removed_ids)


class ProfileStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._lock = Lock()
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = TinyDB(self.storage_path, ensure_ascii=False, indent=2)
            self._table = self._db.table("profiles")
            self._query = Query()
        except OSError as error:
            logger.error("Error de E/S al inicializar ProfileStore en %s: %s", storage_path, error)
            raise RuntimeError(f"No se pudo inicializar el almacenamiento de perfiles: {error}") from error
        except Exception as error:
            logger.exception("Error inesperado al inicializar ProfileStore en %s", storage_path)
            raise RuntimeError(f"Error inesperado al inicializar perfiles: {error}") from error

    def list(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._table.all())

    def get(self, profile_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._table.get(self._query.id == profile_id))

    def get_by_user_id(self, user_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._table.get(self._query.user_id == user_id))

    def create(self, payload: ProfileCreate) -> dict[str, Any]:
        with self._lock:
            existing = self.get_by_user_id(payload.user_id)
            if existing is not None:
                raise ValueError("Ese usuario ya tiene un perfil")

            record = payload.model_dump()
            current_time = now_iso()
            record["id"] = str(uuid4())
            record["created_at"] = current_time
            record["updated_at"] = current_time

            Profile(**record)
            self._table.insert(record)
            return record

    def update(self, profile_id: str, payload: ProfileUpdate) -> dict[str, Any] | None:
        with self._lock:
            current = self.get(profile_id)
            if current is None:
                return None

            updated = dict(current)
            patch = payload.model_dump(exclude_none=True)
            updated.update(patch)
            updated["updated_at"] = now_iso()

            Profile(**updated)
            self._table.update(updated, self._query.id == profile_id)
            return updated

    def delete(self, profile_id: str) -> bool:
        with self._lock:
            removed_ids = self._table.remove(self._query.id == profile_id)
            return bool(removed_ids)

    def delete_by_user_id(self, user_id: str) -> bool:
        with self._lock:
            removed_ids = self._table.remove(self._query.user_id == user_id)
            return bool(removed_ids)


# Keep TinyDB for users, profiles, suppliers, and authentication. SQLModel is
# reserved for the Supabase-backed inventory entities.
# The API's own environment file is authoritative when present; services/.env
# remains a fallback for setups that keep shared service configuration there.
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")

@lru_cache(maxsize=1)
def get_engine():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL no está configurada")
    try:
        return create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    except (ArgumentError, ModuleNotFoundError) as error:
        raise RuntimeError("DATABASE_URL inválida o falta el driver PostgreSQL requerido") from error


def get_db():
    with Session(get_engine()) as session:
        yield session
