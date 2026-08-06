"""
Hideable rows + combinable "Views" for the two v3 journey maps.

(The v2 maps are kept as progression artifacts and deliberately don't get this —
only `journey-map-*-v3.html` is patched.)

Sixteen rows is more map than any one reader needs at once. Every row header is a
control: click (or Enter/Space) removes the row from the grid entirely. What's
hidden doesn't waste space as a blank strip — it moves up into a chips bar above
the map, coloured like its row; clicking a chip restores it. The bar only exists
while something is hidden, so the feature has no standing footprint.

A "Views" button opens a dropdown of checkboxes, one per discipline (Empathy,
Content strategy, UX design, Marketing & growth, Data & measurement,
Strategy/exec). Ticked views combine — the map shows the union of the rows any
ticked discipline needs — so "Strategy + Data" is just two ticks. Rules:

- The Goals row (brand + persona goals) is never hidden by a view; it is the
  frame everything else hangs off. It can still be hidden manually.
- Unticking every box (or "Show all rows") restores the full map.
- Changing views recomputes visibility from scratch, discarding manual tweaks;
  manual hides/restores on top of a view combination don't touch the checkboxes.

PLACEMENT — the part that is easy to get wrong. The button must live in the layer
that never scrolls away, and that layer is different in the two worlds:

- Standalone: the button sits in our own `.stickybar`, styled like the provenance
  toggle beside it. The sticky chrome never scrolls off, so neither does it.
  It must NOT carry the `provtoggle` class: the viewer copies the first
  `.provtoggle`'s textContent as its toolbar toggle label, and `toggleProv`'s
  fallback path targets that class too.
- Embedded: the viewer hides our sticky bar entirely and rebuilds back-link +
  title + prov-toggle in the *parent* toolbar, so the in-bar button is invisible
  there. The parent is same-origin (the pan bar already reads it), so the init
  injects a matching orange button into the parent toolbar itself, next to its
  prov toggle. The viewer rebuilds that toolbar on in-frame navigation, so a
  MutationObserver puts the button back when it vanishes. The injected button
  deliberately does NOT use the plugin's `__toggle` class — the plugin (and our
  tests) select by it.
- The dropdown panel always renders inside our document. Embedded, it is
  re-parented to <body> and pinned just under the parent's sticky toolbar at the
  top of the visible band (computed from the parent's scroll state, like the pan
  bar — `position:fixed` pins to the whole frame in an auto-height iframe, not
  the screen), and follows while open via a cheap interval.

Why a hidden row's cells can leave the grid: the map is one CSS grid filled by
auto-placement, so hiding *some* of a row's items would slide every later item
left and shear the table — but hiding the whole contiguous run (header plus every
stage cell) removes a complete grid row and auto-placement stays aligned.

The chips bar is sticky against whichever ancestor actually scrolls sideways and
JS-sized to that scrollport (`ucPlaceRowbar`): `.main-content` is as wide as the
grid (~2200px — a flex item with `min-width:auto`, propped open by the grid's
min-content width), so a width:auto bar would never wrap its chips and would pan
away with the grid.

Two integrations with the existing patches:

- `ucJumpTo` is wrapped (on top of journey-chrome.py's own wrapper, which reveals
  provenance) so an evidence jump whose target sits in a hidden row restores the
  row before scrolling. A hidden landing site would break the evidence chain.
- journey-chrome's drag-to-pan can *start* on a row header, and the browser still
  fires a click at pointerup — so a hide only counts if the pointer moved less
  than the pan threshold.

Insert-only (anchored on </style>, </body>, `<button class="provtoggle"` and
`<div class="grid-container">`), marker-guarded, idempotent. Must run after
journey-chrome.py, which emits the stickybar the button anchors on. The init is
additionally guarded at runtime (`window.ucRowCollapse`) because the viewer's
frame script re-executes inline scripts. Chip colours are read from each row
header's computed style at runtime, so no colour table is duplicated here.
"""

import sys
from pathlib import Path

MARKER = "uc-row-collapse"

CSS = """
/* ── uc-row-collapse: hideable rows, restore chips, and the Views dropdown. ── */
.row-header{cursor:pointer;user-select:none}
.row-header:hover{filter:brightness(.97)}
.row-header .uc-row-hide{margin-left:auto;align-self:flex-start;flex:0 0 auto;
  font-size:.66rem;line-height:1.4rem;opacity:.35;transition:opacity .15s}
.row-header:hover .uc-row-hide{opacity:.85}
/* A hidden row leaves the grid entirely. Safe only because the whole contiguous
   run — header plus every stage cell — goes together; auto-placement would shear
   every row below if just some of a row's items were removed. */
.row-header.uc-row-hidden,.grid-cell.uc-row-hidden{display:none}

/* Views button, in the sticky bar next to the provenance toggle and dressed like
   it (see supplement.css .provtoggle — same orange, same shape). Not the
   provtoggle class itself: the viewer reads that class's textContent for its
   toolbar label, and toggleProv's fallback targets it. */
.uc-views-wrap{position:relative;flex-shrink:0;margin-right:.55rem}
.uc-views-btn{background:#f59e0b;color:#2c3e50;border:none;border-radius:6px;
  padding:.32rem .7rem;font-size:.74rem;font-weight:700;cursor:pointer;margin:0;
  white-space:nowrap;font-family:inherit}
.uc-views-btn:hover{background:#e08e1e}

.uc-lens-panel{position:absolute;top:calc(100% + 10px);right:0;z-index:520;
  background:#fff;border:1px solid #d6dde5;border-radius:10px;
  box-shadow:0 8px 24px rgba(0,0,0,.18);padding:.7rem .8rem;width:248px;
  text-align:left;font-size:.78rem;font-weight:400}
/* Embedded: body-attached, pinned under the parent's toolbar by ucFloatPanel. */
.uc-lens-panel.uc-lens-float{right:16px;left:auto}
.uc-lens-panel[hidden]{display:none}
.uc-lens-panel label{display:flex;align-items:center;gap:.45rem;padding:.26rem 0;
  cursor:pointer;font-weight:600;color:#2c3e50;font-size:.78rem}
.uc-lens-hint{font-size:.68rem;line-height:1.45;color:#64748b;margin:0 0 .5rem}
.uc-lens-clear{margin-top:.5rem;width:100%;background:#eef2f6;border:1px solid #d6dde5;
  border-radius:8px;padding:.35rem .6rem;font-family:inherit;font-size:.72rem;
  font-weight:700;cursor:pointer;color:#2c3e50}
.uc-lens-clear:hover{background:#e2e8f0}

/* The chips bar above the grid: only exists while rows are hidden. Sticky and
   JS-sized because .main-content is as wide as the grid. */
.uc-hiddenrows{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;
  margin:1rem 1rem 0;padding:.4rem .6rem;background:#fff;border-radius:10px;
  box-shadow:0 1px 4px rgba(0,0,0,.08);font-size:.78rem;position:sticky;z-index:60;
  box-sizing:border-box;max-width:calc(100vw - 2rem)}
.uc-hiddenrows[hidden]{display:none}
.uc-hidden-lbl{color:#64748b;font-weight:700;white-space:nowrap}
.uc-chip{display:inline-flex;align-items:center;gap:.35rem;border:1px solid #d6dde5;
  border-left-width:4px;border-radius:999px;background:#f8fafc;color:#2c3e50;
  padding:.2rem .6rem;font-family:inherit;font-size:.72rem;font-weight:600;
  cursor:pointer;white-space:nowrap}
.uc-chip:hover{background:#eef2f6}
.uc-chip .uc-chip-plus{opacity:.55;font-size:.66rem}
"""

# Inserted into the sticky bar, immediately before the provenance toggle.
VIEWS = """<span class="uc-views-wrap">
<button class="uc-views-btn" type="button" onclick="ucToggleLensPanel()" aria-haspopup="true" aria-expanded="false">Views &#9662;</button>
<div class="uc-lens-panel" hidden>
<p class="uc-lens-hint">Tick views to combine them &mdash; the map shows every row any
ticked view needs, and Goals always stays. Changing views resets individual row
choices; untick everything for the full map.</p>
<label><input type="checkbox" data-lens="empathy" onchange="ucLensChange()"> &#128155; Empathy</label>
<label><input type="checkbox" data-lens="content" onchange="ucLensChange()"> &#128221; Content strategy</label>
<label><input type="checkbox" data-lens="ux" onchange="ucLensChange()"> &#129517; UX design</label>
<label><input type="checkbox" data-lens="marketing" onchange="ucLensChange()"> &#128200; Marketing &amp; growth</label>
<label><input type="checkbox" data-lens="data" onchange="ucLensChange()"> &#128202; Data &amp; measurement</label>
<label><input type="checkbox" data-lens="strategy" onchange="ucLensChange()"> &#9823;&#65039; Strategy / exec</label>
<button class="uc-lens-clear" type="button" onclick="ucLensClear()">Show all rows</button>
</div>
</span>
"""

# Inserted immediately before <div class="grid-container">.
CHIPS = """<div class="uc-hiddenrows" hidden>
<span class="uc-hidden-lbl">Hidden rows &mdash; click to restore:</span>
<span class="uc-chip-list"></span>
</div>
"""

JS = """<script>
/* uc-row-collapse */
var UC_ROW_PRESETS = {
  empathy:   ["narrative-row", "sentiment-row", "quote-row", "questions-row"],
  content:   ["channels-row", "content-assets-row", "cta-row", "questions-row",
              "entry-signals-row", "opportunities-row"],
  ux:        ["tasks-row", "problems-row", "alternate-paths-row", "questions-row",
              "entry-signals-row", "transitions-row", "opportunities-row"],
  marketing: ["channels-row", "entry-signals-row", "transitions-row", "cta-row",
              "opportunities-row"],
  data:      ["data-generated-row", "data-used-row", "entry-signals-row", "transitions-row"],
  strategy:  ["goals-row", "problems-row", "opportunities-row", "sentiment-row"]
};

function ucRowClass(el){
  var cls = null;
  el.classList.forEach(function(c){
    if(c !== "row-header" && c !== "grid-cell" && c !== "uc-row-hidden" && /-row$/.test(c)) cls = c;
  });
  return cls;
}

function ucSetRow(cls, show){
  document.querySelectorAll(".row-header." + cls + ", .grid-cell." + cls).forEach(function(el){
    el.classList.toggle("uc-row-hidden", !show);
  });
}

function ucSyncChips(){
  var list = document.querySelector(".uc-chip-list");
  var bar = document.querySelector(".uc-hiddenrows");
  if(!list || !bar) return;
  list.textContent = "";
  var hidden = document.querySelectorAll(".row-header.uc-row-hidden");
  bar.hidden = hidden.length === 0;
  hidden.forEach(function(h){
    var cls = ucRowClass(h);
    if(!cls) return;
    var chip = document.createElement("button");
    chip.type = "button";
    chip.className = "uc-chip";
    var icon = h.querySelector(".row-icon");
    var label = "";
    h.childNodes.forEach(function(n){ if(n.nodeType === 3) label += n.textContent; });
    label = label.replace(/\\s+/g, " ").trim();
    var ic = document.createElement("span");
    ic.textContent = icon ? icon.textContent : "";
    var tx = document.createElement("span");
    tx.textContent = label;
    var plus = document.createElement("span");
    plus.className = "uc-chip-plus";
    plus.textContent = "\\uFF0B";
    chip.appendChild(ic); chip.appendChild(tx); chip.appendChild(plus);
    chip.title = "Show the " + label + " row again";
    /* Row accent colour straight off the header, so no colour table lives here.
       Computed style resolves fine on a display:none element. */
    try{ chip.style.borderLeftColor = getComputedStyle(h).borderLeftColor; }catch(e){}
    chip.addEventListener("click", function(){ ucShowRow(cls); });
    list.appendChild(chip);
  });
}

function ucShowRow(cls){
  function apply(){ ucSetRow(cls, true); ucSyncChips(); }
  if(window.ucKeepPlace) ucKeepPlace(apply); else apply();
}

function ucHideRow(cls){
  function apply(){ ucSetRow(cls, false); ucSyncChips(); }
  if(window.ucKeepPlace) ucKeepPlace(apply); else apply();
}

function ucLensChange(){
  var keep = [];
  document.querySelectorAll(".uc-lens-panel input[data-lens]:checked").forEach(function(cb){
    keep = keep.concat(UC_ROW_PRESETS[cb.getAttribute("data-lens")] || []);
  });
  function apply(){
    document.querySelectorAll(".row-header[data-uc-collapsible]").forEach(function(h){
      var cls = ucRowClass(h);
      if(!cls) return;
      /* Goals is the frame the rest hangs off: no view ever hides it. */
      ucSetRow(cls, keep.length === 0 || cls === "goals-row" || keep.indexOf(cls) !== -1);
    });
    ucSyncChips();
  }
  if(window.ucKeepPlace) ucKeepPlace(apply); else apply();
}

function ucLensClear(){
  document.querySelectorAll(".uc-lens-panel input[data-lens]").forEach(function(cb){
    cb.checked = false;
  });
  ucLensChange();
}

function ucToggleLensPanel(){
  var p = document.querySelector(".uc-lens-panel");
  if(!p) return;
  p.hidden = !p.hidden;
  document.querySelectorAll(".uc-views-btn").forEach(function(b){
    b.setAttribute("aria-expanded", p.hidden ? "false" : "true");
  });
  if(!p.hidden) ucFloatPanel();
}

/* Embedded, the sticky bar (and the in-bar button) is hidden and the panel's
   anchor is a button in the PARENT toolbar — so the panel re-parents to <body>
   and pins just under that toolbar, at the top of the visible band of the frame.
   position:fixed is no use here: inside an auto-height iframe it pins to the
   whole frame, not the screen (same story as the pan bar). */
function ucFloatPanel(){
  var p = document.querySelector(".uc-lens-panel");
  if(!p || !document.documentElement.classList.contains("uc-embedded")) return;
  try{
    var pwin = window.parent;
    var fr = pwin.document.getElementById("ai-projects-frame-content");
    if(!fr || fr.contentWindow !== window) return;
    if(p.parentNode !== document.body){
      p.classList.add("uc-lens-float");
      document.body.appendChild(p);
    }
    var tb = pwin.document.querySelector(".ai-projects-project-toolbar");
    var visTop = Math.max(0, -fr.getBoundingClientRect().top);
    p.style.top = Math.round(visTop + (tb ? tb.offsetHeight : 0) + 12) + "px";
  }catch(e){}
}

/* The viewer rebuilds only back-link + title + prov-toggle in its toolbar, so the
   in-bar Views button is invisible embedded. The parent is same-origin: put a
   matching button into that toolbar directly, and put it back whenever the
   viewer rebuilds the bar. Deliberately NOT the plugin's __toggle class — the
   plugin and the tests select by it. */
function ucMountToolbarViews(){
  if(!document.documentElement.classList.contains("uc-embedded")) return;
  try{
    var pwin = window.parent;
    var fr = pwin.document.getElementById("ai-projects-frame-content");
    if(!fr || fr.contentWindow !== window) return;
    var tb = pwin.document.querySelector(".ai-projects-project-toolbar");
    if(!tb || tb.querySelector(".uc-views-toolbar-btn")) return;
    var b = pwin.document.createElement("button");
    b.type = "button";
    b.className = "uc-views-toolbar-btn";
    b.textContent = "Views \\u25BE";
    b.style.cssText = "margin-left:auto;background:#f59e0b;color:#2c3e50;border:none;" +
      "border-radius:6px;padding:.32rem .7rem;font-size:.74rem;font-weight:700;" +
      "cursor:pointer;white-space:nowrap;font-family:inherit";
    var ref = tb.querySelector(".ai-projects-project-toolbar__toggle");
    if(ref){ ref.style.marginLeft = "10px"; tb.insertBefore(b, ref); }
    else tb.appendChild(b);
    b.addEventListener("click", function(){ ucToggleLensPanel(); });
    if(pwin.MutationObserver && !window.ucViewsTbObserver){
      window.ucViewsTbObserver = new pwin.MutationObserver(function(){ ucMountToolbarViews(); });
      window.ucViewsTbObserver.observe(tb, {childList: true});
    }
  }catch(e){}
}

/* Pin the chips bar to the visible slice of the map. Mirrors the pan bar: find
   who actually scrolls sideways, then place against that scrollport, in its
   content coordinates — holds in the app layout (fixed sidebar + margin) and the
   embedded flow layout (static sidebar) alike. */
function ucPlaceRowbar(){
  var chips = document.querySelector(".uc-hiddenrows");
  var mc = document.querySelector(".main-content");
  var grid = document.querySelector(".journey-grid");
  if(!chips || !mc || !grid) return;
  var sc = grid.parentElement;
  while(sc && sc !== document.documentElement && sc.scrollWidth <= sc.clientWidth + 1)
    sc = sc.parentElement;
  if(!sc || sc === document.documentElement){
    chips.style.left = ""; chips.style.width = "";
    return;
  }
  var offset = mc.getBoundingClientRect().left - sc.getBoundingClientRect().left + sc.scrollLeft;
  chips.style.left = Math.round(offset + 16) + "px";
  chips.style.width = Math.round(sc.clientWidth - offset - 32) + "px";
}

(function(){
  if(window.ucRowCollapse) return;   /* the viewer re-executes inline scripts */
  window.ucRowCollapse = true;

  var downAt = null;
  document.querySelectorAll(".row-header").forEach(function(h){
    if(!ucRowClass(h) || h.dataset.ucCollapsible) return;
    h.dataset.ucCollapsible = "1";
    h.setAttribute("role", "button");
    h.setAttribute("tabindex", "0");
    h.title = "Hide this row (restore it from the bar above the map)";
    var x = document.createElement("span");
    x.className = "uc-row-hide";
    x.textContent = "\\u2715";
    h.appendChild(x);
    h.addEventListener("pointerdown", function(e){ downAt = {x: e.clientX, y: e.clientY}; });
    h.addEventListener("click", function(e){
      /* Same 5px threshold journey-chrome's pan uses: a pan is not a hide. */
      if(downAt && (Math.abs(e.clientX - downAt.x) > 5 || Math.abs(e.clientY - downAt.y) > 5)) return;
      ucHideRow(ucRowClass(h));
    });
    h.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){ e.preventDefault(); ucHideRow(ucRowClass(h)); }
    });
  });

  /* The Views panel closes on an outside click or Escape, like any dropdown.
     (A click on the parent-toolbar button never reaches this document, so it
     cannot fight the toggle.) */
  document.addEventListener("click", function(e){
    var p = document.querySelector(".uc-lens-panel");
    if(!p || p.hidden) return;
    if(e.target && e.target.closest &&
       e.target.closest(".uc-views-wrap, .uc-lens-panel")) return;
    ucToggleLensPanel();
  });
  document.addEventListener("keydown", function(e){
    var p = document.querySelector(".uc-lens-panel");
    if(e.key === "Escape" && p && !p.hidden) ucToggleLensPanel();
  });

  window.addEventListener("resize", ucPlaceRowbar);
  window.addEventListener("load", function(){ ucPlaceRowbar(); ucMountToolbarViews(); });
  ucPlaceRowbar();
  /* The parent toolbar may not exist yet at parse time. */
  ucMountToolbarViews();
  setTimeout(ucMountToolbarViews, 1000);
  setTimeout(ucMountToolbarViews, 3000);
  /* Keep the floating panel under the toolbar while it is open. */
  if(document.documentElement.classList.contains("uc-embedded"))
    setInterval(function(){
      var p = document.querySelector(".uc-lens-panel");
      if(p && !p.hidden) ucFloatPanel();
    }, 250);

  /* An evidence jump must never land in a hidden row. journey-chrome already
     wraps ucJumpTo to reveal provenance first; this wraps that. */
  var jump = window.ucJumpTo;
  if(jump) window.ucJumpTo = function(id){
    var el = document.getElementById(id);
    var cell = el && el.closest ? el.closest(".grid-cell.uc-row-hidden") : null;
    if(cell){
      var cls = ucRowClass(cell);
      if(cls) ucShowRow(cls);
    }
    return jump(id);
  };
})();
</script>
"""


def patch(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return "skipped (already patched)"

    bar_anchor = '<button class="provtoggle"'
    if s.count(bar_anchor) != 1:
        return "FAILED: provtoggle anchor not unique (run journey-chrome.py first)"
    s = s.replace(bar_anchor, VIEWS + bar_anchor, 1)

    anchor = '<div class="grid-container">'
    if s.count(anchor) != 1:
        return "FAILED: grid-container anchor not unique"
    s = s.replace(anchor, CHIPS + anchor, 1)

    i = s.rfind("</style>")
    if i == -1:
        return "FAILED: no </style>"
    s = s[:i] + CSS + s[i:]

    j = s.rfind("</body>")
    if j == -1:
        return "FAILED: no </body>"
    s = s[:j] + JS + s[j:]

    path.write_text(s, encoding="utf-8")
    return "patched"


base = Path(sys.argv[1])
for name in sorted(base.glob("journey-map-*-v3.html")):
    print(f"{name.name:42s} {patch(name)}")
