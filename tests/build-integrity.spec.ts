import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

/**
 * The two invariants that are about the *repository* rather than the rendered page.
 * They need no browser, but they belong in the same run: they are the checks most
 * likely to catch a change that silently breaks everything downstream.
 *
 * These shell out to the Python toolchain rather than reimplementing it — one source
 * of truth for what "correct" means.
 */
const REPO = path.resolve(__dirname, '..');
const PYTHON = process.env.PYTHON || 'python';
const py = (args: string[], env: Record<string, string> = {}) =>
  execFileSync(PYTHON, args, {
    cwd: path.join(REPO, 'build'),
    encoding: 'utf8',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', ...env },
    maxBuffer: 32 * 1024 * 1024,
  });

test.describe('build integrity', () => {
  test.slow();   // a full rebuild plus a link crawl is not a two-second test

  test('every internal link resolves to a real file and anchor', async () => {
    // 6,000+ links, and the whole point of the site is that they all land somewhere
    // specific. check_links.py also spot-checks the journey → insight → verbatim trail.
    const out = py(['check_links.py']);
    const broken = /BROKEN:\s*(\d+)/.exec(out);
    expect(broken, out).not.toBeNull();
    expect(Number(broken![1]), out).toBe(0);

    const total = /internal links checked:\s*(\d+)/.exec(out);
    expect(Number(total![1])).toBeGreaterThan(6000);
    expect(out).toContain('journey->insight->verbatim intact');
  });

  test('a fresh build reproduces the published site byte for byte', async () => {
    // This was not true until 2026-07-30: the chrome existed only as a postbuild patch
    // over markup the generator no longer emitted, so `site/` was the only complete
    // copy and any rebuild would have destroyed it. Keeping this test green is what
    // stops that happening again.
    const scratch = mkdtempSync(path.join(tmpdir(), 'bb-rebuild-'));
    const env = { BORDERBLEND_SITE: scratch };
    py(['build.py', '--full'], env);
    py([path.join('v3', 'render_personas_v3.py')], env);
    py([path.join('postbuild', 'persona-sim-links.py'), scratch], env);

    const walk = (dir: string, base = ''): string[] =>
      readdirSync(dir).flatMap((name) => {
        const full = path.join(dir, name);
        const rel = base ? `${base}/${name}` : name;
        return statSync(full).isDirectory() ? walk(full, rel) : (rel.endsWith('.html') ? [rel] : []);
      });

    const generated = walk(scratch);
    expect(generated.length, 'the generator should produce the whole set').toBeGreaterThanOrEqual(49);

    const differing = generated.filter((rel) => {
      const built = readFileSync(path.join(scratch, rel));
      const published = readFileSync(path.join(REPO, 'site', rel));
      return !built.equals(published);
    });
    expect(differing, `these differ from site/: ${differing.join(', ')}`).toEqual([]);
  });

  test('the four hand-authored journey maps carry every patch marker', async () => {
    // They have no generator, so their fixes live only in the file. A missing marker
    // means a patch silently stopped applying — the failure mode that started all this.
    const markers = ['uc-journey-chrome', 'uc-journey-perslinks', 'uc-journey-viewport',
                     'uc-journey-oppev', 'uc-journey-css', 'uc-mobile-drawer'];
    const maps = ['journey-map-business-lunch-v2.html', 'journey-map-business-lunch-v3.html',
                  'journey-map-late-night-v2.html', 'journey-map-late-night-v3.html'];
    for (const map of maps) {
      const html = readFileSync(path.join(REPO, 'site', map), 'utf8');
      // Hideable rows + Views ship on the current maps only; v2 stays as-authored.
      const expected = map.includes('-v3') ? [...markers, 'uc-row-collapse'] : markers;
      for (const marker of expected) {
        expect(html.includes(marker), `${map} is missing ${marker}`).toBe(true);
      }
      // Balanced markup: the patches cut and paste whole <div> subtrees.
      const opens = (html.match(/<div\b/g) || []).length;
      const closes = (html.match(/<\/div>/g) || []).length;
      expect(opens - closes, `${map} has unbalanced divs`).toBe(0);
    }
  });

  test('the journey maps carry the live chrome stylesheet, not a stale copy', async () => {
    // They have no generator, so their <style> is frozen at authoring time and every
    // later fix in build/assets/ misses them unless journey-chrome.py re-appends it.
    // Assert the *current* chrome.css is in there, in full.
    const chromeCss = readFileSync(path.join(REPO, 'build', 'assets', 'chrome.css'), 'utf8');
    const fingerprints = chromeCss
      .split(/\r?\n/)
      .filter((l) => /^[.#[a-z@].*\{.*\}$/.test(l.trim()) && l.length < 200)
      .slice(-8);                       // the last few rules: the most recently edited
    expect(fingerprints.length).toBeGreaterThan(3);
    for (const map of ['journey-map-business-lunch-v3.html', 'journey-map-late-night-v3.html']) {
      const html = readFileSync(path.join(REPO, 'site', map), 'utf8');
      for (const rule of fingerprints) {
        expect(html.includes(rule.trim()), `${map} is missing: ${rule.trim().slice(0, 60)}`).toBe(true);
      }
    }
  });

  test('no page hard-codes a stale persona filename', async () => {
    // The rename is easy to half-apply: the maps alone carry ~250 persona hrefs each.
    const stale = /href="persona-[a-z0-9-]+\.html/;
    const dir = path.join(REPO, 'site');
    const files = readdirSync(dir).filter((f) => f.endsWith('.html'));
    for (const f of files) {
      const html = readFileSync(path.join(dir, f), 'utf8');
      if (f.startsWith('persona-')) continue;      // the redirect stubs, which must
      expect(stale.test(html), `${f} still links to an old persona filename`).toBe(false);
    }
  });
});
