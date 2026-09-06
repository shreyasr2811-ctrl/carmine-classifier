"""
Chart layer.

Two charts, each earning its place:

  score_distribution  -- how the per-patch scores are spread, split at the
                         decision threshold. This is the transparency chart:
                         scores at the extremes mean the model finds the
                         sample easy to read, scores bunched at the line mean
                         genuine ambiguity.
  spatial_map         -- where in the slide the suspicious patches actually
                         sit, reconstructed from the x/y coordinates carried
                         in IDC patch filenames. Focal involvement and diffuse
                         involvement can produce the same headline percentage
                         and look completely different here.

Colour discipline
-----------------
Chart marks do NOT reuse the UI's semantic hex values. Fills sitting on a
dark surface need OKLCH lightness in roughly 0.48-0.67 to stay legible;
the UI values are lighter than that because they also have to work as text.
So each mode gets its own validated mark colours (CHART_MARKS below), which
pass the colourblind-separation, chroma, lightness-band and contrast checks
against their own surface -- sage/crimson clears the deutan floor and
separates at normal-vision dE ~51.

The spatial map is a *diverging* scale, not sequential: 0.0 and 1.0 are
opposite poles (confidently benign / confidently malignant) and 0.5 is a
genuine neutral midpoint, so it takes two hues with a grey middle.
"""

import re

import numpy as np
import plotly.graph_objects as go

from .tokens import theme

# Validated per-mode mark colours (see module docstring). Malignant is a true
# crimson here, not the brand coral -- see tokens.py's colour rationale for
# why the chart's alert colour must stay out of the accent's hue family.
CHART_MARKS = {
    "dark":  {"benign": "#7FB894", "malignant": "#E0687C"},
    "light": {"benign": "#4F7A5E", "malignant": "#93202F"},
}

# Diverging ramp: benign pole -> warm neutral midpoint -> malignant pole.
# Sage at one pole, crimson at the other, and the page's own blush as the
# neutral middle -- so an ambiguous patch reads as paper rather than as a
# third category.
DIVERGING = {
    "dark": [
        [0.00, "#3E6E52"], [0.22, "#7FB894"], [0.42, "#4A3E39"],
        [0.50, "#544741"], [0.58, "#6B4A48"], [0.78, "#E0687C"], [1.00, "#93202F"],
    ],
    "light": [
        [0.00, "#3E6E52"], [0.22, "#8FBFA0"], [0.42, "#E6DCD5"],
        [0.50, "#F0E3DC"], [0.58, "#EFCFCF"], [0.78, "#BE5A6A"], [1.00, "#93202F"],
    ],
}


def _base_layout(mode: str, height: int) -> dict:
    t = theme(mode)
    return dict(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=11.5, color=t["text_mid"]),
        hoverlabel=dict(
            bgcolor=t["surface_2"], bordercolor=t["border"],
            font=dict(family="IBM Plex Mono, monospace", size=12, color=t["text_hi"]),
        ),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="top", y=-0.26, xanchor="left", x=0,
            font=dict(size=11.5, color=t["text_mid"]), bgcolor="rgba(0,0,0,0)",
        ),
        dragmode=False,
    )


def _axis(t: dict, title: str = "", grid: bool = True) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=11.5, color=t["text_low"])),
        showgrid=grid, gridcolor=t["grid_line"], gridwidth=1, griddash="solid",
        zeroline=False, showline=False,
        tickfont=dict(size=11, color=t["text_low"]),
        ticks="outside", ticklen=4, tickcolor="rgba(0,0,0,0)",
    )


# --------------------------------------------------------------------------
# 1. Score distribution
# --------------------------------------------------------------------------

def score_distribution(probs: np.ndarray, threshold: float, mode: str = "dark",
                       height: int = 268) -> go.Figure:
    t = theme(mode)
    marks = CHART_MARKS.get(mode, CHART_MARKS["dark"])

    edges = np.linspace(0, 1, 21)
    counts, _ = np.histogram(probs, bins=edges)
    centres = (edges[:-1] + edges[1:]) / 2
    width = (edges[1] - edges[0]) * 0.82          # the 'surface gap' between columns

    below = centres < threshold
    fig = go.Figure()

    for keep, colour, name in (
        (below,  marks["benign"],    "Looks benign"),
        (~below, marks["malignant"], "Looks malignant"),
    ):
        n = int(counts[keep].sum())
        fig.add_bar(
            x=centres[keep], y=counts[keep], width=width,
            marker=dict(color=colour, line=dict(width=0), cornerradius=4),
            name=f"{name} ({n})",
            hovertemplate="score %{x:.2f} &middot; <b>%{y}</b> patches<extra></extra>",
        )

    # Decision threshold: a solid, recessive reference rule with a plain label.
    fig.add_vline(
        x=threshold, line=dict(color=t["text_low"], width=1.5),
        annotation_text=f"threshold {threshold:.2f}",
        annotation_position="top",
        annotation_font=dict(size=10.5, color=t["text_mid"], family="IBM Plex Mono, monospace"),
    )

    layout = _base_layout(mode, height)
    layout.update(
        bargap=0, barmode="overlay",
        xaxis={**_axis(t, "Malignancy score for each patch", grid=False),
               "range": [-0.02, 1.02], "dtick": 0.25, "tickformat": ".2f"},
        yaxis=_axis(t, "Patches"),
        margin=dict(l=8, r=8, t=26, b=76),
    )
    fig.update_layout(**layout)
    return fig


# --------------------------------------------------------------------------
# 2. Spatial tissue map
# --------------------------------------------------------------------------

_COORD = re.compile(r"_x(\d+)_y(\d+)", re.IGNORECASE)


def parse_coordinates(names: list[str]) -> list[tuple[int, int] | None]:
    """IDC patch filenames encode the patch origin: <id>_idx5_x951_y701_classN.png"""
    out = []
    for n in names:
        m = _COORD.search(str(n))
        out.append((int(m.group(1)), int(m.group(2))) if m else None)
    return out


def has_coordinates(names: list[str], minimum: float = 0.6) -> bool:
    coords = parse_coordinates(names)
    return bool(names) and (sum(c is not None for c in coords) / len(names)) >= minimum


def spatial_map(names: list[str], probs: np.ndarray, mode: str = "dark",
                height: int = 400, step: int = 50) -> go.Figure | None:
    """
    Rebuild the slide layout from patch coordinates and colour each tile by its
    malignancy score. Returns None when filenames carry no usable coordinates.
    """
    coords = parse_coordinates(names)
    pts = [(c, p) for c, p in zip(coords, probs) if c is not None]
    if len(pts) < 4:
        return None

    xs = np.array([c[0] for c, _ in pts])
    ys = np.array([c[1] for c, _ in pts])
    vs = np.array([p for _, p in pts], dtype=float)

    cx = ((xs - xs.min()) // step).astype(int)
    cy = ((ys - ys.min()) // step).astype(int)

    grid = np.full((cy.max() + 1, cx.max() + 1), np.nan)
    grid[cy, cx] = vs

    t = theme(mode)
    fig = go.Figure(go.Heatmap(
        z=grid,
        x=np.arange(grid.shape[1]) * step + xs.min(),
        y=np.arange(grid.shape[0]) * step + ys.min(),
        colorscale=DIVERGING.get(mode, DIVERGING["dark"]),
        zmin=0, zmax=1, zsmooth=False,
        xgap=1, ygap=1,
        hovertemplate="x %{x} &middot; y %{y}<br>score <b>%{z:.2f}</b><extra></extra>",
        colorbar=dict(
            orientation="h", thickness=8, len=0.62, outlinewidth=0,
            x=0.5, xanchor="center", y=-0.2, yanchor="top",
            ticks="outside", ticklen=3, ticklabelposition="outside bottom",
            tickfont=dict(size=10, color=t["text_low"], family="IBM Plex Mono, monospace"),
            tickvals=[0, 0.5, 1], ticktext=["0 benign", "0.5", "1 malignant"],
        ),
    ))

    layout = _base_layout(mode, height)
    layout.update(
        showlegend=False,
        xaxis={**_axis(t, "slide x (pixels)", grid=False), "constrain": "domain",
               "scaleanchor": "y", "scaleratio": 1},
        yaxis={**_axis(t, "slide y (pixels)", grid=False), "autorange": "reversed",
               "constrain": "domain"},
        margin=dict(l=8, r=8, t=10, b=86),
    )
    fig.update_layout(**layout)
    return fig


# --------------------------------------------------------------------------
# Shared Streamlit render config
# --------------------------------------------------------------------------

PLOT_CONFIG = {
    "displayModeBar": False,
    "staticPlot": False,
    "scrollZoom": False,
    "doubleClick": False,
    "responsive": True,
}
