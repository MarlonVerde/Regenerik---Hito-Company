import Backoffice from '../../components/backoffice';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { canAccessView, homeForRole, publicViews } from '../../lib/access.mjs';

export const dynamic = 'force-dynamic';

export default async function Page({ params, searchParams }) {
  const { segments = [] } = await params;
  const query = await searchParams;
  const view = segments.join('/');
  const publicView = publicViews.includes(view);
  const token = (await cookies()).get('brasaland_session')?.value;
  if (!token && !publicView) redirect('/login/');
  if (token) {
    const backend = process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';
    const response = await fetch(`${backend}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
      signal: AbortSignal.timeout(10000),
      redirect: 'error',
    });
    if (response.status === 401) {
      if (!publicView) redirect('/login/');
    } else {
      if (!response.ok) throw new Error('No se pudo validar la sesion');
      const user = await response.json();
      if (view === 'login' || view === 'register' || (!publicView && !canAccessView(user.role, view))) {
        redirect(homeForRole(user.role));
      }
    }
  }
  return <Backoffice view={view} resetToken={query.token || ''} />;
}