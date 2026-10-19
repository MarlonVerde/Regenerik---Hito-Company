export function buildSummaryViewModel(summary) {
  const totals = summary.totals || {};
  const invalid = summary.invalid_breakdown || {};
  const sat = summary.satisfaction_index || {};

  const cards = [
    ["Total", totals.total_records ?? "—"],
    ["Validos", totals.valid_records ?? "—"],
    ["Invalidos", totals.invalid_records ?? "—"],
    [
      "Promedio satisfaccion",
      sat.average_score != null ? Number(sat.average_score).toFixed(2) : "—",
    ],
  ];

  const invalidHtml = `
    <li>Falta location_id: <strong>${invalid.missing_location_id ?? 0}</strong></li>
    <li>Category faltante/invalida: <strong>${invalid.invalid_or_missing_category ?? 0}</strong></li>
    <li>Description vacia/corta: <strong>${invalid.empty_description ?? 0}</strong></li>
    <li>CLOSED sin satisfaction_score: <strong>${invalid.closed_without_score ?? 0}</strong></li>
  `;

  const satisfactionHtml = `
    <p>Scored cases: <strong>${sat.scored_cases ?? 0}</strong> de <strong>${sat.closed_cases ?? 0}</strong></p>
    <p>Average score: <strong>${sat.average_score != null ? Number(sat.average_score).toFixed(2) : "—"} / 5.00</strong></p>
    <ul>
      ${(sat.distribution || [])
        .map((item) => `<li>Score ${item.score} (${item.label || "—"}): <strong>${item.count ?? 0}</strong></li>`)
        .join("")}
    </ul>
  `;

  const categoryRowsHtml = (summary.breakdown_by_category || [])
    .map(
      (item) =>
        `<tr><td>${item.category || "—"}</td><td>${item.count ?? 0}</td><td>${
          item.percentage != null ? Number(item.percentage).toFixed(1) : "—"
        }%</td></tr>`
    )
    .join("");

  const statusRowsHtml = (summary.breakdown_by_status || [])
    .map(
      (item) =>
        `<tr><td>${item.status || "—"}</td><td>${item.count ?? 0}</td><td>${
          item.percentage != null ? Number(item.percentage).toFixed(1) : "—"
        }%</td></tr>`
    )
    .join("");

  const totalInvalid =
    (invalid.missing_location_id || 0) +
    (invalid.invalid_or_missing_category || 0) +
    (invalid.empty_description || 0) +
    (invalid.closed_without_score || 0);

  return {
    cards,
    invalidHtml,
    satisfactionHtml,
    categoryRowsHtml,
    statusRowsHtml,
    totalInvalid,
    totalInvalidRecords: totals.invalid_records,
  };
}
