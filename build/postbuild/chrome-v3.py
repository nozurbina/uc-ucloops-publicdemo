"""
Three chrome fixes on top of chrome-v2.

1. FULL-BLEED BANNER. body on most of these pages *is* `.docwrap`, which sets
   `max-width:72rem;margin:0 auto`. The old chrome was `position:fixed;left:0;
   right:0`, so it escaped that; chrome-v2 made it sticky, which put it back in
   flow and therefore inside the 72rem cap — the banner stopped stretching. Fixed
   with the standard full-bleed trick: 100vw wide, pulled out by half the
   difference between the content box and the viewport. Self-neutralising, so it
   is also correct on the journey maps where the body is not capped.

   The banner *background* stretches; the content inside stays capped at 72rem,
   which is the intent — not text running edge to edge on a wide monitor.

2. LOGO. The host serves .svg as `application/octet-stream`, and browsers refuse
   to render an <img> SVG with that content type — hence the broken-image icon.
   (.jpg is served correctly as image/jpeg, so this is SVG-specific.) Switched to
   a base64 data URI, which carries its own type and so cannot be mis-served.
   Deliberately NOT inlined as markup: the file contains `<style>.st0{fill:#fff}`
   plus `id="Layer_2"`, which inlining would leak into every page. A data URI
   keeps them scoped to the image document.

3. CLOSE BUTTON. It sat at the banner's right edge, directly above the Learn more
   button. Now anchored to `.banner-inner` with reserved padding, so it clears the
   button at every width rather than only where a gutter happens to exist.

Idempotent via the `uc-chrome-v3` marker. Run after chrome-v2.py.
"""

import base64
import re
import sys
from pathlib import Path

MARKER = "uc-chrome-v3"

CSS = """
/* ── uc-chrome-v3 ── */

/* Full-bleed. `body` is `.docwrap` (max-width:72rem;margin:0 auto) on most pages,
   so the sticky chrome from v2 was capped at the text column. 50% here is half
   the content box, so this resolves to 0 when the parent is already full width —
   correct on the journey maps too, without a second rule.

   No `width:100vw` on purpose. Setting width alongside both margins
   over-constrains a block, so margin-right is dropped and the banner ends a
   scrollbar-width short of the right edge — a visible sliver. With width auto,
   both margins apply.

   --half-vw is set from documentElement.clientWidth by the script at the end of
   the body. Plain `50vw` overshoots by half a scrollbar width — `vw` counts the
   scrollbar, `50%` does not — which is enough to raise a horizontal scrollbar on
   every page that scrolls vertically. `50vw` stays as the no-JS fallback, with
   overflow-x:clip below containing it in that case. */
.uc-chrome{margin-left:calc(50% - var(--half-vw, 50vw));margin-right:calc(50% - var(--half-vw, 50vw))}

/* `clip`, not `hidden`: `hidden` would make <html> a scroll container and break
   the sticky chrome. */
html{overflow-x:clip}

/* Background stretches, content stays in the 72rem column. */
.uc-chrome .promo-banner .banner-inner{max-width:72rem;margin-left:auto;margin-right:auto;
  position:relative;padding-right:2.8rem}

/* Anchored to the content column rather than the banner edge, with the padding
   above reserving its space — so it clears the Learn more button at every width
   instead of relying on a gutter that only exists on wide screens. */
.uc-chrome .promo-banner .promo-close{position:absolute;top:0;right:0}

@media(max-width:859px){
  .uc-chrome .promo-banner{padding-right:1.25rem}
  .uc-chrome .promo-banner .banner-inner{padding-right:2.4rem}
}
"""


SCRIPT = """<script>
/* uc-chrome-v3: publish half the *content* viewport width so the full-bleed
   margins land exactly on the visible edges. clientWidth excludes the scrollbar;
   the vw unit does not, and that difference is enough to raise a horizontal
   scrollbar. */
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


def patch(path: Path, data_uri: str) -> str:
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return "skipped"
    if "uc-chrome-v2" not in s:
        return "FAILED: chrome-v2 not applied yet"

    # Logo -> data URI. src is "2023-uc-logo-outline.svg" at the top level and
    # "../2023-uc-logo-outline.svg" under sources/, so match either.
    before = s
    s = re.sub(
        r'(<img class="banner-logo" src=")(?:\.\./)?2023-uc-logo-outline\.svg(")',
        lambda m: m.group(1) + data_uri + m.group(2),
        s,
    )
    swapped = s != before

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
    return "patched" + ("" if swapped else " (no logo img found)")


base = Path(sys.argv[1])
svg = base / "2023-uc-logo-outline.svg"
if not svg.exists():
    raise SystemExit(f"logo not found: {svg}")
b64 = base64.b64encode(svg.read_bytes()).decode("ascii")
data_uri = "data:image/svg+xml;base64," + b64
print(f"logo: {svg.stat().st_size} bytes -> {len(data_uri)} char data URI")

files = sorted(base.glob("*.html")) + sorted((base / "sources").glob("*.html"))
counts = {}
for f in files:
    r = patch(f, data_uri)
    counts[r] = counts.get(r, 0) + 1
    if r.startswith("FAILED"):
        print(f"  {f.name:42s} {r}")
for k, v in sorted(counts.items()):
    print(f"{k}: {v}")
