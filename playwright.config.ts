import { defineConfig, devices } from '@playwright/test';

/**
 * Tests for the BorderBlend evidence map.
 *
 * Two things shape this config.
 *
 * 1. The site is static files, so a plain Python http.server over `site/` is the
 *    whole test environment. No build step, no API.
 * 2. Almost every bug this site has had lived in the *embedded* case — the pages are
 *    normally viewed inside an iframe on urbinaconsulting.com, where this document
 *    does not scroll and a plugin rewrites the chrome. `tests/fixtures/viewer.html`
 *    reproduces that contract locally so those paths are testable; read the comments
 *    in it before changing anything there.
 *
 * Chromium is the default project because it is what the site is developed and
 * screenshotted against. Firefox and WebKit are defined but only run when asked for
 * (`npx playwright test --project=firefox`), so the everyday run stays fast: they are
 * there to catch the sticky/scroll differences that bite hardest.
 */
const PORT = Number(process.env.PORT || 4173);
// `python` on Windows, `python3` on the CI runner.
const PYTHON = process.env.PYTHON || 'python';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // One local retry on purpose: this suite drives real scrolling in three engines in
  // parallel, and Firefox has a known teardown race (browserContext.close protocol
  // error) under load. A retry distinguishes a flake from a regression; persistent
  // failures still fail.
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]]
                           : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      testIgnore: /mobile\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 1400, height: 900 } },
    },
    {
      // The mobile breakpoint is 859px everywhere; a Pixel 5 sits well inside it.
      name: 'mobile',
      testMatch: /mobile\.spec\.ts/,
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'firefox',
      testIgnore: /mobile\.spec\.ts/,
      use: { ...devices['Desktop Firefox'], viewport: { width: 1400, height: 900 } },
    },
    {
      name: 'webkit',
      testIgnore: /mobile\.spec\.ts/,
      use: { ...devices['Desktop Safari'], viewport: { width: 1400, height: 900 } },
    },
  ],

  webServer: {
    // Rooted at the repo, not at site/: the viewer fixture in tests/fixtures has to
    // be same-origin as the pages it frames, or the parent access those pages rely on
    // is blocked and the embedded half of this suite cannot run at all. Pages are
    // therefore served under /site/ — see tests/utils.ts.
    command: `${PYTHON} -m http.server ${PORT} --directory . --bind 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}/site/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
