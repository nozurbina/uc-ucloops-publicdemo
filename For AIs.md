# For AIs — BorderBlend evidence map handover

Read this before changing anything in this repository. It exists because several
things here are counter-intuitive and will waste your time or silently destroy
work if you assume the obvious.

Written 2026-07-29. Rebuild chain closed and re-verified 2026-07-30.

---

## 1. The one thing you must not get wrong

**Every HTML file in `site/` is generated output. Editing it by hand is a dead
end** — the next rebuild overwrites it.

```
build/source-data/   27 synthetic .md sources
        │
        ▼
build/build.py  +  build/postbuild/*.py
        │
        │  writes 44 HTML files
        ▼
site/                          <- the published artifact
        │
        │  ai-projects-publisher MCP, pointed at site/
        ▼
urbinaconsulting.com/shares/ucloops/borderblend/
```

As of 2026-07-29 this repo is **self-contained** — generator, source data, working
JSON and patches all moved in from the uc-pharma-analysis workspace where
BorderBlend was first built. There is no longer any outside dependency.

The `site/` + `build/` split exists for a specific reason: the publisher ships the
entire folder it is pointed at, with no exclude option. Pointing it at `site/`
keeps the toolchain, the source data and these docs off the live site.

If a fix belongs in the output, it belongs in `build.py` or a post-build patch.

A rebuild now reproduces `site/` — see §3. That was not true before 2026-07-30, and
the habit that gap taught is still the right one: build into a scratch directory and
diff before letting anything near the published folder.

## 2. Where everything is

| Thing | Location |
|---|---|
| This repo | `D:\DEV\uc-ucloops-publicdemo` · `github.com/nozurbina/uc-ucloops-publicdemo` |
| Published artifact | `site/` — **publish this folder, not the repo root** |
| Generator | `build/build.py` |
| Synthetic sources | `build/source-data/` (27 .md) |
| Working data | `build/data/` (JSON, anchor-index, CANON.md) |
| Stylesheet sources | `build/assets/` — composed by `build/styles.py`, not a file on disk |
| Shared top chrome | `build/chrome.py` (banner + sticky bar markup and scripts) |
| Post-build patches | `build/postbuild/` (two left, both journey-map only) |
| v2/v3 tooling | `build/v2/`, `build/v3/` |
| Link validator | `build/check_links.py` |
| Companion chat app | `D:\DEV\uc-ucloops-ui1` · `github.com/nozurbina/uc-ucloops-ui1` |
| Live site | https://urbinaconsulting.com/shares/ucloops/borderblend/ |
| Live app | https://ucloops-demo-v1.vercel.app |

Split out of `uc-pharma-analysis` on 2026-07-29 (fresh history; older commits stay
there), and made fully self-contained the same day — the generator, source data and
patches were moved across and removed from the analysis repo, so there is one copy
rather than two that drift. The companion app was already self-contained.

Nothing here reads from the analysis workspace any more. If you find a path
pointing at it, that is a bug.

## 3. Rebuilding

```sh
cd build          # SITE defaults to ../site; BORDERBLEND_SITE overrides it
python build.py --full                          # 35 files: sources, insights, v1 personas/journeys, index
python v3/render_personas_v3.py                 # 5 files: the v3 persona pages
python postbuild/mobile-journey.py    ../site   # journey maps only
python postbuild/persona-sim-links.py ../site   # journey maps + v3 persona pages
python check_links.py                           # 6,461 internal links, expect 0 broken
```

Both postbuild scripts are idempotent (markers `uc-mobile-drawer`,
`uc-persona-sim`), so re-running is safe and a partial run can be resumed. Order is
no longer load-bearing between them; `persona-sim-links` must run *after* the v3
persona renderer, because that renderer rewrites those five files.

**Four of the 44 files have no generator**: `journey-map-{late-night,business-lunch}-{v2,v3}.html`.
They were authored on `journey-map-template.html` through the ucLoops prompt chain
and are patched forward, never regenerated. `build/v2/` and `build/v3/patch_v3_maps.py`
are the tooling that produced them. Everything else rebuilds from source.

### How this used to be broken, and the habit to keep

Until 2026-07-30, `build.py` emitted no promo banner at all — that step had been
applied straight to the HTML in an earlier session and never captured as a script.
`chrome-v2.py` therefore found nothing to transform, `chrome-v3.py` refused to run
after it, and a fresh build came out ~17KB per page short. `site/` was the only
complete copy of the chrome layer, so a bare rebuild would have destroyed it.

Closing it turned up four further divergences worth knowing about, because they are
the shape of drift this repo produces:

- The stylesheet had five rule fixes that existed only in the published HTML.
- The sticky bar's markup had changed (arrow + label inside the link).
- `build.py` still emitted a legacy `<a class="home">` nav link nothing wanted.
- The v3 persona renderer had lost the headshot `<img>`, and its published pages
  carried a stickybar that had drifted from build.py's copy.

All of it came from the same cause: a fix applied to output instead of to source.
**So: still build into a scratch directory and diff before touching `site/`.**

```sh
BORDERBLEND_SITE=/tmp/x python build.py --full   # then diff /tmp/x against site/
```

A clean run differs from `site/` in nothing. If your diff shows anything you did
not intend, that is the signal — not noise.

`postbuild/README.md` explains the two remaining patches and why they still exist.

## 4. Publishing

Via the `ai-projects-publisher` MCP. It is a WordPress REST integration — **not
FTP**, and there is no filesystem path you can reach.

1. `preview_project_publish` — read-only, returns `base_revision` + `local_revision`
2. Show the user the changes and get approval
3. `publish_project` with that exact revision pair

Non-negotiables:

- **Preview before publish, always.** The publish call requires revisions from a
  real preview; never invent them.
- Describe a preview in conditional language. Nothing has changed yet.
- **The publisher's granted roots must include this checkout.** It refuses source
  folders outside them. From a session rooted in the analysis repo it cannot see
  this folder any more — open `D:\DEV\uc-ucloops-publicdemo` as the workspace.
- Publishing is **incremental**. A one-file edit previews as `1 update, 49
  unchanged` and uploads only that file. There is no need to avoid republishing.
- **Point it at `<repo>/site`**, never the repo root. The publisher ships the whole
  folder it is given and has no exclude option, so the root would push the
  toolchain, the synthetic sources and these docs onto the live site. Publishing
  `site/` is the entire reason for the split.

Credentials are DPAPI-encrypted per Windows user in
`C:\Users\nozno\Documents\Codex\2026-07-10\g\tools\ai-projects\publish.local.json`.
If you see `rest_forbidden` / 401, the stored application password is wrong. If you
see DPAPI "Key not valid for use in specified state", the credential needs
re-encrypting via `setup-publisher.ps1` (interactive — the user must run it).

## 5. The viewer changes how these pages render

This is the single most misleading thing about this project. Published pages are
served inside an iframe by an AI-projects viewer that:

1. **Hides our `.stickybar`** (`display:none !important`) and rebuilds an
   equivalent bar in the *parent* page, above the iframe.
2. **Auto-sizes the iframe to content height** via `postMessage` + `ResizeObserver`.
   There is therefore no independent viewport inside the iframe.
3. Intercepts link clicks and the provenance toggle via `postMessage`.
4. Injects a `<base href>` and a frame script — the served file is ~4KB larger
   than the local one. That difference is expected, not corruption.

Consequences you must internalise:

- **`position: fixed` is pointless inside the iframe** and actively harmful: any
  `body{padding-top}` reserving space for "floating" chrome becomes a visible
  empty band. This is exactly what caused the white band above the promo banner.
  The chrome is now a single `position: sticky` wrapper (`.uc-chrome`) with both
  bars in normal flow. **Do not convert it back to fixed.**
- Sticky has a knock-on cost: being in normal flow, the chrome inherits `body`'s
  `max-width:72rem`, so it stopped stretching. It is pulled full-bleed with
  negative margins plus a JS-published `--half-vw`. Read `postbuild/README.md`
  before editing that — `width:100vw` and a bare `50vw` each introduce their own
  off-by-a-scrollbar defect.
- **`.svg` is served as `application/octet-stream`** by this host, which browsers
  will not render in an `<img>`; the banner logo is a base64 data URI for that
  reason. `.jpg` is served correctly. A 200 and correct bytes do **not** mean an
  image will display — check the content type.
- `100vh` inside the iframe resolves against the iframe's own auto height, which
  is close to circular. Be suspicious of viewport-height maths here.
- Layout bugs may be **unreproducible locally** and vice versa. Always check the
  wrapped page, not just the file.

### Verifying live content — two traps

**Trap 1: the wrapper is not the content.** `…/shares/ucloops/borderblend/x.html`
returns the viewer page (WordPress chrome, ~190–240KB). To inspect what you
actually published, use the raw path:

```
https://urbinaconsulting.com/_ai-projects/raw/shares/ucloops/borderblend/<file>
```

Grepping the wrapper for your markup will return 0 hits and look like a failed
publish.

**Trap 2: HTTP status is meaningless on that host.** It returns **200 for missing
paths** — a made-up filename returns the same wrapper page. Never use a 200 to
conclude a file exists, or a deleted file's 200 to conclude deletion failed. Diff
content instead.

## 6. Verify visually — you have a browser

Chrome is installed and headless works. Use it; do not reason about CSS from the
source when you can look.

```sh
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1280,900 --screenshot=/tmp/shot.png \
  "file:///d/DEV/uc-ucloops-publicdemo/index.html"
```

Then read the PNG. For live pages add `--virtual-time-budget=15000`.

**Chrome enforces a minimum window width of roughly 512px on Windows.** Asking for
`--window-size=420,…` renders at 512 and crops the PNG to 420. This looks exactly
like broken horizontal overflow and is not. Verify widths by measuring, not by
eye.

For real numbers, append a probe to a copy of the page that writes measurements
into `document.title`, then read it back:

```sh
# in the page copy, before </body>:
# <script>window.addEventListener("load",function(){
#   document.title="M"+JSON.stringify({vw:innerWidth,
#     docScrollW:document.documentElement.scrollWidth});});</script>
"$CHROME" --headless=new --disable-gpu --window-size=512,900 \
  --virtual-time-budget=8000 --dump-dom "file:///…/measure.html" \
  | grep -o 'M{.*}'
```

This is how the white band and the phantom overflow were finally settled. Prefer
it over inference.

## 7. The companion app

`D:\DEV\uc-ucloops-ui1` → https://ucloops-demo-v1.vercel.app

Five personas here can be interviewed in that app. Pages link to it with
`?agent=<id>`:

| Persona page | `?agent=` | Name |
|---|---|---|
| `persona-omar-v3.html` | `omar` | Omar |
| `persona-grace-v3.html` | `grace` | Grace |
| `persona-late-night-foodie-v3.html` | `mateo` | Mateo |
| `persona-franchisee-v3.html` | `diego` | Diego |
| `persona-everyday-20s-v3.html` | `tyler` | Tyler |

Plus two assistants in the app only: `ux`, `data`.

- **Ids are lowercase and the parser is case-sensitive.** `?agent=OMAR` silently
  falls back to the app's overview. Generate lowercase.
- The app defaults to a full-page ucLoops overview; a valid `?agent=` skips it and
  opens that conversation directly.
- Links are `target="_blank"` on purpose — same-tab navigation would replace the
  iframe content inside the viewer.
- The app is behind a shared password gate, so an unauthenticated fetch of it
  returns the gate, not the app.

App facts worth knowing before touching it: model `claude-haiku-4-5`; 15 turns per
persona conversation, 25 per assistant; attachments 3 × 1MB; per-IP cap 60 model
calls per 3 days; global cap 300 calls/day (`DEMO_DAILY_CALL_CAP`), enforced via
Upstash and **failing open** if Upstash is unreachable. Server env vars:
`ANTHROPIC_API_KEY`, `DEMO_PASSWORD`, `CHAT_SESSION_SECRET`,
`DEMO_DAILY_CALL_CAP`, and Upstash creds under **either** `UPSTASH_REDIS_REST_*`
**or** `KV_REST_API_*` (Vercel's marketplace integration injects the latter). The
API key must never be `VITE_`-prefixed — that would ship it to the browser.

## 8. Content rules

**Everything here is synthetic.** BorderBlend is a fictional cross-border taco
brand; the interviews, app logs, tickets, social posts and market research in
`sources/` were generated for this demonstration.

- **Never introduce real client, company, or person names into this repo.** It is
  a public-facing demonstration artifact. The parent analysis project mines real
  pharma engagements and its `OUTPUT/final/` uses codenames; none of that belongs
  here. Verified clean at split time: zero occurrences of any real client name,
  any codename, or the word "pharma".
- **Framing.** BorderBlend is a *winning, growing challenger brand*. Frame
  frictions — schedule reliability, app/POS, French localisation lateness,
  fusion-vs-traditional clarity, brand compliance — as **obstacles to extending a
  lead and scaling**, never as failure or deficit. Franchisees are invested
  partners; consumers are enthusiasts. No mopey or victim tone. This mirrors the
  parent project's standing rule and applies to any content you generate here.

## 9. Structure and conventions

| Path | What |
|---|---|
| `index.html` | Entry point — the evidence map |
| `insights.html` | 36 insights, each linked to sources |
| `persona-*-v3.html` | Current personas (5) |
| `journey-map-*-v3.html` | Current journey maps (2) |
| `journey-map-*-v2.html` | Earlier journey maps, kept for progression |
| `persona-*.html` (no `-v3`) | Earlier personas, kept for progression |
| `sources/` | 27 source docs — interviews, logs, tickets, social, market research |
| `headshots/` | Persona portraits |

The invariant the whole thing exists to demonstrate: **every claim deep-links to
its evidence.** A persona line links to the insight it rests on; each insight
links down to the dated verbatim. Every ID is itself a link, and links target a
specific `#anchor`, never a page top. `check_links.py` validates this — last run
(2026-07-30) reported 6,461 internal links, 0 broken. Don't break the chain.

Markup conventions that patches depend on, so change them carefully:

- `.uc-chrome` wraps the promo banner + sticky bar as one sticky element, emitted
  by `build/chrome.py`. Banner first, bar second, on every page — DOM order used to
  differ by page type and a patch had to normalise it. Don't reintroduce the split.
- Body classes vary: `srcpage`, `docwrap`, `jny-wrap`, `prov-hidden`. Match
  `<body\b[^>]*>`, never the literal `<body>`.
- Journey sidebar persona cards carry `data-persona="personaN"` and link to their
  persona page; patches derive the agent id from that href rather than from N.
- Mobile breakpoint is **859px** everywhere (drawer, banner layout, grid scroll).

## 10. Known state and open work

Done and verified live: chrome rebuild (no white band), full-bleed banner, logo via
data URI, close button clear of Learn more at every width, banner dismiss remembered
across pages via `localStorage`, narrow-screen banner layout (no logo, copy above
button), mobile drawer on journey maps with desktop auto-close suppressed, stage
grid scrollable on mobile, persona chat links and Launch AI Persona Sim buttons.

Geometry was verified by measurement, not eye: 6 page types x 3 widths
(1600/1100/700), asserting the chrome spans exactly the client width, no horizontal
overflow, the close/button gap stays positive (min 39px), and the logo actually
decodes (`naturalWidth > 0`).

Closed 2026-07-30: the chrome now comes out of `build/chrome.py` at generation
time, the stylesheet is composed from `build/assets/` by `build/styles.py`,
`chrome-v2.py` and `chrome-v3.py` are deleted, and a scratch rebuild diffs clean
against `site/`. The v3 persona pages regained their headshots and are generated
from `build/v3/persona-v3-*.json` again. One live broken link
(`index.html` -> `persona-mateo-v3.html`, which never existed) is fixed.

Open:

- **The two remaining patches still patch generated HTML** —
  `mobile-journey.py` and `persona-sim-links.py`. They survive because their targets
  include the four hand-authored journey maps, which have no generator to fold them
  into. If those maps ever get one, both patches should go the same way the chrome
  patches did.
- **`assets/chrome.css` is three layered blocks that fight each other** with
  `!important` — part 1 sets `position:fixed` and `body{padding-top}`, parts 2-3
  override both. Flattening it into one block is safe but must be done with
  before/after screenshots at 1600/1100/700; the comment at the top of part 1 says
  the same thing.
- **v2 journey maps have no persona action row** at all, so they got no chat link.
  Their drawer subtitle still reads "Focus or hide…", which is accurate for them.
  If they matter, the action row needs building.
- **Older non-`v3` persona pages got no launch button** —
  `persona-business-lunch.html` covers Omar *and* Grace, so there is no single
  agent to link to.
- **`README.md` and this file publish to the live site** on the next publish.
  Harmless and unlinked, but if unwanted, relocate them.
- In the app: five markdown-output skills are still disabled, and
  `/p-create-page` + `/j-create-page` need download plumbing before they can
  honestly be enabled.

## 11. Habits that paid off here

- **Measure, don't infer.** Two conclusions were wrong until measured: the white
  band (a viewer/iframe interaction, invisible locally) and a "horizontal overflow"
  that was a screenshot crop.
- **Check the artifact, not the report.** A publish call returning `published:
  true` is not evidence the bytes are right. Fetch the raw URL and diff.
- **Test destructive patches on a copy first**, then verify tag balance
  (`<div>`/`</div>` counts) before touching real files. Every patch script here was
  developed that way.
- **Make patches idempotent and marker-guarded.** It makes partial runs resumable
  and re-runs safe.
- Distinguish failure modes before acting. DPAPI error vs 401 pointed at entirely
  different fixes; guessing would have wasted a cycle.
