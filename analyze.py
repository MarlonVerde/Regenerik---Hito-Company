#!/usr/bin/env python3
"""Brasaland incident report analyzer."""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGES_DIR = Path(__file__).resolve().parent / "packages"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

from shared.incidents_analysis import (
    AnalysisResult,
    SCORE_LABELS,
    VALID_CATEGORIES,
    VALID_STATUSES,
    analyze_csv_file,
    calculate_average_score,
    metrics_rows_to_csv,
    to_metrics_rows,
    verify_expected_values,
)


def print_report(file_path: Path, result: AnalysisResult) -> None:
    print("=" * 60)
    print("  BRASALAND - INCIDENT REPORT ANALYSIS")
    print(f"  Source file: {file_path.name}")
    print("=" * 60)
    print()

    print(f"TOTAL RECORDS IN FILE .......... {result.total}")
    print(f"  |- Valid records ................ {result.valid}")
    print(f"  '- Invalid / incomplete .......... {result.invalid}")
    print()

    print("INVALID RECORDS BREAKDOWN")
    print(f"  |- Missing location_id ........... {result.invalid_counts['missing_location']}")
    print(f"  |- Invalid or missing category ... {result.invalid_counts['invalid_category']}")
    print(f"  |- Empty description ............. {result.invalid_counts['empty_description']}")
    print(f"  '- Closed case, no score ......... {result.invalid_counts['closed_without_score']}")

    optional_rules = [
        ("missing_reporter", "Missing reporter_id"),
        ("score_out_of_range", "Score out of range"),
        ("invalid_status", "Invalid status"),
        ("invalid_incident_id", "Invalid incident_id format"),
        ("invalid_date", "Invalid date format"),
        ("invalid_customer_id", "Invalid customer_id format"),
    ]
    extra_lines = [(key, label) for key, label in optional_rules if result.invalid_counts[key] > 0]
    if extra_lines:
        print("  Additional validation issues:")
        for key, label in extra_lines:
            print(f"  * {label:<30} {result.invalid_counts[key]}")

    print()
    print("BREAKDOWN BY CATEGORY (valid records)")
    for i, category in enumerate(VALID_CATEGORIES):
        count = result.by_category[category]
        prefix = "  |-" if i < len(VALID_CATEGORIES) - 1 else "  '-"
        percentage = (count / result.valid * 100) if result.valid else 0.0
        print(f"{prefix} {category:<26} {count:>3}  ({percentage:.1f}%)")

    print()
    print("BREAKDOWN BY STATUS (valid records)")
    for i, status in enumerate(VALID_STATUSES):
        count = result.by_status[status]
        prefix = "  |-" if i < len(VALID_STATUSES) - 1 else "  '-"
        percentage = (count / result.valid * 100) if result.valid else 0.0
        print(f"{prefix} {status:<26} {count:>3}  ({percentage:.1f}%)")

    print()
    print("SATISFACTION INDEX (closed cases)")
    avg_score = calculate_average_score(result)
    print(f"  Scored cases: {result.scored_closed_cases} of {result.closed_cases}")
    print(f"  Average score: {avg_score:.2f} / 5.00")

    for score in range(1, 6):
        label = SCORE_LABELS[score]
        count = result.by_score[score]
        prefix = "  |-" if score < 5 else "  '-"
        print(f"{prefix} Score {score} ({label}) ... {count}")

    print()
    print("=" * 60)


def export_metrics_csv(result: AnalysisResult, destination: Path) -> None:
    try:
        summary = {
            "totals": {
                "total_records": result.total,
                "valid_records": result.valid,
                "invalid_records": result.invalid,
            },
            "invalid_breakdown": {
                "missing_location_id": result.invalid_counts["missing_location"],
                "invalid_or_missing_category": result.invalid_counts["invalid_category"],
                "empty_description": result.invalid_counts["empty_description"],
                "closed_without_score": result.invalid_counts["closed_without_score"],
            },
            "breakdown_by_category": [
                {
                    "category": category,
                    "count": result.by_category[category],
                    "percentage": (result.by_category[category] / result.valid * 100) if result.valid else 0.0,
                }
                for category in VALID_CATEGORIES
            ],
            "breakdown_by_status": [
                {
                    "status": status,
                    "count": result.by_status[status],
                    "percentage": (result.by_status[status] / result.valid * 100) if result.valid else 0.0,
                }
                for status in VALID_STATUSES
            ],
            "satisfaction_index": {
                "closed_cases": result.closed_cases,
                "scored_cases": result.scored_closed_cases,
                "average_score": calculate_average_score(result),
                "distribution": [
                    {"score": score, "label": SCORE_LABELS[score], "count": result.by_score[score]}
                    for score in range(1, 6)
                ],
            },
        }

        rows = to_metrics_rows(summary)
        content = metrics_rows_to_csv(rows)
        destination.write_text(content, encoding="utf-8")
    except PermissionError:
        print(f"Error: sin permisos para escribir en: {destination}", file=sys.stderr)
        sys.exit(1)
    except OSError as error:
        print(f"Error de E/S al escribir el archivo CSV: {error}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python analyze.py incidents-brasaland.csv", file=sys.stderr)
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: archivo no encontrado: {file_path}", file=sys.stderr)
        sys.exit(1)

    if not file_path.is_file():
        print(f"Error: la ruta no es un archivo: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        result = analyze_csv_file(file_path)
        print_report(file_path, result)
    except PermissionError:
        print(f"Error: sin permisos de lectura para: {file_path}", file=sys.stderr)
        sys.exit(1)
    except ValueError as error:
        print(f"Error de validación: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Error inesperado al analizar archivo: {error}", file=sys.stderr)
        sys.exit(1)

    if file_path.name == "incidents-brasaland.csv":
        mismatches = verify_expected_values(result)
        if not mismatches:
            print("Verificacion CONTEXT: OK. Los valores coinciden exactamente.")
        else:
            print("Verificacion CONTEXT: NO COINCIDE.")
            for item in mismatches:
                print(f"- {item}")
        print()

    answer = input("Deseas exportar los resultados a CSV? [s / n]: ").strip().lower()
    if answer == "s":
        export_path = Path("results.csv")
        export_metrics_csv(result, export_path)
        print(f"CSV exportado en: {export_path}")


if __name__ == "__main__":
    main()
