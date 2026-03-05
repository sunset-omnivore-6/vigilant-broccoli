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
import logging

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────

KWH_MCM = 10_972_000
MAX_SPAN_DAYS = 364

FACILITIES = [
    {"name": "Stublach",     "apiId": "PUBOBJ2370", "col": "rgb(59,130,246)"},
    {"name": "Rough",        "apiId": "PUBOBJ2366", "col": "rgb(245,158,11)"},
    {"name": "Aldbrough",    "apiId": "PUBOBJ2367", "col": "rgb(244,114,182)"},
    {"name": "Holford",      "apiId": "PUBOBJ2368", "col": "rgb(251,146,60)"},
    {"name": "Hornsea",      "apiId": "PUBOBJ2362", "col": "rgb(239,68,68)"},
    {"name": "Humbly Grove", "apiId": "PUBOBJ2361", "col": "rgb(167,139,250)"},
    {"name": "Hill Top",     "apiId": "PUBOBJ2369", "col": "rgb(52,211,153)"},
]

FAC_HEX = {
    "Stublach": "#3B82F6", "Rough": "#F59E0B", "Aldbrough": "#F472B6",
    "Holford": "#FB923C", "Hornsea": "#EF4444", "Humbly Grove": "#A78BFA",
    "Hill Top": "#34D399",
}

# Dark mode palette
BG       = "#0B0F19"
SURFACE  = "#131825"
SURFACE2 = "#1A2035"
BORDER   = "#252D44"
TEXT     = "#E2E8F0"
TEXT_DIM = "#7A8599"
ACCENT   = "#60A5FA"
GRID     = "#1E2640"


def match_facility(site_name):
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
def load_storage_data():
    json_path = Path(__file__).parent / "storage_data.json"
    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)
        latest = max((d for fac in data.values() for d in fac.keys()), default='2020-01-01')
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
                except Exception as e:
                    logger.warning("Failed to write storage cache: %s", e)
        return data
    data = fetch_from_api(date.today() - timedelta(days=1826), date.today())
    return data if data else {f["name"]: {} for f in FACILITIES}


def fetch_from_api(from_date, to_date):
    ids = ','.join(f["apiId"] for f in FACILITIES)
    all_data = {f["name"]: {} for f in FACILITIES}
    total_new = 0
    start = from_date
    while start < to_date:
        end = min(start + timedelta(days=MAX_SPAN_DAYS), to_date)
        url = ("https://data.nationalgas.com/api/find-gas-data-download"
               "?applicableFor=Y&dateFrom=" + start.isoformat() +
               "&dateTo=" + end.isoformat() +
               "&dateType=GASDAY&latestFlag=Y&ids=" + ids + "&type=CSV")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            if resp.text.strip():
                df = pd.read_csv(StringIO(resp.text))
                df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                date_col = next((c for c in df.columns if 'applicable' in c), None)
                item_col = next((c for c in df.columns if 'item' in c), None)
                val_col = next((c for c in df.columns if c == 'value'), None)
                if date_col and val_col:
                    for _, row in df.iterrows():
                        item_str = str(row.get(item_col, '')) if item_col else ''
                        fac = match_facility(item_str)
                        if not fac: continue
                        dt_raw = str(row[date_col]).strip()
                        try:
                            if '/' in dt_raw:
                                p = dt_raw.split('/')
                                dt_str = p[2][:4] + '-' + p[1].zfill(2) + '-' + p[0].zfill(2)
                            else:
                                dt_str = dt_raw[:10]
                        except Exception: continue
                        try: mcm = round(float(row[val_col]) / KWH_MCM, 4)
                        except (ValueError, TypeError): continue
                        all_data[fac][dt_str] = mcm
                        total_new += 1
        except (requests.RequestException, pd.errors.ParserError, ValueError) as e:
            logger.warning("Failed to fetch storage data chunk %s–%s: %s", start, end, e)
        start = end + timedelta(days=1)
    return all_data if total_new > 0 else None


# ── Calculations ────────────────────────────────────────────────────────────

def calculate_bounds(data):
    latest = max((d for fac in data.values() for d in fac.keys()), default='2020-01-01')
    latest_dt = date.fromisoformat(latest)
    bounds_from = latest_dt.replace(year=latest_dt.year - 5).isoformat()
    bounds = {}
    for fac_info in FACILITIES:
        name = fac_info["name"]
        vals = [v for dt, v in data.get(name, {}).items() if bounds_from <= dt <= latest]
        if not vals:
            bounds[name] = {"min": 0, "max": 0, "wv": 0, "cur": 0}
            continue
        mn, mx = min(vals), max(vals)
        cur = data[name].get(latest, 0)
        bounds[name] = {"min": mn, "max": mx, "wv": mx - mn, "cur": cur}
    return bounds, bounds_from, latest


def get_chart_data(data, from_date, to_date):
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
    ordered = sorted(FACILITIES, key=lambda f: bounds[f["name"]]["wv"], reverse=True)
    fig = go.Figure()
    for fac in ordered:
        name = fac["name"]
        b = bounds[name]
        vals = series[name]
        if b["wv"] == 0: continue
        if chart_type == "stock":
            y = [max(v - b["min"], 0) if v is not None else 0 for v in vals]
        else:
            y = [max(b["max"] - v, 0) if v is not None else 0 for v in vals]
        if all(v == 0 for v in y): continue
        fig.add_trace(go.Scatter(
            x=dates, y=y, mode='lines', name=name,
            line=dict(width=0.5, color=fac["col"]),
            stackgroup='one',
            hovertemplate="<b>" + name + ":</b> %{y:.1f} mcm<extra></extra>"
        ))
    if chart_type == "stock":
        title_text = "<b>Stock</b><br><sub>Usable gas: Actual minus 5yr Min, stacked by facility</sub>"
        y_title = "Stock (mcm above 5yr min)"
    else:
        title_text = "<b>Available Space</b><br><sub>Remaining capacity: 5yr Max minus Actual, stacked by facility</sub>"
        y_title = "Space (mcm below 5yr max)"
    fig.update_layout(
        title=dict(text=title_text, font=dict(size=16, color=TEXT)),
        plot_bgcolor=BG, paper_bgcolor=SURFACE,
        font=dict(color=TEXT, size=11), hovermode='x unified',
        height=450, margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(gridcolor=GRID, linecolor=BORDER, linewidth=1, showline=True,
                   tickformat='%b %y', tickfont=dict(color=TEXT_DIM, size=10)),
        yaxis=dict(title=dict(text=y_title, font=dict(color=TEXT_DIM, size=12)),
                   gridcolor=GRID, linecolor=BORDER, linewidth=1, showline=True,
                   rangemode='tozero', tickfont=dict(color=TEXT_DIM, size=11)),
        legend=dict(orientation='h', yanchor='bottom', y=-0.22, xanchor='center', x=0.5,
                    bgcolor=SURFACE, bordercolor=BORDER, borderwidth=1,
                    font=dict(size=11, color=TEXT_DIM))
    )
    return fig


# ── CSS ────────────────────────────────────────────────────────────────────

STORAGE_CSS = """
<style>
    .storage-section {
        background: #131825;
        border: 1px solid #252D44;
        border-radius: 10px;
        padding: 20px 22px;
        margin-bottom: 20px;
    }
    .storage-header {
        background: linear-gradient(135deg, #60A5FA, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .storage-sub {
        color: #7A8599;
        font-size: 13px;
        margin-bottom: 16px;
    }
    .storage-info {
        background: #1A2035;
        border: 1px solid #252D44;
        border-radius: 8px;
        padding: 10px 16px;
        margin: 8px 0 16px 0;
        font-size: 12px;
        color: #7A8599;
    }
    .storage-info strong {
        color: #60A5FA;
    }
    .storage-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        margin: 12px 0;
    }
    .storage-table th {
        text-align: left;
        padding: 8px 12px;
        color: #7A8599;
        font-weight: 500;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        border-bottom: 1px solid #252D44;
    }
    .storage-table td {
        padding: 9px 12px;
        border-bottom: 1px solid #252D44;
        font-family: monospace;
        font-size: 12px;
        color: #E2E8F0;
    }
    .storage-table tr:last-child td {
        border-bottom: none;
    }
    .storage-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 7px;
        vertical-align: middle;
    }
    .storage-fname {
        font-weight: 600;
        font-size: 13px;
    }
    .bounds-label {
        color: #7A8599;
        font-size: 12px;
        margin-bottom: 8px;
    }
</style>
"""


# ── Main render function ───────────────────────────────────────────────────

def render_gas_storage_tab():
    st.markdown(STORAGE_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="storage-header">UK Gas Storage</div>'
        '<div class="storage-sub">Opening stock levels by facility '
        '-- bounds from 5-year min/max -- all values in mcm</div>',
        unsafe_allow_html=True
    )

    with st.spinner("Loading storage data..."):
        data = load_storage_data()

    if not any(data.values()):
        st.error("No storage data available.")
        return

    # ── Preset buttons ──
    if "storage_preset" not in st.session_state:
        st.session_state.storage_preset = "1y"

    preset_options = {"90d": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1826, "10y": 3652}

    btn_cols = st.columns(len(preset_options))
    for i, (label, days) in enumerate(preset_options.items()):
        with btn_cols[i]:
            is_active = st.session_state.storage_preset == label
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key="stg_btn_" + label, use_container_width=True, type=btn_type):
                st.session_state.storage_preset = label
                st.session_state.storage_from = date.today() - timedelta(days=days)
                st.session_state.storage_to = date.today()
                st.rerun()

    with st.expander("Custom date range", expanded=False):
        c1, c2 = st.columns(2)
        default_days = preset_options.get(st.session_state.storage_preset, 365)
        with c1:
            chart_from = st.date_input("From",
                value=st.session_state.get("storage_from", date.today() - timedelta(days=default_days)),
                key="stg_date_from")
        with c2:
            chart_to = st.date_input("To",
                value=st.session_state.get("storage_to", date.today()),
                key="stg_date_to")
        if st.button("Apply", key="stg_apply"):
            st.session_state.storage_from = chart_from
            st.session_state.storage_to = chart_to
            st.session_state.storage_preset = None
            st.rerun()

    default_days = preset_options.get(st.session_state.storage_preset, 365)
    chart_from = st.session_state.get("storage_from", date.today() - timedelta(days=default_days))
    chart_to = st.session_state.get("storage_to", date.today())

    bounds, bounds_from, bounds_to = calculate_bounds(data)
    ordered = sorted(FACILITIES, key=lambda f: bounds[f["name"]]["wv"], reverse=True)

    st.markdown(
        '<div class="bounds-label">'
        'Working Volumes -- bounds: <strong style="color:#60A5FA">' + bounds_from + '</strong>'
        ' to <strong style="color:#60A5FA">' + bounds_to + '</strong></div>',
        unsafe_allow_html=True
    )

    rows_html = []
    for fac in ordered:
        b = bounds[fac["name"]]
        name = fac["name"]
        hex_col = FAC_HEX.get(name, "#888")
        fill_pct = str(round((b['cur'] - b['min']) / b['wv'] * 100, 1)) + "%" if b["wv"] > 0 else "n/a"
        rows_html.append(
            '<tr><td><span class="storage-dot" style="background:' + hex_col + '"></span>'
            '<span class="storage-fname">' + name + '</span></td>'
            '<td>' + str(round(b["min"], 1)) + '</td>'
            '<td>' + str(round(b["max"], 1)) + '</td>'
            '<td>' + str(round(b["wv"], 1)) + '</td>'
            '<td>' + str(round(b["cur"], 1)) + '</td>'
            '<td>' + fill_pct + '</td></tr>'
        )

    st.markdown(
        '<div class="storage-section">'
        '<table class="storage-table"><thead><tr>'
        '<th>Facility</th><th>5yr Min</th><th>5yr Max</th>'
        '<th>Working Vol</th><th>Latest</th><th>Fill %</th>'
        '</tr></thead><tbody>' + ''.join(rows_html) + '</tbody></table></div>',
        unsafe_allow_html=True
    )

    cf_str = chart_from.isoformat()
    ct_str = chart_to.isoformat()
    dates, series = get_chart_data(data, cf_str, ct_str)

    if not dates:
        st.warning("No data in selected range.")
        return

    st.markdown(
        '<div class="storage-info">'
        'Showing <strong>' + str(len(dates)) + '</strong> days '
        '(<strong>' + dates[0] + '</strong> to <strong>' + dates[-1] + '</strong>)</div>',
        unsafe_allow_html=True
    )

    fig_stock = create_stacked_area_chart(dates, series, bounds, "stock")
    st.plotly_chart(fig_stock, use_container_width=True, theme=None)

    fig_space = create_stacked_area_chart(dates, series, bounds, "space")
    st.plotly_chart(fig_space, use_container_width=True, theme=None)
