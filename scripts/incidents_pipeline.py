#!/usr/bin/env python3
"""Valida incidencias CSV y calcula métricas sobre registros válidos."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class ValidationOutcome:
    errors: list[str]
    has_missing: bool
    has_invalid_value: bool


def load_rules(rules_path: Path) -> dict:
    try:
        with rules_path.open("r", encoding="utf-8") as file:
            rules = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"Archivo de reglas no encontrado: {rules_path}")
    except json.JSONDecodeError as error:
        raise ValueError(f"Error al parsear el archivo de reglas JSON: {error}")
    except PermissionError:
        raise ValueError(f"Sin permisos para leer el archivo de reglas: {rules_path}")

    required_fields = rules.get("required_fields")
    allowed_values = rules.get("allowed_values")

    if not isinstance(required_fields, list) or not all(
        isinstance(item, str) for item in required_fields
    ):
        raise ValueError("'required_fields' debe ser una lista de strings")

    if not isinstance(allowed_values, dict) or not all(
        isinstance(key, str) and isinstance(values, list)
        for key, values in allowed_values.items()
    ):
        raise ValueError("'allowed_values' debe ser un objeto field -> [valores]")

    normalized_allowed = {
        field: {str(value).strip() for value in values}
        for field, values in allowed_values.items()
    }

    return {
        "required_fields": [item.strip() for item in required_fields],
        "allowed_values": normalized_allowed,
    }


def validate_row(row: dict[str, str], rules: dict) -> ValidationOutcome:
    errors: list[str] = []
    has_missing = False
    has_invalid_value = False

    for field in rules["required_fields"]:
        value = (row.get(field) or "").strip()
        if not value:
            errors.append(f"MISSING:{field}")
            has_missing = True

    for field, allowed in rules["allowed_values"].items():
        value = (row.get(field) or "").strip()
        if value and value not in allowed:
            errors.append(f"INVALID:{field}:{value}")
            has_invalid_value = True

    return ValidationOutcome(
        errors=errors,
        has_missing=has_missing,
        has_invalid_value=has_invalid_value,
    )


def ensure_headers(headers: Iterable[str] | None, rules: dict) -> list[str]:
    if headers is None:
        raise ValueError("El CSV no tiene cabeceras")

    header_set = set(headers)
    expected = set(rules["required_fields"]) | set(rules["allowed_values"].keys())
    missing_headers = sorted(expected - header_set)

    if missing_headers:
        formatted = ", ".join(missing_headers)
        raise ValueError(f"Faltan columnas requeridas en CSV: {formatted}")

    return list(headers)


def run_pipeline(input_csv: Path, rules_path: Path, output_dir: Path) -> dict:
    rules = load_rules(rules_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_path = output_dir / "valid_records.csv"
    invalid_path = output_dir / "invalid_records.csv"
    summary_path = output_dir / "summary.json"

    total_records = 0
    valid_records = 0
    invalid_records = 0

    incomplete_records = 0
    corrupt_records = 0

    missing_fields_counter: Counter[str] = Counter()
    invalid_values_counter: defaultdict[str, Counter[str]] = defaultdict(Counter)
    allowed_field_counter: defaultdict[str, Counter[str]] = defaultdict(Counter)

    try:
        with input_csv.open("r", encoding="utf-8-sig", newline="") as src:
            reader = csv.DictReader(src)
            fieldnames = ensure_headers(reader.fieldnames, rules)

            invalid_fieldnames = fieldnames + ["source_row", "validation_errors"]

            with valid_path.open("w", encoding="utf-8", newline="") as valid_file, invalid_path.open(
                "w", encoding="utf-8", newline=""
            ) as invalid_file:
                valid_writer = csv.DictWriter(valid_file, fieldnames=fieldnames)
                invalid_writer = csv.DictWriter(invalid_file, fieldnames=invalid_fieldnames)

                valid_writer.writeheader()
                invalid_writer.writeheader()

                for row_number, row in enumerate(reader, start=2):
                    total_records += 1
                    outcome = validate_row(row, rules)

                    if outcome.errors:
                        invalid_records += 1
                        if outcome.has_missing:
                            incomplete_records += 1
                        if outcome.has_invalid_value:
                            corrupt_records += 1

                        for error in outcome.errors:
                            if error.startswith("MISSING:"):
                                _, field = error.split(":", maxsplit=1)
                                missing_fields_counter[field] += 1
                            elif error.startswith("INVALID:"):
                                _, field, value = error.split(":", maxsplit=2)
                                invalid_values_counter[field][value] += 1

                        invalid_row = dict(row)
                        invalid_row["source_row"] = row_number
                        invalid_row["validation_errors"] = " | ".join(outcome.errors)
                        invalid_writer.writerow(invalid_row)
                        continue

                    valid_records += 1
                    valid_writer.writerow(row)

                    for field in rules["allowed_values"].keys():
                        value = (row.get(field) or "").strip()
                        if value:
                            allowed_field_counter[field][value] += 1
    except FileNotFoundError:
        raise ValueError(f"Archivo de entrada no encontrado: {input_csv}")
    except PermissionError:
        raise ValueError(f"Sin permisos para leer/escribir archivos en: {input_csv}")
    except csv.Error as error:
        raise ValueError(f"Error al procesar el CSV: {error}")

    invalid_rate = (invalid_records / total_records * 100) if total_records else 0.0

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_csv),
        "rules_file": str(rules_path),
        "outputs": {
            "valid_records": str(valid_path),
            "invalid_records": str(invalid_path),
            "summary": str(summary_path),
        },
        "totals": {
            "total_records": total_records,
            "valid_records": valid_records,
            "invalid_records": invalid_records,
            "invalid_rate_percent": round(invalid_rate, 2),
        },
        "invalid_breakdown": {
            "incomplete_records": incomplete_records,
            "corrupt_records": corrupt_records,
            "missing_required_field_counts": dict(missing_fields_counter),
            "invalid_value_counts": {
                field: dict(counter) for field, counter in invalid_values_counter.items()
            },
        },
        "valid_metrics": {
            field: dict(counter) for field, counter in allowed_field_counter.items()
        },
    }

    try:
        with summary_path.open("w", encoding="utf-8") as summary_file:
            json.dump(summary, summary_file, ensure_ascii=False, indent=2)
    except PermissionError:
        raise ValueError(f"Sin permisos para escribir el resumen en: {summary_path}")
    except OSError as error:
        raise ValueError(f"Error de E/S al escribir el resumen: {error}")

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida incidencias CSV, excluye inválidos y genera métricas de válidos."
    )
    parser.add_argument("--input", required=True, help="Ruta del CSV de incidencias")
    parser.add_argument(
        "--rules",
        required=True,
        help="Ruta del JSON con reglas (required_fields + allowed_values)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/process/incidents_output",
        help="Directorio para archivos de salida",
    )
    return parser


def main() -> None:
    try:
        args = build_parser().parse_args()

        input_csv = Path(args.input)
        rules_path = Path(args.rules)
        output_dir = Path(args.output_dir)

        if not input_csv.exists():
            print(f"Error: no existe el archivo de entrada: {input_csv}", file=sys.stderr)
            sys.exit(1)
        if not rules_path.exists():
            print(f"Error: no existe el archivo de reglas: {rules_path}", file=sys.stderr)
            sys.exit(1)

        summary = run_pipeline(input_csv=input_csv, rules_path=rules_path, output_dir=output_dir)

        print("Pipeline completado")
        print(f"- Total: {summary['totals']['total_records']}")
        print(f"- Válidos: {summary['totals']['valid_records']}")
        print(f"- Inválidos: {summary['totals']['invalid_records']}")
        print(f"- % inválidos: {summary['totals']['invalid_rate_percent']}")
        print(f"- Resumen: {summary['outputs']['summary']}")
    except ValueError as error:
        print(f"Error de configuración: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Error inesperado: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
