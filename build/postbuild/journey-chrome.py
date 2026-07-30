"""
Brings the four journey maps in line with the rest of the site.

They are the only pages with no generator — authored on `journey-map-template.html`
through the ucLoops prompt chain — so this is the one place their chrome and their
provenance behaviour can be fixed. Three things:

1. THE STICKY BAR. Replaced with `chrome.sticky_bar()`, same as every generated
   page, with the journey's own name as the page title. Their hand-written bar
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

Idempotent via the `uc-journey-chrome` marker.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chrome
import naming

MARKER = "uc-journey-chrome"
LINKS_MARKER = "uc-journey-perslinks"

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


def bar_title(s: str) -> str:
    """"Journey · Late-Night Foodie (v3)" out of the page's own <title>."""
    m = re.search(r"<title>(.*?)</title>", s, re.S)
    t = " ".join(m.group(1).split()) if m else "Journey map"
    t = re.sub(r"\s+—\s+Journey Map\s*$", "", t)
    name = t.split(" — ")[0]
    ver = re.search(r"\((v\d)\)", t)
    return f"Journey · {name}" + (f" ({ver.group(1)})" if ver else "")


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
    bar = chrome.sticky_bar(page_title=bar_title(s))
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
