from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from stores import user_store


def _load_local_env_file() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env_file()

SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "15"))
PASSWORD_RESET_SCOPE = "password_reset"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

if not SECRET_KEY:
    raise RuntimeError("AUTH_SECRET_KEY no configurada. Define la clave en variables de entorno.")


def get_user_store():
    return user_store


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> tuple[str, int]:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire_at = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user_id,
        "exp": expire_at,
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, int(expires_delta.total_seconds())


def create_password_reset_token(user_id: str, hashed_password: str) -> tuple[str, int]:
    expires_delta = timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    expire_at = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user_id,
        "scope": PASSWORD_RESET_SCOPE,
        "pwdfp": _password_fingerprint(hashed_password),
        "exp": expire_at,
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, int(expires_delta.total_seconds())


def _password_fingerprint(hashed_password: str) -> str:
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()


def verify_password_reset_token(token: str) -> str:
    invalid_token_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Token de recuperacion invalido o expirado",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as error:
        raise invalid_token_exception from error

    if payload.get("scope") != PASSWORD_RESET_SCOPE:
        raise invalid_token_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise invalid_token_exception

    user = user_store.get(user_id)
    if user is None:
        raise invalid_token_exception

    # Si la contraseña ya cambio (por este mismo token o por change-password),
    # el fingerprint no coincide y el token queda invalidado de un solo uso.
    if payload.get("pwdfp") != _password_fingerprint(user["hashed_password"]):
        raise invalid_token_exception

    return user_id


def get_current_user(token: str = Depends(oauth2_scheme), users=Depends(get_user_store)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as error:
        raise credentials_exception from error

    user = users.get(user_id)
    if user is None:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    return user
