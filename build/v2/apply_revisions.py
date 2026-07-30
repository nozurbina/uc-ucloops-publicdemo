# -*- coding: utf-8 -*-
"""Apply the v2.1 revision pass to both journey maps:
   1. rewrite items (persona voice / entity spans / genericised brand rows) from revisions-*.json
   2. sync opportunity ref-verbatim quotes for rewritten items
   3. turn every item-ref span into a deep link to its source (persona block / provenance / self)
   4. append prov-link lines to persona-content blocks (pharma pattern)
   5. insert trail-legend bar, CSS additions, focus/X persona buttons + JS, show-all button
Idempotent: safe to re-run.
"""
import re, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parents[1] / "site"

CSS_ADD = """
/* ── v2.1 additions: link trail, provenance links, linked item-refs ── */
.trail-legend{background:#12345910;border:1px solid #cfd8dc;border-radius:10px;padding:14px 18px;margin:14px 0 4px;font-size:13.5px;line-height:1.6}
.trail-legend b{color:#124559}.trail-legend .step{display:inline-block;background:#fff;border:1px solid #d5dde0;border-radius:6px;padding:2px 9px;margin:2px 2px}
.trail-legend a{font-weight:600}
.prov-link{margin-top:8px;font-size:11.5px;opacity:.8}.prov-link a{font-weight:600}
.opp-refs .ref-item a{font-weight:600}
a.item-ref{cursor:pointer}
a.item-ref:hover{outline:1px solid #b3401f;text-decoration:none}
"""

MAPS = {
    "late-night": {
        "file": "journey-map-late-night-v2.html",
        "personas": {"MATE": {"page": "persona-late-night-foodie.html", "name": "Mateo",
                              "blockprefix": "PERS-late-night-foodie-", "dp": "persona1"}},
        "trail": """<div class="trail-legend"><b>Link trail:</b>
<span class="step">Journey <em>(this page)</em></span> →
<span class="step"><a href="persona-late-night-foodie.html">Mateo’s persona (Late-Night Foodie)</a></span> →
<span class="step"><a href="insights.html">36 research insights</a></span> →
<span class="step">Source verbatims <em>(interviews, social, app logs, market report — linked from each insight)</em></span>.
<br>Every persona row links up into Mateo’s persona (<span class="prov-link" style="opacity:1">↳ from Mateo’s persona</span>); every item ID is a deep link to its source; each opportunity’s <em>Show references</em> opens the persona lines, insights and source verbatims it draws on; each insight links down to the dated verbatim.</div>""",
    },
    "business-lunch": {
        "file": "journey-map-business-lunch-v2.html",
        "personas": {"OMAR": {"page": "persona-business-lunch.html", "name": "Omar",
                              "blockprefix": "PERS-business-lunch-", "dp": "persona1"},
                     "GRAC": {"page": "persona-business-lunch.html", "name": "Grace",
                              "blockprefix": "PERS-business-lunch-", "dp": "persona2"}},
        "trail": """<div class="trail-legend"><b>Link trail:</b>
<span class="step">Journey <em>(this page)</em></span> →
<span class="step"><a href="persona-business-lunch.html">Omar &amp; Grace’s persona (Business Lunch)</a></span> →
<span class="step"><a href="insights.html">36 research insights</a></span> →
<span class="step">Source verbatims <em>(interviews, tickets, app logs, market report — linked from each insight)</em></span>.
<br>Every persona row links up into the Business-Lunch persona (<span class="prov-link" style="opacity:1">↳ from Omar’s / Grace’s persona</span>); every item ID is a deep link to its source; each opportunity’s <em>Show references</em> opens the persona lines, insights and source verbatims it draws on; each insight links down to the dated verbatim.</div>""",
    },
}

# row TYPE -> persona-page block slug
ROW_BLOCK = {"GOAL": "goals-motivations", "NARR": "behaviours-habits", "QUES": "frictions-obstacle",
             "PROB": "frictions-obstacle", "TASK": "behaviours-habits", "SENT": "emotional-arc",
             "QUOT": "emotional-arc", "ALTP": "frictions-obstacle", "CHAN": "discovery-channels"}
# row TYPE -> human row label (for prov-link mapping only where needed)

FOCUS_JS = """
<script>
/* v2.1: persona focus / remove controls (ported from Multi-Persona CJM example) */
let activePersona = null;
let removedPersonas = new Set();
function focusPersona(persona) {
    removedPersonas.clear();
    document.querySelectorAll('.persona-card').forEach(c => c.classList.remove('removed'));
    const card = document.querySelector(`[data-persona="${persona}"]`);
    const wasActive = card.classList.contains('active');
    document.querySelectorAll('.persona-card').forEach(c => c.classList.remove('active'));
    if (wasActive) { activePersona = null; updateContentVisibility(); updateRemoveButtons(); return; }
    card.classList.add('active');
    activePersona = persona;
    updateContentVisibility();
    updateRemoveButtons();
}
function toggleRemovePersona(persona) {
    const card = document.querySelector(`[data-persona="${persona}"]`);
    if (removedPersonas.has(persona)) {
        removedPersonas.delete(persona); card.classList.remove('removed');
    } else {
        removedPersonas.add(persona); card.classList.add('removed');
        if (activePersona === persona) { activePersona = null; card.classList.remove('active'); }
    }
    updateContentVisibility(); updateRemoveButtons();
}
function updateContentVisibility() {
    document.querySelectorAll('.persona-content').forEach(content => {
        const p = content.dataset.persona;
        if (p === 'all') { content.classList.remove('hidden'); }
        else if (removedPersonas.has(p)) { content.classList.add('hidden'); }
        else if (activePersona) { content.classList.toggle('hidden', p !== activePersona); }
        else { content.classList.remove('hidden'); }
    });
}
function updateRemoveButtons() {
    document.querySelectorAll('.persona-card').forEach(card => {
        const btn = card.querySelector('.remove-btn');
        if (!btn) return;
        btn.innerHTML = removedPersonas.has(card.dataset.persona) ? '<span>Restore</span> ✔️' : '<span>Remove</span> ❌';
    });
}
function showAllPersonas() {
    activePersona = null; removedPersonas.clear();
    document.querySelectorAll('.persona-card').forEach(c => c.classList.remove('active','removed'));
    document.querySelectorAll('.persona-content').forEach(c => c.classList.remove('hidden'));
    updateRemoveButtons();
}
</script>"""

def find_block_end(html, start):
    """start = index of '<div' opening a persona-content block; return index just before its closing </div>."""
    depth = 0
    i = start
    for m in re.finditer(r'<div\b|</div>', html[start:]):
        if m.group(0) == '<div':
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return start + m.start()
    return -1

def process(slug, cfg):
    path = SITE / cfg["file"]
    html = path.read_text(encoding="utf-8")
    rev = json.loads((HERE / f"revisions-{slug}.json").read_text(encoding="utf-8"))
    warn = []

    # ── 1. journey description ──
    if rev.get("journey_description"):
        html = re.sub(r'(<p class="journey-description">).*?(</p>)',
                      lambda m: m.group(1) + rev["journey_description"] + m.group(2), html, count=1, flags=re.S)

    # ── 2. item rewrites ──
    applied = 0
    for iid, newtext in rev.get("rewrites", {}).items():
        pat = re.compile(r'(<(?:span|a)\b[^>]*class="item-ref"[^>]*id="' + re.escape(iid) +
                         r'"[^>]*>' + re.escape(iid) + r'</(?:span|a)>)(.*?)(</li>|</p>)', re.S)
        def repl(m):
            return m.group(1) + newtext + m.group(3)
        html, n = pat.subn(repl, html, count=1)
        if n: applied += 1
        else: warn.append(f"rewrite target not found: {iid}")

    # ── 3. sync ref-verbatims for rewritten ids ──
    synced = 0
    for iid, newtext in rev.get("rewrites", {}).items():
        plain = re.sub(r'<[^>]+>', '', newtext).strip()
        pat = re.compile(r'(<p class="ref-item" data-ref="' + re.escape(iid) +
                         r'".*?<span class="ref-verbatim">)“?.*?”?(</span>)', re.S)
        html, n = pat.subn(lambda m: m.group(1) + "“" + plain + "”" + m.group(2), html)
        synced += n

    # ── 4. item-ref spans -> deep links ──
    prov = rev.get("provenance", {})
    def link_item(m):
        pre, iid = m.group(1), m.group(2)
        t, scope = iid.split("-")[0], iid.split("-")[1]
        if scope in cfg["personas"]:
            p = cfg["personas"][scope]
            block = ROW_BLOCK.get(t, "goals-motivations")
            href = f'{p["page"]}#{p["blockprefix"]}{block}'
            title = f"Source: {p['name']}’s persona"
        elif t == "OPPO":
            href = f"#{iid}"; title = "References below"
        else:
            href = prov.get(iid)
            title = "View source"
            if not href:
                warn.append(f"no provenance for {iid}"); href = "insights.html#INS-C01"
        return f'<a class="item-ref" id="{iid}" href="{href}" title="{title}">{iid}</a>'
    html = re.sub(r'<span( class="item-ref" id="([A-Z]{4}-[A-Z]{4}-\d{4})")>\2</span>', link_item, html)

    # ── 5. prov-link per persona-content block (persona rows only) ──
    if "prov-link" not in html.split("</style>",1)[1][:200]:  # cheap idempotency check refined below
        pass
    added_prov = 0
    out = []
    idx = 0
    for m in re.finditer(r'<div class="persona-content highlight-(persona\d)" data-persona="\1">', html):
        start = m.start()
        end = find_block_end(html, start)
        if end < 0: continue
        block = html[start:end]
        if 'class="prov-link"' in block: continue
        # which persona + row type from first item-ref inside
        im = re.search(r'id="([A-Z]{4})-([A-Z]{4})-\d{4}"', block)
        if not im: continue
        t, scope = im.group(1), im.group(2)
        p = cfg["personas"].get(scope)
        if not p: continue
        blockslug = ROW_BLOCK.get(t, "goals-motivations")
        prov_div = (f'<div class="prov-link">↳ from <a href="{p["page"]}#{p["blockprefix"]}{blockslug}">'
                    f'{p["name"]}’s persona</a></div>')
        out.append((end, prov_div)); added_prov += 1
    for end, div in sorted(out, reverse=True):
        html = html[:end] + div + html[end:]

    # ── 6. trail-legend after journey-description ──
    if 'trail-legend' not in html:
        html = re.sub(r'(</p>\s*</div>\s*<div class="grid-container">)',
                      lambda m: cfg["trail"] + m.group(1), html, count=1)
        if 'trail-legend' not in html:
            # fallback: insert right after journey-description p
            html = re.sub(r'(<p class="journey-description">.*?</p>)',
                          lambda m: m.group(1) + cfg["trail"], html, count=1, flags=re.S)

    # ── 7. persona focus/X buttons + show-all + JS ──
    if 'persona-actions' not in html:
        def add_buttons(m):
            dp = m.group(1)
            return m.group(0).replace('</div>\n</div>', '')  # unused
        for scope, p in cfg["personas"].items():
            dp = p["dp"]
            btns = (f'<div class="persona-actions">'
                    f'<button class="persona-btn focus-btn" onclick="focusPersona(\'{dp}\')" title="Focus on {p["name"]}"><span>Focus</span> 🔬</button>'
                    f'<button class="persona-btn remove-btn" onclick="toggleRemovePersona(\'{dp}\')" title="Hide {p["name"]}"><span>Remove</span> ❌</button>'
                    f'</div>')
            # insert before the closing of that persona-card: after persona-role div
            pat = re.compile(r'(<div class="persona-card" data-persona="' + dp +
                             r'">.*?<div class="persona-role">[^<]*</div>)', re.S)
            html = pat.sub(lambda m: m.group(1) + btns, html, count=1)
        # show-all button after the persona-filters container
        html = re.sub(r'(<div class="persona-filters">.*?</div>\s*</div>)',
                      lambda m: m.group(1) + '\n<button class="show-all-btn" onclick="showAllPersonas()">Show all personas</button>',
                      html, count=1, flags=re.S)
    if 'focusPersona' not in html.split('</body>')[0].split('<script>')[-1] and 'function focusPersona' not in html:
        html = html.replace('</body>', FOCUS_JS + '\n</body>')

    # ── 8. CSS additions ──
    if 'trail-legend{' not in html:
        html = html.replace('</style>', CSS_ADD + '</style>', 1)

    path.write_text(html, encoding="utf-8")
    print(f"{cfg['file']}: rewrites {applied}/{len(rev.get('rewrites',{}))}, verbatims synced {synced}, "
          f"item-refs linked, prov-links added {added_prov}, warnings {len(warn)}")
    for w in warn[:15]: print("   -", w)
    return warn

if __name__ == "__main__":
    allwarn = []
    for slug, cfg in MAPS.items():
        if (HERE / f"revisions-{slug}.json").exists():
            allwarn += process(slug, cfg)
        else:
            print(f"revisions-{slug}.json not present yet — skipped")
    print("DONE", "with warnings" if allwarn else "clean")
