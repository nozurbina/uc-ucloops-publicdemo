# uc-ucloops-publicdemo

The BorderBlend evidence map — a public-facing worked example of the ucLoops
methodology. Personas, journey maps, insights, and the source verbatims behind
them, where every claim deep-links to its evidence.

**Read [`For AIs.md`](For%20AIs.md) before making changes.** It covers the rebuild
pipeline, the publishing flow, and several traps that will otherwise cost you a
cycle each. What follows is the short version.

## Layout

```
site/     the published artifact - the publisher is pointed HERE, not at the repo root
build/    everything that produces it (self-contained; no outside dependencies)
            build.py            generator
            chrome.py           shared top chrome (promo banner + sticky bar)
            naming.py           persona page filenames + legacy redirect map
            styles.py           composes the one stylesheet from assets/
            source-data/        27 synthetic .md sources
            data/               working JSON + anchor index
            assets/             humanloops-urbina.css + supplement.css + chrome.css + logo
            postbuild/          two patches, journey-map targets only
            v2/ v3/             tooling for the v2/v3 maps and personas
```

Anything outside `site/` is never published, which is why the toolchain and these
docs can live here safely.

## site/ is generated output, not source

Every HTML file in `site/` is produced by `build/build.py` (plus the v3 persona
renderer). **Do not hand-edit it as a fix** - it survives only until the next
rebuild, and every hand-edit here has eventually cost someone a day reconstructing
what it changed. Fixes belong in `build.py`, `chrome.py`, `assets/*.css`, or
`build/postbuild/`.

## Rebuild

```sh
cd build          # SITE defaults to ../site; BORDERBLEND_SITE overrides it
python build.py --full                          # 44 files (35 + 9 legacy redirect stubs)
python v3/render_personas_v3.py                 # the 5 v3 persona pages
python postbuild/journey-chrome.py    ../site   # journey maps: chrome, toggle, persona relink
python postbuild/mobile-journey.py    ../site   # journey maps only
python postbuild/persona-sim-links.py ../site   # last: needs the relinked hrefs and the fresh v3 pages
python check_links.py                           # 6,479 links, expect 0 broken
```

A clean rebuild reproduces `site/` exactly - that is the acceptance test, and it was
not true before 2026-07-30. Keep it true: build into a scratch directory
(`BORDERBLEND_SITE=/tmp/x`) and diff against `site/` before letting anything near the
published folder. Anything in that diff you didn't intend is a bug you just caught.

Four files have **no generator** and are patched forward only:
`journey-map-{late-night,business-lunch}-{v2,v3}.html`. They were authored on
`journey-map-template.html` via the ucLoops prompt chain.

## Publishing

Use the `ai-projects-publisher` MCP: `preview_project_publish`, show the user the
changes, get approval, then `publish_project` with the exact revision pair from
that preview. Never invent revisions. Describe a preview in conditional
language — nothing has changed yet.

- The publisher's granted roots must include this checkout, so open **this folder**
  as the workspace when publishing.
- Publishing is incremental; a one-file change uploads one file. Republishing is
  cheap, so don't avoid it.
- Point it at **`<repo>/site`**, not the repo root. That is the whole reason for
  the split: the toolchain, source data and these docs are then never published,
  and no file has to be held aside at publish time.

## Verify the artifact, not the report

- Published pages are wrapped in a viewer iframe. To check what you actually
  published, fetch the **raw** path:
  `https://urbinaconsulting.com/_ai-projects/raw/shares/ucloops/borderblend/<file>`
  Grepping the normal URL returns the WordPress wrapper and looks like a failure.
- **That host returns HTTP 200 for missing paths.** Never infer existence or
  deletion from a status code; diff content.
- The viewer hides our `.stickybar` (rebuilding it in the parent page) and
  auto-sizes the iframe to content height, so `position: fixed` is pointless
  inside it and reserved padding shows up as an empty band. The top chrome is a
  single `position: sticky` wrapper (`.uc-chrome`) for that reason — **do not
  convert it back to fixed.** Because sticky is in normal flow it inherits
  `body`'s 72rem cap, so the chrome is pulled full-bleed by negative margins; see
  `postbuild/README.md` before touching that maths, it has two non-obvious traps.
- **The host serves `.svg` as `application/octet-stream`**, which browsers refuse
  to render in an `<img>`. The banner logo is therefore a base64 data URI. Don't
  "tidy" it back to a file reference — it will silently break. (`.jpg` is served
  correctly, so headshots are normal files.)
- Chrome is installed; take headless screenshots and look at them rather than
  reasoning about CSS from source. Note Chrome's ~512px minimum window width on
  Windows makes narrower screenshots a misleading crop.

## Content rules

- **Everything here is synthetic.** BorderBlend is a fictional brand; all
  interviews, logs, tickets, social posts and research were generated for the
  example.
- **Never introduce real client, company, or person names.** This is a
  public-facing artifact. The parent analysis project handles real engagements and
  anonymises via codenames; none of that belongs here.
- **Framing:** BorderBlend is a *winning, growing challenger brand*. Frame
  frictions as obstacles to extending a lead and scaling — never as failure or
  deficit. Franchisees are invested partners; consumers are enthusiasts. No mopey
  or victim tone. Re-read this before generating any content.
- **Don't break the evidence chain.** Every ID is a link; every link targets a
  specific `#anchor`, never a page top; trails resolve persona → insight →
  dated verbatim. `check_links.py` validates it (last run 2026-07-30: 6,479 links, 0 broken).

## Companion app

Five personas can be interviewed at https://ucloops-demo-v1.vercel.app via
`?agent=<id>`: `omar`, `grace`, `mateo`, `diego`, `tyler`. Ids are **lowercase and
case-sensitive** — a mis-cased id silently lands on the app's overview. Links open
in a new tab so they don't replace the viewer iframe. Source lives at
`D:\DEV\uc-ucloops-ui1`.

## Conventions patches rely on

- Mobile breakpoint is **859px** throughout.
- The top chrome comes from `build/chrome.py` and its CSS from
  `build/assets/chrome.css`. One sticky wrapper, banner then bar, on every page.
- **The viewer reads our sticky bar to build the parent page's toolbar.** It takes
  the back link's `textContent` as its back label and `.sb-title`'s as the toolbar
  title, and its toggle button calls `window.toggleProv(button)` in the frame —
  falling back to flipping `body.prov-hidden`. So: keep the back label short (it is
  `chrome.BACK_LABEL`, arrow included, since a CSS arrow would not survive the copy),
  emit no `.sb-title` at all (the page's `<h1>` is right below it), and define
  `toggleProv` on any page whose provenance works some other way. The journey maps
  didn't, which is why their toggle was dead live and fine locally.
- **A 16px white band above the banner in the viewer is not ours.** The plugin sets
  `#ai-projects-frame{padding-top: toolbar.offsetHeight + 16}` and sizes the iframe
  to `content + 16`. Measured: 71px of padding under a 55px toolbar. Nothing in this
  repo can close it; the fix is in `project-frame.js`.
- **"Evidence trail" is a control**, not just a label — on persona pages and the
  journey legends it calls `ucToggleFromTrail()`, which drives the same toggle.
- Persona pages are `pers-<person>-<archetype>-v<n>.html`, from `build/naming.py`.
  Old names still resolve via generated redirect stubs.
- Body classes vary (`srcpage`, `docwrap`, `jny-wrap`, `prov-hidden`) — match
  `<body\b[^>]*>`, never a literal `<body>`.
- Journey sidebar persona cards carry `data-persona="personaN"` and link to their
  persona page; the agent id is derived from that href, not from N.
- When writing a patch script: develop it against a copy, verify `<div>`/`</div>`
  balance before touching real files, and guard it with its own marker so re-runs
  are safe.
