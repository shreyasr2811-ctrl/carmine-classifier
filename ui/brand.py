"""
Brand identity.

The product needed a name to sit at the top of a site rather than a page
title. `Carmine` is a histological stain -- a red dye used to mark tissue
structure -- which makes it both literal to the domain and a direct match for
the warm coral/crimson palette the rest of the system runs on.

This is a fictional brand for an academic research project. It is not a real
company, does not resemble one, and every page carries the research-prototype
disclaimer so nothing here can be mistaken for a cleared medical device.

The mark is not decorative. It is a slide (the rounded frame) tiled into nine
patches, two of which are flagged -- which is exactly what the product does:
divide a digitised slide into patches, score each one, and surface the
suspicious ones. A logo that describes the mechanism is worth more than a
logo that describes the mood.
"""

NAME = "Carmine"
DESCRIPTOR = "Computational Pathology"
FULL_NAME = "Carmine Computational Pathology"

TAGLINE = "Read the queue before you read the slide."

# One-line positioning used under the wordmark in the footer.
POSITION = (
    "An open research prototype for patch-level screening of H&amp;E breast "
    "tissue, built and validated on the public IDC dataset."
)


def mark(size: int = 30) -> str:
    """
    The Carmine mark: a slide frame tiled into nine patches, two flagged.

    Uses `currentColor` throughout so it inherits whatever colour the caller
    sets -- accent in the header, text_low in the footer -- and needs no
    network request or theme-specific variant.
    """
    dots = []
    flagged = {(2, 0), (1, 1)}          # (col, row) of the two flagged patches
    for row in range(3):
        for col in range(3):
            cx = 10.5 + col * 5.5
            cy = 10.5 + row * 5.5
            if (col, row) in flagged:
                dots.append(
                    f'<circle cx="{cx}" cy="{cy}" r="2.05" fill="currentColor"/>'
                )
            else:
                dots.append(
                    f'<circle cx="{cx}" cy="{cy}" r="1.5" fill="currentColor" '
                    f'opacity=".28"/>'
                )
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" fill="none" '
        f'role="img" aria-label="Carmine">'
        f'<rect x="3" y="3" width="26" height="26" rx="7.5" fill="none" '
        f'stroke="currentColor" stroke-width="1.9" opacity=".85"/>'
        f'{"".join(dots)}</svg>'
    )


# --------------------------------------------------------------------------
# Site structure
# --------------------------------------------------------------------------

# (slug, nav label). Order is the nav order.
PAGES = [
    ("overview",   "Overview"),
    ("technology", "Technology"),
    ("analyze",    "Analyze"),
    ("validation", "Validation"),
    ("about",      "About"),
]

PAGE_SLUGS = [p[0] for p in PAGES]
DEFAULT_PAGE = "overview"
