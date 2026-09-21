import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Bind all interfaces so the container's published port actually reaches
    // the dev server; on loopback it would only be visible inside the container.
    host: true,
  },
  preview: {
    port: 5173,
    host: true,
  },
  build: {
    // Sourcemaps ship: this is a study app, not a product with a secret
    // client bundle, and a readable stack trace from a user's console is
    // worth more than the obscurity.
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
    // Vitest picks up every *.test.* under the project by default, which
    // would include anything vendored into node_modules.
    include: ['src/**/*.test.{js,jsx}'],
  },
});
