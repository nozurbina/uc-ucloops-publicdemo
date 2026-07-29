# uc-ucloops-publicdemo

The BorderBlend evidence map — a public-facing worked example of the ucLoops
methodology. Personas, journey maps, insights, and the source verbatims behind
them, where every claim deep-links to its evidence.

**Read [`For AIs.md`](For%20AIs.md) before making changes.** It covers the rebuild
pipeline, the publishing flow, and several traps that will otherwise cost you a
cycle each. What follows is the short version.

## This repo is generated output, not source

Every HTML file here is produced by a generator in a **different** repository:

```
<analysis>/OUTPUT/interim/borderblend/build.py   ->   this repo   ->   live site
```

where `<analysis>` is
`D:\UC Dropbox\Work\UC\Orgs\ucLoops Projects\UC ucLoops for UC\Pharma\uc-pharma-analysis`.

**Do not hand-edit HTML here as a fix.** It survives only until the next rebuild.
Fixes belong in `build.py` or in `<analysis>/OUTPUT/interim/borderblend/postbuild/`.

Small caveat, and it matters: several current fixes exist **only** as post-build
patches, so running `build.py` on its own produces a *worse* site than what is
committed here. Never rebuild without also running all three postbuild scripts.

## Rebuild (all steps required)

```sh
export BORDERBLEND_SITE=/d/DEV/uc-ucloops-publicdemo
cd "<analysis>/OUTPUT/interim/borderblend"
python build.py --full
python postbuild/mobile-journey.py    "$BORDERBLEND_SITE"   # order matters:
python postbuild/chrome-v2.py         "$BORDERBLEND_SITE"   # v2 after the drawer,
python postbuild/chrome-v3.py         "$BORDERBLEND_SITE"   # v3 after v2
python postbuild/persona-sim-links.py "$BORDERBLEND_SITE"
python check_links.py
```

`BORDERBLEND_SITE` is required — without it the generator writes to a stale
in-repo path. All four patches are idempotent and marker-guarded; `chrome-v3.py`
refuses to run before `chrome-v2.py`.

## Publishing

Use the `ai-projects-publisher` MCP: `preview_project_publish`, show the user the
changes, get approval, then `publish_project` with the exact revision pair from
that preview. Never invent revisions. Describe a preview in conditional
language — nothing has changed yet.

- The publisher's granted roots must include this checkout, so open **this folder**
  as the workspace when publishing.
- Publishing is incremental; a one-file change uploads one file. Republishing is
  cheap, so don't avoid it.
- The whole folder ships, `README.md` and `For AIs.md` included. No exclude option.

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
