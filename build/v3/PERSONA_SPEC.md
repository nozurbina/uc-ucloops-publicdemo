# v3 Persona authoring spec (shared)

You are producing ONE persona as STRICT JSON, in the real ucLoops `/persona-export` structure, for the
BorderBlend case (Canadian Mexican fusion+traditional food-truck brand). A renderer will place it on
`persona-template.html` with the brand stylesheet, so follow the section list exactly.

## Read (absolute, under "d:/UC Dropbox/Work/UC/Orgs/ucLoops Projects/UC ucLoops for UC/Pharma/uc-pharma-analysis/")
- CANON: OUTPUT/interim/borderblend/CANON.md
- Framing rule: CLAUDE.md "Framing & tone" (winning/growing brand; frictions = obstacles to going further, never deficit).
- Insight index (cite these ids): OUTPUT/interim/borderblend/insights-menu.md + valid-insight-ids.txt
- Source anchors (for demographic facts + verbatim quotes): OUTPUT/interim/borderblend/citation-menu.md
- Your backing interview(s): named in your task.
- Seed (previous, wrongly-structured persona for this archetype — reuse the substance, not the shape): named in your task.

## Output — STRICT JSON to the path named in your task. Schema (EXACT keys):
{
 "slug": "<archetype-slug>",
 "code": "<4-letter persona code, e.g. MATE>",
 "name": "<display name, e.g. Mateo>",
 "role": "<role line, e.g. 'Late-Night Foodie — nightlife service worker · Toronto · 26'>",
 "initials": "<1-2 letters>",
 "sections": [
   {"type":"DEMO","items":[{"text":"<age/location/role etc>","insights":["INS-.."],"evidence":["BB-INT0NN-tK"]}, ... 3-4]},
   {"type":"MIND","items":[{"text":"<mindset point>","insights":[".."],"evidence":[".."]}, ... 3-4]},
   {"type":"EMOT","emotions":[{"emoji":"🤔","label":"<Emotion>","tail":"<short context>","insights":[".."]}, ... 3-5]},
   {"type":"VOIC","voice":"<one italic paragraph describing how they speak>","voice_insights":[".."],
      "quotes":[{"text":"<verbatim-style quote in their voice>","evidence":["BB-INT0NN-tK"]}, ... 2-4]},
   {"type":"GOAL","items":[ ... 3-5]},
   {"type":"TASK","items":[ ... 3-5]},
   {"type":"PAIN","items":[ ... 3-5]},
   {"type":"FEAR","items":[ ... 2-4]},
   {"type":"ETRI","items":[ ... 2-3]},   // emotional decision triggers
   {"type":"XTRI","items":[ ... 2-3]},   // external decision triggers
   {"type":"CRIT","items":[ ... 3-4]},   // key decision criteria
   {"type":"CHAN","items":[ ... 3-5]},   // preferred channels/tools
   {"type":"RELT","rels":[{"label":"<e.g. With the truck staff>","points":["<point>", ...],"insights":[".."]}, ... 2-3]}
 ]
}

## Rules
- EVERY `items[]`/`emotions[]`/`quotes[]`/`rels[]` entry SHOULD carry `insights`: a list of >=1 id from
  valid-insight-ids.txt (choose the insight that actually supports it). Where a direct source verbatim exists
  (demographics facts, quotes, vivid pains), ALSO add `evidence`: source anchor ids (BB-INT0NN-tK, SOC-M0NN,
  FT-0NN, APPLOG-rN, MR-C0N, PAIN-X). Quotes SHOULD have an `evidence` turn id.
- All ids must be valid (insights in valid-insight-ids.txt; anchors in citation-menu.md). Invalid ids are dropped.
- VOICE + QUOTES must sound like the real person from the interview(s) — plain, human, in-character. No UX/analyst
  jargon in persona-voiced text (no "friction", "touchpoint", "conversion", "failure mode", "value prop").
- ENTITY HIGHLIGHTING: wrap specific named menu items / branded artefacts in <span class="entity">…</span>
  in the text: smoked brisket taco, salsa verde, Korean-style chicken taco, plant-based option, Fuego Nights,
  BorderBlend app, newsletter, loyalty programme. Also wrap the persona's MEAL occasion word where it appears —
  <span class="entity">lunch</span> for business personas, <span class="entity">late-night meal</span> /
  <span class="entity">late-night taco run</span> for the foodie, <span class="entity">dinner</span> for family-ish.
- Canadian spelling. Keep each item one crisp sentence. Winning-brand framing throughout.
- Output ONLY valid JSON (double quotes, no trailing commas/comments). Then reply one line: section count + total items + any ids you were unsure about.
