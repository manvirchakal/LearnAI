// The one frontend test that guards a security property rather than a
// behaviour. GameFrame exists because the old DynamicGameComponent ran
// LLM-written JavaScript through `new Function(...)` in the app's own
// origin; the containment is entirely in how the iframe is configured, and
// that configuration is a single easy-to-"fix" attribute. Adding
// allow-same-origin would make generated game code a first-class citizen
// of the app's origin again — cookies, localStorage, parent DOM, and
// credentialed fetch all back on the table — and nothing else in the suite
// would notice.
import { render, screen } from '@testing-library/react';
import GameFrame from './GameFrame';

// Quote-free on purpose: the shell embeds the game via JSON.stringify (see
// the escaping test below), so a payload with double quotes wouldn't appear
// verbatim in the srcdoc.
const GAME_CODE = "return React.createElement('p', null, 'hello');";

const renderFrame = (javascript = GAME_CODE) => {
  render(<GameFrame javascript={javascript} />);
  return screen.getByTitle('Generated game');
};

describe('game sandbox containment', () => {
  test('the generated game runs in a sandboxed iframe', () => {
    expect(renderFrame()).toHaveAttribute('sandbox', 'allow-scripts');
  });

  test('the sandbox never grants allow-same-origin', () => {
    // Asserted separately from the exact-value check above so the reason
    // survives a legitimate future addition (say allow-pointer-lock for a
    // canvas game): whatever else the token list grows, this token stays
    // out of it, because allow-scripts + allow-same-origin together let
    // the frame reach into the parent and remove its own sandbox.
    const sandbox = renderFrame().getAttribute('sandbox').split(/\s+/);

    expect(sandbox).toContain('allow-scripts');
    expect(sandbox).not.toContain('allow-same-origin');
  });

  test('the frame has no src, so the game only ever arrives via srcDoc', () => {
    // A src pointing at our own origin would defeat the opaque origin the
    // same way allow-same-origin does.
    const iframe = renderFrame();

    expect(iframe).not.toHaveAttribute('src');
    expect(iframe.getAttribute('srcdoc')).toContain(GAME_CODE);
  });

  test('the shell document denies network egress by default', () => {
    // Defence in depth behind the opaque origin: even with scripts
    // allowed, default-src 'none' means the game cannot exfiltrate the
    // material it was generated from to an attacker-controlled host.
    const srcdoc = renderFrame().getAttribute('srcdoc');

    expect(srcdoc).toContain('http-equiv="Content-Security-Policy"');
    expect(srcdoc).toContain("default-src 'none'");
  });

  test('game code is embedded as data, not spliced into the shell script', () => {
    // The shell reads the game through JSON.stringify, so a payload that
    // closes the string and opens a new statement stays a string. If this
    // ever became concatenation, the shell's own privileges (postMessage
    // to the parent) would be reachable by generated code.
    const payload = '";window.__pwned=1;"';

    const srcdoc = renderFrame(payload).getAttribute('srcdoc');

    // Present, but with every quote escaped — so it never breaks out of
    // the string literal the shell hands to `new Function`.
    expect(srcdoc).toContain('\\";window.__pwned=1;\\"');
    expect(srcdoc).not.toContain(payload);
  });
});
