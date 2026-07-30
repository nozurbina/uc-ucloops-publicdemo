# Multi-demo abstraction plan

Goal: run several demos — BorderBlend today, pharma next, others later — where each
demo is a set of raw `.md` sources plus deliverable data, built by **one** shared
toolchain into its own evidence-map site and its own set of chat personas in the
companion app, switchable at runtime.

Written 2026-07-30, after the reproducibility work. Grounded in what both repos
actually contain, not what they should contain. Update the Phases section as phases
complete.

---

## 1. The layer model

The single most important decision. Everything else hangs off it.

```
 A. SOURCES            user-authored .md — transcripts, logs, tickets, factsheet…
    (drifts)           friendly to humans, tolerant parse, warnings not errors
        │  ingest (per-demo, schema-flexible)
        ▼
 B. CASE BUNDLE        normalized JSON + anchor index — the strict layer
    (contract)         every claim has an anchor; ids unique; trail resolves
        │  render (shared, demo-agnostic)
        ▼
 C. OUTPUTS            dist/<demo>/ site  +  app persona bundle
        │  publish / deploy
        ▼
 D. LIVE               shares/ucloops/<demo>/  +  app?demo=<demo>&agent=<id>
```

Key property: **flexibility lives at the A→B boundary, strictness at B.** Users can
restructure their markdown (different persona sections, different journey rows) and
only the ingest step has to cope; the renderers never see the mess. This is also
where "the .md structures will drift" is absorbed: drift produces ingest warnings
and generic sections, never broken pages.

This layering already half-exists. `build.py`'s Pass A *is* an ingest step (md →
anchors + source HTML) and Pass B *is* a render step (JSON → deliverables) — they're
just fused in one 750-line file with BorderBlend names baked in. The abstraction is
mostly a separation, not an invention.

## 2. Transfer format: markdown in, JSON as the working truth

Users author `.md`. That stays — it's the whole pitch ("use the AI tools of your
choice"). But renderers consume only the **case bundle** (layer B), produced by a
load step. The bundle formats are the current JSON shapes, kept as-is because they
already encode the method's concepts and 6,400 working links prove them out:

| Concept | Bundle shape today (keep) |
|---|---|
| Source verbatim | `anchor-index.json`: id → {kind, text, speaker, source_key} |
| Insight | `{id, title, statement, body, category, personas, strength, implication, evidence[]}` |
| Persona (profile) | `{slug, name, role, agent, archetype, sections[{type, items[{text, insights[], evidence[]}]}]}` |
| Journey | `{slug, title, personas[], stages[], rows[], cells{}}` |

### How the ingest flexes

- **File typing by convention, overridable by front-matter.** `TRANSCRIPT_*` /
  `SOURCES_*` naming keeps working; a `---\ntype: transcript\nid: PH-INT001\n---`
  front-matter block wins when present. New demos should use front-matter; the
  BorderBlend files stay untouched.
- **Sections are data, not code.** The v3 persona renderer's `SECT` dict (DEMO,
  MIND, EMOT, VOIC…) becomes a per-demo **section registry** in the manifest: a
  list of `{key, heading-pattern, layout}` entries. A persona with a section the
  registry doesn't name still renders — as a generic list section with a slugged id
  — and the ingest logs "unknown section 'Media Diet' rendered generically." Same
  for journey rows: today's 16-row template is a default registry, not a schema.
- **Anchor ids are assigned deterministically** (file id + turn/row counter), so
  re-ingesting unchanged sources yields identical ids. This is what makes the
  byte-identical-rebuild test survivable across the refactor.
- **Errors vs warnings.** Missing referenced anchor = error (the evidence chain is
  the product). Unknown section, extra metadata field, unrecognized row = warning +
  graceful rendering. `check_links.py` remains the backstop and runs per demo.

### What is contract (never flexes)

1. Every ID is unique within a demo and is itself a link.
2. Every evidence link targets a specific `#anchor`, never a page top.
3. The trail resolves: journey cell → insight → dated verbatim.
4. Persona `agent` ids are lowercase and match the app exactly.
5. A scratch rebuild reproduces `dist/<demo>/` byte-for-byte (enforced by test).

## 3. The per-demo manifest

One file, `demos/<demo>/demo.json`, consumed by the site build **and** by the app
bundle generator. It absorbs every constant we've been extracting all day —
`naming.py`'s tables and `chrome.py`'s strings were deliberately built as the seed
of this. Sketch, with today's values:

```jsonc
{
  "id": "borderblend",
  "brand": "BorderBlend",
  "site_title": "BorderBlend Evidence Map",
  "back_label": "← Evidence Map",
  "id_prefix": "BB",                          // BB-INT001, INS-C01 namespaces
  "share_path": "shares/ucloops/borderblend", // publisher destination
  "app_url": "https://ucloops-demo-v1.vercel.app/",
  "banner": {
    "lines": ["This is a generated example…", "…", "…"],
    "cta_url": "https://urbinaconsulting.com/shares/ucloops/cohort-journeys-sept-2026/",
    "cta_label": "Learn more"
  },
  "personas": [
    { "person": "omar", "archetype": "business-lunch", "name": "Omar",
      "agent": "omar", "headshot": "omar.jpg", "initials": "O",
      "role": "Business Lunch — financial-district professional…" }
    // grace, mateo, diego, tyler …
  ],
  "journeys": [
    { "slug": "business-lunch", "personas": ["omar", "grace"], "versions": [1, 3] }
  ],
  "sections": { /* persona + journey section registries, defaulted */ },
  "legacy_urls": { "persona-omar-v3.html": "pers-omar-business-lunch-v3.html" }
}
```

Framing/content rules (winning-challenger tone etc.) stay prose per demo — a
`demos/<demo>/VOICE.md` the generation prompts read, not the build.

## 4. Repo layout and data ownership

**The one decision that needs Noz, not me.** The raw `.md` currently exists twice:
all 27 sources here, 15 of them byte-identical inside `ui1`'s `src/personas.js` — a
2,030-line file whose header claims it is auto-assembled but which **has no
generator** (verified by the previous session: `build-templates.mjs`'s EXPORTS map
doesn't mention it). That is the promo-banner failure mode again, on the file most
in the way of templating.

**Recommendation: this repo owns the raw data.** It has the superset, the anchor
pipeline, and now the test harness that catches drift. Target layout:

```
demos/
  borderblend/
    demo.json            manifest
    sources/             the 27 .md (moved from build/source-data/)
    deliverables/        insights-*.json, persona/journey JSON, v3 JSON
    VOICE.md             framing rules for content generation
  pharma/                the second demo, same shape
toolchain/               build.py split into ingest.py + render/, chrome.py,
                         styles.py, naming.py→manifest, postbuild/, check_links.py
dist/
  borderblend/           today's site/ (publisher points here)
  pharma/
tests/                   parameterized by manifest; fixtures unchanged
```

The app repo then consumes a **generated artifact**, not copies: a script here
emits `agents-<demo>.json` (system prompts + full transcripts + meta) which `ui1`
imports server-side only. The existing prompt/bundle boundary is preserved —
transcripts must never reach the browser, so the artifact is imported solely by the
serverless functions, exactly as `personas.js` is today. A checksum test on both
sides replaces trust. (Alternative: a third data-only repo. More ceremony, only
worth it if demos get authored by people without access to this repo.)

## 5. The app side (uc-ucloops-ui1)

Changes the previous session's audit already located, ordered:

1. **Generate `personas.js`'s successor** from the owned .md (closes the
   no-generator gap; kills the 15 duplicated transcripts).
2. **Single URL source.** `AgentChat.jsx:15` re-declares `EVIDENCE_MAP_URL` instead
   of importing `agentMeta.js`'s export that `api/chat.js` already uses. One copy,
   from the manifest.
3. **Fail visibly on unknown agent.** Today `?agent=typo` silently lands on Omar
   (`AgentChat.jsx:30` returns null → line 363 falls back to `PERSONA_META[0]`).
   With multiple demos this becomes actively misleading. Unknown agent → explicit
   "persona not found in this demo" state.
4. **Demo namespace.** `?demo=<id>&agent=<person>`, defaulting to borderblend so
   every existing link keeps working. Per-demo meta module on the server; the
   client receives only the active demo's public meta.
5. Keep the three-way skill agreement (`DISABLED_COMMANDS` ↔ `DEMO_MODE_ADDENDUM` ↔
   `workflow.js`) shared across demos unless a demo explicitly overrides.

## 6. The journey-map problem (the honest hard part)

The four `journey-map-*.html` files have **no generator** — they were hand-authored
on `journey-map-template.html` via the prompt chain, and today seven postbuild
patches keep them alive. A pharma demo cannot inherit hand-authored BorderBlend
maps, so the abstraction forces the question. Options:

- **(a) Build the v3 journey-map renderer.** `journey-map-template.html`,
  `v2/apply_revisions.py` and `v3/patch_v3_maps.py` contain all the structure; the
  enrich JSON (`v3/enrich-*.json`) is most of the data. Fold the seven patches'
  *outcomes* (shared chrome, unified toggle, flow mode, pan bar, live CSS) into the
  renderer output. Biggest single cost in the plan — but it retires the whole
  frozen-stylesheet class of bug and its tests.
- **(b) Keep maps hand-authored per demo**, patched by the existing chain. Zero
  build cost now, but every demo pays the authoring cost and inherits the drift
  risk the tests currently police.

Recommendation: (a), scheduled as its own phase, *after* a second demo proves the
rest of the pipeline — the renderer's requirements will be much clearer with two
demos' maps in hand than one.

## 7. Phases

Each phase ends green: 197+ tests passing, byte-identical rebuild, links 0 broken.
The rebuild test is what makes refactoring safe — any behavioural slip shows up as
a byte diff.

- [x] **Phase 0 — Reproducibility + tests.** Done 2026-07-30. Chrome in the
      generator, composed stylesheet, shared jump/keep-place helpers, Playwright
      suite, CI.
- [ ] **Phase 1 — Close the `personas.js` generator gap** (ui1). Script in this
      repo emits the agents artifact from the owned .md; ui1 imports it
      server-side; checksum test both ends. Small, urgent, same fix pattern as the
      banner. *Needs the ownership decision (§4) first.*
- [ ] **Phase 2 — Manifest extraction, no behaviour change.** `demo.json` for
      borderblend; `naming.py`/`chrome.py`/`build.py` constants read from it;
      output stays byte-identical (test-enforced). Tests read `PERSONAS`/paths from
      the manifest instead of hardcoding.
- [ ] **Phase 3 — Repo reshape + ingest split.** `demos/`, `toolchain/`, `dist/`;
      `build.py` splits into ingest (md → bundle, tolerant, front-matter aware,
      section registries) and render (bundle → HTML). Publisher pointed at
      `dist/borderblend/`.
- [ ] **Phase 4 — Second demo (pharma).** Sources authored to the front-matter
      convention; new `demo.json`; published at `shares/ucloops/<demo>/`; app gets
      `?demo=`. This phase is the proof — expect it to flush out every hidden
      BorderBlend assumption the tests didn't.
- [ ] **Phase 5 — Journey-map renderer** (§6a), retiring the postbuild patch chain
      for maps.
- [ ] **Phase 6 — Switcher UX.** Demo picker in the app; a demos index page on the
      site; cross-links carry the demo context.

## 8. Traps already known (so nobody rediscovers them)

- The `BB-` prefix is load-bearing in ids, `anchor-index.json`,
  `valid-anchor-ids.txt` and 6,400+ links — per-demo prefixes mean regenerating
  all of it per demo, which the ingest step does anyway. Never mix prefixes in one
  bundle.
- The viewer contract (sticky bar reads, `toggleProv`, the two `+16`s, "framed
  documents don't scroll") is documented in `For AIs.md` §4b and enforced by
  `tests/viewer-embed.spec.ts`. Every new page type must pass that spec.
- `.grid-container` vs `.container`: which ancestor scrolls a journey grid differs
  by mode. Resolve scrollers by measurement, never by class name.
- The publisher ships whole folders with no excludes — anything in `dist/<demo>/`
  goes live. Toolchain and docs stay outside it.
- Chrome/headshot/logo assets: `.svg` is mis-served (data-URI it), `.jpg` is fine.
