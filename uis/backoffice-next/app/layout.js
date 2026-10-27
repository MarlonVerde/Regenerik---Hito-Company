import './globals.css';

export const metadata = {
  title: 'Brasaland | Backoffice',
  description: 'Operaciones Brasaland',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }) {
  return <html lang="es"><body>{children}</body></html>;
}