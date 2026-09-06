"""
Streamlit app for breast cancer histopathology classification.

Two modes:
  1. Single patch  - classify one 50x50 tissue patch
  2. Patient sample - upload every patch from one patient and aggregate them
                      into a slide-level summary

Run with:
    streamlit run app.py
"""

import os
import sys

import numpy as np
import streamlit as st
from PIL import Image
from joblib import load

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from features import extract_features, IMG_SIZE  # noqa: E402

st.set_page_config(page_title="Breast Cancer Histopathology Classifier",
                   page_icon="microscope", layout="centered")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
CLASS_NAMES = {0: "Benign", 1: "Malignant (IDC)"}

BLUE = "#2a78d6"
ORANGE = "#eb6834"


@st.cache_resource
def load_model():
    clf = load(os.path.join(MODEL_DIR, "classifier.joblib"))
    scaler = load(os.path.join(MODEL_DIR, "scaler.joblib"))
    return clf, scaler


def image_to_features(image):
    arr = np.array(image.convert("RGB").resize((IMG_SIZE, IMG_SIZE)))
    return extract_features(arr)


def predict_one(image, clf, scaler):
    feats = image_to_features(image).reshape(1, -1)
    probs = clf.predict_proba(scaler.transform(feats))[0]
    return int(np.argmax(probs)), probs


def predict_many(files, clf, scaler, progress_bar=None, status=None):
    feats, names = [], []
    total = len(files)
    for i, f in enumerate(files):
        try:
            img = Image.open(f)
            feats.append(image_to_features(img))
            names.append(os.path.basename(f) if isinstance(f, str)
                         else getattr(f, "name", str(i)))
        except Exception:
            continue
        if progress_bar is not None and (i % 5 == 0 or i == total - 1):
            progress_bar.progress((i + 1) / total)
            if status is not None:
                status.caption(f"Analysing patch {i + 1} of {total} ...")
    if not feats:
        return np.array([]), []
    X = np.vstack(feats)
    return clf.predict_proba(scaler.transform(X))[:, 1], names


def get_explanation(label_str, confidence):
    try:
        from explain import generate_explanation
        text, sources = generate_explanation(label_str.lower().split()[0], confidence)
        return text, sources, None
    except Exception as e:
        return None, None, str(e)


def probability_histogram(probs, threshold):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 2.8), dpi=160)
    bins = np.linspace(0, 1, 21)
    below = probs[probs < threshold]
    above = probs[probs >= threshold]
    ax.hist(below, bins=bins, color=BLUE, edgecolor="white", linewidth=0.8,
            label=f"Looks benign ({len(below)})")
    ax.hist(above, bins=bins, color=ORANGE, edgecolor="white", linewidth=0.8,
            label=f"Looks malignant ({len(above)})")
    ax.axvline(threshold, color="#52514e", linestyle="--", linewidth=1.2)
    ax.set_xlabel("Malignancy score for each patch", fontsize=9, color="#52514e")
    ax.set_ylabel("Number of patches", fontsize=9, color="#52514e")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.yaxis.grid(True, color="#e4e3df", linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(left=False, bottom=False, labelsize=8, colors="#52514e")
    ax.legend(frameon=False, fontsize=8, loc="upper center",
              bbox_to_anchor=(0.5, -0.28), ncol=2)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------

st.title("Breast Cancer Histopathology Classifier")
st.caption(
    "Classifies H&E-stained tissue patches from Whole Slide Images as Benign or "
    "Malignant (IDC). Trained on a patient-grouped sample of the IDC breast "
    "histopathology dataset. Runs entirely on CPU."
)

with st.expander("Important disclaimer", expanded=False):
    st.warning(
        "This tool is an educational project, not a medical device. Predictions "
        "are made on small image patches, not full clinical slides, and can be "
        "wrong. Never use this for real diagnosis or treatment decisions. Always "
        "consult a qualified pathologist or oncologist."
    )

clf, scaler = load_model()

tab1, tab2 = st.tabs(["Single patch", "Whole patient sample"])

# ======================= TAB 1: SINGLE PATCH ==========================
with tab1:
    st.subheader("Classify one tissue patch")

    uploaded = st.file_uploader(
        "Upload a histopathology patch (PNG/JPG, ideally 50x50 H&E-stained tissue)",
        type=["png", "jpg", "jpeg"], key="single",
    )

    c1, c2 = st.columns(2)
    example_clicked = None
    with c1:
        if st.button("Try an example: benign patch"):
            example_clicked = "0"
    with c2:
        if st.button("Try an example: IDC patch"):
            example_clicked = "1"

    image = None
    if uploaded is not None:
        image = Image.open(uploaded)
    elif example_clicked is not None:
        ex_dir = os.path.join(os.path.dirname(__file__), "data", "idc_sample", example_clicked)
        if os.path.isdir(ex_dir):
            files = [f for f in os.listdir(ex_dir) if f.lower().endswith(".png")]
            if files:
                image = Image.open(os.path.join(ex_dir, files[0]))

    if image is not None:
        st.image(image, caption="Input patch", width=200)

        with st.spinner("Analysing patch..."):
            label, probs = predict_one(image, clf, scaler)

        label_str = CLASS_NAMES[label]
        confidence = float(probs[label])

        st.subheader("Prediction")
        if label == 1:
            st.error(f"**{label_str}**  (confidence: {confidence:.1%})")
        else:
            st.success(f"**{label_str}**  (confidence: {confidence:.1%})")
        st.progress(confidence)
        st.caption(f"Benign probability: {probs[0]:.1%}  |  "
                   f"Malignant (IDC) probability: {probs[1]:.1%}")

        st.info(
            "A single patch is a very small piece of evidence. For a more "
            "reliable read, use the **Whole patient sample** tab to analyse "
            "many patches from the same patient at once."
        )

        st.subheader("AI Explanation")
        with st.spinner("Generating explanation..."):
            text, sources, error = get_explanation(label_str, confidence)

        if error:
            st.info(
                "Live AI explanation is unavailable right now. Showing a general "
                f"note instead:\n\nThe model predicted **{label_str}** with "
                f"{confidence:.1%} confidence. This is a patch-level prediction "
                "from an experimental model, not a diagnosis. Please consult a "
                "qualified medical professional for any real concerns."
            )
            with st.expander("Error details (for debugging)"):
                st.code(error)
        else:
            st.write(text)
            with st.expander("Reference sources used (RAG)"):
                for s in sources:
                    st.markdown(f"- {s}")
    else:
        st.info("Upload an image or click one of the example buttons above.")

# ==================== TAB 2: WHOLE PATIENT SAMPLE =====================
with tab2:
    st.subheader("Analyse every patch from one patient")
    st.markdown(
        "Select all the images from a single patient folder. The app classifies "
        "each patch, then aggregates them into one slide-level summary.\n\n"
        "**Why this is more reliable than a single patch:** individual patch "
        "errors are roughly symmetric, so they largely cancel out when averaged. "
        "Validated on 54 held-out patients, the aggregated estimate of how much "
        "tissue is malignant correlates with the truth at **r = 0.978**, with a "
        "mean absolute error of **2.8 percentage points**."
    )

    mode = st.radio(
        "How do you want to select the patches?",
        ["Point at a folder on this computer (recommended)", "Upload files"],
        key="mode",
    )

    sources, truths, label = [], [], ""

    if mode.startswith("Point"):
        folder = st.text_input(
            "Folder path",
            placeholder=r"C:\Dataset ML\9265",
            help="Paste the patient folder path. Sub-folders are searched too, so "
                 r"C:\Dataset ML\9265 picks up both the 0 and 1 sub-folders.",
        )
        max_n = st.number_input(
            "Maximum patches to analyse (0 = all)", min_value=0, value=400, step=100,
            help="Some patients have thousands of patches. A random sample of a few "
                 "hundred gives a very similar answer much faster.",
        )
        if folder:
            if not os.path.isdir(folder):
                st.error(f"No folder found at: {folder}")
            else:
                found = []
                for dirpath, _, filenames in os.walk(folder):
                    parent = os.path.basename(dirpath)
                    t = int(parent) if parent in ("0", "1") else None
                    for fn in filenames:
                        if fn.lower().endswith((".png", ".jpg", ".jpeg")):
                            found.append((os.path.join(dirpath, fn), t))
                if not found:
                    st.error("No images found in that folder.")
                else:
                    st.success(f"Found {len(found)} images.")
                    if max_n and len(found) > max_n:
                        rng = np.random.default_rng(42)
                        pick = sorted(rng.choice(len(found), int(max_n), replace=False))
                        found = [found[i] for i in pick]
                        st.caption(f"Randomly sampled {len(found)} of them for speed.")
                    sources = [p for p, _ in found]
                    truths = [t for _, t in found]
                    label = os.path.basename(os.path.normpath(folder))
    else:
        multi = st.file_uploader(
            "Select all patches for one patient (Ctrl+A inside the folder selects everything)",
            type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="multi",
        )
        if multi:
            st.caption(f"{len(multi)} files selected.")
            sources = multi
            truths = [None] * len(multi)

    threshold = st.slider(
        "Decision threshold for calling a patch malignant", 0.05, 0.95, 0.50, 0.05,
        help="Lower this to catch more cancerous patches at the cost of more false alarms.",
    )

    if sources:
        run = st.button("Analyse patient sample", type="primary")

        if run:
            bar = st.progress(0.0)
            status = st.empty()
            probs, names = predict_many(sources, clf, scaler, bar, status)
            bar.empty()
            status.empty()

            if len(probs) == 0:
                st.error("None of the selected files could be read as images.")
            else:
                flagged = probs >= threshold
                frac = float(flagged.mean())
                mean_p = float(probs.mean())

                st.subheader("Patient-level summary")

                m1, m2, m3 = st.columns(3)
                m1.metric("Patches analysed", f"{len(probs)}")
                m2.metric("Flagged malignant", f"{int(flagged.sum())}",
                          f"{frac:.1%} of tissue")
                m3.metric("Mean malignancy score", f"{mean_p:.3f}")

                st.markdown("#### Triage assessment")
                if frac >= 0.50:
                    st.error(
                        f"**HIGH PRIORITY REVIEW.** An estimated **{frac:.1%}** of the "
                        "sampled tissue shows features consistent with IDC. This is "
                        "extensive involvement. Route to the front of the pathologist "
                        "review queue."
                    )
                elif frac >= 0.15:
                    st.warning(
                        f"**STANDARD REVIEW.** An estimated **{frac:.1%}** of the sampled "
                        "tissue shows features consistent with IDC. Suspicious regions "
                        "are present and require pathologist confirmation."
                    )
                else:
                    st.success(
                        f"**LOW PRIORITY REVIEW.** An estimated **{frac:.1%}** of the "
                        "sampled tissue shows features consistent with IDC. Limited "
                        "involvement detected in this sample."
                    )
                st.caption(
                    "**What this is:** an estimate of how much of the sampled tissue is "
                    "involved, used to prioritise which slides a pathologist reads first. "
                    "Validated on 54 unseen patients at r = 0.978 against the true "
                    "proportion, mean error 2.8 percentage points.\n\n"
                    "**What this is not:** a diagnosis, and not a yes/no answer on whether "
                    "this person has cancer. Every patient in this dataset is drawn from a "
                    "breast cancer specimen, so the data contains no cancer-free patients "
                    "to support such a claim. A low percentage means limited involvement "
                    "in the tissue sampled, not absence of disease."
                )

                st.pyplot(probability_histogram(probs, threshold))
                st.caption(
                    "Each patch gets a score from 0 (clearly benign) to 1 (clearly "
                    "malignant). A sample with scores clustered at both ends is one "
                    "the model finds easy to read. Scores bunched near the dashed "
                    "line are cases it finds genuinely ambiguous."
                )

                known = [(p, t) for p, t in zip(probs, truths) if t is not None]
                if known:
                    kp = np.array([p for p, _ in known])
                    kt = np.array([t for _, t in known])
                    true_frac = float(kt.mean())
                    acc = float(((kp >= threshold).astype(int) == kt).mean())
                    st.subheader("Ground truth check")
                    st.caption(
                        "Labels were read from the 0/ and 1/ sub-folders, so the "
                        "app can score itself on this patient."
                    )
                    g1, g2, g3 = st.columns(3)
                    g1.metric("True malignant fraction", f"{true_frac:.1%}")
                    g2.metric("Predicted", f"{frac:.1%}",
                              f"{frac - true_frac:+.1%} error", delta_color="off")
                    g3.metric("Per-patch accuracy", f"{acc:.1%}")

                b1, b2, b3 = st.columns(3)
                b1.metric("Confidently malignant", f"{int((probs >= 0.9).sum())}",
                          help="Score of 0.9 or above")
                b2.metric("Confidently benign", f"{int((probs <= 0.1).sum())}",
                          help="Score of 0.1 or below")
                b3.metric("Uncertain", f"{int(((probs > 0.4) & (probs < 0.6)).sum())}",
                          help="Score between 0.4 and 0.6")

                with st.expander("Per-patch results"):
                    import pandas as pd
                    tbl = pd.DataFrame({
                        "file": names,
                        "malignancy_score": np.round(probs, 4),
                        "call": np.where(flagged, "Malignant", "Benign"),
                    }).sort_values("malignancy_score", ascending=False)
                    st.dataframe(tbl, use_container_width=True, height=320)
                    st.download_button(
                        "Download results as CSV",
                        tbl.to_csv(index=False).encode(),
                        file_name="patient_patch_results.csv",
                        mime="text/csv",
                    )

                st.info(
                    "This estimates the proportion of the sampled tissue that "
                    "appears malignant. It is not a diagnosis and does not replace "
                    "review by a qualified pathologist."
                )
    else:
        st.info(
            "No files selected yet. Open a patient folder, press Ctrl+A to select "
            "every image inside, and drag them onto the box above."
        )

st.divider()
st.caption(
    "Model: XGBoost on handcrafted colour and texture features, trained with a "
    "patient-grouped split (CPU only). Cross-validated accuracy 82.6% +/- 2.5%, "
    "AUC 0.897. Explanations: Claude (Anthropic) with RAG over a curated "
    "knowledge base via ChromaDB."
)
