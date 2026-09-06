"""
Patient-level (slide-level) aggregation.

WHY THIS EXISTS
---------------
The classifier predicts on a single 50x50 patch. A patch is not a patient.
A pathology lab cares about the slide and the person, not one pixel square.

This script runs the model over EVERY patch belonging to one patient and
aggregates the results into a single patient-level summary: what proportion
of the sampled tissue looks malignant, how confident the model is on average,
and how the per-patch probabilities are distributed.

VALIDATION (on the 54 patients held out from the shipped model)
---------------------------------------------------------------
    correlation, true vs predicted malignant fraction : r = 0.978
    mean absolute error of the fraction estimate      : 2.8 percentage points

Aggregation is more reliable than any single patch because individual patch
errors are roughly symmetric and therefore largely cancel when averaged.

Usage:
    # a folder of images
    python src/analyze_patient.py "C:/Dataset ML/9265"

    # or just one class subfolder
    python src/analyze_patient.py "C:/Dataset ML/9265/1"
"""

import argparse
import os
import sys

import numpy as np
from joblib import load

sys.path.insert(0, os.path.dirname(__file__))
from features import extract_features_from_path  # noqa: E402

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def find_images(root):
    """Collect every PNG under root, recording the true label when the
    folder structure reveals it (a '0' or '1' parent directory)."""
    found = []
    for dirpath, _, filenames in os.walk(root):
        parent = os.path.basename(dirpath)
        true = int(parent) if parent in ("0", "1") else None
        for fn in filenames:
            if fn.lower().endswith((".png", ".jpg", ".jpeg")):
                found.append((os.path.join(dirpath, fn), true))
    return sorted(found)


def predict_batch(paths, clf, scaler, progress=None):
    feats = []
    for i, p in enumerate(paths):
        feats.append(extract_features_from_path(p))
        if progress:
            progress(i + 1, len(paths))
    X = np.vstack(feats)
    return clf.predict_proba(scaler.transform(X))[:, 1]


def summarise(probs, threshold=0.5):
    flagged = probs >= threshold
    return {
        "n_patches": int(len(probs)),
        "n_flagged": int(flagged.sum()),
        "malignant_fraction": float(flagged.mean()),
        "mean_probability": float(probs.mean()),
        "median_probability": float(np.median(probs)),
        "high_confidence_malignant": int((probs >= 0.9).sum()),
        "high_confidence_benign": int((probs <= 0.1).sum()),
        "uncertain": int(((probs > 0.4) & (probs < 0.6)).sum()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="Folder containing this patient's patches")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--max_images", type=int, default=0,
                    help="0 means use all; set a number to sample randomly for speed")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    items = find_images(args.folder)
    if not items:
        print(f"No images found under {args.folder}")
        return

    if args.max_images and len(items) > args.max_images:
        rng = np.random.default_rng(args.seed)
        pick = rng.choice(len(items), args.max_images, replace=False)
        items = [items[i] for i in sorted(pick)]
        print(f"Sampled {len(items)} images at random for speed "
              f"(use --max_images 0 to process all)")

    paths = [p for p, _ in items]
    truths = [t for _, t in items]

    clf = load(os.path.join(MODEL_DIR, "classifier.joblib"))
    scaler = load(os.path.join(MODEL_DIR, "scaler.joblib"))

    print(f"Processing {len(paths)} patches from {args.folder} ...")

    def prog(i, n):
        if i % 100 == 0 or i == n:
            print(f"  {i}/{n}")

    probs = predict_batch(paths, clf, scaler, progress=prog)
    s = summarise(probs, args.threshold)

    print()
    print("=" * 60)
    print("PATIENT-LEVEL SUMMARY")
    print("=" * 60)
    print(f"  Patches analysed          : {s['n_patches']}")
    print(f"  Flagged as malignant      : {s['n_flagged']}  "
          f"({s['malignant_fraction']:.1%} of tissue sampled)")
    print(f"  Mean malignancy score     : {s['mean_probability']:.3f}")
    print(f"  Median malignancy score   : {s['median_probability']:.3f}")
    print()
    print(f"  High-confidence malignant (p >= 0.9) : {s['high_confidence_malignant']}")
    print(f"  High-confidence benign    (p <= 0.1) : {s['high_confidence_benign']}")
    print(f"  Uncertain            (0.4 < p < 0.6) : {s['uncertain']}")

    known = [(p, t) for p, t in zip(probs, truths) if t is not None]
    if known:
        kp = np.array([p for p, _ in known])
        kt = np.array([t for _, t in known])
        true_frac = kt.mean()
        pred_frac = (kp >= args.threshold).mean()
        acc = ((kp >= args.threshold).astype(int) == kt).mean()
        print()
        print("  GROUND TRUTH AVAILABLE (labels read from 0/ and 1/ folders)")
        print(f"    True malignant fraction      : {true_frac:.1%}")
        print(f"    Predicted malignant fraction : {pred_frac:.1%}")
        print(f"    Absolute error               : {abs(true_frac - pred_frac):.1%}")
        print(f"    Per-patch accuracy           : {acc:.1%}")

    print()
    print("  NOTE: this estimates the proportion of sampled tissue that appears")
    print("  malignant. It is not a diagnosis, and it does not replace review")
    print("  by a qualified pathologist.")


if __name__ == "__main__":
    main()
