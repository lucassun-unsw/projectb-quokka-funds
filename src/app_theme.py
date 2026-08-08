"""Dark product theme for the Streamlit app - deliberately NOT the report style.

The report exhibits use `ft_style.py`'s cream Financial-Times look, which is the
right register for a printed document. The app is a different artefact: a retail
product surface, and retail investing products look like trading terminals, not
like newspapers. So the app gets its own dark theme and its own chart palette.

Two things make this safe to do:
  - The app renders its charts LIVE from `results/*.csv`; it never embeds the
    report PNGs. So restyling here cannot change a single report exhibit.
  - `ft_style.apply_ft_style()` and `apply_app_style()` both just set matplotlib
    rcParams, and only one process ever runs at a time (the app never imports
    the figure-building script).

Colour semantics follow the trading convention the audience already reads:
green for gains, red for losses, amber for the thing to look at.

The surface and type tokens below follow one stated system rather than ad-hoc
choices: a true-black page floor with warm-neutral tiles lifted on it, one
interactive accent used for nothing but interaction, no shadows (the tile IS the
elevation), and a 300/400/600/700 weight ladder with 500 deliberately absent —
mid-weights are what make a product surface read as generic. Spacing is
deliberately tighter than a consumer marketing surface would use: this is a dense
analytics tool and the density is the point.
"""
from __future__ import annotations

import matplotlib.pyplot as plt

# Surfaces. A true-black floor with warm-neutral tiles
# lifted onto it - the tile IS the elevation, which is why the system needs no
# shadows at all. The old blue-black floor (#12151D) sat too close to its own
# panels, so the panels barely read as lifted; going to true black widens every
# step for free. Separation is still by SHADE, with a hairline only where an edge
# genuinely has to be found.
BG = "#000000"           # page floor - the true void the tiles lift off
SURFACE = "#1D1D1F"      # panels, cards, sidebar, chart background (tile 1)
SURFACE_HI = "#2A2A2C"   # raised: active pill, table header (tile 2)
SURFACE_HOVER = "#323234"  # hover state - visible enough to signal "clickable"
# White at ~9% over SURFACE, resolved to a flat hex rather than left as rgba():
# matplotlib rcParams and Streamlit's config.toml both take colours, not CSS
# colour functions, and this one token has to serve all three.
BORDER = "#313133"

# Type. On a dark background the type has to be genuinely bright to stay legible
# under classroom projection and on low-gamma laptop screens, so values run near
# white and even the muted labels sit well clear of the surface they print on.
# The warm-neutral greys below are each at least as bright as the blue-tinted
# ones they replace - warming the hue must not quietly undo that legibility work.
TEXT = "#F5F5F7"         # values, headings
TEXT_MUTED = "#C7C7CC"   # labels, captions, axis text
TEXT_DIM = "#98989D"     # provenance lines

# Direction colours sit on the numbers themselves, not only on deltas.
# Western convention, confirmed: green up, red down. Both are pushed lighter than
# the usual terminal pair - saturated mid-tones go muddy against a dark surface.
# Left unchanged by the restyle: a neutral product surface has no trading semantics to
# borrow, and these two were tuned against a dark surface already.
GREEN = "#3DDC97"
RED = "#FF6B80"

# ACCENT is the single INTERACTIVE colour - selected tab, focus ring, brand mark,
# input hover. A bright on-dark link blue: the
# marketing blue (#0066cc) disappears against a near-black tile.
#
# It deliberately no longer appears in any chart. It used to double as Min-CVaR's
# series colour, which meant one hex was saying both "click me" and "this is the
# fund" - so the app's only affordance cue was also its busiest data colour.
#
# One exception survives and is INTENTIONAL: Streamlit draws every
# `column_config.ProgressColumn` bar in the theme's primary colour and exposes no
# override, so the Sharpe, holdings-weight and coverage bars are accent blue while
# the chart beside them is the fund's own hue. Considered and kept: in a table the
# bar length means "how big", in a chart the colour means "which fund", and the
# only way to unify them is to hand-draw the bars and lose the dataframe's sorting
# and toolbar. Do not "fix" this by rebuilding those tables.
ACCENT = "#2997FF"
ON_ACCENT = "#1D1D1F"    # ink on an accent fill; 5.6:1, clears AA

# Series palette. Four method hues spanning the wheel (purple / teal / blue /
# amber) so no two funds read alike, none of them the accent.
PURPLE = "#BF5AF2"
TEAL = "#4EE0CD"
BLUE = "#6BA3FF"
AMBER = "#FFB84D"
SERIES = [PURPLE, TEAL, BLUE, AMBER, GREEN, RED]

# The four methods keep ONE colour each everywhere in the app, so a colour means
# the same thing on every tab. Min-CVaR takes the most vivid hue because it is the
# pick; Min-Variance sits next to it in the cool family because the bootstrap
# cannot separate the two, and the palette should not claim more than the data.
METHOD_COLORS = {"Min-CVaR": PURPLE, "Risk Parity": TEAL,
                 "Min-Variance": BLUE, "Max-Sharpe": AMBER}

# Radius scale, documented rather than ad-hoc. Pill is reserved for things that are ACTIONS - the
# tab pills and the inputs - which is what makes the radius itself an affordance
# signal rather than decoration.
R_SM = "8px"      # buttons, inputs
R_MD = "12px"     # panels, cards
R_LG = "18px"     # large containers
R_PILL = "9999px"  # actions only

# Motion. Every animation in this app fires on INTENT - a hover, a press - and
# never on render. Entrance animations were considered and rejected: the sidebar
# cost slider deliberately sits outside the tab fragments so that changing it
# reruns the whole page, and a fade-and-rise keyed to render would therefore
# replay the entire app every time someone dragged that slider.
#
# The curve is slow-out rather than symmetric: motion leaves quickly and settles
# gently, which is what makes a press feel like it was acknowledged instead of
# animated.
EASE = "cubic-bezier(0.32, 0.72, 0, 1)"
DUR_FAST = "0.12s"   # press feedback - must feel instant
DUR_BASE = "0.22s"   # hover, colour, border

# The frosted tab strip. Tinted with the page floor rather than with SURFACE, so
# it is INVISIBLE at rest - black on black, leaving the pills to sit directly on
# the page with no card around them - and only resolves into a frosted band once
# content scrolls underneath it. A visible container around navigation is chrome
# the navigation does not need; the veil exists solely to stop scrolled content
# colliding with the pills.
SURFACE_GLASS = "rgba(0, 0, 0, 0.72)"

# Colour carries the METHOD, so the three asset families need a second channel or
# "Combined Min-CVaR" and "Crypto-Only Min-CVaR" plot as the same blue line. Line
# style is that channel: one glance gives method (hue) and family (dash) at once.
FAMILY_STYLES = {"Combined": "-", "Equity-Only": "--", "Crypto-Only": ":"}

# The user's own blend must not collide with any fund it is built from. Near-white
# is outside the whole fund palette, so "yours" always reads as the top line.
BLEND = "#FFFFFF"


def apply_app_style() -> None:
    """Set matplotlib rcParams for charts drawn inside the app.

    Charts are drawn on SURFACE (not the page background) so they read as part of
    the card they sit in rather than as pasted-in images - the single change that
    stops matplotlib output looking bolted on.
    """
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": True,
        "axes.edgecolor": BORDER,
        "axes.labelcolor": TEXT_MUTED,
        "axes.titlecolor": TEXT,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": BORDER,
        "grid.linewidth": 0.7,
        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
        "text.color": TEXT,
        "legend.facecolor": SURFACE,
        "legend.edgecolor": BORDER,
        "legend.labelcolor": TEXT,
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.labelsize": 9.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.prop_cycle": plt.cycler(color=SERIES),
    })


def app_fig(figsize=(9, 4.2)):
    """A themed figure + axes, ready to plot on."""
    apply_app_style()
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(SURFACE)
    return fig, ax


def gain_loss(value: float) -> str:
    """Colour a number by direction, the way the audience already reads it."""
    return GREEN if value >= 0 else RED


# System font stack only - no webfont request, so Streamlit Cloud cold starts stay
# fast and the app cannot be broken by a CDN being unreachable. The first entry is
# not a fallback here: it is the CSS keyword that resolves to whatever system face
# the visitor's OS ships, so the app gets a native typeface at zero download cost
# on every platform. The named families after it cover the browsers that ignore it.
FONT_STACK = ('-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", '
              'Roboto, "Helvetica Neue", Arial, sans-serif')

# The face splits at ~19px: the display cut above, the text cut below. Only
# the big quote values are large enough to want the display cut.
DISPLAY_STACK = ('-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", '
                 'Roboto, "Helvetica Neue", Arial, sans-serif')

# Tracking tightens as size grows, and small text is never tracked. Two steps is
# enough for this app: it has exactly one display-scale number and one wordmark.
TRACK_DISPLAY = "-0.022em"
TRACK_TITLE = "-0.012em"

CSS = f"""
<style>
html, body, [class*="css"] {{ font-family: {FONT_STACK}; }}

/* Density: terminals show more per screen than Streamlit does by default. The
   main column's top padding is the exception - Streamlit's floating header bar
   sits over the first ~3rem of the page, so content has to start below it or the
   headline quote reads as jammed against the window chrome. The sidebar keeps its
   default top padding: the header bar does not overlap it, so pushing the QUOKKA
   mark down only opened dead space. */
div.block-container {{ padding-top: 4.2rem; padding-bottom: 2rem; max-width: 1560px; }}
div[data-testid="stVerticalBlock"] {{ gap: 0.55rem; }}

/* The sidebar goes the OTHER way. Nothing floats over it, so Streamlit's default
   top padding plus the collapse-button header row is pure dead space above the
   brand mark - trimmed back so QUOKKA sits near the top edge. */
section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {{
    padding-top: 0.5rem;
    padding-bottom: 0;
    min-height: 0;
    height: auto;
}}
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {{
    padding-top: 0.4rem;
}}

hr {{ margin: 0.7rem 0; border-color: {BORDER}; }}

/* Every number in the app aligns on the digit. */
body, div[data-testid="stMetricValue"], .stDataFrame, table {{
    font-variant-numeric: tabular-nums;
}}

/* Primary navigation as a segmented control. Streamlit's default tabs are bare
   text with a thin underline, which a first-time reader does not recognise as
   navigation at all. So every tab gets an actual button shell - raised fill,
   visible edge, pointer cursor, and a hover state that moves - and the selected
   one is filled in the accent colour. Affordance beats minimalism here: the four
   other tabs are where most of this app lives. */
/* The strip STICKS. The sub-nav is frosted and pinned so the section switcher
   stays reachable without scrolling back up, and the fact sheet is long enough
   that this is a usability fix rather than an effect. `top` clears Streamlit's
   own floating header, which overlays the first few rem of the page.

   Sticky goes on the WRAPPER, not on the tab list itself. A sticky element can
   only travel inside its parent's box, and the tab list's parent is sized to the
   strip exactly (53.7px) - so sticking the list scrolled it away immediately,
   with no error and no warning. The wrapper's own parent spans the whole tabs
   component, which is the room the effect needs. Verified by scrolling a real
   browser: nothing in the test suite can see this.

   The frosted panel therefore lives on the wrapper too. Painting it on the inner
   list instead would leave the list's margins transparent, and page content would
   slide visibly through the gap above and below the pinned strip. */
div[data-testid="stTabs"] div:has(> div[data-baseweb="tab-list"]) {{
    position: sticky;
    top: 3.3rem;
    z-index: 50;
    background: {SURFACE_GLASS};
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    backdrop-filter: saturate(180%) blur(20px);
    border: none;
    /* Top margin, not padding: it has to sit OUTSIDE the frosted veil, or the
       veil grows by the same amount and the pinned band reads as a thick slab.
       The extra air separates the pills from the stat grid above them now that
       there is no container edge doing that job. */
    margin: 20px 0 10px;
}}
div[data-baseweb="tab-list"] {{
    gap: 7px;
    background: transparent;
    padding: 6px 0 7px;
    border: none;
    margin: 0;
    flex-wrap: wrap;
}}
button[data-baseweb="tab"] {{
    border-radius: {R_PILL};
    padding: 9px 20px;
    height: auto;
    background: {SURFACE_HI};
    border: 1px solid {BORDER};
    color: {TEXT_MUTED};
    cursor: pointer;
    transition: background {DUR_BASE} {EASE}, color {DUR_BASE} {EASE},
                border-color {DUR_BASE} {EASE}, transform {DUR_FAST} {EASE};
}}
button[data-baseweb="tab"] p {{
    font-size: 0.90rem;
    font-weight: 400;
    letter-spacing: {TRACK_TITLE};
    color: inherit;
}}
button[data-baseweb="tab"]:hover {{
    background: {SURFACE_HOVER};
    border-color: {ACCENT};
    color: {TEXT};
    transform: translateY(-1px);
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: {ON_ACCENT};
}}
button[data-baseweb="tab"][aria-selected="true"] p {{
    color: {ON_ACCENT};
    font-weight: 600;
}}
button[data-baseweb="tab"][aria-selected="true"]:hover {{
    background: {ACCENT};
    color: {ON_ACCENT};
}}
button[data-baseweb="tab"]:focus-visible {{
    outline: 2px solid {ACCENT};
    outline-offset: 2px;
}}
/* The press. Controls shrink rather than darken, uniformly across the system -
   the one micro-interaction that makes a surface feel like it belongs to the OS.
   Declared after :hover so a press beats the hover lift. */
button[data-baseweb="tab"]:active {{
    transform: scale(0.96);
    transition-duration: {DUR_FAST};
}}
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {{ display: none; }}

/* Metric tiles: flat panels separated by shade, not outlined boxes. */
div[data-testid="stMetric"] {{
    background: {SURFACE};
    border: none;
    border-radius: {R_MD};
    padding: 10px 13px;
}}
div[data-testid="stMetricLabel"] p {{
    color: {TEXT_MUTED};
    font-size: 0.72rem;
    font-weight: 400;
}}
div[data-testid="stMetricValue"] {{
    font-size: 1.35rem;
    font-weight: 600;
    letter-spacing: {TRACK_TITLE};
}}
div[data-testid="stMetricDelta"] {{ font-size: 0.76rem; }}

/* Tables: tight rows, quiet header, no heavy gridlines. */
.stDataFrame {{ font-size: 0.84rem; }}

/* Streamlit floats each dataframe's hover toolbar (download, search, fullscreen)
   just ABOVE the table, with no background of its own - which lands it directly
   on top of the panel subtitle that sits there. On the fact sheet the icons were
   printing through the middle of the caption, so "Cap: 10% per asset (Crypto-Only
   uses..." read as garbled text. Give the toolbar an opaque plate of its own so it
   reads as a floating control rather than as collided glyphs. */
div[data-testid="stElementToolbar"] {{
    background: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: {R_SM};
}}

/* Captions carry most of the app's caveats, so they get the readable muted grey
   rather than the dim provenance grey Streamlit would default them to. */
div[data-testid="stCaptionContainer"], div[data-testid="stCaptionContainer"] p {{
    color: {TEXT_MUTED};
}}

/* Inputs sit on the panel shade, but keep an edge - an input the reader cannot
   see the boundary of is an input they do not know they can change. */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{
    background: {SURFACE_HI};
    border-color: {BORDER};
    border-radius: {R_SM};
    transition: border-color {DUR_BASE} {EASE}, background {DUR_BASE} {EASE};
}}
div[data-baseweb="select"] > div:hover, div[data-baseweb="input"] > div:hover {{
    border-color: {ACCENT};
}}

/* One press grammar for every control, not just the tabs: buttons, the download
   and fullscreen icons on a dataframe, and the multiselect's remove chips. */
div.stButton > button, div.stDownloadButton > button,
button[data-testid="stBaseButton-elementToolbar"],
span[data-baseweb="tag"] {{
    transition: transform {DUR_FAST} {EASE}, background {DUR_BASE} {EASE},
                border-color {DUR_BASE} {EASE};
}}
div.stButton > button:active, div.stDownloadButton > button:active,
button[data-testid="stBaseButton-elementToolbar"]:active,
span[data-baseweb="tag"]:active {{
    transform: scale(0.96);
}}

/* The slider handle grows slightly under the cursor and settles back on release -
   the same acknowledgement the pills give, on the app's one global control. */
div[data-testid="stSlider"] div[role="slider"] {{
    transition: transform {DUR_BASE} {EASE};
}}
div[data-testid="stSlider"] div[role="slider"]:hover {{ transform: scale(1.15); }}
div[data-testid="stSlider"] div[role="slider"]:active {{ transform: scale(0.95); }}

html {{ scroll-behavior: smooth; }}

/* Motion is a preference, not a decision this app gets to make for the reader.
   Everything above degrades to an instant state change rather than disappearing,
   so the affordances survive with the animation switched off. */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }}
    button[data-baseweb="tab"]:hover,
    button[data-baseweb="tab"]:active,
    div.stButton > button:active,
    div[data-testid="stSlider"] div[role="slider"]:hover,
    div[data-testid="stSlider"] div[role="slider"]:active {{
        transform: none !important;
    }}
}}
label p {{ color: {TEXT_MUTED}; font-weight: 400; }}

/* The ladder is 300/400/600/700 - weight 500 is deliberately absent, and the
   mid-weights Streamlit reaches for by default are most of what made this app
   read as generic-product rather than designed. Pinned here so a widget Streamlit
   ships next year does not quietly reintroduce one. */
button, input, select, textarea, div[data-baseweb] {{ font-weight: 400; }}
h1, h2, h3, h4 {{ letter-spacing: {TRACK_TITLE}; font-weight: 600; }}

/* The stat grid is four columns of label-plus-value on a laptop. Four does not
   fit a phone: the label wraps to two lines and the fourth column's VALUE is
   pushed outside the panel, so "Max drawdown" and "Calendar" appeared with no
   number beside them. Step down to two columns, then one, rather than letting a
   fixed count overflow. `!important` because the column count is written inline
   by `stat_grid(cols=...)`. */
@media (max-width: 900px) {{
    .statgrid {{ grid-template-columns: repeat(2, 1fr) !important;
                 column-gap: 18px !important; }}
}}
@media (max-width: 520px) {{
    .statgrid {{ grid-template-columns: 1fr !important; }}
}}

/* A quote header's value, change and percent sit on one baseline. On a narrow
   screen let them wrap instead of pushing the percent off the edge. */
@media (max-width: 520px) {{
    .quotehead {{ flex-wrap: wrap; row-gap: 2px; }}
}}
</style>
"""


def status_banner(ok: bool, headline: str, detail: str = "") -> str:
    """A connection-status strip with colours set here rather than derived.

    Streamlit's own `st.success`/`st.warning` tint themselves from the theme's
    green and red, and once those were lightened for legibility the derived text
    contrast collapsed - the box rendered as a coloured rectangle with an
    unreadable message inside it. Everything else in this app already draws its
    own panels, so this does too: explicit foreground, explicit background, no
    contrast algorithm in the loop.
    """
    col = GREEN if ok else AMBER
    dot = "●" if ok else "▲"
    detail_html = (f"<div style='color:{TEXT_MUTED};font-size:0.8rem;"
                   f"margin-top:4px'>{detail}</div>") if detail else ""
    return (
        f"<div style='background:{SURFACE};border-left:3px solid {col};"
        f"border-radius:{R_MD};padding:11px 15px'>"
        f"<div style='display:flex;align-items:center;gap:9px'>"
        f"<span style='color:{col};font-size:0.85rem'>{dot}</span>"
        f"<span style='color:{TEXT};font-size:0.88rem;font-weight:600;"
        f"font-variant-numeric:tabular-nums'>{headline}</span></div>"
        f"{detail_html}</div>")


def note(text: str) -> str:
    """A neutral inline message - the empty state, drawn like everything else.

    Same reasoning as `status_banner`: `st.info` tints itself from the theme's
    blue and derives its own text contrast, and this app lightened that blue for
    legibility. Rather than trust a contrast pairing nobody checked, set both
    colours here.
    """
    return (f"<div style='background:{SURFACE};border-left:3px solid {ACCENT};"
            f"border-radius:{R_MD};padding:11px 15px;color:{TEXT};"
            f"font-size:0.88rem'>{text}</div>")


# A `nav_hint()` helper used to print "Choose a section" above the tab strip. It
# was scaffolding for a tab strip that did not look clickable; the pills do that
# job now, and labelling your own navigation is the kind of instruction a good
# system never needs. Removed rather than left unused.


def quote_header(name: str, value: str, change: str, pct: str, up: bool,
                 sub: str = "") -> str:
    """The terminal quote block: big value, then arrow + change + percent.

    Mirrors how a price header reads - the number first, its direction second,
    context third - so a reader who knows trading apps needs no orientation.
    """
    col = GREEN if up else RED
    arrow = "▲" if up else "▼"
    sub_html = (f"<div style='color:{TEXT_DIM};font-size:0.76rem;margin-top:3px'>"
                f"{sub}</div>") if sub else ""
    return (
        f"<div style='background:{SURFACE};border-radius:{R_MD};"
        f"padding:13px 16px'>"
        f"<div style='color:{TEXT_MUTED};font-size:0.8rem;font-weight:400'>{name}</div>"
        f"<div class='quotehead' style='display:flex;align-items:baseline;"
        f"gap:10px;margin-top:2px'>"
        f"<span style='font-family:{DISPLAY_STACK};font-size:2rem;font-weight:600;"
        f"letter-spacing:{TRACK_DISPLAY};color:{col};"
        f"font-variant-numeric:tabular-nums;line-height:1.1'>{value}</span>"
        f"<span style='color:{col};font-size:0.95rem;font-weight:600'>"
        f"{arrow} {change}</span>"
        f"<span style='color:{col};font-size:0.95rem;font-weight:600'>{pct}</span>"
        f"</div>{sub_html}</div>")


def stat_grid(pairs, cols: int = 2) -> str:
    """A label/value grid - the High/Low/Open/Prev-Close block.

    ``pairs`` is a sequence of (label, value, colour-or-None) tuples. Labels stay
    muted and values stay bright, so the grid reads at a glance without borders.
    """
    cells = []
    for label, value, col in pairs:
        cells.append(
            f"<div style='display:flex;justify-content:space-between;gap:12px;"
            f"padding:5px 0'>"
            f"<span style='color:{TEXT_MUTED};font-size:0.82rem'>{label}</span>"
            f"<span style='color:{col or TEXT};font-size:0.82rem;font-weight:600;"
            f"font-variant-numeric:tabular-nums'>{value}</span></div>")
    return (f"<div class='statgrid' style='background:{SURFACE};"
            f"border-radius:{R_MD};"
            f"padding:8px 14px;display:grid;"
            f"grid-template-columns:repeat({cols},1fr);"
            f"column-gap:26px'>{''.join(cells)}</div>")
