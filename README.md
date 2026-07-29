# BorderBlend Evidence Map

A worked example of the **ucLoops** methodology: a complete, traceable research
deliverable set — personas, journey maps, insights, and the source verbatims they
rest on — where every claim links back to the evidence behind it.

**Live:** https://urbinaconsulting.com/shares/ucloops/borderblend/

## The content is synthetic

BorderBlend is a fictional cross-border taco brand. The interviews, app logs,
support tickets, social posts, and market research in `sources/` were all
generated for this demonstration. No real client, company, or person appears
anywhere in this repository.

The point of the example is the *structure* — how evidence chains together — not
the findings.

## Layout

| Path | What it is |
|---|---|
| `index.html` | Entry point: the evidence map |
| `insights.html` | The insight set, each linked to its sources |
| `persona-*-v3.html` | Current persona profiles (5) |
| `journey-map-*-v3.html` | Current journey maps (2) |
| `sources/` | Source material — interviews, app logs, tickets, social, market research |
| `headshots/` | Persona portraits |

`*-v2` files and the non-`v3` persona pages are earlier iterations, kept so the
progression is visible.

## How to read it

Start at `index.html`. Every item ID is a deep link: a persona line links to the
insight it rests on, and each insight links down to the dated verbatim it came
from. **Show Item IDs and Provenance** on any page exposes those chains inline.

Five personas can also be interviewed directly in the ucLoops demo app, via the
🗨️ Chat action in a journey sidebar or **Launch AI Persona Sim** on a persona
page.

## Static, self-contained

Plain HTML with inline CSS and JS. No build step, no dependencies, no external
requests. Open `index.html` in a browser, or serve the folder:

```sh
python -m http.server 8000
```

Published pages are wrapped by a viewer that rebuilds the top bar in the parent
page, so the top chrome renders slightly differently there than when opening the
files directly. Both are expected.
