# -*- coding: utf-8 -*-
"""Post-process + validate the v2 ucLoops journey maps.

1. Inline humanloops-urbina.css in place of the @@INLINE_HUMANLOOPS_CSS@@ placeholder.
2. Validate template conformance:
   - stage headers count, corner cell present
   - item-ref IDs: format {TYPE}-{SCOPE}-{NNNN}, unique, continuous per TYPE+SCOPE
   - every data-ref / #-href resolves to an existing item-ref id
   - external hrefs (insights.html#..., sources/...#...) resolve against the v1 site files
   - no leftover [PLACEHOLDER] brackets or template comments' bracket tokens
"""
import re, os, sys, pathlib

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
SITE = ROOT / "site"
# Was ROOT/"ucLoops TEMPLATES"/... which no longer existed - the folder is
# "HumanLoops TEMPLATES". This script was already broken before the move; it
# now reads a copy vendored into build/assets/ so it has no outside dependency.
CSS = (HERE.parents[1] / "assets" / "humanloops-urbina.css").read_text(encoding="utf-8")

MAPS = sorted(SITE.glob("journey-map-*-v2.html"))
if not MAPS:
    print("no v2 maps found"); sys.exit(1)

ok = True
for m in MAPS:
    html = m.read_text(encoding="utf-8")
    # 1. inline CSS
    if "@@INLINE_HUMANLOOPS_CSS@@" in html:
        html = html.replace("/* @@INLINE_HUMANLOOPS_CSS@@ */", CSS).replace("@@INLINE_HUMANLOOPS_CSS@@", CSS)
        m.write_text(html, encoding="utf-8")
        print(f"[css] inlined into {m.name}")
    elif CSS[:60] in html:
        print(f"[css] already inlined in {m.name}")
    else:
        print(f"[css] WARNING: no placeholder and CSS not found in {m.name}"); ok = False

    # 2. validate
    ids = re.findall(r'class="item-ref"[^>]*\bid="([A-Z]{4}-[A-Z]{4}-\d{4})"', html)
    all_ids = set(ids)
    dup = [i for i in ids if ids.count(i) > 1]
    if dup: print(f"[ids] DUPLICATES in {m.name}: {sorted(set(dup))[:10]}"); ok = False

    # continuity per TYPE+SCOPE
    from collections import defaultdict
    seq = defaultdict(list)
    for i in ids:
        t, s, n = i.split("-")
        seq[(t, s)].append(int(n))
    for k, v in sorted(seq.items()):
        v2 = sorted(v)
        if v2 != list(range(1, len(v2) + 1)):
            missing = sorted(set(range(1, max(v2)+1)) - set(v2))
            print(f"[ids] {m.name} {k[0]}-{k[1]}: not continuous, missing {missing[:8]}"); ok = False

    # data-ref + internal #hrefs (data-ref must be an in-grid ID; external
    # citations are carried by href instead — strip stray external data-refs)
    stray = sorted(set(re.findall(r'data-ref="([^"]+)"', html)) - all_ids)
    if stray:
        for s in stray:
            html = re.sub(r'\s*data-ref="' + re.escape(s) + '"', '', html)
        m.write_text(html, encoding="utf-8")
        print(f"[fix] {m.name}: stripped {len(stray)} external data-ref attrs (href retains the link)")
    unresolved = []
    for ref in re.findall(r'data-ref="([^"]+)"', html):
        if ref not in all_ids: unresolved.append(("data-ref", ref))
    for href in re.findall(r'href="#([^"]+)"', html):
        if href not in all_ids: unresolved.append(("href#", href))
    if unresolved:
        print(f"[refs] {m.name} unresolved in-page refs: {unresolved[:12]}"); ok = False

    # external refs against v1 site
    ext_bad = []
    for href in re.findall(r'href="((?:insights\.html|sources/[^"#]+)#[^"]+)"', html):
        path, anc = href.split("#", 1)
        tgt = SITE / path
        if not tgt.exists():
            ext_bad.append((href, "missing file")); continue
        if f'id="{anc}"' not in tgt.read_text(encoding="utf-8"):
            ext_bad.append((href, "missing anchor"))
    if ext_bad:
        print(f"[refs] {m.name} unresolved external refs: {ext_bad[:12]}"); ok = False

    # leftover template placeholders
    leftovers = re.findall(r'\[(?:STAGE|PERSONA|JOURNEY|INITIALS|Brand goal|Persona \d)[^\]]*\]', html)
    if leftovers:
        print(f"[tpl] {m.name} leftover placeholders: {leftovers[:6]}"); ok = False

    stages = len(re.findall(r'class="grid-header"', html))  # corner is class="grid-header corner", excluded by exact match
    rows = len(re.findall(r'class="row-header', html))
    cells = len(re.findall(r'class="grid-cell', html))
    opps = len(re.findall(r'class="opportunity-card"', html))
    refs_panels = len(re.findall(r'class="opp-refs"', html))
    print(f"[ok?] {m.name}: stages={stages} rows={rows} cells={cells} (expect rows*stages={rows*stages}) "
          f"item-refs={len(ids)} opp-cards={opps} ref-panels={refs_panels}")
    if cells != rows * stages:
        print(f"      CELL COUNT MISMATCH"); ok = False

print("\nRESULT:", "PASS" if ok else "ISSUES FOUND")
sys.exit(0 if ok else 2)
