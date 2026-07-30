import type { Page } from '@playwright/test';

/**
 * The server is rooted at the repo, not at `site/`, for one reason: the viewer
 * fixture in `tests/fixtures/` has to be **same origin** as the pages it frames, or
 * the parent-access the pages rely on (and that we need to assert) is blocked.
 */
export const at = (page: string) => `/site/${page}`;
export const inViewer = (page: string) =>
  `/tests/fixtures/viewer.html?p=${encodeURIComponent('/site/' + page)}`;

/** One of each page type. Add to this rather than hard-coding names in specs. */
export const PAGES = {
  index: 'index.html',
  insights: 'insights.html',
  source: 'sources/BB-INT013.html',
  sourceApplog: 'sources/APPLOG.html',
  factsheet: 'sources/FACT.html',
  personaV3: 'pers-omar-business-lunch-v3.html',
  personaV1: 'pers-business-lunch-v1.html',
  journeyV1: 'journey-late-night-foodie.html',
  mapV3: 'journey-map-business-lunch-v3.html',
  mapLateNight: 'journey-map-late-night-v3.html',
};

/** Every page a reader can reach, for the "this holds everywhere" sweeps. */
export const ALL_PAGE_TYPES = [
  PAGES.index, PAGES.insights, PAGES.source, PAGES.factsheet,
  PAGES.personaV3, PAGES.personaV1, PAGES.journeyV1, PAGES.mapV3,
];

/** Pages carrying a provenance toggle, and what its toggle actually moves. */
export const TOGGLE_PAGES = [
  { page: PAGES.insights, reveals: 'article.insight .evidence' },
  { page: PAGES.source, reveals: '.idbadge' },
  { page: PAGES.personaV3, reveals: '.content .evidence' },
  { page: PAGES.mapV3, reveals: '.journey-grid .evidence' },
];

/**
 * The five persona simulations, keyed by page. The ids are lowercase because the
 * companion app's parser is case-sensitive and silently falls back to its overview.
 */
export const PERSONAS = [
  { page: 'pers-omar-business-lunch-v3.html', agent: 'omar', name: 'Omar' },
  { page: 'pers-grace-business-lunch-v3.html', agent: 'grace', name: 'Grace' },
  { page: 'pers-mateo-late-night-foodie-v3.html', agent: 'mateo', name: 'Mateo' },
  { page: 'pers-diego-franchisee-v3.html', agent: 'diego', name: 'Diego' },
  { page: 'pers-tyler-everyday-20s-v3.html', agent: 'tyler', name: 'Tyler' },
];

/** Height of the chrome, which sticks to the top and is what a jump must clear. */
export const chromeHeight = (page: Page) =>
  page.evaluate(() => {
    const c = document.querySelector('.uc-chrome') as HTMLElement | null;
    return c ? c.offsetHeight : 0;
  });

/**
 * The element `ucKeepPlace` pins: the topmost thing with an id that is on screen.
 * Mirrored here so a test can check the same element the page chose to hold.
 */
export const topmostAnchor = (page: Page) =>
  page.evaluate(() => {
    const chrome = document.querySelector('.uc-chrome') as HTMLElement | null;
    const keep = (chrome ? chrome.offsetHeight : 0) + 24;
    for (const el of Array.from(document.querySelectorAll('[id]'))) {
      const r = el.getBoundingClientRect();
      if (r.height && r.bottom > keep) return { id: el.id, top: Math.round(r.top) };
    }
    return null;
  });

export const rectTop = (page: Page, id: string) =>
  page.evaluate((i) => {
    const el = document.getElementById(i);
    return el ? Math.round(el.getBoundingClientRect().top) : null;
  }, id);

/** Wait for the frame fixture to have measured and laid out at least once. */
export async function viewerReady(page: Page) {
  await page.waitForFunction(() => {
    const v = (window as any).__viewer;
    return v && v.toolbar && v.heights.length > 0;
  }, null, { timeout: 15_000 });
}
