// AuthContext is what replaced Amplify's Authenticator. The property worth
// pinning is negative and easy to regress: no token ever touches JS-readable
// storage. The old Home.js read a Cognito token straight out of
// localStorage; the whole point of this rewrite is that the session lives in
// HttpOnly cookies the client cannot see.
import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, test, vi } from 'vitest';

import { AuthProvider, useAuth } from './AuthContext';
import { API, server } from '../test/server';

const ADA = { id: 'u1', email: 'ada@example.com', name: 'Ada Lovelace' };

/** Renders the context's state as text so assertions can read it. */
function Probe() {
  const { user, loading, isAuthenticated } = useAuth();
  if (loading) return <p>loading</p>;
  return (
    <div>
      <p data-testid="authed">{String(isAuthenticated)}</p>
      <p data-testid="email">{user?.email ?? 'none'}</p>
    </div>
  );
}

const renderWithProvider = () =>
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  );

const meReturning = (handler) => http.get(`${API}/auth/me`, handler);

describe('AuthProvider', () => {
  test('mirrors an authenticated session from GET /auth/me', async () => {
    server.use(meReturning(() => HttpResponse.json(ADA)));

    renderWithProvider();

    await waitFor(() => expect(screen.getByTestId('authed')).toHaveTextContent('true'));
    expect(screen.getByTestId('email')).toHaveTextContent('ada@example.com');
  });

  test('a 401 from /auth/me settles as signed-out, not as a stuck spinner', async () => {
    // The anonymous case is the common one — every first visit hits it — and
    // `loading` must still resolve, or the app renders nothing forever.
    server.use(meReturning(() => new HttpResponse(null, { status: 401 })));

    renderWithProvider();

    await waitFor(() => expect(screen.getByTestId('authed')).toHaveTextContent('false'));
    expect(screen.getByTestId('email')).toHaveTextContent('none');
  });

  test('a server error also settles, rather than leaving the app loading', async () => {
    server.use(meReturning(() => new HttpResponse(null, { status: 500 })));

    renderWithProvider();

    await waitFor(() => expect(screen.getByTestId('authed')).toHaveTextContent('false'));
  });

  test('no session material is written to browser storage', async () => {
    server.use(meReturning(() => HttpResponse.json(ADA)));

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('authed')).toHaveTextContent('true'));

    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    // document.cookie sees only non-HttpOnly cookies, so anything readable
    // here would be a session cookie that JS — and therefore XSS — can read.
    expect(document.cookie).toBe('');
  });
});

describe('useAuth', () => {
  test('refuses to be used outside a provider', () => {
    // Otherwise the hook returns undefined and the failure surfaces much
    // later as a destructuring error in whatever component called it.
    // React logs every render error to console.error on its way out, which
    // is just noise when the throw is the assertion.
    const silenced = vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      expect(() => render(<Probe />)).toThrow(/within an AuthProvider/);
    } finally {
      silenced.mockRestore();
    }
  });
});
