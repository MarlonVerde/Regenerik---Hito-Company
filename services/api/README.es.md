# API de Incidencias Brasaland

Servicio backend para analisis de incidencias y gestion del directorio de proveedores.

Stack del directorio de proveedores: FastAPI + TinyDB + Pydantic.

La API también expone inventario FastAPI + SQLModel sobre PostgreSQL. Usuarios y perfiles siguen en TinyDB.

## Endpoints

### Directorio de proveedores (almacenamiento ligero)

- `GET /suppliers`
  - Filtros opcionales por query: `country`, `category`, `status`.
  - Devuelve `{ "items": [...], "total": number }`.

- `GET /suppliers/{supplier_id}`
  - Devuelve el detalle de un proveedor por ID.
  - Responde `404` si no existe.

- `POST /suppliers`
  - Crea un proveedor.
  - Errores de payload invalidos se devuelven con `422` (validacion de FastAPI/Pydantic).
  - Valida reglas de negocio del contexto:
    - `country` debe ser `Colombia` o `USA`.
    - `currency` debe coincidir con el pais (`COP` para Colombia, `USD` para USA).
    - `categories` debe contener una o mas categorias validas.

- `PATCH /suppliers/{supplier_id}/rate`
  - Actualiza `rate_per_unit` y refresca el timestamp `updated_at`.

- `PATCH /suppliers/{supplier_id}/status`
  - Cambia `status` a `active` o `suspended`.

- `DELETE /suppliers/{supplier_id}`
  - Elimina un proveedor (pensado para correcciones de datos).

- `POST /api/incidents/analyze`
  - Recibe `multipart/form-data` con el campo `file` (`.csv`).
  - Ejecuta la misma lógica de validación + métricas y devuelve resumen en JSON.

- `GET /api/incidents/results/export`
  - Devuelve el último análisis como `results.csv` descargable.

- `GET /api/incidents/results/latest`
  - Devuelve el último resumen en JSON.

- `GET /health`
  - Liveness: confirma que el proceso responde, no comprueba PostgreSQL.
- `GET /health/ready`
  - Readiness: ejecuta `SELECT 1`; devuelve `503` si PostgreSQL no está disponible.

### Inventario (requiere Bearer)

- `GET /inventory/products`, `GET /inventory/products/{product_id}`
- `POST /inventory/products` con `name`, `sku`, `unit`, `category` y `country`.
- `POST /inventory/orders/inbound` con `ingredient_id`, `quantity`, `supplier_name` y `location_id` (1–14).
- `POST /inventory/orders/outbound` con `ingredient_id`, `quantity`, `reason` (`consumption` o `waste`) y `location_id` (1–14).
- `GET /inventory/orders` devuelve entradas y salidas con producto, fecha y `user_uuid`.
- Las lecturas y escrituras requieren `Authorization: Bearer <token>`. El stock se calcula con movimientos; la salida bloquea la fila del producto en PostgreSQL y devuelve `400` si excede el disponible. Una SKU duplicada devuelve `409`.

## Ejecutar

```bash
cd services/api
uv sync --locked
# Configura DATABASE_URL, AUTH_SECRET_KEY y CORS_ALLOWED_ORIGINS en .env local.
uv run python init_db.py
uv run uvicorn main:app --reload --port 8000
```

Si usas pip en vez de uv, instala `requirements.txt` para runtime; para ejecutar pruebas agrega `requirements-dev.txt`.

`main` no crea tablas durante la importación. Ejecuta `init_db.py` una vez para crear las tablas iniciales; el repositorio aún no contiene migraciones. Configura `CORS_ALLOWED_ORIGINS` como lista separada por comas de orígenes exactos; el valor por defecto permite solo los servidores locales documentados.

Para una cuenta administrativa **solo de desarrollo**, establece `APP_ENV=development`, `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD` (mínimo 8 caracteres) en el entorno local y ejecuta `uv run seed-admin`. El registro público siempre crea rol `user`. No guardes credenciales ni datos de `auth.json` en Git.

`BRASALAND_DATA_DIR` permite mover TinyDB a una carpeta persistente; si no se define, se usa `services/api/data/local`. `BRASALAND_SEED_USER_ID` configura el usuario local usado por `services/seed.py`.

Las claves se enumeran en [development-environment.example](development-environment.example); copia y completa los valores solo en `services/api/.env`, que está ignorado por Git.

Los datos runtime de TinyDB se persisten por defecto en `services/api/data/local/`, directorio ignorado por Git. `services/api/data/suppliers.json` se conserva como dataset versionado, no como almacén runtime.

## Seeder

- Script: `services/api/seed.py`
- Ejecucion: `uv run seed` (desde `services/api`)
- Comportamiento: inserta solo proveedores no existentes (evita duplicados) y reporta en consola inserciones/omitidos.

El capturador `scripts/take_screenshots.py` es opcional y requiere Playwright/Chromium. Sus credenciales deben venir de `BRASALAND_SCREENSHOT_EMAIL` y `BRASALAND_SCREENSHOT_PASSWORD`; no son dependencias de la API.
