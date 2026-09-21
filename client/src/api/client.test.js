// The 401-refresh interceptor is the one piece of client code with real
// control flow, and its failure modes are both bad: retry too eagerly and a
// dead session becomes an infinite request loop; don't retry at all and
// every user gets logged out 15 minutes into a session (the access token
// TTL). Neither shows up in a screenshot, so it gets tested here.
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, test } from 'vitest';

import apiClient from './client';
import { API, server } from '../test/server';

// Requests the handlers below actually received, in order — what the
// assertions are really about (how many times, and to where).
let calls = [];

beforeEach(() => {
  calls = [];
});

/** Endpoint that 401s the first `failures` times, then succeeds. */
const flakyEndpoint = (failures) => {
  let seen = 0;
  return http.get(`${API}/api/v1/collections`, () => {
    calls.push('/api/v1/collections');
    seen += 1;
    if (seen <= failures) {
      return new HttpResponse(null, { status: 401 });
    }
    return HttpResponse.json([{ id: 'c1', name: 'Calculus' }]);
  });
};

const refreshReturning = (status) =>
  http.post(`${API}/auth/refresh`, () => {
    calls.push('/auth/refresh');
    return new HttpResponse(null, { status });
  });

describe('401 refresh interceptor', () => {
  test('a 401 is refreshed once and the original request replayed', async () => {
    server.use(flakyEndpoint(1), refreshReturning(200));

    const { data } = await apiClient.get('/api/v1/collections');

    expect(data).toEqual([{ id: 'c1', name: 'Calculus' }]);
    expect(calls).toEqual(['/api/v1/collections', '/auth/refresh', '/api/v1/collections']);
  });

  test('a still-401 replay is not refreshed again', async () => {
    // The loop guard. Without __isRetry, the replay's own 401 would trigger
    // another refresh, and so on until the tab dies.
    server.use(flakyEndpoint(Infinity), refreshReturning(200));

    await expect(apiClient.get('/api/v1/collections')).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(calls).toEqual(['/api/v1/collections', '/auth/refresh', '/api/v1/collections']);
  });

  test('a failed refresh rejects with the original error, not the refresh error', async () => {
    // Callers branch on the original request's failure; surfacing the
    // refresh's own 401 instead would misattribute it to whatever endpoint
    // the user was actually using.
    server.use(flakyEndpoint(Infinity), refreshReturning(401));

    await expect(apiClient.get('/api/v1/collections')).rejects.toMatchObject({
      config: { url: '/api/v1/collections' },
      response: { status: 401 },
    });
    expect(calls).toEqual(['/api/v1/collections', '/auth/refresh']);
  });

  test('a 401 from /auth/refresh itself is never refreshed', async () => {
    server.use(refreshReturning(401));

    await expect(apiClient.post('/auth/refresh')).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(calls).toEqual(['/auth/refresh']);
  });

  test('non-401 failures pass straight through', async () => {
    server.use(
      http.get(`${API}/api/v1/collections`, () => {
        calls.push('/api/v1/collections');
        return new HttpResponse(null, { status: 500 });
      })
    );

    await expect(apiClient.get('/api/v1/collections')).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(calls).toEqual(['/api/v1/collections']);
  });

  test('requests are sent with credentials, since the session is a cookie', () => {
    // Tokens live in HttpOnly cookies and are never readable from JS, so
    // withCredentials is the entire authentication mechanism. If it were
    // ever dropped, every request would simply be anonymous.
    expect(apiClient.defaults.withCredentials).toBe(true);
  });
});
