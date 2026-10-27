'use client';

import { useDeferredValue, useState } from 'react';
import { Pause, Play, RefreshCw, Trash2 } from 'lucide-react';
import { api } from '../lib/api';
import { categories, categoryLabel, CountrySelect, Field, quantity, ResourceState, SubmitForm, useResource } from './ui';

function SupplierRow({ supplier, reload }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function change(path, options) {
    setBusy(true);
    setError('');
    try { await api(`/suppliers/${supplier.id}${path}`, options); reload(); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }
  return <tr><td><strong>{supplier.name}</strong><small>{supplier.contact_email || ''}</small>{error && <p role="alert" className="error-text">{error}</p>}</td>
    <td>{supplier.country}</td><td>{supplier.categories.map(categoryLabel).join(', ')}</td>
    <td><form className="inline-form" aria-label={`Tarifa de ${supplier.name}`} onSubmit={event => {
      event.preventDefault();
      const values = new FormData(event.currentTarget);
      change('/rate', { method: 'PATCH', body: JSON.stringify({ rate_per_unit: Number(values.get('rate')) }) });
    }}><input name="rate" type="number" min="0.01" step="any" defaultValue={supplier.rate_per_unit} aria-label={`Tarifa de ${supplier.name}`} required /><span>{supplier.currency}</span><button disabled={busy} title="Guardar tarifa" aria-label="Guardar tarifa"><RefreshCw size={16} /></button></form></td>
    <td><span className={`badge ${supplier.status === 'active' ? 'active' : ''}`}>{supplier.status === 'active' ? 'Activo' : 'Suspendido'}</span></td>
    <td><div className="row-actions"><button disabled={busy} title={supplier.status === 'active' ? 'Suspender proveedor' : 'Activar proveedor'} aria-label={supplier.status === 'active' ? 'Suspender proveedor' : 'Activar proveedor'} onClick={() => change('/status', { method: 'PATCH', body: JSON.stringify({ status: supplier.status === 'active' ? 'suspended' : 'active' }) })}>{supplier.status === 'active' ? <Pause size={16} /> : <Play size={16} />}</button>
      <button disabled={busy} title="Eliminar proveedor" aria-label="Eliminar proveedor" onClick={() => { if (window.confirm(`Eliminar ${supplier.name}?`)) change('', { method: 'DELETE' }); }}><Trash2 size={16} /></button></div></td>
  </tr>;
}

export default function Suppliers() {
  const [filters, setFilters] = useState({ country: '', category: '', status: '' });
  const [search, setSearch] = useState('');
  const deferredSearch = useDeferredValue(search);
  const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString();
  const resource = useResource(`/suppliers${query ? `?${query}` : ''}`);
  const items = (resource.data?.items || []).filter(item => item.name.toLowerCase().includes(deferredSearch.toLowerCase()));
  async function create(values) {
    const country = values.get('country');
    await api('/suppliers', { method: 'POST', body: JSON.stringify({ name: values.get('name'), country, categories: values.getAll('categories'), rate_per_unit: Number(values.get('rate_per_unit')), currency: country === 'Colombia' ? 'COP' : 'USD', status: 'active', contact_email: values.get('contact_email') || null, notes: values.get('notes') || null }) });
    resource.reload();
    return 'Proveedor creado.';
  }
  return <section><div className="page-heading"><div><div className="eyebrow">DIRECTORIO</div><h1>Proveedores</h1></div><button onClick={resource.reload} title="Actualizar proveedores"><RefreshCw size={16} /> Actualizar</button></div>
    <div className="toolbar"><Field label="Buscar"><input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Nombre del proveedor" /></Field>
      <Field label="Pais"><select value={filters.country} onChange={event => setFilters({ ...filters, country: event.target.value })}><option value="">Todos</option><option>Colombia</option><option>USA</option></select></Field>
      <Field label="Categoria"><select value={filters.category} onChange={event => setFilters({ ...filters, category: event.target.value })}><option value="">Todas</option>{categories.map(value => <option value={value} key={value}>{categoryLabel(value)}</option>)}</select></Field>
      <Field label="Estado"><select value={filters.status} onChange={event => setFilters({ ...filters, status: event.target.value })}><option value="">Todos</option><option value="active">Activo</option><option value="suspended">Suspendido</option></select></Field></div>
    <ResourceState resource={resource}><div className="table-wrap"><table><caption>{quantity(items.length)} proveedores</caption><thead><tr>{['Proveedor', 'Pais', 'Categorias', 'Tarifa', 'Estado', 'Acciones'].map(label => <th key={label}>{label}</th>)}</tr></thead><tbody>{items.map(supplier => <SupplierRow key={supplier.id} supplier={supplier} reload={resource.reload} />)}{!items.length && <tr><td colSpan={6} className="empty">No hay proveedores con estos filtros.</td></tr>}</tbody></table></div></ResourceState>
    <details className="creation"><summary>Nuevo proveedor</summary><SubmitForm onSubmit={create} label="Crear proveedor" reset className="grid-form" name="Nuevo proveedor">
      <Field label="Nombre"><input name="name" required /></Field><Field label="Pais"><CountrySelect name="country" /></Field>
      <Field label="Tarifa por unidad"><input name="rate_per_unit" type="number" min="0.01" step="any" required /></Field><Field label="Email de contacto"><input name="contact_email" type="email" /></Field>
      <fieldset className="category-options"><legend>Categorias</legend>{categories.map(value => <label key={value}><input type="checkbox" name="categories" value={value} />{categoryLabel(value)}</label>)}</fieldset>
      <Field label="Notas"><textarea name="notes" rows={2} /></Field>
    </SubmitForm></details>
  </section>;
}