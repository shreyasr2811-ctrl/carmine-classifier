"""
Patient-grouped training and evaluation for the IDC breast histopathology
classifier.

WHY THIS FILE EXISTS
--------------------
The original train.py split the data at the PATCH level. Because many
patches come from the same patient (and therefore the same physical slide,
the same staining batch, and the same scanner session), patches from one
patient ended up in both the training set and the test set. The model could
therefore score well partly by recognising a patient's slide, not by
recognising cancer. This is a well-known leakage failure mode in
histopathology machine learning, and it inflates reported accuracy.

This script fixes that by grouping on patient ID, which is the prefix of
every filename (e.g. "10253_idx5_x501_y351_class1.png" -> patient 10253).
No patient ever appears on both sides of a split.

It deliberately reports BOTH the old (leaky) number and the new (grouped)
number, because the size of the gap is itself the scientific finding.

Usage:
    python src/train_grouped.py --data_dir data/idc_sample --out_dir models
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, roc_auc_score, confusion_matrix, classification_report,
    precision_recall_fscore_support,
)
from xgboost import XGBClassifier

sys.path.insert(0, os.path.dirname(__file__))
from features import extract_features_from_path  # noqa: E402


# ----------------------------------------------------------------------
# Data manifest
# ----------------------------------------------------------------------

def build_manifest(data_dir):
    """Build a table of every image with its label AND its patient ID.

    The patient ID is the filename prefix before the first underscore.
    This is the grouping key that prevents leakage.
    """
    rows = []
    for label_str in ("0", "1"):
        cls_dir = os.path.join(data_dir, label_str)
        if not os.path.isdir(cls_dir):
            continue
        for fname in os.listdir(cls_dir):
            if fname.lower().endswith(".png"):
                patient_id = fname.split("_")[0]
                rows.append({
                    "path": os.path.join(cls_dir, fname),
                    "label": int(label_str),
                    "patient_id": patient_id,
                })
    return pd.DataFrame(rows)


def extract_all_features(paths, cache_path=None, log_every=500):
    """Extract features for every image once, with optional disk caching.

    Feature extraction is stateless per image, so doing it for the whole
    dataset up front introduces no leakage. Only the SCALER must be fit
    per-split, which is handled separately below.
    """
    if cache_path and os.path.exists(cache_path):
        print(f"  loading cached features from {cache_path}")
        return np.load(cache_path)

    feats = []
    t0 = time.time()
    for i, p in enumerate(paths):
        feats.append(extract_features_from_path(p))
        if (i + 1) % log_every == 0:
            print(f"  extracted {i + 1}/{len(paths)} ({time.time() - t0:.1f}s)")
    X = np.vstack(feats)
    if cache_path:
        np.save(cache_path, X)
        print(f"  cached features to {cache_path}")
    return X


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------

def full_metrics(y_true, y_prob, threshold=0.5):
    """Return the full medical-classifier metric set, not just accuracy."""
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    sensitivity = tp / (tp + fn) if (tp + fn) else float("nan")   # recall, malignant
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")   # recall, benign
    ppv = tp / (tp + fp) if (tp + fp) else float("nan")           # precision
    npv = tn / (tn + fn) if (tn + fn) else float("nan")
    f1 = 2 * ppv * sensitivity / (ppv + sensitivity) if (ppv + sensitivity) else float("nan")

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "auc": roc_auc_score(y_true, y_prob),
        "sensitivity_recall_malignant": sensitivity,
        "specificity_recall_benign": specificity,
        "ppv_precision": ppv,
        "npv": npv,
        "f1": f1,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "n": int(len(y_true)),
    }


def wilson_ci(successes, n, z=1.96):
    """Wilson score interval. More reliable than the normal approximation
    at small n or extreme proportions."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (centre - half, centre + half)


def make_models(seed):
    return {
        "dummy_baseline": DummyClassifier(strategy="most_frequent", random_state=seed),
        "logistic_regression": LogisticRegression(max_iter=2000, random_state=seed),
        "random_forest": RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, n_jobs=-1,
            random_state=seed, class_weight="balanced",
        ),
        "xgboost": XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
            n_jobs=-1, random_state=seed,
        ),
    }


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="data/idc_sample")
    ap.add_argument("--out_dir", default="models")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("=" * 72)
    print("STEP 1: Building manifest with patient IDs")
    print("=" * 72)
    df = build_manifest(args.data_dir)
    n_patients = df["patient_id"].nunique()
    print(f"Images: {len(df)}  (benign={sum(df.label == 0)}, malignant={sum(df.label == 1)})")
    print(f"Unique patients: {n_patients}")
    print(f"Patches per patient: min={df.groupby('patient_id').size().min()}, "
          f"median={int(df.groupby('patient_id').size().median())}, "
          f"max={df.groupby('patient_id').size().max()}")

    print()
    print("=" * 72)
    print("STEP 2: Extracting features once for all images")
    print("=" * 72)
    cache = os.path.join(args.out_dir, "features_cache.npy")
    X = extract_all_features(df["path"].tolist(), cache_path=cache)
    y = df["label"].values
    groups = df["patient_id"].values
    print(f"Feature matrix: {X.shape}")

    results = {"n_images": len(df), "n_patients": int(n_patients), "feature_dim": int(X.shape[1])}

    # ------------------------------------------------------------------
    # STEP 3: The leaky baseline, reproduced deliberately for comparison
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("STEP 3: NAIVE patch-level split (the ORIGINAL, LEAKY approach)")
    print("        Reproduced only so we can measure how much it inflates.")
    print("=" * 72)

    idx = np.arange(len(df))
    tr_idx, te_idx = train_test_split(
        idx, test_size=0.30, stratify=y, random_state=args.seed
    )
    scaler = StandardScaler().fit(X[tr_idx])
    model = XGBClassifier(
        n_estimators=400, max_depth=6, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, eval_metric="logloss", n_jobs=-1, random_state=args.seed,
    )
    model.fit(scaler.transform(X[tr_idx]), y[tr_idx])
    naive_prob = model.predict_proba(scaler.transform(X[te_idx]))[:, 1]
    naive = full_metrics(y[te_idx], naive_prob)

    # how much patient overlap did the naive split actually have?
    overlap = len(set(groups[tr_idx]) & set(groups[te_idx]))
    print(f"Patients appearing in BOTH train and test: {overlap} of {n_patients}")
    print(f"  accuracy    = {naive['accuracy']:.4f}")
    print(f"  AUC         = {naive['auc']:.4f}")
    print(f"  sensitivity = {naive['sensitivity_recall_malignant']:.4f}")
    print(f"  specificity = {naive['specificity_recall_benign']:.4f}")
    naive["patients_leaked"] = int(overlap)
    results["naive_patch_level_split"] = naive

    # ------------------------------------------------------------------
    # STEP 4: Patient-grouped cross-validation (the honest evaluation)
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print(f"STEP 4: PATIENT-GROUPED {args.folds}-fold cross-validation")
    print("        No patient appears in both train and test in any fold.")
    print("=" * 72)

    sgkf = StratifiedGroupKFold(n_splits=args.folds, shuffle=True, random_state=args.seed)
    cv_scores = {name: [] for name in make_models(args.seed)}

    for fold, (tr, te) in enumerate(sgkf.split(X, y, groups), start=1):
        leak = len(set(groups[tr]) & set(groups[te]))
        assert leak == 0, f"Fold {fold} leaked {leak} patients"

        sc = StandardScaler().fit(X[tr])          # fit on TRAIN ONLY, every fold
        Xtr, Xte = sc.transform(X[tr]), sc.transform(X[te])

        line = [f"  fold {fold} (test n={len(te)}, patients={len(set(groups[te]))})"]
        for name, mdl in make_models(args.seed).items():
            mdl.fit(Xtr, y[tr])
            if hasattr(mdl, "predict_proba"):
                prob = mdl.predict_proba(Xte)[:, 1]
            else:
                prob = mdl.decision_function(Xte)
            m = full_metrics(y[te], prob)
            cv_scores[name].append(m)
            line.append(f"{name}={m['accuracy']:.3f}")
        print("  ".join(line))

    print()
    print("  Cross-validated means (+/- standard deviation across folds):")
    cv_summary = {}
    for name, folds in cv_scores.items():
        agg = {}
        for key in ("accuracy", "auc", "sensitivity_recall_malignant",
                    "specificity_recall_benign", "ppv_precision", "npv", "f1"):
            vals = np.array([f[key] for f in folds], dtype=float)
            agg[key] = {"mean": float(np.nanmean(vals)), "std": float(np.nanstd(vals))}
        cv_summary[name] = agg
        print(f"    {name:22s} acc={agg['accuracy']['mean']:.4f} +/- {agg['accuracy']['std']:.4f}   "
              f"AUC={agg['auc']['mean']:.4f} +/- {agg['auc']['std']:.4f}   "
              f"sens={agg['sensitivity_recall_malignant']['mean']:.4f}   "
              f"spec={agg['specificity_recall_benign']['mean']:.4f}")
    results["grouped_cross_validation"] = cv_summary
    results["n_folds"] = args.folds

    # ------------------------------------------------------------------
    # STEP 5: Final grouped hold-out model for deployment
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("STEP 5: Final model, patient-grouped train/test hold-out")
    print("=" * 72)

    # take one fold of a 5-way grouped split as the held-out test set
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=args.seed)
    tr_idx, te_idx = next(iter(outer.split(X, y, groups)))
    assert len(set(groups[tr_idx]) & set(groups[te_idx])) == 0

    scaler = StandardScaler().fit(X[tr_idx])
    final = XGBClassifier(
        n_estimators=400, max_depth=6, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, eval_metric="logloss", n_jobs=-1, random_state=args.seed,
    )
    final.fit(scaler.transform(X[tr_idx]), y[tr_idx])
    test_prob = final.predict_proba(scaler.transform(X[te_idx]))[:, 1]
    grouped = full_metrics(y[te_idx], test_prob)

    n_test = grouped["n"]
    acc_lo, acc_hi = wilson_ci(round(grouped["accuracy"] * n_test), n_test)

    print(f"  Train: {len(tr_idx)} patches from {len(set(groups[tr_idx]))} patients")
    print(f"  Test:  {len(te_idx)} patches from {len(set(groups[te_idx]))} patients")
    print(f"  Patient overlap: 0  (verified)")
    print()
    print(f"  accuracy    = {grouped['accuracy']:.4f}   95% CI [{acc_lo:.4f}, {acc_hi:.4f}]")
    print(f"  AUC         = {grouped['auc']:.4f}")
    print(f"  sensitivity = {grouped['sensitivity_recall_malignant']:.4f}  (malignant recall)")
    print(f"  specificity = {grouped['specificity_recall_benign']:.4f}  (benign recall)")
    print(f"  PPV         = {grouped['ppv_precision']:.4f}")
    print(f"  NPV         = {grouped['npv']:.4f}")
    print(f"  F1          = {grouped['f1']:.4f}")
    cm = grouped["confusion_matrix"]
    print(f"  confusion   = TN {cm['tn']}  FP {cm['fp']}  FN {cm['fn']}  TP {cm['tp']}")
    print()
    print(classification_report(y[te_idx], (test_prob >= 0.5).astype(int),
                                target_names=["benign", "malignant(IDC)"]))

    grouped["accuracy_95ci"] = [acc_lo, acc_hi]
    grouped["n_train_patches"] = int(len(tr_idx))
    grouped["n_test_patches"] = int(len(te_idx))
    grouped["n_train_patients"] = int(len(set(groups[tr_idx])))
    grouped["n_test_patients"] = int(len(set(groups[te_idx])))
    results["grouped_holdout"] = grouped

    # ------------------------------------------------------------------
    # STEP 6: The headline comparison
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("STEP 6: LEAKAGE IMPACT")
    print("=" * 72)
    d_acc = naive["accuracy"] - grouped["accuracy"]
    d_auc = naive["auc"] - grouped["auc"]
    print(f"  Naive (leaky) accuracy   : {naive['accuracy']:.4f}")
    print(f"  Grouped (honest) accuracy: {grouped['accuracy']:.4f}")
    print(f"  Inflation from leakage   : {d_acc:+.4f} ({d_acc * 100:+.2f} percentage points)")
    print(f"  AUC inflation            : {d_auc:+.4f}")
    results["leakage_inflation"] = {"accuracy": float(d_acc), "auc": float(d_auc)}

    dump(final, os.path.join(args.out_dir, "classifier.joblib"))
    dump(scaler, os.path.join(args.out_dir, "scaler.joblib"))
    with open(os.path.join(args.out_dir, "metadata_grouped.json"), "w") as f:
        json.dump(results, f, indent=2)
    print()
    print(f"Saved patient-grouped model + scaler + metadata_grouped.json to {args.out_dir}/")


if __name__ == "__main__":
    main()
