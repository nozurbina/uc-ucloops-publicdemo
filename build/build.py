# -*- coding: utf-8 -*-
"""
BorderBlend synthetic case — static site generator.

Single source of truth for the evidence trail:
  Journey cell -> Insight -> verbatim (transcript turn / dataset item / market claim).

Pass A: parse + number + anchor all SOURCE docs; emit anchor-index.json; render source HTML.
Pass B: render insights / personas / journeys from JSON with resolved cross-links; render index.

Design rules enforced here:
  1. Every link targets a specific #anchor (never page top).
  2. Every ID is itself a clickable link (self-link on sources; nav link on deliverables).
  3. Trail resolves all the way down to the verbatim quote.
"""
import json, re, html, os, pathlib

import chrome   # shared top chrome (promo banner + sticky bar); see chrome.py
import styles   # the composed stylesheet; see styles.py

# Everything this needs lives in the repo, so paths are relative to this file.
# It used to read from the uc-pharma-analysis workspace where BorderBlend was
# first built; that dependency is gone.
HERE = pathlib.Path(__file__).resolve().parent          # <repo>/build
ROOT = HERE.parent                                      # <repo>
SRC_DIR = HERE / "source-data"                          # the 27 synthetic .md sources
WORK = HERE / "data"                                    # JSON + the anchor index

# `site/` is the published folder — the publisher is pointed at it directly, which
# is why the toolchain sits outside it. BORDERBLEND_SITE can override for a dry run
# into a scratch directory.
#
# NOTE: generating is only half the job — see postbuild/README.md. A bare build
# produces a site with the old broken chrome, no mobile support, and no links to
# the persona sim app.
SITE = pathlib.Path(os.environ.get("BORDERBLEND_SITE") or (ROOT / "site"))
SRC_OUT = SITE / "sources"
for d in (SITE, SRC_OUT):
    d.mkdir(parents=True, exist_ok=True)

# anchor registry: id -> record
ANCHORS = {}
SOURCES = {}   # source_key -> meta

def esc(s): return html.escape(s, quote=True)

# ───────────────────────── minimal markdown (inline) ─────────────────────────
def md_inline(text):
    """Bold, italic, code, links, and MR reference markers -> HTML. Text is raw md."""
    # escape first, then re-introduce tags
    t = esc(text)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)', r'<em>\1</em>', t)
    # markdown links [txt](url)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    return t

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

# ───────────────────────── block markdown (generic) ─────────────────────────
def md_blocks(md, row_anchor_prefix=None, row_counter=None):
    """
    Convert a markdown string to HTML. Supports headings, hr, lists, GFM tables,
    blockquotes, paragraphs. If row_anchor_prefix is given, each table body <tr>
    gets an id (prefix-rN) and its first cell carries a clickable id badge.
    row_counter is a mutable [int] so numbering can continue across calls.
    Returns (html, headings) where headings is list of (level, text, id).
    """
    lines = md.split('\n')
    out, headings = [], []
    i, n = 0, len(lines)
    if row_counter is None: row_counter = [0]

    def flush_para(buf):
        if buf:
            out.append('<p>' + md_inline(' '.join(buf).strip()) + '</p>')
            buf.clear()

    para = []
    while i < n:
        ln = lines[i]
        s = ln.strip()
        # heading
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            flush_para(para)
            lvl = len(m.group(1)); txt = m.group(2).strip()
            hid = slug(txt)[:60] or f'h{i}'
            headings.append((lvl, txt, hid))
            out.append(f'<h{lvl} id="{hid}">{md_inline(txt)}</h{lvl}>')
            i += 1; continue
        # hr
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', s):
            flush_para(para); out.append('<hr/>'); i += 1; continue
        # table (GFM): header line then |---| separator
        if '|' in s and i+1 < n and re.match(r'^\s*\|?[\s:|-]+\|?\s*$', lines[i+1]) and '-' in lines[i+1]:
            flush_para(para)
            def cells(row):
                r = row.strip()
                if r.startswith('|'): r = r[1:]
                if r.endswith('|'): r = r[:-1]
                return [c.strip() for c in r.split('|')]
            header = cells(lines[i]); i += 2
            body = []
            while i < n and '|' in lines[i] and lines[i].strip():
                body.append(cells(lines[i])); i += 1
            thead = '<thead><tr>' + ''.join(f'<th>{md_inline(c)}</th>' for c in header) + '</tr></thead>'
            trs = []
            for row in body:
                row_counter[0] += 1
                rid = f'{row_anchor_prefix}-r{row_counter[0]}' if row_anchor_prefix else None
                tds = []
                for ci, c in enumerate(row):
                    inner = md_inline(c)
                    if ci == 0 and rid:
                        badge = f'<a class="rowid" href="#{rid}">{rid}</a> '
                        inner = badge + inner
                    tds.append(f'<td>{inner}</td>')
                idattr = f' id="{rid}"' if rid else ''
                if rid:
                    ANCHORS[rid] = {'kind':'applog-row','text':' | '.join(row),
                                    'source_key':row_anchor_prefix,'speaker':'','role':''}
                trs.append(f'<tr{idattr}>' + ''.join(tds) + '</tr>')
            out.append('<div class="tablewrap"><table>' + thead + '<tbody>' + ''.join(trs) + '</tbody></table></div>')
            continue
        # blockquote
        if s.startswith('>'):
            flush_para(para)
            q = []
            while i < n and lines[i].strip().startswith('>'):
                q.append(lines[i].strip()[1:].strip()); i += 1
            out.append('<blockquote>' + md_inline(' '.join(q)) + '</blockquote>'); continue
        # lists
        if re.match(r'^[-*+]\s+', s) or re.match(r'^\d+\.\s+', s):
            flush_para(para)
            ordered = bool(re.match(r'^\d+\.\s+', s))
            tag = 'ol' if ordered else 'ul'
            items = []
            while i < n and (re.match(r'^[-*+]\s+', lines[i].strip()) or re.match(r'^\d+\.\s+', lines[i].strip())):
                it = re.sub(r'^([-*+]|\d+\.)\s+', '', lines[i].strip())
                items.append('<li>' + md_inline(it) + '</li>'); i += 1
            out.append(f'<{tag}>' + ''.join(items) + f'</{tag}>'); continue
        # blank
        if not s:
            flush_para(para); i += 1; continue
        para.append(s); i += 1
    flush_para(para)
    return '\n'.join(out), headings

# ───────────────────────── page shell ─────────────────────────
def css():
    return styles.stylesheet()

def page(title, body, rel="", extra_head="", body_class="", prov=False, bar=None):
    """Full page. The top chrome (promo banner + sticky bar) is emitted here for
    every page — see chrome.py; it used to be bolted on by postbuild patches, which
    is what made the site un-rebuildable.

    `prov` gives the page a sticky bar with the provenance toggle, and starts it
    folded. `bar=True` with `prov=False` gives the bar without the toggle — for the
    factsheet and the market report, where every claim is an addressable anchor by
    design and there is nothing to fold away.
    """
    show_bar = prov if bar is None else bar
    bar_html = ""
    if prov:
        body_class = (body_class + " prov-hidden").strip()
    if show_bar:
        bar_html = chrome.sticky_bar(home=f'{rel}index.html', toggle=prov)
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<style>{css()}</style>{extra_head}
</head><body class="{body_class}">
{chrome.EARLY}{chrome.chrome(bar_html)}{body}
<script>{JS}</script>
{chrome.SCRIPTS}</body></html>
{chrome.MARKER}
"""

JS = r"""
// Toggle item IDs + provenance (evidence rows). Pages start with body.prov-hidden.
function toggleProv(btn){
  var on = document.body.classList.toggle('prov-hidden');
  btn.innerHTML = on ? 'Show Item IDs &amp; Provenance' : 'Hide Item IDs &amp; Provenance';
}
// Evidence-trail helpers: hover/click preview of the verbatim a link points to.
document.addEventListener('DOMContentLoaded',function(){
  // highlight target on hash nav
  function flash(){var h=location.hash.slice(1); if(!h)return;
    var el=document.getElementById(decodeURIComponent(h)); if(el){el.classList.add('flash');
    setTimeout(function(){el.classList.remove('flash');},1600); el.scrollIntoView({block:'center'});}}
  window.addEventListener('hashchange',flash); flash();
});
"""

# ───────────────────────── transcript parsing ─────────────────────────
def parse_transcript(path):
    raw = path.read_text(encoding='utf-8')
    lines = raw.split('\n')
    m = re.search(r'#\s*Interview Transcript\s*[—-]\s*([A-Z]+-INT\d+)', raw)
    fname = path.name
    fm = re.search(r'_((?:BB|VER)-INT\d+)_', fname)
    tid = (m.group(1) if m else (fm.group(1) if fm else path.stem)).strip()
    meta = {}
    for mm in re.finditer(r'^\*\*(.+?):\*\*\s*(.*)$', raw, re.M):
        k = mm.group(1).strip()
        if k not in ('Interviewer',) or 'Participant' in meta:  # metadata block only (top)
            pass
    # metadata: bold lines before first '---'
    head = raw.split('\n---',1)[0]
    for mm in re.finditer(r'^\*\*(.+?):\*\*\s*(.*)$', head, re.M):
        meta[mm.group(1).strip()] = mm.group(2).strip()
    # sections
    secs = {}
    for mm in re.finditer(r'^##\s+(.*)$', raw, re.M):
        pass
    parts = re.split(r'^##\s+', raw, flags=re.M)
    for p in parts[1:]:
        title = p.split('\n',1)[0].strip()
        rest = p.split('\n',1)[1] if '\n' in p else ''
        secs[title] = rest.strip()
    # turns
    tsec = secs.get('Transcript','')
    turns = []
    cur = None
    for ln in tsec.split('\n'):
        sm = re.match(r'^\*\*(.+?):\*\*\s?(.*)$', ln)
        if sm:
            if cur: turns.append(cur)
            cur = {'speaker': sm.group(1).strip(), 'text': [sm.group(2)]}
        else:
            if cur is not None:
                cur['text'].append(ln)
    if cur: turns.append(cur)
    # number + register
    participant = meta.get('Participant', tid)
    for idx, t in enumerate(turns, 1):
        aid = f'{tid}-t{idx}'
        t['id'] = aid
        t['text'] = '\n'.join(t['text']).strip()
        role = 'interviewer' if t['speaker'].lower().startswith('interview') else 'participant'
        t['role'] = role
        ANCHORS[aid] = {'kind':'transcript-turn','text':t['text'],'source_key':tid,
                        'speaker':t['speaker'],'role':role,'participant':participant}
    SOURCES[tid] = {'kind':'transcript','title':f'{tid} — {participant.split(".")[0]}',
                    'participant':participant,'meta':meta,'html':f'sources/{tid}.html',
                    'file':path.name,'nturns':len(turns)}
    return tid, meta, secs, turns

def render_transcript(tid, meta, secs, turns):
    metarows = ''.join(f'<div><span class="mk">{esc(k)}</span><span class="mv">{md_inline(v)}</span></div>'
                       for k,v in meta.items())
    pre = md_blocks(secs.get('Pre-interview notes',''))[0]
    post = md_blocks(secs.get('Post-interview notes',''))[0]
    turnhtml = []
    for t in turns:
        paras = ''.join(f'<p>{md_inline(p.strip())}</p>' for p in re.split(r'\n\s*\n', t['text']) if p.strip())
        turnhtml.append(
          f'<div class="turn {t["role"]}" id="{t["id"]}">'
          f'<div class="turnhead"><a class="idbadge" href="#{t["id"]}" title="Permalink to this line">{t["id"]}</a>'
          f'<span class="spk">{esc(t["speaker"])}</span></div>'
          f'<div class="turntext">{paras}</div></div>')
    body = f"""
<header class="srchead">
  <div class="kicker">Source · Interview transcript</div>
  <h1>{esc(tid)} — {esc(meta.get('Participant',''))}</h1>
  <div class="metagrid">{metarows}</div>
</header>
<section class="notes"><h2>Pre-interview notes</h2>{pre}</section>
<section class="transcript"><h2>Transcript <span class="hint">· every line has a permalink ID — this is the leaf of the evidence trail</span></h2>
{''.join(turnhtml)}
</section>
<section class="notes"><h2>Post-interview notes</h2>{post}</section>
"""
    (SRC_OUT / f'{tid}.html').write_text(page(f'{tid} — {meta.get("Participant","")}', body, body_class="srcpage", prov=True, rel="../"), encoding='utf-8')

# ───────────────────────── dataset: card-style (social, tickets) ─────────────
def parse_card_dataset(path, key, id_from_heading, kind, title, kicker):
    raw = path.read_text(encoding='utf-8')
    intro = raw.split('\n## ',1)[0]
    # split into ### blocks
    blocks = re.split(r'^###\s+', raw, flags=re.M)
    cards = []
    for b in blocks[1:]:
        heading = b.split('\n',1)[0].strip()
        aid = id_from_heading(heading)
        if not aid: continue
        content = b.split('\n',1)[1] if '\n' in b else ''
        # stop at a following '## '
        content = re.split(r'^##\s+', content, flags=re.M)[0]
        chtml, _ = md_blocks(content)
        # plain text for index
        txt = re.sub(r'\s+',' ', re.sub(r'\*\*|\*|`|\[|\]|>','', content)).strip()[:600]
        ANCHORS[aid] = {'kind':kind,'text':txt,'source_key':key,'speaker':'','role':'',
                        'heading':heading}
        cards.append((aid, heading, chtml))
    # trailing sections after last card (theme summary / distribution)
    tail = ''
    tm = re.search(r'\n(##\s+(?:Theme summary|Category distribution|Notable patterns)[\s\S]+)$', raw)
    if tm: tail = md_blocks(tm.group(1))[0]
    SOURCES[key] = {'kind':kind,'title':title,'html':f'sources/{key}.html','file':path.name,
                    'ncards':len(cards)}
    # render
    cardhtml = []
    for aid, heading, chtml in cards:
        cardhtml.append(
          f'<div class="card" id="{aid}"><div class="cardhead">'
          f'<a class="idbadge" href="#{aid}">{aid}</a><span class="ch">{md_inline(heading)}</span></div>'
          f'<div class="cardbody">{chtml}</div></div>')
    body = f"""
<header class="srchead"><div class="kicker">Source · {esc(kicker)}</div>
<h1>{esc(title)}</h1>{md_blocks(intro.split(chr(10),1)[1] if chr(10) in intro else '')[0]}</header>
<section class="cards">{''.join(cardhtml)}</section>
{('<section class="notes">'+tail+'</section>') if tail else ''}
"""
    (SRC_OUT / f'{key}.html').write_text(page(title, body, body_class="srcpage", prov=True, rel="../"), encoding='utf-8')

# ───────────────────────── dataset: doc-style (applogs, factsheet) ─────────────
def render_doc_source(path, key, kind, title, kicker, row_prefix=None):
    raw = path.read_text(encoding='utf-8')
    # strip leading H1
    body_md = re.sub(r'^#\s+.*\n','',raw,count=1)
    hhtml, headings = md_blocks(body_md, row_anchor_prefix=row_prefix, row_counter=[0])
    # register factsheet section anchors
    if kind == 'factsheet':
        for lvl,txt,hid in headings:
            if lvl==2:
                ANCHORS[hid] = {'kind':'factsheet-section','text':txt,'source_key':key,'speaker':'','role':''}
    SOURCES[key] = {'kind':kind,'title':title,'html':f'sources/{key}.html','file':path.name}
    body = f"""
<header class="srchead"><div class="kicker">Source · {esc(kicker)}</div><h1>{esc(title)}</h1></header>
<section class="doc">{hhtml}</section>"""
    is_ctx = kind == 'factsheet'
    (SRC_OUT / f'{key}.html').write_text(page(title, body, body_class="srcpage",
                                             prov=not is_ctx, bar=True, rel="../"), encoding='utf-8')

# ───────────────────────── market research (claim anchors) ─────────────
def render_market(path, key='MRKT'):
    raw = path.read_text(encoding='utf-8')
    body_md = re.sub(r'^#\s+.*\n','',raw,count=1)
    # split off the References section (rendered specially so each ref is an anchor target)
    mref = re.search(r'^##\s+References\s*$', body_md, re.M)
    main_md = body_md[:mref.start()] if mref else body_md
    refs_md = body_md[mref.start():] if mref else ''

    # register claim text for the index — split each line on markers so >1 marker/line works
    for line in main_md.split('\n'):
        if '{#MR-C' not in line: continue
        parts = re.split(r'\{#(MR-C\d+)\}', line)
        # parts = [text0, id1, text1, id2, text2, ...]
        for j in range(1, len(parts), 2):
            cid = parts[j]
            txt = re.sub(r'\[MR-REF\d+\]|\{#MR-C\d+\}|[*`]','', parts[j-1]).strip()
            ANCHORS[cid] = {'kind':'mr-claim','text':txt[-360:],'source_key':key,'speaker':'','role':''}

    hhtml, _ = md_blocks(main_md)
    hhtml = re.sub(r'\{#(MR-C\d+)\}',
                   lambda m: f'<a class="claimid" id="{m.group(1)}" href="#{m.group(1)}" title="Cited claim {m.group(1)}">{m.group(1)}</a>', hhtml)
    hhtml = re.sub(r'\[(MR-REF\d+)\]',
                   lambda m: f'<a class="refcite" href="#{m.group(1)}">[{m.group(1)}]</a>', hhtml)

    # References: each "[MR-REFxx] text" -> anchored list row with self-linking id badge
    refs_html = ''
    if refs_md:
        rows = []
        for rm in re.finditer(r'\[(MR-REF\d+)\]\s+(.+)', refs_md):
            rid, rtxt = rm.group(1), rm.group(2).strip().lstrip('-').strip()
            ANCHORS[rid] = {'kind':'mr-ref','text':rtxt[:300],'source_key':key,'speaker':'','role':''}
            rows.append(f'<li id="{rid}"><a class="idbadge" href="#{rid}">{rid}</a> {md_inline(rtxt)}</li>')
        refs_html = '<h2 id="references">References</h2><ol class="reflist">' + ''.join(rows) + '</ol>'

    SOURCES[key] = {'kind':'market','title':'Canadian Mexican & Fusion Street-Food Market — 2026',
                    'html':f'sources/{key}.html','file':path.name}
    body = f"""
<header class="srchead"><div class="kicker">Source · Market research report</div>
<h1>Canadian Mexican &amp; Fusion Street-Food Market — 2026 Outlook</h1>
<p class="hint">Tagged claims (MR-C##) and references (MR-REF##) are individually addressable — downstream insights link straight to the specific claim.</p></header>
<section class="doc market">{hhtml}{refs_html}</section>"""
    (SRC_OUT / f'{key}.html').write_text(page('Market research — BorderBlend', body, body_class="srcpage",
                                             prov=False, bar=True, rel="../"), encoding='utf-8')

# ───────────────────────── heading helpers for datasets ─────────────
def social_id(h):
    m = re.search(r'#(\d+)', h);  return f'SOC-M{int(m.group(1)):03d}' if m else None
def ticket_id(h):
    m = re.search(r'#(\d+)', h);  return f'FT-{int(m.group(1)):03d}' if m else None
def pain_id(h):
    m = re.match(r'\s*([A-O])\.', h); return f'PAIN-{m.group(1)}' if m else None

# ───────────────────────── PASS A ─────────────────────────
def pass_a():
    for p in sorted(SRC_DIR.glob('TRANSCRIPT_*.md')):
        tid, meta, secs, turns = parse_transcript(p)
        render_transcript(tid, meta, secs, turns)
    parse_card_dataset(SRC_DIR/'SOURCES_BorderBlend_ConsumerSocialMentions.md','SOC',
                       social_id,'social','Consumer Social Media Mentions','Social listening')
    parse_card_dataset(SRC_DIR/'SOURCES_BorderBlend_FranchiseePortalTickets.md','FT',
                       ticket_id,'ticket','Franchisee Portal Support Tickets','Support tickets')
    parse_card_dataset(SRC_DIR/'SOURCES_BorderBlend_PainPoints.md','PAIN',
                       pain_id,'pain','BorderBlend Pain Points — Content & Knowledge Gaps','Pain-point inventory')
    render_doc_source(SRC_DIR/'SOURCES_BorderBlend_ConsumerAppSearchLogs.md','APPLOG','applog',
                      'Consumer App Search Logs','App/web search logs', row_prefix='APPLOG')
    render_doc_source(SRC_DIR/'SOURCES_BorderBlend_Factsheet.md','FACT','factsheet',
                      'BorderBlend Company Factsheet','Company factsheet')
    render_market(SRC_DIR/'SOURCES_BorderBlend_MarketResearch.md','MRKT')
    (WORK/'anchor-index.json').write_text(json.dumps(
        {'sources':SOURCES,'anchors':ANCHORS}, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'PASS A ok: {len(SOURCES)} sources, {len(ANCHORS)} anchors')
    # quick breakdown
    from collections import Counter
    c = Counter(a['kind'] for a in ANCHORS.values())
    print('anchors by kind:', dict(c))

# ═══════════════════════════ PASS B ═══════════════════════════
INSIGHTS = {}       # id -> insight dict
PERSONAS = {}       # slug -> persona dict
WARN = []

SRC_LABEL = {'transcript-turn':'Interview','social':'Social mention','ticket':'Franchisee ticket',
 'pain':'Pain point','applog-row':'App search log','mr-claim':'Market report · claim',
 'mr-ref':'Market report · reference','factsheet-section':'Factsheet'}

def load_json(name):
    p = WORK / name
    if not p.exists(): return None
    txt = p.read_text(encoding='utf-8')
    try:
        return json.loads(txt)
    except Exception as e:
        WARN.append(f'JSON parse fail {name}: {e}'); return None

def ev_meta(aid):
    """Return (href, label, quote) for an anchor id (or whole-source key), or None."""
    if aid in SOURCES:   # whole-interview / whole-source citation
        m = SOURCES[aid]
        lbl = f'{aid} · {m.get("participant","")}'.strip(' ·') if m.get('kind')=='transcript' else m.get('title',aid)
        return (m.get('html','index.html'), lbl, '(full source)')
    r = ANCHORS.get(aid)
    if not r: return None
    sk = r.get('source_key'); srch = SOURCES.get(sk, {}).get('html', 'index.html')
    kind = r.get('kind')
    if kind == 'transcript-turn':
        who = r.get('speaker','') ; label = f'{sk} · {who}'
    else:
        label = f'{SRC_LABEL.get(kind,kind)} {aid if kind in ("social","ticket","pain") else ""}'.strip()
    quote = ' '.join(r.get('text','').split())
    return (f'{srch}#{aid}', label, quote)

def evref(aid):
    m = ev_meta(aid)
    if not m:
        WARN.append(f'invalid evidence id: {aid}');
        return f'<span class="evref" style="opacity:.5" title="unresolved">{esc(aid)}</span>'
    href,label,quote = m
    q = esc(quote[:260]) + ('…' if len(quote)>260 else '')
    return (f'<a class="evref" href="{href}">{esc(aid)}'
            f'<span class="tip"><span class="src">{esc(label)}</span>“{q}”</span></a>')

def evidence_row(ids, lbl='Verbatim evidence'):
    if not ids: return ''
    return (f'<div class="evidence"><span class="lbl">{esc(lbl)} →</span> '
            + ' '.join(evref(a) for a in ids) + '</div>')

def insref(ins_id):
    ins = INSIGHTS.get(ins_id)
    if not ins:
        WARN.append(f'invalid insight ref: {ins_id}')
        return f'<span class="evref" style="opacity:.5">{esc(ins_id)}</span>'
    q = esc(ins.get('statement',''))
    return (f'<a class="evref insid" href="insights.html#{ins_id}">{esc(ins_id)}'
            f'<span class="tip"><span class="src">Insight · {esc(ins.get("category",""))}</span>{q}</span></a>')

def insight_row(ids):
    if not ids: return ''
    return (f'<div class="evidence"><span class="lbl">Insight →</span> '
            + ' '.join(insref(i) for i in ids) + '</div>')

# ── insights page ──
def render_insights():
    data = []
    for f in ('insights-consumer-a.json','insights-consumer-b.json',
              'insights-franchisee.json','insights-brand.json'):
        d = load_json(f)
        if d: data.extend(d)
    for ins in data:
        INSIGHTS[ins['id']] = ins
    # validate evidence
    for ins in data:
        ins['evidence'] = [e for e in ins.get('evidence',[]) if (ANCHORS.get(e) or WARN.append(f'{ins["id"]} bad ev {e}'))]
    cats = sorted(set(i.get('category','') for i in data))
    personas = ['late-night-foodie','business-lunch','everyday-20s','family','franchisee','brand']
    def card(ins):
        strength = ins.get('strength','moderate')
        return (f'<article class="insight" id="{ins["id"]}" data-cat="{esc(ins.get("category",""))}" '
          f'data-personas="{esc(" ".join(ins.get("personas",[])))}">'
          f'<h3><a class="idbadge" href="#{ins["id"]}">{ins["id"]}</a> {md_inline(ins.get("title",""))} '
          f'<span class="cat">{esc(ins.get("category",""))}</span>'
          f'<span class="strength st-{strength}">{esc(strength)}</span></h3>'
          f'<div class="body"><p><strong>{md_inline(ins.get("statement",""))}</strong></p>'
          f'<p>{md_inline(ins.get("body",""))}</p>'
          f'<p class="imp">↗ <em>{md_inline(ins.get("implication",""))}</em></p>'
          f'{evidence_row(ins.get("evidence",[]))}</div></article>')
    catbtns = ''.join(f'<button data-f="cat:{esc(c)}">{esc(c)}</button>' for c in cats)
    perbtns = ''.join(f'<button data-f="per:{p}">{p}</button>' for p in personas)
    body = f"""
<header class="srchead"><div class="kicker">Discover phase · Insights</div>
<h1>BorderBlend — Insights</h1>
<p class="hint">{len(data)} insights, each grounded in verbatim evidence. Hover any <span class="evref">ID</span> to preview the source quote; click to jump to it. This is the middle link of the trail: <strong>Journey → Insight → Verbatim</strong>.</p>
<div class="filterbar" id="catbar"><button class="on" data-f="all">All</button>{catbtns}</div>
<div class="filterbar" id="perbar"><span class="lbl" style="align-self:center">Persona:</span>{perbtns}</div>
</header>
<section class="insights">{''.join(card(i) for i in data)}</section>
"""
    (SITE/'insights.html').write_text(page('BorderBlend — Insights', body, body_class='docwrap', extra_head=INSIGHT_JS, prov=True), encoding='utf-8')
    print(f'  insights: {len(data)}')

INSIGHT_JS = """<script>document.addEventListener('DOMContentLoaded',function(){
 var cards=[].slice.call(document.querySelectorAll('.insight'));
 var active={cat:null,per:null};
 function apply(){cards.forEach(function(c){
   var ok=true;
   if(active.cat&&c.dataset.cat!==active.cat)ok=false;
   if(active.per&&c.dataset.personas.split(' ').indexOf(active.per)<0)ok=false;
   c.style.display=ok?'':'none';});}
 document.querySelectorAll('.filterbar button').forEach(function(b){b.onclick=function(){
   var f=b.dataset.f;
   if(f==='all'){active={cat:null,per:null};}
   else if(f.indexOf('cat:')===0){active.cat=active.cat===f.slice(4)?null:f.slice(4);}
   else if(f.indexOf('per:')===0){active.per=active.per===f.slice(4)?null:f.slice(4);}
   document.querySelectorAll('.filterbar button').forEach(function(x){x.classList.remove('on');});
   if(!active.cat&&!active.per)document.querySelector('[data-f=all]').classList.add('on');
   document.querySelectorAll('.filterbar button').forEach(function(x){
     var xf=x.dataset.f;
     if(xf.indexOf('cat:')===0&&active.cat===xf.slice(4))x.classList.add('on');
     if(xf.indexOf('per:')===0&&active.per===xf.slice(4))x.classList.add('on');});
   apply();};});
});</script>"""

# ── personas ──
def render_personas():
    data = []
    order = ['late-night-foodie','business-lunch','everyday-20s','franchisee']
    files = {p.stem.replace('persona-',''):p for p in WORK.glob('persona-*.json')}
    for slug in order + [s for s in files if s not in order]:
        if slug in files:
            d = load_json(files[slug].name)
            if isinstance(d, dict): data.append(d)
            elif isinstance(d, list): data.extend(d)
    for p in data: PERSONAS[p['slug']] = p
    for p in data:
        render_one_persona(p)
    print(f'  personas: {len(data)}')
    return data

def render_one_persona(p):
    slug = p['slug']; pid = f'PERS-{slug}'
    dem = ''.join(f'<div><span class="mk">{esc(k)}</span> <span class="mv">{md_inline(v)}</span></div>'
                  for k,v in p.get('demographics',{}).items())
    blocks = []
    for bi, blk in enumerate(p.get('blocks',[]), 1):
        bslug = slug + '-' + slug_short(blk['title'])
        items = []
        for ii, it in enumerate(blk.get('items',[]), 1):
            iid = f'{pid}-{slug_short(blk["title"])}-{ii}'
            items.append(
              f'<div class="pitem" id="{iid}"><a class="idbadge" href="#{iid}">{iid}</a> '
              f'<span class="txt">{md_inline(it.get("text",""))}</span>'
              f'{insight_row(it.get("insights",[]))}'
              f'{evidence_row(it.get("evidence",[])) if it.get("evidence") else ""}</div>')
        blk_id = f'{pid}-{slug_short(blk["title"])}'
        blocks.append(f'<div class="pblock" id="{blk_id}"><h3><a class="idbadge" href="#{blk_id}">{blk_id}</a> {esc(blk["title"])}</h3>{"".join(items)}</div>')
    qev = evidence_row(p.get('quote_evidence',[]),'Quote source') if p.get('quote_evidence') else ''
    srcline = ('<p class="hint">Built from: ' +
               ' '.join(evref(a) for a in p.get('evidence',[])) + '</p>') if p.get('evidence') else ''
    body = f"""
<div class="persona-head">
  <div class="avatar" style="background:{p.get('color','var(--accent)')}">{p.get('emoji','🌮')}</div>
  <div><div class="kicker">Persona · <a class="idbadge" href="#{pid}" id="{pid}">{pid}</a></div>
  <h1>{esc(p.get('name',slug))}</h1><p class="hint">{md_inline(p.get('tagline',''))}</p></div>
</div>
<p class="lead">{md_inline(p.get('one_liner',''))}</p>
<div class="metagrid">{dem}</div>
<blockquote class="quotebar">“{md_inline(p.get('quote',''))}”</blockquote>{qev}
{srcline}
<div class="two-col">{''.join(blocks)}</div>
"""
    (SITE/f'persona-{slug}.html').write_text(page(f'Persona — {p.get("name",slug)}', body, body_class='docwrap'), encoding='utf-8')

def slug_short(t):
    return re.sub(r'[^a-z0-9]+','-', t.lower()).strip('-')[:18]

# ── journeys ──
def render_journeys():
    data = []
    order = ['late-night-foodie','business-lunch']
    files = {p.stem.replace('journey-',''):p for p in WORK.glob('journey-*.json')}
    for slug in order + [s for s in files if s not in order]:
        if slug in files:
            d = load_json(files[slug].name)
            if isinstance(d, dict): data.append(d)
            elif isinstance(d, list): data.extend(d)
    for j in data: render_one_journey(j)
    print(f'  journeys: {len(data)}')
    return data

def render_one_journey(j):
    slug = j['slug']; jid = f'JNY-{slug}'
    stages = j['stages']; rows = j['rows']; cells = j.get('cells',{})
    ncol = len(stages)
    colcss = f'grid-template-columns:180px repeat({ncol}, minmax(230px,1fr));'
    # header
    parts = [f'<div class="jrow-label jstage-head" style="background:{j.get("color","var(--accent)")}">Stage →</div>']
    for st in stages:
        parts.append(f'<div class="jstage-head" style="background:{j.get("color","var(--accent)")}">{esc(st["name"])}'
                     f'<span class="sub">{esc(st.get("sub",""))}</span></div>')
    # rows
    for row in rows:
        parts.append(f'<div class="jrow-label">{esc(row["label"])}</div>')
        for st in stages:
            cell = cells.get(st['key'],{}).get(row['key'])
            cid = f'{jid}-{st["key"]}-{row["key"]}'
            if not cell:
                parts.append(f'<div class="stagecell"></div>'); continue
            if isinstance(cell,str): cell={'text':cell}
            emoji = f'<span class="emoji">{cell["emoji"]}</span> ' if cell.get('emoji') else ''
            inner = (f'<div class="cellid"><a class="idbadge" href="#{cid}">{cid}</a></div>'
                     f'<div>{emoji}{md_inline(cell.get("text",""))}</div>'
                     f'{insight_row(cell.get("insights",[]))}'
                     f'{evidence_row(cell.get("evidence",[])) if cell.get("evidence") else ""}')
            parts.append(f'<div class="stagecell" id="{cid}">{inner}</div>')
    grid = f'<div class="jgrid" style="{colcss}">' + ''.join(parts) + '</div>'
    persona = PERSONAS.get(j.get('persona'),{})
    plink = (f'<a href="persona-{j["persona"]}.html">{esc(persona.get("name",j.get("persona","")))}</a>'
             if j.get('persona') else '')
    body = f"""
<header class="srchead"><div class="kicker">Journey map · <a class="idbadge" id="{jid}" href="#{jid}">{jid}</a></div>
<h1>{esc(j.get('title',slug))}</h1>
<p class="hint">Persona: {plink} · {md_inline(j.get('subtitle',''))}</p>
<div class="trailnote">Full evidence trail live in every cell: each <span class="evref">JNY-ID</span> cell links to the <span class="evref">Insight</span> it rests on, and each insight links down to the <span class="evref">verbatim</span> quote. Hover to preview, click to jump.</div>
</header>
<div class="scrollx">{grid}</div>
"""
    (SITE/f'journey-{slug}.html').write_text(page(j.get('title',slug), body, body_class='jny-wrap'), encoding='utf-8')

# ── index / home ──
def render_index(insights, personas, journeys):
    def tiles(items): return '<div class="grid">' + ''.join(items) + '</div>'
    # The v2/v3 maps and v3 personas are rendered by build/v2 and build/v3, not here,
    # so the index just links them. Tiles are emitted unconditionally rather than
    # gated on the file existing: a build into a scratch directory has to produce the
    # same index as a build into site/, or it can't be diffed. check_links.py is what
    # catches a link with no file behind it.
    stiles = []
    for sk,meta in SOURCES.items():
        # FACT and MRKT get their own tiles under Organisational Context above.
        if sk in ('FACT','MRKT'):
            continue
        kind = meta.get('kind')
        icon = {'transcript':'🎙️','social':'📱','ticket':'🎫','pain':'⚠️','applog':'🔎',
                'factsheet':'🏷️','market':'📊'}.get(kind,'📄')
        sub = {'transcript':'Interview transcript','social':'Consumer social listening · 25 mentions',
               'ticket':'Franchisee support tickets · 15','pain':'Content & knowledge gaps · A–O','applog':'Consumer app/web search logs',
               'factsheet':'Company factsheet','market':'Market research report'}.get(kind,'')
        title = meta.get('title', sk)
        stiles.append(f'<a class="tile" href="{meta["html"]}"><h3>{icon} {esc(title)}</h3>'
                      f'<p><span class="srccode">{esc(sk)}</span> · {esc(sub)}</p></a>')
    # ── v3 (current) — ucLoops-method journey maps + real-structure personas ──
    def tile(fn, title, sub):
        return f'<a class="tile" href="{fn}"><h3>{title}</h3><p>{esc(sub)}</p></a>'
    v3maps = tiles([tile('journey-map-late-night-v3.html','🗺️ Late-Night Foodie journey',
                         'Persona: Mateo · 16-row template grid, focus/hide personas, opportunity cards with verbatim references'),
                    tile('journey-map-business-lunch-v3.html','🗺️ Business Lunch journey',
                         'Personas: Omar + Grace (multi-persona) · Focus / Remove, catering stage, verbatim references')])
    v3pers = tiles([
        tile('persona-late-night-foodie-v3.html','🌮 Mateo','Late-Night Foodie — nightlife service worker, Toronto'),
        tile('persona-omar-v3.html','💼 Omar','Business Lunch — solo financial-district professional, Toronto'),
        tile('persona-grace-v3.html','💼 Grace','Business Lunch — office manager & catering coordinator, Calgary'),
        tile('persona-everyday-20s-v3.html','🍽️ Tyler','Everyday 20-something — convenience-first eater, Vancouver'),
        tile('persona-franchisee-v3.html','🚚 Diego','Franchisee / Operator — multi-truck veteran archetype'),
    ])
    earlier = tiles(
        [f'<a class="tile" href="journey-{j["slug"]}.html"><h3>🗺️ {esc(j.get("title",j["slug"]))} <span class="cat">v1</span></h3><p>first draft</p></a>' for j in journeys]
        + [f'<a class="tile" href="{fn}"><h3>🗺️ {esc(t)} <span class="cat">v2</span></h3><p>pre-restyle</p></a>' for fn,t in [
            ('journey-map-late-night-v2.html','Late-Night Foodie'),('journey-map-business-lunch-v2.html','Business Lunch')]]
        + [f'<a class="tile" href="persona-{p["slug"]}.html"><h3>{p.get("emoji","🌮")} {esc(p.get("name",p["slug"]))} <span class="cat">v1 persona</span></h3><p>superseded</p></a>' for p in personas])
    fact_href = SOURCES.get('FACT',{}).get('html','sources/FACT.html')
    mrkt = SOURCES.get('MRKT',{})
    # Own grid class, not .grid: two tiles of very different copy length, and the
    # equal-height two-column layout is what stops the shorter one looking orphaned.
    orgtiles = ('<div class="orgcontext-grid">'
        f'<a class="tile" href="{fact_href}#brand-story"><h3>🏷️ BorderBlend Company Factsheet</h3>'
        f'<p>Brand story, vision &amp; mission, menu, positioning, and the fusion-vs-traditional question</p></a>'
        f'<a class="tile" href="{mrkt.get("html","sources/MRKT.html")}#executive-summary"><h3>📊 Canadian Mexican &amp; Fusion Street-Food Market — 2026</h3>'
        f'<p>Commissioned market research · 41 cited claims on the market BorderBlend competes in</p></a>'
        '</div>')
    body = f"""
<header class="hero">
<div class="kicker">Urbina Consulting · ucLoops — synthetic case</div>
<h1>BorderBlend — Evidence Map</h1>
<p>This is a demo of Urbina Consulting ucLoops.</p>
</header>
<div class="overview"><strong>How this was created:</strong> ucLoops is a method you can use in the AI tools of your choice (Claude, ChatGPT, Grok, etc) that lets you ingest data sources like interviews, analytics, support tickets, existing persona/journey research, and more, and output richly linked, living deliverables. Everything you see here can be (re)built to your own templates for strategy, personas, journeys, and the rest.<br/><br/>
<strong>How to use this demo:</strong> Click around the <a href="journey-map-late-night-v3.html">journey maps</a>, <a href="persona-late-night-foodie-v3.html">personas</a>, and <a href="insights.html">insights</a>, and click the <span class="evref">Show Item IDs and Provenance</span> buttons (top right). Each section will show what it draws on, linking all the way back to the exact <span class="evref">verbatim</span> lines in a transcript, dataset row, pain point, or market-report claim.<br/><br/><strong>How to have some <i>real</i> fun:</strong> You can chat live with the <a href="https://urbinaconsulting.com/ai/synthetic-users-vs-persona-simulations/">Persona Simulations</a> used to create these materials by clicking over to the <a href="https://ucloops-demo-v1.vercel.app/">interactive demo app</a>.</div>
<div class="sec-title">Organisational Context</div>
<div class="overview">
<h2>Project Overview</h2>
<p><a href="{fact_href}#brand-story"><strong>BorderBlend</strong></a> is a fast-growing Canadian food-truck brand — <strong>27 trucks, headquartered in Toronto</strong> — serving Mexican <em>fusion</em> alongside <em>traditional</em> street food, anchored by a signature smoked-brisket taco. As a challenger still deciding how hard to lean into fusion, it wants to extend its lead across discovery, loyalty, and its franchise network.</p>
<p class="ctx">This site is the output of a <strong>discover → define</strong> UX &amp; content-strategy engagement. Real customer, franchisee and market research — interviews, consumer app &amp; social data, franchisee support tickets, and a market report — is distilled into <strong>insights → personas → journey maps</strong>, with <em>every</em> claim traceable back to the exact source line. Start with the <a href="{fact_href}#brand-story">company factsheet</a>, then follow any journey down to its verbatim evidence.</p>
</div>
{orgtiles}
<div class="sec-title">Journey maps</div>{v3maps}
<div class="sec-title">Personas</div>{v3pers}
<div class="sec-title">Insights</div>
<div class="grid"><a class="tile" href="insights.html"><h3>💡 {len(insights)} insights</h3><p>Consumer, franchisee & brand/content-architecture — each grounded in verbatim evidence, filterable by persona & category.</p></a></div>
<div class="sec-title">Sources ({len(SOURCES)})</div>{tiles(stiles)}
<details style="margin-top:2rem"><summary class="sec-title" style="cursor:pointer">Earlier drafts (v1 / v2) — kept for comparison</summary>{earlier}</details>
<p class="hint" style="margin-top:2rem">Generated by <code>build/build.py</code> (+ v3 renderers in <code>build/v3/</code>) · {len(ANCHORS)} addressable anchors.</p>
"""
    (SITE/'index.html').write_text(page('BorderBlend — Evidence Map', body, body_class='docwrap'), encoding='utf-8')

def pass_b():
    render_insights()
    personas = render_personas()
    journeys = render_journeys()
    render_index(list(INSIGHTS.values()), personas, journeys)
    if WARN:
        print(f'  WARNINGS ({len(WARN)}):')
        for w in WARN[:40]: print('   -', w)

if __name__ == '__main__':
    import sys
    pass_a()
    if '--full' in sys.argv:
        pass_b()
