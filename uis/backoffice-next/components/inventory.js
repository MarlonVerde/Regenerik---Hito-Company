'use client';

import { useState } from 'react';
import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import { api } from '../lib/api';
import { categoryLabel, CountrySelect, Field, quantity, ResourceState, SubmitForm, useResource } from './ui';

export default function Inventory({ mode = 'products', productId }) {
  const products = useResource('/inventory/products');
  const orders = useResource('/inventory/orders');
  const [search, setSearch] = useState('');
  const [country, setCountry] = useState('');
  const entries = (products.data || []).filter(item => item.name.toLowerCase().includes(search.toLowerCase()) && (!country || item.country === country));
  const product = (products.data || []).find(item => String(item.id) === productId);
  const refresh = () => { products.reload(); orders.reload(); };
  const inbound = mode === 'inbound';
  async function createProduct(values) {
    await api('/inventory/products', { method: 'POST', body: JSON.stringify(Object.fromEntries(values)) });
    refresh();
    return 'Producto creado.';
  }
  async function createOrder(values) {
    const payload = { ...Object.fromEntries(values), ingredient_id: Number(values.get('ingredient_id')), quantity: Number(values.get('quantity')), location_id: Number(values.get('location_id')) };
    await api(`/inventory/orders/${inbound ? 'inbound' : 'outbound'}`, { method: 'POST', body: JSON.stringify(payload) });
    refresh();
    return inbound ? 'Entrada registrada.' : 'Salida registrada.';
  }
  return <section><div className="page-heading"><div><div className="eyebrow">ALMACEN</div><h1>{mode === 'history' ? 'Movimientos' : mode === 'inbound' ? 'Entrada de inventario' : mode === 'outbound' ? 'Salida de inventario' : productId ? 'Detalle de producto' : 'Productos'}</h1></div><button onClick={refresh}><RefreshCw size={16} /> Actualizar</button></div>
    <nav className="subnav" aria-label="Inventario"><Link href="/inventory/products/">Productos</Link><Link href="/inventory/inbound/">Entradas</Link><Link href="/inventory/outbound/">Salidas</Link><Link href="/inventory/orders/">Movimientos</Link></nav>
    <ResourceState resource={products}>
      {mode === 'products' && !productId && <>
        <div className="toolbar"><Field label="Buscar producto"><input type="search" value={search} onChange={event => setSearch(event.target.value)} /></Field><Field label="Pais"><select value={country} onChange={event => setCountry(event.target.value)}><option value="">Todos</option><option value="CO">Colombia</option><option value="US">USA</option></select></Field></div>
        <div className="table-wrap"><table><caption>{entries.length} productos</caption><thead><tr>{['Producto', 'SKU', 'Categoria', 'Pais', 'Existencias'].map(value => <th key={value}>{value}</th>)}</tr></thead><tbody>{entries.map(item => <tr key={item.id}><td><Link href={`/inventory/products/${item.id}/`}>{item.name}</Link></td><td>{item.sku}</td><td>{categoryLabel(item.category)}</td><td>{item.country}</td><td>{quantity(item.current_stock)} {item.unit}</td></tr>)}{!entries.length && <tr><td colSpan={5} className="empty">No hay productos.</td></tr>}</tbody></table></div>
        <details className="creation"><summary>Nuevo producto</summary><SubmitForm onSubmit={createProduct} label="Crear producto" name="Nuevo producto" reset className="grid-form">
          <Field label="Nombre"><input name="name" required /></Field><Field label="SKU"><input name="sku" required /></Field><Field label="Unidad"><input name="unit" placeholder="kg, litro, unidad" required /></Field>
          <Field label="Categoria"><select name="category">{['meat', 'produce', 'sauce', 'beverage', 'packaging', 'cleaning'].map(value => <option key={value}>{value}</option>)}</select></Field><Field label="Pais"><CountrySelect name="country" inventory /></Field>
        </SubmitForm></details>
      </>}
      {productId && (product ? <dl className="detail-grid">{Object.entries({ Producto: product.name, SKU: product.sku, Unidad: product.unit, Categoria: product.category, Pais: product.country, Existencias: quantity(product.current_stock) }).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : <p className="notice">Producto no encontrado.</p>)}
      {(mode === 'inbound' || mode === 'outbound') && <SubmitForm onSubmit={createOrder} label={inbound ? 'Registrar entrada' : 'Registrar salida'} name="Movimiento de inventario" className="grid-form" reset>
        <Field label="Producto"><select name="ingredient_id" required defaultValue=""><option value="" disabled>Selecciona un producto</option>{(products.data || []).map(item => <option value={item.id} key={item.id}>{item.name} ({quantity(item.current_stock)} {item.unit})</option>)}</select></Field>
        <Field label="Cantidad"><input name="quantity" type="number" min="0.001" step="any" required /></Field>
        <Field label="Local"><select name="location_id">{Array.from({ length: 14 }, (_, index) => <option value={index + 1} key={index}>Local {index + 1}</option>)}</select></Field>
        {inbound ? <Field label="Proveedor"><input name="supplier_name" required /></Field> : <Field label="Motivo"><select name="reason"><option value="consumption">Consumo</option><option value="waste">Desperdicio</option></select></Field>}
      </SubmitForm>}
    </ResourceState>
    {(mode === 'history' || productId) && <ResourceState resource={orders}><div className="table-wrap"><table><caption>Historial de movimientos</caption><thead><tr>{['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Unidad'].map(value => <th key={value}>{value}</th>)}</tr></thead><tbody>{(orders.data || []).filter(item => !productId || String(item.ingredient.id) === productId).map(item => <tr key={`${item.movement_type}-${item.id}`}><td>{new Date(item.created_at).toLocaleString('es')}</td><td>{item.ingredient.name}</td><td>{item.movement_type === 'inbound' ? 'Entrada' : 'Salida'}</td><td>{quantity(item.quantity)}</td><td>{item.ingredient.unit}</td></tr>)}{!orders.data?.length && <tr><td colSpan={5} className="empty">No hay movimientos.</td></tr>}</tbody></table></div></ResourceState>}
  </section>;
}