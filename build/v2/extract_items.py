# -*- coding: utf-8 -*-
"""Extract every item-ref item from the v2 maps into compact JSON for revision agents.
Output: v2/items-<slug>.json  [{id,row,stage,scope,text}]  (text = inner HTML after the item-ref span)
Also extracts the journey-description html."""
import re, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parents[1] / "site"

ROW_OF = {"GOAL":"Goals","NARR":"Narrative","QUES":"Questions","PROB":"Problems","TASK":"Tasks",
          "SENT":"Sentiment","QUOT":"Think/Feel quote","ALTP":"Alternate paths","CHAN":"Channels",
          "OPPO":"Opportunities","CONT":"Content assets","CTAT":"Calls to action",
          "ENTR":"Entry signals","TRAN":"Transition signals","DGEN":"Data generated","DUSE":"Data used"}

for f in sorted(SITE.glob("journey-map-*-v2.html")):
    html = f.read_text(encoding="utf-8")
    body = html.split("</style>", 1)[1]
    desc = re.search(r'<p class="journey-description">(.*?)</p>', body, re.S)
    items = []
    # walk grid cells to know stage index: count grid-cell occurrences per row block
    # simpler: per row (TYPE+SCOPE) items are continuous; stage = position of the enclosing
    # grid-cell among cells after its row-header. We approximate stage by cell walking:
    pos = 0
    stage = 0
    for m in re.finditer(r'<div class="(?:row-header|grid-cell)[^"]*"|<(?:span|a) class="item-ref"[^>]*id="([A-Z]{4}-[A-Z]{4}-\d{4})"[^>]*>[^<]*</(?:span|a)>', body):
        tok = m.group(0)
        if tok.startswith('<div class="row-header'):
            stage = 0
        elif tok.startswith('<div class="grid-cell'):
            stage += 1
        else:
            iid = m.group(1)
            t, s, n = iid.split("-")[0], iid.split("-")[1], iid.split("-")[2]
            # inner text: from end of the span to nearest closing </li> or </p>
            rest = body[m.end():]
            endm = re.search(r'</li>|</p>', rest)
            text = rest[:endm.start()] if endm else rest[:200]
            items.append({"id": iid, "row": ROW_OF.get(t, t), "stage": stage,
                          "scope": s, "text": text.strip()})
    slug = f.stem.replace("journey-map-", "").replace("-v2", "")
    out = {"file": f.name, "journey_description": desc.group(1).strip() if desc else "",
           "items": items}
    (HERE / f"items-{slug}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    c = Counter(i["scope"] for i in items)
    print(f"{f.name}: {len(items)} items, scopes {dict(c)}, stages seen {max(i['stage'] for i in items)}")
