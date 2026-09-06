"""
Design tokens for the Breast Cancer Histopathology Classifier.

Single source of truth for colour, type, spacing, radius, elevation and
motion. Everything downstream (CSS, Plotly charts, matplotlib fallbacks)
reads from here, so the product has one visual language rather than a set
of independently-chosen values.

Colour rationale
----------------
A vintage clinical palette: aged off-white paper, warm brown-black ink and a
single dusty-rose accent. The reference is a printed pamphlet rather than a
software console -- generous margins, a serif masthead, thin rules, and colour
spent so sparingly that it means something wherever it lands.

Two colour systems, kept deliberately separate:

  BRAND (non-clinical)   a muted dusty rose, used only for buttons, links,
                          focus rings and section kickers -- never for a
                          clinical state.
  SEMANTIC (clinical)     benign sage, uncertain ochre, malignant crimson,
                          critical oxblood. These carry meaning and must never
                          be reused decoratively.

  * accent      dusty rose         light #BE7C88 / dark #D69AA3
  * benign      sage               light #4F7A5E / dark #7FB894
  * uncertain   ochre              light #9A7526 / dark #D3A651
  * malignant   crimson            light #93202F / dark #E0687C
  * critical    oxblood            light #6E1624 / dark #E2465E (HIGH PRIORITY only)

The semantics were re-hued for this palette rather than carried over. Sage and
ochre are muted enough to sit inside a vintage page without shouting, and the
crimson was deepened until it separated cleanly from the rose it now shares a
family with: accent-to-malignant measures ΔE(CIEDE2000) = 27.5, comfortably
above the ΔE 16-18 the original coral pairing achieved.

Sage/crimson (rather than the conventional green/red) stays separable under
protanopia and deuteranopia at ΔE 50.7, and sits against the pink-purple of
H&E-stained tissue without competing with it. Ochre is never the only signal
-- it always ships with a text label.

Contrast, measured against the #FBF6F3 ground: body text 7.7:1, headings
12.1:1, malignant 7.9:1, critical 10.9:1, benign 4.6:1 and ochre 4.0:1 all
clear AA for text; the rose accent carries 3.1:1, above the 3:1 floor for
interface components, and accent_hi at 4.7:1 is used wherever the rose has to
carry words.
"""

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------

SEMANTIC = {
    "benign":    "#4F7A5E",
    "uncertain": "#9A7526",
    "malignant": "#93202F",
    "critical":  "#6E1624",
}

# Aged off-white and blush -- the default, primary mode.
LIGHT = {
    # surfaces
    "bg":            "#FBF6F3",
    "canvas":        "#FDFAF8",
    "surface":       "#FFFFFF",
    "surface_2":     "#F7EFEA",
    "surface_3":     "#F0E3DC",
    "overlay":       "rgba(251, 246, 243, 0.82)",
    # lines -- thin and warm, never grey
    "border_subtle": "#F0E5DF",
    "border":        "#E3D3CB",
    "border_strong": "#C9B0A6",
    # text -- warm brown-black, the colour of old print
    "text_hi":       "#3A2F2C",
    "text":          "#5A4B46",
    "text_mid":      "#857370",
    "text_low":      "#A89793",
    # interactive -- dusty rose, never reused for a clinical state
    "accent":        "#BE7C88",
    "accent_hi":     "#9E5C68",
    "accent_soft":   "rgba(190, 124, 136, 0.10)",
    "accent_line":   "rgba(190, 124, 136, 0.30)",
    "accent_half":   "rgba(190, 124, 136, 0.58)",
    "btn_from":      "#C4848F",
    "btn_to":        "#9E5C68",
    # decorative-only accents (NOT clinical) -- used to keep icon badges,
    # blobs and card accents from reading as one dominant pink. Chosen far
    # from every SEMANTIC hue (no green, no gold) so nothing decorative can
    # ever be mistaken for a benign/uncertain reading.
    "decor2":        "#5C8A82",
    "decor2_soft":   "rgba(92, 138, 130, 0.12)",
    "decor2_line":   "rgba(92, 138, 130, 0.30)",
    "decor3":        "#9B7BA6",
    "decor3_soft":   "rgba(155, 123, 166, 0.12)",
    "decor3_line":   "rgba(155, 123, 166, 0.30)",
    # semantic
    "benign":        SEMANTIC["benign"],
    "benign_soft":   "rgba(79, 122, 94, 0.10)",
    "benign_line":   "rgba(79, 122, 94, 0.30)",
    "uncertain":     SEMANTIC["uncertain"],
    "uncertain_soft": "rgba(154, 117, 38, 0.10)",
    "uncertain_line": "rgba(154, 117, 38, 0.30)",
    "malignant":     SEMANTIC["malignant"],
    "malignant_soft": "rgba(147, 32, 47, 0.08)",
    "malignant_line": "rgba(147, 32, 47, 0.26)",
    "critical":      SEMANTIC["critical"],
    "critical_soft": "rgba(110, 22, 36, 0.09)",
    "critical_line": "rgba(110, 22, 36, 0.30)",
    # effects -- very soft, paper rather than glass
    "shadow_1":      "0 1px 2px rgba(58,47,44,.05)",
    "shadow_2":      "0 1px 2px rgba(58,47,44,.05), 0 8px 24px rgba(58,47,44,.055)",
    "shadow_3":      "0 3px 8px rgba(58,47,44,.06), 0 20px 52px rgba(58,47,44,.09)",
    "grid_line":     "rgba(58,47,44,.045)",
    "sheen":         "rgba(58,47,44,.02)",
    "scrim":         "rgba(58,47,44,.014)",
}

# Warm charcoal companion mode -- a workstation-at-night toggle, not the default.
DARK = {
    "bg":            "#1B1614",
    "canvas":        "#201A18",
    "surface":       "#261F1C",
    "surface_2":     "#2F2723",
    "surface_3":     "#3A302B",
    "overlay":       "rgba(27, 22, 20, 0.80)",
    "border_subtle": "#332A26",
    "border":        "#42362F",
    "border_strong": "#5C4B42",
    "text_hi":       "#F5EBE5",
    "text":          "#DCCCC4",
    "text_mid":      "#AC998F",
    "text_low":      "#7D6C64",
    "accent":        "#D69AA3",
    "accent_hi":     "#E4B4BB",
    "accent_soft":   "rgba(214, 154, 163, 0.13)",
    "accent_line":   "rgba(214, 154, 163, 0.32)",
    "accent_half":   "rgba(214, 154, 163, 0.62)",
    "btn_from":      "#C88892",
    "btn_to":        "#E4B4BB",
    "decor2":        "#8FBDB3",
    "decor2_soft":   "rgba(143, 189, 179, 0.15)",
    "decor2_line":   "rgba(143, 189, 179, 0.32)",
    "decor3":        "#C3A6CE",
    "decor3_soft":   "rgba(195, 166, 206, 0.15)",
    "decor3_line":   "rgba(195, 166, 206, 0.32)",
    "benign":        "#7FB894",
    "benign_soft":   "rgba(127, 184, 148, 0.13)",
    "benign_line":   "rgba(127, 184, 148, 0.32)",
    "uncertain":     "#D3A651",
    "uncertain_soft": "rgba(211, 166, 81, 0.13)",
    "uncertain_line": "rgba(211, 166, 81, 0.32)",
    "malignant":     "#E0687C",
    "malignant_soft": "rgba(224, 104, 124, 0.14)",
    "malignant_line": "rgba(224, 104, 124, 0.34)",
    "critical":      "#E2465E",
    "critical_soft": "rgba(226, 70, 94, 0.15)",
    "critical_line": "rgba(226, 70, 94, 0.40)",
    "shadow_1":      "0 1px 2px rgba(0,0,0,.32)",
    "shadow_2":      "0 2px 6px rgba(0,0,0,.30), 0 10px 30px rgba(0,0,0,.26)",
    "shadow_3":      "0 4px 12px rgba(0,0,0,.34), 0 20px 54px rgba(0,0,0,.34)",
    "grid_line":     "rgba(245,235,229,.04)",
    "sheen":         "rgba(245,235,229,.045)",
    "scrim":         "rgba(245,235,229,.018)",
}

THEMES = {"dark": DARK, "light": LIGHT}

# --------------------------------------------------------------------------
# Type / space / motion
# --------------------------------------------------------------------------

# A serif masthead over a quiet sans body is what makes the page read as
# printed rather than rendered. The serif carries display sizes only -- it is
# too fine for interface text, where Inter stays.
FONT_DISPLAY = "'Cormorant Garamond', 'Iowan Old Style', Georgia, 'Times New Roman', serif"
FONT_UI = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
FONT_MONO = "'IBM Plex Mono', 'SFMono-Regular', Menlo, Consolas, monospace"

# cubic-beziers: expo-out for entrances, a soft standard for state changes
EASE_OUT = "cubic-bezier(.16, 1, .3, 1)"
EASE_STD = "cubic-bezier(.4, 0, .2, 1)"

DUR = {"xs": "120ms", "sm": "180ms", "md": "260ms", "lg": "440ms", "xl": "760ms"}

RADIUS = {"xs": "5px", "sm": "8px", "md": "12px", "lg": "16px", "xl": "22px", "pill": "999px"}


def theme(name: str = "dark") -> dict:
    return THEMES.get(name, DARK)


def css_variables(name: str = "dark") -> str:
    """Render the active theme as a :root custom-property block."""
    t = theme(name)
    lines = [f"  --{k.replace('_', '-')}: {v};" for k, v in t.items()]
    lines.append(f"  --font-display: {FONT_DISPLAY};")
    lines.append(f"  --font-ui: {FONT_UI};")
    lines.append(f"  --font-mono: {FONT_MONO};")
    lines.append(f"  --ease-out: {EASE_OUT};")
    lines.append(f"  --ease-std: {EASE_STD};")
    for k, v in DUR.items():
        lines.append(f"  --dur-{k}: {v};")
    for k, v in RADIUS.items():
        lines.append(f"  --r-{k}: {v};")
    return ":root {\n" + "\n".join(lines) + "\n}"


def tone_for_fraction(frac: float) -> str:
    """Triage tone from malignant tissue fraction."""
    if frac >= 0.50:
        return "critical"
    if frac >= 0.15:
        return "uncertain"
    return "benign"


# --------------------------------------------------------------------------
# Extent bands
# --------------------------------------------------------------------------
# The one ordinal scale in the product. Bands 1 and 2 sit exactly on the
# triage boundaries (15% and 50%), so the ladder and the review-priority
# banner are two readings of a single quantity rather than two competing
# scales. The split at 75% subdivides the top band for legibility only and
# changes no routing decision: both band 3 and band 4 are high priority.
#
# These are NOT cancer stages, and the vocabulary avoids stage language on
# purpose -- no numerals, no "stage", no roman numbers. What is measured is
# the proportion of sampled patches the classifier flagged, and nothing else.

EXTENT_BANDS = [
    {"name": "Minimal",     "lo": 0.00, "hi": 0.15, "tone": "benign"},
    {"name": "Limited",     "lo": 0.15, "hi": 0.50, "tone": "uncertain"},
    {"name": "Substantial", "lo": 0.50, "hi": 0.75, "tone": "critical"},
    {"name": "Extensive",   "lo": 0.75, "hi": 1.01, "tone": "critical"},
]


def extent_band(frac: float) -> int:
    """Index into EXTENT_BANDS for a flagged-tissue fraction."""
    for i, b in enumerate(EXTENT_BANDS):
        if frac < b["hi"]:
            return i
    return len(EXTENT_BANDS) - 1


def extent_range_text(i: int) -> str:
    """Human-readable range for band i, e.g. '15% to 50%'."""
    b = EXTENT_BANDS[i]
    if i == 0:
        return f"under {b['hi']:.0%}"
    if i == len(EXTENT_BANDS) - 1:
        return f"{b['lo']:.0%} and above"
    return f"{b['lo']:.0%} to {b['hi']:.0%}"


def tone_for_score(score: float, threshold: float = 0.5) -> str:
    """Per-patch tone, with an explicit 'uncertain' band around the line."""
    if 0.4 < score < 0.6:
        return "uncertain"
    return "malignant" if score >= threshold else "benign"
