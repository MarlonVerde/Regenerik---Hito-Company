from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    if os.getenv("APP_ENV") != "development":
        raise SystemExit("El bootstrap de admin solo está permitido con APP_ENV=development.")

    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email or len(password) < 8:
        raise SystemExit("Configura email y contraseña de bootstrap en el entorno local (mínimo 8 caracteres).")

    from auth import verify_password
    from models import UserCreate, UserRole, UserUpdate
    from stores import user_store
    from user_service import create_user

    existing = user_store.get_by_email(email)
    if existing is not None:
        if not existing.get("is_active", True) or not verify_password(password, existing["hashed_password"]):
            raise SystemExit("No se pudo verificar la cuenta existente con las credenciales configuradas.")
        if existing.get("role") != UserRole.admin.value:
            user_store.update(existing["id"], UserUpdate(role=UserRole.admin))
        print("Cuenta administrativa existente habilitada; contrasena y perfil conservados.")
        return

    create_user(UserCreate(email=email, password=password, role=UserRole.admin))
    print("Cuenta administrativa de desarrollo creada en el almacén local ignorado por Git.")


if __name__ == "__main__":
    main()
