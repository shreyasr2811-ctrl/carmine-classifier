# What changed in this version

## The problem that was fixed

The original training script split the 3,000 images randomly at the **patch**
level. Because many patches come from the same patient (and therefore the same
physical slide, staining batch and scanner session), the same patient appeared
in both the training set and the test set.

Measured directly: **247 of 274 patients (90%) had patches on both sides of the
original split.**

This is called data leakage. The model could score well partly by recognising a
particular patient's slide rather than by recognising cancer, so the reported
accuracy was optimistic.

## The fix

`src/train_grouped.py` splits by **patient ID** (the number at the start of every
filename, e.g. `10253_idx5_x501_y351_class1.png` is patient 10253). No patient
appears on both sides of any split. The code asserts this, so it fails loudly if
leakage ever reappears.

It also now runs 5-fold cross-validation instead of a single split, so results
come with a measure of variability rather than one point estimate.

## Corrected results

Patient-grouped 5-fold cross-validation:

| Model | Accuracy | AUC | Sensitivity | Specificity |
|---|---|---|---|---|
| Dummy baseline | 0.4993 +/- 0.0003 | 0.500 | - | - |
| Logistic regression | 0.8210 +/- 0.0158 | 0.8902 | 0.8307 | 0.8113 |
| Random forest | 0.8220 +/- 0.0271 | 0.8903 | 0.8321 | 0.8119 |
| XGBoost | 0.8264 +/- 0.0251 | 0.8970 | 0.8275 | 0.8253 |

Effect of removing the leakage: accuracy fell by **1.69 percentage points**
(0.8589 to 0.8420 on the same fold), AUC fell by 0.0117.

**Headline figure to quote: 82.6% +/- 2.5% accuracy, AUC 0.897, from
patient-grouped 5-fold cross-validation.**

## Three things to note when writing this up

1. **Fold-to-fold accuracy ranged from 78.6% to 86.1%.** The original single-split
   result of 85.8% sat near the top of that range. Reporting one split as though
   it were precise was the methodological error underneath the headline error.

2. **The three model families are statistically indistinguishable.** XGBoost beats
   logistic regression by 0.54 percentage points against a fold standard deviation
   of 2.5%. Any claim that XGBoost is the better model is not supportable. The
   defensible conclusion is that performance is limited by the features, not by
   the choice of classifier.

3. **Sensitivity is now the weaker side** (0.8275 vs specificity 0.8253 in CV, and
   0.819 vs 0.865 on the shipped model). For a screening aid justified by the cost
   of a missed cancer, the model is currently weakest at the thing that matters
   most. Tuning the decision threshold away from the default 0.5 is the next fix.

## Honest caveat about the "hold-out" in Step 5

The hold-out test set in Step 5 of `train_grouped.py` reuses fold 1 of the
cross-validation. It is **not** an independent confirmation, and its 84.2% should
not be quoted as a separate result. Quote the cross-validated mean instead. The
Step 5 model exists only to produce the `classifier.joblib` the app loads.

## Files

| File | Status |
|---|---|
| `src/train_grouped.py` | NEW. Use this. |
| `src/train.py` | Superseded. Kept only to reproduce the leaky baseline. Has a warning banner. |
| `models/classifier.joblib` | Retrained with patient-grouped split. |
| `models/scaler.joblib` | Refitted on the grouped training set. |
| `models/metadata_grouped.json` | All corrected results. |
| `models/metadata_OLD_leaky_DO_NOT_CITE.json` | The old inflated numbers, renamed so they are not cited by accident. |
| `models/features_cache.npy` | Cached features, so reruns skip the 3-minute extraction step. |
| `requirements.txt` | `opencv-python-headless` removed. It was listed but never imported anywhere in the code. |

## Still outstanding

The 22-page project report still cites the old figures (85.78% accuracy,
0.9204 AUC) throughout. Those numbers are superseded and need replacing before
submission.

---

# Update: patient-level (slide-level) aggregation

## What was added

The classifier only ever saw one 50x50 patch at a time, but a pathology lab
cares about the patient's slide, not one pixel square. Two new ways to analyse
all of a patient's patches at once:

**In the app:** a second tab, "Whole patient sample". Select every image from
one patient folder, and the app classifies each patch then aggregates them into
a single slide-level summary: what proportion of tissue looks malignant, the
mean malignancy score, a distribution chart, and a downloadable per-patch table.
The decision threshold is adjustable with a slider.

**From the command line:** `src/analyze_patient.py` points straight at a folder,
which is better for very large patient folders where browser upload is slow.

    python src/analyze_patient.py "C:/Dataset ML/9265"

If the folder contains `0/` and `1/` subfolders, the script reads the true
labels from them and reports its own error automatically.

## Why aggregation is more trustworthy than a single patch

Individual patch errors are roughly symmetric: the model over-calls about as
often as it under-calls. Those errors largely cancel when averaged over many
patches, so the aggregate is far more stable than any single prediction.

## Validation, on the 54 patients held out from the shipped model

| Measure | Result |
|---|---|
| Correlation, true vs predicted malignant fraction | **r = 0.978** |
| Same, patients with 10 or more patches | r = 0.984 |
| Mean absolute error of the fraction estimate | **2.8 percentage points** |

Compare that with 82.6% accuracy on individual patches. Aggregation converts a
moderately accurate patch classifier into a much more reliable slide-level
estimate. This is arguably the strongest result in the project.

## Caveat you must state if you report this

The "true fraction" used in validation is the malignant fraction **within the
balanced 3,000-image sample**, not the patient's real clinical tumour burden.
The sampling drew 1,500 benign and 1,500 malignant patches overall, which
distorts each patient's true ratio. When you run the tool on a complete patient
folder from the original dataset, the fraction reflects that patient's actual
sampled tissue. The r = 0.978 figure demonstrates that aggregation recovers the
correct proportion, not that the tool measures clinical tumour burden.

Median patches per held-out patient was only 10, which is thin. On full patient
folders with hundreds of patches the estimate should be more stable still,
though that has not been measured here.

---

# Specimen grouping: what changed in this revision

## A feature that was clustering on missingness

The mixture was originally fitted on four patient-level measurements:
involvement, nuclear load, pleomorphism and **spread** (how widely the flagged
tissue is distributed). Spread comes from the focality routine, which needs at
least eight coordinate-bearing patches and at least three flagged ones. Where
it could not be computed, the pipeline substituted the neutral value 0.5.

Measured directly: **that substitution applied to 138 of 274 patients.** Half
the cohort sat on a hard point mass at exactly 0.5, and the mixture split two
of its components along it. Groups 2 and 3 in the previous build differed
mainly in *whether the measurement had been possible*, not in the tissue.

Spread was removed from the feature vector. Focality is still measured and
still reported to the operator; it is simply no longer allowed to define the
groups. The fit now uses three measurements, all available for every patient.

Side effect worth noting: with the artifact gone, BIC independently prefers
k = 4, which it did not before, and the covariance-type choice stopped being a
coin flip (full wins on held-out likelihood *and* BIC).

## Probabilities that were too confident to be informative

A single fitted mixture answers "assuming these four components are exactly
right, which one produced this specimen?" On this cohort the median answer was
**0.98**, and 43% of specimens were reported above 0.99. That is not a bug in
the arithmetic; it is the wrong question. The components were estimated from
274 patients and would move under a different 274, and a single fit ignores
that entirely.

The reported posterior is now averaged over **60 mixtures refitted on bootstrap
resamples of the cohort**, each aligned back to the reference fit by
minimum-cost assignment on component means. Nothing is rescaled or softened:
these are the posteriors the resampled fits actually produce.

| | single fit | bootstrap-averaged |
|---|---|---|
| Median top-group probability | 0.98 | 0.70 |
| Reported above 0.99 | 43% | 4% |
| Reported below 0.60 | 7% | 29% |

The two agree on which group is top for 90.9% of the cohort, so this changes
how certain the model claims to be, not what it says. Specimens deep inside a
component stay confident; specimens near a boundary do not, which is the truth
about those specimens.

Group distribution across the 274 patients under the reported posterior:
**G1 33 (12%), G2 70 (26%), G3 83 (30%), G4 88 (32%)**.

## Missing measurements are marginalised, not filled in

A single uploaded patch has no involvement fraction — one patch is not a
proportion of itself. Rather than substituting a stand-in value (the mistake
that produced the spread artifact above), the unobserved dimension is
marginalised out of each Gaussian exactly: the marginal of a multivariate
normal is the normal on the retained rows and columns. The card states how many
measurements the posterior used, and the split it reports is correspondingly
wider.

## Where grouping is and is not shown

Grouping is gated on the **aggregate verdict**, not on whether any individual
patch was flagged:

| Input | Grouped? |
|---|---|
| Whole sample, reads malignant (≥ 15% flagged) | yes |
| Whole sample, reads benign — even with some flagged patches | no |
| Whole sample, nothing flagged at all | no |
| Folder holding more than one patient | no |
| Single patch, classified malignant | yes, on two measurements |
| Single patch, classified benign | no |

The benign case is the one that changed. A sample the pipeline has just
declined to call malignant should not carry a specimen-level characterisation
of malignant tissue, however some of its individual patches scored.
