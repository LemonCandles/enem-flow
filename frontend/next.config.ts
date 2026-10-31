import type { NextConfig } from 'next';

const config: NextConfig = {
  output: process.env.BUILD_STANDALONE === 'true' ? 'standalone' : undefined,
  async rewrites() {
    const backend = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
    return [{ source: '/api/:path*', destination: `${backend}/:path*` }];
  },
};
export default config;
