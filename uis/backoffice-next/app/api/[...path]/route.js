import { NextResponse } from 'next/server';

const cookieName = 'brasaland_session';
const backend = process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';

async function proxy(request, { params }) {
  const { path } = await params;
  if (path.some(segment => segment === '.' || segment === '..')) {
    return NextResponse.json({ detail: 'Ruta invalida' }, { status: 400 });
  }
  const endpoint = path.join('/');
  if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method)) {
    const origin = request.headers.get('origin');
    const host = request.headers.get('x-forwarded-host') || request.headers.get('host');
    if (origin && new URL(origin).host !== host) {
      return NextResponse.json({ detail: 'Origen no permitido' }, { status: 403 });
    }
  }
  const cookieOptions = {
    httpOnly: true,
    sameSite: 'lax',
    secure: request.headers.get('x-forwarded-proto') === 'https',
    path: '/uis/backoffice',
  };
  if (endpoint === 'auth/logout' && request.method === 'POST') {
    const response = NextResponse.json({ message: 'Sesion cerrada' });
    response.cookies.set(cookieName, '', { ...cookieOptions, maxAge: 0 });
    return response;
  }
  const headers = new Headers();
  const contentType = request.headers.get('content-type');
  if (contentType) headers.set('Content-Type', contentType);
  const token = request.cookies.get(cookieName)?.value;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  try {
    const upstream = await fetch(`${backend}/${path.map(encodeURIComponent).join('/')}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(),
      cache: 'no-store',
      signal: AbortSignal.timeout(30000),
      redirect: 'error',
    });
    if (endpoint === 'auth/login' && upstream.ok) {
      const session = await upstream.json();
      const response = NextResponse.json({ user_id: session.user_id });
      response.cookies.set(cookieName, session.access_token, { ...cookieOptions, maxAge: session.expires_in });
      response.headers.set('Cache-Control', 'no-store');
      return response;
    }
    const response = new NextResponse(upstream.body, { status: upstream.status });
    for (const name of ['content-type', 'content-disposition']) {
      if (upstream.headers.has(name)) response.headers.set(name, upstream.headers.get(name));
    }
    response.headers.set('Cache-Control', 'no-store');
    if (upstream.status === 401 && endpoint !== 'auth/login') {
      response.cookies.set(cookieName, '', { ...cookieOptions, maxAge: 0 });
    }
    return response;
  } catch {
    return NextResponse.json({ detail: 'No se pudo conectar con la API. Intenta de nuevo.' }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };