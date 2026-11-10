from __future__ import annotations

from fastapi import HTTPException, status

from auth import get_user_role, hash_password, is_admin_email, verify_password
from models import ProfileCreate, UserCreate, UserPublic, UserRole, UserUpdate
from stores import profile_store, user_store


def to_public_user(record: dict) -> dict:
    return UserPublic(
        id=record["id"],
        email=record["email"],
        is_active=record["is_active"],
        role=get_user_role(record),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    ).model_dump(mode="json")


def create_user(payload: UserCreate) -> dict:
    hashed_password = hash_password(payload.password)
    created = user_store.create(payload=payload, hashed_password=hashed_password)

    try:
        profile_store.create(
            ProfileCreate(
                user_id=created["id"],
                name=payload.name or payload.email.split("@")[0],
                phone=payload.phone,
                address=payload.address,
            )
        )
    except Exception:
        user_store.delete(created["id"])
        raise

    return created


def get_user_by_id(user_id: str) -> dict | None:
    return user_store.get(user_id)


def get_user_by_email(email: str) -> dict | None:
    return user_store.get_by_email(email)


def list_users() -> list[dict]:
    return user_store.list()


def ensure_user_access(current_user: dict, target_user_id: str) -> None:
    if current_user.get("role") == UserRole.admin.value:
        return
    if current_user["id"] != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para este recurso")


def update_user(user_id: str, payload: UserUpdate, current_user: dict) -> dict | None:
    if current_user.get("role") != UserRole.admin.value:
        raise HTTPException(status_code=403, detail="Solo el administrador puede gestionar usuarios")
    current = user_store.get(user_id)
    if current is None:
        return None
    reserved = is_admin_email(current["email"])
    if payload.role is not None and (payload.role != UserRole.user or reserved):
        raise HTTPException(status_code=403, detail="El administrador se habilita exclusivamente desde el servidor")
    if payload.email is not None and payload.email != current["email"].strip().lower():
        if reserved or is_admin_email(payload.email):
            raise HTTPException(status_code=403, detail="No se puede reasignar el correo administrativo")
    if reserved and payload.is_active is False:
        raise HTTPException(status_code=403, detail="No se puede desactivar la cuenta administrativa")

    return user_store.update(user_id=user_id, payload=payload)


def delete_user(user_id: str, current_user: dict) -> bool:
    if current_user.get("role") != UserRole.admin.value or user_id == current_user["id"]:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar esta cuenta")
    deleted = user_store.delete(user_id)
    if deleted:
        profile_store.delete_by_user_id(user_id)
    return deleted


def set_user_password(user_id: str, new_password: str) -> dict | None:
    hashed_password = hash_password(new_password)
    return user_store.update_password(user_id=user_id, hashed_password=hashed_password)


def change_password(user_id: str, current_password: str, new_password: str) -> dict:
    user = user_store.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not verify_password(current_password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")

    updated = set_user_password(user_id=user_id, new_password=new_password)
    if updated is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return updated
