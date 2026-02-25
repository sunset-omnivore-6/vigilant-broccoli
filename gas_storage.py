"""
gas_storage.py
--------------
Gas Storage functions for the UK Energy Market Streamlit Dashboard.
Sub-view under the National Gas tab.

Place this file + storage_data.json alongside streamlit_app.py.
"""

import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
import json

# ── Config ──────────────────────────────────────────────────────────────────

KWH_MCM = 10_972_000
MAX_SPAN_DAYS = 364

FACILITIES = [
    {"name": "Stublach",     "apiId": "PUBOBJ2370", "col": "#3B82F6"},
    {"name": "Rough",        "apiId": "PUBOBJ2366", "col": "#F59E0B"},
    {"name": "Aldbrough",    "apiId": "PUBOBJ2367", "col": "#F472B6"},
    {"name": "Holford",      "apiId": "PUBOBJ2368", "col": "#FB923C"},
    {"name": "Hornsea",      "apiId": "PUBOBJ2362", "col": "#EF4444"},
    {"name": "Humbly Grove", "apiId": "PUBOBJ2361", "col": "#A78BFA"},
    {"name": "Hill Top",     "apiId": "PUBOBJ2369", "col": "#34D399"},
]

# Dark mode palette
BG       = "#0B0F19"
SURFACE  = "#131825"
SURFACE2 = "#1A2035"
BORDER   = "#252D44"
TEXT     = "#E2E8F0"
TEXT_DIM = "#7A8599"
ACCENT   = "#60A5FA"
GRID     = "#1E2640"


def match_facility(site_name: str) -> str | None:
    s = site_name.lower()
    if 'humbly' in s:    return 'Humbly Grove'
    if 'hill top' in s:  return 'Hill Top'
    if 'stublach' in s:  return 'Stublach'
    if 'aldbrough' in s: return 'Aldbrough'
    if 'holford' in s:   return 'Holford'
    if 'hornsea' in s or 'atwick' in s: return 'Hornsea'
    if 'rough' in s:     return 'Rough'
    return None


# ── Data loading ────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def load_storage_data() -> dict:
    """Load storage data from JSON, auto-update from API if stale."""
    json_path = Path(__file__).parent / "storage_data.json"

    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)

        latest = max(
            (d for fac in data.values() for d in fac.keys()),
            default='2020-01-01'
        )
        today = date.today().isoformat()

        if latest < today:
            new_data = fetch_from_api(date.fromisoformat(latest), date.today())
            if new_data:
                for fac in data:
                    if fac in new_data:
                        data[fac].update(new_data[fac])
                try:
                    with open(json_path, 'w') as f:
                        json.dump(data, f, separators=(',', ':'))
                except Exception:
                    pass

        return data

    data = fetch_from_api(date.today() - timedelta(days=1826), date.today())
    return data if data else {f["name"]: {} for f in FACILITIES}


def fetch_from_api(from_date: date, to_date: date) -> dict | None:
    """Fetch storage data from National Gas API."""
    ids = ','.join(f["apiId"] for f in FACILITIES)
    all_data = {f["name"]: {} for f in FACILITIES}
    total_new = 0

    start = from_date
    while start < to_date:
        end = min(start + timedelta(days=MAX_SPAN_DAYS), to_date)
        url = (
            f"https://data.nationalgas.com/api/find-gas-data-download"
            f"?applicableFor=Y&dateFrom={start.isoformat()}&dateTo={end.isoformat()}"
            f"&dateType=GASDAY&latestFlag=Y&ids={ids}&type=CSV"
        )
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            if resp.text.strip():
                df = pd.read_csv(StringIO(resp.text))
                df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                date_col = next((c for c in df.columns if 'applicable' in c), None)
                item_col = next((c for c in df.columns if 'item' in c), None)
                val_col  = next((c for c in df.columns if c == 'value'), None)
                if date_col and val_col:
                    for _, row in df.iterrows():
                        item_str = str(row.get(item_col, '')) if item_col else ''
                        fac = match_facility(item_str)
                        if not fac:
                            continue
                        dt_raw = str(row[date_col]).strip()
                        try:
                            if '/' in dt_raw:
                                p = dt_raw.split('/')
                                dt_str = f"{p[2][:4]}-{p[1].zfill(2)}-{p[0].zfill(2)}"
                            else:
                                dt_str = dt_raw[:10]
                        except Exception:
                            continue
                        try:
                            mcm = round(float(row[val_col]) / KWH_MCM, 4)
                        except (ValueError, TypeError):
                            continue
                        all_data[fac][dt_str] = mcm
                        total_new += 1
        except Exception:
            pass
        start = end + timedelta(days=1)

    return all_data if total_new > 0 else None


# ── Calculations ────────────────────────────────────────────────────────────

def calculate_bounds(data: dict) -> dict:
    """Calculate 5-year min/max bounds from latest date."""
    latest = max(
        (d for fac in data.values() for d in fac.keys()),
        default='2020-01-01'
    )
    latest_dt = date.fromisoformat(latest)
    bounds_from = latest_dt.replace(year=latest_dt.year - 5).isoformat()

    bounds = {}
    for fac_info in FACILITIES:
        name = fac_info["name"]
        vals = [v for dt, v in data.get(name, {}).items()
                if bounds_from <= dt <= latest]
        if not vals:
            bounds[name] = {"min": 0, "max": 0, "wv": 0, "cur": 0}
            continue
        mn, mx = min(vals), max(vals)
        cur = data[name].get(latest, 0)
        bounds[name] = {"min": mn, "max": mx, "wv": mx - mn, "cur": cur}

    return bounds, bounds_from, latest


def get_chart_data(data: dict, from_date: str, to_date: str) -> tuple:
    """Get date-aligned chart data for the specified range."""
    all_dates = set()
    for fac_info in FACILITIES:
        for dt in data.get(fac_info["name"], {}):
            if from_date <= dt <= to_date:
                all_dates.add(dt)

    dates = sorted(all_dates)
    series = {}
    for fac_info in FACILITIES:
        name = fac_info["name"]
        series[name] = [data.get(name, {}).get(dt) for dt in dates]

    return dates, series


# ── Plotly charts (dark mode) ──────────────────────────────────────────────

def create_stacked_area_chart(dates, series, bounds, chart_type="stock"):
    """Create a dark-mode stacked area chart for stock or space."""
    ordered = sorted(
        FACILITIES,
        key=lambda f: bounds[f["name"]]["wv"],
        reverse=True
    )

    fig = go.Figure()

    for fac in ordered:
        name = fac["name"]
        b = bounds[name]
        vals = series[name]

        # Skip facilities with zero working volume
        if b["wv"] == 0:
            continue

        # Replace None with 0 for stacking — Plotly can't stack with None
        if chart_type == "stock":
            y = [max(v - b["min"], 0) if v is not None else 0 for v in vals]
        else:
            y = [max(b["max"] - v, 0) if v is not None else 0 for v in vals]

        # Skip if all zeros
        if all(v == 0 for v in y):
            continue

        fig.add_trace(go.Scatter(
            x=dates, y=y,
            mode='lines',
            name=name,
            line=dict(width=0.5, color=fac["col"]),
            fillcolor=fac["col"] + "DD",
            stackgroup='one',
            hovertemplate=f"<b>{name}:</b> " + "%{y:.1f} mcm<extra></extra>"
        ))

    if chart_type == "stock":
        title_text = "<b>Stock</b><br><sub>Usable gas: Actual − 5yr Min, stacked by facility</sub>"
        y_title = "Stock (mcm above 5yr min)"
    else:
        title_text = "<b>Available Space</b><br><sub>Remaining capacity: 5yr Max − Actual, stacked by facility</sub>"
        y_title = "Space (mcm below 5yr max)"

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=16, color=TEXT)),
        plot_bgcolor=BG,
        paper_bgcolor=SURFACE,
        font=dict(color=TEXT, size=11),
        hovermode='x unified',
        height=450,
        margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(
            gridcolor=GRID, linecolor=BORDER, linewidth=1, showline=True,
            tickformat='%b %y',
            tickfont=dict(color=TEXT_DIM, size=10),
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(color=TEXT_DIM, size=12)),
            gridcolor=GRID, linecolor=BORDER, linewidth=1, showline=True,
            rangemode='tozero',
            tickfont=dict(color=TEXT_DIM, size=11),
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom', y=-0.22,
            xanchor='center', x=0.5,
            bgcolor=SURFACE, bordercolor=BORDER, borderwidth=1,
            font=dict(size=11, color=TEXT_DIM),
        )
    )

    return fig


# ── Custom CSS for dark storage section ────────────────────────────────────

STORAGE_CSS = f"""
<style>
    .storage-section {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 20px 22px;
        margin-bottom: 20px;
    }}
    .storage-header {{
        background: linear-gradient(135deg, {ACCENT}, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 4px;
    }}
    .storage-sub {{
        color: {TEXT_DIM};
        font-size: 13px;
        margin-bottom: 16px;
    }}
    .storage-info {{
        background: {SURFACE2};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 10px 16px;
        margin: 8px 0 16px 0;
        font-size: 12px;
        color: {TEXT_DIM};
    }}
    .storage-info strong {{
        color: {ACCENT};
    }}
    .storage-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        margin: 12px 0;
    }}
    .storage-table th {{
        text-align: left;
        padding: 8px 12px;
        color: {TEXT_DIM};
        font-weight: 500;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        border-bottom: 1px solid {BORDER};
    }}
    .storage-table td {{
        padding: 9px 12px;
        border-bottom: 1px solid {BORDER};
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: {TEXT};
    }}
    .storage-table tr:last-child td {{
        border-bottom: none;
    }}
    .storage-dot {{
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 7px;
        vertical-align: middle;
    }}
    .storage-fname {{
        font-weight: 600;
        font-size: 13px;
    }}
    .bounds-label {{
        color: {TEXT_DIM};
        font-size: 12px;
        margin-bottom: 8px;
    }}
</style>
"""


# ── Main render function ───────────────────────────────────────────────────

def render_gas_storage_tab():
    """Render the Gas Storage sub-view with dark mode theme."""

    st.markdown(STORAGE_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="storage-header">UK Gas Storage</div>'
        '<div class="storage-sub">Opening stock levels by facility — '
        'bounds from 5-year min/max — all values in mcm</div>',
        unsafe_allow_html=True
    )

    # Load data
    with st.spinner("Loading storage data..."):
        data = load_storage_data()

    if not any(data.values()):
        st.error("⚠️ No storage data available. Check API connectivity.")
        return

    # ── Preset buttons ──
    if "storage_preset" not in st.session_state:
        st.session_state.storage_preset = "1y"

    preset_options = {
        "90d": 90, "6m": 180, "1y": 365,
        "2y": 730, "5y": 1826, "10y": 3652
    }

    btn_cols = st.columns(len(preset_options))
    for i, (label, days) in enumerate(preset_options.items()):
        with btn_cols[i]:
            if st.button(
                label,
                key=f"storage_btn_{label}",
                use_container_width=True,
                type="primary" if st.session_state.storage_preset == label else "secondary",
            ):
                st.session_state.storage_preset = label
                st.session_state.storage_from = date.today() - timedelta(days=days)
                st.session_state.storage_to = date.today()
                st.rerun()

    # Custom date range in expander
    with st.expander("Custom date range", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            chart_from = st.date_input(
                "From",
                value=st.session_state.get(
                    "storage_from",
                    date.today() - timedelta(days=preset_options[st.session_state.storage_preset])
                ),
                key="storage_date_from"
            )
        with c2:
            chart_to = st.date_input(
                "To",
                value=st.session_state.get("storage_to", date.today()),
                key="storage_date_to"
            )
        if st.button("Apply", key="storage_apply_custom"):
            st.session_state.storage_from = chart_from
            st.session_state.storage_to = chart_to
            st.session_state.storage_preset = None  # deselect presets
            st.rerun()

    # Resolve final dates
    chart_from = st.session_state.get(
        "storage_from",
        date.today() - timedelta(days=preset_options.get(st.session_state.storage_preset, 365))
    )
    chart_to = st.session_state.get("storage_to", date.today())

    # Calculate bounds
    bounds, bounds_from, bounds_to = calculate_bounds(data)

    # ── Bounds table ──
    ordered = sorted(FACILITIES, key=lambda f: bounds[f["name"]]["wv"], reverse=True)

    st.markdown(
        f'<div class="bounds-label">'
        f'Working Volumes — bounds: <strong style="color:{ACCENT}">{bounds_from}</strong>'
        f' → <strong style="color:{ACCENT}">{bounds_to}</strong></div>',
        unsafe_allow_html=True
    )

    rows_html = []
    for fac in ordered:
        b = bounds[fac["name"]]
        fill_pct = f"{(b['cur'] - b['min']) / b['wv'] * 100:.1f}%" if b["wv"] > 0 else "—"
        rows_html.append(
            f'<tr>'
            f'<td><span class="storage-dot" style="background:{fac["col"]}"></span>'
            f'<span class="storage-fname">{fac["name"]}</span></td>'
            f'<td>{b["min"]:.1f}</td><td>{b["max"]:.1f}</td>'
            f'<td>{b["wv"]:.1f}</td><td>{b["cur"]:.1f}</td>'
            f'<td>{fill_pct}</td></tr>'
        )

    st.markdown(
        f'<div class="storage-section">'
        f'<table class="storage-table"><thead><tr>'
        f'<th>Facility</th><th>5yr Min</th><th>5yr Max</th>'
        f'<th>Working Vol</th><th>Latest</th><th>Fill %</th>'
        f'</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True
    )

    # ── Chart data ──
    cf_str = chart_from.isoformat()
    ct_str = chart_to.isoformat()
    dates, series = get_chart_data(data, cf_str, ct_str)

    if not dates:
        st.warning("No data in selected range.")
        return

    st.markdown(
        f'<div class="storage-info">'
        f'Showing <strong>{len(dates)}</strong> days '
        f'(<strong>{dates[0]}</strong> → <strong>{dates[-1]}</strong>)</div>',
        unsafe_allow_html=True
    )

    # ── Charts ──
    fig_stock = create_stacked_area_chart(dates, series, bounds, "stock")
    st.plotly_chart(fig_stock, use_container_width=True, theme=None)

    fig_space = create_stacked_area_chart(dates, series, bounds, "space")
    st.plotly_chart(fig_space, use_container_width=True, theme=None)
