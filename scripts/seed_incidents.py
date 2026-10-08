#!/usr/bin/env python3
"""Seed incidents CSV into the TinyDB database."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB

PACKAGES_DIR = Path(__file__).resolve().parent.parent / "packages"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

from shared.incidents_analysis import (
    VALID_CATEGORIES,
    VALID_LOCATIONS,
    VALID_STATUSES,
    validate_record,
)


def load_csv(file_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load CSV and return (valid_records, invalid_records)."""
    import csv

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []

    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                errors = validate_record(row)
                record = {
                    "incident_id": row.get("incident_id", "").strip(),
                    "date": row.get("date", "").strip(),
                    "location_id": row.get("location_id", "").strip(),
                    "category": row.get("category", "").strip(),
                    "description": row.get("description", "").strip(),
                    "status": row.get("status", "").strip(),
                    "customer_id": row.get("customer_id", "").strip() or None,
                    "satisfaction_score": row.get("satisfaction_score", "").strip() or None,
                    "reporter_id": row.get("reporter_id", "").strip(),
                }

                if errors:
                    record["_errors"] = errors
                    invalid.append(record)
                else:
                    if record["satisfaction_score"] is not None:
                        record["satisfaction_score"] = int(record["satisfaction_score"])
                    valid.append(record)
    except FileNotFoundError:
        print(f"Error: archivo no encontrado: {file_path}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: sin permisos para leer el archivo: {file_path}", file=sys.stderr)
        sys.exit(1)
    except csv.Error as error:
        print(f"Error al parsear el CSV en {file_path}: {error}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as error:
        print(f"Error de codificación en {file_path}: el archivo debe estar en UTF-8.", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Error inesperado al leer {file_path}: {error}", file=sys.stderr)
        sys.exit(1)

    return valid, invalid


def seed_database(
    db_path: Path,
    valid_records: list[dict[str, Any]],
    invalid_records: list[dict[str, Any]],
) -> tuple[int, int]:
    """Insert records into TinyDB, returning (inserted, skipped)."""
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db = TinyDB(db_path, ensure_ascii=False, indent=2)
        table = db.table("incidents")
        query = Query()
    except OSError as error:
        print(f"Error de E/S al crear la base de datos en {db_path}: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Error inesperado al inicializar la base de datos: {error}", file=sys.stderr)
        sys.exit(1)

    inserted = 0
    skipped = 0

    try:
        for record in valid_records:
            existing = table.get(query.incident_id == record["incident_id"])
            if existing:
                skipped += 1
                continue
            record["valid"] = True
            table.insert(record)
            inserted += 1

        for record in invalid_records:
            existing = table.get(query.incident_id == record["incident_id"])
            if existing:
                skipped += 1
                continue
            record["valid"] = False
            table.insert(record)
            inserted += 1
    except Exception as error:
        print(f"Error al insertar registros en la base de datos: {error}", file=sys.stderr)
        sys.exit(1)

    return inserted, skipped


def print_summary(
    file_path: Path,
    valid: list[dict[str, Any]],
    invalid: list[dict[str, Any]],
    inserted: int,
    skipped: int,
) -> None:
    """Print a summary of the seeding operation."""
    print("=" * 60)
    print("  BRASALAND - INCIDENT SEED")
    print(f"  Source: {file_path.name}")
    print("=" * 60)
    print()
    print(f"Records read ................... {len(valid) + len(invalid)}")
    print(f"  Valid ........................ {len(valid)}")
    print(f"  Invalid ...................... {len(invalid)}")
    print()
    print(f"Database operations")
    print(f"  Inserted ..................... {inserted}")
    print(f"  Skipped (duplicates) ......... {skipped}")
    print()

    if invalid:
        print("Invalid record IDs:")
        for rec in invalid:
            errors = ", ".join(rec.get("_errors", []))
            print(f"  - {rec['incident_id']}: {errors}")
        print()

    print("Done.")


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "services" / "api" / "data"
    default_csv = Path(__file__).resolve().parent.parent / "incidents-brasaland.csv"
    db_path = data_dir / "incidents.json"

    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_csv

    if not csv_path.exists():
        print(f"Error: archivo no encontrado: {csv_path}")
        sys.exit(1)

    valid, invalid = load_csv(csv_path)
    inserted, skipped = seed_database(db_path, valid, invalid)
    print_summary(csv_path, valid, invalid, inserted, skipped)


if __name__ == "__main__":
    main()