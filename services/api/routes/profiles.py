from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from models import Profile, ProfileCreate, ProfileUpdate
from stores import profile_store

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=Profile)
def get_my_profile(current_user: dict = Depends(get_current_user)) -> Profile:
    profile = profile_store.get_by_user_id(current_user["id"])
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return profile


@router.put("/me", response_model=Profile)
def update_my_profile(payload: ProfileUpdate, current_user: dict = Depends(get_current_user)) -> Profile:
    profile = profile_store.get_by_user_id(current_user["id"])
    if profile is None:
        try:
            created = profile_store.create(
                ProfileCreate(
                    user_id=current_user["id"],
                    name=payload.name or current_user["email"].split("@")[0],
                    phone=payload.phone,
                    address=payload.address,
                )
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Datos de perfil inválidos. Verifica los campos e intenta de nuevo.") from error
        return created

    updated = profile_store.update(profile_id=profile["id"], payload=payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return updated
