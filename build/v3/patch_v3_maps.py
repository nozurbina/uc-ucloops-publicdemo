# -*- coding: utf-8 -*-
"""Build v3 journey maps from the v2 maps (v2 left untouched). Applies:
  1. focus/X buttons on EVERY persona card + show-all + JS (fixes v2's one-card bug)
  2. sidebar persona cards link to their v3 persona page
  3. retarget persona-row item-ref + prov-link deep-links to v3 persona pages & section anchors
  4. trail-legend retargeted to v3 personas (+ both faces for business)
  5. "Meal" ontological concept in the short description; the specific meal highlighted throughout the grid
  6. title/h1 (v2)->(v3)
"""
import re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parents[1] / "site"

ROW_SECTION = {"GOAL":"goals","NARR":"background-mindset","QUES":"decision-criteria","PROB":"pain-points",
               "TASK":"key-tasks","SENT":"main-emotions","QUOT":"voice-tone","ALTP":"fears-concerns",
               "CHAN":"tools-channels"}

FOCUS_JS = """<script>
let activePersona=null,removedPersonas=new Set();
function focusPersona(p){removedPersonas.clear();document.querySelectorAll('.persona-card').forEach(c=>c.classList.remove('removed'));
 var card=document.querySelector('[data-persona="'+p+'"]');var was=card.classList.contains('active');
 document.querySelectorAll('.persona-card').forEach(c=>c.classList.remove('active'));
 if(was){activePersona=null;updateContentVisibility();updateRemoveButtons();return;}
 card.classList.add('active');activePersona=p;updateContentVisibility();updateRemoveButtons();}
function toggleRemovePersona(p){var card=document.querySelector('[data-persona="'+p+'"]');
 if(removedPersonas.has(p)){removedPersonas.delete(p);card.classList.remove('removed');}
 else{removedPersonas.add(p);card.classList.add('removed');if(activePersona===p){activePersona=null;card.classList.remove('active');}}
 updateContentVisibility();updateRemoveButtons();}
function updateContentVisibility(){document.querySelectorAll('.persona-content').forEach(c=>{var p=c.dataset.persona;
 if(p==='all'){c.classList.remove('hidden');}else if(removedPersonas.has(p)){c.classList.add('hidden');}
 else if(activePersona){c.classList.toggle('hidden',p!==activePersona);}else{c.classList.remove('hidden');}});}
function updateRemoveButtons(){document.querySelectorAll('.persona-card').forEach(card=>{var b=card.querySelector('.remove-btn');
 if(b)b.innerHTML=removedPersonas.has(card.dataset.persona)?'<span>Restore</span> ✔️':'<span>Remove</span> ❌';});}
function showAllPersonas(){activePersona=null;removedPersonas.clear();
 document.querySelectorAll('.persona-card').forEach(c=>c.classList.remove('active','removed'));
 document.querySelectorAll('.persona-content').forEach(c=>c.classList.remove('hidden'));updateRemoveButtons();}
</script>"""

CSS_ADD = """<style>
.persona-card .persona-name a,.persona-card .persona-role a{color:inherit;text-decoration:none}
.persona-card .persona-name a:hover,.persona-card .persona-role a:hover{text-decoration:underline}
.sidebar .show-all-btn{margin-top:0;margin-bottom:1.25rem}
/* per-item provenance trail on persona rows (hidden until "Show Item IDs and Provenance") */
.journey-grid .evidence{display:none}
.journey-grid.show-refs .evidence{display:block}
.journey-grid .evidence{margin:.35rem 0 .1rem;font-size:.72rem;color:#667085;line-height:1.9}
.journey-grid .evidence .lbl{text-transform:uppercase;letter-spacing:.08em;font-size:.6rem;color:#94a3b8;margin-right:.2rem}
.evref{font-family:'SF Mono','Fira Code',ui-monospace,monospace;font-weight:700;font-size:.62rem;
  background:#fef3c7;color:#78350f;border:1px solid #fde68a;border-radius:4px;padding:.03rem .3rem;
  text-decoration:none;display:inline-block;margin:.08rem .2rem .08rem 0;position:relative}
.evref:hover{outline:1px solid #f59e0b;text-decoration:none}
.evref.insid{background:#e0f2f1;color:#0b6a5b;border-color:#b2dfdb}
.evref .tip{display:none;position:absolute;left:0;top:135%;z-index:60;width:20rem;max-width:60vw;
  background:#fff;border:1px solid #f59e0b;border-radius:9px;padding:.5rem .65rem;font-family:-apple-system,sans-serif;
  font-weight:400;font-size:.75rem;color:#333;box-shadow:0 8px 26px rgba(0,0,0,.2);white-space:normal;line-height:1.4}
.evref:hover .tip{display:block}
.evref .tip .src{display:block;color:#b45309;font-weight:700;font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem}
a.item-ref{text-decoration:none}a.ref-item-id{text-decoration:none}
</style>"""

MAPS = {
 "late-night": {
   "src":"journey-map-late-night-v2.html","dst":"journey-map-late-night-v3.html",
   "cards":{"persona1":("persona-late-night-foodie-v3.html","Mateo")},
   "codes":{"MATE":"persona-late-night-foodie-v3.html"},
   "meal":[r"late-night taco run",r"late-night meals?",r"late-night tacos?",r"midnight tacos?"],
   "meal_sentence":' The <span class="entity">Meal</span> occasion in focus is the <span class="entity">late-night meal</span> — the after-shift, after-venue taco run.',
   "trail_personas":'<span class="step">Persona: <a href="persona-late-night-foodie-v3.html">Mateo (Late-Night Foodie)</a></span>',
 },
 "business-lunch": {
   "src":"journey-map-business-lunch-v2.html","dst":"journey-map-business-lunch-v3.html",
   "cards":{"persona1":("persona-omar-v3.html","Omar"),"persona2":("persona-grace-v3.html","Grace")},
   "codes":{"OMAR":"persona-omar-v3.html","GRAC":"persona-grace-v3.html"},
   "meal":[r"lunches",r"lunch"],
   "meal_sentence":' The <span class="entity">Meal</span> occasion in focus is <span class="entity">lunch</span> — the weekday midday break and the team / catering window.',
   "trail_personas":'<span class="step">Personas: <a href="persona-omar-v3.html">Omar</a>, <a href="persona-grace-v3.html">Grace</a></span>',
 },
}

def find_block_end(html, start):
    depth = 0
    for m in re.finditer(r'<div\b|</div>', html[start:]):
        if m.group(0) == '<div': depth += 1
        else:
            depth -= 1
            if depth == 0: return start + m.start()
    return -1

def wrap_meal(region, pats):
    store = []
    def prot(m): store.append(m.group(0)); return f"\x00{len(store)-1}\x00"
    s = re.sub(r'<span class="entity">.*?</span>', prot, region, flags=re.S)
    s = re.sub(r'<[^>]+>', prot, s)
    for p in pats:
        s = re.sub(r'(?<![\w-])(' + p + r')(?![\w-])',
                   lambda m: f'<span class="entity">{m.group(1)}</span>', s, flags=re.I)
    s = re.sub('\x00(\\d+)\x00', lambda m: store[int(m.group(1))], s)
    return s

def process(cfg):
    html = (SITE / cfg["src"]).read_text(encoding="utf-8")
    codes = cfg["codes"]

    # 1+3. block walker: retarget persona item-refs + prov-links
    starts = [m.start() for m in re.finditer(r'<div class="persona-content highlight-persona\d" data-persona="persona\d">', html)]
    edits = []
    for st in starts:
        end = find_block_end(html, st)
        if end < 0: continue
        block = html[st:end]
        im = re.search(r'id="([A-Z]{4})-([A-Z]{4})-\d{4}"', block)
        if not im: continue
        typ, scope = im.group(1), im.group(2)
        page = codes.get(scope)
        if not page: continue
        section = ROW_SECTION.get(typ, "goals")
        tgt = f"{page}#{section}"
        # item-ref ID links up to the persona-page section (the journey→persona connection)
        nb = re.sub(r'(<a class="item-ref" id="[A-Z]{4}-' + scope + r'-\d{4}" href=")[^"]*(")',
                    lambda m: m.group(1) + tgt + m.group(2), block)
        # remove the redundant "↳ from … persona" prov-link (the ID link already carries it)
        nb = re.sub(r'<div class="prov-link">.*?</div>', '', nb, flags=re.S)
        edits.append((st, end, nb))
    for st, end, nb in sorted(edits, reverse=True):
        html = html[:st] + nb + html[end:]

    # renumber journey item-refs with a stage segment: {TYPE}-{SCOPE}-ST{NN}-{seq}
    # (disambiguates journey goals from persona-page goals; seq resets per stage)
    pat = re.compile(r'<div class="row-header|<div class="grid-cell'
                     r'|<(?:a|span) class="item-ref" id="([A-Z]{4})-([A-Z]{4})-(\d{4})"')
    stage = 0; counters = {}; idmap = {}
    for m in pat.finditer(html):
        tok = m.group(0)
        if tok.startswith('<div class="row-header'): stage = 0
        elif tok.startswith('<div class="grid-cell'): stage += 1
        else:
            T, S, N = m.group(1), m.group(2), m.group(3)
            old = f"{T}-{S}-{N}"
            if old in idmap: continue
            key = (T, S, stage); counters[key] = counters.get(key, 0) + 1
            idmap[old] = f"{T}-{S}-ST{stage:02d}-{counters[key]:04d}"
    if idmap:
        rx = re.compile('|'.join(re.escape(k) for k in sorted(idmap, key=len, reverse=True)))
        html = rx.sub(lambda m: idmap[m.group(0)], html)

    # 2. rebuild persona cards (link + focus/X); tolerate an existing persona-actions block
    def rebuild_card(m):
        dp = m.group("dp"); avatar = m.group("avatar"); name = m.group("name"); role = m.group("role")
        page = cfg["cards"].get(dp, ("#",""))[0]
        # strip any anchor already wrapping the captured name (v2 leftovers); link name + role to the persona page
        name_txt = re.sub(r'</?a[^>]*>', '', name).strip()
        role_txt = re.sub(r'</?a[^>]*>', '', role).strip()
        return (f'<div class="persona-card" data-persona="{dp}">\n{avatar}\n'
                f'<div class="persona-name"><a href="{page}">{name_txt}</a></div>\n'
                f'<div class="persona-role"><a href="{page}">{role_txt}</a></div>\n'
                f'<div class="persona-actions">'
                f'<button class="persona-btn focus-btn" onclick="focusPersona(\'{dp}\')" title="Focus on {name_txt}"><span>Focus</span> \U0001f52c</button>'
                f'<button class="persona-btn remove-btn" onclick="toggleRemovePersona(\'{dp}\')" title="Hide {name_txt}"><span>Remove</span> ❌</button>'
                f'</div>\n</div>')
    card_re = re.compile(
        r'<div class="persona-card" data-persona="(?P<dp>persona\d)">\s*'
        r'(?P<avatar><div class="persona-avatar.*?</div>)\s*'
        r'<div class="persona-name">(?P<name>.*?)</div>\s*'
        r'<div class="persona-role">(?P<role>.*?)</div>'
        r'(?:\s*<a class="persona-profile-link".*?</a>)?'
        r'(?:\s*<div class="persona-actions">.*?</div>)?\s*</div>', re.S)
    html = card_re.sub(rebuild_card, html)
    # strip any name link nesting artefacts (if name already had <a>)
    html = re.sub(r'<a href="[^"]*"><a href="([^"]*)">([^<]*)</a></a>', r'<a href="\1">\2</a>', html)

    # single Show-all button at the TOP of the sidebar, outside the persona cards
    html = re.sub(r'\s*<button class="show-all-btn"[^>]*>.*?</button>', '', html, flags=re.S)
    html = html.replace('<h2>Personas</h2>',
        '<h2>Personas</h2>\n<button class="show-all-btn" onclick="showAllPersonas()">Show all personas</button>', 1)

    # JS + CSS
    if 'function focusPersona' not in html and 'focusPersona=' not in html:
        html = html.replace('</body>', FOCUS_JS + '\n</body>')
    else:
        html = re.sub(r'<script>\s*let activePersona.*?</script>', FOCUS_JS, html, flags=re.S)  # normalise
    if 'persona-profile-link{' not in html:
        html = html.replace('</head>', CSS_ADD + '</head>')

    # 4. trail-legend personas step -> v3
    html = re.sub(r'<span class="step">Personas?:.*?</span>', cfg["trail_personas"], html, count=1, flags=re.S)
    # any remaining links to the old v1 persona pages in the trail/body -> v3 primary
    prim = list(cfg["codes"].values())[0]
    html = re.sub(r'href="persona-(?:late-night-foodie|business-lunch)\.html(#[^"]*)?"',
                  lambda m: f'href="{prim}"', html)

    # 5. Meal concept in short description
    html = re.sub(r'(<p class="journey-description">.*?)(</p>)',
                  lambda m: m.group(1) + cfg["meal_sentence"] + m.group(2), html, count=1, flags=re.S)
    #    highlight the specific meal throughout the grid region (grid-container -> first trailing <script>)
    gstart = html.find('<div class="grid-container">')
    if gstart != -1:
        sc = html.find('<script', gstart)
        gend = sc if sc != -1 else html.find('</body>', gstart)
        region = html[gstart:gend]
        html = html[:gstart] + wrap_meal(region, cfg["meal"]) + html[gend:]

    # 6. titles + toggle rename (the header toggle now governs IDs *and* provenance rows)
    html = html.replace("(v2)", "(v3)")
    html = html.replace('>Show item IDs</button>', '>Show Item IDs and Provenance</button>')
    html = html.replace("'Hide item IDs'", "'Hide Item IDs and Provenance'").replace("'Show item IDs'", "'Show Item IDs and Provenance'")

    (SITE / cfg["dst"]).write_text(html, encoding="utf-8")
    ncards = len(re.findall(r'class="persona-actions"', html))
    print(f'{cfg["dst"]}: cards w/ actions {ncards}, blocks retargeted {len(edits)}')

if __name__ == "__main__":
    for cfg in MAPS.values():
        process(cfg)
