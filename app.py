"""
Carmine -- computational pathology for breast tissue. Streamlit front end.

The app is structured as a five-tab site rather than a single screen:

  Overview    the landing page -- what the product claims and what it doesn't
  Technology  the feature vector, the classifier, the retrieval layer
  Analyze     the console itself, in two modes:
                * Single patch   -- score one 50x50 H&E tissue patch
                * Patient sample -- score every patch from one patient and
                                    aggregate them into slide-level triage
  Validation  the leakage story, held-out metrics, and the limitations
  About       the data, the stack, and the full disclaimer

The machine learning stack is untouched and lives in src/ (features.py,
explain.py, rag.py) with artefacts in models/. This file is presentation and
orchestration only; everything visual comes from ui/, and the four non-tool
pages are rendered by ui/site.py.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import streamlit as st
from PIL import Image
from joblib import load

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# On Streamlit Community Cloud there is no .env -- the key is supplied through
# the app's Secrets panel. src/explain.py reads os.environ, so mirror the secret
# into the environment before anything imports it. Reading st.secrets when no
# secrets file exists raises, hence the broad guard.
try:
    if not os.environ.get("ANTHROPIC_API_KEY") and "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = str(st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    pass

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(APP_DIR, "src"))

from features import extract_features, IMG_SIZE  # noqa: E402
import morphology as morph  # noqa: E402

from ui import brand, charts, components as c, copy as txt, site  # noqa: E402
from ui.compat import STRETCH, WIDE  # noqa: E402
from ui.theme import inject as inject_theme  # noqa: E402
from ui.tokens import tone_for_fraction  # noqa: E402

MODEL_DIR = os.path.join(APP_DIR, "models")
DATA_DIR = os.path.join(APP_DIR, "data", "idc_sample")
CLASS_NAMES = {0: "Benign", 1: "Malignant (IDC)"}
IMAGE_EXT = (".png", ".jpg", ".jpeg")
WORKERS = min(8, max(2, (os.cpu_count() or 2)))

st.set_page_config(
    page_title=f"{brand.NAME} · {brand.DESCRIPTOR}",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Model + metadata
# --------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def load_model():
    clf = load(os.path.join(MODEL_DIR, "classifier.joblib"))
    scaler = load(os.path.join(MODEL_DIR, "scaler.joblib"))
    return clf, scaler


@st.cache_resource(show_spinner=False)
def load_metadata() -> dict:
    path = os.path.join(MODEL_DIR, "metadata_grouped.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


@st.cache_resource(show_spinner=False)
def load_morphology_reference() -> dict:
    """Cohort reference for the morphological profile. Never raises."""
    return morph.load_reference()


@st.cache_resource(show_spinner=False)
def explanation_engine_status() -> tuple[str, str]:
    """(state, label) for the header pill. Never raises."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "off", "Explanations offline - no API key"
    try:
        from rag import retrieve
        retrieve("idc", k=1)
        return "live", "Explanations online - RAG ready"
    except Exception:
        return "warn", "Explanations degraded - knowledge base unreachable"


# --------------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------------


def image_to_features(image: Image.Image) -> np.ndarray:
    arr = np.array(image.convert("RGB").resize((IMG_SIZE, IMG_SIZE)))
    return extract_features(arr)


def predict_one(image, clf, scaler) -> tuple[int, np.ndarray]:
    feats = image_to_features(image).reshape(1, -1)
    probs = clf.predict_proba(scaler.transform(feats))[0]
    return int(np.argmax(probs)), probs


def _features_for(src) -> np.ndarray | None:
    try:
        if hasattr(src, "seek"):
            src.seek(0)
        return image_to_features(Image.open(src))
    except Exception:
        return None


def _features_and_morph(src, h_thr: float, min_px: int):
    """
    Both measurements in one pass over the file.

    Morphology costs under a millisecond per patch against roughly eighty for
    feature extraction, so it rides along inside the existing thread pool
    rather than justifying a second pass over the images.
    """
    try:
        if hasattr(src, "seek"):
            src.seek(0)
        img = Image.open(src).convert("RGB")
        rgb50 = np.array(img.resize((IMG_SIZE, IMG_SIZE)))
        feats = extract_features(rgb50)
        m = morph.nuclear_measures(rgb50, h_thr, min_px)
        return feats, m
    except Exception:
        return None, None


def predict_many(sources, clf, scaler, progress=None):
    """
    Score a list of paths and/or uploaded file objects.

    Feature extraction is the bottleneck (~45 ms/patch) and scikit-image
    releases the GIL inside its Cython kernels, so a small thread pool gives a
    near-linear speed-up on multi-core machines. Order is preserved.
    """
    ref = load_morphology_reference()
    h_thr = float(ref["h_threshold"])
    min_px = int(ref.get("min_nucleus_px", 4))

    total = len(sources)
    feats: list[np.ndarray | None] = [None] * total
    morphs: list[tuple | None] = [None] * total
    done = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(_features_and_morph, s, h_thr, min_px): i
                   for i, s in enumerate(sources)}
        for fut in as_completed(futures):
            i = futures[fut]
            feats[i], morphs[i] = fut.result()
            done += 1
            if progress is not None and (done % 8 == 0 or done == total):
                progress.update(done / total, f"Reading patch {done:,} of {total:,}")

    keep = [i for i, f in enumerate(feats) if f is not None]
    if not keep:
        return np.array([]), [], [], []

    if progress is not None:
        progress.update(1.0, "Scoring patches")

    X = np.vstack([feats[i] for i in keep])
    probs = clf.predict_proba(scaler.transform(X))[:, 1]
    names = [_display_name(sources[i], i) for i in keep]
    kept_morph = [morphs[i] for i in keep]
    return probs, names, keep, kept_morph


def _display_name(src, idx: int) -> str:
    if isinstance(src, str):
        return os.path.basename(src)
    return getattr(src, "name", f"patch_{idx}")


# --------------------------------------------------------------------------
# Ground truth recovery
# --------------------------------------------------------------------------

_CLASS_IN_NAME = re.compile(r"class([01])\b", re.IGNORECASE)


def truth_from(path_or_name, folder_label: int | None = None) -> int | None:
    """Prefer the 0/ or 1/ parent folder; fall back to the classN filename suffix."""
    if folder_label is not None:
        return folder_label
    m = _CLASS_IN_NAME.search(os.path.basename(str(path_or_name)))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------
# Explanation
# --------------------------------------------------------------------------


def get_explanation(label_str: str, confidence: float):
    try:
        from explain import generate_explanation
        text, sources = generate_explanation(label_str.lower().split()[0], confidence)
        return text, sources, None
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, never swallowed
        return None, None, str(exc)


# --------------------------------------------------------------------------
# Shell
# --------------------------------------------------------------------------

st.session_state.setdefault("ui_mode", "Light")
st.session_state.setdefault("queue", [])
st.session_state.setdefault("page", brand.DEFAULT_PAGE)

MODE = st.session_state["ui_mode"].lower()
inject_theme(MODE)


def goto(slug: str) -> None:
    """Navigate to a tab from anywhere on a page (hero CTAs, cross-links)."""
    if slug in brand.PAGE_SLUGS:
        st.session_state["page"] = slug
        st.rerun()

clf, scaler = load_model()
META = load_metadata()
ENGINE_STATE, ENGINE_LABEL = explanation_engine_status()

PAGE = st.session_state["page"]

# ---------------------------------- sidebar -------------------------------
# Only the console gets a sidebar. Streamlit omits the whole rail when nothing
# is written to it, so the four content pages render edge to edge like a site
# rather than like an app with an empty tool rail bolted to the left.
if PAGE == "analyze":
    with st.sidebar:
        c.render(
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:.2rem">'
            f'<span style="color:var(--accent)">{brand.mark(22)}</span>'
            f'<span style="font-weight:760;font-size:.98rem;color:var(--text-hi);'
            f'letter-spacing:-.038em">{brand.NAME}</span></div>'
            '<div style="font-size:.735rem;color:var(--text-low);line-height:1.5">'
            'IDC whole-slide patch screening</div>'
        )

        c.side_title("Session queue")
        queue_items = []
        for entry in st.session_state["queue"]:
            frac = float((entry["probs"] >= entry["threshold"]).mean())
            queue_items.append({
                "id": entry["label"], "n": entry["n"],
                "fraction": frac, "tone": tone_for_fraction(frac),
            })
        queue_items.sort(key=lambda d: -d["fraction"])
        c.queue_list(queue_items)
        if queue_items:
            if st.button("Clear queue", **WIDE):
                st.session_state["queue"] = []
                st.rerun()

        c.side_title("Model card")
        cv = META.get("grouped_cross_validation", {}).get("xgboost", {})
        ho = META.get("grouped_holdout", {})
        c.kv_list([
            ("Algorithm", "XGBoost"),
            ("Features", f"{META.get('feature_dim', 118)} handcrafted"),
            ("Patients", f"{META.get('n_patients', '--')}"),
            ("CV accuracy", f"{cv.get('accuracy', {}).get('mean', 0):.1%}"
                            f" ± {cv.get('accuracy', {}).get('std', 0):.1%}"),
            ("CV AUC", f"{cv.get('auc', {}).get('mean', 0):.3f}"),
            ("Held-out acc.", f"{ho.get('accuracy', 0):.1%}"),
            ("Sensitivity", f"{ho.get('sensitivity_recall_malignant', 0):.1%}"),
            ("Specificity", f"{ho.get('specificity_recall_benign', 0):.1%}"),
            ("Split", "Patient-grouped"),
            ("Compute", "CPU only"),
        ])

        c.side_title("Full disclaimer")
        with st.expander("Read before use", expanded=False):
            st.markdown(
                f'<div style="font-size:.8rem;line-height:1.65;color:var(--text-mid)">'
                f'{txt.DISCLAIMER_LONG}</div>', unsafe_allow_html=True)

# ---------------------------------- site chrome ---------------------------
site.header(pills=[
    ("live", f"Classifier loaded · {META.get('feature_dim', 118)} features"),
    (ENGINE_STATE, ENGINE_LABEL),
    ("live", f"{WORKERS} worker{'s' if WORKERS > 1 else ''} · CPU"),
])

_clicked = site.nav(st.session_state["page"])
if _clicked and _clicked != st.session_state["page"]:
    st.session_state["page"] = _clicked
    st.rerun()

PAGE = st.session_state["page"]


# ==========================================================================
# ANALYZE -- MODE 1: SINGLE PATCH
# ==========================================================================

def render_single_patch() -> None:
    c.section("Classify one tissue patch", kicker="Spot check", note=txt.SINGLE_INTRO,
              help=txt.HELP["single"])

    left, right = st.columns([1, 1.55], gap="large")

    with left:
        uploaded = st.file_uploader(
            "Histopathology patch",
            type=["png", "jpg", "jpeg"], key="single",
            help="A 50x50 H&E-stained tissue patch. Larger images are resized.",
        )
        b1, b2 = st.columns(2)
        example_clicked = None
        if b1.button("Example · benign", **WIDE):
            example_clicked = "0"
        if b2.button("Example · IDC", **WIDE):
            example_clicked = "1"

    image, image_caption = None, ""
    if uploaded is not None:
        image, image_caption = Image.open(uploaded), uploaded.name
    elif example_clicked is not None:
        ex_dir = os.path.join(DATA_DIR, example_clicked)
        if os.path.isdir(ex_dir):
            files = sorted(f for f in os.listdir(ex_dir) if f.lower().endswith(IMAGE_EXT))
            if files:
                pick = files[np.random.default_rng().integers(len(files))]
                image = Image.open(os.path.join(ex_dir, pick))
                image_caption = pick

    if image is None:
        with left:
            st.write("")
            c.empty_state(
                "No patch loaded",
                "Upload an image, or load one of the labelled examples to see the "
                "full read-out.",
            )
    else:
        with left:
            st.image(image.resize((260, 260), Image.NEAREST), caption=image_caption, width=260)

        with right:
            with st.spinner("Extracting features and scoring..."):
                label, probs = predict_one(image, clf, scaler)

            label_str = CLASS_NAMES[label]
            confidence = float(probs[label])
            tone = "malignant" if label == 1 else "benign"
            if 0.4 < float(probs[1]) < 0.6:
                tone = "uncertain"

            c.verdict_card(
                label_str, confidence, tone,
                "Model probability, not clinical certainty.",
            )
            st.write("")
            c.probability_split(float(probs[0]), float(probs[1]))
            st.write("")
            c.note(txt.SINGLE_WEAK_EVIDENCE, title="Read this before trusting it",
                   tone="uncertain", delay=260)

        # No extent reading here, by design. Extent is a proportion of a
        # sample, and one patch is not a proportion of itself. Putting a band
        # on a single patch would be inventing the very quantity the whole
        # ladder is meant to report honestly.
        if label == 1:
            c.note(txt.SINGLE_NO_EXTENT, title="No extent reading for one patch",
                   tone="uncertain", delay=120)
            st.write("")

        c.section("Plain-language explanation", kicker="Grounded generation", delay=60,
                  help=txt.HELP["explanation"])
        with st.spinner("Retrieving reference passages and generating..."):
            text, sources, error = get_explanation(label_str, confidence)

        if error:
            c.explanation_panel(
                txt.EXPLANATION_FALLBACK.format(label=label_str, conf=f"{confidence:.0%}"),
                sources=None, unavailable=True,
            )
            with st.expander("Why the live explanation is unavailable"):
                st.code(error)
        else:
            c.explanation_panel(text, sources)


# ==========================================================================
# ANALYZE -- MODE 2: WHOLE PATIENT SAMPLE
# ==========================================================================


_PATIENT_ID = re.compile(r"^([A-Za-z0-9]+)_")


def patient_ids(names) -> set:
    """
    Distinct patient identifiers among a set of filenames.

    IDC filenames start with the patient id. A folder holding more than one of
    them is not a specimen, and aggregating across it produces a cohort average
    dressed up as a patient result.
    """
    out = set()
    for n in names:
        m = _PATIENT_ID.match(os.path.basename(str(n)))
        if m:
            out.add(m.group(1))
    return out


def scan_folder(folder: str) -> list:
    """
    Every image in the folder tree, with whatever label its path carries.

    Kept separate from the cap so the interface can report a true total
    before asking anyone to choose a sample size.
    """
    found = []
    for dirpath, _, filenames in os.walk(folder):
        parent = os.path.basename(dirpath)
        folder_label = int(parent) if parent in ("0", "1") else None
        for fn in sorted(filenames):
            if fn.lower().endswith(IMAGE_EXT):
                full = os.path.join(dirpath, fn)
                found.append((full, truth_from(full, folder_label)))
    return found


def apply_cap(found: list, max_n: int) -> tuple[list, bool]:
    """Random subsample to at most max_n. Seeded, so a rerun is reproducible."""
    if not max_n or len(found) <= max_n:
        return found, False
    rng = np.random.default_rng(42)
    pick = sorted(rng.choice(len(found), int(max_n), replace=False))
    return [found[i] for i in pick], True


def patch_readout(total: int, labelled: int, n_patients: int, noun: str) -> None:
    """The count, shown before any control that depends on knowing it."""
    bits = [f"{labelled:,} carry labels" if labelled else "no labels in filenames"]
    bits.append(f"{n_patients} patient" + ("s" if n_patients != 1 else ""))
    c.render(
        f'<div class="hp-rail-read"><span class="k">{c._e(noun)}</span>'
        f'<span class="v">{total:,}</span></div>'
        f'<div class="hp-rail-sub">{" &middot; ".join(bits)}</div>'
    )


def patch_cap(total: int) -> int:
    """
    The sample cap, offered only once the total is known and shown.

    Defaults to analysing everything for samples small enough that it costs
    nothing, and to a few hundred above that, where a random subsample lands
    within a point or two of the full answer.
    """
    default = 0 if total <= 600 else 400
    return int(st.number_input(
        f"Max patches to analyse (0 = all {total:,})",
        min_value=0, max_value=int(total), value=default, step=100,
        help="Large patients run to thousands of patches. A random sample of a few "
             "hundred lands within a point or two of the full answer, and the "
             "sample is seeded so a rerun gives the same result.",
    ))


def patient_controls(res: dict | None) -> None:
    """
    The left rail: what the operator sets, and a live read of what it does.

    Kept separate from render_patient_results so that one column holds inputs
    and the other holds the outputs those inputs drive.
    """
    if res is None:
        return
    probs = res["probs"]
    st.write("")
    c.render('<div class="hp-rail-title">Decision threshold'
             + c.info(txt.HELP["threshold"]) + '</div>')
    st.slider(
        "Threshold for calling a patch malignant",
        0.05, 0.95, float(res["threshold"]), 0.05,
        key="thr_live", label_visibility="collapsed", **STRETCH,
    )
    thr = float(st.session_state.get("thr_live", res["threshold"]))
    n_flag = int((probs >= thr).sum())
    c.render(
        f'<div class="hp-rail-read"><span class="k">flagged</span>'
        f'<span class="v">{n_flag / len(probs):.1%}</span></div>'
        f'<div class="hp-rail-sub">{n_flag:,} of {len(probs):,} patches '
        f'at threshold {thr:.2f}</div>'
    )


def render_patient_results(res: dict) -> None:
    probs = res["probs"]
    names = res["names"]
    truths = res["truths"]

    # The slider itself lives in the left rail; this reads what it is set to.
    threshold = float(st.session_state.get("thr_live", res["threshold"]))
    res["threshold"] = threshold

    flagged = probs >= threshold
    frac = float(flagged.mean())
    tone = tone_for_fraction(frac)
    spec = txt.TRIAGE[tone]

    c.section("Triage assessment", kicker=f"Patient {res['label']}", delay=40,
              help=txt.HELP["triage"])
    c.triage_banner(frac, tone, spec["headline"], spec["action"])

    # ---- extent of involvement ----
    # The headline reading, on the one ordinal scale in the product. Its band
    # boundaries at 15% and 50% are the triage boundaries, so this and the
    # banner above are two readings of a single quantity. It is not a stage,
    # and the reference block immediately below says what a stage actually is.
    st.write("")
    c.section("How much tissue is involved", kicker="Extent",
              note=txt.EXTENT_INTRO, delay=40, help=txt.HELP["extent"])
    c.involvement_ladder(frac, int(flagged.sum()), len(probs), threshold,
                         txt.EXTENT_MEANING, help_html=c.info(txt.HELP["extent"]))
    st.write("")
    c.note(txt.EXTENT_NOT_STAGE, title="Read this before quoting the band",
           tone="uncertain", delay=60)
    st.write("")
    c.staging_reference(txt.STAGING_REF, txt.STAGING_REF_WHY,
                        intro=txt.STAGING_REF_INTRO,
                        help_html=c.info(txt.HELP["staging_ref"]))

    st.write("")
    c.is_is_not(txt.IS_THIS, txt.IS_NOT_THIS)

    st.write("")
    c.stat_tiles([
        {"label": "Patches analysed", "value": f"{len(probs):,}",
         "sub": f"of {res['found']:,} found" if res["sampled"] else "complete sample",
         "tone_value": False},
        {"label": "Flagged malignant", "value": f"{int(flagged.sum()):,}",
         "sub": f"{frac:.1%} of sampled tissue", "tone": tone, "sub_tone": True},
        {"label": "Mean malignancy score", "value": f"{probs.mean():.3f}",
         "sub": f"median {np.median(probs):.3f}", "tone_value": False},
    ], columns=3)

    # ---- distribution + spatial map ----
    show_map = charts.has_coordinates(names)
    c.section("Where the evidence sits", kicker="Transparency", delay=40)

    if show_map:
        col_a, col_b = st.columns([1, 1], gap="large")
    else:
        col_a, col_b = st.container(), None

    with col_a:
        c.render('<div style="font-size:.78rem;font-weight:620;color:var(--text-hi);'
                 'margin-bottom:.15rem">Score distribution'
                 + c.info(txt.HELP["distribution"]) + '</div>')
        st.plotly_chart(
            charts.score_distribution(probs, threshold, MODE),
            config=charts.PLOT_CONFIG, key="dist_chart", **WIDE,
        )
        pass

    if col_b is not None:
        with col_b:
            c.render('<div style="font-size:.78rem;font-weight:620;color:var(--text-hi);'
                     'margin-bottom:.15rem">Spatial tissue map'
                     + c.info(txt.HELP["spatial"]) + '</div>')
            fig = charts.spatial_map(names, probs, MODE)
            if fig is not None:
                st.plotly_chart(fig, config=charts.PLOT_CONFIG,
                                key="spatial_chart", **WIDE)
                pass

    # ---- confidence composition ----
    st.write("")
    conf_mal = int((probs >= 0.9).sum())
    conf_ben = int((probs <= 0.1).sum())
    ambiguous = int(((probs > 0.4) & (probs < 0.6)).sum())
    c.section("How sure was it?", kicker="Confidence composition", delay=40,
              help=txt.HELP["confidence"])
    c.stat_tiles([
        {"label": "Confidently malignant", "value": f"{conf_mal:,}",
         "sub": f"score ≥ 0.90 · {conf_mal / len(probs):.0%}", "tone": "malignant"},
        {"label": "Confidently benign", "value": f"{conf_ben:,}",
         "sub": f"score ≤ 0.10 · {conf_ben / len(probs):.0%}", "tone": "benign"},
        {"label": "Genuinely ambiguous", "value": f"{ambiguous:,}",
         "sub": f"score 0.40-0.60 · {ambiguous / len(probs):.0%}", "tone": "uncertain"},
    ], columns=3)

    # ---- morphological profile ----
    # Supporting detail, below the headline reading rather than beside it.
    # Two gates before any of it is meaningful.
    #
    # Nothing flagged means there is no suspicious tissue to characterise, and
    # measuring the appearance of tissue the model called benign would be
    # describing something that is not there.
    #
    # More than one patient in the input means every measurement below is a
    # cohort average, which describes no specimen at all.
    n_pat = int(res.get("n_patients", 1) or 1)
    n_flagged = int(flagged.sum())

    if n_pat > 1:
        c.section("A closer look at the flagged tissue", kicker="Supporting detail", delay=40)
        c.note(f"Not shown. The input holds patches from <strong>{n_pat}</strong> "
               f"patients, so these measurements would describe a cohort average "
               f"rather than a specimen. Analyse one patient at a time.",
               title="Multiple patients in one input", tone="malignant")
        st.write("")
        morphs = None
    elif n_flagged == 0:
        c.section("A closer look at the flagged tissue", kicker="Supporting detail", delay=40)
        c.note("Not shown. No patch in this sample was flagged at the current "
               "threshold, so there is no suspicious tissue to describe. Lower the "
               "threshold to see whether anything sits just below it.",
               title="No malignant tissue detected", tone="benign")
        st.write("")
        morphs = None
    else:
        morphs = res.get("morphs")

    if morphs:
        ref = load_morphology_reference()
        prof = morph.patient_profile(morphs, names, flagged, ref)
        if prof.get("available"):
            c.section("A closer look at the flagged tissue", kicker="Supporting detail",
                      note=txt.MORPH_INTRO, delay=40, help=txt.HELP["morphology"])

            blocks = []
            if "focality" in prof:
                f = prof["focality"]
                lab, p = morph.top_label(f)
                blocks.append({
                    "title": txt.MORPH_TITLES[0],
                    "labels": f["labels"], "probs": f["probs"],
                    "reading": f"{lab} · {p:.0%}",
                    "detail": txt.MORPH_FOCALITY,
                    "help": txt.HELP["focality"],
                    "measure": (f'{f["regions"]} region'
                                f'{"s" if f["regions"] != 1 else ""}  /  largest holds '
                                f'{f["largest_share"]:.0%}  /  {f["flagged_cells"]} flagged cells'),
                })
            lo = prof["load"]
            lab, p = morph.top_label(lo)
            blocks.append({
                "title": txt.MORPH_TITLES[1],
                "labels": lo["labels"], "probs": lo["probs"],
                "reading": f"{lab} · {p:.0%}",
                "detail": txt.MORPH_LOAD,
                "help": txt.HELP["load"],
                "measure": (f'measured {lo["value"]:.3f}  /  cohort tertiles '
                            f'{lo["thresholds"][0]:.3f} and {lo["thresholds"][1]:.3f}'),
            })
            pl = prof["pleomorphism"]
            lab, p = morph.top_label(pl)
            blocks.append({
                "title": txt.MORPH_TITLES[2],
                "labels": pl["labels"], "probs": pl["probs"],
                "reading": f"{lab} · {p:.0%}",
                "detail": txt.MORPH_PLEO,
                "help": txt.HELP["pleomorphism"],
                "measure": (f'measured {pl["value"]:.3f}  /  cohort tertiles '
                            f'{pl["thresholds"][0]:.3f} and {pl["thresholds"][1]:.3f}'),
            })

            if prof.get("calibrated"):
                note = (f'<b>Not a stage and not a grade.</b>'
                        f'{c.info(txt.HELP["not_stage"])} Bands are tertiles of our '
                        f'{prof.get("cohort_size", 0)}-patient cohort. Measured on '
                        f'{prof["n_measured"]:,} flagged patch'
                        f'{"es" if prof["n_measured"] != 1 else ""}.')
            else:
                note = txt.MORPH_UNCALIBRATED
            c.morphology_profile(blocks, note)
            st.write("")

    # ---- ground truth ----
    known = [(p, t) for p, t in zip(probs, truths) if t is not None]
    if known:
        kp = np.array([p for p, _ in known])
        kt = np.array([t for _, t in known])
        true_frac = float(kt.mean())
        acc = float(((kp >= threshold).astype(int) == kt).mean())
        err = frac - true_frac
        # Wording matters here. The model is not predicting anything about the
        # patient: it is estimating a proportion, and these particular files
        # happen to carry the answer, so the estimate can be marked. "Actual"
        # and "Model estimate" say that; "Predicted" did not.
        c.section("Marking the model's own work", kicker="Self-check",
                  note=txt.GROUND_TRUTH_NOTE, delay=40, help=txt.HELP["ground_truth"])
        c.stat_tiles([
            {"label": "Actual (from filename labels)", "value": f"{true_frac:.1%}",
             "sub": f"{len(known):,} labelled patches", "tone_value": False},
            {"label": "Model estimate", "value": f"{frac:.1%}",
             "sub": f"{err * 100:+.1f} points from actual",
             "tone": "benign" if abs(err) <= 0.05 else "uncertain", "sub_tone": True},
            {"label": "Per-patch agreement", "value": f"{acc:.1%}",
             "sub": "with the labels, on this patient", "tone_value": False},
        ], columns=3)

    # ---- evidence gallery ----
    gallery = res.get("gallery")
    if gallery:
        c.section("The patches behind the number", kicker="Evidence",
                  note=txt.EVIDENCE_NOTE, delay=40, help=txt.HELP["evidence"])
        order = np.argsort(-probs)
        top = [(gallery[i], float(probs[i])) for i in order[:14] if i in gallery]
        bottom = [(gallery[i], float(probs[i])) for i in order[-7:] if i in gallery]
        if top:
            c.render('<div style="font-size:.7rem;font-weight:650;letter-spacing:.12em;'
                     'text-transform:uppercase;color:var(--text-mid);margin:.2rem 0 .45rem">'
                     'Most suspicious</div>')
            c.evidence_gallery(top, threshold)
        if bottom:
            c.render('<div style="font-size:.7rem;font-weight:650;letter-spacing:.12em;'
                     'text-transform:uppercase;color:var(--text-mid);margin:1rem 0 .45rem">'
                     'Least suspicious</div>')
            c.evidence_gallery(bottom, threshold)

    # ---- table + export ----
    st.write("")
    with st.expander(f"Per-patch results  ·  {len(probs):,} rows"):
        import pandas as pd
        tbl = pd.DataFrame({
            "file": names,
            "malignancy_score": np.round(probs, 4),
            "call": np.where(flagged, "Malignant", "Benign"),
            "label": ["-" if t is None else CLASS_NAMES[t] for t in truths],
        }).sort_values("malignancy_score", ascending=False)
        st.dataframe(tbl, height=340, hide_index=True, **WIDE)
        st.download_button(
            "Download results as CSV",
            tbl.to_csv(index=False).encode(),
            file_name=f"patient_{res['label']}_patch_results.csv",
            mime="text/csv",
        )

    st.write("")


def patient_inputs() -> tuple:
    """
    Everything the operator sets. Returns whatever is needed to run.

    Lives in the left rail with the threshold, so that one column holds the
    inputs and the other holds what they produce.
    """
    source_mode = st.radio(
        "Patch source",
        ["Point at a folder", "Upload files"],
        key="patient_source", label_visibility="collapsed", **STRETCH,
    )

    sources: list = []
    truths: list = []
    patient_label = ""
    n_found = 0
    was_sampled = False

    # The count comes before every control that depends on it. Asking someone
    # to cap a sample at N patches before telling them how many there are is
    # asking them to guess, so the scan runs first and the cap is offered
    # afterwards with the total already on screen.
    if source_mode.startswith("Point"):
        folder = st.text_input(
            "Patient folder path",
            placeholder=os.path.join(DATA_DIR),
            help="Sub-folders are searched too, so a patient folder containing "
                 "0/ and 1/ works directly and brings its labels with it.",
        )

        if folder:
            folder = os.path.expanduser(folder.strip().strip('"'))
            if not os.path.isdir(folder):
                c.note(f"No folder at <code>{folder}</code>.", title="Path not found",
                       tone="malignant")
            else:
                every = scan_folder(folder)
                if not every:
                    c.note("No PNG or JPG images here.", title="Nothing to analyse",
                           tone="uncertain")
                else:
                    total = len(every)
                    labelled = sum(t is not None for _, t in every)
                    pids = patient_ids([p for p, _ in every])
                    patch_readout(total, labelled, len(pids), "patches found")

                    if len(pids) > 1:
                        c.note(
                            f"This folder holds patches from <strong>{len(pids)}</strong> "
                            f"different patients. Averaging them produces a cohort "
                            f"average, not a specimen result. Point at one patient's "
                            f"folder instead.",
                            title=f"{len(pids)} patients in one folder",
                            tone="malignant")

                    max_n = patch_cap(total)
                    found, was_sampled = apply_cap(every, max_n)
                    sources = [p for p, _ in found]
                    truths = [t for _, t in found]
                    patient_label = os.path.basename(os.path.normpath(folder)) or "patient"
                    n_found = total
                    msg = (f"Analysing <strong>{len(sources):,}</strong> of "
                           f"{total:,}, sampled at random."
                           if was_sampled else
                           f"Analysing all <strong>{len(sources):,}</strong>.")
                    c.note(msg, title="Ready", tone="benign")
    else:
        multi = st.file_uploader(
            "Select every patch for one patient",
            type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="multi",
        )
        if multi:
            every = [(f, truth_from(f.name)) for f in multi]
            total = len(every)
            labelled = sum(t is not None for _, t in every)
            pids = patient_ids([getattr(f, "name", "") for f in multi])
            patch_readout(total, labelled, len(pids), "files selected")

            if len(pids) > 1:
                c.note(
                    f"These files hold patches from <strong>{len(pids)}</strong> "
                    f"different patients. Averaging them produces a cohort average, "
                    f"not a specimen result. Upload one patient at a time.",
                    title=f"{len(pids)} patients in one selection", tone="malignant")

            max_n = patch_cap(total)
            found, was_sampled = apply_cap(every, max_n)
            sources = [f for f, _ in found]
            truths = [t for _, t in found]
            patient_label = "uploaded sample"
            n_found = total
            msg = (f"Analysing <strong>{len(sources):,}</strong> of {total:,}, "
                   f"sampled at random."
                   if was_sampled else
                   f"Analysing all <strong>{len(sources):,}</strong>.")
            c.note(msg, title="Ready", tone="benign")

    st.write("")
    run = st.button("Analyse patient sample", type="primary",
                    disabled=not sources, **WIDE)
    return run, sources, truths, patient_label, n_found, was_sampled


def render_patient_sample() -> None:
    c.section("Analyse every patch from one patient", kicker="Slide-level triage",
              note=txt.PATIENT_INTRO, help=txt.HELP["patient"])

    # Controls left, outputs right. The rail is made sticky in the stylesheet,
    # so the threshold stays on screen while the results scroll past it.
    with st.container(key="console"):
        rail, out = st.columns([1, 2.15], gap="large")

    with rail:
        run, sources, truths, patient_label, n_found, was_sampled = patient_inputs()

    if run and sources:
        with out:
            holder = st.empty()
            progress = c.ScanProgress(holder, "Preparing patches")
            probs, names, kept, morphs = predict_many(sources, clf, scaler, progress)
            progress.clear()

            if len(probs) == 0:
                c.note("None of the selected files could be read as images.",
                       title="Nothing scored", tone="malignant")
            else:
                kept_truths = [truths[i] for i in kept]
                order = np.argsort(-probs)
                wanted = set(order[:14].tolist()) | set(order[-7:].tolist())
                gallery = {i: sources[kept[i]] for i in wanted}

                result = {
                    "probs": probs, "names": names, "truths": kept_truths,
                    "label": patient_label or "patient", "n": len(probs),
                    "found": n_found, "sampled": was_sampled,
                    "threshold": float(st.session_state.get("thr_live", 0.50)),
                    "gallery": gallery, "morphs": morphs,
                    "n_patients": len(patient_ids(names)),
                }
                st.session_state["patient_result"] = result

                queue = [q for q in st.session_state["queue"]
                         if q["label"] != result["label"]]
                queue.append({"label": result["label"], "probs": probs,
                              "n": len(probs), "threshold": result["threshold"]})
                st.session_state["queue"] = queue[-12:]

    result = st.session_state.get("patient_result")

    # The threshold control is drawn after the run so it can report against
    # real scores, but it sits in the rail above the outputs it drives.
    with rail:
        patient_controls(result)

    with out:
        if result:
            render_patient_results(result)
            for q in st.session_state["queue"]:
                if q["label"] == result["label"]:
                    q["threshold"] = result["threshold"]
        elif not sources:
            c.empty_state(
                "No patient loaded",
                "Point at a folder of patches or upload them, then run the analysis. "
                "The bundled sample at data/idc_sample is a good first test.",
                icon="grid",
            )


def page_analyze() -> None:
    """The console. Identity lives in the brand bar, so this page just works."""
    site.page_head("Triage console", kicker="Analyze", sub=txt.SUBTITLE)
    c.disclaimer_strip(txt.DISCLAIMER_SHORT)
    st.write("")

    tab_single, tab_patient = st.tabs(["Single patch", "Whole patient sample"])
    with tab_single:
        render_single_patch()
    with tab_patient:
        render_patient_sample()


# ==========================================================================
# Router
# ==========================================================================

if PAGE == "overview":
    site.page_overview(META, goto)
elif PAGE == "technology":
    site.page_technology(META)
elif PAGE == "analyze":
    page_analyze()
elif PAGE == "validation":
    site.page_validation(META)
elif PAGE == "about":
    site.page_about(META)
else:                                    # unknown slug in session state
    st.session_state["page"] = brand.DEFAULT_PAGE
    st.rerun()

site.footer(txt.FOOTER)
