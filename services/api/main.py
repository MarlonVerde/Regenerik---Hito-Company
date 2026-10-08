from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

PACKAGES_DIR = Path(__file__).resolve().parents[2] / "packages"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.append(str(REPOSITORY_ROOT))

from shared.incidents_analysis import (  # noqa: E402
    analyze_csv_text,
    metrics_rows_to_csv,
    to_metrics_rows,
    to_summary,
)
from auth import get_current_user  # noqa: E402
from database import get_engine  # noqa: E402
import services.models  # noqa: E402,F401
from services.routers.inventory import router as inventory_router  # noqa: E402
from routes.auth import router as auth_router  # noqa: E402
from routes.profiles import router as profiles_router  # noqa: E402
from routes.suppliers import router as suppliers_router  # noqa: E402
from routes.users import router as users_router  # noqa: E402

logger = logging.getLogger(__name__)
app = FastAPI(title="Brasaland Operations API", version="1.0.0")

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5500,http://127.0.0.1:5500,"
    "http://localhost:8080,http://127.0.0.1:8080"
)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
if "*" in CORS_ALLOWED_ORIGINS:
    raise RuntimeError("CORS_ALLOWED_ORIGINS debe enumerar orígenes explícitos; no se admite '*'.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

LATEST_SUMMARY: dict | None = None
LATEST_RESULTS_CSV: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (RuntimeError, SQLAlchemyError) as error:
        logger.warning("Readiness check failed: database unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
    return {"status": "ready"}


@app.post("/api/incidents/analyze", dependencies=[Depends(get_current_user)])
async def analyze_incidents(file: UploadFile = File(...)) -> JSONResponse:
    global LATEST_SUMMARY, LATEST_RESULTS_CSV

    if not file.filename:
        raise HTTPException(status_code=400, detail="Debes enviar un archivo CSV")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Formato incorrecto: se espera un archivo .csv")

    raw_content = await file.read()
    if not raw_content:
        raise HTTPException(status_code=400, detail="El fichero está vacío")

    try:
        csv_text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="El archivo debe estar en UTF-8") from error

    if not csv_text.strip():
        raise HTTPException(status_code=400, detail="El fichero está vacío")

    try:
        result = analyze_csv_text(csv_text)
        summary = to_summary(result, source_file=file.filename)
        rows = to_metrics_rows(summary)
        csv_output = metrics_rows_to_csv(rows)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Error inesperado al analizar CSV")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error al procesar el archivo. Verifica el formato e intenta de nuevo.",
        ) from error

    LATEST_SUMMARY = summary
    LATEST_RESULTS_CSV = csv_output

    return JSONResponse(content=summary)


@app.get("/api/incidents/results/export", dependencies=[Depends(get_current_user)])
def export_last_results() -> Response:
    if LATEST_RESULTS_CSV is None:
        raise HTTPException(status_code=404, detail="No hay resultados para exportar. Ejecuta primero el análisis.")

    return Response(
        content=LATEST_RESULTS_CSV,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=results.csv"},
    )


@app.get("/api/incidents/results/latest", dependencies=[Depends(get_current_user)])
def latest_results() -> JSONResponse:
    if LATEST_SUMMARY is None:
        raise HTTPException(status_code=404, detail="No hay análisis ejecutados todavía")
    return JSONResponse(content=LATEST_SUMMARY)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(suppliers_router, dependencies=[Depends(get_current_user)])
app.include_router(suppliers_router, prefix="/api", dependencies=[Depends(get_current_user)])

app.include_router(inventory_router)
