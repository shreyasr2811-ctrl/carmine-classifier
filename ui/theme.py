"""
Theme injection: turns the design tokens into the stylesheet the app runs on.

Everything here is CSS-only. Streamlit strips <script> from markdown, so all
motion is expressed as CSS keyframes and transitions, which has the useful
side effect of being cheap and of respecting prefers-reduced-motion for free.

The only Streamlit-internal selectors used are stable data-testid attributes
and BaseWeb roles, not generated class names, so this survives Streamlit
upgrades far better than the usual copy-pasted class-name hacks.
"""

import re

import streamlit as st

from .tokens import css_variables

FONT_LINK = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&"
    "family=Inter:wght@400;500;600;700;800&"
    "family=IBM+Plex+Mono:wght@400;500;600&display=swap');"
)

# --------------------------------------------------------------------------
# Motion vocabulary
# --------------------------------------------------------------------------
KEYFRAMES = """
@keyframes hpRise {
  from { opacity: 0; transform: translate3d(0, 14px, 0); }
  to   { opacity: 1; transform: translate3d(0, 0, 0); }
}
@keyframes hpFade {
  from { opacity: 0; } to { opacity: 1; }
}
@keyframes hpPop {
  0%   { opacity: 0; transform: scale(.94); }
  60%  { opacity: 1; transform: scale(1.012); }
  100% { opacity: 1; transform: scale(1); }
}
@keyframes hpGrow {
  from { transform: scaleX(0); } to { transform: scaleX(1); }
}
@keyframes hpDraw {
  from { stroke-dashoffset: var(--dash-full); }
  to   { stroke-dashoffset: var(--dash-to); }
}
@keyframes hpSweep {
  0%   { transform: translateX(-120%); }
  100% { transform: translateX(320%); }
}
@keyframes hpBreathe {
  0%, 100% { opacity: .45; }
  50%      { opacity: .95; }
}
@keyframes hpScan {
  0%   { transform: translateY(-100%); opacity: 0; }
  12%  { opacity: 1; }
  88%  { opacity: 1; }
  100% { transform: translateY(1100%); opacity: 0; }
}
@keyframes hpShimmer {
  0%   { background-position: -420px 0; }
  100% { background-position: 420px 0; }
}
@keyframes hpSpin {
  to { transform: rotate(360deg); }
}
@keyframes hpReveal {
  from { opacity: 0; filter: blur(5px); transform: translateY(6px); }
  to   { opacity: 1; filter: blur(0);   transform: translateY(0); }
}
@keyframes hpPulseRing {
  0%   { box-shadow: 0 0 0 0 var(--pulse-color); }
  70%  { box-shadow: 0 0 0 12px rgba(0,0,0,0); }
  100% { box-shadow: 0 0 0 0 rgba(0,0,0,0); }
}
"""

# --------------------------------------------------------------------------
# Base shell + Streamlit chrome
# --------------------------------------------------------------------------
BASE = """
html, body, .stApp {
  font-family: var(--font-ui);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-feature-settings: 'tnum' 1, 'cv05' 1, 'ss01' 1;
}

/* Streamlit ships its own font-family on headings and widgets via emotion
   classes, so inheritance alone is not enough -- these override it without
   !important, which would otherwise clobber the monospace numerals. */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp li, .stApp label, .stApp button, .stApp input,
.stApp textarea, .stApp select, .stApp summary,
.stApp [class*="st-emotion"], .stApp [data-testid="stMarkdownContainer"] {
  font-family: var(--font-ui);
}

/* ...except Streamlit's Material Symbols glyphs, which are ligatures and
   render as the literal string 'keyboard_arrow_right' under any other face. */
.stApp [data-testid="stIconMaterial"],
.stApp [data-testid*="Icon"],
.stApp .material-icons, .stApp [class*="material-symbols"] {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
               'Material Icons' !important;
}

.stApp {
  background:
    radial-gradient(1100px 620px at 78% -12%, var(--accent-soft), transparent 62%),
    radial-gradient(900px 520px at 4% 4%, var(--scrim), transparent 60%),
    linear-gradient(180deg, var(--canvas) 0%, var(--bg) 62%);
  background-attachment: fixed;
  color: var(--text);
}

/* The ground is plain paper. An earlier draft laid a specimen grid over it;
   at this weight of type it read as noise and fought the serif, so the page
   now carries nothing but a soft blush wash falling from the top edge. */
.stApp::before {
  content: "";
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(1400px 560px at 50% -10%, var(--accent-soft), transparent 70%);
  opacity: .8;
}

[data-testid="stAppViewContainer"] > .main { position: relative; z-index: 1; }
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"] { right: 8px; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

.block-container {
  padding-top: 1.6rem !important;
  padding-bottom: 4.5rem !important;
  max-width: 1220px;
}

/* ---------- typography ---------- */
h1, h2, h3, h4 { color: var(--text-hi); letter-spacing: -0.022em; }
p, li, span { color: var(--text); }
a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hi); text-decoration: underline; }
code, .hp-mono { font-family: var(--font-mono) !important; }
hr { border-color: var(--border-subtle) !important; }

::selection { background: var(--accent-soft); color: var(--text-hi); }

/* ---------- scrollbars ---------- */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; border: 3px solid transparent; background-clip: content-box; }
::-webkit-scrollbar-thumb:hover { background: var(--border-strong); background-clip: content-box; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, var(--surface) 0%, var(--canvas) 100%);
  border-right: 1px solid var(--border-subtle);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
"""

# --------------------------------------------------------------------------
# Widget restyling
# --------------------------------------------------------------------------
WIDGETS = """
/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: var(--r-sm);
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-hi);
  font-weight: 560;
  font-size: .875rem;
  letter-spacing: -0.005em;
  padding: .5rem 1rem;
  transition: background var(--dur-sm) var(--ease-std),
              border-color var(--dur-sm) var(--ease-std),
              transform var(--dur-sm) var(--ease-out),
              box-shadow var(--dur-md) var(--ease-out);
  box-shadow: var(--shadow-1);
}
.stButton > button:hover, .stDownloadButton > button:hover {
  background: var(--surface-3);
  border-color: var(--border-strong);
  transform: translateY(-1px);
  box-shadow: var(--shadow-2);
  color: var(--text-hi);
}
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(0); }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px;
}

/* primary CTA -- the one place a gradient earns its keep */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primaryFormSubmit"] {
  position: relative;
  background: linear-gradient(135deg, var(--btn-from) 0%, var(--btn-to) 100%) !important;
  border: none;
  color: #FFFFFF !important;
  font-weight: 600;
  padding: .58rem 1.35rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.2), 0 6px 20px var(--accent-soft);
  overflow: hidden;
}
/* the label lives in a nested <p>, which would otherwise inherit body text
   colour and go dark-on-blue in light mode */
.stButton > button[kind="primary"] *,
.stFormSubmitButton > button[kind="primary"] *,
.stFormSubmitButton > button[kind="primaryFormSubmit"] * {
  color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:disabled, .stButton > button[kind="primary"]:disabled * {
  opacity: .5; cursor: not-allowed;
}
.stButton > button[kind="primary"]::after {
  content: ""; position: absolute; top: 0; bottom: 0; width: 34%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.26), transparent);
  transform: translateX(-120%);
}
.stButton > button[kind="primary"]:hover::after { animation: hpSweep 900ms var(--ease-std); }
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 2px 4px rgba(0,0,0,.24), 0 10px 30px var(--accent-soft);
  transform: translateY(-1px);
}

/* ---------- radio rendered as a segmented control ----------
   Streamlit renders the group as [data-testid="stRadioGroup"] containing
   [data-testid="stRadioOption"] labels, each carrying data-selected. Those
   attributes are stable API surface; the emotion class names are not. */
/* Streamlit sizes widgets to their content by default; a segmented control
   reads as a control only when it fills the slot it sits in. */
.stRadio { width: 100% !important; }
[data-testid="stRadioGroup"] {
  width: 100%; max-width: 520px;
  display: flex; flex-wrap: nowrap; gap: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--r-md);
  padding: 4px;
}
[data-testid="stSidebar"] [data-testid="stRadioGroup"] { max-width: none; }
[data-testid="stRadioOption"] {
  flex: 1 1 0; min-width: 0;
  margin: 0 !important; padding: .42rem .7rem;
  border-radius: var(--r-xs);
  cursor: pointer;
  border: 1px solid transparent;
  transition: background var(--dur-sm) var(--ease-std),
              border-color var(--dur-sm) var(--ease-std),
              box-shadow var(--dur-sm) var(--ease-out);
}
[data-testid="stRadioOption"]:hover { background: var(--surface-3); }
/* the radio dot is the element immediately before the option's text */
[data-testid="stRadioOption"] div:has(+ [data-testid="stMarkdownContainer"]) { display: none; }
[data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] { width: 100%; }
[data-testid="stRadioOption"] p {
  font-size: .8rem !important; font-weight: 540; color: var(--text-mid) !important;
  text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  transition: color var(--dur-sm) var(--ease-std);
}
[data-testid="stRadioOption"][data-selected="true"] {
  background: var(--surface); border-color: var(--border); box-shadow: var(--shadow-1);
}
[data-testid="stRadioOption"][data-selected="true"] p { color: var(--text-hi) !important; }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] {
  gap: 2px; background: transparent; border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
  height: auto; padding: .62rem 1.05rem; background: transparent;
  border-radius: var(--r-sm) var(--r-sm) 0 0;
  color: var(--text-mid);
  font-weight: 560; font-size: .875rem;
  transition: color var(--dur-sm) var(--ease-std), background var(--dur-sm) var(--ease-std);
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text-hi); background: var(--scrim); }
.stTabs [aria-selected="true"] { color: var(--text-hi) !important; }
.stTabs [data-baseweb="tab-highlight"] {
  background: linear-gradient(90deg, var(--accent), var(--accent-hi));
  height: 2px; border-radius: 2px;
}
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.35rem; animation: hpFade var(--dur-lg) var(--ease-out) both; }

/* ---------- inputs ---------- */
.stTextInput input, .stNumberInput input, .stTextArea textarea, [data-baseweb="select"] > div {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-sm) !important;
  color: var(--text-hi) !important;
  font-size: .875rem !important;
  transition: border-color var(--dur-sm) var(--ease-std), box-shadow var(--dur-sm) var(--ease-std);
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-soft) !important;
}
.stTextInput input::placeholder { color: var(--text-low) !important; }
[data-testid="stWidgetLabel"] p, .stSlider label p, .stRadio > label p {
  font-size: .78rem !important; font-weight: 600 !important;
  letter-spacing: .045em; text-transform: uppercase;
  color: var(--text-mid) !important;
}

/* ---------- slider ---------- */
.stSlider [data-baseweb="slider"] [role="slider"] {
  background: var(--surface) !important;
  border: 2px solid var(--accent) !important;
  box-shadow: 0 0 0 4px var(--accent-soft), var(--shadow-1) !important;
  transition: transform var(--dur-sm) var(--ease-out), box-shadow var(--dur-sm) var(--ease-out);
}
.stSlider [data-baseweb="slider"] [role="slider"]:hover { transform: scale(1.14); }
.stSlider [data-testid="stThumbValue"] {
  color: var(--accent-hi) !important; font-family: var(--font-mono) !important;
  font-size: .74rem !important; font-weight: 600 !important;
}
.stSlider [data-testid="stTickBarMin"], .stSlider [data-testid="stTickBarMax"] {
  color: var(--text-low) !important; font-family: var(--font-mono) !important; font-size: .68rem !important;
}

/* ---------- file uploader ---------- */
[data-testid="stFileUploaderDropzone"] {
  background: var(--surface-2);
  border: 1px dashed var(--border-strong);
  border-radius: var(--r-md);
  transition: border-color var(--dur-md) var(--ease-std), background var(--dur-md) var(--ease-std);
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--accent); background: var(--accent-soft);
}
[data-testid="stFileUploaderDropzoneInstructions"] span { color: var(--text-mid) !important; }
[data-testid="stFileUploaderDropzone"] button {
  background: var(--surface-3) !important; color: var(--text-hi) !important;
  border: 1px solid var(--border) !important;
}

/* ---------- number input stepper ----------
   Streamlit's BaseWeb internals follow config.toml's `base`, which is fixed at
   load time, so the stepper would stay dark in light mode. Paint it from the
   tokens instead. */
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] {
  background: var(--surface-3) !important;
  color: var(--text-mid) !important;
  border-left: 1px solid var(--border) !important;
  transition: background var(--dur-sm) var(--ease-std), color var(--dur-sm) var(--ease-std);
}
[data-testid="stNumberInputStepUp"]:hover, [data-testid="stNumberInputStepDown"]:hover {
  background: var(--accent-soft) !important; color: var(--accent) !important;
}
[data-testid="stNumberInputContainer"] { border-color: var(--border) !important; }

/* ---------- expander ---------- */
[data-testid="stExpander"] {
  border: 1px solid var(--border-subtle);
  border-radius: var(--r-md);
  background: var(--surface);
  overflow: hidden;
  box-shadow: var(--shadow-1);
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] details > summary {
  padding: .68rem .95rem; font-weight: 560; font-size: .84rem;
  transition: background var(--dur-sm) var(--ease-std);
}
[data-testid="stExpander"] summary:hover { background: var(--surface-2); }
[data-testid="stExpander"] p { font-size: .875rem; }

/* ---------- dataframe ---------- */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--r-md) !important; overflow: hidden;
}

/* ---------- progress ---------- */
.stProgress > div > div { background: var(--surface-3) !important; border-radius: 99px; height: 6px !important; }
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--accent), var(--accent-hi)) !important;
  border-radius: 99px;
}

/* ---------- native alerts, softened to match ---------- */
[data-testid="stAlert"] {
  border-radius: var(--r-md); border: 1px solid var(--border-subtle);
  background: var(--surface); font-size: .875rem;
}

/* ---------- images ---------- */
[data-testid="stImage"] img { border-radius: var(--r-sm); }
"""

# --------------------------------------------------------------------------
# Custom components
# --------------------------------------------------------------------------
COMPONENTS = """
/* ============ entrance choreography ============ */
.hp-in { animation: hpRise var(--dur-lg) var(--ease-out) both; animation-delay: var(--d, 0ms); }
.hp-fade { animation: hpFade var(--dur-lg) var(--ease-out) both; animation-delay: var(--d, 0ms); }

/* ============ masthead ============ */
.hp-mast { display: flex; align-items: flex-start; gap: 16px; margin-bottom: .55rem; }
.hp-mast-mark {
  flex: 0 0 auto; width: 46px; height: 46px; border-radius: var(--r-md);
  display: grid; place-items: center;
  background: linear-gradient(150deg, var(--surface-3), var(--surface));
  border: 1px solid var(--border);
  box-shadow: var(--shadow-2);
  position: relative; overflow: hidden;
}
.hp-mast-mark::after { content: none; }
.hp-mast-title {
  font-family: var(--font-display);
  font-size: 2.2rem; font-weight: 600; letter-spacing: -0.005em;
  color: var(--text-hi); line-height: 1.1; margin: 0;
}
.hp-mast-sub { font-size: .865rem; color: var(--text-mid); margin: .32rem 0 0; max-width: 80ch; line-height: 1.6; }

/* ============ status pills ============ */
.hp-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: .7rem; }
.hp-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: .22rem .6rem .22rem .5rem;
  border-radius: var(--r-pill);
  background: var(--surface-2); border: 1px solid var(--border-subtle);
  font-size: .705rem; font-weight: 560; color: var(--text-mid);
  letter-spacing: .012em;
}
.hp-dot { width: 6px; height: 6px; border-radius: 99px; background: var(--text-low); flex: 0 0 auto; }
.hp-dot.live { background: var(--benign); animation: hpBreathe 2.6s var(--ease-std) infinite; }
.hp-dot.warn { background: var(--uncertain); }
.hp-dot.off  { background: var(--text-low); }

/* ============ section heading ============ */
.hp-sect { margin: 3.1rem 0 1.25rem; }
.hp-sect:first-child { margin-top: .5rem; }
.hp-sect-kicker {
  font-size: .64rem; font-weight: 600; letter-spacing: .22em; text-transform: uppercase;
  color: var(--accent); margin-bottom: .42rem; display: block;
}
.hp-sect-title {
  font-family: var(--font-display);
  font-size: 1.62rem; font-weight: 600; color: var(--text-hi);
  letter-spacing: -0.005em; line-height: 1.2; margin: 0;
}
.hp-sect-note {
  font-size: .845rem; color: var(--text-mid); margin: .42rem 0 0;
  line-height: 1.72; max-width: 72ch;
}
.hp-rule { height: 1px; background: var(--border-subtle); margin-top: 1.05rem; }

/* ============ stat tiles ============ */
.hp-tiles { display: grid; gap: 10px; }
.hp-tile {
  position: relative; overflow: hidden;
  background: var(--surface); border: 1px solid var(--border-subtle);
  border-radius: var(--r-md); padding: .85rem .95rem 1rem;
  box-shadow: var(--shadow-1);
  transition: transform var(--dur-md) var(--ease-out), box-shadow var(--dur-md) var(--ease-out),
              border-color var(--dur-md) var(--ease-std);
}
.hp-tile:hover { transform: translateY(-2px); box-shadow: var(--shadow-2); border-color: var(--border); }
.hp-tile::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
  background: var(--tone, var(--border-strong));
  transform: scaleY(0); transform-origin: top;
  animation: hpGrow var(--dur-lg) var(--ease-out) both;
  animation-name: hpGrow; animation-delay: var(--d, 0ms);
}
.hp-tile-label {
  font-size: .675rem; font-weight: 650; letter-spacing: .13em; text-transform: uppercase;
  color: var(--text-mid); display: flex; align-items: center; gap: 5px;
}
.hp-tile-value {
  font-family: var(--font-mono); font-size: 1.72rem; font-weight: 600;
  color: var(--text-hi); line-height: 1.1; margin-top: .42rem;
  letter-spacing: -0.03em;
  animation: hpPop var(--dur-lg) var(--ease-out) both; animation-delay: calc(var(--d, 0ms) + 90ms);
}
.hp-tile-value.tone { color: var(--tone); }
.hp-tile-sub { font-size: .745rem; color: var(--text-mid); margin-top: .3rem; font-weight: 500; }
.hp-tile-sub.tone { color: var(--tone); }

/* ============ triage banner ============ */
.hp-triage {
  position: relative; overflow: hidden;
  border-radius: var(--r-lg);
  border: 1px solid var(--tone-line);
  background:
    linear-gradient(100deg, var(--tone-soft) 0%, transparent 58%),
    var(--surface);
  padding: 1.25rem 1.4rem 1.3rem 1.65rem;
  box-shadow: var(--shadow-2);
  animation: hpRise var(--dur-xl) var(--ease-out) both;
}
.hp-triage::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: var(--tone);
  transform: scaleY(0); transform-origin: top;
  animation: hpGrow var(--dur-lg) var(--ease-out) 160ms both;
}
.hp-triage::after {
  content: ""; position: absolute; top: 0; bottom: 0; left: 0; width: 26%;
  background: linear-gradient(90deg, transparent, var(--sheen), transparent);
  transform: translateX(-120%);
  animation: hpSweep 1500ms var(--ease-std) 340ms 1;
}
.hp-triage-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.hp-triage-badge {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: .69rem; font-weight: 750; letter-spacing: .15em; text-transform: uppercase;
  color: var(--tone);
  padding: .26rem .6rem; border-radius: var(--r-pill);
  background: var(--tone-soft); border: 1px solid var(--tone-line);
}
.hp-triage.is-critical .hp-triage-badge { --pulse-color: var(--tone-line); animation: hpPulseRing 2.6s var(--ease-std) infinite; }
.hp-triage-figure {
  font-family: var(--font-mono); font-size: 2.5rem; font-weight: 600; color: var(--tone);
  letter-spacing: -0.035em; line-height: 1; margin: .7rem 0 .1rem;
  animation: hpPop var(--dur-xl) var(--ease-out) 220ms both;
}
.hp-triage-figure small { font-size: .95rem; color: var(--text-mid); font-weight: 500; margin-left: .45rem; letter-spacing: 0; }
.hp-triage-action { font-size: .89rem; color: var(--text); margin: .55rem 0 0; line-height: 1.6; max-width: 76ch; }
.hp-triage-action strong { color: var(--text-hi); font-weight: 620; }

/* ============ verdict card ============ */
.hp-verdict {
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
  border-radius: var(--r-lg); border: 1px solid var(--tone-line);
  background: linear-gradient(120deg, var(--tone-soft), transparent 62%), var(--surface);
  padding: 1.15rem 1.3rem; box-shadow: var(--shadow-2);
  animation: hpRise var(--dur-xl) var(--ease-out) both;
}
.hp-verdict-body { flex: 1 1 220px; min-width: 0; }
.hp-verdict-kicker {
  font-size: .66rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--text-mid);
}
.hp-verdict-label {
  font-size: 1.52rem; font-weight: 700; color: var(--tone); letter-spacing: -0.028em;
  margin: .3rem 0 .15rem; line-height: 1.15;
  animation: hpReveal var(--dur-lg) var(--ease-out) 160ms both;
}
.hp-verdict-note { font-size: .8rem; color: var(--text-mid); line-height: 1.55; }

/* animated confidence ring */
.hp-ring { flex: 0 0 auto; position: relative; width: 112px; height: 112px; }
.hp-ring svg { transform: rotate(-90deg); overflow: visible; }
.hp-ring .track { stroke: var(--surface-3); }
.hp-ring .fill {
  stroke: var(--tone); stroke-linecap: round;
  stroke-dasharray: var(--dash-full);
  animation: hpDraw 1100ms var(--ease-out) 200ms both;
}
.hp-ring-center {
  position: absolute; inset: 0; display: grid; place-content: center; text-align: center;
}
.hp-ring-num { font-family: var(--font-mono); font-size: 1.24rem; font-weight: 600; color: var(--text-hi); letter-spacing: -0.03em; line-height: 1.05; }
.hp-ring-cap { font-size: .52rem; font-weight: 650; letter-spacing: .07em; text-transform: uppercase; color: var(--text-mid); margin-top: 2px; }

/* ============ dual probability bar ============ */
.hp-split { margin-top: .3rem; }
.hp-split-track {
  display: flex; height: 9px; border-radius: 99px; overflow: hidden;
  background: var(--surface-3); border: 1px solid var(--border-subtle);
}
.hp-split-seg { height: 100%; transform-origin: left; animation: hpGrow 900ms var(--ease-out) 260ms both; }
.hp-split-seg.b { background: var(--benign); box-shadow: inset 0 1px 0 rgba(255,255,255,.28); }
.hp-split-seg.m { background: var(--malignant); box-shadow: inset 0 1px 0 rgba(255,255,255,.28); transform-origin: right; }
.hp-split-legend { display: flex; justify-content: space-between; margin-top: .42rem; font-size: .72rem; }
.hp-split-legend span { display: inline-flex; align-items: center; gap: 5px; color: var(--text-mid); font-weight: 520; }
.hp-split-legend b { font-family: var(--font-mono); font-weight: 600; }

/* ============ callouts ============ */
.hp-note {
  border-radius: var(--r-md); padding: .82rem 1rem;
  background: var(--surface); border: 1px solid var(--border-subtle);
  border-left: 2px solid var(--tone, var(--accent));
  font-size: .825rem; line-height: 1.65; color: var(--text);
  box-shadow: var(--shadow-1);
  animation: hpFade var(--dur-lg) var(--ease-out) both; animation-delay: var(--d, 0ms);
}
.hp-note strong { color: var(--text-hi); font-weight: 620; }
.hp-note .hp-note-title {
  display: block; font-size: .675rem; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--tone, var(--accent)); margin-bottom: .35rem;
}

/* the honesty block: two columns, is / is not */
.hp-isnot { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.hp-isnot > div {
  border-radius: var(--r-md); padding: .8rem .95rem;
  border: 1px solid var(--border-subtle); background: var(--surface);
  font-size: .805rem; line-height: 1.62; color: var(--text-mid);
}
.hp-isnot .k {
  display: block; font-size: .66rem; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; margin-bottom: .35rem;
}
.hp-isnot .is .k { color: var(--benign); }
.hp-isnot .isnt .k { color: var(--malignant); }
.hp-isnot b { color: var(--text-hi); font-weight: 620; }

/* ============ explanation panel ============ */
.hp-xplain {
  border-radius: var(--r-lg); border: 1px solid var(--border-subtle);
  background: linear-gradient(150deg, var(--accent-soft), transparent 46%), var(--surface);
  padding: 1.05rem 1.2rem; box-shadow: var(--shadow-1);
  animation: hpRise var(--dur-lg) var(--ease-out) both;
}
.hp-xplain-head { display: flex; align-items: center; gap: 8px; margin-bottom: .6rem; }
.hp-xplain-head .t {
  font-size: .68rem; font-weight: 700; letter-spacing: .15em; text-transform: uppercase; color: var(--accent);
}
.hp-xplain-body { font-size: .875rem; line-height: 1.72; color: var(--text); }
.hp-xplain-body p { margin: 0 0 .7rem; animation: hpReveal 620ms var(--ease-out) both; }
.hp-xplain-body p:nth-child(1) { animation-delay: 60ms; }
.hp-xplain-body p:nth-child(2) { animation-delay: 170ms; }
.hp-xplain-body p:nth-child(3) { animation-delay: 280ms; }
.hp-xplain-body p:nth-child(4) { animation-delay: 390ms; }
.hp-xplain-body p:last-child { margin-bottom: 0; }
.hp-src { display: flex; flex-wrap: wrap; gap: 6px; margin-top: .8rem; }
.hp-src-chip {
  font-size: .7rem; color: var(--text-mid); background: var(--surface-2);
  border: 1px solid var(--border-subtle); border-radius: var(--r-pill);
  padding: .2rem .58rem; font-family: var(--font-mono);
}

/* ============ evidence gallery ============ */
.hp-gal { display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: 9px; }
.hp-gal-item {
  position: relative; border-radius: var(--r-sm); overflow: hidden;
  border: 1px solid var(--border); background: var(--surface-2);
  animation: hpPop var(--dur-md) var(--ease-out) both; animation-delay: var(--d, 0ms);
  transition: transform var(--dur-sm) var(--ease-out), box-shadow var(--dur-sm) var(--ease-out), border-color var(--dur-sm) var(--ease-std);
}
.hp-gal-item:hover { transform: translateY(-3px) scale(1.03); box-shadow: var(--shadow-2); border-color: var(--tone); z-index: 2; }
.hp-gal-item img { display: block; width: 100%; aspect-ratio: 1; object-fit: cover; image-rendering: auto; }
.hp-gal-score {
  position: absolute; left: 0; right: 0; bottom: 0;
  font-family: var(--font-mono); font-size: .655rem; font-weight: 600;
  text-align: center; padding: 2px 0 3px; color: #fff;
  background: linear-gradient(0deg, rgba(0,0,0,.82), rgba(0,0,0,.05));
}
.hp-gal-item::after {
  content: ""; position: absolute; inset: 0; border: 2px solid var(--tone);
  border-radius: var(--r-sm); opacity: .55; pointer-events: none;
}

/* ============ scanning progress ============ */
.hp-scan {
  position: relative; border-radius: var(--r-md); border: 1px solid var(--border-subtle);
  background: var(--surface); padding: .9rem 1.05rem; overflow: hidden; box-shadow: var(--shadow-1);
}
.hp-scan-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.hp-scan-txt { font-size: .8rem; color: var(--text); font-weight: 520; }
.hp-scan-pct { font-family: var(--font-mono); font-size: .8rem; color: var(--accent-hi); font-weight: 600; }
.hp-scan-track { height: 4px; border-radius: 99px; background: var(--surface-3); margin-top: .65rem; overflow: hidden; }
.hp-scan-bar {
  height: 100%; border-radius: 99px;
  background: linear-gradient(90deg, var(--accent), var(--accent-hi));
  transition: width var(--dur-md) var(--ease-out);
  position: relative;
}
.hp-scan-bar::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.42), transparent);
  animation: hpSweep 1200ms linear infinite;
}

/* skeleton for the pending state */
.hp-skel {
  border-radius: var(--r-md); height: var(--h, 76px);
  background: linear-gradient(90deg, var(--surface) 0%, var(--surface-2) 46%, var(--surface) 92%);
  background-size: 420px 100%;
  animation: hpShimmer 1250ms linear infinite;
  border: 1px solid var(--border-subtle);
}

/* ============ empty state ============ */
.hp-empty {
  border-radius: var(--r-lg); border: 1px dashed var(--border);
  background: var(--surface); padding: 2.3rem 1.6rem; text-align: center;
  animation: hpFade var(--dur-lg) var(--ease-out) both;
}
.hp-empty-mark { margin: 0 auto .8rem; width: 40px; height: 40px; opacity: .8; }
.hp-empty-title { font-size: .95rem; font-weight: 620; color: var(--text-hi); }
.hp-empty-body { font-size: .82rem; color: var(--text-mid); margin-top: .35rem; line-height: 1.6; max-width: 46ch; margin-inline: auto; }

/* ============ queue (sidebar) ============ */
.hp-q { display: flex; flex-direction: column; gap: 6px; }
.hp-q-item {
  display: flex; align-items: center; gap: 9px;
  padding: .5rem .6rem; border-radius: var(--r-sm);
  background: var(--surface-2); border: 1px solid var(--border-subtle);
  border-left: 2px solid var(--tone);
  animation: hpRise var(--dur-md) var(--ease-out) both;
  transition: background var(--dur-sm) var(--ease-std);
}
.hp-q-item:hover { background: var(--surface-3); }
.hp-q-id { font-family: var(--font-mono); font-size: .76rem; color: var(--text-hi); font-weight: 600; flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hp-q-val { font-family: var(--font-mono); font-size: .76rem; color: var(--tone); font-weight: 600; }
.hp-q-n { font-size: .66rem; color: var(--text-low); }

/* ============ sidebar meta ============ */
.hp-side-title {
  font-size: .655rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
  color: var(--text-low); margin: 1.35rem 0 .55rem;
}
.hp-kv { display: flex; justify-content: space-between; gap: 10px; padding: .3rem 0; border-bottom: 1px dashed var(--border-subtle); }
.hp-kv:last-child { border-bottom: none; }
.hp-kv .k { font-size: .745rem; color: var(--text-mid); }
.hp-kv .v { font-size: .745rem; color: var(--text-hi); font-family: var(--font-mono); font-weight: 550; }

/* ============ footer / model card ============ */
.hp-foot {
  margin-top: 2.6rem; padding-top: 1.1rem; border-top: 1px solid var(--border-subtle);
  font-size: .745rem; color: var(--text-low); line-height: 1.75;
}
.hp-foot b { color: var(--text-mid); font-weight: 600; }
.hp-foot .hp-mono { color: var(--text-mid); }

/* ============ compact legend ============ */
.hp-legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: .73rem; color: var(--text-mid); margin-top: .5rem; }
.hp-legend i { width: 9px; height: 9px; border-radius: 2px; display: inline-block; margin-right: 5px; vertical-align: -1px; }

/* ============ disclaimer strip ============ */
.hp-disc {
  display: flex; gap: 10px; align-items: flex-start;
  border-radius: var(--r-md); padding: .7rem .9rem;
  background: var(--uncertain-soft); border: 1px solid var(--uncertain-line);
  font-size: .785rem; line-height: 1.6; color: var(--text);
}
.hp-disc b { color: var(--text-hi); }
"""

# --------------------------------------------------------------------------
# Site chrome: brand bar, top navigation, and the marketing-page primitives
# --------------------------------------------------------------------------
# The nav is built from real st.button widgets rather than anchor tags, so a
# tab switch is a rerun instead of a full page reload. Streamlit gives a
# container a stable `.st-key-<key>` class when you pass key=, which is what
# lets the nav row be styled without touching every other button in the app.
# The active tab is rendered as kind="primary" and re-skinned here from a
# filled button into an underlined nav item.
SITE = """
/* ============ brand bar ============ */
.hp-brandbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 1.4rem; flex-wrap: wrap; padding: .15rem 0 .8rem;
}
.hp-brand { display: flex; align-items: center; gap: .68rem; }
.hp-brand-mark { color: var(--accent); display: flex; align-items: center; }
.hp-brand-mark svg { display: block; }
.hp-brand-name {
  font-family: var(--font-display);
  font-size: 1.58rem; font-weight: 600; letter-spacing: -.004em;
  color: var(--text-hi); line-height: 1.02;
}
.hp-brand-sub {
  font-size: .6rem; font-weight: 600; letter-spacing: .26em;
  text-transform: uppercase; color: var(--text-low); margin-top: 3px;
}
.hp-brand-right { display: flex; align-items: center; gap: .42rem; flex-wrap: wrap; }

/* ============ top navigation ============ */
.st-key-sitenav {
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--scrim);
  margin-bottom: 1.5rem;
}
.st-key-sitenav [data-testid="stHorizontalBlock"] { gap: 0 !important; }
.st-key-sitenav [data-testid="stColumn"] { padding: 0 !important; }
.st-key-sitenav .stButton { margin: 0 !important; }
.st-key-sitenav .stButton > button {
  width: 100%;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: .78rem .35rem !important;
  font-size: .818rem !important;
  font-weight: 600 !important;
  letter-spacing: -.006em;
  color: var(--text-mid) !important;
  position: relative;
  transform: none !important;
  transition: color var(--dur-sm) var(--ease-std),
              background var(--dur-sm) var(--ease-std),
              box-shadow var(--dur-md) var(--ease-out);
}
.st-key-sitenav .stButton > button::after { display: none; }
.st-key-sitenav .stButton > button * { color: inherit !important; }
.st-key-sitenav .stButton > button:hover {
  color: var(--text-hi) !important; background: var(--sheen) !important;
}
/* The active-tab underline is an inset box-shadow, not an ::after bar.
   Streamlit ships `top: 0` on that pseudo-element, and an absolutely
   positioned box with top, bottom and height all set is over-constrained --
   CSS honours `top` and the rule lands at the wrong edge. A shadow has no
   position to fight over, transitions cleanly, and costs no layout. */
.st-key-sitenav .stButton > button:hover {
  box-shadow: inset 0 -2px 0 var(--border) !important;
}
.st-key-sitenav .stButton > button[kind="primary"] {
  color: var(--text-hi) !important;
  background: var(--surface) !important;
  font-weight: 680 !important;
  box-shadow: inset 0 -2px 0 var(--accent) !important;
}
.st-key-sitenav .stButton > button[kind="primary"] * { color: var(--text-hi) !important; }

/* the appearance toggle rides at the right-hand end of the nav, as a
   utility control rather than a tab -- so it stays reachable on the pages
   where the sidebar is not rendered at all */
.st-key-sitenav [data-testid="stRadioGroup"] {
  margin: .34rem .1rem .34rem 0 !important;
}
.st-key-sitenav [data-testid="stRadioOption"] {
  padding: .3rem .5rem !important;
  font-size: .715rem !important;
}
.st-key-sitenav [data-testid="stElementContainer"]:has([data-testid="stRadioGroup"]) {
  display: flex; align-items: center; height: 100%;
}

/* ============ hero ============ */
.hp-hero {
  display: grid; grid-template-columns: 1.35fr .95fr; gap: 3.2rem;
  align-items: center; padding: 2.8rem 0 1.6rem;
}
.hp-hero-eyebrow {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: .64rem; font-weight: 600; letter-spacing: .24em;
  text-transform: uppercase; color: var(--accent-hi);
  padding: .34rem .78rem; border: 1px solid var(--accent-line);
  background: var(--accent-soft); border-radius: var(--r-pill);
  animation: hpRise var(--dur-lg) var(--ease-out) both;
}
.hp-hero-title {
  font-family: var(--font-display);
  font-size: 3.35rem; line-height: 1.06; font-weight: 500;
  letter-spacing: -.012em; color: var(--text-hi);
  margin: 1.25rem 0 1.05rem; max-width: 16ch;
  animation: hpRise var(--dur-lg) var(--ease-out) 60ms both;
}
.hp-hero-body {
  font-size: 1.005rem; line-height: 1.68; color: var(--text-mid);
  max-width: 54ch;
  animation: hpRise var(--dur-lg) var(--ease-out) 120ms both;
}
.hp-hero-note {
  margin-top: 1.05rem; font-size: .765rem; color: var(--text-low);
  display: flex; align-items: center; gap: 7px;
  animation: hpFade var(--dur-xl) var(--ease-out) 300ms both;
}
.hp-hero-note::before {
  content: ""; width: 15px; height: 1px; background: var(--border-strong);
  flex: 0 0 auto;
}

/* the hero's right-hand spec card */
.hp-spec {
  border: 1px solid var(--border); border-radius: var(--r-lg);
  background: linear-gradient(165deg, var(--surface) 0%, var(--surface-2) 100%);
  box-shadow: var(--shadow-2); overflow: hidden;
  animation: hpRise var(--dur-xl) var(--ease-out) 180ms both;
}
.hp-spec-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: .72rem .95rem; border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-2);
}
.hp-spec-head .t {
  font-size: .685rem; font-weight: 660; letter-spacing: .14em;
  text-transform: uppercase; color: var(--text-mid);
}
.hp-spec-row {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; padding: .62rem .95rem;
  border-bottom: 1px solid var(--border-subtle);
}
.hp-spec-row:last-child { border-bottom: none; }
.hp-spec-row .k { font-size: .775rem; color: var(--text-mid); }
.hp-spec-row .v {
  font-family: var(--font-mono); font-size: .84rem; font-weight: 600;
  color: var(--text-hi); font-variant-numeric: tabular-nums;
}
.hp-spec-row .v.tone { color: var(--tone); }

/* ============ pillar / feature cards ============ */
.hp-cards { display: grid; gap: 14px; margin: .3rem 0 .2rem; }
.hp-card {
  border: 1px solid var(--border-subtle); border-radius: var(--r-lg);
  background: var(--surface); padding: 1.15rem 1.2rem 1.25rem;
  box-shadow: var(--shadow-1);
  animation: hpRise var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
  transition: border-color var(--dur-md) var(--ease-std),
              box-shadow var(--dur-md) var(--ease-std),
              transform var(--dur-md) var(--ease-out);
  position: relative; overflow: hidden;
}
.hp-card::before {
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent 70%);
  transform: scaleX(0); transform-origin: left;
  transition: transform var(--dur-lg) var(--ease-out);
}
.hp-card:hover {
  border-color: var(--border); box-shadow: var(--shadow-2);
  transform: translateY(-2px);
}
.hp-card:hover::before { transform: scaleX(1); }
.hp-card-kicker {
  font-size: .62rem; font-weight: 600; letter-spacing: .22em;
  text-transform: uppercase; color: var(--accent); display: block;
  margin-bottom: .62rem;
}
.hp-card-title {
  font-family: var(--font-display);
  font-size: 1.42rem; font-weight: 600; letter-spacing: -.004em;
  color: var(--text-hi); line-height: 1.22; margin-bottom: .58rem;
}
.hp-card-body { font-size: .855rem; line-height: 1.74; color: var(--text-mid); }

/* ============ stat band ============ */
.hp-band {
  display: grid; gap: 1px; background: var(--border-subtle);
  border: 1px solid var(--border-subtle); border-radius: var(--r-lg);
  overflow: hidden; margin: .2rem 0;
}
.hp-band-cell {
  background: var(--surface); padding: 1.05rem 1rem;
  animation: hpFade var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
}
.hp-band-value {
  font-family: var(--font-mono); font-size: 1.62rem; font-weight: 600;
  color: var(--text-hi); letter-spacing: -.03em; line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.hp-band-value small {
  font-size: .92rem; color: var(--text-mid); font-weight: 500; margin-left: 1px;
}
.hp-band-label {
  font-size: .715rem; color: var(--text-low); margin-top: .34rem;
  line-height: 1.45;
}

/* ============ numbered process steps ============ */
.hp-steps { display: grid; gap: 0; margin: .3rem 0; }
.hp-step {
  display: grid; grid-template-columns: 42px 1fr; gap: 1rem;
  padding: 1rem 0; border-bottom: 1px solid var(--border-subtle);
  animation: hpRise var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
}
.hp-step:last-child { border-bottom: none; }
.hp-step-n {
  font-family: var(--font-mono); font-size: .76rem; font-weight: 600;
  color: var(--accent); border: 1px solid var(--accent-line);
  background: var(--accent-soft); border-radius: var(--r-sm);
  height: 30px; display: flex; align-items: center; justify-content: center;
}
.hp-step-t {
  font-size: .93rem; font-weight: 680; color: var(--text-hi);
  letter-spacing: -.022em; margin-bottom: .22rem;
}
.hp-step-b { font-size: .832rem; line-height: 1.66; color: var(--text-mid); }

/* ============ data table ============ */
.hp-tablewrap {
  border: 1px solid var(--border-subtle); border-radius: var(--r-lg);
  overflow-x: auto; background: var(--surface); box-shadow: var(--shadow-1);
}
.hp-table { width: 100%; border-collapse: collapse; font-size: .818rem; }
.hp-table thead th {
  text-align: left; padding: .7rem .9rem; background: var(--surface-2);
  font-size: .655rem; font-weight: 680; letter-spacing: .13em;
  text-transform: uppercase; color: var(--text-mid);
  border-bottom: 1px solid var(--border-subtle); white-space: nowrap;
}
.hp-table tbody td {
  padding: .72rem .9rem; border-bottom: 1px solid var(--border-subtle);
  color: var(--text-mid); line-height: 1.6; vertical-align: top;
}
.hp-table tbody tr:last-child td { border-bottom: none; }
.hp-table tbody tr { transition: background var(--dur-sm) var(--ease-std); }
.hp-table tbody tr:hover { background: var(--sheen); }
.hp-table td.name, .hp-table th.name {
  color: var(--text-hi); font-weight: 640; min-width: 148px;
}
.hp-table td.num, .hp-table th.num {
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  color: var(--text-hi); white-space: nowrap;
}
.hp-table tr.is-flagged td { background: var(--malignant-soft); }
.hp-table tr.is-flagged td.name { color: var(--malignant); }
.hp-table tr.is-good td.num.lead { color: var(--benign); }

/* ============ confusion matrix ============ */
.hp-cm {
  display: grid; grid-template-columns: auto 1fr 1fr; gap: 7px;
  max-width: 460px; margin: .2rem 0;
}
.hp-cm-h {
  font-size: .655rem; font-weight: 680; letter-spacing: .12em;
  text-transform: uppercase; color: var(--text-low);
  display: flex; align-items: center; justify-content: center;
  padding: .3rem; text-align: center;
}
.hp-cm-h.side { writing-mode: vertical-rl; transform: rotate(180deg); }
.hp-cm-cell {
  border-radius: var(--r-md); padding: .85rem .7rem; text-align: center;
  border: 1px solid var(--tone-line); background: var(--tone-soft);
  animation: hpPop var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
}
.hp-cm-n {
  font-family: var(--font-mono); font-size: 1.42rem; font-weight: 600;
  color: var(--tone); font-variant-numeric: tabular-nums; line-height: 1.1;
}
.hp-cm-l {
  font-size: .662rem; color: var(--text-low); margin-top: .28rem;
  letter-spacing: .04em; text-transform: uppercase; font-weight: 620;
}

/* ============ limitations list ============ */
.hp-limits { display: grid; gap: 0; }
.hp-limit {
  display: grid; grid-template-columns: 20px 1fr; gap: .85rem;
  padding: .92rem 0; border-bottom: 1px solid var(--border-subtle);
  animation: hpFade var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
}
.hp-limit:last-child { border-bottom: none; }
.hp-limit-mark { color: var(--uncertain); display: flex; margin-top: 2px; }
.hp-limit-t {
  font-size: .885rem; font-weight: 680; color: var(--text-hi);
  letter-spacing: -.02em; margin-bottom: .2rem;
}
.hp-limit-b { font-size: .828rem; line-height: 1.66; color: var(--text-mid); }

/* ============ page heading ============ */
.hp-pagehead { margin: 1.1rem 0 1.6rem; }
.hp-pagehead-kicker {
  font-size: .64rem; font-weight: 600; letter-spacing: .24em;
  text-transform: uppercase; color: var(--accent); display: block;
  margin-bottom: .7rem;
  animation: hpFade var(--dur-lg) var(--ease-out) both;
}
.hp-pagehead-title {
  font-family: var(--font-display);
  font-size: 2.95rem; font-weight: 500; letter-spacing: -.01em;
  color: var(--text-hi); line-height: 1.1; margin: 0 0 .7rem;
  max-width: 24ch;
  animation: hpRise var(--dur-lg) var(--ease-out) 50ms both;
}
.hp-pagehead-sub {
  font-size: .928rem; line-height: 1.62; color: var(--text-mid); max-width: 62ch;
  animation: hpRise var(--dur-lg) var(--ease-out) 110ms both;
}
.hp-pagehead-rule {
  height: 1px; background: var(--border);
  margin-top: 1.6rem;
  animation: hpGrow var(--dur-xl) var(--ease-out) 180ms both; transform-origin: left;
}

/* ============ lead paragraph ============ */
.hp-lead {
  font-size: 1.04rem; line-height: 1.82; color: var(--text-mid);
  max-width: 66ch; margin: .2rem 0 .4rem;
  animation: hpRise var(--dur-lg) var(--ease-out) both;
}
.hp-lead strong, .hp-lead b { color: var(--text-hi); font-weight: 640; }
.hp-lead em { color: var(--text); font-style: italic; }

/* ============ call to action band ============ */
.hp-cta {
  border: 1px solid var(--accent-line); border-radius: var(--r-lg);
  background:
    radial-gradient(560px 200px at 88% -40%, var(--accent-soft), transparent 70%),
    var(--surface);
  padding: 1.5rem 1.6rem; box-shadow: var(--shadow-2);
  animation: hpRise var(--dur-lg) var(--ease-out) both;
}
.hp-cta-title {
  font-family: var(--font-display);
  font-size: 1.75rem; font-weight: 600; letter-spacing: -.006em;
  color: var(--text-hi); margin-bottom: .48rem; line-height: 1.2;
}
.hp-cta-body {
  font-size: .875rem; line-height: 1.66; color: var(--text-mid); max-width: 62ch;
}

/* ============ tooltip affordances ============ */
.hp-info {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; margin-left: 7px; vertical-align: 1px;
  color: var(--text-low); cursor: help; border-radius: 50%;
  transition: color var(--dur-sm) var(--ease-std),
              background var(--dur-sm) var(--ease-std);
}
.hp-info:hover, .hp-info:focus-visible {
  color: var(--accent); background: var(--accent-soft); outline: none;
}
.hp-info svg { width: 13px; height: 13px; }
.hp-term {
  border-bottom: 1px dotted var(--border-strong); cursor: help;
  transition: border-color var(--dur-sm) var(--ease-std),
              color var(--dur-sm) var(--ease-std);
}
.hp-term:hover, .hp-term:focus-visible {
  border-bottom-color: var(--accent); color: var(--text-hi); outline: none;
}

/* ============ morphological profile ============ */
.hp-mp { display: grid; gap: 16px; margin: .2rem 0; }
.hp-mp-row { animation: hpRise var(--dur-lg) var(--ease-out) var(--d, 0ms) both; }
.hp-mp-head {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; margin-bottom: .4rem;
}
.hp-mp-title {
  font-size: .82rem; font-weight: 660; color: var(--text-hi); letter-spacing: -.018em;
}
.hp-mp-read {
  font-family: var(--font-mono); font-size: .77rem; font-weight: 600;
  color: var(--accent-hi); font-variant-numeric: tabular-nums;
}
.hp-mp-track {
  display: flex; height: 13px; border-radius: var(--r-pill); overflow: hidden;
  background: var(--surface-2); border: 1px solid var(--border-subtle);
}
.hp-mp-seg { height: 100%; transition: width var(--dur-lg) var(--ease-out); }
.hp-mp-seg.b1 { background: var(--surface-3); }
.hp-mp-seg.b2 { background: var(--accent-line); }
.hp-mp-seg.b3 { background: var(--accent); }
.hp-mp-seg.b4 { background: var(--accent); }
/* a four-band track needs an extra step so the ramp still reads
   as a progression rather than two identical blocks at the top */
.hp-mp-track.n4 .hp-mp-seg.b3 { background: var(--accent-half); }
.hp-mp-keys {
  display: flex; gap: 14px; flex-wrap: wrap; margin-top: .42rem;
  font-size: .715rem; color: var(--text-mid);
}
.hp-mp-key i {
  width: 9px; height: 9px; border-radius: 2px; display: inline-block;
  margin-right: 5px; vertical-align: -1px; border: 1px solid var(--border-subtle);
}
.hp-mp-key i.b1 { background: var(--surface-3); }
.hp-mp-key i.b2 { background: var(--accent-line); }
.hp-mp-key i.b3 { background: var(--accent); }
.hp-mp-key i.b4 { background: var(--accent); }
.hp-mp-keys.n4 i.b3 { background: var(--accent-half); }
.hp-mp-key b { color: var(--text-hi); font-weight: 620; font-family: var(--font-mono); }
.hp-mp-detail {
  font-size: .73rem; color: var(--text-low); line-height: 1.55; margin-top: .3rem;
}
.hp-mp-measure {
  font-family: var(--font-mono); font-size: .705rem; color: var(--text-mid);
  margin-top: .32rem; font-variant-numeric: tabular-nums;
  padding: .22rem .55rem; background: var(--surface-2); border-radius: var(--r-xs);
  display: inline-block; border: 1px solid var(--border-subtle);
}
.hp-mp-note {
  font-size: .755rem; line-height: 1.62; color: var(--text-mid);
  border-left: 2px solid var(--uncertain-line); padding-left: .8rem; margin-top: .2rem;
}
.hp-mp-note b { color: var(--text-hi); }

/* ============ console: sticky control rail ============ */
/* The left column holds the inputs and the threshold; the right holds
   everything they drive. align-self is load-bearing: a flex child stretches
   to full height by default, and a full-height box has nothing to stick to. */
.st-key-console [data-testid="stColumn"]:first-of-type {
  position: sticky; top: .6rem; align-self: flex-start; z-index: 2;
}
.st-key-console [data-testid="stColumn"]:first-of-type > div {
  background: var(--surface); border: 1px solid var(--border-subtle);
  border-radius: var(--r-lg); padding: 1rem .95rem 1.1rem;
  box-shadow: var(--shadow-1);
}
.hp-rail-title {
  font-size: .78rem; font-weight: 660; color: var(--text-hi);
  margin: .1rem 0 .3rem; letter-spacing: -.015em;
}
.hp-rail-read {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-top: .35rem;
}
.hp-rail-read .k { font-size: .715rem; color: var(--text-low); }
.hp-rail-read .v {
  font-family: var(--font-mono); font-size: 1.12rem; font-weight: 600;
  color: var(--accent-hi); font-variant-numeric: tabular-nums;
}
.hp-rail-sub {
  font-size: .69rem; color: var(--text-low); line-height: 1.5;
  margin-bottom: .7rem;
}

/* ============ involvement ladder ============ */
/* The stepped extent reading. Shaped like the graphic people expect from an
   oncology tool, and deliberately not labelled like one: no numerals, no
   roman numbers, no use of "stage" as a label. The active step borrows the
   semantic tone the triage banner already carries, so the two read as one
   quantity rather than two scales. */
.hp-lad {
  border: 1px solid var(--border); border-radius: var(--r-lg);
  background: var(--surface);
  padding: 1.15rem 1.3rem 1.2rem; box-shadow: var(--shadow-1);
  animation: hpRise var(--dur-lg) var(--ease-out) both;
}
.hp-lad-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1rem; margin-bottom: 1.1rem;
}
.hp-lad-kicker {
  display: flex; align-items: center; gap: 3px;
  font-size: .655rem; font-weight: 680; letter-spacing: .15em;
  text-transform: uppercase; color: var(--text-low); margin-bottom: .32rem;
}
.hp-lad-band {
  font-size: 1.32rem; font-weight: 760; letter-spacing: -.032em;
  color: var(--text-hi); line-height: 1.15;
}
.hp-lad-band .n {
  display: block; font-size: .8rem; font-weight: 500; color: var(--text-mid);
  letter-spacing: -.01em; margin-top: .14rem;
}
.hp-lad-figure {
  font-family: var(--font-mono); font-size: 1.72rem; font-weight: 600;
  color: var(--tone); font-variant-numeric: tabular-nums; line-height: 1;
  text-align: right; white-space: nowrap;
}
.hp-lad-figure small {
  display: block; font-size: .6rem; color: var(--text-low);
  font-family: var(--font-ui); letter-spacing: .12em; text-transform: uppercase;
  margin-top: .3rem; font-weight: 620;
}
.hp-lad-steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.hp-lad-step {
  display: grid; grid-template-rows: 104px auto;
  animation: hpRise var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
}
.hp-lad-bar {
  align-self: end; height: var(--h, 50%); min-height: 26px;
  border-radius: var(--r-sm) var(--r-sm) 0 0;
  background: var(--surface-2);
  border: 1px solid var(--border-subtle); border-bottom: none;
  transition: background var(--dur-md) var(--ease-std),
              border-color var(--dur-md) var(--ease-std);
}
.hp-lad-step.is-on .hp-lad-bar {
  background: var(--tone-soft); border-color: var(--tone-line);
  border-width: 1.5px; box-shadow: inset 0 -5px 0 var(--tone);
}
.hp-lad-cap { border-top: 2px solid var(--border-subtle); padding-top: .45rem; }
.hp-lad-step.is-on .hp-lad-cap { border-top-color: var(--tone); }
.hp-lad-name {
  display: flex; align-items: center; gap: 2px;
  font-size: .755rem; font-weight: 620; color: var(--text-mid);
  letter-spacing: -.012em;
}
.hp-lad-step.is-on .hp-lad-name { color: var(--text-hi); font-weight: 700; }
.hp-lad-range {
  display: block; font-size: .655rem; color: var(--text-low);
  margin-top: .12rem; font-family: var(--font-mono);
}
.hp-lad-basis {
  margin-top: .95rem; padding-top: .72rem;
  border-top: 1px solid var(--border-subtle);
  font-size: .71rem; line-height: 1.6; color: var(--text-low); max-width: 88ch;
}

/* ============ staging reference ============ */
/* Reference material, never model output. Styled as a reference block rather
   than a result card so it cannot be mistaken for something computed from
   the reader's data. */
.hp-stg {
  border: 1px solid var(--border-subtle); border-radius: var(--r-lg);
  background: var(--surface-2);
  padding: 1.05rem 1.2rem 1.1rem;
  animation: hpRise var(--dur-lg) var(--ease-out) both;
}
.hp-stg-kicker {
  display: flex; align-items: center; gap: 3px;
  font-size: .63rem; font-weight: 700; letter-spacing: .15em;
  text-transform: uppercase; color: var(--text-low);
}
.hp-stg-title {
  display: block; font-size: .95rem; font-weight: 720; letter-spacing: -.022em;
  color: var(--text-hi); margin-top: .26rem;
}
.hp-stg-intro {
  font-size: .755rem; line-height: 1.62; color: var(--text-mid);
  margin: .38rem 0 .85rem; max-width: 80ch;
}
.hp-stg-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.hp-stg-item {
  position: relative; display: flex; flex-direction: column; gap: .22rem;
  padding: .62rem .7rem; border-radius: var(--r-sm);
  background: var(--surface); border: 1px solid var(--border-subtle);
  cursor: help;
  transition: border-color var(--dur-sm) var(--ease-std),
              transform var(--dur-sm) var(--ease-std);
}
.hp-stg-item:hover, .hp-stg-item:focus-visible {
  border-color: var(--border-strong); transform: translateY(-1px); outline: none;
}
.hp-stg-num {
  font-family: var(--font-mono); font-size: 1.05rem; font-weight: 600;
  color: var(--text-hi); line-height: 1;
}
.hp-stg-name { font-size: .675rem; line-height: 1.4; color: var(--text-mid); }
.hp-stg-mark {
  position: absolute; top: .45rem; right: .5rem;
  color: var(--text-low); opacity: .45; display: flex;
}
.hp-stg-item:hover .hp-stg-mark { opacity: .8; }
.hp-stg-why {
  margin-top: .9rem; padding-top: .8rem; border-top: 1px solid var(--border);
  font-size: .735rem; line-height: 1.68; color: var(--text-mid); max-width: 84ch;
}
.hp-stg-why b { color: var(--text-hi); font-weight: 680; }

@media (max-width: 680px) {
  .hp-stg-row { grid-template-columns: repeat(2, 1fr); }
  .hp-lad-steps { gap: 6px; }
  .hp-lad-step { grid-template-rows: 76px auto; }
  .hp-lad-name { font-size: .69rem; }
  .hp-lad-range { font-size: .6rem; }
}

/* ============ site footer ============ */
.hp-sitefoot {
  margin-top: 2.6rem; padding-top: 1.4rem;
  border-top: 1px solid var(--border-subtle);
}
.hp-sitefoot-top {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 2rem; flex-wrap: wrap; margin-bottom: 1.15rem;
}
.hp-sitefoot-brand { display: flex; align-items: center; gap: .6rem; }
.hp-sitefoot-brand .n {
  font-size: .95rem; font-weight: 740; letter-spacing: -.035em; color: var(--text-mid);
}
.hp-sitefoot-pos {
  font-size: .765rem; color: var(--text-low); line-height: 1.6; max-width: 46ch;
}
.hp-sitefoot-note {
  font-size: .742rem; line-height: 1.62; color: var(--text-low);
  border-left: 2px solid var(--uncertain-line); padding-left: .8rem;
  max-width: 78ch;
}
"""

REDUCED_MOTION = """
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
    scroll-behavior: auto !important;
  }
  .hp-tile:hover, .hp-gal-item:hover, .stButton > button:hover { transform: none !important; }
}
"""

RESPONSIVE = """
@media (max-width: 760px) { .stApp .hp-isnot { grid-template-columns: 1fr; } }
@media (max-width: 900px) {
  .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
  .hp-mast-title { font-size: 1.32rem; }
  .hp-triage-figure { font-size: 2rem; }
  .hp-verdict { gap: 14px; }
}
/* Site chrome collapses to a single column before the nav starts to crowd. */
@media (max-width: 1020px) {
  .stApp .hp-hero { grid-template-columns: 1fr; gap: 1.5rem; }
  .stApp .hp-hero-title { font-size: 2.1rem; max-width: none; }
}
@media (max-width: 760px) {
  .stApp .hp-hero-title { font-size: 1.78rem; }
  .stApp .hp-brandbar { padding-bottom: .6rem; }
  .stApp .hp-cm { grid-template-columns: auto 1fr 1fr; font-size: .9em; }
  .stApp .hp-sitefoot-top { flex-direction: column; gap: 1rem; }
}
"""


_SELECTOR = re.compile(r'^(?P<sel>[^@{}\n][^{}\n]*?)\s*\{', re.M)


def scope_css(css: str, scope: str = ".stApp") -> str:
    """
    Prefix every selector with `.stApp`.

    Streamlit styles its own markdown output with attribute+element selectors
    such as `[data-testid="stMarkdownContainer"] h1`, specificity (0,1,1).
    A bare `.hp-mast-title` is (0,1,0) and loses, so custom type sizes would
    silently fall back to Streamlit's. Scoping lifts every component rule to
    (0,2,x) and wins cleanly -- without carpet-bombing the sheet with
    !important, which would then break the monospace numerals.
    """
    def rep(m: "re.Match") -> str:
        parts = [p.strip() for p in m.group("sel").split(",") if p.strip()]
        parts = [p if p.startswith(scope) else f"{scope} {p}" for p in parts]
        return ", ".join(parts) + " {"
    return _SELECTOR.sub(rep, css)

VINTAGE = """
/* ============================================================================
   VINTAGE PASS
   ----------------------------------------------------------------------------
   The rules below sit last on purpose. Everything above builds the product;
   this layer sets its manners -- rounder corners, a serif wherever a phrase is
   meant to be read rather than scanned, small-caps tracking on labels, and
   hairline rules instead of gradients. Kept as one block so the visual
   language can be read, argued with, or lifted out in one piece.
   ========================================================================== */

/* scope_css prefixes bare selectors with .stApp, which would turn :root into
   `.stApp :root` and match nothing. Custom properties set on .stApp itself
   inherit to everything inside it, which is all this needs. */
.stApp {
  --r-xs: 4px; --r-sm: 9px; --r-md: 14px; --r-lg: 20px; --r-xl: 28px;
}

/* --- the serif carries every display phrase, never interface text --- */
.hp-verdict-label,
.hp-lad-band,
.hp-stg-title,
.hp-empty-title,
.hp-limit-t,
.hp-cm-title,
.hp-band-value {
  font-family: var(--font-display) !important;
  letter-spacing: -.004em;
}
.hp-verdict-label { font-size: 1.72rem; font-weight: 600; line-height: 1.15; }
.hp-lad-band      { font-size: 1.72rem; font-weight: 600; }
.hp-stg-title     { font-size: 1.26rem; font-weight: 600; }
.hp-empty-title   { font-size: 1.3rem;  font-weight: 600; }
.hp-limit-t       { font-size: 1.06rem; font-weight: 600; }

/* --- labels become small caps: the vintage tell, and it buys back space --- */
.hp-tile-label,
.hp-lad-kicker,
.hp-stg-kicker,
.hp-rail-title,
.hp-side-title,
.hp-spec-head .t,
.hp-triage-badge,
.hp-xplain-head .t {
  letter-spacing: .2em !important;
  text-transform: uppercase;
  font-weight: 600 !important;
}

/* --- rules are hairlines, never gradients --- */
.hp-rule,
.hp-pagehead-rule { background: var(--border-subtle) !important; }

/* --- cards: softer, flatter, more generous inside --- */
.hp-card,
.hp-tile,
.hp-note,
.hp-spec,
.hp-xplain,
.hp-lad,
.hp-stg,
.hp-triage {
  box-shadow: none !important;
  border-color: var(--border-subtle) !important;
}
.hp-card:hover { box-shadow: var(--shadow-1) !important; transform: translateY(-1px); }
.hp-card  { padding: 1.5rem 1.55rem 1.6rem; }
.hp-tile  { padding: 1.15rem 1.2rem 1.25rem; }
.hp-lad   { padding: 1.5rem 1.65rem 1.55rem; }
.hp-stg   { padding: 1.35rem 1.5rem 1.4rem; }

/* --- more air between blocks, the way a printed page breathes --- */
.hp-tiles { gap: 14px; }
.hp-cards { gap: 18px; }
.block-container { padding-top: 2.2rem !important; }

/* --- primary action: a quiet rose slab, letterspaced, no gradient --- */
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  border: 1px solid var(--accent) !important;
  border-radius: var(--r-sm) !important;
  box-shadow: none !important;
  font-size: .74rem !important;
  font-weight: 600 !important;
  letter-spacing: .16em !important;
  text-transform: uppercase;
  padding: .78rem 1.2rem !important;
  transition: background var(--dur-sm) var(--ease-std),
              border-color var(--dur-sm) var(--ease-std);
}
.stButton > button[kind="primary"]:hover {
  background: var(--accent-hi) !important;
  border-color: var(--accent-hi) !important;
  transform: none !important;
}
/* the nav is a row of tabs, not buttons -- exempt it from the slab above */
.st-key-sitenav .stButton > button[kind="primary"] {
  background: var(--surface) !important;
  border: none !important;
  text-transform: none;
  letter-spacing: -.006em !important;
  font-size: .818rem !important;
  padding: .78rem .35rem !important;
}

/* --- nav: small caps, wider tracking, hairline frame --- */
.st-key-sitenav .stButton > button {
  font-size: .705rem !important;
  letter-spacing: .18em !important;
  text-transform: uppercase;
  font-weight: 600 !important;
}
.st-key-sitenav .stButton > button[kind="primary"] {
  font-size: .705rem !important;
  letter-spacing: .18em !important;
  text-transform: uppercase;
  font-weight: 700 !important;
}
.st-key-sitenav { background: transparent; border-top: none; }

/* --- tables: hairlines and small-caps headings --- */
.hp-table th {
  font-size: .625rem !important;
  letter-spacing: .2em !important;
  text-transform: uppercase;
  font-weight: 600 !important;
  color: var(--text-mid) !important;
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
}
.hp-table td { border-bottom: 1px solid var(--border-subtle) !important; }

/* --- text inputs and uploader: paper, not chrome --- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
  border-radius: var(--r-sm) !important;
  background: var(--surface) !important;
}
[data-testid="stFileUploaderDropzone"] {
  border-radius: var(--r-md) !important;
  border-style: solid !important;
  border-color: var(--border) !important;
  background: var(--surface-2) !important;
}

/* --- the ladder reads better with the serif sitting a little lower --- */
.hp-lad-figure { font-size: 1.95rem; }

/* --- narrow screens: the serif needs to come down faster than the sans --- */
@media (max-width: 760px) {
  .hp-hero { grid-template-columns: 1fr; gap: 2rem; padding: 1.6rem 0 1rem; }
  .hp-hero-title { font-size: 2.6rem; }
  .hp-pagehead-title { font-size: 2.1rem; }
  .hp-sect-title { font-size: 1.35rem; }
  .hp-mast-title { font-size: 1.8rem; }
}
"""

LANDING = """
/* ============================================================================
   LANDING PASS
   ----------------------------------------------------------------------------
   VINTAGE re-skinned colour and type. This layer changes shape: it is what
   makes the home page read as an illustrated landing page (soft blobs,
   circular icon badges, a connected process line, a rounded sign-off band)
   rather than a data console with a serif font pasted over it.

   Colour discipline carries over unchanged: SEMANTIC tones (benign/uncertain/
   malignant/critical) never appear here. Everything decorative below cycles
   through --accent (rose), --decor2 (muted teal) and --decor3 (dusty plum) so
   the page is not read as dominated by one colour, pink included.
   ========================================================================== */

/* --- rounder, friendlier corners everywhere the token is used --- */
.stApp {
  --r-md: 16px; --r-lg: 26px; --r-xl: 38px;
}

/* --- page wash: rose and teal in balance, not one pink flood --- */
.stApp::before {
  background:
    radial-gradient(1000px 480px at 84% -8%, var(--accent-soft), transparent 68%),
    radial-gradient(900px 460px at 6% 18%, var(--decor2-soft), transparent 66%);
  opacity: .9;
}

/* --- hero: two soft organic blobs sit behind the copy and the spec card --- */
.hp-hero { position: relative; z-index: 0; overflow: visible; }
.hp-hero::before,
.hp-hero::after {
  content: ""; position: absolute; z-index: -1; pointer-events: none;
  filter: blur(48px);
}
.hp-hero::before {
  top: -18%; right: -8%; width: 400px; height: 360px;
  background: var(--accent-soft);
  border-radius: 62% 38% 55% 45% / 45% 55% 42% 58%;
}
.hp-hero::after {
  bottom: -22%; left: 40%; width: 280px; height: 240px;
  background: var(--decor2-soft);
  border-radius: 40% 60% 55% 45% / 55% 40% 60% 45%;
}

/* ============ icon badge row ============ */
.hp-icon-row {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1.4rem;
  margin: 1.4rem 0 .4rem; text-align: center;
}
.hp-icon-item {
  animation: hpRise var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
}
.hp-icon-badge {
  width: 62px; height: 62px; margin: 0 auto .85rem;
  display: flex; align-items: center; justify-content: center;
  border-radius: 999px; background: var(--accent-soft); color: var(--accent-hi);
  border: 1px solid var(--accent-line);
  transition: transform var(--dur-md) var(--ease-out);
}
.hp-icon-item:hover .hp-icon-badge { transform: translateY(-3px) scale(1.04); }
.hp-icon-item:nth-child(4n+2) .hp-icon-badge {
  background: var(--decor2-soft); color: var(--decor2); border-color: var(--decor2-line);
}
.hp-icon-item:nth-child(4n+3) .hp-icon-badge {
  background: var(--decor3-soft); color: var(--decor3); border-color: var(--decor3-line);
}
.hp-icon-item:nth-child(4n+4) .hp-icon-badge {
  background: var(--accent-soft); color: var(--accent-hi); border-color: var(--accent-line);
}
.hp-icon-t {
  font-size: .9rem; font-weight: 680; color: var(--text-hi);
  letter-spacing: -.015em; margin-bottom: .32rem;
}
.hp-icon-b { font-size: .8rem; line-height: 1.6; color: var(--text-mid); padding: 0 .3rem; }

/* ============ connected process flow ============ */
.hp-flow {
  display: grid; grid-template-columns: repeat(var(--n, 4), 1fr);
  gap: .5rem; margin: .4rem 0 .2rem; position: relative;
}
.hp-flow-item {
  position: relative; text-align: center; padding-top: 4px;
  animation: hpRise var(--dur-lg) var(--ease-out) var(--d, 0ms) both;
}
.hp-flow-item::before {
  content: ""; position: absolute; top: 22px; left: -50%; width: 100%;
  height: 1px; background: var(--border-strong); z-index: 0;
}
.hp-flow-item:first-child::before { display: none; }
.hp-flow-dot {
  position: relative; z-index: 1; width: 44px; height: 44px; margin: 0 auto .85rem;
  display: flex; align-items: center; justify-content: center;
  border-radius: 999px; background: var(--accent); color: var(--canvas);
  font-family: var(--font-mono); font-size: .84rem; font-weight: 700;
  box-shadow: 0 0 0 6px var(--canvas);
}
.hp-flow-t {
  font-size: .87rem; font-weight: 680; color: var(--text-hi);
  letter-spacing: -.015em; margin-bottom: .3rem; padding: 0 .3rem;
}
.hp-flow-b {
  font-size: .782rem; line-height: 1.62; color: var(--text-mid); padding: 0 .55rem;
}

/* ============ feature cards: three accents in rotation ============ */
.hp-cards .hp-card:nth-child(3n+1) { --card-accent: var(--accent); }
.hp-cards .hp-card:nth-child(3n+2) { --card-accent: var(--decor2); }
.hp-cards .hp-card:nth-child(3n+3) { --card-accent: var(--decor3); }
.hp-cards .hp-card::before { background: linear-gradient(90deg, var(--card-accent, var(--accent)), transparent 70%) !important; }
.hp-cards .hp-card-kicker { color: var(--card-accent, var(--accent)) !important; }

/* ============ closing sign-off band ============ */
.hp-closing {
  position: relative; overflow: hidden; z-index: 0;
  border-radius: var(--r-xl); border: 1px solid var(--border-subtle);
  background: var(--surface); text-align: center;
  padding: 3.2rem 2rem; margin: .3rem 0;
  animation: hpRise var(--dur-xl) var(--ease-out) both;
}
.hp-closing-blobs { position: absolute; inset: 0; z-index: -1; pointer-events: none; }
.hp-closing-blobs::before,
.hp-closing-blobs::after { content: ""; position: absolute; filter: blur(52px); }
.hp-closing-blobs::before {
  top: -30%; left: -10%; width: 340px; height: 300px; background: var(--accent-soft);
  border-radius: 58% 42% 48% 52% / 42% 58% 42% 58%;
}
.hp-closing-blobs::after {
  bottom: -34%; right: -8%; width: 360px; height: 320px; background: var(--decor3-soft);
  border-radius: 46% 54% 60% 40% / 55% 45% 55% 45%;
}
.hp-closing-kicker {
  display: inline-block; font-size: .64rem; font-weight: 600; letter-spacing: .24em;
  text-transform: uppercase; color: var(--accent-hi); margin-bottom: .9rem;
}
.hp-closing-title {
  font-family: var(--font-display); font-size: 2.35rem; font-weight: 600;
  letter-spacing: -.01em; color: var(--text-hi); line-height: 1.16;
  max-width: 26ch; margin: 0 auto .7rem;
}
.hp-closing-body {
  font-size: .93rem; line-height: 1.68; color: var(--text-mid);
  max-width: 52ch; margin: 0 auto;
}

@media (max-width: 760px) {
  .hp-icon-row { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.6rem 1rem; }
  .hp-flow { grid-template-columns: 1fr; gap: 1.6rem; }
  .hp-flow-item::before { display: none; }
  .hp-closing { padding: 2.2rem 1.3rem; }
  .hp-closing-title { font-size: 1.85rem; }
}
"""

def inject(mode: str = "dark") -> None:
    """Inject the full stylesheet for the chosen mode. Call once per rerun."""
    css = "\n".join([
        FONT_LINK,
        css_variables(mode),
        KEYFRAMES,
        BASE,
        WIDGETS,
        scope_css(COMPONENTS),
        scope_css(SITE),
        RESPONSIVE,
        scope_css(VINTAGE),
        scope_css(LANDING),
        REDUCED_MOTION,
    ])
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
