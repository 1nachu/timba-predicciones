import type { NextConfig } from 'next';

const API_INTERNAL_URL = process.env.API_INTERNAL_URL || 'http://127.0.0.1:5000';

const nextConfig: NextConfig = {
  output: 'standalone',
  compress: true,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: ['react-bootstrap'],
  },
  async headers() {
    return [
      {
        source: '/:all*(png|jpg|jpeg|svg|webp|ico|woff|woff2)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=2592000, stale-while-revalidate=86400',
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_INTERNAL_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
