/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig