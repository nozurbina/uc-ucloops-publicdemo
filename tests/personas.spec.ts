import { test, expect } from '@playwright/test';
import { at, PERSONAS, PAGES } from './utils';

/**
 * Persona pages and their link out to the companion app. The filename carries both
 * the person and the archetype (`pers-mateo-late-night-foodie-v3.html`) precisely so
 * these two can never disagree again — naming a page for the archetype while everyone
 * called him Mateo is what produced a live link to a file that never existed.
 */
test.describe('persona pages', () => {
  for (const { page: target, agent, name } of PERSONAS) {
    test(`${target} is ${name}`, async ({ page }) => {
      await page.goto(at(target));
      await expect(page.locator('.persona-name')).toHaveText(name);

      // The headshot is named after the agent id, so one value covers the photo and
      // the app link. It must actually decode, not just be present.
      const shot = page.locator('.avatar-wrapper img');
      await expect(shot).toHaveAttribute('src', `headshots/${agent}.jpg`);
      expect(await shot.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0);

      // Ids are lowercase because the app's parser is case-sensitive and silently
      // falls back to its overview on anything it doesn't recognise.
      const chat = page.locator('a.sim-launch');
      await expect(chat).toHaveText(/Chat with this persona/);
      await expect(chat).toHaveAttribute('href', `https://ucloops-demo-v1.vercel.app/?agent=${agent}`);
      await expect(chat).toHaveAttribute('target', '_blank');
      await expect(page.locator('.sim-launch-note'))
        .toContainText('is a persona simulation, not a real person');

      // A persona can appear in any number of maps, so it links to none of them.
      await expect(page.locator('.trail-note a[href*="journey-map"]')).toHaveCount(0);
    });
  }

  test('the old persona URLs still resolve', async ({ page }) => {
    // These were live. Each is now a generated stub pointing at the new name; empty
    // naming.LEGACY and they disappear on the next build.
    const legacy = {
      'persona-omar-v3.html': 'pers-omar-business-lunch-v3.html',
      'persona-late-night-foodie-v3.html': 'pers-mateo-late-night-foodie-v3.html',
      'persona-business-lunch.html': 'pers-business-lunch-v1.html',
    };
    for (const [old, expected] of Object.entries(legacy)) {
      // The stub itself, without running its meta refresh.
      const res = await page.request.get(at(old));
      expect(res.status(), old).toBe(200);
      const html = await res.text();
      expect(html, old).toContain(`content="0;url=${expected}"`);
      expect(html, old).toContain(`rel="canonical" href="${expected}"`);

      // And in a browser, it lands you on the new page.
      await page.goto(at(old));
      await expect.poll(() => page.url(), { timeout: 5000 }).toContain(expected);
    }
  });

  test('the index lists every current persona and journey map', async ({ page }) => {
    await page.goto(at(PAGES.index));
    for (const { page: target, name } of PERSONAS) {
      await expect(page.locator(`a.tile[href="${target}"]`), name).toHaveCount(1);
    }
    for (const map of ['journey-map-late-night-v3.html', 'journey-map-business-lunch-v3.html']) {
      await expect(page.locator(`a.tile[href="${map}"]`)).toHaveCount(1);
    }
  });

  test('the journey legend links each persona to their own page', async ({ page }) => {
    // One link used to cover both names and sent Grace's readers to Omar's page.
    await page.goto(at(PAGES.mapV3));
    const legend = page.locator('.trail-legend');
    await expect(legend).toContainText('Evidence trail');
    await expect(legend).not.toContainText('Link trail');
    await expect(legend.locator('a[href="pers-omar-business-lunch-v3.html"]')).toHaveText('Omar');
    await expect(legend.locator('a[href="pers-grace-business-lunch-v3.html"]')).toHaveText('Grace');
  });

  test('journey sidebars offer a chat action per persona', async ({ page }) => {
    await page.goto(at(PAGES.mapV3));
    const chats = page.locator('.persona-card a.chat-btn');
    expect(await chats.count()).toBeGreaterThanOrEqual(2);
    for (const href of await chats.evaluateAll((els) =>
        els.map((e) => (e as HTMLAnchorElement).getAttribute('href')!))) {
      expect(href).toMatch(/^https:\/\/ucloops-demo-v1\.vercel\.app\/\?agent=[a-z]+$/);
    }
  });
});
