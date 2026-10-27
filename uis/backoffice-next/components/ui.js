'use client';

import { cloneElement, useEffect, useId, useState } from 'react';
import { RefreshCw, Save } from 'lucide-react';
import { api } from '../lib/api';

export function useResource(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const reload = () => setRevision(value => value + 1);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setData(null);
    api(path).then(value => { if (active) setData(value); })
      .catch(reason => { if (active) setError(reason.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, revision]);
  return { data, loading, error, reload };
}

export function ResourceState({ resource, children }) {
  if (resource.loading) return <p role="status" className="muted">Cargando datos...</p>;
  if (resource.error) return <div className="notice" role="alert">{resource.error}<button onClick={resource.reload}><RefreshCw size={16} /> Reintentar</button></div>;
  return children;
}

export function Field({ label, children }) {
  const generatedId = useId();
  const id = children.props.id || generatedId;
  return <div className="field"><label htmlFor={id}>{label}</label>{cloneElement(children, { id })}</div>;
}

export function SubmitForm({ onSubmit, children, label = 'Guardar', reset = false, className = '', name }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [failed, setFailed] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true);
    setMessage('');
    try {
      const result = await onSubmit(values);
      setMessage(result || 'Cambios guardados.');
      setFailed(false);
      if (reset) form.reset();
    } catch (error) {
      setMessage(error.message);
      setFailed(true);
    } finally { setBusy(false); }
  }
  return <form onSubmit={submit} aria-label={name} className={className}>
    <fieldset disabled={busy} className="form-fields">{children}
      <div className="form-action"><button type="submit" className="primary"><Save size={16} />{busy ? 'Guardando...' : label}</button></div>
    </fieldset>
    {message && <p className={failed ? 'notice' : 'success'} role={failed ? 'alert' : 'status'}>{message}</p>}
  </form>;
}

export const categories = ['carne', 'verduras_y_hortalizas', 'salsas_y_condimentos', 'bebidas', 'packaging', 'productos_limpieza', 'lacteos', 'carbon_y_combustible'];
export const categoryLabel = value => value.replaceAll('_', ' ');
export const quantity = value => new Intl.NumberFormat('es', { maximumFractionDigits: 2 }).format(value ?? 0);

export function CountrySelect({ inventory = false, ...props }) {
  return <select {...props}><option value={inventory ? 'CO' : 'Colombia'}>Colombia</option><option value={inventory ? 'US' : 'USA'}>USA</option></select>;
}