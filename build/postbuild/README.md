# Post-build patches for the BorderBlend site

`build.py` generates the site; these scripts then patch the generated HTML.
**Running `build.py` alone produces a site missing all of the fixes below** — it
will have the old broken chrome, no mobile support, and no links to the persona
sim app.

Run all four, in this order, after every full rebuild:

```sh
SITE=/d/DEV/uc-ucloops-publicdemo      # wherever the site repo lives
python mobile-journey.py    "$SITE"
python chrome-v2.py         "$SITE"
python chrome-v3.py         "$SITE"
python persona-sim-links.py "$SITE"
```

Order matters twice over: `chrome-v2.py` must run after `mobile-journey.py`,
because its CSS has to land later in the cascade to win against the drawer's
`!important` height rule; and `chrome-v3.py` refuses to run before `chrome-v2.py`
(it checks for the v2 marker), since it corrects v2's own regressions.

All four are idempotent — each checks for its own marker and skips a file that
already has it — so re-running is safe and a partial run can be resumed.

| Script | Marker | What it does |
|---|---|---|
| `mobile-journey.py` | `uc-mobile-drawer` | Turns the journey maps' fixed 240px sidebar into an off-canvas drawer below 859px, with a backdrop and an "Open personas & filters" bar. Auto-dismiss is gated on `ucIsNarrow()` so desktop never auto-closes. |
| `chrome-v2.py` | `uc-chrome-v2` | Rebuilds the top chrome as **one** `position:sticky` wrapper containing the promo banner and sticky bar. Adds the banner's dismiss button and its narrow-screen layout. Also gives the stage grid its own horizontal scroll. |
| `chrome-v3.py` | `uc-chrome-v3` | Fixes three things v2 left: the banner no longer stretching, the broken logo, and the close button colliding with Learn more. See below. |
| `persona-sim-links.py` | `uc-persona-sim` | Adds the 🗨️ Chat action to v3 journey sidebar persona cards and the **Launch AI Persona Sim** button to v3 persona pages, both deep-linking `?agent=<id>`. |

## What chrome-v3 fixes, and why each is subtle

**The banner stopped stretching.** `body` on most of these pages *is* `.docwrap`,
which sets `max-width:72rem;margin:0 auto`. The original chrome was
`position:fixed;left:0;right:0`, so it escaped that cap; making it sticky in v2 put
it back in normal flow and therefore inside the 72rem column. Fixed with the
full-bleed negative-margin trick, which self-neutralises on the journey maps where
the body is not capped — one rule covers both.

Two traps in that trick, both found by measuring:

- Do **not** also set `width:100vw`. Setting a width alongside both margins
  over-constrains the block, so `margin-right` is dropped and the banner ends a
  scrollbar-width short of the right edge.
- `50vw` counts the scrollbar; `50%` does not. That mismatch overshoots by half a
  scrollbar width — enough to raise a horizontal scrollbar on every vertically
  scrolling page. So the injected script publishes `--half-vw` from
  `documentElement.clientWidth`, with `50vw` kept as the no-JS fallback and
  `overflow-x:clip` on `<html>` containing it in that case. `clip` rather than
  `hidden` — `hidden` would make `<html>` a scroll container and break the sticky
  chrome.

**The logo was broken.** The host serves `.svg` as `application/octet-stream`, and
browsers refuse to render an `<img>` SVG with that content type. `.jpg` is served
correctly as `image/jpeg`, so this is SVG-specific and not a publishing failure —
the bytes were always correct. Switched to a base64 data URI, which carries its own
type and cannot be mis-served. Deliberately **not** inlined as markup: the file
contains `<style>.st0{fill:#fff}</style>` and `id="Layer_2"`, which inlining would
leak into all 44 pages. Costs ~8KB per page.

**The close button collided with Learn more.** It was anchored to the banner's
right edge, which only clears the button on screens wide enough to have a gutter.
Now anchored to `.banner-inner` with reserved padding, so it clears at every width.
Verified: minimum measured gap 39px across six page types at 1600/1100/700.

## Why the chrome needed rebuilding

The generated markup had the promo banner and the sticky bar as two independently
`position:fixed` elements, offset from each other by a JS-measured `--banner-h`,
with `body{padding-top}` reserving room for both. Three values had to agree and
often didn't, which showed up as a white band. Two further faults: the sizing
script sat *between* the two bars, so it measured a `.stickybar` that did not exist
yet; and the non-journey pages used a variant that never set `--banner-h` at all,
which the bar's offset depended on.

Sticky rather than fixed is deliberate. Published pages are viewed inside the
AI-projects viewer, which **hides our `.stickybar`** (it rebuilds it in the parent
page above the iframe) and auto-sizes the iframe to content height. With no
independent viewport, `fixed` buys nothing and the reserved padding becomes a
visible empty band.

DOM order also differs across the set — sources and insights emit the bar first,
journeys and personas the banner — so the wrapper normalises it.

## Worth folding into build.py

These are patches over generated output, which is fragile: a change to `build.py`'s
templates can silently stop a patch from matching. The durable fix is to move all
three into `build.py` so it emits correct markup directly. Until then, treat this
directory as a required build step, not an optional one.
