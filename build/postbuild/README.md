# Post-build patches for the BorderBlend site

Three patches are left, and they all exist for the same reason: their targets are the
four journey maps that have **no generator** — `journey-map-{late-night,business-lunch}-{v2,v3}.html`
were authored on `journey-map-template.html` through the ucLoops prompt chain, so
there is nowhere upstream to put the fix. (`persona-sim-links.py` also touches the
five generated persona pages, which is the one exception.)

Run them after every rebuild, in this order:

```sh
python journey-chrome.py    ../site
python mobile-journey.py    ../site
python persona-sim-links.py ../site
```

| Script | Markers | What it does |
|---|---|---|
| `journey-chrome.py` | `uc-journey-chrome`, `uc-journey-perslinks` | Gives the maps the shared sticky bar, defines `toggleProv` so the viewer's toolbar toggle works, folds the per-card "Show references" buttons into the one site-wide toggle, makes in-map reference links scroll + flash their target, and points ~250 persona hrefs per map at the renamed persona pages. |
| `mobile-journey.py` | `uc-mobile-drawer` | Turns the journey maps' fixed 240px sidebar into an off-canvas drawer below 859px, with a backdrop and an "Open personas & filters" bar. Auto-dismiss is gated on `ucIsNarrow()` so desktop never auto-closes. |
| `persona-sim-links.py` | `uc-persona-sim` | Adds the 🗨️ Chat action to v3 journey sidebar persona cards and the **Launch AI Persona Sim** button to v3 persona pages, both deep-linking `?agent=<id>`. |

All are idempotent — each checks its own marker and skips a file that already has
it — so re-running is safe and a partial run can be resumed.

Order matters twice: `journey-chrome.py` relinks the persona hrefs that
`persona-sim-links.py` reads to work out which agent a sidebar card belongs to, and
`persona-sim-links.py` must also run after `v3/render_personas_v3.py`, which rewrites
the five persona pages it patches.

## What used to live here, and why it doesn't

`chrome-v2.py` and `chrome-v3.py` rebuilt the top chrome — promo banner, sticky bar,
dismiss button, full-bleed maths, data-URI logo — by *transforming* markup `build.py`
had already emitted. Deleted 2026-07-30. The chrome is now emitted directly by
`build/chrome.py`, with its CSS in `build/assets/chrome.css`.

They had to go because the arrangement didn't actually work. The banner was never in
`build.py` at all — that step had been applied straight to the HTML in some earlier
session — so `chrome-v2` had nothing to find, failed on all 35 pages with `no old
sizing script found`, and `chrome-v3` then refused to run. A fresh build came out
~17KB per page short, which meant the committed `site/` was the only complete copy of
the chrome layer and a rebuild would have destroyed it.

The general lesson, worth keeping in mind before adding a third patch here: a patch
that *transforms* generated markup is coupled to that markup. When the generator
changes, the patch stops matching and nothing fails loudly. A patch that only
*inserts* (anchored on `<body>`, `</style>`, `</body>`) is much harder to break —
which is why the two survivors are insert-only.

## If you write a new patch anyway

- Develop it against a copy of `site/`, never the real thing.
- Verify `<div>`/`</div>` balance before writing back.
- Guard it with its own marker so re-runs are safe.
- Match `<body\b[^>]*>` — body classes vary (`srcpage`, `docwrap`, `jny-wrap`,
  `prov-hidden`).
- Then ask whether it belongs in `build.py` instead. It usually does.
