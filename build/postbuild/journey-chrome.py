"""
Brings the four journey maps in line with the rest of the site.

They are the only pages with no generator — authored on `journey-map-template.html`
through the ucLoops prompt chain — so this is the one place their chrome and their
provenance behaviour can be fixed. Three things:

1. THE STICKY BAR. Replaced with `chrome.sticky_bar()`, same as every generated
   page: the way back and the provenance toggle, nothing else. Their hand-written bar
   nested the site name inside the back link, and the AI-projects viewer reads that
   link's textContent as the label for the *parent* page's toolbar — so the toolbar
   came out as "←BorderBlend Evidence Map   BorderBlend Evidence Map".

2. THE PROVENANCE TOGGLE, which did nothing on the live site. The viewer hides our
   bar and rebuilds it above the iframe; its button posts a message back, and the
   injected frame script then calls `window.toggleProv(button)` **if that function
   exists**, otherwise falls back to toggling `body.prov-hidden`. These pages
   defined `toggleItemRefs()` and key their CSS off `.journey-grid.show-refs`, so
   the fallback flipped a class nothing reads. Defining `toggleProv` fixes the
   live toolbar and leaves the in-page button working identically.

   It is declared as a plain `function toggleProv(btn)` on purpose: the frame script
   re-executes inline scripts to restore `onclick` handlers, and it finds them by
   searching script text for `function <name>`.

3. THE OPPORTUNITY REFERENCES. Each opportunity card had its own "Show references"
   button — a second, independent disclosure control that behaved differently from
   the site-wide toggle and left the two out of sync. The reference lists now follow
   `.show-refs` like every other piece of provenance, and the per-card buttons are
   removed.

   Those references point at items *in this map* (`PROB-MATE-ST01-0001` and
   friends), so clicking one now scrolls it into view and flashes it rather than
   relying on a native hash jump — the grid scrolls horizontally, and a native jump
   in a scroll container lands unpredictably. Links that leave the page are
   untouched: they already carry the same `.tip` hover previews as the rest of the
   site, and the viewer needs to see them as ordinary navigation.

   The maps' own `toggleRefs()` function is left defined and unreachable — nothing
   calls it once the buttons are gone. Deleting it would mean editing their inline
   script, which buys nothing; if you are reading it and wondering, that is why.

5. THE VIEWPORT FEEDBACK LOOP — the scrollbar that grew forever and took the
   horizontal scroll with it. Documented at VIEWPORT_CSS below; it predates this
   script.

Idempotent, via `uc-journey-chrome`, `uc-journey-perslinks`, `uc-journey-trail` and
`uc-journey-viewport`.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chrome
import naming

MARKER = "uc-journey-chrome"
LINKS_MARKER = "uc-journey-perslinks"
TRAIL_MARKER = "uc-journey-trail"
VIEWPORT_MARKER = "uc-journey-viewport"

# ── The scrollbar that grew forever ──────────────────────────────────────────
#
# Reported as: on load the vertical scrollbar grows for ~10 seconds, then there is
# no horizontal scroll. Predates this script — the version live before it ratcheted
# identically, verified by emulating the viewer's own loop (150 -> 534px in 25
# cycles, +16 each, monotonic).
#
# The cause is not the `100vh` you would suspect first. It is this:
#
#   documentElement.scrollHeight never reports less than the frame's own height,
#
# and the viewer posts `Math.max(body.scrollHeight, documentElement.scrollHeight)`
# to the parent, which sets the iframe to that **+ 16**. So for any page whose real
# content is *shorter* than its frame, docEl.scrollHeight is just the frame height
# and every cycle adds 16px, forever. Isolated in a 6-line test page: body stayed at
# 200px while docEl climbed 200 -> 216 -> 232 -> 248 in lockstep with the frame.
#
# Every other page on this site is far taller than the frame, so `body` wins the max
# and the loop settles. These maps are the exception: they are a fixed-viewport app
# (`.container{height:calc(100vh - --chrome-h)}` with both scrollbars inside that
# box), so their content is always exactly one screen — shorter than the frame, every
# time. And once the frame is taller than the parent's viewport, the container's own
# scrollbars sit below the fold, which is the missing horizontal scroll.
#
# So the fix is to stop being shorter than the frame: when embedded, let the map
# flow to its natural height (~10,000px) like every other page. The parent scrolls it
# vertically, `body.scrollHeight` wins the max, and the ratchet becomes the same
# harmless 16px of trailing whitespace every other page already has.
#
# The cost is that the horizontal scrollbar moves to the bottom of a very tall grid,
# out of reach — so this also adds a pan bar that stays put while you scroll
# horizontally, and drag-to-pan anywhere on the grid.
#
# The real fix is two lines in the plugin: measure `body.scrollHeight` rather than
# `max(..., documentElement.scrollHeight)`, and drop the `+ 16`.
VIEWPORT_EARLY = """<script>
/* uc-journey-viewport: sets the flag before first paint, hence up here. */
(function(){
  if(window.parent!==window) document.documentElement.className+=" uc-embedded";
})();
</script>
"""

VIEWPORT_CSS = """
/* ── uc-journey-viewport ──
   Embedded only: the map flows to its natural height instead of clipping itself to
   one screen. See the long comment in postbuild/journey-chrome.py for why that is
   what stops the frame growing. `html.uc-embedded` outranks the plain `.container`
   selectors, so cascade order between the postbuild patches doesn't matter. */
html.uc-embedded .container{height:auto !important}
html.uc-embedded .main-content{height:auto !important}

@media(min-width:860px){
  /* position:fixed against a viewport that is the whole frame would pin the sidebar
     to the top of a 10,000px page. In flow, as the flex item it already is, it
     stretches beside the grid — and .main-content's offset for the fixed copy goes. */
  html.uc-embedded .sidebar{position:static !important;height:auto !important}
  html.uc-embedded .main-content{margin-left:0 !important}
}

/* Pan bar: the grid's horizontal scrollbar is now at the bottom of a very tall
   element, so this is a second, reachable one. `position:sticky;left:0` inside the
   horizontal scroller is what keeps it in place while the grid pans under it. */
html.uc-embedded .uc-panbar{position:sticky;left:0;height:14px;margin:.6rem 1rem 0;
  overflow-x:auto;overflow-y:hidden;background:#f1f5f9;border-radius:7px}
html.uc-embedded .uc-panbar>div{height:1px}
html.uc-embedded .uc-panbar[hidden]{display:none}
html.uc-embedded .journey-grid{cursor:grab}
html.uc-embedded .journey-grid.uc-dragging{cursor:grabbing;user-select:none}
"""

VIEWPORT_SCRIPT = """<script>
/* uc-journey-viewport: reachable horizontal panning for the embedded layout. */
(function(){
  if(!document.documentElement.classList.contains("uc-embedded")) return;
  /* .container is the horizontal scroller — the grid is its child, not
     .main-content's, which is why an earlier version of this mirrored the wrong
     element and never showed. */
  var scroller = document.querySelector(".container");
  var main = document.querySelector(".main-content");
  var grid = document.querySelector(".journey-grid");
  if(!scroller || !main || !grid) return;

  /* A mirror of the grid's width, directly above the grid, held in place while the
     grid pans under it. */
  var bar = document.createElement("div");
  bar.className = "uc-panbar";
  var inner = document.createElement("div");
  bar.appendChild(inner);
  grid.parentNode.insertBefore(bar, grid);

  var syncing = false;
  function size(){
    /* The bar is as wide as the *visible* area and holds a spacer as wide as the
       whole grid — that is what gives it a thumb to drag. In flow mode
       .main-content stretches to the grid's width, so without this the bar would be
       3000px wide and never overflow. */
    bar.style.width = scroller.clientWidth + "px";
    inner.style.width = scroller.scrollWidth + "px";
    bar.hidden = scroller.scrollWidth <= scroller.clientWidth + 1;
  }
  bar.addEventListener("scroll", function(){
    if(syncing) return; syncing = true; scroller.scrollLeft = bar.scrollLeft; syncing = false;
  });
  scroller.addEventListener("scroll", function(){
    if(syncing) return; syncing = true; bar.scrollLeft = scroller.scrollLeft; syncing = false;
  });
  window.addEventListener("resize", size);
  if(window.ResizeObserver) new ResizeObserver(size).observe(grid);
  size();

  /* Drag anywhere on the grid. Guarded so it never eats a click on a link, a button
     or a text selection: panning only starts once the pointer has moved 5px. */
  var down = null;
  grid.addEventListener("pointerdown", function(e){
    if(e.button !== 0) return;
    if(e.target.closest("a,button,input,select,textarea")) return;
    down = {x:e.clientX, left:scroller.scrollLeft, panning:false};
  });
  window.addEventListener("pointermove", function(e){
    if(!down) return;
    var dx = e.clientX - down.x;
    if(!down.panning){
      if(Math.abs(dx) < 5) return;
      down.panning = true;
      grid.classList.add("uc-dragging");
    }
    scroller.scrollLeft = down.left - dx;
  });
  window.addEventListener("pointerup", function(){
    if(down && down.panning) grid.classList.remove("uc-dragging");
    down = null;
  });
})();
</script>
"""

CSS = """
/* ── uc-journey-chrome ── */

/* Opportunity references follow the one site-wide toggle, exactly like the
   .evidence rows on persona lines do. The per-card buttons are gone. */
.opp-refs{display:none}
.journey-grid.show-refs .opp-refs{display:block}
.refs-toggle{display:none !important}

/* Landing highlight for an in-map reference jump. Backgrounds only, so it works on
   a grid cell and on an inline badge without moving anything. */
@keyframes uc-jump-flash{0%{background:#fff3c9;box-shadow:0 0 0 3px #fde68a}100%{background:transparent;box-shadow:none}}
.uc-jump-flash{animation:uc-jump-flash 1.8s ease-out}

/* "Evidence trail" in the legend is a control, not a link out — same treatment as
   the persona pages give it. */
a.trail-toggle{border-bottom:1px dashed currentColor;cursor:pointer;color:inherit}
a.trail-toggle:hover{text-decoration:none;border-bottom-style:solid}
"""

SCRIPT = """<script>
/* uc-journey-chrome */

/* The viewer's toolbar button ends up here: the injected frame script calls
   window.toggleProv(button) when it exists. Without this the live toggle silently
   did nothing on these pages — the fallback flips body.prov-hidden, which this
   page's CSS does not read. Declared as a function statement because that script
   locates handlers by searching for "function <name>". */
function toggleProv(btn){
  var grid = document.querySelector('.journey-grid');
  if(!grid) return;
  var on = grid.classList.toggle('show-refs');
  var b = btn && btn.tagName ? btn : document.querySelector('.provtoggle');
  if(b){
    b.textContent = on ? 'Hide Item IDs & Provenance' : 'Show Item IDs & Provenance';
    b.classList.toggle('refs-visible', on);
  }
  return on;
}
/* Kept: older inline handlers and the persona controls call this name. */
function toggleItemRefs(){ return toggleProv(document.querySelector('.provtoggle')); }
/* The legend's "Evidence trail" label explains the toggle, so it is also the
   toggle — same on the persona pages. */
function ucToggleFromTrail(){ toggleProv(document.querySelector('.provtoggle')); return false; }

(function(){
  function ensureRefsShown(){
    var grid = document.querySelector('.journey-grid');
    if(grid && !grid.classList.contains('show-refs')) toggleProv(null);
  }
  function flash(el){
    el.classList.remove('uc-jump-flash');
    void el.offsetWidth;                     /* restart the animation */
    el.classList.add('uc-jump-flash');
    setTimeout(function(){ el.classList.remove('uc-jump-flash'); }, 1900);
  }
  function jump(id){
    var el = document.getElementById(id);
    if(!el) return false;
    ensureRefsShown();
    var box = el.closest('.grid-cell, .opportunity-card') || el;
    box.scrollIntoView({block:'center', inline:'center', behavior:'smooth'});
    flash(box);
    return true;
  }
  /* Capture phase, and we stop propagation on a hit: inside the viewer the frame
     script also listens on document for link clicks and would hand this off to the
     parent page as navigation. Only same-page (#) links are ours. */
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if(!a) return;
    var id = decodeURIComponent(a.getAttribute('href').slice(1));
    if(!id || !jump(id)) return;
    e.preventDefault();
    e.stopPropagation();
    if(history.replaceState) history.replaceState(null, '', '#' + id);
  }, true);

  /* Arriving with a hash (from another page, or the viewer's own hash sync). */
  function onHash(){ var h = location.hash.slice(1); if(h) setTimeout(function(){ jump(h); }, 60); }
  window.addEventListener('hashchange', onHash);
  window.addEventListener('load', onHash);
})();
</script>
"""


# Who each multi-persona map is about, in the order the legend names them. Only the
# business-lunch maps have a trail legend; the late-night ones never had one.
TRAIL_PERSONAS = {"business-lunch": (("Omar", "omar"), ("Grace", "grace"))}

# The one link that used to cover both names — v3 maps point at a v3 persona page,
# v2 maps at the v1 page.
TRAIL_OLD_LINKS = (
    '<a href="pers-omar-business-lunch-v3.html">Omar &amp; Grace’s persona (Business Lunch)</a>',
    '<a href="pers-business-lunch-v1.html">Omar &amp; Grace’s persona (Business Lunch)</a>',
)


def fix_viewport_loop(path: Path) -> str:
    """Size the map from the parent's viewport when embedded. See VIEWPORT_* above."""
    s = path.read_text(encoding="utf-8")
    if VIEWPORT_MARKER in s:
        return "skipped (already sized)"

    m = re.search(r"<body\b[^>]*>", s)
    if not m:
        return "FAILED: no <body>"
    s = s[: m.end()] + "\n" + VIEWPORT_EARLY + s[m.end():]

    i = s.rfind("</style>")
    if i == -1:
        return "FAILED: no </style>"
    s = s[:i] + VIEWPORT_CSS + s[i:]

    j = s.rfind("</body>")
    if j == -1:
        return "FAILED: no </body>"
    s = s[:j] + VIEWPORT_SCRIPT + s[j:]

    s += "\n<!-- " + VIEWPORT_MARKER + " -->\n"
    path.write_text(s, encoding="utf-8")
    return "embedded layout + pan bar added"


def fix_trail_legend(path: Path) -> str:
    """"Evidence trail", one link per person, and no stale instructions.

    Three things wrong with the legend: it said "Link trail" where the rest of the
    site says "Evidence trail", it wrapped *both* persona names in a single link to
    Omar's page, and it still told people to use the per-card "Show references"
    buttons that step 3 removes.
    """
    s = path.read_text(encoding="utf-8")
    if TRAIL_MARKER in s:
        return "skipped (already fixed)"
    if '<div class="trail-legend">' not in s:
        return "no trail legend on this map"

    # Same wording and same behaviour as the persona pages: the label explains what
    # the toggle does, so it is also the toggle.
    s = s.replace(
        "<b>Link trail:</b>",
        '<a class="trail-toggle" href="#" onclick="return ucToggleFromTrail()">'
        "<b>Evidence trail</b></a>:", 1)

    journey = "business-lunch" if "business-lunch" in path.name else ""
    people = TRAIL_PERSONAS.get(journey)
    old = next((o for o in TRAIL_OLD_LINKS if o in s), None)
    if people and old:
        v1 = "-v2.html" in path.name
        links = " &amp; ".join(
            f'<a href="{naming.persona_v1_page(journey) if v1 else naming.persona_page(person, journey)}">{name}</a>'
            for name, person in people)
        s = s.replace(old, f"{links}’s personas", 1)

    s = s.replace(
        "each opportunity’s <em>Show references</em> opens the persona lines, "
        "insights and source verbatims it draws on",
        "each opportunity lists the persona lines, insights and source verbatims it "
        "draws on — click one to jump to it in the map", 1)

    s += "\n<!-- " + TRAIL_MARKER + " -->\n"
    path.write_text(s, encoding="utf-8")
    return "trail legend fixed"


def patch(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return "skipped (already patched)"

    # 1. Sticky bar. Keep the journey's own id badge, which only this page carries.
    m = re.search(r'<div class="stickybar">.*?</div>\s*(?=<)', s, re.S)
    if not m:
        return "FAILED: no stickybar"
    old = m.group(0)
    jid = re.search(r'<span class="journey-id">[^<]*</span>', old)
    bar = chrome.sticky_bar()
    if jid:
        bar = bar.replace('<button class="provtoggle"', jid.group(0) + '<button class="provtoggle"')
    s = s[: m.start()] + bar + s[m.end():]

    # 2. Per-card disclosure buttons out. The CSS hides them too, belt and braces,
    #    in case a variant spells the button differently.
    s, n_btn = re.subn(r'<button class="refs-toggle"[^>]*>.*?</button>\s*', "", s, flags=re.S)

    # 3. CSS + script.
    i = s.rfind("</style>")
    if i == -1:
        return "FAILED: no </style>"
    s = s[:i] + CSS + s[i:]

    j = s.rfind("</body>")
    if j == -1:
        return "FAILED: no </body>"
    s = s[:j] + SCRIPT + s[j:]

    s += f"\n<!-- {MARKER} -->\n"
    path.write_text(s, encoding="utf-8")
    return f"patched ({n_btn} per-card buttons removed)"


def relink_personas(path: Path) -> str:
    """Point the sidebar cards and cell links at the renamed persona pages.

    These maps carry ~145 persona hrefs each and no generator, so the rename has to
    reach them here. Must run before persona-sim-links.py, which finds a card's agent
    by looking for a known persona filename inside the card.
    """
    s = path.read_text(encoding="utf-8")
    if LINKS_MARKER in s:
        return "skipped (already relinked)"
    n = 0
    for old, new in naming.LEGACY.items():
        c = s.count(f'href="{old}')
        if c:
            s = s.replace(f'href="{old}', f'href="{new}')
            n += c
    s += f"\n<!-- {LINKS_MARKER} -->\n"
    path.write_text(s, encoding="utf-8")
    return f"relinked ({n} persona hrefs)"


base = Path(sys.argv[1])
for f in sorted(base.glob("journey-map-*.html")):
    print(f"  {f.name:42s} {patch(f)}")
    print(f"  {'':42s} {relink_personas(f)}")
    print(f"  {'':42s} {fix_trail_legend(f)}")
    print(f"  {'':42s} {fix_viewport_loop(f)}")
