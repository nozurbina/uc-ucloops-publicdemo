import { test, expect } from '@playwright/test';
import { at, ALL_PAGE_TYPES, PAGES } from './utils';

/**
 * The top chrome — promo banner plus sticky bar — and the contract the viewer reads
 * out of it. Every assertion here corresponds to something that has actually broken:
 * a doubled toolbar label, a dead toggle button, a close button jammed in the corner,
 * and a rebuild that lost the banner altogether.
 */
test.describe('top chrome', () => {
  for (const page of ALL_PAGE_TYPES) {
    test(`${page} has one banner-then-bar chrome`, async ({ page: p }) => {
      await p.goto(at(page));

      // The banner was once missing from every generated page because it lived only
      // in a postbuild patch that had stopped matching. Assert it exists at all.
      const chrome = p.locator('.uc-chrome');
      await expect(chrome).toHaveCount(1);
      await expect(chrome.locator('.promo-banner')).toHaveCount(1);
      await expect(chrome.locator('.promo-close')).toHaveCount(1);

      // Banner first, bar second, always: DOM order used to vary by page type and a
      // patch had to normalise it.
      const order = await chrome.evaluate((el) =>
        Array.from(el.children).map((c) => c.className.split(' ')[0]));
      expect(order[0]).toBe('promo-banner');

      // Sticky, never fixed: inside the viewer there is no independent viewport, so
      // fixed buys nothing and the space reserved for it shows as an empty band.
      await expect(chrome).toHaveCSS('position', 'sticky');

      // The logo must be a data URI. The host serves .svg as
      // application/octet-stream, which browsers refuse to render in an <img>.
      const logo = chrome.locator('img.banner-logo');
      await expect(logo).toHaveAttribute('src', /^data:image\/svg\+xml;base64,/);
      expect(await logo.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0);
    });
  }

  test('back link is short, and the page name is not restated', async ({ page }) => {
    // The viewer uses this link's textContent as its own toolbar label. When the site
    // name was nested inside the link *and* repeated in .sb-title, the toolbar read
    // "←BorderBlend Evidence Map   BorderBlend Evidence Map".
    for (const target of [PAGES.insights, PAGES.source, PAGES.personaV3, PAGES.mapV3]) {
      await page.goto(at(target));
      const home = page.locator('.stickybar .sb-home');
      await expect(home).toHaveText('← Evidence Map');
      await expect(page.locator('.stickybar .sb-title')).toHaveCount(0);
    }
  });

  test('toggleProv is a global on every page with a toggle', async ({ page }) => {
    // The viewer's toolbar button posts a message that calls window.toggleProv(btn)
    // if it exists, and otherwise flips body.prov-hidden. The journey maps key their
    // CSS off .journey-grid.show-refs instead, so without this function their live
    // toggle did nothing at all while working perfectly on localhost.
    for (const target of [PAGES.insights, PAGES.source, PAGES.personaV3, PAGES.mapV3]) {
      await page.goto(at(target));
      await expect(page.locator('.provtoggle')).toHaveCount(1);
      expect(await page.evaluate(() => typeof (window as any).toggleProv))
        .toBe('function');
    }
  });

  test.describe('banner close button', () => {
    // Every page type, because the four journey maps hold a *frozen copy* of the
    // stylesheet: a fix to build/assets/chrome.css reaches them only because
    // journey-chrome.py re-appends it. That is exactly how this button ended up back
    // at top:0;right:0 on the maps two rounds after being fixed everywhere else.
    for (const width of [1600, 1100, 700])
    for (const target of [PAGES.insights, PAGES.mapV3, PAGES.personaV3]) {
      test(`${target} clears "Learn more" and the edges at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 800 });
        await page.goto(at(target));
        const box = await page.evaluate(() => {
          const q = (s: string) => document.querySelector(s)!.getBoundingClientRect();
          return { close: q('.promo-close'), learn: q('.promo-btn'), banner: q('.promo-banner') };
        });
        // Inset from the corner, not flush in it.
        expect(box.close.top - box.banner.top,
          'close button is flush against the top edge').toBeGreaterThanOrEqual(4);
        expect(box.banner.right - box.close.right,
          'close button is flush against the right edge').toBeGreaterThanOrEqual(4);
        // Never overlapping the call to action: either clear horizontally, or on
        // separate rows once the banner stacks.
        const overlaps = box.close.left < box.learn.right && box.close.right > box.learn.left
                      && box.close.top < box.learn.bottom && box.close.bottom > box.learn.top;
        expect(overlaps).toBe(false);
      });
    }
  });

  test('dismissing the banner is remembered across pages', async ({ page }) => {
    await page.goto(at(PAGES.insights));
    await expect(page.locator('.promo-banner')).toBeVisible();
    await page.locator('.promo-close').click();
    await expect(page.locator('.promo-banner')).toBeHidden();

    // The early script applies the class before the banner is parsed, so a dismissed
    // banner never flashes into view on the next page.
    await page.goto(at(PAGES.source));
    await expect(page.locator('.promo-banner')).toBeHidden();
    expect(await page.evaluate(() =>
      document.documentElement.classList.contains('uc-promo-hidden'))).toBe(true);
  });

  test('no page scrolls sideways at any width', async ({ page }) => {
    // The full-bleed chrome is pulled out with negative margins; getting that wrong
    // by half a scrollbar width raises a horizontal scrollbar on every page.
    for (const width of [1600, 1100, 860]) {
      await page.setViewportSize({ width, height: 800 });
      for (const target of [PAGES.index, PAGES.insights, PAGES.source, PAGES.personaV3]) {
        await page.goto(at(target));
        const overflow = await page.evaluate(() =>
          document.documentElement.scrollWidth - document.documentElement.clientWidth);
        expect(overflow, `${target} at ${width}px`).toBeLessThanOrEqual(1);
      }
    }
  });
});
