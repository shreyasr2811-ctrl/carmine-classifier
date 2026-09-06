# Design system & front-end architecture

The UI was rebuilt as a design system rather than a set of styled screens. This
document is the reference for how it is put together and how to extend it.

Nothing in `src/`, `models/` or `rag_kb/` changed. The classifier, the feature
extractor and the RAG explanation layer are called exactly as before.

---

## 1. Structure

The product is a five-tab **site**, not a single screen:

| Tab | What it carries |
|---|---|
| Overview | Hero, the three principles, the stat band, how it works, where it fits |
| Technology | The 118-dim feature vector, the classifier, aggregation, the RAG layer |
| **Analyze** | The console itself — single patch and whole patient sample |
| Validation | The leakage comparison, held-out metrics, confusion matrix, limitations |
| About | The dataset, the stack, contact, the full disclaimer |

Navigation is `st.button` widgets inside `st.container(key="sitenav")`, which
gives the row a stable `.st-key-sitenav` class to style against. Anchor tags
with `?page=` would also work — Streamlit reads `st.query_params` — but each
click would cost a full page reload and a websocket reconnect. A button costs
one rerun.

The sidebar (session queue, model card, disclaimer) is rendered **only** on
Analyze. Streamlit omits the rail entirely when nothing is written to it, so
the four content pages lay out edge to edge like a site rather than like an app
with an empty tool rail bolted to the left. The Light/Dark control therefore
lives at the right-hand end of the nav, where every page can reach it.

```
app.py                  routing + the Analyze page; calls src/ unchanged
app_legacy_v5.py        the previous single-file app, kept for reference
ui/
├── brand.py            name, wordmark SVG, tab list -- the identity layer
├── tokens.py           colour, type, motion, radii -- the single source of truth
├── theme.py            tokens -> stylesheet; injected once per rerun
├── components.py       HTML/SVG components (tiles, banners, ring, gallery...)
├── site.py             site chrome + the four non-tool pages
├── charts.py           themed Plotly figures
├── copy.py             every piece of substantial user-facing prose
└── compat.py           Streamlit version shims (width= vs use_container_width)
.streamlit/config.toml  first-paint theme + server settings
```

The dependency direction is one-way: `app.py` → `ui/*` → `tokens.py`. No colour
value is written at a call site; components take a *tone*, and the tone resolves
to CSS custom properties.

**On the branding.** `Carmine` is a histological stain, which makes it literal
to the domain and a direct match for the warm palette. It is a fictional brand
for an academic project — the footer says so on every page, and there are no
invented testimonials, no institution logos, and no performance figure that
`models/metadata_grouped.json` does not contain. On a page deliberately styled
to look like a company's, that restraint is what keeps the styling honest.

---

## 2. Colour

Rebuilt as a warm clinical palette — the brand identity of a diagnostics
company, not a generic dark SaaS console. **Light is the primary mode** (a
clinic-facing medical brand is read in daylight far more often than at a dark
workstation); dark is available as a toggle for low-light reading rooms.

Two colour systems, kept deliberately separate:

| System | Role | Light | Dark | Used for |
|---|---|---|---|---|
| Brand (non-clinical) | accent | `#E8734F` | `#F0916D` | buttons, links, focus rings, kickers — **never** a clinical state |
| Semantic (clinical) | benign | `#0E9C86` | `#2AC4A8` | calm / low-involvement state |
| Semantic (clinical) | uncertain | `#B57A12` | `#E0A63C` | ambiguity, caution, standard review |
| Semantic (clinical) | malignant | `#B8303F` | `#D6394E` | flagged tissue |
| Semantic (clinical) | critical | `#8F2430` | `#E2465E` | **only** the HIGH PRIORITY banner |

**Why crimson and teal, not green and red.** Green/red is the conventional
medical pairing and the worst possible choice here: it collapses under
protanopia and deuteranopia, which affects roughly 1 in 12 men. Teal and
crimson stay separable under both, and sit against the pink-purple of
H&E-stained tissue without competing with it.

**A brand colour and an alert colour, kept apart on purpose.** Malignant is a
true crimson, not the brand's coral, precisely *because* the brand accent is
coral: a malignant badge sitting next to a primary button must never share a
hue family with it, or "the button is coral" starts to read as "this is the
alert colour". The pair is validated at ΔE 16–18 (normal vision) and clears
the colourblind-separation floor in both modes.

**Amber is never the only signal.** It always ships with a text label
("Genuinely ambiguous", "Standard review"), because it is the pair most at risk
under CVD.

### Chart colours are separate from UI colours

`ui/charts.py` carries its own `CHART_MARKS`. A fill sitting on a dark surface
needs OKLCH lightness roughly in 0.48–0.67 to read correctly; the UI values are
lighter than that because they also have to work as text. The chart values were
validated, not eyeballed:

```
dark   #17A992 / #D6394E   lightness band PASS · chroma PASS
                           deuteranopia ΔE 15.9 · normal-vision ΔE 18.6
                           contrast vs surface PASS
light  #0E9C86 / #B23A46   all checks PASS against surface
```

The spatial map uses a **diverging** scale, not a sequential one, because 0.0
and 1.0 are opposite poles (confidently benign / confidently malignant) and 0.5
is a real neutral midpoint. Two hues, grey middle, no rainbow.

---

## 3. Type

- **Inter** for UI, **IBM Plex Mono** for every number that is data.
- Loaded via a Google Fonts `@import` at the top of the injected stylesheet
  (verified to survive Streamlit's markdown sanitiser). Both have full fallback
  stacks, so an offline machine degrades to system fonts rather than breaking.
- `font-feature-settings: 'tnum'` so digits do not jitter when a value updates.

Putting scores, percentages and metrics in mono is a deliberate signal: it
separates *measurements* from *prose*, which matters in a tool whose credibility
rests on the reader being able to tell one from the other.

---

## 4. Motion

Ten keyframes in `theme.py` (`hpRise`, `hpPop`, `hpGrow`, `hpDraw`, `hpSweep`,
`hpBreathe`, `hpScan`, `hpShimmer`, `hpReveal`, `hpPulseRing`), all CSS.
Streamlit strips `<script>` from markdown, so there is no JavaScript animation
anywhere — which also makes `prefers-reduced-motion` work for free.

Motion is used where it carries meaning:

| Element | Motion | Why |
|---|---|---|
| Confidence ring | `stroke-dashoffset` draws to the value | the arc *is* the number |
| Triage banner | rise + one-time light sweep + accent bar growing down | marks arrival of a result |
| HIGH PRIORITY badge | slow 2.6s pulse ring | urgency without alarm |
| Stat tiles | staggered rise, 70ms apart | eye reads left to right |
| Probability split | segments grow from their own ends | shows the split forming |
| Progress | scan-line sweep | evokes a slide scanner |
| Masthead mark | 4.2s scan line | quiet sign of life |

Easing is expo-out (`cubic-bezier(.16,1,.3,1)`) for entrances and a standard
curve for state changes. Durations are 120/180/260/440/760ms.

Every animation is disabled under `@media (prefers-reduced-motion: reduce)`.
This is not optional in a medical-adjacent tool.

---

## 5. Four Streamlit problems worth knowing about

**Specificity.** Streamlit styles its own markdown output with selectors like
`[data-testid="stMarkdownContainer"] h1`, specificity (0,1,1). A bare
`.hp-mast-title` is (0,1,0) and silently loses, so custom type sizes fall back
to Streamlit's. `theme.scope_css()` prefixes every component selector with
`.stApp`, lifting them to (0,2,x). This is why the sheet is not carpeted in
`!important` — which would have broken the monospace numerals.

**Icon ligatures.** Streamlit's chevrons are Material Symbols ligatures. A
global `font-family` override renders them as the literal string
`keyboard_arrow_right`. `[data-testid="stIconMaterial"]` is explicitly excluded.

**Over-constrained pseudo-elements.** The active-tab underline started as an
`::after` bar at `bottom: -1px` and rendered at the *top* of the tab. Streamlit
ships `top: 0` on that pseudo-element, and an absolutely positioned box with
`top`, `bottom` and `height` all set is over-constrained — CSS resolves it by
honouring `top`. It is now an `inset` box-shadow, which has no position to
fight over, transitions cleanly and costs no layout.

**Form submit buttons are a different `kind`.** `st.button(type="primary")`
renders `kind="primary"`, but `st.form_submit_button(type="primary")` renders
`kind="primaryFormSubmit"`. Both are selected explicitly.

Only stable `data-testid` and BaseWeb role attributes are targeted, never
generated emotion class names, so this survives Streamlit upgrades.

---

## 6. What changed functionally

Design work that changed behaviour, not just appearance:

1. **The threshold slider is now live.** Scores are cached in session state
   after a run, so moving the threshold re-reads them instantly instead of
   re-scoring every patch. The operator can now actually *explore* the
   miss-versus-false-alarm trade-off, which was the point of the control.
2. **Spatial tissue map.** Patch coordinates are parsed from IDC filenames
   (`..._x951_y701_...`) and rebuilt into a slide-level heatmap. Focal and
   diffuse involvement produce the same headline percentage and look completely
   different here.
3. **Evidence gallery.** The 14 most and 7 least suspicious patches are shown as
   thumbnails with their scores. A headline figure a pathologist cannot trace
   back to tissue is not decision support.
4. **Ground truth from filenames.** Labels are recovered from the `classN`
   suffix as well as the `0/`–`1/` folders, so upload mode can now self-score.
5. **Session queue.** Analysed patients accumulate in the sidebar, sorted by
   priority — the queue view the tool is ultimately for.
6. **Threaded feature extraction.** `~45 ms/patch` was the bottleneck;
   scikit-image releases the GIL in its Cython kernels, so a small thread pool
   roughly halves wall-clock time on a dual-core machine and scales further.
7. **Honest model card.** The sidebar reads real numbers from
   `metadata_grouped.json`. The footer states explicitly that the higher
   patch-level split leaks patients and is not cited.
8. **Morphological profile.** Three properties of the flagged tissue measured
   from the same images: spatial pattern from the patch coordinates, and
   nuclear load and pleomorphism from colour deconvolution of the H&E stain.
   Reported on bands that are tertiles of our own cohort, with graded rather
   than hard membership, and labelled throughout as measurements rather than
   as a stage or a grade. Costs under 1 ms per patch, so it rides inside the
   existing extraction pass.
9. **Review priority index.** Involvement, nuclear load and spread combined
   into one figure graded across four bands. `graded_bands()` takes an
   arbitrary list of boundaries, so the three-band morphology rows and the
   four-band index share one implementation. Structured so involvement
   leads and morphology only modifies: an earlier weighted-sum version let a
   small amount of dense tissue push a 5%-involvement patient into the middle
   tier, so the quantity with a validated error bar behind it was put back in
   charge.
10. **Wordiness moved into tooltips.** Roughly 670 words of explanation left
   the results page for `title`-attribute tooltips behind info markers, about
   halving the visible text. Native tooltips rather than scripted popovers,
   because Streamlit strips `<script>` and the browser's own affordance is
   keyboard reachable for free. Long-form copy lives in `HELP` in `ui/copy.py`.
11. **Console split into a sticky rail and an output column.** Inputs and the
   threshold on the left, everything they drive on the right. `align-self:
   flex-start` on the column is load-bearing: a flex child stretches to full
   height by default and a full-height box has nothing to stick to.
12. **Unsupervised grouping via a Gaussian mixture**, replacing the
   hand-weighted index. Real posteriors instead of a smoothed rule, and BIC
   chose k rather than us.
13. **Two gates on the grouping.** It is suppressed when nothing is flagged
   (no suspicious tissue means nothing to characterise) and when the input
   holds more than one patient ID (that produces a cohort average, not a
   specimen). The second was a real bug: pointing at `data/idc_sample`, which
   holds 274 patients, silently returned one confident group for the whole
   cohort.
14. **The Validation page publishes the leak.** Rather than quietly reporting
   the grouped figure, the site shows the naive 85.9% next to the grouped
   82.6% and labels the 1.7-point gap as performance that exists only because
   247 of 274 patients appear on both sides of the split.

---

## 7. Extending it

**Add a semantic tone:** add `<name>`, `<name>_soft`, `<name>_line` to both
`DARK` and `LIGHT` in `tokens.py`, then add the name to `TONES` in
`components.py`. Every component picks it up.

**Add a stat tile:** `c.stat_tiles([{...}], columns=n)` — grid, not
`st.columns`, so card heights stay equal regardless of content length.

**Add a morphological measurement:** compute it per patch in
`src/morphology.py`, add its cohort tertiles to
`build_morphology_reference.py`, and append a block to the list built in
`render_patient_results`. Use `graded_bands()` so the output degrades to a
split reading near a boundary rather than snapping to one side.

**Add an explanation without adding words:** put the short form in the display
string and the long form in `HELP` in `ui/copy.py`, then pass it as
`help=` to `c.section()` or wrap a phrase in `c.term()`. The screen carries the
answer, the tooltip carries the explanation.

**Add a chart:** start from `_base_layout()` and `_axis()` in `charts.py`, and
take mark colours from `CHART_MARKS[mode]`. If you add a categorical series,
re-run the palette validation before shipping it.

**Add a tab:** append a `(slug, label)` pair to `PAGES` in `ui/brand.py`,
write a `page_<slug>()` renderer in `ui/site.py`, and add one branch to the
router at the bottom of `app.py`. The nav sizes itself from `PAGES`.

**Change the wording:** everything substantial is in `ui/copy.py`, on purpose.
The honesty framing is a feature of this product, and the fastest way for
careful wording to rot is to scatter it through layout code.

---

## 8. Known limitation

`config.toml`'s `base = "light"` is read once at load, so a few BaseWeb internals
(dropdown menus, some tooltips) stay light when the app is switched to Dark. The
visible offenders — number-input steppers, the uploader button — are painted
from the tokens explicitly. Light is the primary mode; Dark is a workstation-at-
night toggle.
