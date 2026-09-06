"""
Every piece of substantial user-facing prose lives here.

This is deliberate. The honesty framing in this product is a feature, not
legal boilerplate, and the fastest way for careful wording to rot is to have
it scattered through layout code where nobody reviews it. Keeping it in one
file means a supervisor, a clinician or an examiner can read the entire
claim surface of the app in one sitting.
"""

TITLE = "Breast Cancer Histopathology Classifier"

SUBTITLE = (
    "A first-pass reader for H&E-stained whole-slide tissue patches. It estimates how "
    "much of a patient's sampled tissue shows features consistent with invasive ductal "
    "carcinoma, so the most involved slides reach a pathologist first."
)

DISCLAIMER_SHORT = (
    "<b>Decision support, not a diagnosis.</b> This is an educational research tool, not "
    "a certified medical device. It reads small image patches, not full clinical slides, "
    "and it can be wrong. Every clinical decision stays with a qualified pathologist."
)

DISCLAIMER_LONG = (
    "This tool was built as an academic project. It has not been reviewed or approved by "
    "any regulator, and it is not validated for clinical use. Its predictions are made on "
    "50x50 pixel tissue patches drawn from digitised slides, not on the full slide a "
    "pathologist would read, and not on any patient history. Model errors are ordinary and "
    "expected: per-patch accuracy is roughly 83%, which means around one patch in six is "
    "called wrongly. Never use this output for diagnosis, treatment, triage of a real "
    "patient, or any decision affecting a person's care. Always consult a qualified "
    "pathologist or oncologist."
)

# --- Single patch ---------------------------------------------------------

SINGLE_INTRO = "Score one patch. A spot check, not the main event."

SINGLE_WEAK_EVIDENCE = (
    "About one patch call in six is wrong, and nothing here tells you which. Use "
    "<strong>Whole patient sample</strong> for anything that matters."
)

SINGLE_NO_EXTENT = (
    "Extent of involvement is a proportion of a sample, and one patch is not a "
    "proportion of itself. Analyse a whole patient sample to get that reading."
)

EXPLANATION_FALLBACK = (
    "Live explanation is unavailable, so here is the standing note.\n"
    "The model returned {label} at {conf} confidence. That is a patch-level score from an "
    "experimental classifier trained on colour and texture statistics, not a diagnosis and "
    "not a statement about this person's health.\n"
    "For anything that matters clinically, the reading belongs to a qualified pathologist "
    "working from the full slide and the patient's history."
)

# --- Patient sample -------------------------------------------------------

PATIENT_INTRO = "Score every patch from one patient and aggregate."

# The action line says what to do, once. The standing caveat that a
# pathologist confirms everything lives in the disclaimer strip at the top of
# the page and is not repeated here.
TRIAGE = {
    "critical": {
        "headline": "High priority review",
        "action": "<strong>Route to the front of the pathologist queue.</strong>",
    },
    "uncertain": {
        "headline": "Standard review",
        "action": "<strong>Queue in the normal order.</strong>",
    },
    "benign": {
        "headline": "Low priority review",
        "action": ("<strong>Queue behind higher-scoring cases.</strong> "
                   "A statement about sampled tissue, not a clearance."),
    },
}

IS_THIS = (
    "An estimate of <b>how much of the sampled tissue is involved</b>, used to order a "
    "reading queue. Tracks truth at <b>r = 0.978</b> on 54 unseen patients."
)

IS_NOT_THIS = (
    "Not a diagnosis. The data contains <b>no cancer-free patients</b>, so a low figure "
    "means limited involvement in the tissue sampled, <b>not absence of disease</b>."
)

DISTRIBUTION_NOTE = (
    "Each patch scores from 0 (clearly benign) to 1 (clearly malignant). Scores piled at both "
    "ends mean the model finds this sample easy to read. Scores bunched against the threshold "
    "line mean it finds them genuinely ambiguous &mdash; treat that headline number with more "
    "caution."
)

SPATIAL_NOTE = (
    "Reconstructed from the coordinates in each patch filename, so you can see <em>where</em> "
    "the suspicion sits. Focal involvement and diffuse involvement can produce an identical "
    "headline percentage and look completely different here. Blank cells are patches not "
    "present in the sample."
)

THRESHOLD_NOTE = "Lower it to catch more tissue, at the cost of more false alarms."

GROUND_TRUTH_NOTE = (
    "These files carry their own labels, so the system can mark its own work. "
    "A check on the model, not a finding about the patient."
)

EVIDENCE_NOTE = "The patches driving the number, most suspicious first."


FOOTER = (
    "<b>Model</b> &mdash; XGBoost over 118 handcrafted colour and texture features "
    "(RGB/HSV histograms, GLCM, LBP), trained on a <b>patient-grouped</b> split so no patient "
    "appears in both training and test. CPU only, no GPU, no pretrained weights. "
    "<span class='hp-mono'>Cross-validated accuracy 82.6% &plusmn; 2.5% &middot; AUC 0.897 &middot; "
    "held-out 84.2% (95% CI 81.1-86.9)</span>. The naive patch-level split scores higher; it "
    "leaks patients between folds and is not cited here. "
    "<b>Explanations</b> &mdash; Claude, grounded by TF-IDF retrieval over a curated knowledge "
    "base in ChromaDB."
)


# ==========================================================================
# SITE PAGES
# --------------------------------------------------------------------------
# Copy for the four non-tool pages. Held to the same rule as everything
# above: no claim appears here that the numbers in models/metadata_grouped.json
# do not support. Where a figure is quoted it is the patient-grouped one, never
# the flattering patch-level one.
# ==========================================================================

# --- Overview -------------------------------------------------------------

HERO_EYEBROW = "Computational pathology · Breast"

HERO_TITLE = "Read the queue before you read the slide."

HERO_BODY = (
    "Carmine scores every tissue patch in a digitised breast specimen and estimates how "
    "much of the sampled tissue carries features consistent with invasive ductal carcinoma. "
    "The output is an ordering, not an opinion &mdash; so the most involved slides reach a "
    "pathologist first, and the least involved ones stop competing for their attention."
)

HERO_NOTE = (
    "Research prototype. Validated on 54 held-out patients, never on a live clinical "
    "workflow."
)

PILLARS = [
    {
        "kicker": "Validated honestly",
        "title": "Patient-grouped, or it doesn't count",
        "body": (
            "Split patches by patient, not at random. The random split scores 85.9% and is "
            "meaningless &mdash; the same patient's tissue lands on both sides of it. Every "
            "figure Carmine publishes comes from the grouped split, including the ones that "
            "look worse."
        ),
    },
    {
        "kicker": "Traceable",
        "title": "Every number leads back to tissue",
        "body": (
            "The headline percentage is not the end of the screen. Underneath it sit the score "
            "distribution, a spatial map of where the suspicion falls, and the actual patches "
            "that drove it &mdash; ranked, thumbnailed and scored."
        ),
    },
    {
        "kicker": "Deployable",
        "title": "Runs on the laptop you already have",
        "body": (
            "118 handcrafted colour and texture features, CPU only, no GPU and no pretrained "
            "weights to download. A 400-patch patient scores in seconds on a dual-core "
            "machine."
        ),
    },
]

HOW_STEPS = [
    ("Tile", "The slide arrives already tiled into 50&times;50 px patches, each carrying its "
             "slide coordinates in the filename."),
    ("Describe", "118 features per patch &mdash; RGB and HSV histograms for stain uptake, GLCM "
                 "and LBP for nuclear texture and density."),
    ("Score", "An XGBoost classifier returns a malignancy probability between 0 and 1 for "
              "every patch, in parallel across CPU cores."),
    ("Aggregate", "Patch errors are close to symmetric, so they largely cancel. The tissue-"
                  "involvement estimate tracks truth at r = 0.978 across held-out patients."),
]

WHERE_IT_FITS = (
    "Carmine sits <em>before</em> the microscope, not in place of it. It takes a stack of "
    "digitised specimens with no natural reading order and gives them one. The pathologist "
    "reads every slide they would have read anyway &mdash; they simply reach the involved "
    "ones sooner. Nothing is filed, cleared, or ruled out by the model."
)

CTA_TITLE = "Score a specimen"

CTA_BODY = (
    "The console runs against the bundled sample, a folder of patches on this machine, or "
    "files you upload. Nothing leaves the machine it runs on."
)

ICON_ROW_ITEMS = [
    ("upload", "Point it at a folder",
     "A folder of tissue patches or a handful of uploaded files &mdash; no other setup."),
    ("scan", "Every patch scored",
     "The same calibrated model reads every patch. No sampling, no manual triage step."),
    ("layers", "Evidence stays visible",
     "Each flagged patch is kept as a thumbnail, so a reviewer checks the call against "
     "the actual tissue, not just a number."),
    ("doc", "A cited explanation",
     "The written summary names the passages it was built from, and says so plainly "
     "when it has none to cite."),
]

CLOSING_KICKER = "Ready when you are"

CLOSING_TITLE = "Bring your own specimen."

CLOSING_BODY = (
    "The console runs against the bundled sample, a folder on this machine, or files you "
    "upload &mdash; nothing leaves the machine it runs on, and every figure it shows you "
    "traces back to a number on the Validation page."
)

# --- Technology -----------------------------------------------------------

TECH_INTRO = (
    "No deep learning, no pretrained weights, no GPU. That was a constraint before it was a "
    "position &mdash; 274 patients is not enough data to fine-tune a large vision model "
    "without overfitting to them, and a feature vector you can name is a feature vector you "
    "can argue with."
)

FEATURE_FAMILIES = [
    ("RGB histograms", 48, "16 bins &times; 3 channels",
     "Raw stain uptake. Malignant regions take up haematoxylin differently as nuclear "
     "density rises."),
    ("HSV histograms", 48, "16 bins &times; 3 channels",
     "Hue separates the blue-purple of nuclei from the pink of stroma more cleanly than RGB, "
     "and survives slide-to-slide brightness drift better."),
    ("Channel statistics", 6, "mean and std &times; 3",
     "A compact summary of overall staining intensity and its spread across the patch."),
    ("GLCM texture", 6, "6 properties, 2 distances, 4 angles",
     "Contrast, dissimilarity, homogeneity, energy, correlation and ASM &mdash; the classical "
     "descriptors of nuclear crowding and disorder."),
    ("LBP histogram", 10, "P=8, R=1, uniform",
     "Fine-grained local texture, rotation-invariant, which picks up chromatin pattern at a "
     "scale the GLCM window misses."),
]

WHY_HANDCRAFTED = (
    "A 118-dimensional vector of named statistics has three properties a learned embedding "
    "does not. It trains to convergence on 2,405 patches without a GPU. It fails in ways you "
    "can inspect &mdash; when the model is wrong about a patch you can go and look at which "
    "texture statistic was unusual. And it carries no ImageNet prior, so nothing in the "
    "result is inherited from a dataset of photographs of dogs."
)

MODEL_NOTE = (
    "XGBoost over the 118 features, trained on 2,405 patches from 220 patients. The "
    "hyperparameters are deliberately conservative &mdash; shallow trees, heavy subsampling "
    "&mdash; because the failure mode that matters at this sample size is memorising "
    "patients, not underfitting them."
)

AGGREGATION_NOTE = (
    "One patch at 84% accuracy is weak evidence: about one call in six is wrong and nothing "
    "in the output tells you which. Several hundred patches from the same specimen is a "
    "different object. Individual errors are roughly symmetric around the truth, so averaging "
    "them cancels most of the noise &mdash; which is why the aggregate estimate lands within "
    "2.8 percentage points of the true malignant proportion while any single patch inside it "
    "may well be wrong."
)

RAG_NOTE = (
    "The written explanation is generated by Claude, but not from the model's memory. Each "
    "prediction retrieves passages from a curated histopathology knowledge base held in "
    "ChromaDB via TF-IDF, and the language model is given those passages to write from. The "
    "retrieved sources are printed under every explanation so the reader can check whether "
    "the text actually follows from them. With no API key the panel degrades to a fixed "
    "written note rather than inventing one."
)

# --- Validation -----------------------------------------------------------

VAL_INTRO = (
    "The most important number on this page is the one that got smaller. Splitting the same "
    "3,000 patches at random rather than by patient adds 1.7 points of accuracy and 1.2 "
    "points of AUC that do not exist &mdash; tissue from one patient appears in training and "
    "test at once, and the model is rewarded for recognising the patient rather than the "
    "disease."
)

LEAKAGE_NOTE = (
    "Both rows above were produced by the same model on the same 3,000 patches. Only the "
    "split differs. The naive row is reported here <em>because</em> it is the one a careless "
    "evaluation would publish."
)

VAL_METHOD = (
    "274 patients, 3,000 patches, 118 features. 220 patients (2,405 patches) train; 54 "
    "patients (595 patches) are held out and touched once. Five-fold cross-validation is "
    "grouped by patient, so no patient's tissue is ever split across a fold boundary. The "
    "95% confidence interval is a Wilson interval on the held-out accuracy."
)

CONFUSION_NOTE = (
    "On held-out patients the model misses 54 malignant patches and false-alarms on 40. That "
    "asymmetry is the wrong way round for a screening tool &mdash; misses cost more than "
    "false alarms &mdash; which is exactly why the decision threshold is exposed as a live "
    "control in the console rather than frozen at 0.50."
)

PATIENT_LEVEL_NOTE = (
    "Aggregated to the patient, the picture improves sharply. Across the 54 held-out "
    "patients the estimated malignant fraction tracks the true fraction at <strong>r = "
    "0.978</strong> with a mean absolute error of <strong>2.8 percentage points</strong>. "
    "This is the number the product is actually built on, and the reason the console leads "
    "with a patient-level figure rather than a patch-level one."
)

LIMITATIONS = [
    ("One dataset, one stain protocol",
     "Every patch comes from the same public IDC collection. Nothing here demonstrates that "
     "the model survives a different scanner, a different lab's staining, or a different "
     "population."),
    ("No cancer-free patients exist in the data",
     "Every patient in the dataset is a breast cancer patient. The model has never seen a "
     "healthy specimen, so a low involvement score means limited involvement in the tissue "
     "sampled &mdash; it can never mean absence of disease."),
    ("50&times;50 px is not a slide",
     "A pathologist reads architecture across millimetres of tissue plus the patient's "
     "history. A 50-pixel patch carries neither, and no aggregation of patches recovers "
     "them."),
    ("Sampling is not exhaustive",
     "The console samples a few hundred patches from large specimens by default. That lands "
     "within a point or two of the full answer on average, but it is an estimate of an "
     "estimate."),
    ("The morphological profile is descriptive, not diagnostic",
     "Spatial pattern, nuclear load and pleomorphism are measured from the images, but "
     "their bands are tertiles of this cohort rather than clinical thresholds, and the "
     "memberships are rule-based rather than learned. Pleomorphism in particular separates "
     "benign from malignant tissue only weakly here (Cohen's d 0.29 against 1.44 for "
     "nuclear load) and is inflated where touching nuclei merge. None of it is a stage or "
     "a grade, and the dataset carries no label that would allow either to be predicted."),
    ("Never prospectively evaluated",
     "Held-out accuracy is not clinical performance. No pathologist has used this in a real "
     "reading workflow, and no study exists showing it changes an outcome."),
]

CLINICAL_GAP = (
    "What would have to happen before anything like this touched patient care: multi-site "
    "data with different scanners and staining protocols; prospective evaluation against "
    "reporting pathologists; a defined intended-use population; failure-mode analysis on the "
    "cases it gets wrong; and regulatory review as a medical device. None of those has "
    "happened. This is a research prototype and the gap between it and a cleared product is "
    "the entire distance."
)

# --- About ----------------------------------------------------------------

ABOUT_INTRO = (
    "Carmine is an academic project: a complete, honest computational pathology pipeline "
    "built end to end &mdash; feature extraction, patient-grouped validation, a triage "
    "interface and a retrieval-grounded explanation layer &mdash; on public data and "
    "commodity hardware."
)

ABOUT_WHY = (
    "The interesting problem in this space is not getting a classifier to 85%. It is "
    "reporting the 85% in a way that survives scrutiny, and presenting it so that the person "
    "reading it can tell what it does and does not mean. Most of the work here is in the "
    "second half."
)

ABOUT_DATA = (
    "The dataset is the public IDC (invasive ductal carcinoma) breast histopathology "
    "collection: 50&times;50 pixel patches cut from digitised whole-slide images at 40&times;, "
    "each labelled malignant or benign, each filename carrying its patient identifier and its "
    "x/y coordinates on the source slide. This build uses 3,000 patches drawn from 274 "
    "patients."
)

ABOUT_STACK_INTRO = (
    "Every layer, and what it is actually doing here. Nothing in this list is "
    "decorative &mdash; if a library is named, its output reaches the screen."
)

# (layer, implementation, what it does here)
ABOUT_STACK = [
    ("Language", "Python 3.11",
     "The whole pipeline, training through interface."),
    ("Image handling", "Pillow, NumPy",
     "Reads each 50&times;50 patch, converts to RGB, holds it as an array."),
    ("Feature extraction", "scikit-image, SciPy",
     "Builds the 118-dimension vector: RGB and HSV histograms, "
     "grey-level co-occurrence matrix (GLCM) texture, local binary patterns "
     "(LBP). SciPy&rsquo;s <span class='hp-mono'>ndimage</span> labels nuclei "
     "for the morphology measurements."),
    ("Colour deconvolution", "scikit-image <span class='hp-mono'>rgb2hed</span>",
     "Separates the haematoxylin stain from the eosin, so nuclear "
     "measurements respond to staining rather than to image brightness."),
    ("Classifier", "XGBoost",
     "Gradient-boosted decision trees over the 118 features. Chosen over a "
     "CNN deliberately: it trains on a CPU in minutes and every feature it "
     "splits on can be named."),
    ("Validation", "scikit-learn",
     "<span class='hp-mono'>StratifiedGroupKFold</span> for the patient-grouped "
     "split, <span class='hp-mono'>StandardScaler</span>, and the metrics "
     "quoted on the Validation page."),
    ("Model artefacts", "joblib",
     "Serialises the trained classifier and the fitted scaler into "
     "<span class='hp-mono'>models/</span>, so the app loads rather than retrains."),
    ("Interface", "Streamlit",
     "The application shell, routing, file upload and state."),
    ("Design system", "Custom CSS in <span class='hp-mono'>ui/</span>",
     "Design tokens, components and theme, written by hand rather than taken "
     "from a component library, so the visual language is one system."),
    ("Charts", "Plotly",
     "Score distribution and the spatial tissue map, both interactive."),
    ("Data handling", "pandas, NumPy",
     "Aggregating patch scores to the patient-level figure."),
    ("Retrieval", "ChromaDB, TF-IDF",
     "Vector store over a curated reference collection. Retrieves the passages "
     "the explanation is allowed to draw on."),
    ("Generation", "Claude, via LangChain",
     "Writes the plain-language explanation from the retrieved passages only. "
     "The passages are printed underneath so the text can be checked."),
    ("Configuration", "python-dotenv",
     "Keeps the API key out of the source tree."),
    ("Version control", "Git, GitHub",
     "Source of truth, and what the deployment builds from."),
    ("Deployment", "Streamlit Community Cloud",
     "Builds from the GitHub repository on push. Free tier, roughly 1&nbsp;GB "
     "of memory, which is why the dependency list stays short."),
    ("Compute", "CPU only",
     "No GPU, no pretrained weights, no deep learning anywhere in the pipeline."),
]

CONTACT_NOTE = (
    "This is a demonstration form on a research prototype. It does not send anything "
    "anywhere and no data is stored."
)

SITE_FOOTER_NOTE = (
    "Carmine is a fictional brand for an academic research project. It is not a company, not "
    "a product, and not a medical device. Nothing on this site has been reviewed by any "
    "regulator."
)


# --- Extent of involvement -------------------------------------------------
# The ladder is the headline reading. Its vocabulary avoids stage language
# entirely -- no numerals, no roman numbers, no use of the word "stage" as a
# label -- because the one thing a reader must not take away from a stepped
# graphic in an oncology context is that they have been given a stage.

EXTENT_INTRO = (
    "How much of the tissue sampled from this patient was flagged. This is the one "
    "quantity the system measures, and the only one validated against ground truth."
)

# Per-band meaning. The component appends the live arithmetic underneath, so
# the tooltip carries both what the band means and how this reading was
# arrived at.
EXTENT_MEANING = [
    (
        "Under 15% of the sampled patches were flagged. The specimen can go behind "
        "higher-scoring cases in the reading queue. This is a statement about the "
        "tissue that was sampled and not a clearance: this dataset contains no "
        "cancer-free patients, so a low figure means limited involvement in what was "
        "sampled, not absence of disease."
    ),
    (
        "Between 15% and 50% of the sampled patches were flagged, so the specimen is "
        "genuinely mixed. This is the band where the spatial map is worth reading: the "
        "same percentage can come from one contained region or from involvement "
        "scattered throughout, and those look identical in the headline figure."
    ),
    (
        "Between 50% and 75% of the sampled patches were flagged, so more of the "
        "sampled tissue was flagged than was not. Route to the front of the queue."
    ),
    (
        "75% or more of the sampled patches were flagged, so nearly all the sampled "
        "tissue carries features consistent with invasive ductal carcinoma. Route to "
        "the front of the queue."
    ),
]

EXTENT_BASIS = (
    "Basis: {n_flag} of {n_total} patches scored at or above the decision threshold "
    "of {thr:.2f}, giving {frac:.1%}. Band boundaries are 15%, 50% and 75%. Those are "
    "a product decision about queue order, not a clinical or statistical result."
)

EXTENT_NOT_STAGE = (
    "<b>This is not a cancer stage.</b> It is the proportion of sampled tissue that "
    "was flagged, on a four-band scale of our own. Staging is a different thing "
    "entirely, and this system cannot produce one &mdash; the reference below says why."
)

# --- Staging reference ------------------------------------------------------
# Reference material, never model output. It exists so the reader learns what
# staging actually is, and can see for themselves that none of its inputs are
# available to this system.

STAGING_REF_INTRO = (
    "Reference only &mdash; none of this is produced by the model. Included because "
    "&lsquo;what stage is it?&rsquo; is the first question anyone asks of a breast "
    "cancer tool, and the honest answer is that no image classifier reading tissue "
    "patches can answer it."
)

STAGING_REF = [
    ("0", "Non-invasive", (
        "Ductal carcinoma in situ. Abnormal cells are confined within the milk ducts "
        "and have not invaded the surrounding breast tissue. Determined by a "
        "pathologist examining the architecture of the whole duct, not a fragment of it."
    )),
    ("I", "Early, localised", (
        "An invasive tumour up to 20mm across with no lymph node involvement, or a "
        "smaller tumour with only microscopic deposits in a node. Requires the tumour "
        "to be measured and the nodes to be sampled."
    )),
    ("II", "Localised, larger or node-positive", (
        "An invasive tumour of 20-50mm, or a tumour under 20mm that has reached one to "
        "three axillary lymph nodes. The distinction turns on measurements this system "
        "does not have."
    )),
    ("III", "Regional spread", (
        "A tumour larger than 50mm, or involvement of four or more axillary nodes, or "
        "spread to the chest wall or skin. Established from the gross specimen, nodal "
        "dissection and clinical examination together."
    )),
    ("IV", "Distant spread", (
        "Cancer has spread beyond the breast and regional nodes to distant organs, "
        "most often bone, liver, lung or brain. Established by imaging, never by "
        "looking at breast tissue."
    )),
]

STAGING_REF_WHY = (
    "Stage is TNM. <b>T</b> is tumour size, measured on the gross specimen with a "
    "ruler. <b>N</b> is regional lymph node status, which requires a different tissue "
    "sample entirely. <b>M</b> is distant metastasis, established by imaging. This "
    "system reads 50&times;50 pixel patches of one slide, so it has access to none of "
    "the three &mdash; and the IDC dataset it learned from carries no stage label to "
    "train on. Modern AJCC staging additionally folds in tumour grade and ER, PR and "
    "HER2 receptor status, which need immunohistochemistry rather than an H&amp;E "
    "image. A model emitting a stage here would be reporting a number invented by "
    "whoever wrote its formula, which in this domain is worse than reporting nothing."
)


# --- Morphological profile ------------------------------------------------

MORPH_INTRO = (
    "Supporting detail. Three things measured directly from the flagged patches, "
    "shown so the headline figure can be sanity-checked against the tissue."
)

MORPH_UNCALIBRATED = (
    "<b>Running on fallback reference values.</b> The cohort reference has not been "
    "built, so the band boundaries are defaults rather than tertiles measured on this "
    "data. Run <code>python src/build_morphology_reference.py</code> to calibrate."
)

MORPH_FOCALITY = (
    "Whether the flagged tissue sits in one place or is scattered across the slide. "
    "A pathologist would call this <em>focality</em>."
)

MORPH_LOAD = (
    "How densely packed the cell nuclei are in the flagged tissue. A pathologist would "
    "call this <em>nuclear load</em>. It is the strongest of these three in our data."
)

MORPH_PLEO = (
    "How much the nuclei vary in size from one another. A pathologist would call this "
    "<em>nuclear pleomorphism</em>. Weak in our data and inflated where nuclei touch, "
    "so read it as a hint rather than a finding."
)

MORPH_TITLES = [
    "Where the flagged tissue sits",
    "How densely packed the nuclei are",
    "How much the nuclei vary in size",
]

TECH_MORPH = (
    "The classifier answers one question: how much of the sampled tissue looks malignant. "
    "Three further properties are measured from the same images and coordinates, at a cost "
    "of under a millisecond per patch, so they ride along inside the existing pass rather "
    "than justifying a second one. They are reported as measurements, on bands defined by "
    "tertiles of our own cohort, and they are not predictions of anything."
)

TECH_MORPH_NOT_STAGE = (
    "Staging is TNM. <b>T</b> is tumour size measured on the gross specimen with a ruler. "
    "<b>N</b> is regional lymph node involvement, which requires a different tissue sample "
    "entirely. <b>M</b> is distant metastasis, established by imaging. None of these three "
    "quantities is present in a 50&times;50 pixel patch of breast tissue, and the dataset "
    "carries no stage label to learn from. A model trained on invented stage labels would "
    "emit confident numbers that mean nothing, which in this domain is worse than emitting "
    "nothing at all. The same argument applies to histological grade: the components are "
    "partly visible here, the labels are not."
)


# ==========================================================================
# HELP
# --------------------------------------------------------------------------
# Everything the screen no longer says out loud. Reached by hovering the info
# marker beside a heading, so the detail stays one gesture away from anyone
# who wants it and out of the way of everyone who does not.
# ==========================================================================

HELP = {
    "single": (
        "A single 50x50 patch is thin evidence. Per-patch accuracy is about 84%, so "
        "roughly one call in six is wrong and nothing in the output identifies which. "
        "The whole-patient view averages hundreds of patches, where independent errors "
        "largely cancel."
    ),
    "patient": (
        "Individual patch errors are roughly symmetric, so they largely offset when "
        "averaged. Across 54 held-out patients the aggregated estimate tracked the true "
        "malignant proportion at r = 0.978, with a mean absolute error of 2.8 percentage "
        "points, which is far tighter than any single patch."
    ),
    "threshold": (
        "The score above which a patch is called malignant. Lowering it catches more "
        "cancerous tissue at the cost of more false alarms: the cost of a miss against "
        "the cost of a second look. Scores are already computed, so moving this re-reads "
        "them instantly rather than re-analysing anything. The default of 0.50 is a "
        "convention, not a validated operating point."
    ),
    "triage": (
        "Review bands are set at 50% and 15% of sampled tissue flagged. These are a "
        "product decision, not a statistical one. In a real deployment they would follow "
        "from the receiving laboratory's capacity and its tolerance for a delayed case."
    ),
    "distribution": (
        "Each patch scores from 0 (clearly benign) to 1 (clearly malignant). Scores piled "
        "at both ends mean the model finds this sample easy to read. Scores bunched "
        "against the threshold line mean it finds them genuinely ambiguous, so the "
        "headline figure deserves more caution."
    ),
    "spatial": (
        "Reconstructed from the coordinates carried in each patch filename, so you can "
        "see where the suspicion sits rather than only how much there is. Focal and "
        "diffuse involvement can produce an identical headline percentage and look "
        "completely different here. Blank cells are patches not present in the sample."
    ),
    "confidence": (
        "How decisively the model read this sample. Patches scoring at the extremes were "
        "easy to call; those between 0.40 and 0.60 were genuinely ambiguous and the model "
        "is close to guessing on them."
    ),
    "ground_truth": (
        "This panel is a self-check, not a result. These particular files already carry "
        "their answers: the labels are recovered from the 0/ and 1/ sub-folders, or from "
        "the classN suffix in each filename. The model never sees them, so comparing its "
        "estimate against them shows how close it got on the patient in front of you. It "
        "appears only where the source data carries labels, and never on real unlabelled "
        "tissue."
    ),
    "evidence": (
        "The patches that drove the number, ranked by score. A headline figure a "
        "pathologist cannot trace back to tissue is not decision support."
    ),
    "morphology": (
        "Nuclear load and pleomorphism come from colour deconvolution, which separates the "
        "haematoxylin signal from the eosin so the measurement responds to nuclear staining "
        "rather than to how dark the image is. Spatial pattern comes from the patch "
        "coordinates. Bands are tertiles of our own 274-patient cohort, so 'high' means "
        "high relative to these patients and not on any clinical scale."
    ),
    "focality": (
        "Flagged patches are snapped back onto the slide grid and grouped into connected "
        "regions. One dominant region reads as focal, several substantial regions as "
        "multifocal, a scatter of isolated patches as diffuse. Not tumour size: extent "
        "within the sampled patches says nothing about the dimensions of the lesion."
    ),
    "load": (
        "The proportion of the flagged tissue that is haematoxylin-positive, which is a "
        "direct measure of how much nuclear material is present. This separates benign "
        "from malignant patches strongly in our data (Cohen's d = 1.44)."
    ),
    "pleomorphism": (
        "Variability in the size of detected nuclear regions, used as a proxy for nuclear "
        "pleomorphism. Much weaker than nuclear load in our data (Cohen's d = 0.29) and "
        "inflated where touching nuclei merge into a single region, so read it as "
        "indicative only."
    ),
    "extent": (
        "The proportion of this patient's sampled patches that scored at or above the "
        "decision threshold, placed on a four-band scale. It is the only figure in this "
        "app validated against ground truth: across 54 held-out patients it tracked the "
        "true malignant proportion at r = 0.978, mean absolute error 2.8 percentage "
        "points. The band boundaries at 15%, 50% and 75% are a product decision about "
        "queue order, not a clinical threshold, and this is not a cancer stage."
    ),
    "staging_ref": (
        "Reference material about real TNM staging, included so the difference between "
        "what this system measures and what staging actually is stays visible. Nothing "
        "in this panel is computed from your data, and the model never outputs a stage."
    ),
    "not_stage": (
        "This is not a cancer stage and not a predicted grade. Stage is TNM: tumour size "
        "measured on the gross specimen, lymph node status from a different tissue sample, "
        "and distant metastasis established by imaging. None of those exists in a 50x50 "
        "pixel patch, and this dataset carries no stage or grade label to learn from."
    ),
    "explanation": (
        "Written by a language model that is given retrieved passages from a fixed "
        "reference collection and instructed to use no other source. The passages it was "
        "given are printed beneath, so the text can be checked against them."
    ),
}

