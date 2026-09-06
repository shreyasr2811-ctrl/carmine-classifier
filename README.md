# Carmine — Breast Cancer Histopathology Classifier (IDC)

A CPU-only, no-GPU-required ML pipeline that classifies breast tissue
histopathology patches (from Whole Slide Images) as **Benign** or
**Malignant (IDC)**, with a Streamlit front end and an AI-generated,
RAG-grounded plain-language explanation of each prediction.

The front end is presented as a five-tab site — **Overview · Technology ·
Analyze · Validation · About** — with the classifier console living under
*Analyze*. `Carmine` (a histological stain) is a fictional brand for this
academic project; it is not a company and not a medical device, and the site
footer says so on every page.

Built on a sample of the [Breast Histopathology Images (IDC) dataset](https://www.kaggle.com/datasets/paultimothymooney/breast-histopathology-images).

## Tech stack

| Layer | Tech |
|---|---|
| Classification | Handcrafted color/texture features (color histograms, GLCM, LBP) + Random Forest / XGBoost |
| Vector DB / RAG | ChromaDB (with TF-IDF embeddings, no external model download needed) |
| LLM explanation | Claude (Anthropic) via LangChain |
| Front end | Streamlit |

**Why handcrafted features instead of a deep CNN?** This project targets a
laptop with no GPU. Rather than training a CNN from scratch on CPU (slow)
or relying on downloading pretrained ImageNet weights (which isn't always
possible on locked-down networks), we extract well-established
color/texture descriptors used in histopathology image analysis and feed
them into fast, CPU-friendly ensemble classifiers.

On a **patient-grouped** split (no patient's tissue in both train and test)
this reaches **84.2% held-out accuracy / 0.911 AUC**, cross-validated at
**82.6% ± 2.5% / 0.897 AUC**. The naive random patch-level split scores 85.9%
/ 0.922, but leaks 247 of 274 patients across the boundary — the Validation
tab shows both numbers side by side and labels the 1.7-point gap for what it
is. Aggregated to the patient, the estimated malignant fraction tracks the
true fraction at **r = 0.978** (mean absolute error 2.8 points).

## Project structure

```
breast_cancer_app/
├── app.py                  # Streamlit app (entry point)
├── app_legacy_v5.py        # previous single-file UI, kept for reference
├── DESIGN.md               # design system + front-end architecture
├── requirements.txt
├── .env.example             # copy to .env and add your Anthropic API key
├── .streamlit/
│   └── config.toml          # first-paint theme + server settings
├── ui/                      # presentation layer (no ML logic)
│   ├── brand.py             # name, wordmark SVG, the tab list
│   ├── tokens.py            # colour / type / motion tokens
│   ├── theme.py             # tokens -> injected stylesheet
│   ├── components.py        # reusable HTML/SVG components
│   ├── site.py              # site chrome + the four non-tool pages
│   ├── charts.py            # themed Plotly figures
│   ├── copy.py              # all user-facing prose in one place
│   └── compat.py            # Streamlit version shims
├── data/
│   └── idc_sample/          # sampled patches (0=benign, 1=malignant), used for examples in the app
├── models/
│   ├── morphology_reference.json  # cohort tertiles for the morphology bands
│   ├── classifier.joblib    # trained model (best of RF/XGBoost)
│   ├── scaler.joblib        # feature StandardScaler
│   └── metadata.json        # training results/metrics
├── rag_kb/
│   ├── knowledge_base.py    # curated breast cancer / histopathology facts
│   └── chroma_store/        # persisted ChromaDB vector store
└── src/
    ├── features.py           # feature extraction (color + texture)
    ├── train.py               # training script (reproduce the model)
    ├── rag.py                 # builds/queries the ChromaDB knowledge base
    └── explain.py              # LangChain + Claude explanation generation
```

## Setup

1. Install dependencies (Python 3.10+ recommended):

   ```
   pip install -r requirements.txt
   ```

2. Add your Anthropic API key (needed for the "AI Explanation" feature --
   the classifier itself works without it):

   ```
   cp .env.example .env
   # then edit .env and paste your key
   ```

   Get a key at https://console.anthropic.com. Note: your account needs an
   active credit balance for calls to succeed -- check Plans & Billing if
   you see explanation errors.

3. Run the app:

   ```
   streamlit run app.py
   ```

   It'll open in your browser at http://localhost:8501. Upload a patch
   image or click one of the "Try an example" buttons to test it
   immediately using the bundled sample data.

## Reproducing / retraining the model

The `models/` folder already contains a trained classifier, so you can run
the app immediately. If you want to retrain (e.g., on more data, or after
adding more patches to `data/idc_sample/0` and `data/idc_sample/1`):

```
python src/train.py --data_dir data/idc_sample --out_dir models
```

This will re-extract features, train both Random Forest and XGBoost,
pick the better one by validation AUC, evaluate on a held-out test set,
and overwrite the saved model + scaler + metadata.

### Using more data

The bundled `data/idc_sample/` is a balanced sample of ~3,000 patches
(1,500 benign + 1,500 IDC) drawn from the full IDC dataset for fast,
CPU-friendly training. To use more of the full dataset:

1. Download the full [IDC dataset](https://www.kaggle.com/datasets/paultimothymooney/breast-histopathology-images) from Kaggle.
2. Point `--data_dir` at a folder containing `0/` and `1/` subfolders of
   patches (or adapt `build_manifest()` in `src/train.py` to walk the
   original per-patient folder structure).
3. Re-run `src/train.py`. Note training time scales roughly linearly with
   image count since feature extraction is done per-image on CPU --
   expect a few minutes per few thousand images.

## Rebuilding the RAG knowledge base

If you edit `rag_kb/knowledge_base.py` (add/change facts), rebuild the
vector store with:

```
python src/rag.py
```

## Important disclaimer

This is an educational/portfolio project, **not a medical device** and
not validated for clinical use. Predictions are made on small image
patches, not full clinical slides or patients, and the model can be
wrong (both false positives and false negatives). Never use this tool
for real diagnosis or treatment decisions -- always consult a qualified
pathologist or oncologist.

## Morphological profile

Alongside the malignant-fraction estimate, the console reports three measured
properties of the flagged tissue:

| Measurement | Source | Separation (benign vs malignant) |
|---|---|---|
| Spatial pattern | Connected regions on the reconstructed slide grid | focal / multifocal / diffuse |
| Nuclear load | Colour deconvolution, haematoxylin-positive area fraction | Cohen's d = 1.44 |
| Nuclear pleomorphism | Coefficient of variation of nuclear region areas | Cohen's d = 0.29 |

**This is not staging and not a predicted grade.** Stage is TNM: tumour size
measured on the gross specimen, lymph node status from a different tissue
sample, and distant metastasis from imaging. None of those exists in a 50x50
pixel patch, and the IDC dataset carries no stage or grade label. The bands are
tertiles of our own 274-patient cohort, so "high" means high relative to these
patients, and memberships are graded by rule from the measured value rather
than being probabilities from a trained classifier.

### Specimen grouping (unsupervised)

After classification, patients are grouped by a **Gaussian mixture model**
fitted to four patient-level measurements: involvement, nuclear load,
pleomorphism and spread. The percentages the app shows are genuine posterior
probabilities from that model rather than a rule.

| Group | n | Character | Involvement | Nuclear load | Spread |
|---|---|---|---|---|---|
| Group 1 | 26 | No flagged tissue | 0.00 | 0.05 | 0.50 |
| Group 2 | 105 | Moderate involvement, focal | 0.50 | 0.28 | 0.50 |
| Group 3 | 86 | Moderate involvement, dispersed | 0.57 | 0.26 | 0.80 |
| Group 4 | 57 | Moderate involvement, dense and dispersed | 0.51 | 0.72 | 0.77 |

`mean_score` was dropped from the feature set after the first fit because it
correlated with `involvement` at r = 0.99 and handed the mixture the same axis
twice.

**Choosing k.** BIC was computed for k = 2 to 8 and independently preferred
k = 4:

| k | BIC | Silhouette |
|---|---|---|
| 2 | 1866 | 0.264 |
| 3 | 1768 | 0.280 |
| 4 | 1573 | 0.198 |
| 5 | 1717 | 0.226 |
| 6 | 1679 | 0.206 |
| 7 | 1727 | 0.116 |
| 8 | 1660 | 0.100 |

Silhouette at the fitted k is 0.20, which is weak: the
groups overlap and many specimens sit between them. That is the reason the app
shows the whole posterior rather than a single hard label.

**When the grouping is not shown.** Two gates suppress it, because in both
cases the numbers would be meaningless:

- **Nothing flagged.** If no patch is called malignant at the current
  threshold there is no suspicious tissue to characterise. Measuring the
  appearance of tissue the model called benign and then assigning it a group
  describes something that is not there.
- **More than one patient in the input.** Pointing at a folder holding several
  patients averages them into a single cohort figure dressed up as a specimen
  result. The app now counts distinct patient IDs from the filenames and warns
  before you run it.

**On the posteriors.** They are usually confident, often above 95%. That is a
property of the data rather than a defect: the components separate cleanly in
likelihood terms on these four features. It does not contradict the low
silhouette, which measures Euclidean cohesion and answers a different
question.

**These are not cancer stages.** Nothing in the four input measurements relates
to tumour size on the gross specimen, lymph node involvement or distant
metastasis, which are what staging is defined by. An unsupervised model cannot
recover a label that is absent from its inputs. Groups 2 and 3 differ mainly in
whether disease is focal or dispersed, not in how much of it there is.

Rebuild with:

```
python src/build_cluster_model.py --data_dir data/idc_sample --k 4
```

### Review priority index

The three measurements are combined into a single ordering figure across four
bands (Tier 1 minimal, Tier 2 limited, Tier 3 substantial, Tier 4 extensive
involvement). Involvement sets the tier; nuclear load and spread adjust it by
at most 25 per cent in either direction and cannot set it alone. The weighting is a stated
editorial choice rather than a fitted result, and all three inputs are shown
alongside the tier so the figure can be reconstructed by hand.

**It is not a stage.** The four bands are a presentation choice and the
numbering deliberately does not correspond to any staging system. The index
carries no claim about tumour size, nodal status or metastasis. It is an ordering aid
built from quantities this system measured.

Recalibrate the bands for a different cohort with:

```
python src/build_morphology_reference.py --data_dir data/idc_sample
```

