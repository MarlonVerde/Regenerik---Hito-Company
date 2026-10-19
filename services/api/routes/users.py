from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from models import ApiMessageResponse, UserCreate, UserListResponse, UserPublic, UserRole, UserUpdate
from user_service import (
    create_user as svc_create_user,
    delete_user as svc_delete_user,
    ensure_user_access,
    get_user_by_id as svc_get_user_by_id,
    list_users as svc_list_users,
    to_public_user,
    update_user as svc_update_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.post("", status_code=201, response_model=UserPublic)
def create_user(payload: UserCreate) -> UserPublic:
    try:
        public_payload = payload.model_copy(update={"role": UserRole.user})
        created = svc_create_user(payload=public_payload)
    except ValueError as error:
        logger.warning("Error al crear usuario: %s", error)
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario. Verifica los datos e intenta de nuevo.") from error

    return to_public_user(created)


@router.get("", response_model=UserListResponse)
def list_users(current_user: dict = Depends(get_current_user)) -> UserListResponse:
    records = svc_list_users() if current_user.get("role") == UserRole.admin.value else [current_user]
    users = [to_public_user(user) for user in records]
    return {"items": users, "total": len(users)}


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: str, current_user: dict = Depends(get_current_user)) -> UserPublic:
    ensure_user_access(current_user=current_user, target_user_id=user_id)
    user = svc_get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return to_public_user(user)


@router.put("/{user_id}", response_model=UserPublic)
def update_user(user_id: str, payload: UserUpdate, current_user: dict = Depends(get_current_user)) -> UserPublic:
    try:
        updated = svc_update_user(user_id=user_id, payload=payload, current_user=current_user)
    except ValueError as error:
        logger.warning("Error al actualizar usuario: %s", error)
        raise HTTPException(status_code=400, detail="No se pudo actualizar el usuario. Verifica los datos e intenta de nuevo.") from error

    if updated is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return to_public_user(updated)


@router.delete("/{user_id}", response_model=ApiMessageResponse)
def delete_user(user_id: str, current_user: dict = Depends(get_current_user)) -> ApiMessageResponse:
    deleted = svc_delete_user(user_id=user_id, current_user=current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"message": "Usuario eliminado"}
