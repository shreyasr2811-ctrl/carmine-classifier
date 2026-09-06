"""
Handcrafted feature extraction for histopathology patches.

We deliberately avoid deep-learning feature extractors here because this
project targets CPU-only machines with no GPU, and downloading pretrained
ImageNet weights is not reliably possible in all environments. Instead we
use a combination of color, texture, and shape statistics that are known
to work well for H&E-stained histopathology image classification:

  - Color histograms in RGB and HSV space (captures staining intensity /
    hue differences between normal and malignant tissue)
  - Gray-Level Co-occurrence Matrix (GLCM) texture features (contrast,
    homogeneity, energy, correlation) -- captures nuclear texture/density
  - Local Binary Pattern (LBP) histogram -- captures fine-grained texture
  - Basic intensity statistics (mean, std, skewness-like measures) per
    channel

This produces a compact (~150-dim) feature vector per patch that a
Random Forest / XGBoost classifier can learn from efficiently on CPU.
"""

import numpy as np
from PIL import Image
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern
from skimage.color import rgb2gray, rgb2hsv

IMG_SIZE = 50  # native patch size for the IDC dataset


def load_image(path_or_file, size=IMG_SIZE):
    img = Image.open(path_or_file).convert("RGB")
    if img.size != (size, size):
        img = img.resize((size, size))
    return np.array(img)


def _hist_features(channel, bins=16, value_range=(0, 256)):
    hist, _ = np.histogram(channel, bins=bins, range=value_range, density=True)
    return hist


def _color_features(rgb):
    feats = []
    # RGB channel histograms
    for c in range(3):
        feats.append(_hist_features(rgb[:, :, c]))
    # HSV channel histograms (hue is very informative for staining)
    hsv = (rgb2hsv(rgb) * 255).astype(np.uint8)
    for c in range(3):
        feats.append(_hist_features(hsv[:, :, c]))
    # per-channel mean/std (RGB)
    stats = []
    for c in range(3):
        ch = rgb[:, :, c].astype(np.float64)
        stats.extend([ch.mean(), ch.std()])
    feats.append(np.array(stats))
    return np.concatenate(feats)


def _texture_features(rgb):
    gray = (rgb2gray(rgb) * 255).astype(np.uint8)

    # GLCM texture features at a couple of distances/angles, averaged
    glcm = graycomatrix(
        gray, distances=[1, 2], angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4],
        levels=256, symmetric=True, normed=True,
    )
    props = ["contrast", "dissimilarity", "homogeneity", "energy", "correlation", "ASM"]
    glcm_feats = np.array([graycoprops(glcm, p).mean() for p in props])

    # Local Binary Pattern histogram
    lbp = local_binary_pattern(gray, P=8, R=1, method="uniform")
    lbp_hist, _ = np.histogram(lbp, bins=10, range=(0, 10), density=True)

    return np.concatenate([glcm_feats, lbp_hist])


def extract_features(rgb_array):
    """rgb_array: HxWx3 uint8 numpy array -> 1D feature vector."""
    color = _color_features(rgb_array)
    texture = _texture_features(rgb_array)
    return np.concatenate([color, texture]).astype(np.float32)


def extract_features_from_path(path):
    return extract_features(load_image(path))


FEATURE_NAMES = None  # populated lazily if needed for inspection
