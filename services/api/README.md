# Brasaland Incidents API

Backend service for incidents analysis and supplier directory management.

Stack for supplier directory: FastAPI + TinyDB + Pydantic.

The API also exposes inventory through FastAPI + SQLModel/PostgreSQL. Users and profiles remain in TinyDB.

## Password recovery email

`POST /auth/forgot-password` sends the reset link by email using [Resend](https://resend.com) or [SendGrid](https://sendgrid.com), selected via the `EMAIL_PROVIDER` environment variable. No API key is ever hardcoded in the source; all values are loaded from environment variables (see `.env.example`).

- `EMAIL_PROVIDER`: `resend` or `sendgrid`. If unset, email is skipped; reset links and tokens are never logged.
- `RESEND_API_KEY` / `RESEND_FROM_EMAIL`: required when `EMAIL_PROVIDER=resend`.
- `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL`: required when `EMAIL_PROVIDER=sendgrid`.
- `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`: reset token expiry window (default `15`).
- `PASSWORD_RESET_URL_BASE`: base URL of the frontend `/reset-password` page used to build the emailed link.

## Endpoints

### Suppliers directory (lightweight storage)

- `GET /suppliers`
  - Optional query filters: `country`, `category`, `status`.
  - Returns `{ "items": [...], "total": number }`.

- `GET /suppliers/{supplier_id}`
  - Returns supplier details by ID.
  - Returns `404` when not found.

- `POST /suppliers`
  - Creates a supplier.
  - Invalid payloads are rejected with `422` by FastAPI/Pydantic validation.
  - Validates business rules from the company context:
    - `country` must be `Colombia` or `USA`.
    - `currency` must match country (`COP` for Colombia, `USD` for USA).
    - `categories` must contain one or more valid values.

- `PATCH /suppliers/{supplier_id}/rate`
  - Updates `rate_per_unit` and refreshes `updated_at` timestamp.

- `PATCH /suppliers/{supplier_id}/status`
  - Sets `status` to `active` or `suspended`.

- `DELETE /suppliers/{supplier_id}`
  - Deletes a supplier (for data correction scenarios).

- `POST /api/incidents/analyze`
  - `multipart/form-data` with field `file` (`.csv`)
  - Runs the incidents validation + metrics logic and returns JSON summary.

- `GET /api/incidents/results/export`
  - Returns the latest analysis as downloadable `results.csv`.

- `GET /api/incidents/results/latest`
  - Returns latest analysis JSON summary.

- `GET /health`
  - Liveness only; it does not check PostgreSQL.
- `GET /health/ready`
  - Readiness; runs `SELECT 1` and returns `503` when PostgreSQL is unavailable.

### Inventory (Bearer token required)

- `GET /inventory/products`, `GET /inventory/products/{product_id}`
- `POST /inventory/products` with `name`, `sku`, `unit`, `category`, and `country`.
- `POST /inventory/orders/inbound` with `ingredient_id`, `quantity`, `supplier_name`, and `location_id` (1–14).
- `POST /inventory/orders/outbound` with `ingredient_id`, `quantity`, `reason` (`consumption` or `waste`), and `location_id` (1–14).
- `GET /inventory/orders` returns movements with product, timestamp, and `user_uuid`.
- All inventory reads and writes require `Authorization: Bearer <token>`. Stock is calculated from movements; outbound requests lock the product row in PostgreSQL and return `400` when quantity exceeds stock. Duplicate SKUs return `409`.

## Run

```bash
cd services/api
uv sync --locked
# Configure DATABASE_URL, AUTH_SECRET_KEY, and CORS_ALLOWED_ORIGINS in a local .env.
uv run python init_db.py
uv run uvicorn main:app --reload --port 8000
```

When using pip instead of uv, install `requirements.txt` for runtime; add `requirements-dev.txt` to run the test suite.

The API no longer creates tables during import. Run `init_db.py` once to create the initial tables; this repository does not yet contain migrations. Set `CORS_ALLOWED_ORIGINS` to a comma-separated list of exact origins; the default allows only the documented local frontend servers.

For a **development-only** administrator, set `APP_ENV=development`, `BOOTSTRAP_ADMIN_EMAIL`, and `BOOTSTRAP_ADMIN_PASSWORD` (at least 8 characters) locally, then run `uv run seed-admin`. Public registration always creates role `user`. Never commit credentials or `auth.json` data.

`BRASALAND_DATA_DIR` can relocate TinyDB; the default is `services/api/data/local`. `BRASALAND_SEED_USER_ID` configures the local account used by `services/seed.py`.

The keys are listed in [development-environment.example](development-environment.example); copy and fill them only in `services/api/.env`, which is ignored by Git.

Runtime TinyDB data is persisted by default in `services/api/data/local/`, which is ignored by Git. `services/api/data/suppliers.json` remains a tracked seed dataset, not the runtime store.

## Seeder

- Script: `services/api/seed.py`
- Run: `uv run seed` (from `services/api`)
- Behavior: inserts only missing suppliers (no duplicates) and prints inserted/skipped counts.

`scripts/take_screenshots.py` is optional and requires Playwright/Chromium. Credentials come from `BRASALAND_SCREENSHOT_EMAIL` and `BRASALAND_SCREENSHOT_PASSWORD`; Playwright is not an API dependency.
