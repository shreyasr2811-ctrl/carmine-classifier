"""
Reusable presentation components.

Each function returns an HTML string (or renders directly via st.markdown).
Keeping them here means the page files stay readable as *layout*, and the
visual language can be changed in one place.

Design note on `tone`: every component that carries clinical meaning takes a
tone in {benign, uncertain, malignant, critical, accent, neutral}. The tone
sets three CSS custom properties (--tone, --tone-soft, --tone-line) which the
stylesheet consumes. Nothing hard-codes a hex value at the call site.
"""

import base64
import html
import io
import os

import streamlit as st

TONES = {"benign", "uncertain", "malignant", "critical", "accent"}


def tone_vars(tone: str) -> str:
    """CSS custom-property triplet for a semantic tone."""
    if tone not in TONES:
        return "--tone: var(--border-strong); --tone-soft: var(--scrim); --tone-line: var(--border);"
    return (f"--tone: var(--{tone}); "
            f"--tone-soft: var(--{tone}-soft); "
            f"--tone-line: var(--{tone}-line);")


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def render(html_str: str) -> None:
    st.markdown(html_str, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Iconography -- inline SVG so it inherits colour and needs no network
# --------------------------------------------------------------------------

ICONS = {
    "slide": ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
              'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
              'stroke-linejoin="round"><rect x="6" y="2" width="12" height="20" rx="1.5"/>'
              '<rect x="8.5" y="7" width="7" height="9" rx="1"/><path d="M6 5h12M6 19h12"/></svg>'),
    "grid": ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.6" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/>'
             '<rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>'
             '<rect x="14" y="14" width="7" height="7" rx="1"/></svg>'),
    "alert": ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round"><path d="M12 8v5"/><circle cx="12" cy="16.5" r="1.1" fill="currentColor" stroke="none"/>'
              '<path d="M10.3 3.9 2.6 17.4A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3.1L13.7 3.9a2 2 0 0 0-3.4 0Z"/></svg>'),
    "check": ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m4 12.5 5 5L20 6.5"/></svg>'),
    "clock": ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.2 2"/></svg>'),
    "spark": ('<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">'
              '<path d="M12 2.5 13.9 9 20.5 11 13.9 13 12 19.5 10.1 13 3.5 11 10.1 9Z"/></svg>'),
    "info": ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/>'
             '<circle cx="12" cy="7.8" r="1.1" fill="currentColor" stroke="none"/></svg>'),
    "upload": ('<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
               'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4"/>'
               '<path d="m7.5 8.5 4.5-4.5 4.5 4.5"/><path d="M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15"/></svg>'),
    "scan": ('<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8"/>'
             '<path d="M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/>'
             '<circle cx="12" cy="12" r="3.4"/></svg>'),
    "layers": ('<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
               'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="m12 3 8.5 4.5L12 12 3.5 7.5Z"/>'
               '<path d="m3.5 12 8.5 4.5 8.5-4.5"/><path d="m3.5 16.5 8.5 4.5 8.5-4.5"/></svg>'),
    "doc": ('<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M7 3h7l4 4v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/>'
            '<path d="M14 3v4h4M9 12.5h6M9 16h6"/></svg>'),
}

TRIAGE_ICON = {"critical": ICONS["alert"], "uncertain": ICONS["clock"], "benign": ICONS["check"]}


# --------------------------------------------------------------------------
# Masthead + status
# --------------------------------------------------------------------------

def masthead(title: str, subtitle: str, pills: list[tuple[str, str]] | None = None) -> None:
    """pills: list of (state, text) where state in {live, warn, off}."""
    pill_html = ""
    if pills:
        items = "".join(
            f'<span class="hp-pill"><i class="hp-dot {_e(state)}"></i>{_e(text)}</span>'
            for state, text in pills
        )
        pill_html = f'<div class="hp-pills">{items}</div>'

    render(f"""
<div class="hp-in">
  <div class="hp-mast">
    <div class="hp-mast-mark" style="color: var(--accent)">{ICONS["slide"]}</div>
    <div>
      <h1 class="hp-mast-title">{_e(title)}</h1>
      <p class="hp-mast-sub">{_e(subtitle)}</p>
    </div>
  </div>
  {pill_html}
</div>
""")


def section(title: str, kicker: str = "", note: str = "", delay: int = 0,
            help: str = "") -> None:
    """
    A section heading.

    `note` prints under the title and should be at most one line. Anything
    longer belongs in `help`, which renders as an info affordance the reader
    can hover instead of having to read past. The screen carries the answer;
    the tooltip carries the explanation.
    """
    k = f'<span class="hp-sect-kicker">{_e(kicker)}</span>' if kicker else ""
    n = f'<p class="hp-sect-note">{note}</p>' if note else ""
    h = info(help) if help else ""
    render(f"""
<div class="hp-sect hp-in" style="--d:{delay}ms">
  {k}
  <h2 class="hp-sect-title">{_e(title)}{h}</h2>
  {n}
  <div class="hp-rule"></div>
</div>
""")


def info(text: str) -> str:
    """
    An inline info marker carrying its explanation in a native tooltip.

    Deliberately a `title` attribute rather than a scripted popover: Streamlit
    strips <script> from markdown, and the browser's own tooltip is keyboard
    reachable and works on every platform without any of our code running.
    """
    if not text:
        return ""
    return (f'<span class="hp-info" tabindex="0" title="{_plain(text)}" '
            f'aria-label="{_plain(text)}">{ICONS["info"]}</span>')


def term(label: str, explanation: str) -> str:
    """A term the reader can hover for its definition, marked with a dotted rule."""
    return (f'<span class="hp-term" tabindex="0" title="{_plain(explanation)}">'
            f'{_e(label)}</span>')


def _plain(html_str: str) -> str:
    """Strip tags and entities so a string is safe inside a title attribute."""
    import re as _re
    t = _re.sub(r"<[^>]+>", "", str(html_str))
    t = (t.replace("&mdash;", "-").replace("&times;", "x").replace("&ndash;", "-")
          .replace("&lsquo;", "'").replace("&rsquo;", "'").replace("&amp;", "&")
          .replace("&nbsp;", " "))
    return html.escape(" ".join(t.split()), quote=True)


# --------------------------------------------------------------------------
# Stat tiles
# --------------------------------------------------------------------------

def stat_tiles(tiles: list[dict], columns: int = 3) -> None:
    """
    tiles: [{label, value, sub?, tone?, sub_tone?, mono?}]
    Rendered as one CSS grid rather than st.columns so gutters and card
    heights stay identical regardless of content length.
    """
    cells = []
    for i, t in enumerate(tiles):
        tone = t.get("tone", "")
        tv = tone_vars(tone) if tone else "--tone: var(--border-strong);"
        val_cls = "hp-tile-value tone" if tone and t.get("tone_value", True) else "hp-tile-value"
        sub = ""
        if t.get("sub"):
            sub_cls = "hp-tile-sub tone" if t.get("sub_tone") else "hp-tile-sub"
            sub = f'<div class="{sub_cls}">{_e(t["sub"])}</div>'
        cells.append(
            f'<div class="hp-tile" style="{tv} --d:{60 + i * 70}ms">'
            f'<div class="hp-tile-label">{_e(t["label"])}</div>'
            f'<div class="{val_cls}">{_e(t["value"])}</div>{sub}</div>'
        )
    render(
        f'<div class="hp-tiles" style="grid-template-columns: repeat({columns}, minmax(0,1fr))">'
        + "".join(cells) + "</div>"
    )


# --------------------------------------------------------------------------
# Triage banner
# --------------------------------------------------------------------------

def triage_banner(fraction: float, tone: str, headline: str, action_html: str) -> None:
    icon = TRIAGE_ICON.get(tone, ICONS["info"])
    crit = " is-critical" if tone == "critical" else ""
    render(f"""
<div class="hp-triage{crit}" style="{tone_vars(tone)}">
  <div class="hp-triage-head">
    <span class="hp-triage-badge">{icon}{_e(headline)}</span>
  </div>
  <div class="hp-triage-figure">{fraction * 100:.1f}<small>% of sampled tissue flagged</small></div>
  <p class="hp-triage-action">{action_html}</p>
</div>
""")


# --------------------------------------------------------------------------
# Verdict card (single patch)
# --------------------------------------------------------------------------

def verdict_card(label: str, confidence: float, tone: str, note: str) -> None:
    r = 48
    circ = 2 * 3.14159265 * r
    dash_to = circ * (1 - min(max(confidence, 0.0), 1.0))
    render(f"""
<div class="hp-verdict" style="{tone_vars(tone)}">
  <div class="hp-ring" style="--dash-full:{circ:.2f}; --dash-to:{dash_to:.2f}">
    <svg width="112" height="112" viewBox="0 0 112 112">
      <circle class="track" cx="56" cy="56" r="{r}" fill="none" stroke-width="8"/>
      <circle class="fill"  cx="56" cy="56" r="{r}" fill="none" stroke-width="8"/>
    </svg>
    <div class="hp-ring-center">
      <div class="hp-ring-num">{confidence:.0%}</div>
      <div class="hp-ring-cap">confidence</div>
    </div>
  </div>
  <div class="hp-verdict-body">
    <div class="hp-verdict-kicker">Patch-level call</div>
    <div class="hp-verdict-label">{_e(label)}</div>
    <div class="hp-verdict-note">{note}</div>
  </div>
</div>
""")


def probability_split(p_benign: float, p_malignant: float) -> None:
    b = max(p_benign, 0.0) * 100
    m = max(p_malignant, 0.0) * 100
    render(f"""
<div class="hp-split hp-in" style="--d:200ms">
  <div class="hp-split-track">
    <div class="hp-split-seg b" style="width:{b:.2f}%"></div>
    <div class="hp-split-seg m" style="width:{m:.2f}%"></div>
  </div>
  <div class="hp-split-legend">
    <span><i class="hp-dot" style="background:var(--benign)"></i>Benign <b>{p_benign:.1%}</b></span>
    <span><b>{p_malignant:.1%}</b> Malignant (IDC)<i class="hp-dot" style="background:var(--malignant);margin-left:5px"></i></span>
  </div>
</div>
""")


# --------------------------------------------------------------------------
# Callouts
# --------------------------------------------------------------------------

def note(body_html: str, title: str = "", tone: str = "accent", delay: int = 0) -> None:
    t = f'<span class="hp-note-title">{_e(title)}</span>' if title else ""
    render(f'<div class="hp-note" style="{tone_vars(tone)} --d:{delay}ms">{t}{body_html}</div>')


def is_is_not(is_html: str, is_not_html: str) -> None:
    render(f"""
<div class="hp-isnot hp-in" style="--d:120ms">
  <div class="is"><span class="k">What this is</span>{is_html}</div>
  <div class="isnt"><span class="k">What this is not</span>{is_not_html}</div>
</div>
""")


def disclaimer_strip(text_html: str) -> None:
    render(f'<div class="hp-disc hp-fade"><span style="color:var(--uncertain);flex:0 0 auto;margin-top:2px">'
           f'{ICONS["alert"]}</span><div>{text_html}</div></div>')


# --------------------------------------------------------------------------
# Explanation panel
# --------------------------------------------------------------------------

def explanation_panel(text: str, sources: list[str] | None, unavailable: bool = False) -> None:
    paras = "".join(f"<p>{_e(p.strip())}</p>" for p in text.split("\n") if p.strip())
    src = ""
    if sources:
        chips = "".join(
            f'<span class="hp-src-chip">{_e(s[:64] + ("..." if len(s) > 64 else ""))}</span>'
            for s in sources
        )
        src = f'<div class="hp-src">{chips}</div>'
    kicker = "Offline explanation" if unavailable else "AI explanation, grounded in the knowledge base"
    dot = "off" if unavailable else "live"
    render(f"""
<div class="hp-xplain">
  <div class="hp-xplain-head">
    <span style="color:var(--accent)">{ICONS["spark"]}</span>
    <span class="t">{_e(kicker)}</span>
    <i class="hp-dot {dot}" style="margin-left:auto"></i>
  </div>
  <div class="hp-xplain-body">{paras}</div>
  {src}
</div>
""")


# --------------------------------------------------------------------------
# Evidence gallery
# --------------------------------------------------------------------------

def _thumb_data_uri(src, size: int = 96) -> str | None:
    """Accepts a filesystem path or an uploaded file-like object."""
    try:
        from PIL import Image
        if hasattr(src, "seek"):
            src.seek(0)
        img = Image.open(src).convert("RGB")
        img = img.resize((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def evidence_gallery(items: list[tuple], threshold: float = 0.5) -> None:
    """items: [(path_or_file, score)] -- renders thumbnails with score chips."""
    from .tokens import tone_for_score
    cells = []
    for i, (src, score) in enumerate(items):
        uri = _thumb_data_uri(src)
        if uri is None:
            continue
        tone = tone_for_score(float(score), threshold)
        name = os.path.basename(src) if isinstance(src, str) else getattr(src, "name", "")
        cells.append(
            f'<div class="hp-gal-item" style="{tone_vars(tone)} --d:{i * 34}ms" title="{_e(name)}">'
            f'<img src="{uri}" alt="tissue patch, malignancy score {score:.2f}"/>'
            f'<div class="hp-gal-score">{score:.2f}</div></div>'
        )
    if cells:
        render(f'<div class="hp-gal">{"".join(cells)}</div>')


# --------------------------------------------------------------------------
# Process states
# --------------------------------------------------------------------------

class ScanProgress:
    """Custom animated progress readout; replaces st.progress + st.caption."""

    def __init__(self, container, label: str = "Preparing"):
        self._c = container
        self.update(0.0, label)

    def update(self, pct: float, label: str) -> None:
        pct = min(max(pct, 0.0), 1.0)
        self._c.markdown(f"""
<div class="hp-scan">
  <div class="hp-scan-row">
    <span class="hp-scan-txt">{_e(label)}</span>
    <span class="hp-scan-pct">{pct * 100:.0f}%</span>
  </div>
  <div class="hp-scan-track"><div class="hp-scan-bar" style="width:{pct * 100:.1f}%"></div></div>
</div>
""", unsafe_allow_html=True)

    def clear(self) -> None:
        self._c.empty()


def empty_state(title: str, body: str, icon: str = "upload") -> None:
    render(f"""
<div class="hp-empty">
  <div class="hp-empty-mark" style="color:var(--text-low)">{ICONS.get(icon, ICONS["upload"])}</div>
  <div class="hp-empty-title">{_e(title)}</div>
  <div class="hp-empty-body">{_e(body)}</div>
</div>
""")


def skeleton(height: int = 76, count: int = 1) -> None:
    render("".join(f'<div class="hp-skel" style="--h:{height}px;margin-bottom:8px"></div>'
                   for _ in range(count)))


# --------------------------------------------------------------------------
# Sidebar pieces
# --------------------------------------------------------------------------

def side_title(text: str) -> None:
    render(f'<div class="hp-side-title">{_e(text)}</div>')


def kv_list(pairs: list[tuple[str, str]]) -> None:
    rows = "".join(f'<div class="hp-kv"><span class="k">{_e(k)}</span>'
                   f'<span class="v">{_e(v)}</span></div>' for k, v in pairs)
    render(f'<div>{rows}</div>')


def queue_list(items: list[dict]) -> None:
    """items: [{id, fraction, tone, n}] sorted by priority."""
    if not items:
        render('<div style="font-size:.76rem;color:var(--text-low);line-height:1.6">'
               'Patients you analyse this session collect here, ordered by priority.</div>')
        return
    rows = "".join(
        f'<div class="hp-q-item" style="{tone_vars(it["tone"])} --d:{i * 50}ms">'
        f'<span class="hp-q-id">{_e(it["id"])}</span>'
        f'<span class="hp-q-n">{it["n"]}p</span>'
        f'<span class="hp-q-val">{it["fraction"]:.0%}</span></div>'
        for i, it in enumerate(items)
    )
    render(f'<div class="hp-q">{rows}</div>')


def legend(entries: list[tuple[str, str]]) -> None:
    """entries: [(css_var_name, label)]"""
    items = "".join(f'<span><i style="background:var(--{v})"></i>{_e(l)}</span>' for v, l in entries)
    render(f'<div class="hp-legend">{items}</div>')


def footer(model_line: str) -> None:
    render(f'<div class="hp-foot">{model_line}</div>')

# --------------------------------------------------------------------------
# Morphological profile
# --------------------------------------------------------------------------

def morphology_profile(blocks: list[dict], note_html: str = "") -> None:
    """
    blocks: [{title, labels, probs, reading, detail}]

    Rendered on a neutral-to-accent ramp rather than in the clinical tones.
    That is deliberate. Benign, uncertain and malignant carry clinical meaning
    in this product, and these bars are measurements of tissue appearance, not
    verdicts about a patient. Borrowing the semantic palette here would imply
    a severity claim the data cannot support.
    """
    rows = []
    for i, b in enumerate(blocks):
        segs = "".join(
            f'<div class="hp-mp-seg b{j + 1}" style="width:{p * 100:.2f}%" '
            f'title="{_e(l)} {p:.0%}"></div>'
            for j, (l, p) in enumerate(zip(b["labels"], b["probs"])) if p > 0.001
        )
        keys = "".join(
            f'<span class="hp-mp-key"><i class="b{j + 1}"></i>{_e(l)} '
            f'<b>{p:.0%}</b></span>'
            for j, (l, p) in enumerate(zip(b["labels"], b["probs"]))
        )
        measure = (f'<div class="hp-mp-measure">{_e(b["measure"])}</div>'
                   if b.get("measure") else "")
        rows.append(
            f'<div class="hp-mp-row" style="--d:{i * 90}ms">'
            f'<div class="hp-mp-head">'
            f'<span class="hp-mp-title">{_e(b["title"])}'
            f'{info(b.get("help", ""))}</span>'
            f'<span class="hp-mp-read">{_e(b["reading"])}</span></div>'
            f'<div class="hp-mp-track">{segs}</div>'
            f'<div class="hp-mp-keys">{keys}</div>'
            f'<div class="hp-mp-detail">{b.get("detail", "")}</div>'
            f'{measure}</div>'
        )
    n = f'<div class="hp-mp-note">{note_html}</div>' if note_html else ""
    render(f'<div class="hp-mp">{"".join(rows)}{n}</div>')



def involvement_ladder(frac: float, n_flag: int, n_total: int, threshold: float,
                       meanings: list[str], help_html: str = "") -> None:
    """
    The headline reading: how much of the sampled tissue was flagged, placed
    on a four-band scale.

    Deliberately shaped like the stepped graphic people expect from an
    oncology tool, and deliberately not labelled like one. There are no
    numerals, no roman numbers and no use of the word "stage" as a label,
    because a stepped graphic in this context is exactly where a reader would
    otherwise infer a stage that the system has not produced and cannot.

    The active band takes the semantic tone the triage banner already uses, so
    the two are visibly one reading of one quantity rather than two scales.
    Every band carries a tooltip giving both its meaning and the arithmetic
    that produced this particular reading.
    """
    from .tokens import EXTENT_BANDS, extent_band, extent_range_text

    active = extent_band(frac)
    basis = (f"Basis: {n_flag:,} of {n_total:,} patches scored at or above the "
             f"decision threshold of {threshold:.2f}, giving {frac:.1%}. Band "
             f"boundaries are 15%, 50% and 75%, which are a product decision "
             f"about queue order, not a clinical threshold.")

    heights = [46, 64, 82, 100]
    steps = []
    for i, b in enumerate(EXTENT_BANDS):
        is_on = i == active
        tv = tone_vars(b["tone"]) if is_on else ""
        tip = f"{meanings[i]}  {basis}" if i < len(meanings) else basis
        steps.append(
            f'<div class="hp-lad-step{" is-on" if is_on else ""}" '
            f'style="{tv} --h:{heights[i]}%; --d:{80 + i * 90}ms">'
            f'<div class="hp-lad-bar"></div>'
            f'<div class="hp-lad-cap">'
            f'<span class="hp-lad-name">{_e(b["name"])}{info(tip)}</span>'
            f'<span class="hp-lad-range">{_e(extent_range_text(i))}</span>'
            f'</div></div>'
        )

    band = EXTENT_BANDS[active]
    render(f"""
<div class="hp-lad" style="{tone_vars(band["tone"])}">
  <div class="hp-lad-head">
    <div>
      <div class="hp-lad-kicker">Extent of involvement{help_html}</div>
      <div class="hp-lad-band">{_e(band["name"])}
        <span class="n">{_e(extent_range_text(active))} of sampled tissue</span></div>
    </div>
    <div class="hp-lad-figure">{frac * 100:.1f}<small>% flagged</small></div>
  </div>
  <div class="hp-lad-steps">{"".join(steps)}</div>
  <div class="hp-lad-basis">{_e(basis)}</div>
</div>
""")


def icon_row(items: list[tuple[str, str, str]]) -> None:
    """
    items: [(icon_key, title, body)]

    A row of circular icon badges, the shape the reference layout uses for
    its "how it works at a glance" strip. The badge colour rotates across
    three decorative hues (rose, then two non-clinical accents) purely so
    the row does not read as one dominant pink block -- see the note on
    DECOR colours in tokens.py. None of these three colours is ever the
    benign/uncertain/malignant tone, so nothing here can be misread as a
    clinical signal.
    """
    cells = "".join(
        f'<div class="hp-icon-item" style="--d:{60 + i * 80}ms">'
        f'<div class="hp-icon-badge">{ICONS.get(icon, ICONS["spark"])}</div>'
        f'<div class="hp-icon-t">{_e(title)}</div>'
        f'<div class="hp-icon-b">{body}</div></div>'
        for i, (icon, title, body) in enumerate(items)
    )
    render(f'<div class="hp-icon-row">{cells}</div>')


def process_flow(items: list[tuple[str, str]]) -> None:
    """
    items: [(title, body)]

    A horizontal, connected-dot process line -- the "Process" stepper shape
    from the reference layout -- used in place of the vertical numbered list
    on pages where the pipeline reads better left to right. Falls back to a
    stacked column under `RESPONSIVE` on narrow screens.
    """
    nodes = "".join(
        f'<div class="hp-flow-item" style="--d:{60 + i * 90}ms">'
        f'<div class="hp-flow-dot">{i + 1}</div>'
        f'<div class="hp-flow-t">{_e(t)}</div>'
        f'<div class="hp-flow-b">{b}</div></div>'
        for i, (t, b) in enumerate(items)
    )
    render(f'<div class="hp-flow" style="--n:{len(items)}">{nodes}</div>')


def closing_band(kicker: str, title: str, body: str) -> None:
    """
    A full-width, soft-blob sign-off band for the end of a page -- the
    "thank you" close from the reference layout. The button that follows it
    is a real st.button rendered by the caller, since HTML markdown cannot
    trigger a Streamlit rerun.
    """
    k = f'<span class="hp-closing-kicker">{_e(kicker)}</span>' if kicker else ""
    render(f"""
<div class="hp-closing">
  <div class="hp-closing-blobs"></div>
  <div class="hp-closing-in">
    {k}
    <div class="hp-closing-title">{_e(title)}</div>
    <p class="hp-closing-body">{body}</p>
  </div>
</div>
""")


def staging_reference(stages: list[tuple[str, str, str]], why_html: str,
                      intro: str = "", help_html: str = "") -> None:
    """
    Reference material on real TNM staging. Never model output.

    It sits below the ladder rather than beside it, and is styled as a
    reference block rather than a result card, so that no reader can mistake
    it for something computed from their data. Each stage carries its full
    definition in a tooltip.
    """
    items = "".join(
        f'<div class="hp-stg-item" tabindex="0" title="{_plain(desc)}">'
        f'<span class="hp-stg-num">{_e(num)}</span>'
        f'<span class="hp-stg-name">{_e(name)}</span>'
        f'<span class="hp-stg-mark">{ICONS["info"]}</span></div>'
        for num, name, desc in stages
    )
    intro_html = f'<p class="hp-stg-intro">{intro}</p>' if intro else ""
    render(f"""
<div class="hp-stg">
  <div class="hp-stg-head">
    <span class="hp-stg-kicker">Reference &middot; not model output{help_html}</span>
    <span class="hp-stg-title">What breast cancer staging actually is</span>
  </div>
  {intro_html}
  <div class="hp-stg-row">{items}</div>
  <div class="hp-stg-why">{why_html}</div>
</div>
""")

