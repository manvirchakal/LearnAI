// Runs before every test file (see vite.config.js's test.setupFiles).
// jest-dom's matchers — toBeInTheDocument, toHaveAttribute, ... — are what
// let a DOM assertion read as one line instead of a manual querySelector.
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';

import { server } from './test/server';

// `onUnhandledRequest: 'error'` is the setting that makes these tests worth
// having: a component that calls an endpoint the test didn't stub fails
// here, instead of quietly receiving undefined and rendering an empty state
// that the assertions might well accept.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
});
afterAll(() => server.close());
