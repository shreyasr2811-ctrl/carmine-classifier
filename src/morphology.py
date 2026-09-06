"""
Morphological profiling of a patient's tissue.

WHAT THIS IS
------------
The classifier answers one question: how much of the sampled tissue looks
malignant. This module answers three more, all of them measured directly from
the same images and coordinates:

    focality      is the involvement one region, a few regions, or scattered?
    nuclear load  how much of the tissue is nuclear material?
    pleomorphism  how variable are the nuclei in size?

WHAT THIS IS NOT
----------------
This is NOT cancer staging and it must never be presented as staging. Stage is
TNM: tumour size measured on the gross specimen, regional lymph node status
determined from a *different* tissue sample, and distant metastasis established
by imaging. None of those quantities exists anywhere in a 50x50 pixel patch of
breast tissue, and the IDC dataset carries no stage label to learn from. A
model trained on invented stage labels would emit confident numbers that mean
nothing.

It is also NOT a predicted histological grade. Nuclear pleomorphism and mitotic
activity are two of the three components of Nottingham grading, and nuclear
load relates loosely to the third, but this dataset carries no grade labels
either. What follows are *measurements*, reported as measurements.

HOW THE CATEGORIES WORK
-----------------------
The band boundaries are not clinical thresholds. They are tertiles of the
distribution observed across the patients in our own cohort, computed once by
build_morphology_reference.py and stored in models/morphology_reference.json.
A patient described as "high nuclear load" is therefore high *relative to this
cohort*, which is a defensible statement, rather than high on some absolute
scale, which would not be.

Membership is graded rather than hard. A value sitting close to a boundary
produces a split reading instead of an arbitrary assignment to one side, which
is the honest presentation when the underlying quantity is continuous. These
are rule-based memberships derived from measured statistics, not posterior
probabilities from a trained classifier, and the interface says so.
"""

from __future__ import annotations

import json
import os
import re

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2hed


REFERENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "models",
                              "morphology_reference.json")

# Fallback reference, used only when the calibrated file is absent. Values are
# the ones build_morphology_reference.py produced on the bundled sample.
_FALLBACK = {
    "h_threshold": 0.0354,
    "min_nucleus_px": 4,
    "nuclear_load": {"t1": 0.18, "t2": 0.34},
    "pleomorphism": {"t1": 0.62, "t2": 0.95},
    "n_patients": 0,
    "calibrated": False,
}

_COORD = re.compile(r"_x(\d+)_y(\d+)", re.IGNORECASE)


# --------------------------------------------------------------------------
# Reference
# --------------------------------------------------------------------------

def load_reference() -> dict:
    """Cohort reference values. Never raises; falls back to stored defaults."""
    try:
        with open(REFERENCE_PATH, "r", encoding="utf-8") as fh:
            ref = json.load(fh)
        ref.setdefault("calibrated", True)
        return ref
    except Exception:
        return dict(_FALLBACK)


# --------------------------------------------------------------------------
# Per-patch measurement
# --------------------------------------------------------------------------

def nuclear_measures(rgb: np.ndarray, h_threshold: float,
                     min_nucleus_px: int = 4) -> tuple[float, int, float]:
    """
    Measure nuclear material in one patch.

    Returns (nuclear_fraction, nucleus_count, size_cv).

    Colour deconvolution separates the haematoxylin signal from eosin, so the
    measurement responds to nuclear staining rather than to overall darkness.
    The threshold is global rather than per-patch on purpose: an Otsu
    threshold computed inside each patch would normalise away exactly the
    between-patch density difference we are trying to measure, and would
    "find" nuclei in a patch containing none.

    Touching nuclei merge into one component, so the count is a lower bound
    and the size spread is inflated in crowded fields. nuclear_fraction does
    not depend on separating them and is the more stable of the two.
    """
    h = rgb2hed(rgb)[:, :, 0]
    mask = h > h_threshold
    if mask.any():
        mask = ndi.binary_fill_holes(mask)
        # size filter written directly rather than via remove_small_objects,
        # whose min_size parameter is deprecated and changes meaning in 2.0
        lab0, n0 = ndi.label(mask)
        if n0:
            counts = np.bincount(lab0.ravel())
            keep = counts >= int(min_nucleus_px)
            keep[0] = False
            mask = keep[lab0]

    fraction = float(mask.mean())
    if not mask.any():
        return fraction, 0, 0.0

    lab, n = ndi.label(mask)
    if n == 0:
        return fraction, 0, 0.0

    areas = np.bincount(lab.ravel())[1:].astype(float)
    mean_a = areas.mean()
    size_cv = float(areas.std() / mean_a) if mean_a > 0 else 0.0
    return fraction, int(n), size_cv


def measure_patch(src, h_threshold: float, min_nucleus_px: int = 4):
    """Accepts a path or a file-like object. Returns None on unreadable input."""
    try:
        if hasattr(src, "seek"):
            src.seek(0)
        img = Image.open(src).convert("RGB")
        if img.size != (50, 50):
            img = img.resize((50, 50))
        return nuclear_measures(np.asarray(img), h_threshold, min_nucleus_px)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Graded membership
# --------------------------------------------------------------------------

def graded_bands(value: float, *boundaries, softness: float = 0.18) -> list[float]:
    """
    Convert a continuous measurement into a graded membership over N+1 bands,
    given N boundaries in ascending order.

    `softness` is a fraction of the mean gap between boundaries, so the
    transition width scales with the spread of the cohort rather than being
    fixed in absolute units. A value sitting exactly on a boundary splits
    evenly between the two bands it separates.
    """
    if len(boundaries) == 1 and isinstance(boundaries[0], (list, tuple)):
        boundaries = tuple(boundaries[0])
    ts = sorted(float(t) for t in boundaries)
    if not ts:
        return [1.0]

    gaps = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
    mean_gap = (sum(gaps) / len(gaps)) if gaps else max(abs(ts[0]), 1e-3)
    w = max(mean_gap * softness, 1e-9)

    # logistic weight for sitting above each boundary
    above = [1.0 / (1.0 + np.exp(-(value - t) / w)) for t in ts]

    out = [1.0 - above[0]]
    for i in range(len(ts) - 1):
        out.append(above[i] - above[i + 1])
    out.append(above[-1])

    arr = np.clip(np.array(out, dtype=float), 0.0, None)
    total = arr.sum()
    n = len(arr)
    return (arr / total).tolist() if total > 0 else [1.0 / n] * n


# --------------------------------------------------------------------------
# Spatial pattern
# --------------------------------------------------------------------------

def parse_coordinates(names: list[str]):
    out = []
    for n in names:
        m = _COORD.search(str(n))
        out.append((int(m.group(1)), int(m.group(2))) if m else None)
    return out


def focality(names: list[str], flagged: np.ndarray, step: int = 50) -> dict | None:
    """
    Describe how the flagged tissue is distributed across the slide.

    The patch coordinates are snapped back onto a grid and the flagged cells
    are grouped into connected regions. Two statistics then describe the
    pattern: how many separate regions there are, and what share of the
    flagged tissue sits in the largest one. A single dominant region is focal
    involvement; several comparable regions are multifocal; many small
    scattered ones are diffuse.

    Returns None when the filenames carry no usable coordinates or too little
    flagged tissue to describe.
    """
    coords = parse_coordinates(names)
    pts = [(c, bool(f)) for c, f in zip(coords, flagged) if c is not None]
    if len(pts) < 8:
        return None

    xs = np.array([c[0] for c, _ in pts])
    ys = np.array([c[1] for c, _ in pts])
    fl = np.array([f for _, f in pts])
    if fl.sum() < 3:
        return None

    cx = ((xs - xs.min()) // step).astype(int)
    cy = ((ys - ys.min()) // step).astype(int)
    grid = np.zeros((cy.max() + 1, cx.max() + 1), dtype=bool)
    grid[cy[fl], cx[fl]] = True

    lab, n = ndi.label(grid, structure=np.ones((3, 3)))   # 8-connectivity
    if n == 0:
        return None
    sizes = np.bincount(lab.ravel())[1:].astype(float)
    total = sizes.sum()
    largest = float(sizes.max() / total)

    # Fragmentation: how many separate regions the flagged tissue breaks into,
    # relative to how much flagged tissue there is. One solid block tends to
    # zero; every cell standing alone tends to one.
    frag = float(n / max(total, 1.0))

    def sig(x, centre, width):
        return 1.0 / (1.0 + np.exp(-(x - centre) / width))

    # Focal is decided by whether one region dominates. If no region does, the
    # choice between multifocal and diffuse turns on whether the remainder is
    # a handful of substantial regions or a scatter of isolated cells.
    p_focal = sig(largest, 0.55, 0.12)
    scattered = sig(frag, 0.45, 0.12)
    p_diffuse = (1.0 - p_focal) * scattered
    p_multi = (1.0 - p_focal) * (1.0 - scattered)

    raw = np.clip(np.array([p_focal, p_multi, p_diffuse], dtype=float), 1e-6, None)
    probs = (raw / raw.sum()).tolist()

    return {
        "regions": int(n),
        "largest_share": largest,
        "fragmentation": frag,
        "flagged_cells": int(total),
        "probs": probs,
        "labels": ["Focal", "Multifocal", "Diffuse"],
    }


# --------------------------------------------------------------------------
# Patient-level profile
# --------------------------------------------------------------------------

LOAD_LABELS = ["Low", "Moderate", "High"]
PLEO_LABELS = ["Low", "Moderate", "Marked"]


def patient_profile(measures: list[tuple], names: list[str],
                    flagged: np.ndarray, reference: dict | None = None) -> dict:
    """
    Build the profile for one patient.

    `measures` is the per-patch output of measure_patch, aligned with `names`
    and `flagged`. Nuclear measurements are averaged over the flagged patches
    only, because the question being asked is what the suspicious tissue looks
    like, not what the whole sample averages to.
    """
    ref = reference or load_reference()
    ok = [(m, bool(f)) for m, f in zip(measures, flagged) if m is not None]
    if not ok:
        return {"available": False}

    sel = [m for m, f in ok if f] or [m for m, _ in ok]   # fall back to all
    frac = float(np.mean([m[0] for m in sel]))
    count = float(np.mean([m[1] for m in sel]))
    cv = float(np.mean([m[2] for m in sel]))

    load_t = ref["nuclear_load"]
    pleo_t = ref["pleomorphism"]

    profile = {
        "available": True,
        "calibrated": bool(ref.get("calibrated", False)),
        "cohort_size": int(ref.get("n_patients", 0)),
        "nuclear_fraction": frac,
        "nuclei_per_patch": count,
        "size_cv": cv,
        "n_measured": len(sel),
        "load": {
            "labels": LOAD_LABELS,
            "probs": graded_bands(frac, load_t["t1"], load_t["t2"]),
            "value": frac,
            "thresholds": [load_t["t1"], load_t["t2"]],
        },
        "pleomorphism": {
            "labels": PLEO_LABELS,
            "probs": graded_bands(cv, pleo_t["t1"], pleo_t["t2"]),
            "value": cv,
            "thresholds": [pleo_t["t1"], pleo_t["t2"]],
        },
    }

    foc = focality(names, flagged)
    if foc is not None:
        profile["focality"] = foc
    return profile


def top_label(block: dict) -> tuple[str, float]:
    """Highest-membership label and its share, for a compact summary line."""
    i = int(np.argmax(block["probs"]))
    return block["labels"][i], float(block["probs"][i])
