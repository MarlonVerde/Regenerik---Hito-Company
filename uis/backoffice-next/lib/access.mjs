export const publicViews = ['login', 'register', 'forgot-password', 'reset-password'];
export const userViews = ['incidents', 'account/profile', 'account/change-password'];

export function homeForRole(role) {
  return role === 'admin' ? '/' : '/incidents/';
}

export function canAccessView(role, view) {
  return role === 'admin' || (role === 'user' && userViews.includes(view));
}