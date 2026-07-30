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
            source-data/        27 synthetic .md sources
            data/               working JSON, anchor index, site.css
            postbuild/          required patch scripts
            v2/ v3/             tooling for the v2/v3 maps and personas
            assets/             vendored humanloops-urbina.css
```

Anything outside `site/` is never published, which is why the toolchain and these
docs can live here safely.

## site/ is generated output, not source

Every HTML file in `site/` is produced by `build/build.py`. **Do not hand-edit it
as a fix** - it survives only until the next rebuild. Fixes belong in `build.py`
or in `build/postbuild/`.

Caveat, and it matters: several current fixes exist **only** as post-build patches,
so `build.py` on its own produces a *worse* site than what is committed. Never
rebuild without also running every postbuild script.

## Rebuild

```sh
cd build          # SITE defaults to ../site; BORDERBLEND_SITE overrides it
python build.py --full
python postbuild/mobile-journey.py    ../site   # order matters:
python postbuild/chrome-v2.py         ../site   # v2 after the drawer,
python postbuild/chrome-v3.py         ../site   # v3 after v2
python postbuild/persona-sim-links.py ../site
python check_links.py
```

All four patches are idempotent and marker-guarded; `chrome-v3.py` refuses to run
before `chrome-v2.py`.

> ### The chain is incomplete — a rebuild does NOT reproduce `site/`
>
> `build.py` emits **no promo banner**. That step was applied straight to the HTML
> before anyone captured it as a script, so it exists only in the committed files.
> `chrome-v2` then finds no banner to transform, reports `no old sizing script
> found`, and `chrome-v3` refuses to run at all. A fresh build comes out roughly
> **16.7KB per page short**: no banner, no dismiss button, no logo.
>
> **Never overwrite `site/` from a bare rebuild.** Build into a scratch directory
> (`BORDERBLEND_SITE=/tmp/x`) and diff before letting anything near `site/`.
> Closing this gap — folding the chrome into `build.py` — is the top open task.

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
  dated verbatim. `check_links.py` validates it (last run: 5,021 links, 0 broken).

## Companion app

Five personas can be interviewed at https://ucloops-demo-v1.vercel.app via
`?agent=<id>`: `omar`, `grace`, `mateo`, `diego`, `tyler`. Ids are **lowercase and
case-sensitive** — a mis-cased id silently lands on the app's overview. Links open
in a new tab so they don't replace the viewer iframe. Source lives at
`D:\DEV\uc-ucloops-ui1`.

## Conventions patches rely on

- Mobile breakpoint is **859px** throughout.
- Body classes vary (`srcpage`, `docwrap`, `jny-wrap`, `prov-hidden`) — match
  `<body\b[^>]*>`, never a literal `<body>`.
- Journey sidebar persona cards carry `data-persona="personaN"` and link to their
  persona page; the agent id is derived from that href, not from N.
- When writing a patch script: develop it against a copy, verify `<div>`/`</div>`
  balance before touching real files, and guard it with its own marker so re-runs
  are safe.
