'use client';

import Link from 'next/link';
import { api } from '../lib/api';
import { Field, SubmitForm } from './ui';

export default function Auth({ view, resetToken, onLogin }) {
  const register = view === 'register';
  const forgot = view === 'forgot-password';
  const reset = view === 'reset-password';
  const title = register ? 'Crear cuenta' : forgot ? 'Recuperar acceso' : reset ? 'Restablecer contrasena' : 'Iniciar sesion';
  async function submit(values) {
    const payload = Object.fromEntries(values);
    if (forgot) {
      const response = await api('/auth/forgot-password', { method: 'POST', body: JSON.stringify(payload) });
      return response.message;
    }
    if (reset) {
      if (payload.new_password !== payload.confirm_password) throw new Error('Las contrasenas no coinciden.');
      await api('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token: resetToken, new_password: payload.new_password }) });
      return 'Contrasena actualizada. Ya puedes iniciar sesion.';
    }
    if (register) {
      if (payload.password !== payload.confirm_password) throw new Error('Las contrasenas no coinciden.');
      await api('/users', { method: 'POST', body: JSON.stringify(payload) });
    }
    await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: payload.email, password: payload.password }) });
    await onLogin();
  }
  return <section className="auth-surface">
    <div className="eyebrow">OPERACIONES BRASALAND</div><h1>{title}</h1>
    {reset && !resetToken ? <p role="alert" className="notice">El enlace no contiene un token de recuperacion.</p> : <SubmitForm onSubmit={submit} label={title} name={title}>
      {register && <Field label="Nombre"><input name="name" autoComplete="name" required /></Field>}
      {!reset && <Field label="Email"><input type="email" name="email" autoComplete="username" required /></Field>}
      {!forgot && <Field label={reset ? 'Nueva contrasena' : 'Contrasena'}><input type="password" name={reset ? 'new_password' : 'password'} autoComplete={register || reset ? 'new-password' : 'current-password'} minLength={8} required /></Field>}
      {(register || reset) && <Field label="Confirmar contrasena"><input type="password" name="confirm_password" autoComplete="new-password" minLength={8} required /></Field>}
    </SubmitForm>}
    <div className="auth-links">
      {view !== 'login' && <Link href="/login/">Iniciar sesion</Link>}
      {view === 'login' && <><Link href="/forgot-password/">Olvide mi contrasena</Link><Link href="/register/">Crear cuenta</Link></>}
    </div>
  </section>;
}