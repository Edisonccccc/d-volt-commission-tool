"""Shared CSS injection and HTML component helpers."""
import os
import streamlit as st

# ── Brand palette ──────────────────────────────────────────────────────────────
GREEN       = "#16A34A"   # primary green
GREEN_DARK  = "#15803D"   # hover
GREEN_LIGHT = "#DCFCE7"   # light tint (badges, highlights)
GREEN_TEXT  = "#14532D"   # dark green for text on light bg
BG_MAIN     = "#F8FAFC"   # page background (neutral light gray)
BG_CARD     = "#FFFFFF"
BORDER      = "#D1FAE5"   # subtle green border
BORDER_GRAY = "#E5E7EB"
TEXT_DARK   = "#1A1A1A"
TEXT_MID    = "#6B7280"
TEXT_LIGHT  = "#9CA3AF"


def inject_css():
    st.markdown(f"""
    <style>
    /* ── Layout ─────────────────────────────────────────────────────── */
    .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1100px !important;
    }}

    /* ── Tabs ────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: {BG_CARD};
        border-radius: 10px;
        padding: 4px;
        border: 1px solid {BORDER_GRAY};
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 7px;
        padding: 8px 28px;
        font-weight: 600;
        font-size: 0.88rem;
        color: {TEXT_MID};
        background: transparent;
        border: none;
    }}
    .stTabs [aria-selected="true"] {{
        background: {GREEN} !important;
        color: white !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
    .stTabs [data-baseweb="tab-border"] {{ display: none; }}

    /* ── Metrics ─────────────────────────────────────────────────────── */
    [data-testid="metric-container"] {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 1.1rem 1.4rem !important;
        box-shadow: 0 1px 3px rgba(22,163,74,0.06);
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        color: {TEXT_DARK} !important;
    }}
    [data-testid="stMetricLabel"] > div {{
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        color: {TEXT_LIGHT} !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    /* ── Buttons ─────────────────────────────────────────────────────── */
    .stButton > button {{
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 0.4rem 1rem !important;
        transition: all 0.15s ease !important;
    }}
    [data-testid="baseButton-primary"] {{
        background: {GREEN} !important;
        border: none !important;
        color: white !important;
    }}
    [data-testid="baseButton-primary"]:hover {{
        background: {GREEN_DARK} !important;
        box-shadow: 0 4px 14px rgba(22,163,74,0.35) !important;
        transform: translateY(-1px);
    }}
    [data-testid="baseButton-secondary"] {{
        background: {BG_CARD} !important;
        border: 1px solid {BORDER_GRAY} !important;
        color: {TEXT_MID} !important;
    }}
    [data-testid="baseButton-secondary"]:hover {{
        border-color: {GREEN} !important;
        color: {GREEN} !important;
        background: {GREEN_LIGHT} !important;
    }}

    /* ── Expanders ───────────────────────────────────────────────────── */
    .stExpander {{
        background: {BG_CARD} !important;
        border: 1px solid {BORDER_GRAY} !important;
        border-radius: 10px !important;
        margin-bottom: 6px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }}
    .stExpander > details > summary {{
        padding: 0.75rem 1rem !important;
        font-weight: 500 !important;
        border-radius: 10px !important;
    }}
    .stExpander > details > summary:hover {{
        background: {GREEN_LIGHT} !important;
    }}

    /* ── Forms ───────────────────────────────────────────────────────── */
    [data-testid="stForm"] {{
        background: {BG_MAIN} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 12px !important;
        padding: 1.25rem 1.5rem !important;
    }}

    /* ── Inputs ──────────────────────────────────────────────────────── */
    input[type="text"], input[type="number"] {{
        border-radius: 8px !important;
        border: 1px solid {BORDER_GRAY} !important;
        font-size: 0.9rem !important;
    }}
    input[type="text"]:focus, input[type="number"]:focus {{
        border-color: {GREEN} !important;
        box-shadow: 0 0 0 3px rgba(22,163,74,0.12) !important;
    }}

    /* ── Dataframe ───────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }}

    /* ── Divider ─────────────────────────────────────────────────────── */
    hr {{ border-color: {BORDER_GRAY} !important; margin: 1.25rem 0 !important; }}

    /* ── Alerts ──────────────────────────────────────────────────────── */
    [data-testid="stAlert"] {{ border-radius: 10px !important; }}

    /* ── Selectbox ───────────────────────────────────────────────────── */
    [data-testid="stSelectbox"] > div > div {{
        border-radius: 8px !important;
        border: 1px solid {BORDER_GRAY} !important;
    }}

    /* ── Hide sidebar ────────────────────────────────────────────────── */
    [data-testid="collapsedControl"] {{ display: none; }}
    section[data-testid="stSidebar"] {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    sub_html = f'<div style="color:#86EFAC;font-size:0.85rem;margin-top:2px;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #14532D 0%, {GREEN} 100%);
        padding: 1rem 1.75rem;
        border-radius: 12px;
        margin-bottom: 1.25rem;
    ">
        <div style="color:white;font-size:1.3rem;font-weight:700;letter-spacing:-0.02em;">{title}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def project_card_html(customer: str, project_no: str, description: str,
                      contract: float, collected: float, num_employees: int) -> str:
    pct = min((collected / contract * 100) if contract else 0, 100)
    bar_color = GREEN if pct < 100 else "#15803D"
    emp_badge = (
        f'<span style="background:{GREEN_LIGHT};color:{GREEN_TEXT};'
        f'padding:2px 10px;border-radius:20px;font-size:0.72rem;font-weight:600;">'
        f'{num_employees} employee{"s" if num_employees != 1 else ""}</span>'
    )
    desc_html = f'<div style="color:{TEXT_LIGHT};font-size:0.78rem;margin-bottom:2px;">{description}</div>' if description else ""
    return f"""
    <div style="padding: 2px 0 8px 0;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
            <div>
                <div style="font-size:1.05rem;font-weight:700;color:{TEXT_DARK};line-height:1.3;">{customer}</div>
                <div style="color:{TEXT_MID};font-size:0.8rem;">{project_no}</div>
                {desc_html}
            </div>
            {emp_badge}
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:{TEXT_LIGHT};margin-bottom:3px;">
            <span>Collected  <b style="color:{TEXT_DARK};">${collected:,.0f}</b></span>
            <b style="color:{bar_color};">{pct:.1f}%</b>
        </div>
        <div style="background:#D1FAE5;border-radius:9999px;height:5px;margin-bottom:4px;">
            <div style="background:{bar_color};border-radius:9999px;height:5px;width:{pct:.1f}%;"></div>
        </div>
        <div style="font-size:0.75rem;color:{TEXT_LIGHT};">of ${contract:,.0f} contract</div>
    </div>
    """


_AVATAR_DIR = os.path.join(os.path.dirname(__file__), "assets", "avatars")

_FEMALE_FILES = [
    "Aria","Luna","Stella","Chloe","Emma","Lily","Zoe","Mia","Sofia","Ava",
    "Nora","Isla","Ruby","Violet","Hazel","Aurora","Ellie","Ivy","Jade","Rose",
    "Layla","Freya","Nova","Willow","Scarlett","Penelope","Clara","Grace","Piper","Maya",
    "Elara","Cora","Wren","Skye","Sienna","Nina","Lena","Elsie","Fiona","Alma",
]
_MALE_FILES = [
    "Liam","Noah","Ethan","Oliver","Lucas","Mason","Logan","Aiden","Jack","Owen",
    "Finn","Leo","Theo","Milo","Hugo","Eli","Zane","Cole","Reid","Beau",
    "Axel","Blake","Caden","Dax","Ezra","Flynn","Gage","Huck","Ivan","Jace",
    "Knox","Lane","Max","Nate","Otto","Penn","Rex","Seth","Tate","Wade",
]
_OTHER_FILES = [
    "Alex","River","Quinn","Sage","Avery","Casey","Drew","Emery","Finley","Gray",
    "Harley","Jamie","Jordan","Kai","Robin","Morgan","Parker","Reese","Skyler","Taylor",
]

# Cache SVG content in memory after first load
_avatar_cache: dict = {}


def employee_avatar(emp_name: str, size: int = 36, gender: str = None) -> str:
    """Offline cartoon avatar loaded from assets/avatars/, gender-aware."""
    idx = sum(ord(c) for c in emp_name)
    if gender == "female":
        seed = _FEMALE_FILES[idx % len(_FEMALE_FILES)]
    elif gender == "male":
        seed = _MALE_FILES[idx % len(_MALE_FILES)]
    else:
        seed = _OTHER_FILES[idx % len(_OTHER_FILES)]

    key = f"{gender or 'other'}_{seed}"
    if key not in _avatar_cache:
        path = os.path.join(_AVATAR_DIR, f"{gender or 'other'}_{seed}.svg")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _avatar_cache[key] = f.read()
        except FileNotFoundError:
            initials = "".join(p[0].upper() for p in emp_name.split()[:2])
            return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
                    f'background:{GREEN_LIGHT};color:{GREEN_TEXT};display:inline-flex;'
                    f'align-items:center;justify-content:center;font-weight:700;'
                    f'font-size:{size//3}px;flex-shrink:0;">{initials}</div>')

    svg = _avatar_cache[key]
    # Inject width/height so the SVG fills the container exactly
    svg = svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;overflow:hidden;'
        f'flex-shrink:0;display:inline-block;">{svg}</div>'
    )


def avatar(name: str, size: int = 36, bg: str = GREEN_LIGHT, fg: str = GREEN_TEXT) -> str:
    initials = "".join(p[0].upper() for p in name.split()[:2])
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{bg};color:{fg};'
        f'display:inline-flex;align-items:center;justify-content:center;'
        f'font-weight:700;font-size:{size//2.5:.0f}px;flex-shrink:0;">{initials}</div>'
    )


def dist_bar(assignments: list) -> str:
    if not assignments:
        return ""
    colors = [GREEN, "#F59E0B", "#3B82F6", "#EF4444", "#8B5CF6", "#EC4899"]
    segments = "".join(
        f'<div title="{n}: {p:.1f}%" style="background:{colors[i%len(colors)]};height:100%;width:{p:.1f}%;"></div>'
        for i, (n, p) in enumerate(assignments)
    )
    legend = "  ".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;color:{TEXT_MID};">'
        f'<span style="width:10px;height:10px;border-radius:2px;background:{colors[i%len(colors)]};display:inline-block;"></span>'
        f'{n} {p:.1f}%</span>'
        for i, (n, p) in enumerate(assignments)
    )
    return f"""
    <div style="background:#D1FAE5;border-radius:6px;height:10px;overflow:hidden;display:flex;margin-bottom:6px;">
        {segments}
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:8px;">{legend}</div>
    """


def section_title(text: str):
    st.markdown(
        f'<div style="font-size:0.7rem;font-weight:700;color:{TEXT_LIGHT};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">{text}</div>',
        unsafe_allow_html=True,
    )


def badge(text: str, color: str = "green") -> str:
    palettes = {
        "green":  (GREEN_LIGHT, GREEN_TEXT),
        "blue":   ("#DBEAFE", "#1D4ED8"),
        "orange": ("#FEF3C7", "#92400E"),
        "red":    ("#FEE2E2", "#991B1B"),
        "gray":   ("#F3F4F6", "#374151"),
    }
    bg, fg = palettes.get(color, palettes["gray"])
    return f'<span style="background:{bg};color:{fg};padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;">{text}</span>'
