// One MSW server for the whole suite, intercepting at the network layer
// rather than stubbing axios. That distinction is the point: a test that
// mocks `apiClient.get` proves the component calls a function, while this
// proves it issues the request the backend actually serves — the URL, the
// method, the credentials mode, and the interceptor behaviour in
// api/client.js all stay under test.
//
// Handlers are per-test (`server.use(...)`); this file deliberately
// registers none, so a request no test accounted for fails loudly instead
// of silently returning undefined.
import { setupServer } from 'msw/node';

export const server = setupServer();

export const API = 'http://localhost:8000';
