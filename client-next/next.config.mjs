/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Single-origin access to the FastAPI backend (no CORS in the browser)
    return [
      {
        source: "/api-backend/:path*",
        destination: `${process.env.API_URL || "http://localhost:8000"}/:path*`,
      },
    ];
  },
  experimental: {
    // Study-material generation runs several LLM calls; the default 30s proxy timeout is too short
    proxyTimeout: 300_000,
  },
  webpack: (config) => {
    // react-pdf: pdfjs optionally requires node-canvas, which the browser build never needs
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
