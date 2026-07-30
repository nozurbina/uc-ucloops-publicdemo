import { test, expect } from '@playwright/test';
import { at, PAGES, TOGGLE_PAGES, topmostAnchor, rectTop } from './utils';

/**
 * The provenance toggle: what it reveals, what it must never hide, and the fact that
 * it changes the page height under the reader.
 */
test.describe('provenance toggle', () => {
  for (const { page: target, reveals } of TOGGLE_PAGES) {
    test(`${target} reveals ${reveals}`, async ({ page }) => {
      await page.goto(at(target));
      const first = page.locator(reveals).first();
      await expect(first).toBeHidden();
      await page.locator('.provtoggle').click();
      await expect(first).toBeVisible();
      await page.locator('.provtoggle').click();
      await expect(first).toBeHidden();
    });
  }

  test('the button says what it will do next', async ({ page }) => {
    await page.goto(at(PAGES.insights));
    const btn = page.locator('.provtoggle');
    await expect(btn).toHaveText(/^Show Item IDs/);
    await btn.click();
    await expect(btn).toHaveText(/^Hide Item IDs/);
  });

  test('an insight keeps its ID when provenance is folded', async ({ page }) => {
    // An insight's ID is its name — every journey cell and persona line cites it — so
    // it is not the kind of thing the toggle should fold away. The evidence under it is.
    await page.goto(at(PAGES.insights));
    await expect(page.locator('article.insight > h3 .idbadge').first()).toBeVisible();
    await expect(page.locator('article.insight .evidence').first()).toBeHidden();
  });

  test('each insight carries a labelled key takeaway, not green italics', async ({ page }) => {
    await page.goto(at(PAGES.insights));
    const imp = page.locator('article.insight .imp').first();
    await expect(imp.locator('.imp-tag')).toHaveText('Key takeaway');
    await expect(imp).toBeVisible();                    // never behind the toggle
    await expect(imp.locator('em')).toHaveCount(0);
  });

  test.describe('keeping your place', () => {
    // Toggling provenance halfway down a long page used to move the text out from
    // under you: ucKeepPlace pins the topmost visible id and puts it back.
    for (const target of [PAGES.insights, PAGES.source, PAGES.personaV3]) {
      test(target, async ({ page }) => {
        await page.goto(at(target));
        for (const y of [1200, 3500]) {
          await page.evaluate((to) => window.scrollTo(0, to), y);
          const anchor = await topmostAnchor(page);
          expect(anchor, 'something with an id should be on screen').not.toBeNull();

          await page.locator('.provtoggle').click();
          const after = await rectTop(page, anchor!.id);
          expect(Math.abs(after! - anchor!.top),
            `${anchor!.id} drifted after toggling at y=${y}`).toBeLessThanOrEqual(4);

          await page.locator('.provtoggle').click();   // back to folded for the next pass
        }
      });
    }
  });

  test('channel pills wrap instead of stretching the column', async ({ page }) => {
    // .channels-tags li is white-space:nowrap, which is right for a pill and wrong
    // once an evidence row goes inside one: measured, the pill grew to 431px inside a
    // 399px cell and overflowed it by 94px.
    await page.goto(at(PAGES.mapV3));
    await page.locator('.provtoggle').click();
    const overflow = await page.evaluate(() => {
      const li = document.querySelector('.channels-tags li')!;
      const cell = li.closest('.grid-cell')! as HTMLElement;
      return { by: cell.scrollWidth - cell.clientWidth,
               wrap: getComputedStyle(li).whiteSpace };
    });
    expect(overflow.wrap).toBe('normal');
    expect(overflow.by).toBeLessThanOrEqual(1);
  });

  test('opportunity references use the site-wide evidence pattern', async ({ page }) => {
    // They used to be a bespoke list with no hover previews, and their own per-card
    // "Show references" button that behaved differently from this toggle.
    await page.goto(at(PAGES.mapV3));
    await expect(page.locator('.refs-toggle')).toHaveCount(0);
    await expect(page.locator('.opp-refs')).toHaveCount(0);

    await page.locator('.provtoggle').click();
    const ev = page.locator('.opportunity-card .evidence').first();
    await expect(ev).toBeVisible();
    await expect(ev).toContainText('In this map →');
    await expect(ev).toContainText('Verbatim →');
    // Same badges, and they carry the same hover preview as everywhere else.
    const ref = ev.locator('a.evref').first();
    await expect(ref.locator('.tip')).toHaveCount(1);
    expect((await ref.locator('.tip').innerText()).length).toBeGreaterThan(20);
  });

  test('"Evidence trail" is the control, not just a label', async ({ page }) => {
    // Folded-ness is expressed differently per page type: the generated pages use
    // body.prov-hidden, the journey maps .journey-grid.show-refs.
    const folded = (p: typeof page) => p.evaluate(() => {
      const grid = document.querySelector('.journey-grid');
      return grid ? !grid.classList.contains('show-refs')
                  : document.body.classList.contains('prov-hidden');
    });
    for (const target of [PAGES.personaV3, PAGES.mapV3]) {
      await page.goto(at(target));
      expect(await folded(page), `${target} should start folded`).toBe(true);
      await page.locator('a.trail-toggle').click();
      expect(await folded(page), `${target}: the trail label should drive the toggle`).toBe(false);
      // It acts on this page, so it must not leave a #hash behind.
      expect(new URL(page.url()).hash).toBe('');
    }
  });
});
