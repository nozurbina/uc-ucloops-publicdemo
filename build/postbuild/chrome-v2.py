"""
Rebuilds the top chrome (promo banner + sticky bar) on the BorderBlend pages.

The white band came from the two bars being independently `position:fixed` and
agreeing on a measured `--banner-h`: the sizing script sat *between* them in the
document, so `querySelector('.stickybar')` was null on its first run and the
offsets disagreed until `load` fired. Rather than patch the measurement, this
collapses both bars into ONE fixed wrapper (`.uc-chrome`) with the children in
normal flow inside it. One element to position, one height to measure, and no
seam between them where background could show through.

Also adds:
  - a dismiss button, remembered across pages via localStorage
  - a narrow-screen layout: no logo, copy stacked above the button

Idempotent via the `uc-chrome-v2` marker.
"""

import re
import sys
from pathlib import Path

MARKER = "uc-chrome-v2"
NARROW = 859  # matches the mobile drawer breakpoint

CSS = """
/* ── uc-chrome-v2: banner + sticky bar as one sticky wrapper ──
   Previously both bars were position:fixed independently, offset from each
   other by a JS-measured --banner-h, with body padding-top reserving room for
   them. Three things had to agree and often didn't — hence the white seam.

   Sticky instead of fixed, deliberately. These pages are normally viewed inside
   the AI-projects viewer, which hides our .stickybar (it rebuilds it in the
   parent page above the iframe) and auto-sizes the iframe to content height.
   With no independent viewport, `fixed` buys nothing and the reserved padding
   becomes a visible empty band. Sticky sits in normal flow — nothing to reserve,
   nothing to measure — and still sticks when the page IS viewed directly. ── */
.uc-chrome{position:sticky;top:0;z-index:300}
.uc-chrome .promo-banner{position:relative !important;top:auto !important;left:auto !important;right:auto !important;z-index:auto !important}
.uc-chrome .stickybar{position:static !important;top:auto !important;left:auto !important;right:auto !important;z-index:auto !important}
/* The chrome is in flow now, so any reserved space is a gap. */
body{padding-top:0 !important}

/* Dismiss. Applied to <html> by a parser-blocking script before the banner is
   parsed, so a previously-dismissed banner never flashes into view. */
.uc-promo-hidden .promo-banner{display:none !important}
.promo-close{position:absolute;top:.45rem;right:.55rem;width:26px;height:26px;padding:0;
  background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.35);border-radius:6px;
  color:#fff;font-size:.8rem;line-height:1;cursor:pointer;font-family:inherit;
  display:flex;align-items:center;justify-content:center}
.promo-close:hover{background:rgba(255,255,255,.26)}

@media(max-width:NARROWpx){
  /* The logo is the first thing to sacrifice — it carries no information the
     copy doesn't already, and it costs a whole row once the text wraps. */
  .uc-chrome .promo-banner .banner-logo{display:none}
  .uc-chrome .promo-banner .banner-inner{flex-direction:column;align-items:stretch;gap:.55rem}
  .uc-chrome .promo-banner .banner-line{font-size:.92rem}
  .uc-chrome .promo-banner .promo-btn{align-self:flex-start}
  .promo-close{top:.3rem;right:.35rem}
  .uc-chrome .promo-banner{padding-right:2.4rem}

  /* The stage grid is several times wider than a phone. The drawer patch added
     .container{overflow-x:hidden} so the off-canvas sidebar couldn't create a
     page-level scrollbar — but that also clipped the grid, making every stage
     after the first unreachable. Give the grid its own horizontal scroll. */
  .main-content{overflow-x:auto !important;-webkit-overflow-scrolling:touch}
}
""".replace("NARROW", str(NARROW))

# Runs during parsing, before <div class="promo-banner"> exists, so the hide is
# applied by the time the banner would first paint.
EARLY = (
    '<script>try{if(localStorage.getItem("ucPromoDismissed")==="1")'
    'document.documentElement.className+=" uc-promo-hidden";}catch(e){}</script>\n'
)

CLOSE_BTN = (
    '<button class="promo-close" type="button" onclick="ucCloseBanner()" '
    'aria-label="Dismiss this notice" title="Dismiss">&#10005;</button>'
)

# Placed at the end of <body> so the whole chrome exists before it measures.
SCRIPT = """<script>
/* uc-chrome-v2 sizing. The chrome is sticky and therefore in normal flow, so
   nothing needs padding reserved for it. --chrome-h is still published because
   the journey-map container sizes itself against it. */
(function(){
  var KEY="ucPromoDismissed";
  function fit(){
    var c=document.querySelector(".uc-chrome");
    var h=c?c.offsetHeight:0;
    document.documentElement.style.setProperty("--chrome-h",h+"px");
  }
  window.ucFitChrome=fit;
  window.ucCloseBanner=function(){
    document.documentElement.classList.add("uc-promo-hidden");
    try{localStorage.setItem(KEY,"1");}catch(e){}
    fit();
  };
  fit();
  window.addEventListener("load",fit);
  window.addEventListener("resize",fit);
  /* The banner's height depends on how the copy wraps, which web fonts change
     after first paint. Without this the reserved space can be stale. */
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
})();
</script>
"""


def match_div(s: str, start: int):
    """Index just past the </div> that closes the <div> beginning at `start`.

    Counts nested divs rather than guessing at a closing pattern, because the
    banner and the sticky bar nest to different depths and the sticky bar isn't
    always followed by a newline.
    """
    depth = 0
    i = start
    while i < len(s):
        nxt_open = s.find("<div", i)
        nxt_close = s.find("</div>", i)
        if nxt_close == -1:
            return None
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            i = nxt_close + 6
            if depth == 0:
                return i
    return None


def patch(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return "skipped (already patched)"

    # 1. CSS before the final </style>
    i = s.rfind("</style>")
    if i == -1:
        return "FAILED: no </style>"
    s = s[:i] + CSS + s[i:]

    # 2. Early dismiss check, immediately after the opening <body ...> tag.
    #    These pages use several body classes (srcpage, docwrap, prov-hidden…),
    #    so match the tag rather than a literal "<body>".
    m = re.search(r"<body\b[^>]*>", s)
    if not m:
        return "FAILED: no <body>"
    s = s[: m.end()] + "\n" + EARLY + s[m.end() :]

    # 3. Drop the old sizing script. Two variants exist: `fitChrome` on the
    #    journey maps (measured banner + bar, but sat before the bar existed in
    #    the document) and `fitBanner` everywhere else (measured only the banner
    #    and never set --banner-h, which the bar's offset depended on).
    start = -1
    for probe in (
        "<script>(function(){function fitChrome()",
        "<script>(function(){function fitBanner()",
    ):
        start = s.find(probe)
        if start != -1:
            break
    if start == -1:
        return "FAILED: no old sizing script found"
    end = s.find("</script>", start)
    if end == -1:
        return "FAILED: unterminated sizing script"
    s = s[:start] + s[end + len("</script>") :]

    # 4. Wrap the banner and (when present) the sticky bar in one wrapper.
    #
    #    DOM order is NOT consistent across the set: the journey maps and
    #    persona pages put the banner first, the sources and insights pages put
    #    the sticky bar first. Extract both by matching their divs, then always
    #    emit banner-then-bar so every page reads the same way.
    b0 = s.find('<div class="promo-banner">')
    if b0 == -1:
        return "FAILED: no promo-banner"
    b1 = match_div(s, b0)
    if b1 is None:
        return "FAILED: unterminated banner"
    banner = s[b0:b1]

    s0 = s.find('<div class="stickybar">')
    if s0 != -1:
        s1 = match_div(s, s0)
        if s1 is None:
            return "FAILED: unterminated stickybar"
        bar = s[s0:s1]
    else:
        s1 = None
        bar = ""

    # Close button goes inside .promo-banner, which is now position:relative.
    anchor = '<div class="banner-inner">'
    if anchor not in banner:
        return "FAILED: no banner-inner"
    banner = banner.replace(anchor, CLOSE_BTN + anchor, 1)

    wrapper = '<div class="uc-chrome">' + banner + bar + "</div>\n"

    # Remove both originals, highest offset first so the earlier index stays
    # valid, then insert the wrapper where the first of them used to be.
    spans = [(b0, b1)] + ([(s0, s1)] if s1 is not None else [])
    insert_at = min(a for a, _ in spans)
    for a, b in sorted(spans, reverse=True):
        s = s[:a] + s[b:]
    s = s[:insert_at] + wrapper + s[insert_at:]

    # 5. Sizing script at the end of body
    j = s.rfind("</body>")
    if j == -1:
        return "FAILED: no </body>"
    s = s[:j] + SCRIPT + s[j:]

    path.write_text(s, encoding="utf-8")
    return "patched"


base = Path(sys.argv[1])
files = sorted(base.glob("*.html")) + sorted((base / "sources").glob("*.html"))
counts = {}
for f in files:
    r = patch(f)
    counts[r] = counts.get(r, 0) + 1
    if not r.startswith(("patched", "skipped")):
        print(f"  {f.name:42s} {r}")
for k, v in sorted(counts.items()):
    print(f"{k}: {v}")
