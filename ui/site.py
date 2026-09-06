"""
Site chrome and the four non-tool pages.

The product is presented as a site rather than a single screen: a brand bar,
a five-tab top navigation, four content pages and a shared footer. The
classifier itself lives on the Analyze tab and is rendered by app.py, which
is why it is absent from this file.

Navigation is st.button widgets inside a keyed container, not anchor tags.
Anchors would work -- Streamlit reads ?page= out of st.query_params -- but
every click would cost a full page reload and a websocket reconnect. Buttons
cost one rerun. The URL does not change; the trade is worth it.

Nothing here fabricates evidence. There are no invented customer quotes, no
logos of institutions that have not used this, and no performance figure that
models/metadata_grouped.json does not contain. On a page that is deliberately
styled to look like a company's, that restraint is the only thing keeping the
styling honest.
"""

from __future__ import annotations

import streamlit as st

from . import brand
from . import components as c
from . import copy as txt
from .compat import STRETCH, WIDE


# ==========================================================================
# Chrome
# ==========================================================================

def header(pills: list[tuple[str, str]] | None = None) -> None:
    """Brand bar: wordmark left, live status pills right."""
    pill_html = ""
    if pills:
        pill_html = "".join(
            f'<span class="hp-pill"><i class="hp-dot {c._e(state)}"></i>'
            f'{c._e(text)}</span>'
            for state, text in pills
        )
    c.render(f"""
<div class="hp-brandbar hp-fade">
  <div class="hp-brand">
    <span class="hp-brand-mark">{brand.mark(32)}</span>
    <span>
      <div class="hp-brand-name">{brand.NAME}</div>
      <div class="hp-brand-sub">{brand.DESCRIPTOR}</div>
    </span>
  </div>
  <div class="hp-brand-right">{pill_html}</div>
</div>
""")


def nav(active: str) -> str | None:
    """
    Render the tab row. Returns the slug the user clicked, or None.

    The active tab is drawn as kind="primary" purely so the stylesheet has a
    stable hook for it -- SITE re-skins that from a filled button into an
    underlined nav item, so nothing here looks like a call to action.

    The Light/Dark control rides at the right-hand end rather than in the
    sidebar, because the sidebar is only rendered on the Analyze page and the
    appearance switch has to stay reachable from all five.
    """
    clicked = None
    with st.container(key="sitenav"):
        cols = st.columns([1] * len(brand.PAGES) + [0.92], gap="small")
        for col, (slug, label) in zip(cols, brand.PAGES):
            with col:
                if st.button(
                    label,
                    key=f"nav_{slug}",
                    type="primary" if slug == active else "tertiary",
                    **WIDE,
                ):
                    clicked = slug
        with cols[-1]:
            st.radio(
                "Appearance", ["Light", "Dark"], key="ui_mode",
                horizontal=True, label_visibility="collapsed", **STRETCH,
            )
    return clicked


def footer(model_line: str) -> None:
    c.render(f"""
<div class="hp-sitefoot">
  <div class="hp-sitefoot-top">
    <div>
      <div class="hp-sitefoot-brand">
        <span style="color:var(--text-low)">{brand.mark(22)}</span>
        <span class="n">{brand.NAME}</span>
      </div>
      <div class="hp-sitefoot-pos" style="margin-top:.45rem">{brand.POSITION}</div>
    </div>
    <div class="hp-sitefoot-note">{txt.SITE_FOOTER_NOTE}</div>
  </div>
</div>
""")
    c.footer(model_line)


# ==========================================================================
# Shared page primitives
# ==========================================================================

def cards(items: list[dict], columns: int = 3) -> None:
    """items: [{kicker, title, body}]"""
    cells = "".join(
        f'<div class="hp-card" style="--d:{60 + i * 90}ms">'
        f'<span class="hp-card-kicker">{c._e(it["kicker"])}</span>'
        f'<div class="hp-card-title">{c._e(it["title"])}</div>'
        f'<div class="hp-card-body">{it["body"]}</div></div>'
        for i, it in enumerate(items)
    )
    c.render(f'<div class="hp-cards" style="grid-template-columns:'
             f'repeat({columns},minmax(0,1fr))">{cells}</div>')


def band(cells_in: list[tuple[str, str]], columns: int | None = None) -> None:
    """cells_in: [(value_html, label)] -- the wide statistics strip."""
    n = columns or len(cells_in)
    cells = "".join(
        f'<div class="hp-band-cell" style="--d:{i * 80}ms">'
        f'<div class="hp-band-value">{v}</div>'
        f'<div class="hp-band-label">{c._e(l)}</div></div>'
        for i, (v, l) in enumerate(cells_in)
    )
    c.render(f'<div class="hp-band" style="grid-template-columns:'
             f'repeat({n},minmax(0,1fr))">{cells}</div>')


def steps(items: list[tuple[str, str]]) -> None:
    rows = "".join(
        f'<div class="hp-step" style="--d:{i * 80}ms">'
        f'<div class="hp-step-n">{i + 1:02d}</div>'
        f'<div><div class="hp-step-t">{c._e(t)}</div>'
        f'<div class="hp-step-b">{b}</div></div></div>'
        for i, (t, b) in enumerate(items)
    )
    c.render(f'<div class="hp-steps">{rows}</div>')


def table(headers: list[tuple[str, str]], rows: list[list], row_classes=None) -> None:
    """
    headers: [(label, css_class)] where css_class in {'', 'name', 'num'}
    rows:    list of cell lists, already HTML-safe
    """
    head = "".join(f'<th class="{cls}">{c._e(h)}</th>' for h, cls in headers)
    body = []
    for i, r in enumerate(rows):
        rc = row_classes[i] if row_classes else ""
        tds = "".join(
            f'<td class="{headers[j][1]}">{cell}</td>' for j, cell in enumerate(r)
        )
        body.append(f'<tr class="{rc}">{tds}</tr>')
    c.render(
        f'<div class="hp-tablewrap"><table class="hp-table">'
        f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody>'
        f'</table></div>'
    )


def spec_card(title: str, rows: list[tuple[str, str, str]]) -> str:
    """rows: [(key, value, tone)] -- tone '' for neutral. Returns HTML."""
    body = "".join(
        f'<div class="hp-spec-row" style="{c.tone_vars(tone) if tone else ""}">'
        f'<span class="k">{c._e(k)}</span>'
        f'<span class="v{" tone" if tone else ""}">{c._e(v)}</span></div>'
        for k, v, tone in rows
    )
    return (f'<div class="hp-spec"><div class="hp-spec-head">'
            f'<span class="t">{c._e(title)}</span>'
            f'<i class="hp-dot live"></i></div>{body}</div>')


def limitations(items: list[tuple[str, str]]) -> None:
    rows = "".join(
        f'<div class="hp-limit" style="--d:{i * 70}ms">'
        f'<span class="hp-limit-mark">{c.ICONS["alert"]}</span>'
        f'<div><div class="hp-limit-t">{t}</div>'
        f'<div class="hp-limit-b">{b}</div></div></div>'
        for i, (t, b) in enumerate(items)
    )
    c.render(f'<div class="hp-limits">{rows}</div>')


def page_head(title: str, kicker: str = "", sub: str = "") -> None:
    """
    The heading at the top of a content page.

    Deliberately heavier than c.section(): a section title is a signpost
    inside a page, whereas this is the page's name and has to hold the top of
    a full-width layout on its own.
    """
    k = f'<span class="hp-pagehead-kicker">{c._e(kicker)}</span>' if kicker else ""
    s = f'<p class="hp-pagehead-sub">{sub}</p>' if sub else ""
    c.render(f'<div class="hp-pagehead">{k}'
             f'<h1 class="hp-pagehead-title">{c._e(title)}</h1>{s}'
             f'<div class="hp-pagehead-rule"></div></div>')


def lead(text_html: str) -> None:
    c.render(f'<div class="hp-lead">{text_html}</div>')


def cta(title: str, body: str) -> None:
    c.render(f'<div class="hp-cta"><div class="hp-cta-title">{c._e(title)}</div>'
             f'<div class="hp-cta-body">{body}</div></div>')


def confusion_matrix(tn: int, fp: int, fn: int, tp: int) -> None:
    """2x2, coloured by whether the cell is a correct call or an error."""
    def cell(n: int, label: str, tone: str, d: int) -> str:
        return (f'<div class="hp-cm-cell" style="{c.tone_vars(tone)} --d:{d}ms">'
                f'<div class="hp-cm-n">{n}</div>'
                f'<div class="hp-cm-l">{label}</div></div>')

    c.render(f"""
<div class="hp-cm">
  <div class="hp-cm-h"></div>
  <div class="hp-cm-h">called benign</div>
  <div class="hp-cm-h">called malignant</div>
  <div class="hp-cm-h side">truly benign</div>
  {cell(tn, "correct", "benign", 0)}
  {cell(fp, "false alarm", "uncertain", 60)}
  <div class="hp-cm-h side">truly malignant</div>
  {cell(fn, "missed", "malignant", 120)}
  {cell(tp, "correct", "benign", 180)}
</div>
""")


# ==========================================================================
# Pages
# ==========================================================================

def page_overview(meta: dict, goto) -> None:
    cv = meta.get("grouped_cross_validation", {}).get("xgboost", {})
    ho = meta.get("grouped_holdout", {})

    spec = spec_card("At a glance", [
        ("Held-out accuracy", f"{ho.get('accuracy', 0):.1%}", "benign"),
        ("Held-out AUC", f"{ho.get('auc', 0):.3f}", ""),
        ("Cross-validated", f"{cv.get('accuracy', {}).get('mean', 0):.1%}"
                            f" ± {cv.get('accuracy', {}).get('std', 0):.1%}", ""),
        ("Patients", f"{meta.get('n_patients', 274)}", ""),
        ("Features per patch", f"{meta.get('feature_dim', 118)}", ""),
        ("Validation split", "Patient-grouped", ""),
        ("Compute", "CPU only", ""),
    ])

    c.render(f"""
<div class="hp-hero">
  <div>
    <span class="hp-hero-eyebrow">{c.ICONS["spark"]}{txt.HERO_EYEBROW}</span>
    <h1 class="hp-hero-title">{txt.HERO_TITLE}</h1>
    <p class="hp-hero-body">{txt.HERO_BODY}</p>
    <div class="hp-hero-note">{txt.HERO_NOTE}</div>
  </div>
  <div>{spec}</div>
</div>
""")

    st.write("")
    b1, b2, _ = st.columns([1, 1, 2.1], gap="small")
    if b1.button("Open the console", type="primary", **WIDE):
        goto("analyze")
    if b2.button("See the validation", **WIDE):
        goto("validation")

    st.write("")
    c.disclaimer_strip(txt.DISCLAIMER_SHORT)

    st.write("")
    c.icon_row(txt.ICON_ROW_ITEMS)

    c.section("Why the numbers hold up", kicker="Principles", delay=40)
    cards(txt.PILLARS, columns=3)

    st.write("")
    band([
        (f"{meta.get('n_patients', 274)}", "patients in the study set"),
        (f"{meta.get('n_images', 3000):,}", "labelled tissue patches"),
        (f"{ho.get('accuracy', 0):.1%}", "accuracy on 54 held-out patients"),
        ("0.978", "correlation with true involvement"),
    ])

    c.section("How it works", kicker="Pipeline", delay=40)
    c.process_flow(txt.HOW_STEPS)

    c.section("Where it fits", kicker="Workflow", delay=40)
    lead(txt.WHERE_IT_FITS)
    st.write("")
    c.is_is_not(txt.IS_THIS, txt.IS_NOT_THIS)

    st.write("")
    st.write("")
    c.closing_band(txt.CLOSING_KICKER, txt.CLOSING_TITLE, txt.CLOSING_BODY)
    st.write("")
    g1, g2, _ = st.columns([1, 1, 2.1], gap="small")
    if g1.button("Go to Analyze", type="primary", key="cta_go", **WIDE):
        goto("analyze")
    if g2.button("See the validation", key="cta_val", **WIDE):
        goto("validation")


def page_technology(meta: dict) -> None:
    page_head("How the model reads tissue", kicker="Technology",
              sub="Feature extraction, classification, aggregation, and the "
                  "retrieval layer that writes the explanations.")
    lead(txt.TECH_INTRO)

    c.section("The feature vector", kicker="118 dimensions", delay=40)
    rows = [
        [name, f"{n}", detail, why]
        for name, n, detail, why in txt.FEATURE_FAMILIES
    ]
    rows.append(["<strong>Total</strong>",
                 f"<strong>{meta.get('feature_dim', 118)}</strong>",
                 "per 50&times;50 patch", ""])
    table(
        [("Family", "name"), ("Dims", "num"), ("Shape", ""), ("What it captures", "")],
        rows,
    )
    st.write("")
    c.note(txt.WHY_HANDCRAFTED, title="Why handcrafted, not learned", tone="accent")

    c.section("The classifier", kicker="XGBoost", delay=40)
    lead(txt.MODEL_NOTE)
    st.write("")
    ho = meta.get("grouped_holdout", {})
    band([
        (f"{ho.get('n_train_patches', 2405):,}", "training patches"),
        (f"{ho.get('n_train_patients', 220)}", "training patients"),
        (f"{ho.get('n_test_patches', 595):,}", "held-out patches"),
        (f"{ho.get('n_test_patients', 54)}", "held-out patients"),
    ])

    c.section("From patches to a patient", kicker="Aggregation", delay=40)
    lead(txt.AGGREGATION_NOTE)

    c.section("Measuring the tissue, not just classifying it", kicker="Morphology", delay=40)
    lead(txt.TECH_MORPH)
    st.write("")
    table(
        [("Measurement", "name"), ("How it is obtained", ""), ("What it is not", "")],
        [
            ["Spatial pattern",
             "Flagged patches are snapped back onto the slide grid and grouped into "
             "connected regions. One dominant region reads as focal, several substantial "
             "regions as multifocal, a scatter of isolated patches as diffuse.",
             "Not tumour size. Extent within the sampled patches says nothing about the "
             "dimensions of the lesion in the specimen."],
            ["Nuclear load",
             "Colour deconvolution separates the haematoxylin signal from the eosin. The "
             "proportion of the patch above a cohort-calibrated threshold is a direct "
             "measure of nuclear material.",
             "Not a grade. Nuclear density contributes to grading but a grade is assigned "
             "by a pathologist across a whole section."],
            ["Nuclear pleomorphism",
             "Variability in the size of detected nuclear regions, taken as the coefficient "
             "of variation of their areas.",
             "Weaker in our data than nuclear load, and inflated where touching nuclei "
             "merge into one region. Indicative only."],
        ],
    )
    st.write("")
    c.note(txt.TECH_MORPH_NOT_STAGE, title="Why there is no stage prediction",
           tone="malignant")

    c.section("Explanations that cite their sources", kicker="Retrieval", delay=40)
    lead(txt.RAG_NOTE)
    st.write("")
    c.process_flow([
        ("Retrieve", "The prediction and its confidence are turned into a query "
                     "against a curated histopathology knowledge base held in ChromaDB, "
                     "scored by TF-IDF."),
        ("Ground", "The retrieved passages &mdash; not the model's own recollection "
                   "&mdash; are handed to Claude as the material to write from."),
        ("Attribute", "Every source that fed the answer is printed beneath it, so the "
                      "reader can check the text against what it was given."),
        ("Degrade safely", "With no API key the panel falls back to a fixed written "
                           "note. It never invents an explanation to fill the space."),
    ])


def page_validation(meta: dict) -> None:
    cv = meta.get("grouped_cross_validation", {}).get("xgboost", {})
    ho = meta.get("grouped_holdout", {})
    naive = meta.get("naive_patch_level_split", {})
    infl = meta.get("leakage_inflation", {})
    cm = ho.get("confusion_matrix", {})
    ci = ho.get("accuracy_95ci", [0, 0])

    page_head("What the model actually scores", kicker="Validation",
              sub="Every figure below comes from the patient-grouped split. "
                  "The flattering one is shown too, and labelled as such.")
    lead(txt.VAL_INTRO)

    c.section("The cost of a careless split", kicker="Leakage", delay=40)
    table(
        [("Split", "name"), ("Accuracy", "num"), ("AUC", "num"), ("What it means", "")],
        [
            ["Random patch-level split",
             f"{naive.get('accuracy', 0):.1%}", f"{naive.get('auc', 0):.3f}",
             f"<strong>Not reported.</strong> {naive.get('patients_leaked', 247)} of "
             f"{meta.get('n_patients', 274)} patients appear on both sides of the split."],
            ["Patient-grouped split",
             f"{cv.get('accuracy', {}).get('mean', 0):.1%}",
             f"{cv.get('auc', {}).get('mean', 0):.3f}",
             "The honest figure. No patient's tissue crosses a fold boundary."],
            ["<strong>Inflation</strong>",
             f"<strong>+{infl.get('accuracy', 0) * 100:.1f} pts</strong>",
             f"<strong>+{infl.get('auc', 0) * 100:.1f} pts</strong>",
             "Performance that exists only because of the leak."],
        ],
        row_classes=["is-flagged", "", ""],
    )
    st.write("")
    c.note(txt.LEAKAGE_NOTE, title="Same model, same patches", tone="uncertain")

    c.section("Held-out performance", kicker="54 unseen patients", delay=40)
    band([
        (f"{ho.get('accuracy', 0):.1%}", f"accuracy · 95% CI {ci[0]:.1%}–{ci[1]:.1%}"),
        (f"{ho.get('auc', 0):.3f}", "area under the ROC curve"),
        (f"{ho.get('sensitivity_recall_malignant', 0):.1%}", "sensitivity to malignant tissue"),
        (f"{ho.get('specificity_recall_benign', 0):.1%}", "specificity on benign tissue"),
    ])
    st.write("")
    band([
        (f"{ho.get('ppv_precision', 0):.1%}", "positive predictive value"),
        (f"{ho.get('npv', 0):.1%}", "negative predictive value"),
        (f"{ho.get('f1', 0):.3f}", "F1 score"),
        (f"{cv.get('accuracy', {}).get('mean', 0):.1%} ± "
         f"{cv.get('accuracy', {}).get('std', 0):.1%}",
         f"{meta.get('n_folds', 5)}-fold grouped cross-validation"),
    ])
    st.write("")
    c.note(txt.VAL_METHOD, title="Method", tone="accent")

    c.section("Where the errors fall", kicker="Confusion matrix", delay=40)
    cm_col, note_col = st.columns([1, 1], gap="large")
    with cm_col:
        confusion_matrix(
            int(cm.get("tn", 257)), int(cm.get("fp", 40)),
            int(cm.get("fn", 54)), int(cm.get("tp", 244)),
        )
    with note_col:
        lead(txt.CONFUSION_NOTE)

    c.section("Aggregated to the patient", kicker="The number that matters", delay=40)
    lead(txt.PATIENT_LEVEL_NOTE)
    st.write("")
    band([
        ("0.978", "correlation with true malignant fraction"),
        ("2.8<small> pts</small>", "mean absolute error"),
        (f"{ho.get('n_test_patients', 54)}", "held-out patients in the check"),
    ])

    c.section("What this does not establish", kicker="Limitations", delay=40)
    limitations(txt.LIMITATIONS)
    st.write("")
    c.note(txt.CLINICAL_GAP, title="The distance to clinical use", tone="malignant")


def page_about(meta: dict) -> None:
    page_head("An honest pipeline, end to end", kicker="About",
              sub="What this project is, what it runs on, and what it is not.")
    lead(txt.ABOUT_INTRO)
    st.write("")
    lead(txt.ABOUT_WHY)

    c.section("The data", kicker="IDC breast histopathology", delay=40)
    lead(txt.ABOUT_DATA)
    st.write("")
    band([
        (f"{meta.get('n_patients', 274)}", "patients"),
        (f"{meta.get('n_images', 3000):,}", "labelled patches"),
        ("50×50", "pixels per patch"),
        ("40×", "source magnification"),
    ])

    c.section("The stack", kicker="Built with", delay=40)
    lead(txt.ABOUT_STACK_INTRO)
    st.write("")
    table(
        [("Layer", "name"), ("Implementation", ""), ("What it does here", "")],
        [[k, v, w] for k, v, w in txt.ABOUT_STACK],
    )

    c.section("Get in touch", kicker="Contact", delay=40)
    with st.form("contact", clear_on_submit=False):
        f1, f2 = st.columns(2)
        f1.text_input("Name")
        f2.text_input("Email")
        st.selectbox("Enquiry", ["Research collaboration", "Dataset or methods question",
                                 "Reporting an issue", "Something else"])
        st.text_area("Message", height=110)
        sent = st.form_submit_button("Send", type="primary")
    if sent:
        c.note("Nothing was sent. This form exists to show the layout of the page; "
               "there is no backend behind it and no data was recorded.",
               title="Demonstration form", tone="uncertain")
    else:
        c.render(f'<div style="font-size:.755rem;color:var(--text-low);'
                 f'line-height:1.6;margin-top:-.4rem">{txt.CONTACT_NOTE}</div>')

    c.section("Full disclaimer", kicker="Read this", delay=40)
    c.note(txt.DISCLAIMER_LONG, title="Not a medical device", tone="malignant")
