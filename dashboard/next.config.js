/** @type {import('next').NextConfig} */
const nextConfig = {
  // Let Vercel handle the build natively (no static export)
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
