'use client';

import { useState } from 'react';
import { Download } from 'lucide-react';
import { api } from '../lib/api';
import { Field, quantity, SubmitForm } from './ui';

export default function Incidents() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function analyze(values) {
    const file = values.get('file');
    if (!file?.name?.toLowerCase().endsWith('.csv')) throw new Error('Selecciona un archivo CSV.');
    if (file.size > 10 * 1024 * 1024) throw new Error('El archivo supera el limite de 10 MB.');
    const result = await api('/api/incidents/analyze', { method: 'POST', body: values });
    setSummary(result);
    return 'Analisis completado.';
  }
  async function download() {
    setError('');
    setBusy(true);
    try {
      const blob = await api('/api/incidents/results/export');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'results.csv';
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }
  return <section><div className="page-heading"><div><div className="eyebrow">CALIDAD Y SERVICIO</div><h1>Incidentes</h1></div>{summary && <button onClick={download} disabled={busy}><Download size={16} /> Exportar CSV</button>}</div>
    <SubmitForm onSubmit={analyze} label="Analizar CSV" name="Analisis de incidentes" className="upload-form"><Field label="Archivo CSV"><input type="file" name="file" accept=".csv,text/csv" required /></Field></SubmitForm>
    {error && <p role="alert" className="notice">{error}</p>}
    {summary && <div className="analysis"><h2>{summary.source_file}</h2><div className="metrics">{[['Registros', summary.totals.total_records], ['Validos', summary.totals.valid_records], ['Invalidos', summary.totals.invalid_records], ['Satisfaccion', summary.satisfaction_index.average_score ?? 0]].map(([label, value]) => <div className="metric" key={label}><span>{label}</span><strong>{quantity(value)}</strong></div>)}</div>
      <div className="analysis-grid"><div className="table-wrap"><table><caption>Por categoria</caption><thead><tr><th>Categoria</th><th>Casos</th><th>Porcentaje</th></tr></thead><tbody>{summary.breakdown_by_category.map(row => <tr key={row.category}><td>{row.category}</td><td>{row.count}</td><td>{row.percentage}%</td></tr>)}</tbody></table></div>
        <div className="table-wrap"><table><caption>Por estado</caption><thead><tr><th>Estado</th><th>Casos</th><th>Porcentaje</th></tr></thead><tbody>{summary.breakdown_by_status.map(row => <tr key={row.status}><td>{row.status}</td><td>{row.count}</td><td>{row.percentage}%</td></tr>)}</tbody></table></div></div>
      <h2>Registros invalidos</h2><dl className="detail-grid">{Object.entries(summary.invalid_breakdown).map(([label, value]) => <div key={label}><dt>{label.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}</dl>
      <h2>Satisfaccion</h2><div className="table-wrap"><table><thead><tr><th>Puntuacion</th><th>Valoracion</th><th>Casos</th></tr></thead><tbody>{summary.satisfaction_index.distribution.map(row => <tr key={row.score}><td>{row.score}</td><td>{row.label}</td><td>{row.count}</td></tr>)}</tbody></table></div>
    </div>}
  </section>;
}