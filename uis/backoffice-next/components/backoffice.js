'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { LayoutDashboard, Truck, Package, ClipboardList, FileBarChart, UserRound, KeyRound, UsersRound, LogOut, RefreshCw } from 'lucide-react';
import { api } from '../lib/api';
import Auth from './auth';
import Dashboard from './dashboard';
import Suppliers from './suppliers';
import Inventory from './inventory';
import Incidents from './incidents';
import { Account, Users } from './account';

const publicViews = ['login', 'register', 'forgot-password', 'reset-password'];
const navigation = [
  ['', 'Resumen', LayoutDashboard], ['suppliers', 'Proveedores', Truck],
  ['inventory/products', 'Productos', Package], ['inventory/orders', 'Movimientos', ClipboardList],
  ['incidents', 'Incidentes', FileBarChart], ['account/profile', 'Perfil', UserRound],
  ['account/change-password', 'Contrasena', KeyRound], ['users', 'Usuarios', UsersRound],
];

export default function Backoffice({ view, resetToken }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setMessage('');
    api('/auth/me').then(me => {
      if (!active) return;
      setUser(me);
      if (view === 'login' || view === 'register') router.replace('/');
    }).catch(error => {
      if (!active) return;
      if (error.status === 401) {
        setUser(null);
        if (!publicViews.includes(view)) router.replace('/login/');
      } else setMessage(error.message);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [view, attempt, router]);

  useEffect(() => {
    function expire() {
      setUser(null);
      if (!publicViews.includes(view)) router.replace('/login/');
    }
    window.addEventListener('brasaland:unauthorized', expire);
    return () => window.removeEventListener('brasaland:unauthorized', expire);
  }, [view, router]);

  async function onLogin() {
    setUser(await api('/auth/me'));
    router.replace('/');
  }

  async function logout() {
    try {
      await api('/auth/logout', { method: 'POST' });
      setUser(null);
      router.replace('/login/');
    } catch (error) { setMessage(error.message); }
  }

  const authView = publicViews.includes(view);
  let content;
  if (!view) content = <Dashboard user={user} />;
  else if (view === 'suppliers') content = <Suppliers />;
  else if (view.startsWith('inventory/')) {
    const parts = view.split('/');
    const mode = parts.at(-1) === 'inbound' ? 'inbound' : parts.at(-1) === 'outbound' ? 'outbound' : parts[1] === 'orders' ? 'history' : 'products';
    content = <Inventory mode={mode} productId={parts[1] === 'products' && /^\d+$/.test(parts[2] || '') ? parts[2] : undefined} />;
  } else if (view === 'incidents') content = <Incidents />;
  else if (view === 'account/profile' || view === 'account/change-password') content = <Account user={user} password={view.endsWith('change-password')} onUpdate={async () => setUser(await api('/auth/me'))} />;
  else if (view === 'users') content = <Users currentUser={user} />;
  else content = <section><h1>Pagina no encontrada</h1><Link href="/">Volver al resumen</Link></section>;

  return <>
    <header className="topbar"><a href="/" className="brand">BRASALAND <span>BACKOFFICE</span></a>
      {user && <div className="session"><span>{user.email}</span><button onClick={logout}><LogOut size={16} /> Salir</button></div>}
    </header>
    <div className={user && !authView ? 'workspace' : ''}>
      {user && !authView && <aside><nav aria-label="Principal">{navigation.filter(([path]) => path !== 'users' || user.role === 'admin').map(([path, label, Icon]) => <Link href={`/${path}${path ? '/' : ''}`} key={path} aria-current={view === path ? 'page' : undefined}><Icon size={18} />{label}</Link>)}</nav><div className="sidebar-note">Brasaland Operations</div></aside>}
      <main aria-busy={loading}>
        {loading ? <p role="status" className="muted">Cargando sesion...</p> : authView || !user ? <Auth view={authView ? view : 'login'} resetToken={resetToken} onLogin={onLogin} /> : content}
        {message && <div role="alert" className="notice">{message}<button onClick={() => { setMessage(''); setAttempt(value => value + 1); }} title="Reintentar"><RefreshCw size={16} /></button></div>}
      </main>
    </div>
  </>;
}