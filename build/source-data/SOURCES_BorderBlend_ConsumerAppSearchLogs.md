# Source: Consumer App Search Logs — BorderBlend Consumer App and Web Ordering Flow
**Source type:** Search log
**Period:** 90 days (Q3)
**Platform:** BorderBlend consumer app (iOS and Android) and web ordering at borderblend.ca
**Total sessions analysed:** Approximately 31,000 sessions including a search or browse event
**Methodology:** Top terms extracted and grouped by intent cluster. Drop-off points noted at key funnel stages. App and web sessions combined; platform noted where behaviour differs. Personally identifiable data excluded.

---

## Summary observations

The consumer app and web ordering flow reveals a gap between user intent and available functionality. The most-searched terms fall into two categories: operational (is the truck open, where is it) and decisional (what should I order, is this item available). Both categories represent live, real-time intent that the current platform handles poorly — operational information is not always current, and menu availability is static rather than live.

Drop-off data shows the most significant funnel abandonment occurring at the "select location" step, suggesting that the inability to confirm whether a specific truck is currently operating is causing order abandonment before checkout.

---

## Cluster 1: Location and availability (highest volume)

| Query / action | Volume | Drop-off point | Notes |
|----------------|--------|---------------|-------|
| [Search: "truck near me"] | Very high | 38% drop-off if no truck shows as "open now" | Primary search intent; users checking whether a nearby truck is currently operating |
| [Browse: location map with no "open" filter] | High | 34% drop-off | Users scanning the map cannot distinguish open from scheduled |
| [Search: "open now"] | High | 49% drop-off | Term used when users are in real-time decision mode; app does not reliably surface this |
| [Search: truck by neighbourhood name] | Medium-high | 27% drop-off | Specific neighbourhood searches suggest repeat customers checking a known location |
| [Search: "hours today"] | Medium | 42% drop-off | Real-time hours query; static schedule does not satisfy this intent |
| [Search: "Saturday locations"] | Medium | 31% drop-off | Weekend schedule query |
| [Search: "festival" or "event"] | Medium | 24% drop-off | Event-based location intent; partial information available |

**Key finding:** The location step has the single highest funnel drop-off point. Users who cannot confirm a truck is open in real time abandon the session at 35–49% rates depending on the query. This is a direct revenue impact from an infrastructure gap, not a marketing or content problem.

---

## Cluster 2: Menu and ordering (second-highest volume)

| Query / action | Volume | Drop-off point | Notes |
|----------------|--------|---------------|-------|
| [Search: "brisket"] | Very high | 8% drop-off | Dominant menu search; users seeking the hero item convert well |
| [Browse: menu page, time >60s] | High | 19% drop-off | Extended menu browsing before ordering — suggests some users are making up their minds |
| [Search: "plant-based" or "vegetarian"] | Medium-high | 12% drop-off | Dietary option search converts well, suggesting good content for this category |
| [Search: "gluten"] | Medium | 31% drop-off | Allergen information-seeking; exit rate suggests information is hard to find |
| [Search: "seasonal"] | Medium | 22% drop-off | Users looking for limited/seasonal items; when the seasonal item is not listed, high drop-off |
| [Search: "new"] | Medium | 28% drop-off | Menu curiosity / new item seeking |
| [Browse: menu then exit without ordering] | High | — | Significant browse-and-exit pattern; in-app menu doesn't always match in-person menu |

**Key finding:** Allergen information-seeking has a high exit rate (31%). Users with dietary restrictions are not finding clear allergen information and abandoning. This is both a UX gap and a potential food safety concern.

---

## Cluster 3: Ordering experience

| Query / action | Volume | Drop-off point | Notes |
|----------------|--------|---------------|-------|
| [Checkout abandonment — payment step] | Medium | — | After selecting items, a segment drops off at payment; likely reflects UX friction or distrust of the payment flow |
| [Search: "order ahead"] | Medium | 44% drop-off | Users explicitly seeking the pre-order function; when it doesn't work as expected, high abandonment |
| [Checkout abandonment — location confirmation step] | High | — | Users who got to checkout drop off when asked to confirm pickup location — suggests the location they selected may not match expectation |
| [Return visit without ordering] | Medium-high | — | Users who open the app, browse, but consistently don't order; may represent the "checking if the truck is open" use case without a smooth conversion path |

---

## Cluster 4: Loyalty and account

| Query / action | Volume | Drop-off point | Notes |
|----------------|--------|---------------|-------|
| [Search: "loyalty" or "points"] | Medium | 33% drop-off | Users seeking loyalty programme information; discovery and conversion are incomplete |
| [Account creation step abandonment] | Medium | — | A portion of users start account creation but do not complete it; likely friction in the registration flow |
| [Search: "my account"] | Low-medium | 18% drop-off | Returning users managing their account; relatively smooth |
| [Search: "referral"] | Low | 27% drop-off | Users seeking a referral or sharing mechanism; feature exists but is not prominent |

---

## Notable patterns

**Location confirmation is the single biggest conversion barrier.** Across multiple query types, the inability to confirm in real time whether a specific truck is currently open causes 35–49% session abandonment. This is consistent with interview data from Rafael Cruz (BB-INT010), Thomas Hardy (BB-INT011), Carmen Rodriguez (BB-INT012), and Priya Sharma (BB-INT008) — all independently identified schedule/location confirmation as a friction point. Four-source convergence makes this the strongest single finding from quantitative data.

**Allergen information-seeking has a high and disproportionate exit rate.** For a food brand operating in an increasingly allergen-aware consumer environment, this gap creates both experience friction and potential food safety exposure. 31% abandonment on allergen queries is notably high.

**Browse-and-exit without ordering is a significant pattern.** Users who open the app and browse the menu without ordering may be using the app purely as a menu reference, or may be dropping off because the information doesn't match their in-person experience (e.g., menu items available on the app are not available at the truck, or vice versa). This in-person/digital menu discrepancy is a known franchisee operations challenge.

**"Order ahead" has high drop-off when it doesn't work as expected (44%).** Users who explicitly seek this function have high intent. When the function fails them, they are more likely to abandon the channel entirely than to convert through a workaround.
