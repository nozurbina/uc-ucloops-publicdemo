import { test, expect } from '@playwright/test';
import { at, PAGES } from './utils';

/**
 * Phone-width behaviour. The breakpoint is 859px everywhere — drawer, banner layout,
 * grid scrolling — so this project runs on a Pixel 5 (412px) to sit well inside it.
 */
test.describe('on a phone', () => {
  test('the banner sheds its logo and stacks, without sideways scroll', async ({ page }) => {
    await page.goto(at(PAGES.insights));
    await expect(page.locator('.banner-logo')).toBeHidden();
    await expect(page.locator('.promo-btn')).toBeVisible();
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test('the sticky bar still fits its back link and its toggle', async ({ page }) => {
    // This is why the bar carries nothing else: at this width there is no room for a
    // page name as well, and the back link is the part you cannot lose.
    await page.goto(at(PAGES.source));
    const bar = page.locator('.stickybar');
    await expect(bar.locator('.sb-home')).toBeVisible();
    await expect(bar.locator('.provtoggle')).toBeVisible();
    const fits = await bar.evaluate((el) => el.scrollWidth <= el.clientWidth + 1);
    expect(fits).toBe(true);
  });

  test('a journey map opens and closes its persona drawer', async ({ page }) => {
    await page.goto(at(PAGES.mapV3));
    const handle = page.locator('.uc-drawer-handle');
    const sidebar = page.locator('.sidebar');
    await expect(handle).toBeVisible();

    // Off canvas to start: translated out, not merely narrow.
    const offCanvas = await sidebar.evaluate((el) =>
      getComputedStyle(el).transform !== 'none');
    expect(offCanvas).toBe(true);

    await handle.click();
    await expect(page.locator('.uc-drawer-backdrop')).toBeVisible();
    await page.locator('.uc-drawer-close').click();
    await expect(page.locator('.uc-drawer-backdrop')).toBeHidden();
  });

  test('the stage grid can be panned sideways', async ({ page }) => {
    // The drawer patch put overflow-x:hidden on .container so the off-canvas sidebar
    // could not raise a page-level scrollbar; that also clipped the grid, which made
    // every stage after the first unreachable. Asserted as behaviour rather than
    // against a named element: which ancestor scrolls differs between the app layout
    // (.grid-container) and embedded flow mode (.container).
    await page.goto(at(PAGES.mapV3));
    const panned = await page.evaluate(() => {
      const grid = document.querySelector('.journey-grid') as HTMLElement;
      let el: HTMLElement | null = grid.parentElement as HTMLElement;
      while (el && el !== document.documentElement) {
        if (el.scrollWidth > el.clientWidth + 1) break;
        el = el.parentElement as HTMLElement;
      }
      if (!el || el === document.documentElement) return { found: false, moved: 0 };
      const before = grid.getBoundingClientRect().left;
      el.scrollLeft = 300;
      return { found: true, scroller: el.className,
               moved: Math.round(before - grid.getBoundingClientRect().left) };
    });
    expect(panned.found, 'nothing in the grid’s ancestry scrolls horizontally').toBe(true);
    expect(panned.moved).toBeGreaterThan(200);
  });

  test('the provenance toggle still keeps your place', async ({ page }) => {
    await page.goto(at(PAGES.insights));
    await page.evaluate(() => window.scrollTo(0, 2000));
    const before = await page.evaluate(() => {
      const chrome = document.querySelector('.uc-chrome') as HTMLElement;
      const keep = chrome.offsetHeight + 24;
      for (const el of Array.from(document.querySelectorAll('[id]'))) {
        const r = el.getBoundingClientRect();
        if (r.height && r.bottom > keep) return { id: el.id, top: Math.round(r.top) };
      }
      return null;
    });
    expect(before).not.toBeNull();
    await page.locator('.provtoggle').click();
    const after = await page.evaluate((id) =>
      Math.round(document.getElementById(id)!.getBoundingClientRect().top), before!.id);
    expect(Math.abs(after - before!.top)).toBeLessThanOrEqual(4);
  });
});
