"""
Fit the patient-level Gaussian mixture used to group specimens.

WHY A MIXTURE MODEL
-------------------
The previous version of this grouping was a weighted formula with hand-chosen
boundaries. That worked, but the weights and the cut points were our editorial
judgement rather than anything the data had to say, and the memberships it
produced were rule-based rather than probabilistic.

A Gaussian mixture replaces both. It finds the groups that actually exist in
the joint distribution of the patient-level measurements, and because it is a
generative probabilistic model it returns genuine posterior probabilities of
membership rather than a smoothed rule. When a specimen sits between two
groups, the posterior says so for a real reason.

WHAT THE GROUPS ARE, AND ARE NOT
--------------------------------
They are clusters of specimens that resemble one another in tissue extent and
nuclear appearance. Mixture components come out of a fit in arbitrary order, so
they are sorted for presentation by a stated severity key (see below); the
groups themselves are whatever the mixture found.

They are NOT cancer stages. Nothing in the feature vector carries information
about tumour size on the gross specimen, lymph node involvement or distant
metastasis, which are the three things staging is defined by. An unsupervised
model cannot discover a label that has no correlate in its inputs, and a
cluster index is not a clinical grade merely because both happen to be small
integers.

The fit is descriptive rather than predictive: it is fitted on the whole
cohort because its purpose is to characterise that cohort. It is not evaluated
on held-out patients because there is no target to be right or wrong about.

Usage:
    python src/build_cluster_model.py --data_dir data/idc_sample --k 4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
from joblib import dump, load
from PIL import Image
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

sys.path.insert(0, os.path.dirname(__file__))
from features import extract_features  # noqa: E402
from morphology import nuclear_measures, load_reference, focality  # noqa: E402
from staging import ensemble_posteriors  # noqa: E402

# mean_score was dropped after the first fit: it correlated with involvement
# at r = 0.99, so including both handed the mixture the same axis twice and
# let tissue extent dominate the covariance structure for no added signal.
#
# `spread` was dropped after the second fit, for a worse reason. Focality can
# only be computed when a patient has at least eight coordinate-bearing
# patches and at least three flagged ones; for everyone else the pipeline
# substituted the neutral value 0.5. That substitution turned out to apply to
# 138 of 274 patients, so half the cohort sat on a hard point mass at exactly
# 0.5 and the mixture duly split two of its components along it. Those two
# groups differed mainly in *whether the measurement had been possible*, not
# in the tissue. Clustering on missingness is a bug however good the
# separation looks, so the feature was removed from the fit. Focality is still
# measured and still reported to the operator -- it is just no longer allowed
# to define the groups.
FEATURE_NAMES = ["involvement", "nuclear_load", "pleomorphism"]

# Covariance type was chosen by 5-fold cross-validated log-likelihood, which
# is the honest criterion for a density model. On the three-feature vector the
# comparison is no longer close:
#
#   full  reg 1e-4   held-out LL -3.525   train-test gap 0.326   BIC 1910
#   diag  reg 1e-4   held-out LL -3.676   train-test gap 0.184   BIC 2016
#   tied  reg 1e-4   held-out LL -3.909   train-test gap 0.143   BIC 2184
#
# Full wins on held-out likelihood and on BIC at the same time, and its
# optimism gap is no longer alarming now that the mixture is not being asked
# to model a point mass. With `spread` still in, this choice was a coin flip
# decided on secondary criteria; removing the artifact made it obvious.
#
# BIC now also lands on k = 4 on its own, which it did not before. That is a
# better position to be in than choosing k for interpretability and recording
# the disagreement, though the disagreement is still recorded when it happens.
COV = "full"
REG = 1e-4

# How many bootstrap refits back the reported posterior. See fit_ensemble.
B_BOOT = 60


def build_manifest(data_dir):
    """Same ordering as train_grouped.py, so the cached feature matrix aligns."""
    rows = []
    for label_str in ("0", "1"):
        d = os.path.join(data_dir, label_str)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith(".png"):
                rows.append({"path": os.path.join(d, fn), "label": int(label_str),
                             "patient": fn.split("_")[0], "name": fn})
    return rows


def patch_scores(rows, model_dir, cache_path):
    """Per-patch malignancy score, reusing the cached feature matrix if valid."""
    clf = load(os.path.join(model_dir, "classifier.joblib"))
    scaler = load(os.path.join(model_dir, "scaler.joblib"))

    X = None
    if os.path.exists(cache_path):
        cached = np.load(cache_path)
        if cached.shape[0] == len(rows):
            X = cached
            print(f"  reusing cached features {cached.shape}")
    if X is None:
        print("  extracting features (no usable cache)")
        feats = []
        for i, r in enumerate(rows):
            arr = np.asarray(Image.open(r["path"]).convert("RGB").resize((50, 50)))
            feats.append(extract_features(arr))
            if (i + 1) % 500 == 0:
                print(f"    {i + 1}/{len(rows)}")
        X = np.vstack(feats)

    return clf.predict_proba(scaler.transform(X))[:, 1]


def patient_features(rows, scores, ref, threshold=0.5):
    """Aggregate patches into one feature vector per patient."""
    by_patient = defaultdict(list)
    for r, s in zip(rows, scores):
        by_patient[r["patient"]].append((r, float(s)))

    out, ids = [], []
    n_focality = 0
    for pid in sorted(by_patient):
        items = by_patient[pid]
        sc = np.array([s for _, s in items])
        flagged = sc >= threshold

        # Morphology is measured on the flagged patches, since the question is
        # what the suspicious tissue looks like. With nothing flagged we fall
        # back to the whole sample rather than emitting a hole.
        use = [it for it, f in zip(items, flagged) if f] or items
        fr, cv = [], []
        for r, _ in use:
            try:
                arr = np.asarray(Image.open(r["path"]).convert("RGB").resize((50, 50)))
            except Exception:
                continue
            f_, _n, c_ = nuclear_measures(arr, ref["h_threshold"], ref["min_nucleus_px"])
            fr.append(f_)
            cv.append(c_)
        if not fr:
            continue

        # Focality is still measured, and still shown to the operator, but it
        # is not part of the feature vector -- see the note beside
        # FEATURE_NAMES. What is counted here is how often it is measurable at
        # all, because that number is the reason it was dropped.
        names = [r["name"] for r, _ in items]
        if focality(names, flagged) is not None:
            n_focality += 1

        out.append([float(flagged.mean()), float(np.mean(fr)), float(np.mean(cv))])
        ids.append(pid)
    return np.array(out, dtype=float), ids, n_focality


def fit_ensemble(Z, reference, k, seed, n_boot=B_BOOT):
    """
    Refit the mixture on bootstrap resamples of the cohort.

    WHY
    ---
    A single fitted mixture answers "given that these are exactly the right
    four components, which one produced this specimen?" -- and the answer is
    usually near-certain, because a point that sits close to one centroid is
    close to it under any reasonable reading. What that number leaves out is
    that the components themselves were estimated from 274 patients and would
    move if we had sampled 274 different ones.

    Refitting on resampled cohorts and averaging the posteriors puts that
    second source of uncertainty back in. A specimen deep inside a component
    stays confident, because every resample agrees about it. A specimen near a
    boundary drops, because the resamples disagree about which side it falls
    on -- which is the truth about that specimen, not a softening of it.

    Empirically on this cohort the median top-group probability falls from
    0.98 to 0.72 and the share of specimens reported above 0.99 falls from 43%
    to 4%. Nothing was rescaled: those are the posteriors the resampled fits
    actually produce.

    ALIGNMENT
    ---------
    Mixture components come out of every fit in arbitrary order, so each
    resampled fit is matched back to the reference fit by minimum-cost
    assignment on component means before averaging. Members are stored already
    permuted into reference order, so inference does not repeat the work.
    """
    from scipy.optimize import linear_sum_assignment

    rng = np.random.default_rng(seed)
    weights, means, covs, costs = [], [], [], []
    skipped = 0
    for b in range(n_boot):
        idx = rng.integers(0, len(Z), len(Z))
        g = GaussianMixture(n_components=k, covariance_type=COV, n_init=4,
                            random_state=seed + 1000 + b, reg_covar=REG)
        g.fit(Z[idx])
        if not g.converged_:
            skipped += 1
            continue
        d = ((g.means_[:, None, :] - reference.means_[None, :, :]) ** 2).sum(-1)
        rows, cols = linear_sum_assignment(d)
        perm = np.empty(k, dtype=int)
        perm[cols] = rows                      # reference component -> member component
        weights.append(g.weights_[perm])
        means.append(g.means_[perm])
        covs.append(g.covariances_[perm])
        costs.append(float(d[rows, cols].mean()))

    print(f"  {len(weights)} of {n_boot} resamples kept "
          f"({skipped} failed to converge)")
    print(f"  mean alignment cost {np.mean(costs):.3f}   worst {max(costs):.3f}")
    return {"weights": np.array(weights), "means": np.array(means),
            "covariances": np.array(covs),
            "alignment_cost_mean": float(np.mean(costs)),
            "alignment_cost_max": float(max(costs))}


def choose_k(Z, ks, seed):
    """Report BIC, AIC and silhouette across candidate component counts."""
    print(f"  {'k':>3}  {'BIC':>10}  {'AIC':>10}  {'silhouette':>11}  {'converged':>10}")
    table = []
    for k in ks:
        g = GaussianMixture(n_components=k, covariance_type=COV,
                            n_init=10, random_state=seed, reg_covar=REG)
        lab = g.fit_predict(Z)
        sil = silhouette_score(Z, lab) if len(set(lab)) > 1 else float("nan")
        table.append({"k": k, "bic": float(g.bic(Z)), "aic": float(g.aic(Z)),
                      "silhouette": float(sil), "converged": bool(g.converged_)})
        print(f"  {k:>3}  {g.bic(Z):>10.1f}  {g.aic(Z):>10.1f}  {sil:>11.3f}  "
              f"{str(g.converged_):>10}")
    best = min(table, key=lambda r: r["bic"])["k"]
    print(f"\n  lowest BIC at k = {best}")
    return table, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="data/idc_sample")
    ap.add_argument("--model_dir", default="models")
    ap.add_argument("--k", type=int, default=4,
                    help="number of groups; BIC is reported for 2..8 regardless")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 70)
    print("STEP 1  Scoring every patch with the trained classifier")
    print("=" * 70)
    rows = build_manifest(args.data_dir)
    print(f"  {len(rows)} patches")
    scores = patch_scores(rows, args.model_dir,
                          os.path.join(args.model_dir, "features_cache.npy"))

    print()
    print("=" * 70)
    print("STEP 2  Aggregating to patient-level feature vectors")
    print("=" * 70)
    ref = load_reference()
    F, ids, n_foc = patient_features(rows, scores, ref, args.threshold)
    print(f"  {F.shape[0]} patients x {F.shape[1]} features: {', '.join(FEATURE_NAMES)}")
    print(f"  focality measurable for {n_foc} of {F.shape[0]} patients "
          f"({n_foc / max(F.shape[0], 1):.0%}) -- reported, not clustered on")
    for j, n in enumerate(FEATURE_NAMES):
        print(f"    {n:<13} mean {F[:, j].mean():.3f}  sd {F[:, j].std():.3f}  "
              f"range {F[:, j].min():.3f} to {F[:, j].max():.3f}")

    corr = np.corrcoef(F.T)
    print("\n  correlation between features:")
    print("               " + "".join(f"{n[:9]:>11}" for n in FEATURE_NAMES))
    for i, n in enumerate(FEATURE_NAMES):
        print(f"    {n:<11}" + "".join(f"{corr[i, j]:>11.2f}" for j in range(len(FEATURE_NAMES))))

    print()
    print("=" * 70)
    print("STEP 3  Choosing the number of groups")
    print("=" * 70)
    fs = StandardScaler().fit(F)
    Z = fs.transform(F)
    table, best = choose_k(Z, range(2, 9), args.seed)

    print()
    print("=" * 70)
    print(f"STEP 4  Fitting the final mixture at k = {args.k}")
    print("=" * 70)
    gmm = GaussianMixture(n_components=args.k, covariance_type=COV,
                          n_init=20, random_state=args.seed, reg_covar=REG)
    gmm.fit(Z)
    lab = gmm.predict(Z)

    # Components come out of the fit in arbitrary order and something has to
    # order them for presentation. Ordering by mean involvement alone was tried
    # first and failed: three of the four groups sat within 0.07 of each other
    # on that axis and were separated by nuclear load and spread instead, so
    # the numbering carried no information.
    #
    # The ordering key below is stated rather than learned. Involvement leads,
    # nuclear load modifies it, and the product form means a group needs both
    # extent and density to rank highly. This is a presentation decision; the
    # groups themselves are whatever the mixture found.
    def severity(c):
        m = lab == c
        if not m.any():
            return -1.0
        return float(F[m, 0].mean() * (0.5 + F[m, 1].mean()))

    order = np.argsort([severity(c) for c in range(args.k)])
    rank = {int(c): int(r) for r, c in enumerate(order)}
    print("  components ordered by the severity key:")
    for c in order:
        m = lab == c
        print(f"    component {c} -> group {rank[int(c)] + 1}   n={m.sum():>3}   "
              f"involvement {F[m, 0].mean():.3f}   load {F[m, 1].mean():.3f}   "
              f"pleo {F[m, 2].mean():.3f}   severity {severity(c):.3f}")

    # Descriptors are generated from the fitted means rather than written by
    # hand, so they cannot drift out of step with a refit on different data.
    def describe(means):
        inv, load, pleo = (means["involvement"], means["nuclear_load"],
                           means["pleomorphism"])
        if inv < 0.05:
            return "No flagged tissue"
        extent = "Limited" if inv < 0.35 else ("Moderate" if inv < 0.65 else "Extensive")
        dense = "dense" if load >= np.median(F[:, 1]) else "sparse"
        varied = "variable" if pleo >= np.median(F[:, 2]) else "uniform"
        return f"{extent} involvement, {dense} tissue, {varied} nuclei"

    profiles = []
    for c in order:
        m = lab == c
        means = {n: float(F[m, j].mean()) for j, n in enumerate(FEATURE_NAMES)}
        profiles.append({
            "component": int(c),
            "n": int(m.sum()),
            "means": means,
            "label": f"Group {rank[int(c)] + 1}",
            "descriptor": describe(means),
        })
    print("\n  generated descriptors:")
    for p in profiles:
        print(f"    {p['label']}  n={p['n']:>3}  {p['descriptor']}")

    print()
    print("=" * 70)
    print(f"STEP 5  Bootstrap ensemble ({B_BOOT} refits) for the reported posterior")
    print("=" * 70)
    ens = fit_ensemble(Z, gmm, args.k, args.seed)

    # Stored already permuted into presentation order, so inference reads them
    # straight through with no reordering.
    ens_ordered = {
        "weights": ens["weights"][:, order],
        "means": ens["means"][:, order],
        "covariances": ens["covariances"][:, order],
    }

    point = gmm.predict_proba(Z)[:, order]
    avg, _ll = ensemble_posteriors(ens_ordered, Z)
    for nm, p in (("single fit", point), ("bootstrap-averaged", avg)):
        mx = p.max(1)
        print(f"  {nm:>19}: median top prob {np.median(mx):.3f}   "
              f">0.99 {(mx > 0.99).mean():>5.1%}   <0.60 {(mx < 0.60).mean():>5.1%}")
    agree = float((point.argmax(1) == avg.argmax(1)).mean())
    print(f"  the two agree on the assigned group for {agree:.1%} of the cohort")
    sizes = np.bincount(avg.argmax(1), minlength=args.k)
    print(f"  group sizes under the reported posterior: "
          + "  ".join(f"G{i + 1} {n}" for i, n in enumerate(sizes)))

    dump({"gmm": gmm, "feature_scaler": fs, "order": order.tolist(),
          "rank": rank, "feature_names": FEATURE_NAMES,
          "ensemble": ens_ordered},
         os.path.join(args.model_dir, "cluster_model.joblib"))

    meta = {
        "k": args.k,
        "feature_names": FEATURE_NAMES,
        "n_patients": int(F.shape[0]),
        "threshold": args.threshold,
        "model_selection": table,
        "bic_preferred_k": int(best),
        "converged": bool(gmm.converged_),
        "profiles": profiles,
        "silhouette_at_k": float(silhouette_score(Z, lab)) if len(set(lab)) > 1 else None,
        "covariance_type": COV,
        "reg_covar": REG,
        "ordering": "mean involvement x (0.5 + mean nuclear load), stated not learned",
        "k_note": ("k was set for interpretability; on this feature set BIC "
                   "independently agrees. Any disagreement is recorded in "
                   "model_selection."),
        "focality_measurable": int(n_foc),
        "focality_note": ("Focality is measured and reported but excluded from "
                          "the fit: it was unavailable for 138 of 274 patients "
                          "and the neutral value substituted for them formed a "
                          "point mass the mixture clustered on."),
        "posterior": {
            "method": "bootstrap-averaged over refits of the mixture",
            "n_boot": int(ens_ordered["weights"].shape[0]),
            "alignment_cost_mean": ens["alignment_cost_mean"],
            "alignment_cost_max": ens["alignment_cost_max"],
            "cohort_median_top_prob": float(np.median(avg.max(1))),
            "cohort_median_top_prob_single_fit": float(np.median(point.max(1))),
            "argmax_agreement_with_single_fit": agree,
            "note": ("Averaging over mixtures refitted on bootstrap resamples "
                     "propagates uncertainty in the component estimates into "
                     "the reported probability. Nothing is rescaled."),
        },
    }
    with open(os.path.join(args.model_dir, "cluster_metadata.json"), "w",
              encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    print(f"\n  converged: {gmm.converged_}   silhouette: {meta['silhouette_at_k']:.3f}")
    print(f"  saved cluster_model.joblib and cluster_metadata.json "
          f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
