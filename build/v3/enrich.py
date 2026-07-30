# -*- coding: utf-8 -*-
"""Add the INSIGHT -> / VERBATIM -> provenance trail to journey-map persona-row items.
Modes:
  extract  -> write enrich-src-<slug>.json  (persona-scope items: id,row,scope,text) for the agents
  inject   -> read enrich-<slug>.json {id:{insights:[],verbatim:[]}} + build evidence rows into the maps
Usage: python enrich.py extract | python enrich.py inject
"""
import sys, re, json, html, pathlib

HERE = pathlib.Path(__file__).resolve().parent
WORK = HERE.parent / "data"
SITE = HERE.parents[1] / "site"
IDX = json.loads((WORK / "anchor-index.json").read_text(encoding="utf-8"))
ANCH, SRC = IDX["anchors"], IDX["sources"]
INS = {}
for f in ("insights-consumer-a.json","insights-consumer-b.json","insights-franchisee.json","insights-brand.json"):
    for i in json.loads((WORK/f).read_text(encoding="utf-8")): INS[i["id"]] = i

ROW = {"GOAL":"Goals","NARR":"Narrative","QUES":"Questions","PROB":"Problems","TASK":"Tasks",
       "SENT":"Sentiment","QUOT":"Think/Feel","ALTP":"Alternate paths","CHAN":"Channels"}
PERSONA_SCOPES = {"MATE","OMAR","GRAC"}
MAPS = {"late-night":"journey-map-late-night-v3.html","business-lunch":"journey-map-business-lunch-v3.html"}
ITEMRX = re.compile(r'<a class="item-ref" id="([A-Z]{4})-([A-Z]{4})-(ST\d{2}-)?(\d{4})"[^>]*>[^<]*</a>(.*?)(</li>|</p>)', re.S)

def esc(s): return html.escape(str(s), quote=True)

def extract():
    for slug, fn in MAPS.items():
        htmltext = (SITE/fn).read_text(encoding="utf-8")
        items = []
        for m in ITEMRX.finditer(htmltext):
            T,S,st,N,inner,_ = m.groups()
            if S not in PERSONA_SCOPES: continue
            if T not in ROW: continue
            iid = f"{T}-{S}-{st or ''}{N}"
            text = re.sub(r'<[^>]+>','', inner).strip()
            items.append({"id":iid,"row":ROW[T],"scope":S,"text":text})
        (HERE/f"enrich-src-{slug}.json").write_text(json.dumps(items,indent=1,ensure_ascii=False),encoding="utf-8")
        print(f"{fn}: {len(items)} persona-row items -> enrich-src-{slug}.json")

def evref(aid):
    r = ANCH.get(aid)
    if aid in SRC:
        m=SRC[aid]; lbl=f'{aid} · {m.get("participant","")}'.strip(" ·"); href=m.get("html"); q="(full source)"
    elif r:
        k=r.get("kind")
        lbl=(f'{r.get("source_key")} · {r.get("speaker")}' if k=="transcript-turn"
             else {"social":"Social mention","ticket":"Franchisee ticket","pain":"Pain point","applog-row":"App search log",
                   "mr-claim":"Market report · claim","mr-ref":"Market report · ref","factsheet-section":"Factsheet"}.get(k,k)+" "+aid)
        href=f'{SRC.get(r.get("source_key"),{}).get("html","index.html")}#{aid}'; q=" ".join(r.get("text","").split())
    else:
        return None
    q=esc(q[:240])+("…" if len(q)>240 else "")
    return f'<a class="evref" href="{href}">{esc(aid)}<span class="tip"><span class="src">{esc(lbl)}</span>“{q}”</span></a>'

def insref(iid):
    i=INS.get(iid)
    if not i: return None
    return (f'<a class="evref insid" href="insights.html#{iid}">{esc(iid)}'
            f'<span class="tip"><span class="src">Insight · {esc(i.get("category",""))}</span>{esc(i.get("statement",""))}</span></a>')

def inject():
    warn=[]
    for slug, fn in MAPS.items():
        prov = json.loads((HERE/f"enrich-{slug}.json").read_text(encoding="utf-8"))
        htmltext=(SITE/fn).read_text(encoding="utf-8")
        # validate + drop bad ids
        added=0
        def repl(m):
            nonlocal added
            T,S,st,N,inner,close=m.groups()
            if S not in PERSONA_SCOPES or T not in ROW: return m.group(0)
            iid=f"{T}-{S}-{st or ''}{N}"
            p=prov.get(iid)
            if not p: return m.group(0)
            ins=[insref(x) for x in p.get("insights",[]) if insref(x)]
            vrb=[evref(x) for x in p.get("verbatim",[]) if evref(x)]
            for x in p.get("insights",[]):
                if not insref(x): warn.append(f"{iid} bad insight {x}")
            for x in p.get("verbatim",[]):
                if not evref(x): warn.append(f"{iid} bad verbatim {x}")
            if not ins and not vrb: return m.group(0)
            bits=[]
            if ins: bits.append('<span class="lbl">Insight →</span> '+' '.join(ins))
            if vrb: bits.append('<span class="lbl">Verbatim →</span> '+' '.join(vrb))
            added+=1
            return (m.group(0)[:-len(close)] + f'<div class="evidence">{"  ".join(bits)}</div>' + close)
        htmltext=ITEMRX.sub(repl,htmltext)
        (SITE/fn).write_text(htmltext,encoding="utf-8")
        print(f"{fn}: injected provenance into {added} items")
    if warn:
        print("WARNINGS:",len(warn)); [print("  -",w) for w in warn[:20]]

if __name__=="__main__":
    (extract if sys.argv[1:]==["extract"] else inject if sys.argv[1:]==["inject"] else extract)()
