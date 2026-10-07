from __future__ import annotations

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypedDict

VALID_LOCATIONS = {f"COL-{i:02d}" for i in range(1, 11)} | {f"FLA-{i:02d}" for i in range(1, 5)}
VALID_CATEGORIES = [
    "CUSTOMER_COMPLAINT",
    "EQUIPMENT",
    "SUPPLY",
    "FOOD_QUALITY",
    "STAFF",
]
VALID_STATUSES = ["OPEN", "CLOSED", "DISCARDED"]

SCORE_LABELS = {
    1: "Very dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very satisfied",
}

class ExpectedInvalidCounts(TypedDict):
    missing_location: int
    invalid_category: int
    empty_description: int
    closed_without_score: int


class ExpectedContextValues(TypedDict):
    total: int
    valid: int
    invalid: int
    invalid_counts: ExpectedInvalidCounts
    by_category: dict[str, int]
    by_status: dict[str, int]
    by_score: dict[int, int]
    avg_score: float


EXPECTED_CONTEXT_VALUES: ExpectedContextValues = {
    "total": 100,
    "valid": 96,
    "invalid": 4,
    "invalid_counts": {
        "missing_location": 1,
        "invalid_category": 1,
        "empty_description": 1,
        "closed_without_score": 1,
    },
    "by_category": {
        "CUSTOMER_COMPLAINT": 29,
        "EQUIPMENT": 17,
        "SUPPLY": 22,
        "FOOD_QUALITY": 19,
        "STAFF": 9,
    },
    "by_status": {
        "OPEN": 32,
        "CLOSED": 50,
        "DISCARDED": 14,
    },
    "by_score": {
        1: 4,
        2: 6,
        3: 12,
        4: 19,
        5: 9,
    },
    "avg_score": 3.46,
}

RE_INCIDENT_ID = re.compile(r"^BRS-\d{6}$")
RE_CUSTOMER_ID = re.compile(r"^CLI-\d{6}$")
RE_REPORTER_ID = re.compile(r"^MGR-\d{2}$")


@dataclass
class AnalysisResult:
    total: int
    valid: int
    invalid: int
    invalid_counts: Counter[str]
    by_category: Counter[str]
    by_status: Counter[str]
    by_score: Counter[int]
    closed_cases: int
    scored_closed_cases: int


def pct(part: int, total: int) -> float:
    return (part / total * 100) if total else 0.0


def is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_score(raw_value: str) -> tuple[int | None, bool]:
    value = raw_value.strip()
    if not value:
        return None, True

    if not value.isdigit():
        return None, False

    score = int(value)
    if 1 <= score <= 5:
        return score, True

    return None, False


def validate_record(row: dict[str, str]) -> list[str]:
    errors: list[str] = []

    incident_id = (row.get("incident_id") or "").strip()
    date_value = (row.get("date") or "").strip()
    location_id = (row.get("location_id") or "").strip()
    category = (row.get("category") or "").strip()
    description = (row.get("description") or "").strip()
    status = (row.get("status") or "").strip()
    customer_id = (row.get("customer_id") or "").strip()
    satisfaction_score = (row.get("satisfaction_score") or "").strip()
    reporter_id = (row.get("reporter_id") or "").strip()

    if not incident_id or not RE_INCIDENT_ID.match(incident_id):
        errors.append("invalid_incident_id")

    if not date_value or not is_valid_date(date_value):
        errors.append("invalid_date")

    if not location_id or location_id not in VALID_LOCATIONS:
        errors.append("missing_location")

    if not category or category not in VALID_CATEGORIES:
        errors.append("invalid_category")

    if len(description) < 5:
        errors.append("empty_description")

    if not status or status not in VALID_STATUSES:
        errors.append("invalid_status")

    if customer_id and not RE_CUSTOMER_ID.match(customer_id):
        errors.append("invalid_customer_id")

    if not reporter_id or not RE_REPORTER_ID.match(reporter_id):
        errors.append("missing_reporter")

    score, is_valid_score = parse_score(satisfaction_score)
    if not is_valid_score:
        errors.append("score_out_of_range")

    if status == "CLOSED" and score is None:
        errors.append("closed_without_score")

    return errors


def analyze_reader(reader: csv.DictReader) -> AnalysisResult:
    invalid_counts: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_score: Counter[int] = Counter()

    total = 0
    valid = 0
    closed_cases = 0
    scored_closed_cases = 0

    expected_headers = {
        "incident_id",
        "date",
        "location_id",
        "category",
        "description",
        "status",
        "customer_id",
        "satisfaction_score",
        "reporter_id",
    }

    if not reader.fieldnames:
        raise ValueError("El CSV no tiene encabezados")

    missing_headers = expected_headers - set(reader.fieldnames)
    if missing_headers:
        missing_text = ", ".join(sorted(missing_headers))
        raise ValueError(f"Faltan columnas en CSV: {missing_text}")

    for row in reader:
        total += 1
        errors = validate_record(row)

        if errors:
            for rule in set(errors):
                invalid_counts[rule] += 1
            continue

        valid += 1
        category = (row.get("category") or "").strip()
        status = (row.get("status") or "").strip()
        score_raw = (row.get("satisfaction_score") or "").strip()

        by_category[category] += 1
        by_status[status] += 1

        if status == "CLOSED":
            closed_cases += 1
            score = int(score_raw)
            by_score[score] += 1
            scored_closed_cases += 1

    return AnalysisResult(
        total=total,
        valid=valid,
        invalid=total - valid,
        invalid_counts=invalid_counts,
        by_category=by_category,
        by_status=by_status,
        by_score=by_score,
        closed_cases=closed_cases,
        scored_closed_cases=scored_closed_cases,
    )


def analyze_csv_text(csv_text: str) -> AnalysisResult:
    stream = io.StringIO(csv_text)
    reader = csv.DictReader(stream)
    return analyze_reader(reader)


def analyze_csv_file(file_path: Path) -> AnalysisResult:
    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            return analyze_reader(reader)
    except FileNotFoundError:
        raise ValueError(f"Archivo no encontrado: {file_path}")
    except PermissionError:
        raise ValueError(f"Sin permisos de lectura para: {file_path}")
    except csv.Error as error:
        raise ValueError(f"Error al parsear el CSV: {error}")
    except UnicodeDecodeError as error:
        raise ValueError(f"Error de codificación en {file_path}: {error}")


def calculate_average_score(result: AnalysisResult) -> float:
    return (
        sum(score * count for score, count in result.by_score.items()) / result.scored_closed_cases
        if result.scored_closed_cases
        else 0.0
    )


def to_summary(result: AnalysisResult, source_file: str) -> dict:
    avg_score = calculate_average_score(result)

    breakdown_by_category = [
        {
            "category": category,
            "count": result.by_category[category],
            "percentage": round(pct(result.by_category[category], result.valid), 1),
        }
        for category in VALID_CATEGORIES
    ]

    breakdown_by_status = [
        {
            "status": status,
            "count": result.by_status[status],
            "percentage": round(pct(result.by_status[status], result.valid), 1),
        }
        for status in VALID_STATUSES
    ]

    score_distribution = [
        {
            "score": score,
            "label": SCORE_LABELS[score],
            "count": result.by_score[score],
        }
        for score in range(1, 6)
    ]

    return {
        "source_file": source_file,
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
        "breakdown_by_category": breakdown_by_category,
        "breakdown_by_status": breakdown_by_status,
        "satisfaction_index": {
            "closed_cases": result.closed_cases,
            "scored_cases": result.scored_closed_cases,
            "average_score": round(avg_score, 2),
            "distribution": score_distribution,
        },
    }


def to_metrics_rows(summary: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def append_metric(metric: str, value: str, percentage: str = "") -> None:
        rows.append({"metric": metric, "value": value, "percentage": percentage})

    totals = summary["totals"]
    invalid = summary["invalid_breakdown"]
    sat = summary["satisfaction_index"]

    append_metric("total_records", str(totals["total_records"]))
    append_metric(
        "valid_records",
        str(totals["valid_records"]),
        f"{pct(totals['valid_records'], totals['total_records']):.1f}%",
    )
    append_metric(
        "invalid_records",
        str(totals["invalid_records"]),
        f"{pct(totals['invalid_records'], totals['total_records']):.1f}%",
    )

    append_metric("invalid_missing_location_id", str(invalid["missing_location_id"]))
    append_metric(
        "invalid_missing_or_invalid_category",
        str(invalid["invalid_or_missing_category"]),
    )
    append_metric("invalid_empty_description", str(invalid["empty_description"]))
    append_metric("invalid_closed_without_score", str(invalid["closed_without_score"]))

    for item in summary["breakdown_by_category"]:
        append_metric(
            f"category_{item['category']}",
            str(item["count"]),
            f"{item['percentage']:.1f}%",
        )

    for item in summary["breakdown_by_status"]:
        append_metric(
            f"status_{item['status']}",
            str(item["count"]),
            f"{item['percentage']:.1f}%",
        )

    append_metric("closed_cases", str(sat["closed_cases"]))
    append_metric("scored_closed_cases", str(sat["scored_cases"]))
    append_metric("avg_satisfaction_score", f"{sat['average_score']:.2f}")

    for item in sat["distribution"]:
        append_metric(f"satisfaction_score_{item['score']}", str(item["count"]))

    return rows


def metrics_rows_to_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["metric", "value", "percentage"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def verify_expected_values(result: AnalysisResult) -> list[str]:
    mismatches: list[str] = []

    if result.total != EXPECTED_CONTEXT_VALUES["total"]:
        mismatches.append(
            f"total: esperado {EXPECTED_CONTEXT_VALUES['total']}, obtenido {result.total}"
        )
    if result.valid != EXPECTED_CONTEXT_VALUES["valid"]:
        mismatches.append(
            f"valid: esperado {EXPECTED_CONTEXT_VALUES['valid']}, obtenido {result.valid}"
        )
    if result.invalid != EXPECTED_CONTEXT_VALUES["invalid"]:
        mismatches.append(
            f"invalid: esperado {EXPECTED_CONTEXT_VALUES['invalid']}, obtenido {result.invalid}"
        )

    for field, expected in EXPECTED_CONTEXT_VALUES["invalid_counts"].items():
        got = result.invalid_counts[field]
        if got != expected:
            mismatches.append(f"invalid_counts.{field}: esperado {expected}, obtenido {got}")

    for category, expected in EXPECTED_CONTEXT_VALUES["by_category"].items():
        got = result.by_category[category]
        if got != expected:
            mismatches.append(f"by_category.{category}: esperado {expected}, obtenido {got}")

    for status, expected in EXPECTED_CONTEXT_VALUES["by_status"].items():
        got = result.by_status[status]
        if got != expected:
            mismatches.append(f"by_status.{status}: esperado {expected}, obtenido {got}")

    for score, expected in EXPECTED_CONTEXT_VALUES["by_score"].items():
        got = result.by_score[score]
        if got != expected:
            mismatches.append(f"by_score.{score}: esperado {expected}, obtenido {got}")

    avg_score = calculate_average_score(result)
    if round(avg_score, 2) != EXPECTED_CONTEXT_VALUES["avg_score"]:
        mismatches.append(
            "avg_score: esperado "
            f"{EXPECTED_CONTEXT_VALUES['avg_score']:.2f}, obtenido {avg_score:.2f}"
        )

    return mismatches
