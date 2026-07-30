# Tests

```sh
npm test                    # chromium + mobile + firefox + webkit (~35s)
npm run test:chromium       # the everyday run
npm run test:mobile         # Pixel 5, for the 859px breakpoint
npx playwright test --grep "keeping your place"
npm run report              # open the HTML report after a failure
```

The server is `python -m http.server` over the **repo root**, not `site/`, and pages
are served at `/site/<page>`. That is deliberate: `fixtures/viewer.html` has to be
same-origin with the pages it frames, or the parent access those pages depend on is
blocked and half the suite cannot run at all.

## What is covered, and why each one exists

Every test here corresponds to something that actually broke. The comments in the
specs say which, because a test whose reason is forgotten is a test someone deletes.

| Spec | Covers |
|---|---|
| `chrome.spec.ts` | Banner + sticky bar on every page type: it exists at all (a rebuild once lost it), it's sticky not fixed, the logo is a data URI that decodes, the back link is short with no restated page name, `toggleProv` is a global, the close button clears "Learn more" and the corner at three widths on three page types, dismissal persists, and nothing scrolls sideways. |
| `provenance.spec.ts` | What the toggle reveals per page type, what it must never hide (an insight's own ID), the labelled key takeaway, **keeping your place** across the height change, channel pills wrapping instead of stretching their column, opportunity references using the site-wide evidence pattern, and "Evidence trail" acting as the control. |
| `evidence-trail.spec.ts` | The invariant the site exists for: journey cell → insight → dated verbatim, all resolving; hover previews; every ID badge being a link; jumps landing clear of the sticky chrome and flashing. |
| `viewer-embed.spec.ts` | The embedded case against the viewer fixture: toolbar label and title, the toolbar toggle reaching into the frame, **no runaway height growth**, journey maps flowing to full height, the pan bar's position and sync, and a click scrolling the parent. |
| `personas.spec.ts` | Each persona page is who its filename says, headshots decode, `?agent=` ids are right, old persona URLs still redirect, the index lists the current set, and the journey legend links each name separately. |
| `mobile.spec.ts` | Phone width: banner sheds its logo, the bar fits, the drawer opens and closes, the stage grid can be panned, and the toggle still keeps your place. |
| `build-integrity.spec.ts` | No browser. Runs `check_links.py` (0 broken), rebuilds into a temp dir and asserts **byte-identical reproduction** of `site/`, checks the four hand-authored maps carry every patch marker plus balanced markup and the live chrome stylesheet, and that nothing links to a pre-rename persona filename. |

## Two things to know before you edit

**`fixtures/viewer.html` is a copy of a contract, not a convenience.** It reproduces
what `wp-content/plugins/ai-projects/assets/project-frame.js` does around our pages —
including two `+ 16`s that look like bugs and are load-bearing for what we test:

- the frame is sized to `max(body.scrollHeight, documentElement.scrollHeight) + 16`,
  which is why a page *shorter* than its frame grows 16px per measurement forever;
- the frame container is padded by `toolbar height + 16`, which is the white band
  above the banner that no amount of work inside the iframe can remove.

Tidying either of those in the fixture would make the tests pass while the live site
stays broken. If the plugin changes, change the fixture to match and say so here.

**The four journey maps have no generator.** Their `<style>` is a frozen copy of the
site CSS, so a fix in `build/assets/` reaches them only because
`postbuild/journey-chrome.py` re-appends the chrome layer. Two tests exist purely to
notice when that stops being true — a marker check and a stylesheet fingerprint check
in `build-integrity.spec.ts`.

## Worth adding next

- A visual snapshot or two (`toHaveScreenshot`) for the banner and a grid cell. Held
  off deliberately: screenshots on Windows have a ~512px minimum window width that
  makes narrow captures a misleading crop, so the baselines want generating in CI.
- A live smoke test against `urbinaconsulting.com/shares/ucloops/borderblend/` after
  publishing, tagged so it never runs in the normal suite. It would have caught the
  dead toolbar toggle a day earlier than a human did.
