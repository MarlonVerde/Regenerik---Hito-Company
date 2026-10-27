'use client';

import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { quantity, ResourceState, useResource } from './ui';

export default function Dashboard({ user }) {
  const suppliers = useResource('/suppliers');
  const products = useResource('/inventory/products');
  return <section><div className="page-heading"><div><div className="eyebrow">BRASALAND · OPERACIONES</div><h1>Resumen</h1><p className="muted">{user.profile?.name || user.email}</p></div><img className="restaurant-image" src="/uis/web/assets/brasaland-768.webp" alt="Restaurante Brasaland" width={160} height={100} /></div>
    <div className="metrics"><div className="metric"><span>Proveedores</span><ResourceState resource={suppliers}><strong>{quantity(suppliers.data?.total)}</strong></ResourceState></div><div className="metric"><span>Productos</span><ResourceState resource={products}><strong>{quantity(products.data?.length)}</strong></ResourceState></div><div className="metric"><span>Proveedores activos</span><ResourceState resource={suppliers}><strong>{quantity(suppliers.data?.items.filter(item => item.status === 'active').length)}</strong></ResourceState></div></div>
    <h2>Operaciones</h2><div className="operation-links">{[['Proveedores', '/suppliers/'], ['Productos y existencias', '/inventory/products/'], ['Registrar entrada', '/inventory/inbound/'], ['Registrar salida', '/inventory/outbound/'], ['Historial de movimientos', '/inventory/orders/'], ['Analisis de incidentes', '/incidents/']].map(([label, href]) => <Link key={href} href={href}>{label}<ArrowUpRight size={18} /></Link>)}</div>
  </section>;
}