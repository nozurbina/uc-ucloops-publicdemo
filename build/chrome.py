# -*- coding: utf-8 -*-
"""
The top chrome shared by every generated page: promo banner + sticky bar, wrapped
in one sticky container, plus the two scripts that size it.

This used to live in `postbuild/chrome-v2.py` and `postbuild/chrome-v3.py`, which
*transformed* markup `build.py` had already emitted. That made the site
un-rebuildable: the banner itself was never in `build.py` at all, so chrome-v2 had
nothing to find and a fresh build came out ~17KB per page short. Emitting the final
markup here instead means `build.py --full` reproduces the published site, and the
CSS lives in `assets/chrome.css`, composed in by styles.py.

Three things here are load-bearing and easy to undo by accident:

  * **Sticky, not fixed.** Published pages are viewed inside the AI-projects
    viewer, which hides our `.stickybar` (it rebuilds it in the parent page) and
    auto-sizes the iframe to content height. With no independent viewport `fixed`
    buys nothing, and the padding reserved for it becomes a visible empty band.
  * **One wrapper, not two bars.** The two bars were independently positioned and
    offset by a JS-measured `--banner-h`; three values had to agree and often
    didn't, which showed as a white seam. One element, one height.
  * **The logo is a base64 data URI.** The host serves `.svg` as
    `application/octet-stream` and browsers refuse to render that in an `<img>`.
    A data URI carries its own type and cannot be mis-served. Deliberately not
    inlined as markup: the file carries `<style>.st0{fill:#fff}</style>` and
    `id="Layer_2"`, which inlining would leak into every page.

The full-bleed maths and the `--half-vw` trap are documented in `assets/chrome.css`
where the rules are.
"""
import base64
import html
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
LOGO = HERE / "assets" / "2023-uc-logo-outline.svg"

# The sticky bar's back link, and the only thing in that bar besides the toggle.
# Kept short deliberately: the AI-projects viewer reads this element's textContent
# as the label for the *parent* page's toolbar, and it has to survive a phone-width
# bar. The arrow is part of the text so the viewer's copy keeps it too.
BACK_LABEL = "← Evidence Map"

# Site name, for the index's own <title> and the archive pages that have no better
# label of their own.
SITE_TITLE = "BorderBlend Evidence Map"

PROMO_URL = "https://urbinaconsulting.com/shares/ucloops/cohort-journeys-sept-2026/"

# Marks a page as carrying the final chrome. Emitted at the very end of the file.
MARKER = "<!-- uc-chrome -->"

# Runs during parsing, before the banner exists, so a banner dismissed on an
# earlier page never flashes into view on this one. sessionStorage, not
# localStorage: dismissal should hold for the rest of this visit (across page
# navigations in the same tab) but reappear on the next visit, not vanish forever.
EARLY = (
    '<script>try{if(sessionStorage.getItem("ucPromoDismissed")==="1")'
    'document.documentElement.className+=" uc-promo-hidden";}catch(e){}</script>\n'
)

BANNER_LINES = (
    "This is a generated example built with Urbina's ucLoops AI methodology.",
    "It's even better when used with <b>real research sources!</b>",
    'Learn how to use it yourself on our <a class="banner-link" '
    f'href="{PROMO_URL}">cohort or private courses.</a>',
)

_logo_uri = None


def logo_data_uri():
    global _logo_uri
    if _logo_uri is None:
        b64 = base64.b64encode(LOGO.read_bytes()).decode("ascii")
        _logo_uri = "data:image/svg+xml;base64," + b64
    return _logo_uri


def banner():
    lines = "".join(f'<div class="banner-line">{l}</div>' for l in BANNER_LINES)
    return (
        '<div class="promo-banner">'
        '<button class="promo-close" type="button" onclick="ucCloseBanner()" '
        'aria-label="Dismiss this notice" title="Dismiss">&#10005;</button>'
        '<div class="banner-inner">'
        f'<img class="banner-logo" src="{logo_data_uri()}" alt="Urbina Consulting">'
        f'<div class="banner-copy">{lines}</div>'
        f'<a class="promo-btn" href="{PROMO_URL}">Learn more</a>'
        "</div></div>"
    )


def sticky_bar(home="index.html", toggle=True):
    """The dark bar under the banner: the way back, and the provenance toggle.

    Nothing else goes in here. It briefly carried the page's own name as well, which
    the viewer copies into its toolbar title — but the page says what it is in its own
    <h1> a few pixels below, so it was a restatement taking the room the back link
    needs on a phone.

    What matters is that this link's **textContent** is what the viewer uses for the
    parent page's back label. Keep it short, and keep the arrow in it, since it is
    the only part of our bar that survives into the toolbar.

    `toggle=False` for pages with nothing to fold away. Lives here rather than in
    build.py because the v3 renderers emit it too, and when they each had their own
    copy the two drifted apart.
    """
    btn = ('<button class="provtoggle" onclick="toggleProv(this)">'
           'Show Item IDs &amp; Provenance</button>') if toggle else ''
    esc = lambda s: html.escape(str(s), quote=True)
    return (f'<div class="stickybar"><a class="sb-home" href="{home}" '
            f'title="Back to the evidence map">{esc(BACK_LABEL)}</a>{btn}</div>')


def chrome(bar=""):
    """The whole top chrome. `bar` is a sticky_bar(), or "" for pages that don't
    have one (index, personas, v1 journeys).

    Banner first, bar second, always — the old patch had to normalise this because
    different generators emitted them in different orders.
    """
    return '<div class="uc-chrome">' + banner() + bar + "</div>"


# ── Scroll helpers, shared by every page including the hand-authored maps ─────
#
# Both problems these solve come from the same fact: **inside the viewer this
# document does not scroll.** The parent sizes the iframe to the full content height
# and scrolls its own page instead. So `scrollIntoView` is a no-op vertically, a
# native `#id` jump moves nothing, and the highlight fires somewhere off screen where
# nobody sees it. Everything here therefore asks "who actually scrolls?" first:
#
#   embedded      -> the parent window (same origin, so its scroll is ours to set)
#   journey maps  -> `.container`, an inner box, when viewed directly
#   otherwise     -> this window
#
# `ucKeepPlace` is the other half: the provenance toggle changes the page height, and
# without it you lose your place. It pins the topmost id that is currently on screen
# and puts it back where it was afterwards.
#
# Emitted into build.py's pages via SCRIPTS below, and into the journey maps by
# postbuild/journey-chrome.py, which imports this constant rather than keeping a
# second copy that could drift.
JUMP_HELPERS = """<script>
/* uc-jump: shared scroll + highlight helpers. See chrome.py for why. */
(function(){
  function parentFrame(){
    if(window.parent === window) return null;
    try{
      var pw = window.parent;
      var fr = pw.document.getElementById("ai-projects-frame-content");
      if(!fr || fr.contentWindow !== window) return null;
      return {win: pw, frame: fr};
    }catch(e){ return null; }        /* cross-origin embed: treat as standalone */
  }

  /* Height to keep clear at the top: the viewer's toolbar plus our own chrome. */
  function headroom(){
    var h = 24, p = parentFrame();
    if(p){
      var tb = p.win.document.querySelector(".ai-projects-project-toolbar");
      if(tb) h += tb.offsetHeight;
    }
    var c = document.querySelector(".uc-chrome");
    if(c) h += c.offsetHeight;
    return h;
  }

  function innerBox(){
    var b = document.querySelector(".container");
    return (b && b.scrollHeight > b.clientHeight + 1) ? b : null;
  }

  function host(){
    var p = parentFrame();
    if(p) return {
      by: function(d){ p.win.scrollBy(0, d); },
      to: function(y){ p.win.scrollTo({top: Math.max(0, y), behavior: "smooth"}); },
      /* Our rects are document coordinates, since this document never scrolls. */
      docTop: function(){ return p.frame.getBoundingClientRect().top + p.win.scrollY; },
      band: function(){
        var r = p.frame.getBoundingClientRect();
        return {top: Math.max(0, -r.top), bottom: Math.min(p.win.innerHeight - r.top, r.height)};
      }
    };
    var box = innerBox();
    if(box) return {
      by: function(d){ box.scrollTop += d; }, to: null,
      band: function(){ var r = box.getBoundingClientRect(); return {top: r.top, bottom: r.bottom}; }
    };
    return {
      by: function(d){ window.scrollBy(0, d); }, to: null,
      band: function(){ return {top: 0, bottom: window.innerHeight}; }
    };
  }

  /* The box worth highlighting: the row, card or section the id sits in, not the
     badge itself — a 60px badge flashing in a 10,000px page is easy to miss. */
  var BOXES = ".grid-cell,.opportunity-card,article.insight,.turn,.card,.pblock,.section," +
              ".emotion-tag,.quote-block,tr,li,p,h2,h3";
  function boxFor(el){ return el.closest(BOXES) || el; }

  window.ucFlash = function(el){
    el.classList.remove("flash");
    void el.offsetWidth;                       /* restart a running animation */
    el.classList.add("flash");
    setTimeout(function(){ el.classList.remove("flash"); }, 3100);
  };

  window.ucJumpTo = function(id){
    var el = id && document.getElementById(id);
    if(!el) return false;
    var box = boxFor(el), h = host();
    if(h.to) h.to(h.docTop() + box.getBoundingClientRect().top - headroom());
    else box.scrollIntoView({block: "center", inline: "center", behavior: "smooth"});
    /* Horizontal is always ours, even when the parent owns the vertical. */
    if(h.to) box.scrollIntoView({block: "nearest", inline: "center"});
    ucFlash(box);
    return true;
  };

  window.ucKeepPlace = function(mutate){
    var h = host(), band = h.band(), keep = band.top + headroom();
    var ref = null, before = 0, all = document.querySelectorAll("[id]");
    for(var i = 0; i < all.length; i++){
      var r = all[i].getBoundingClientRect();
      if(r.height && r.bottom > keep){ ref = all[i]; before = r.top; break; }
    }
    var out = mutate();
    if(ref){
      var delta = ref.getBoundingClientRect().top - before;
      if(Math.abs(delta) > 1) h.by(delta);
    }
    return out;
  };

  /* Same-page links are ours: inside the viewer the injected frame script also
     listens for clicks and would hand a `#id` link to the parent as navigation,
     which lands the target under the toolbar. Capture phase so we go first. */
  document.addEventListener("click", function(e){
    var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if(!a) return;
    var id = decodeURIComponent(a.getAttribute("href").slice(1));
    if(!ucJumpTo(id)) return;
    e.preventDefault();
    e.stopPropagation();
    lastHash = id;   /* so the arrival poll below doesn't re-jump this one */
    if(history.replaceState) history.replaceState(null, "", "#" + id);
  }, true);

  /* Arriving with a hash — from another page, or from the viewer's own hash sync.
     Inside the viewer OUR url usually has no hash at all: the plugin strips it from
     the frame and keeps it on the parent's URL, doing its own scroll. That is why a
     cross-page evidence link used to land with no highlight — location.hash here was
     empty. The parent is same-origin, so read the hash from it instead.
     The delay lets the viewer finish its own scroll attempt before we correct it. */
  function targetId(){
    var h = location.hash.slice(1);
    if(h) return h;
    var p = parentFrame();
    if(p){ try{ return p.win.location.hash.slice(1); }catch(e){} }
    return "";
  }
  var lastHash = "";
  function onHash(){
    var h = targetId();
    if(h && h !== lastHash){
      lastHash = h;
      setTimeout(function(){ ucJumpTo(decodeURIComponent(h)); }, 350);
    }
  }
  window.addEventListener("hashchange", onHash);
  window.addEventListener("load", onHash);
  /* The parent's URL can change without any event reaching this document (its
     pushState navigation). A slow poll catches that; it is idle when nothing moves. */
  if(parentFrame()) setInterval(onHash, 700);
})();
</script>
"""

# Placed at the end of <body> so the whole chrome exists before it measures.
SCRIPTS = JUMP_HELPERS + """<script>
/* Chrome sizing. The chrome is sticky and therefore in normal flow, so nothing
   needs padding reserved for it. --chrome-h is still published because the
   journey-map container sizes itself against it. */
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
    try{sessionStorage.setItem(KEY,"1");}catch(e){}
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
<script>
/* Publish half the *content* viewport width so the full-bleed margins land
   exactly on the visible edges. clientWidth excludes the scrollbar; the vw unit
   does not, and that difference is enough to raise a horizontal scrollbar. */
(function(){
  function setHalfVw(){
    document.documentElement.style.setProperty(
      "--half-vw", (document.documentElement.clientWidth / 2) + "px");
  }
  setHalfVw();
  window.addEventListener("resize", setHalfVw);
  window.addEventListener("load", setHalfVw);
})();
</script>
"""
