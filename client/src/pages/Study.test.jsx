// Study's tabs hide panels with `display: none` instead of unmounting them,
// and that is a deliberate choice with a cost: it keeps four panels alive at
// once. The obvious "tidy-up" is conditional rendering — `{tab === 0 && ...}`
// — which looks identical on screen and silently throws away an in-flight
// narrative stream, a generated game, and the chat history the moment the
// user looks at another tab. These tests are what make that regression
// visible.
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, test } from 'vitest';

import Study from './Study';
import { AuthProvider } from '../context/AuthContext';
import { API, server } from '../test/server';

const COLLECTION_ID = 'col-1';

/** An SSE body in the shape routers/generation.py streams. */
const sse = (...chunks) =>
  HttpResponse.text(chunks.map((c) => `data: ${JSON.stringify({ chunk: c })}\n\n`).join(''), {
    headers: { 'Content-Type': 'text/event-stream' },
  });

/**
 * What the page requests on mount: the collection itself, the chat history
 * (ChatPanel loads eagerly), and /auth/me for NavBar. The narrative is NOT
 * here — it streams on a button press, not on mount.
 */
const mountHandlers = () => [
  http.get(`${API}/api/v1/collections/${COLLECTION_ID}`, () =>
    HttpResponse.json({ id: COLLECTION_ID, name: 'Linear Algebra', material_refs: [] })
  ),
  http.get(`${API}/api/v1/collections/${COLLECTION_ID}/chat`, () => HttpResponse.json([])),
  http.get(`${API}/auth/me`, () => HttpResponse.json({ id: 'u1', email: 'ada@example.com' })),
];

const renderStudy = () =>
  render(
    <AuthProvider>
      <MemoryRouter initialEntries={[`/study/${COLLECTION_ID}`]}>
        <Routes>
          <Route path="/study/:collectionId" element={<Study />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );

/**
 * Whether any ancestor carries the `display: none` a hidden tab panel sets.
 * Read through getComputedStyle, not `node.style`: MUI's `sx` prop compiles
 * to an emotion class, so the inline style attribute is empty.
 */
const isVisible = (element) => {
  for (let node = element; node && node !== document.body; node = node.parentElement) {
    if (window.getComputedStyle(node).display === 'none') return false;
  }
  return true;
};

describe('Study', () => {
  test('loads the collection and names it', async () => {
    server.use(...mountHandlers());

    renderStudy();

    expect(await screen.findByText('Linear Algebra')).toBeInTheDocument();
  });

  test('offers all four kinds of generated material', async () => {
    server.use(...mountHandlers());

    renderStudy();

    await screen.findByText('Linear Algebra');
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual([
      'Narrative',
      'Game',
      'Diagrams',
      'Chat',
    ]);
  });

  test('every panel is mounted from the start, not just the visible one', async () => {
    // Conditional rendering would leave only the Narrative panel in the
    // tree. Each of these buttons belongs to a different panel, and only
    // the first is on the tab currently shown.
    //
    // `hidden: true` is what makes this an assertion about *mounting*:
    // getByRole otherwise searches the accessibility tree, which excludes
    // everything under `display: none`. Querying both ways in one test says
    // the whole thing — the panels exist, and the hidden ones are properly
    // hidden rather than merely off-screen.
    server.use(...mountHandlers());

    renderStudy();
    await screen.findByText('Linear Algebra');

    const mounted = (name) => screen.getByRole('button', { name, hidden: true });
    expect(mounted('Generate narrative')).toBeInTheDocument();
    expect(mounted('Generate a game')).toBeInTheDocument();
    expect(mounted('Generate diagrams')).toBeInTheDocument();

    // Only the active tab's panel is exposed to assistive technology.
    expect(screen.getByRole('button', { name: 'Generate narrative' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Generate a game' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Generate diagrams' })).toBeNull();
  });

  test('switching tabs hides streamed narrative text rather than destroying it', async () => {
    server.use(
      http.get(`${API}/api/v1/collections/${COLLECTION_ID}/narrative`, () =>
        sse('The determinant ', 'measures area.')
      ),
      ...mountHandlers()
    );

    renderStudy();
    await screen.findByText('Linear Algebra');
    fireEvent.click(screen.getByRole('button', { name: 'Generate narrative' }));

    const narrative = await screen.findByText(/determinant measures area/i);
    expect(isVisible(narrative)).toBe(true);

    fireEvent.click(screen.getByRole('tab', { name: 'Game' }));

    // Still in the document — the accumulated stream survived the switch —
    // but no longer shown.
    await waitFor(() => expect(isVisible(narrative)).toBe(false));
    expect(narrative).toBeInTheDocument();
    expect(screen.getByText(/determinant measures area/i)).toBe(narrative);
  });

  test('a failed collection load surfaces an error instead of rendering blank', async () => {
    // The failing handler goes first: MSW resolves with the earliest match,
    // so listing it after mountHandlers() would leave it permanently shadowed.
    server.use(
      http.get(
        `${API}/api/v1/collections/${COLLECTION_ID}`,
        () => new HttpResponse(null, { status: 500 })
      ),
      ...mountHandlers()
    );

    renderStudy();

    expect(await screen.findByRole('alert')).toHaveTextContent(/failed to load/i);
  });
});
