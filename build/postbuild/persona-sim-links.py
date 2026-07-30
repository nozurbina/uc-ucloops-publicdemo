"""
Links the BorderBlend evidence map to the ucLoops persona-simulation app.

Three changes:
  1. Journey sidebar — a Chat action on each persona card, first of the three,
     deep-linking to that persona in the app.
  2. Journey drawer handle — subtitle now mentions chatting.
  3. Persona pages — a "Launch AI Persona Sim" button in the page header.

Links carry ?agent=<id>, which the app reads on boot to open that persona's
conversation directly. Ids are lowercase because the app's parser is
case-sensitive and falls back to its overview on anything it doesn't recognise.

Idempotent via the `uc-persona-sim` marker.
"""

import re
import sys
from pathlib import Path

MARKER = "uc-persona-sim"
APP = "https://ucloops-demo-v1.vercel.app/"

# Persona page -> the app's agent id. Only the v3 pages are mapped: they are the
# current set and each corresponds to exactly one agent. The older pages are
# left alone — persona-business-lunch.html covers two personas at once, so there
# is no single agent to send someone to.
PAGE_TO_AGENT = {
    "persona-omar-v3.html": ("omar", "Omar"),
    "persona-grace-v3.html": ("grace", "Grace"),
    "persona-late-night-foodie-v3.html": ("mateo", "Mateo"),
    "persona-franchisee-v3.html": ("diego", "Diego"),
    "persona-everyday-20s-v3.html": ("tyler", "Tyler"),
}

CSS = """
/* ── uc-persona-sim: links out to the persona simulation app ── */
.persona-actions{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center}
a.persona-btn{text-decoration:none}
a.persona-btn.chat-btn{background:rgba(117,6,117,.9);border-color:rgba(215,163,43,.6);color:#fff}
a.persona-btn.chat-btn:hover{background:rgba(117,6,117,1);border-color:#d7a32b;text-decoration:none}

.sim-launch-wrap{margin:.9rem auto 0;text-align:center}
.sim-launch{display:inline-flex;align-items:center;gap:.5rem;
  background:linear-gradient(180deg,#e8bc52,#d7a32b);border:1px solid #d7a32b;border-radius:999px;
  color:#500850;text-decoration:none;font-weight:700;font-size:.95rem;padding:.55rem 1.2rem}
.sim-launch:hover{filter:brightness(1.06);text-decoration:none;color:#500850}
.sim-launch-note{display:block;font-size:.75rem;color:rgba(255,255,255,.75);margin-top:.4rem}
"""


def chat_link(agent: str, name: str) -> str:
    return (
        f'<a class="persona-btn chat-btn" href="{APP}?agent={agent}" '
        f'target="_blank" rel="noopener" title="Chat with the {name} AI persona">'
        f"<span>Chat</span> &#128488;&#65039;</a>"
    )


def inject_css(s: str) -> str:
    i = s.rfind("</style>")
    return s if i == -1 else s[:i] + CSS + s[i:]


def patch_journey(path: Path) -> str:
    """Chat action on each sidebar persona card, plus the drawer subtitle."""
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return "skipped"

    added = 0
    # Split on the card boundary rather than regex-matching a whole card: the
    # cards nest an avatar div, so a non-greedy ".*?</div>\n</div>" stops at the
    # avatar's closing pair and never reaches .persona-actions.
    #
    # Each card names the persona page it links to, so the agent is derivable
    # from the card itself — no separate persona1/persona2 mapping needed.
    sep = '<div class="persona-card"'
    parts = s.split(sep)
    for k in range(1, len(parts)):
        chunk = parts[k]
        anchor = '<div class="persona-actions">'
        a = chunk.find(anchor)
        if a == -1:
            continue
        head = chunk[:a]  # the card's own content, where its href lives
        page = next((c for c in PAGE_TO_AGENT if c in head), None)
        if page is None:
            continue
        agent, name = PAGE_TO_AGENT[page]
        insert = a + len(anchor)
        parts[k] = chunk[:insert] + chat_link(agent, name) + chunk[insert:]
        added += 1
    s = sep.join(parts)
    if added == 0:
        return "FAILED: no persona cards matched"

    old_sub = "Focus or hide personas in this journey"
    new_sub = "Focus on, hide, or chat with personas in this journey"
    subs = s.count(old_sub)
    s = s.replace(old_sub, new_sub)

    s = inject_css(s) + f"\n<!-- {MARKER} -->\n"
    path.write_text(s, encoding="utf-8")
    return f"patched ({added} cards, {subs} subtitle)"


def patch_persona(path: Path) -> str:
    """Launch button in the persona page header."""
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return "skipped"
    agent, name = PAGE_TO_AGENT[path.name]

    m = re.search(r'(<div class="persona-role">.*?</div>)\s*(</header>)', s, re.S)
    if not m:
        return "FAILED: no persona-role before </header>"

    button = (
        '\n<div class="sim-launch-wrap">'
        f'<a class="sim-launch" href="{APP}?agent={agent}" target="_blank" rel="noopener">'
        f"&#128488;&#65039; Launch AI Persona Sim</a>"
        f'<span class="sim-launch-note">Chat with {name} in the ucLoops demo app'
        " &middot; opens in a new tab</span></div>\n"
    )
    s = s[: m.end(1)] + button + s[m.end(1) : ]

    s = inject_css(s) + f"\n<!-- {MARKER} -->\n"
    path.write_text(s, encoding="utf-8")
    return "patched"


base = Path(sys.argv[1])
print("── journey maps ──")
for f in sorted(base.glob("journey-map-*.html")):
    # The v2 maps have no persona action row to add a Chat link to — they predate it.
    # Skipping them by name keeps a clean run from printing a FAILED line that is
    # expected, which is worse than useless: it teaches you to ignore failures.
    if "-v2.html" in f.name:
        print(f"  {f.name:42s} skipped (v2 has no persona action row)")
        continue
    print(f"  {f.name:42s} {patch_journey(f)}")
print("── persona pages ──")
for name in sorted(PAGE_TO_AGENT):
    f = base / name
    if not f.exists():
        print(f"  {name:42s} MISSING")
        continue
    print(f"  {name:42s} {patch_persona(f)}")
