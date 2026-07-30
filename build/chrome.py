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

# The sticky bar's back link. Kept short deliberately — the AI-projects viewer
# reads this element's textContent as the label for the *parent* page's toolbar
# ("Back to <label>"), and it has to survive a phone-width bar. The arrow is CSS
# (`.sb-home::before`), not markup, so it stays out of that textContent.
BACK_LABEL = "Evidence Map"

# Site name, for the index's own <title> and the archive pages that have no better
# label of their own.
SITE_TITLE = "BorderBlend Evidence Map"

PROMO_URL = "https://urbinaconsulting.com/shares/ucloops/cohort-journeys-sept-2026/"

# Marks a page as carrying the final chrome. Emitted at the very end of the file.
MARKER = "<!-- uc-chrome -->"

# Runs during parsing, before the banner exists, so a banner dismissed on an
# earlier page never flashes into view on this one.
EARLY = (
    '<script>try{if(localStorage.getItem("ucPromoDismissed")==="1")'
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


def sticky_bar(home="index.html", page_title="", toggle=True):
    """The dark bar under the banner: back link, where you are, provenance toggle.

    The two texts are deliberately different things, because the viewer maps them
    onto separate slots in the parent page's toolbar:

        <a class="sb-home">   -> "Back to {this}"   (BACK_LABEL, short)
        <span class="sb-title"> -> the toolbar title (this page)

    They used to be the same string, nested — so the toolbar read
    "←BorderBlend Evidence Map   BorderBlend Evidence Map" and told you nothing
    about where you were. Keep the page's own name in `page_title`.

    `toggle=False` for pages with nothing to fold away. Lives here rather than in
    build.py because the v3 renderers emit it too, and when they each had their own
    copy the two drifted apart.
    """
    btn = ('<button class="provtoggle" onclick="toggleProv(this)">'
           'Show Item IDs &amp; Provenance</button>') if toggle else ''
    esc = lambda s: html.escape(str(s), quote=True)
    title = (f'<span class="sb-title">{esc(page_title)}</span>'
             if page_title else '')
    return (f'<div class="stickybar"><a class="sb-home" href="{home}" '
            f'title="Back to the {esc(BACK_LABEL)}">{esc(BACK_LABEL)}</a>'
            f'{title}{btn}</div>')


def chrome(bar=""):
    """The whole top chrome. `bar` is a sticky_bar(), or "" for pages that don't
    have one (index, personas, v1 journeys).

    Banner first, bar second, always — the old patch had to normalise this because
    different generators emitted them in different orders.
    """
    return '<div class="uc-chrome">' + banner() + bar + "</div>"


# Placed at the end of <body> so the whole chrome exists before it measures.
SCRIPTS = """<script>
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
