"""
Calibrate the morphological reference against our own cohort.

The band boundaries used by morphology.py are tertiles of the distribution
observed across the patients in this dataset. They are not clinical
thresholds and this script is what makes that statement true rather than
decorative: it measures every patient, then splits the resulting distribution
into thirds.

The haematoxylin threshold is calibrated the same way, as a percentile of the
pooled channel distribution across a sample of patches, so that it adapts to
the staining of whatever cohort it is run on instead of being a constant
copied from another dataset.

Only malignant patches contribute to the nuclear statistics, because the
question the profile answers is what the suspicious tissue looks like.

Usage:
    python src/build_morphology_reference.py --data_dir data/idc_sample
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
from PIL import Image
from skimage.color import rgb2hed

sys.path.insert(0, os.path.dirname(__file__))
from morphology import nuclear_measures  # noqa: E402


def collect(data_dir):
    """Map patient id -> list of (path, label)."""
    by_patient = defaultdict(list)
    for label_str in ("0", "1"):
        d = os.path.join(data_dir, label_str)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith((".png", ".jpg", ".jpeg")):
                by_patient[fn.split("_")[0]].append(
                    (os.path.join(d, fn), int(label_str)))
    return by_patient


def calibrate_threshold(paths, percentile, cap=400):
    """Pick the haematoxylin cut-off from the pooled channel distribution."""
    rng = np.random.default_rng(42)
    if len(paths) > cap:
        paths = [paths[i] for i in sorted(rng.choice(len(paths), cap, replace=False))]
    pooled = []
    for p in paths:
        try:
            a = np.asarray(Image.open(p).convert("RGB"))
            pooled.append(rgb2hed(a)[:, :, 0].ravel())
        except Exception:
            continue
    if not pooled:
        raise SystemExit("no readable images for threshold calibration")
    return float(np.percentile(np.concatenate(pooled), percentile))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="data/idc_sample")
    ap.add_argument("--out", default="models/morphology_reference.json")
    ap.add_argument("--h_percentile", type=float, default=75.0)
    ap.add_argument("--min_nucleus_px", type=int, default=4)
    args = ap.parse_args()

    print("=" * 68)
    print("STEP 1  Collecting patients")
    print("=" * 68)
    by_patient = collect(args.data_dir)
    all_paths = [p for v in by_patient.values() for p, _ in v]
    print(f"  patients: {len(by_patient)}   patches: {len(all_paths)}")

    print()
    print("=" * 68)
    print("STEP 2  Calibrating the haematoxylin threshold")
    print("=" * 68)
    h_thr = calibrate_threshold(all_paths, args.h_percentile)
    print(f"  percentile {args.h_percentile:.0f} of the pooled channel -> {h_thr:.4f}")

    print()
    print("=" * 68)
    print("STEP 3  Measuring every patient")
    print("=" * 68)
    t0 = time.time()
    rows = []
    for i, (pid, items) in enumerate(sorted(by_patient.items()), start=1):
        mal = [p for p, lab in items if lab == 1]
        use = mal if mal else [p for p, _ in items]
        fr, cv = [], []
        for p in use:
            try:
                a = np.asarray(Image.open(p).convert("RGB"))
            except Exception:
                continue
            f, _n, c = nuclear_measures(a, h_thr, args.min_nucleus_px)
            fr.append(f)
            cv.append(c)
        if fr:
            rows.append({"patient": pid, "n": len(fr),
                         "nuclear_fraction": float(np.mean(fr)),
                         "size_cv": float(np.mean(cv))})
        if i % 50 == 0:
            print(f"  {i}/{len(by_patient)} patients  ({time.time() - t0:.0f}s)")

    if len(rows) < 10:
        raise SystemExit("too few patients measured to calibrate")

    frac = np.array([r["nuclear_fraction"] for r in rows])
    cvs = np.array([r["size_cv"] for r in rows])

    print()
    print("=" * 68)
    print("STEP 4  Tertiles across the cohort")
    print("=" * 68)
    ref = {
        "h_threshold": h_thr,
        "h_percentile": args.h_percentile,
        "min_nucleus_px": args.min_nucleus_px,
        "nuclear_load": {"t1": float(np.percentile(frac, 33.3)),
                         "t2": float(np.percentile(frac, 66.7))},
        "pleomorphism": {"t1": float(np.percentile(cvs, 33.3)),
                         "t2": float(np.percentile(cvs, 66.7))},
        "n_patients": len(rows),
        "calibrated": True,
        "distribution": {
            "nuclear_fraction": {
                "min": float(frac.min()), "p25": float(np.percentile(frac, 25)),
                "median": float(np.median(frac)), "p75": float(np.percentile(frac, 75)),
                "max": float(frac.max()), "mean": float(frac.mean()),
                "std": float(frac.std()),
            },
            "size_cv": {
                "min": float(cvs.min()), "p25": float(np.percentile(cvs, 25)),
                "median": float(np.median(cvs)), "p75": float(np.percentile(cvs, 75)),
                "max": float(cvs.max()), "mean": float(cvs.mean()),
                "std": float(cvs.std()),
            },
        },
    }

    print(f"  nuclear load   tertiles at {ref['nuclear_load']['t1']:.4f} "
          f"and {ref['nuclear_load']['t2']:.4f}")
    print(f"                 range {frac.min():.4f} to {frac.max():.4f}, "
          f"median {np.median(frac):.4f}")
    print(f"  pleomorphism   tertiles at {ref['pleomorphism']['t1']:.4f} "
          f"and {ref['pleomorphism']['t2']:.4f}")
    print(f"                 range {cvs.min():.4f} to {cvs.max():.4f}, "
          f"median {np.median(cvs):.4f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(ref, fh, indent=2)
    print()
    print(f"  written to {args.out}  ({len(rows)} patients, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
