#!/usr/bin/env python3
"""Take screenshots of the Brasaland application for PR."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "http://127.0.0.1:8000"
BACKOFFICE_URL = "http://127.0.0.1:8080/uis/backoffice/index.html"
WEB_URL = "http://127.0.0.1:8080/uis/web/index.html"

TEST_EMAIL = os.getenv("BRASALAND_SCREENSHOT_EMAIL")
TEST_PASSWORD = os.getenv("BRASALAND_SCREENSHOT_PASSWORD")


def login(page, url: str) -> None:
    try:
        page.goto(url)
        page.wait_for_load_state("networkidle")
    except PlaywrightTimeout:
        print(f"Error: La página {url} no cargó a tiempo. Verifica que el servidor esté corriendo.", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Error al navegar a {url}: {error}", file=sys.stderr)
        sys.exit(1)

    try:
        page.fill('input[name="email"]', TEST_EMAIL)
        page.fill('input[name="password"]', TEST_PASSWORD)
        page.click('button:has-text("Iniciar sesión")')
        page.wait_for_timeout(2000)
    except Exception as error:
        print(f"Error al completar el formulario de inicio de sesión: {error}", file=sys.stderr)
        sys.exit(1)


def take_screenshot(page, filename: str, description: str) -> None:
    try:
        page.screenshot(path=str(EVIDENCE_DIR / filename), full_page=True)
        print(f"  Saved: {EVIDENCE_DIR / filename}")
    except Exception as error:
        print(f"Error al capturar {filename}: {error}", file=sys.stderr)


def take_screenshots() -> None:
    if not TEST_EMAIL or not TEST_PASSWORD:
        print(
            "Configura BRASALAND_SCREENSHOT_EMAIL y BRASALAND_SCREENSHOT_PASSWORD en el entorno local.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="es-ES",
            )
            page = context.new_page()

            # --- Screenshot 1: Validation error on supplier form ---
            print("Taking screenshot 1: Form validation error...")
            login(page, BACKOFFICE_URL)

            try:
                page.click('a[href="#suppliers"]')
                page.wait_for_timeout(1000)

                page.fill('form#supplierForm input[name="name"]', "")
                page.click('form#supplierForm button:has-text("Crear proveedor")')
                page.wait_for_timeout(500)
            except Exception as error:
                print(f"Error al preparar screenshot 1: {error}", file=sys.stderr)

            take_screenshot(page, "01-form-validation-error.png", "Form validation error")

            # --- Screenshot 2: Suppliers listing with data loaded ---
            print("Taking screenshot 2: Suppliers listing...")
            try:
                page.fill('form#supplierForm input[name="name"]', "Test Supplier")
                page.fill('form#supplierForm input[name="categories"]', "carne")
                page.fill('form#supplierForm input[name="rate_per_unit"]', "10000")
                page.click('#refreshSuppliersBtn')
                page.wait_for_timeout(1500)
            except Exception as error:
                print(f"Error al preparar screenshot 2: {error}", file=sys.stderr)

            take_screenshot(page, "02-suppliers-listing.png", "Suppliers listing")

            # --- Screenshot 3: Incidents analysis results ---
            print("Taking screenshot 3: Incidents analysis results...")
            try:
                csv_path = Path(__file__).resolve().parent.parent / "incidents-brasaland.csv"
                if not csv_path.exists():
                    print(f"Error: Archivo CSV no encontrado: {csv_path}", file=sys.stderr)
                else:
                    file_input = page.locator('input[type="file"]')
                    file_input.set_input_files(str(csv_path))
                    page.wait_for_timeout(500)

                    page.click('#analyzeBtn')
                    page.wait_for_timeout(2000)
            except Exception as error:
                print(f"Error al preparar screenshot 3: {error}", file=sys.stderr)

            take_screenshot(page, "03-incidents-summary.png", "Incidents summary")

            browser.close()
    except Exception as error:
        print(f"Error crítico al capturar screenshots: {error}", file=sys.stderr)
        sys.exit(1)

    print("\nAll screenshots captured successfully!")


if __name__ == "__main__":
    take_screenshots()