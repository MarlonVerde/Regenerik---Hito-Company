'use client';

import { api } from '../lib/api';
import { Field, ResourceState, SubmitForm, useResource } from './ui';

export function Account({ user, password = false, onUpdate }) {
  async function save(values) {
    const payload = Object.fromEntries(values);
    if (password) {
      if (payload.new_password !== payload.confirm_password) throw new Error('Las contrasenas no coinciden.');
      await api('/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password: payload.current_password, new_password: payload.new_password }) });
      return 'Contrasena actualizada.';
    }
    await api('/profiles/me', { method: 'PUT', body: JSON.stringify(payload) });
    await onUpdate();
    return 'Perfil actualizado.';
  }
  return <section><div className="eyebrow">MI CUENTA</div><h1>{password ? 'Cambiar contrasena' : 'Perfil'}</h1>
    <SubmitForm onSubmit={save} reset={password} label="Guardar cambios" className="account-form" name={password ? 'Cambiar contrasena' : 'Mi perfil'}>
      {password ? <><Field label="Contrasena actual"><input name="current_password" type="password" autoComplete="current-password" required /></Field><Field label="Nueva contrasena"><input name="new_password" type="password" minLength={8} autoComplete="new-password" required /></Field><Field label="Confirmar contrasena"><input name="confirm_password" type="password" minLength={8} autoComplete="new-password" required /></Field></> : <><p className="muted">{user.email} · {user.role}</p><Field label="Nombre"><input name="name" defaultValue={user.profile?.name || ''} autoComplete="name" required /></Field><Field label="Telefono"><input name="phone" type="tel" defaultValue={user.profile?.phone || ''} autoComplete="tel" /></Field><Field label="Direccion"><input name="address" defaultValue={user.profile?.address || ''} autoComplete="street-address" /></Field></>}
    </SubmitForm>
  </section>;
}

function UserRow({ user, admin, reload }) {
  async function save(values) {
    const payload = { email: values.get('email') };
    if (admin) { payload.role = values.get('role'); payload.is_active = values.get('is_active') === 'true'; }
    await api(`/users/${user.id}`, { method: 'PUT', body: JSON.stringify(payload) });
    reload();
  }
  async function remove() {
    if (!window.confirm(`Eliminar la cuenta ${user.email}?`)) return 'Eliminacion cancelada.';
    await api(`/users/${user.id}`, { method: 'DELETE' });
    reload();
    return 'Cuenta eliminada.';
  }
  return <article className="user-row"><SubmitForm onSubmit={save} label="Actualizar" name={`Usuario ${user.email}`} className="grid-form"><Field label="Email"><input name="email" type="email" defaultValue={user.email} required /></Field>{admin && <><Field label="Rol"><select name="role" defaultValue={user.role}><option>user</option><option>manager</option><option>admin</option></select></Field><Field label="Estado"><select name="is_active" defaultValue={String(user.is_active)}><option value="true">Activo</option><option value="false">Inactivo</option></select></Field></>}</SubmitForm>{admin && <SubmitForm onSubmit={remove} label="Eliminar usuario" name={`Eliminar ${user.email}`} />}</article>;
}

export function Users({ currentUser }) {
  const resource = useResource('/users');
  return <section><div className="eyebrow">ACCESOS</div><h1>Usuarios</h1><ResourceState resource={resource}>{resource.data?.items.map(user => <UserRow key={user.id} user={user} admin={currentUser.role === 'admin'} reload={resource.reload} />)}</ResourceState></section>;
}