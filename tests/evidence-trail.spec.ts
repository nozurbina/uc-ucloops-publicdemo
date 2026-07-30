import { test, expect } from '@playwright/test';
import { at, PAGES, chromeHeight } from './utils';

/**
 * The invariant the whole site exists to demonstrate: every claim deep-links to its
 * evidence, and the trail resolves persona → insight → dated verbatim. If these fail,
 * the demo is making a promise it doesn't keep.
 */
test.describe('evidence trail', () => {
  test('a journey cell reaches an insight, and that insight reaches a verbatim',
    async ({ page }) => {
      await page.goto(at(PAGES.mapV3));
      await page.locator('.provtoggle').click();

      const insightLink = page.locator('.journey-grid a.evref[href*="insights.html#INS-"]').first();
      const href = (await insightLink.getAttribute('href'))!;
      const insightId = href.split('#')[1];

      await page.goto(at(href.replace(/^\.\//, '')));
      const insight = page.locator(`article.insight#${insightId}`);
      await expect(insight).toHaveCount(1);

      // …and from the insight down to an actual source line.
      await page.locator('.provtoggle').click();
      const verbatim = insight.locator('a.evref[href*="sources/"]').first();
      const vHref = (await verbatim.getAttribute('href'))!;
      const [file, anchor] = vHref.split('#');
      expect(anchor, 'a verbatim link must target a specific line, never a page top').toBeTruthy();

      await page.goto(at(file));
      await expect(page.locator(`#${anchor}`)).toHaveCount(1);
    });

  test('hovering an evidence badge previews the quote', async ({ page }) => {
    await page.goto(at(PAGES.insights));
    await page.locator('.provtoggle').click();
    const ref = page.locator('article.insight .evidence a.evref').first();
    const tip = ref.locator('.tip');
    await expect(tip).toHaveCount(1);
    await ref.hover();
    await expect(tip).toBeVisible();
    expect((await tip.innerText()).length).toBeGreaterThan(20);
  });

  test('every ID badge is itself a link', async ({ page }) => {
    await page.goto(at(PAGES.source));
    const badges = page.locator('.idbadge');
    expect(await badges.count()).toBeGreaterThan(10);
    const tags = await badges.evaluateAll((els) => els.map((e) => e.tagName));
    expect(new Set(tags)).toEqual(new Set(['A']));
  });

  test.describe('jumping to a target', () => {
    for (const target of [PAGES.insights, PAGES.source]) {
      test(`${target}: lands clear of the chrome and flashes`, async ({ page }) => {
        await page.goto(at(target));
        // Source pages hide their ID badges while provenance is folded, so there is
        // nothing to click until the toggle is on.
        await page.locator('.provtoggle').click();
        const link = page.locator('a[href^="#"]:visible').nth(3);
        const id = (await link.getAttribute('href'))!.slice(1);
        await link.click();

        // The chrome is sticky on top, so landing at 0 means landing underneath it.
        await expect.poll(async () => {
          const top = await page.evaluate((i) => {
            const el = document.getElementById(i);
            return el ? Math.round(el.getBoundingClientRect().top) : -9999;
          }, id);
          return top;
        }, { timeout: 10_000 }).toBeGreaterThanOrEqual(0);

        const height = await chromeHeight(page);
        const top = await page.evaluate((i) =>
          Math.round(document.getElementById(i)!.getBoundingClientRect().top), id);
        expect(top, 'target should not be hidden behind the sticky chrome')
          .toBeGreaterThanOrEqual(height - 4);

        // Something around the target should have been highlighted.
        expect(await page.locator('.flash').count()).toBeGreaterThan(0);
      });
    }
  });

  test('arriving with a hash scrolls and highlights', async ({ page }) => {
    await page.goto(at('insights.html') + '#INS-C05');
    await expect.poll(async () => page.locator('.flash').count(), { timeout: 10_000 })
      .toBeGreaterThan(0);
    const height = await chromeHeight(page);
    const top = await page.evaluate(() =>
      Math.round(document.getElementById('INS-C05')!.getBoundingClientRect().top));
    expect(top).toBeGreaterThanOrEqual(height - 4);
  });

  test('an in-map reference jumps to the item it cites', async ({ page }) => {
    await page.goto(at(PAGES.mapV3));
    await page.locator('.provtoggle').click();
    const ref = page.locator('.opportunity-card .evidence a.evref[href^="#"]').first();
    const id = (await ref.getAttribute('href'))!.slice(1);
    await ref.click();
    await expect(page.locator(`#${id}`)).toHaveCount(1);
    await expect.poll(async () => page.locator('.uc-jump-flash, .flash').count(),
      { timeout: 10_000 }).toBeGreaterThan(0);
  });
});
