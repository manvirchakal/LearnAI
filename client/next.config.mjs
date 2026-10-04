/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained server bundle for the Docker image (.next/standalone)
  output: "standalone",
  // /api-backend/* is proxied to the FastAPI backend by app/api-backend/[...path]/route.ts
  webpack: (config) => {
    // react-pdf: pdfjs optionally requires node-canvas, which the browser build never needs
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
