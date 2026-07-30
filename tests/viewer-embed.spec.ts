import { test, expect } from '@playwright/test';
import { inViewer, PAGES, viewerReady } from './utils';

/**
 * The embedded case, against `tests/fixtures/viewer.html` — a faithful copy of what
 * the AI-projects WordPress plugin does around our pages.
 *
 * This is where the expensive bugs have lived, all of them from one fact: **the framed
 * document does not scroll.** The parent sizes the iframe to the content height and
 * scrolls its own page, so `position:fixed` pins to the whole frame, `scrollIntoView`
 * is a no-op vertically, and a page shorter than its frame grows forever.
 */
test.describe('inside the viewer', () => {
  test('the toolbar gets a short back label and no repeated title', async ({ page }) => {
    await page.goto(inViewer(PAGES.insights));
    await viewerReady(page);
    const toolbar = await page.evaluate(() => (window as any).__viewer.toolbar);
    expect(toolbar.backLabel).toBe('← Evidence Map');
    expect(toolbar.title).toBe('');          // the page's own <h1> is right below it
    expect(toolbar.hasToggle).toBe(true);
    expect(toolbar.toggleText).toMatch(/^Show Item IDs/);
  });

  test('the toolbar toggle actually toggles provenance in the frame', async ({ page }) => {
    // It posts a message; the injected script calls window.toggleProv(button). The
    // journey maps once defined only toggleItemRefs(), so this did nothing live.
    for (const target of [PAGES.insights, PAGES.mapV3]) {
      await page.goto(inViewer(target));
      await viewerReady(page);
      const frame = page.frameLocator('#ai-projects-frame-content');
      const evidence = frame.locator(
        target === PAGES.mapV3 ? '.journey-grid .evidence' : 'article.insight .evidence').first();
      await expect(evidence).toBeHidden();
      await page.locator('.ai-projects-project-toolbar__toggle').click();
      await expect(evidence, `${target}: toolbar toggle should reach the frame`).toBeVisible();
    }
  });

  for (const target of [PAGES.insights, PAGES.source, PAGES.personaV3, PAGES.mapV3]) {
    test(`${target} settles instead of growing forever`, async ({ page }) => {
      // documentElement.scrollHeight never reports less than the frame's own height,
      // and the viewer sizes the frame to max(body, documentElement) + 16 — so a page
      // shorter than its frame ratchets 16px per measurement, indefinitely. The
      // journey maps did exactly that: they clipped themselves to one screen.
      await page.goto(inViewer(target));
      await viewerReady(page);
      await page.waitForTimeout(2500);
      const heights: number[] = await page.evaluate(() => (window as any).__viewer.heights);
      const growth = heights[heights.length - 1] - heights[0];
      expect(heights.length, `${heights.length} height updates: ${heights.join(' → ')}`)
        .toBeLessThanOrEqual(4);
      expect(growth, `grew ${growth}px: ${heights.join(' → ')}`).toBeLessThanOrEqual(64);
    });
  }

  test('a journey map flows to full height and offers a pan bar', async ({ page }) => {
    await page.goto(inViewer(PAGES.mapV3));
    await viewerReady(page);
    const frame = page.frameLocator('#ai-projects-frame-content');

    // Flow mode, not the fixed-viewport app layout: that is what stops the ratchet.
    await expect(frame.locator('html')).toHaveClass(/uc-embedded/);
    const flowed = await page.evaluate(() => {
      const d = (document.getElementById('ai-projects-frame-content') as HTMLIFrameElement)
        .contentDocument!;
      const c = d.querySelector('.container') as HTMLElement;
      const grid = d.querySelector('.journey-grid') as HTMLElement;
      return { containerH: c.getBoundingClientRect().height, gridH: grid.offsetHeight,
               sidebarPos: d.defaultView!.getComputedStyle(d.querySelector('.sidebar')!).position };
    });
    expect(flowed.containerH).toBeGreaterThan(flowed.gridH * 0.9);
    expect(flowed.sidebarPos).toBe('static');   // fixed would pin it to the whole frame

    // The grid's own scrollbar is now at the bottom of a very tall element, so there
    // has to be a reachable one: full width, at the bottom of the visible band.
    const bar = frame.locator('.uc-panbar');
    await expect(bar).toBeVisible();
    const geometry = await page.evaluate(() => {
      const fr = document.getElementById('ai-projects-frame-content') as HTMLIFrameElement;
      const d = fr.contentDocument!;
      const b = d.querySelector('.uc-panbar') as HTMLElement;
      const r = fr.getBoundingClientRect();
      const visibleBottom = Math.min(window.innerHeight - r.top, r.height);
      return { barTop: parseFloat(b.style.top || '0'), visibleBottom,
               barW: b.clientWidth, spacerW: (b.firstElementChild as HTMLElement).offsetWidth };
    });
    expect(Math.abs(geometry.barTop + 18 - geometry.visibleBottom)).toBeLessThanOrEqual(24);
    expect(geometry.spacerW).toBeGreaterThan(geometry.barW);   // there is a thumb to drag
  });

  test('the pan bar drives the grid, and follows the parent as it scrolls',
    async ({ page }) => {
      await page.goto(inViewer(PAGES.mapV3));
      await viewerReady(page);

      const synced = await page.evaluate(() => {
        const d = (document.getElementById('ai-projects-frame-content') as HTMLIFrameElement)
          .contentDocument!;
        const bar = d.querySelector('.uc-panbar') as HTMLElement;
        const scroller = d.querySelector('.container') as HTMLElement;
        bar.scrollLeft = 250;
        bar.dispatchEvent(new Event('scroll'));
        return scroller.scrollLeft;
      });
      expect(Math.round(synced), 'Firefox reports fractional scroll offsets')
        .toBeCloseTo(250, 0);

      const before = await page.evaluate(() => {
        const d = (document.getElementById('ai-projects-frame-content') as HTMLIFrameElement)
          .contentDocument!;
        return parseFloat((d.querySelector('.uc-panbar') as HTMLElement).style.top || '0');
      });
      await page.evaluate(() => window.scrollTo(0, 2500));
      await expect.poll(async () => page.evaluate(() => {
        const d = (document.getElementById('ai-projects-frame-content') as HTMLIFrameElement)
          .contentDocument!;
        return parseFloat((d.querySelector('.uc-panbar') as HTMLElement).style.top || '0');
      }), { timeout: 10_000 }).toBeGreaterThan(before + 1000);
    });

  test('clicking an evidence link scrolls the parent page', async ({ page }) => {
    // scrollIntoView inside the frame does nothing vertically here, so the page has to
    // scroll the parent itself — computed from the frame's offset and the toolbar height.
    await page.goto(inViewer(PAGES.mapV3));
    await viewerReady(page);
    await page.locator('.ai-projects-project-toolbar__toggle').click();

    await page.evaluate(() => window.scrollTo(0, 0));
    const target = await page.evaluate(() => {
      const d = (document.getElementById('ai-projects-frame-content') as HTMLIFrameElement)
        .contentDocument!;
      // A reference deep in the map, so any scroll is unambiguous.
      const refs = d.querySelectorAll('.opportunity-card .evidence a.evref[href^="#"]');
      const ref = refs[Math.min(refs.length - 1, 20)] as HTMLElement;
      const id = ref.getAttribute('href')!.slice(1);
      ref.click();
      return id;
    });
    expect(target).toBeTruthy();
    await expect.poll(async () => page.evaluate(() => Math.round(window.scrollY)),
      { timeout: 10_000 }).toBeGreaterThan(200);
  });
});
