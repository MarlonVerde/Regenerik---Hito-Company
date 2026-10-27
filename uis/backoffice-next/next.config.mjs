import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));

const nextConfig = {
  basePath: '/uis/backoffice',
  output: 'standalone',
  outputFileTracingRoot: root,
  turbopack: { root },
  trailingSlash: true,
  poweredByHeader: false,
  experimental: { cpus: 2 },
  async redirects() {
    return [{ source: '/index.html', destination: '/', permanent: false }];
  },
};

export default nextConfig;