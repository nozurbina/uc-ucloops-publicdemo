# -*- coding: utf-8 -*-
"""Render v3 persona pages on the real persona-template.html structure + humanloops brand CSS.
   - sections in /persona-export order, section-slug ids (journey maps deep-link to these)
   - item-ref IDs {TYPE}-{CODE}-{NNNN} are clickable <a> links to their primary insight
   - each item also shows an evidence row (source-anchor links) so the page reaches verbatims
Reads: v3/persona-v3-*.json, anchor-index.json, merged insights.
Writes: site/persona-<slug>-v3.html
"""
import json, os, re, sys, html, pathlib

HERE = pathlib.Path(__file__).resolve().parent
WORK = HERE.parent / "data"
ROOT = HERE.parents[1]
# Same override as build.py, so a dry run into a scratch directory can be diffed
# against site/ before anything overwrites it.
SITE = pathlib.Path(os.environ.get("BORDERBLEND_SITE") or (ROOT / "site"))

sys.path.insert(0, str(HERE.parent))
import chrome   # the shared top chrome — same markup build.py emits
import naming   # output filenames for persona pages
import styles   # the same composed stylesheet build.py inlines

CSS = styles.stylesheet()
IDX = json.loads((WORK / "anchor-index.json").read_text(encoding="utf-8"))
ANCH, SRC = IDX["anchors"], IDX["sources"]
INS = {}
for f in ("insights-consumer-a.json","insights-consumer-b.json","insights-franchisee.json","insights-brand.json"):
    for i in json.loads((WORK/f).read_text(encoding="utf-8")):
        INS[i["id"]] = i

def esc(s): return html.escape(str(s), quote=True)

SECT = {  # type -> (section slug/id, title, icon, css-variant, layout)
 "DEMO":("demographics","Demographics and key characteristics","&#128100;","","list"),
 "MIND":("background-mindset","Background and mindset","&#128161;","","list"),
 "EMOT":("main-emotions","Main emotions","&#128148;","","emotions"),
 "VOIC":("voice-tone","Voice and tone","&#128172;","","voice"),
 "GOAL":("goals","Goals","&#127919;","goals","list"),
 "TASK":("key-tasks","Key tasks","&#9745;","","list"),
 "PAIN":("pain-points","Pain points","&#9888;","pain-points","list"),
 "FEAR":("fears-concerns","Fears and concerns","&#128561;","pain-points","list"),
 "ETRI":("emotional-triggers","Emotional decision triggers","&#128293;","","list"),
 "XTRI":("external-triggers","External decision triggers","&#128202;","","list"),
 "CRIT":("decision-criteria","Key decision criteria","&#9878;","","list"),
 "CHAN":("tools-channels","Tools and channels","&#128421;","","channels"),
 "RELT":("relationships","Relationships","&#128101;","","rels"),
}
TWO_COL = [("DEMO","MIND"),("GOAL","TASK"),("ETRI","XTRI")]

def md_inline(t):
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    return t

def src_html(key): return SRC.get(key, {}).get("html", "index.html")

def evref(aid):
    r = ANCH.get(aid)
    if aid in SRC:
        m = SRC[aid]; lbl = f'{aid} · {m.get("participant","")}'.strip(" ·"); href = m.get("html"); q="(full source)"
    elif r:
        kind = r.get("kind")
        lbl = (f'{r.get("source_key")} · {r.get("speaker")}' if kind=="transcript-turn"
               else {"social":"Social mention","ticket":"Franchisee ticket","pain":"Pain point",
                     "applog-row":"App search log","mr-claim":"Market report · claim","mr-ref":"Market report · ref",
                     "factsheet-section":"Factsheet"}.get(kind,kind)+" "+aid)
        href = f'{src_html(r.get("source_key"))}#{aid}'; q = " ".join(r.get("text","").split())
    else:
        return f'<span class="evref" style="opacity:.5">{esc(aid)}</span>'
    q = esc(q[:260]) + ("…" if len(q)>260 else "")
    return f'<a class="evref" href="{href}">{esc(aid)}<span class="tip"><span class="src">{esc(lbl)}</span>“{q}”</span></a>'

def insref(iid):
    i = INS.get(iid)
    if not i: return f'<span class="evref" style="opacity:.5">{esc(iid)}</span>'
    return (f'<a class="evref insid" href="insights.html#{iid}">{esc(iid)}'
            f'<span class="tip"><span class="src">Insight · {esc(i.get("category",""))}</span>{esc(i.get("statement",""))}</span></a>')

def item_id_link(iid, insights, evidence):
    """The item-ref badge itself links to its primary insight (chain to verbatim); fallback evidence/self."""
    href = f"#{iid}"; tip = ""
    if insights and insights[0] in INS:
        href = f"insights.html#{insights[0]}"
        tip = ' title="Insight: ' + esc(INS[insights[0]].get("statement","")) + '"'
    elif evidence:
        a = evidence[0]; r = ANCH.get(a)
        if a in SRC: href = SRC[a]["html"]
        elif r: href = f'{src_html(r.get("source_key"))}#{a}'
        tip = ' title="Source evidence"'
    return f'<a class="item-ref" id="{iid}" href="{href}"{tip}>{iid}</a>'

def ev_row(insights, evidence):
    bits = []
    if insights: bits.append('<span class="lbl">Insight →</span> ' + " ".join(insref(i) for i in insights))
    if evidence: bits.append('<span class="lbl">Verbatim →</span> ' + " ".join(evref(a) for a in evidence))
    return f'<div class="evidence">{"  ".join(bits)}</div>' if bits else ""

def render(persona, out_slug):
    code = persona["code"]; slug = out_slug
    counters = {}
    def nid(t):
        counters[t] = counters.get(t,0)+1
        return f"{t}-{code}-{counters[t]:04d}"
    secmap = {s["type"]: s for s in persona["sections"]}

    def li_items(sec):
        out = []
        for it in sec.get("items", []):
            iid = nid(sec["type"])
            out.append(f'<li>{item_id_link(iid, it.get("insights",[]), it.get("evidence",[]))}'
                       f'{md_inline(it.get("text",""))}{ev_row(it.get("insights",[]), it.get("evidence",[]))}</li>')
        return "<ul>" + "".join(out) + "</ul>"

    def render_section(t):
        sec = secmap.get(t)
        if not sec: return ""
        sslug, title, icon, variant, layout = SECT[t]
        head = f'<h3><span class="section-icon">{icon}</span> {title}</h3>'
        cls = "section" + (f" {variant}" if variant else "")
        if layout == "list":
            inner = li_items(sec)
        elif layout == "emotions":
            tags = []
            for e in sec.get("emotions", []):
                iid = nid(t)
                tags.append(f'<div class="emotion-tag">{item_id_link(iid, e.get("insights",[]), e.get("evidence",[]))}'
                            f'{e.get("emoji","")} <span class="emotion-label">{md_inline(e.get("label",""))}</span> &mdash; {md_inline(e.get("tail",""))}</div>')
            inner = '<div class="emotion-grid">' + "".join(tags) + "</div>"
        elif layout == "voice":
            iid = nid("VOIC")
            inner = (f'<p class="voice-description">{item_id_link(iid, sec.get("voice_insights",[]), [])}'
                     f'{md_inline(sec.get("voice",""))}{ev_row(sec.get("voice_insights",[]), [])}</p>')
            for q in sec.get("quotes", []):
                qid = nid("QUOT")
                inner += (f'<div class="quote-block">{item_id_link(qid, q.get("insights",[]), q.get("evidence",[]))}'
                          f'&ldquo;{md_inline(q.get("text",""))}&rdquo;{ev_row(q.get("insights",[]), q.get("evidence",[]))}</div>')
        elif layout == "channels":
            lis = []
            for n, it in enumerate(sec.get("items", []), 1):
                iid = nid(t)
                lis.append(f'<li><span class="channel-number">{n}</span><span>{item_id_link(iid, it.get("insights",[]), it.get("evidence",[]))}'
                           f'{md_inline(it.get("text",""))}{ev_row(it.get("insights",[]), it.get("evidence",[]))}</span></li>')
            inner = '<ul class="channel-list">' + "".join(lis) + "</ul>"
        elif layout == "rels":
            blocks = []
            for r in sec.get("rels", []):
                iid = nid(t)
                pts = "".join(f"<li>{md_inline(p)}</li>" for p in r.get("points", []))
                blocks.append(f'<div class="relationship-block"><h4>{item_id_link(iid, r.get("insights",[]), r.get("evidence",[]))}'
                              f'{md_inline(r.get("label",""))}</h4><ul>{pts}</ul>{ev_row(r.get("insights",[]), r.get("evidence",[]))}</div>')
            inner = "".join(blocks)
        return f'<div class="{cls}" id="{sslug}">{head}{inner}</div>'

    # assemble body honouring two-col pairings
    done = set()
    body_parts = []
    order = [s["type"] for s in persona["sections"]]
    for t in order:
        if t in done: continue
        pair = next((p for p in TWO_COL if t in p), None)
        if pair and all(x in secmap for x in pair):
            body_parts.append('<div class="two-col">' + render_section(pair[0]) + render_section(pair[1]) + "</div>")
            done.update(pair)
        else:
            body_parts.append(render_section(t)); done.add(t)

    # No link out to a journey map: a persona can appear in any number of them, so
    # naming one here would be arbitrary. The maps link *to* the persona, not back.
    # The headshot is named after the persona's agent id — the same lowercase id the
    # companion app takes in ?agent=, so one value covers the photo and the sim link.
    # It sits *before* .initials, which stays as the fallback underneath it.
    agent = persona.get("agent")
    headshot = (f'<img src="headshots/{agent}.jpg" alt="{esc(persona["name"])}">'
                if agent else "")
    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Persona: {esc(persona['name'])} — {esc(persona['role'])}</title>
<style>{CSS}
a.item-ref{{text-decoration:none;cursor:pointer}}a.item-ref:hover{{outline:1px solid #f59e0b}}
.content .evidence{{margin:.3rem 0 .2rem}}.persona-topbar{{max-width:960px;margin:0 auto;padding:.6rem 1.5rem 0}}
.persona-topbar a{{font-size:.8rem;color:#667085}}.trail-note{{max-width:960px;margin:.4rem auto 0;padding:0 1.5rem}}
.trail-note .tn{{background:#fff8ef;border:1px solid #f3c9ad;border-radius:10px;padding:.6rem .9rem;font-size:.82rem;color:#7a4b2a}}
.persona-topbar .provtoggle{{float:right}}
</style></head><body class="prov-hidden">
{chrome.EARLY}{chrome.chrome(chrome.sticky_bar())}
<header class="page-header">
<h1>Persona Profile</h1>
<div class="avatar-wrapper">{headshot}<div class="initials">{esc(persona['initials'])}</div></div>
<div class="persona-name">{esc(persona['name'])}</div>
<div class="persona-role">{esc(persona['role'])}</div>
</header>
<div class="trail-note"><div class="tn"><a class="trail-toggle" href="#" onclick="return ucToggleFromTrail()"><b>Evidence trail</b></a>: every item ID links to the <b>insight</b> it rests on; each insight links down to the <b>verbatim</b> source. Direct source quotes are linked inline too.</div></div>
<main class="content">
{''.join(body_parts)}
</main>
<footer class="page-footer"><div>Prepared by: ucLoops UX Assistant | Urbina Consulting — BorderBlend (synthetic)</div></footer>
<script>function toggleProv(btn){{var on=document.body.classList.toggle('prov-hidden');btn.innerHTML=on?'Show Item IDs &amp; Provenance':'Hide Item IDs &amp; Provenance';}}
/* The "Evidence trail" label is the explanation of what the toggle does, so it is
   also the control — people read the sentence and then look for the switch. */
function ucToggleFromTrail(){{toggleProv(document.querySelector('.provtoggle'));return false;}}
document.addEventListener('DOMContentLoaded',function(){{function f(){{var h=location.hash.slice(1);if(!h)return;var el=document.getElementById(decodeURIComponent(h));if(el){{el.style.transition='background 1.5s';el.style.background='#fff3c9';setTimeout(function(){{el.style.background='';}},1500);el.scrollIntoView({{block:'center'}});}}}}window.addEventListener('hashchange',f);f();}});</script>
{chrome.SCRIPTS}</body></html>
{chrome.MARKER}
"""
    # pers-<person>-<archetype>-v3.html — see naming.py for why both halves.
    out = naming.persona_page(persona["agent"], persona["archetype"])
    (SITE / out).write_text(doc, encoding="utf-8")
    return out, sum(counters.values())

if __name__ == "__main__":
    import glob
    for f in sorted(glob.glob(str(HERE/"persona-v3-*.json"))):
        p = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        out_slug = pathlib.Path(f).stem.replace("persona-v3-", "")
        out, n = render(p, out_slug)
        print(f"{out}  ({n} item-refs)")
