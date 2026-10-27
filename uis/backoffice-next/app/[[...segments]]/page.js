import Backoffice from '../../components/backoffice';

export const dynamic = 'force-dynamic';

export default async function Page({ params, searchParams }) {
  const { segments = [] } = await params;
  const query = await searchParams;
  return <Backoffice view={segments.join('/')} resetToken={query.token || ''} />;
}