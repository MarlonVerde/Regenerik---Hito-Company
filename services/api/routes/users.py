from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from auth import get_current_user
from models import UserCreate, UserRole, UserUpdate
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


@router.post("", status_code=201)
def create_user(payload: UserCreate) -> JSONResponse:
    try:
        public_payload = payload.model_copy(update={"role": UserRole.user})
        created = svc_create_user(payload=public_payload)
    except ValueError as error:
        logger.warning("Error al crear usuario: %s", error)
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario. Verifica los datos e intenta de nuevo.") from error

    return JSONResponse(status_code=201, content=to_public_user(created))


@router.get("")
def list_users(current_user: dict = Depends(get_current_user)) -> JSONResponse:
    records = svc_list_users() if current_user.get("role") == UserRole.admin.value else [current_user]
    users = [to_public_user(user) for user in records]
    return JSONResponse(content={"items": users, "total": len(users)})


@router.get("/{user_id}")
def get_user(user_id: str, current_user: dict = Depends(get_current_user)) -> JSONResponse:
    ensure_user_access(current_user=current_user, target_user_id=user_id)
    user = svc_get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return JSONResponse(content=to_public_user(user))


@router.put("/{user_id}")
def update_user(user_id: str, payload: UserUpdate, current_user: dict = Depends(get_current_user)) -> JSONResponse:
    try:
        updated = svc_update_user(user_id=user_id, payload=payload, current_user=current_user)
    except ValueError as error:
        logger.warning("Error al actualizar usuario: %s", error)
        raise HTTPException(status_code=400, detail="No se pudo actualizar el usuario. Verifica los datos e intenta de nuevo.") from error

    if updated is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return JSONResponse(content=to_public_user(updated))


@router.delete("/{user_id}")
def delete_user(user_id: str, current_user: dict = Depends(get_current_user)) -> JSONResponse:
    deleted = svc_delete_user(user_id=user_id, current_user=current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return JSONResponse(content={"message": "Usuario eliminado"})
