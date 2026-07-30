# -*- coding: utf-8 -*-
"""
Output filenames for persona pages, in one place.

Persona pages are `pers-<person>-<archetype>-v<n>.html`:

    pers-mateo-late-night-foodie-v3.html
    pers-omar-business-lunch-v3.html

Both halves earn their keep. The archetype is what the journey maps and the index
group by; the person is who the page is actually about, and it is the id the
companion app takes in `?agent=`. Keeping only one of them is what produced a live
broken link to `persona-mateo-v3.html` — a file that never existed, because the page
was named for the archetype (`late-night-foodie`) while everything human-facing
called him Mateo.

The v1 pages are archetypes rather than people — `persona-business-lunch.html`
covered Omar *and* Grace — so they carry no person: `pers-<archetype>-v1.html`.

LEGACY exists because these files were live. `build.py` generates a redirect stub at
each old name, so anything already linking to one still lands in the right place.
When they've been dead long enough, delete the map and the stubs go with it.
"""

# Personas whose pages are generated from build/v3/persona-v3-*.json. The archetype
# also lives in each JSON (`archetype`); this is the map the *index* and the patches
# need, without loading five files.
V3_ARCHETYPE = {
    "omar": "business-lunch",
    "grace": "business-lunch",
    "mateo": "late-night-foodie",
    "diego": "franchisee",
    "tyler": "everyday-20s",
}

# v1 archetype pages, in the order the index lists them.
V1_ARCHETYPES = ("business-lunch", "late-night-foodie", "everyday-20s", "franchisee")


def persona_page(person, archetype, version=3):
    return f"pers-{person}-{archetype}-v{version}.html"


def persona_v1_page(archetype):
    return f"pers-{archetype}-v1.html"


def v3_page(person):
    return persona_page(person, V3_ARCHETYPE[person])


# Old name -> new name. Everything that used to be a persona URL.
LEGACY = {
    "persona-omar-v3.html": v3_page("omar"),
    "persona-grace-v3.html": v3_page("grace"),
    "persona-late-night-foodie-v3.html": v3_page("mateo"),
    "persona-franchisee-v3.html": v3_page("diego"),
    "persona-everyday-20s-v3.html": v3_page("tyler"),
    "persona-business-lunch.html": persona_v1_page("business-lunch"),
    "persona-late-night-foodie.html": persona_v1_page("late-night-foodie"),
    "persona-everyday-20s.html": persona_v1_page("everyday-20s"),
    "persona-franchisee.html": persona_v1_page("franchisee"),
}
