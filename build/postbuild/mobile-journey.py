"""
Applies the same mobile drawer pattern used in the ucLoops app to the
BorderBlend journey maps.

The journey maps have a fixed 240px .sidebar with .main-content offset by the
same amount, so on a phone the grid is pushed almost entirely off screen. Below
860px the sidebar becomes an off-canvas drawer with a backdrop, opened by a bar
in the main column — matching the app so the two feel like one product.

Idempotent: re-running detects the marker and skips.
"""

import sys, re
from pathlib import Path

MARKER = "uc-mobile-drawer"

CSS = """
/* ── uc-mobile-drawer: sidebar becomes an off-canvas drawer on small screens.
   Mirrors the ucLoops app so the journey maps and the chat tool behave the
   same way. z-index sits above the promo banner (300) so the drawer covers it
   rather than appearing underneath. ── */
.uc-drawer-handle { display: none; }
.uc-drawer-backdrop { display: none; }

@media (max-width: 859px) {
  .sidebar {
    width: 80vw !important;
    max-width: 320px;
    top: 0 !important;
    bottom: 0;
    left: 0;
    height: 100% !important;
    z-index: 400 !important;
    transform: translateX(-100%);
    transition: transform .22s ease;
    box-shadow: none;
  }
  .sidebar.uc-open {
    transform: translateX(0);
    box-shadow: 4px 0 24px rgba(0,0,0,.4);
  }
  .main-content { margin-left: 0 !important; }
  .container { overflow-x: hidden; }

  .uc-drawer-handle {
    display: flex;
    align-items: center;
    gap: .55rem;
    width: 100%;
    background: #34495e;
    border: none;
    border-bottom: 1px solid rgba(255,255,255,.12);
    color: #fff;
    padding: .5rem .8rem;
    cursor: pointer;
    font-family: inherit;
    font-size: .78rem;
    font-weight: 700;
    text-align: left;
    flex-shrink: 0;
  }
  .uc-drawer-handle .uc-dh-sub {
    display: block;
    font-size: .68rem;
    font-weight: 400;
    color: rgba(255,255,255,.6);
  }
  .uc-drawer-backdrop.uc-show {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.45);
    z-index: 390;
  }
  /* The close button inside the drawer, hidden on desktop. */
  .uc-drawer-close { display: block !important; }
}
.uc-drawer-close { display: none; }
"""

HANDLE = """<button class="uc-drawer-handle" type="button" onclick="ucOpenDrawer()">
<span>&#9776;</span>
<span style="flex:1;min-width:0">Open personas &amp; filters<span class="uc-dh-sub">Focus or hide personas in this journey</span></span>
<span style="opacity:.6;font-size:.7rem">&#9656;</span>
</button>
"""

# NB: .sidebar is a plain block, not a flex container, so this right-aligns with
# margin-left:auto rather than align-self.
CLOSE_BTN = """<button class="uc-drawer-close" type="button" onclick="ucCloseDrawer()" style="background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);color:#fff;border-radius:8px;padding:.3rem .7rem;font-size:.75rem;font-weight:700;cursor:pointer;margin:0 0 .75rem auto;width:max-content;font-family:inherit">&#10005; Close</button>
"""

BACKDROP = '<div class="uc-drawer-backdrop" onclick="ucCloseDrawer()"></div>\n'

JS = """<script>
/* uc-mobile-drawer toggle. On a phone, selecting a persona closes the drawer,
   since it covers the very grid the selection is meant to affect. On desktop
   the sidebar is a permanent column and must never auto-close — so every
   auto-dismiss path is gated on ucIsNarrow(). Explicit dismissals (the ✕ and
   the backdrop) stay ungated; they only exist on mobile anyway. */
function ucIsNarrow(){ return window.matchMedia('(max-width: 859px)').matches; }
function ucOpenDrawer(){
  document.querySelector('.sidebar')?.classList.add('uc-open');
  document.querySelector('.uc-drawer-backdrop')?.classList.add('uc-show');
}
function ucCloseDrawer(){
  document.querySelector('.sidebar')?.classList.remove('uc-open');
  document.querySelector('.uc-drawer-backdrop')?.classList.remove('uc-show');
}
document.addEventListener('DOMContentLoaded', function(){
  var sb = document.querySelector('.sidebar');
  if (!sb) return;
  sb.addEventListener('click', function(e){
    if (e.target.closest('.persona-btn, .show-all-btn, .persona-card')) {
      if (ucIsNarrow()) setTimeout(ucCloseDrawer, 180);
    }
  });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && ucIsNarrow()) ucCloseDrawer();
  });
});
</script>
"""


def patch(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return "skipped (already patched)"

    # 1. CSS before the final </style>
    idx = s.rfind("</style>")
    if idx == -1:
        return "FAILED: no </style>"
    s = s[:idx] + CSS + s[idx:]

    # 2. Close button as the first child of the sidebar
    if '<div class="sidebar">' not in s:
        return "FAILED: no .sidebar div"
    s = s.replace('<div class="sidebar">', '<div class="sidebar">\n' + CLOSE_BTN, 1)

    # 3. Handle as the first child of main-content, plus the backdrop
    if '<div class="main-content">' not in s:
        return "FAILED: no .main-content div"
    s = s.replace(
        '<div class="main-content">',
        BACKDROP + '<div class="main-content">\n' + HANDLE,
        1,
    )

    # 4. JS before </body>
    idx = s.rfind("</body>")
    if idx == -1:
        return "FAILED: no </body>"
    s = s[:idx] + JS + s[idx:]

    path.write_text(s, encoding="utf-8")
    return "patched"


base = Path(sys.argv[1])
for name in sorted(base.glob("journey-map-*.html")):
    print(f"{name.name:42s} {patch(name)}")
