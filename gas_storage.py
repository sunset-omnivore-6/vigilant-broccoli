"""
gas_storage.py
--------------
Gas Storage functions for the UK Energy Market Streamlit Dashboard.
Add this as a sub-view under the National Gas tab.

Integration:
  1. Copy this file alongside your main dashboard script
  2. Add `from gas_storage import render_gas_storage_tab` at the top
  3. In the National Gas tab, add "Gas Storage" to the radio options
  4. Call render_gas_storage_tab() when that view is selected
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

EXCLUDE_SITES = ['holehouse', 'avonmouth']


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

@st.cache_data(ttl=86400)  # Cache for 24 hours — data updates daily
def load_storage_data() -> dict:
    """
    Load storage data. Tries to read from embedded JSON file first,
    then falls back to API fetch for last 5 years.
    """
    json_path = Path(__file__).parent / "storage_data.json"

    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)

        # Check if we need to update
        latest = max(d for fac in data.values() for d in fac.keys())
        today = date.today().isoformat()

        if latest < today:
            # Fetch new data since latest
            new_data = fetch_from_api(date.fromisoformat(latest), date.today())
            if new_data:
                for fac in data:
                    if fac in new_data:
                        data[fac].update(new_data[fac])
                # Save updated data
                try:
                    with open(json_path, 'w') as f:
                        json.dump(data, f, separators=(',', ':'))
                except Exception:
                    pass  # Read-only filesystem, no problem

        return data

    # No JSON file — fetch from API (last 5 years)
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
    latest = max((d for fac in data.values() for d in fac.keys()), default='2020-01-01')
    latest_dt = date.fromisoformat(latest)
    bounds_from = (latest_dt.replace(year=latest_dt.year - 5)).isoformat()

    bounds = {}
    for fac_info in FACILITIES:
        name = fac_info["name"]
        vals = [v for dt, v in data.get(name, {}).items() if dt >= bounds_from and dt <= latest]
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


# ── Plotly charts ───────────────────────────────────────────────────────────

def create_stacked_area_chart(dates, series, bounds, chart_type="stock"):
    """Create a stacked area chart for stock or space."""
    ordered = sorted(FACILITIES, key=lambda f: bounds[f["name"]]["wv"], reverse=True)

    fig = go.Figure()

    for fac in ordered:
        name = fac["name"]
        b = bounds[name]
        vals = series[name]

        if chart_type == "stock":
            y = [max(v - b["min"], 0) if v is not None else None for v in vals]
            title_text = "<b>Stock</b><br><sub>Usable gas: Actual − 5yr Min, stacked by facility</sub>"
            y_title = "Stock (mcm above 5yr min)"
        else:
            y = [max(b["max"] - v, 0) if v is not None else None for v in vals]
            title_text = "<b>Available Space</b><br><sub>Remaining capacity: 5yr Max − Actual, stacked by facility</sub>"
            y_title = "Space (mcm below 5yr max)"

        fig.add_trace(go.Scatter(
            x=dates, y=y,
            mode='lines',
            name=name,
            line=dict(width=0.5, color=fac["col"]),
            fillcolor=fac["col"] + "DD",
            stackgroup='one',
            hovertemplate=f"<b>{name}:</b> " + "%{y:.1f} mcm<extra></extra>"
        ))

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=16, color='#1e293b')),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(color='#1e293b', size=11),
        hovermode='x unified',
        height=450,
        margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(
            gridcolor='#e2e8f0', linecolor='#1e293b', linewidth=2, showline=True,
            tickformat='%b %y',
        ),
        yaxis=dict(
            title=y_title,
            gridcolor='#e2e8f0', linecolor='#1e293b', linewidth=2, showline=True,
            rangemode='tozero'
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5,
            bgcolor='rgba(255,255,255,0.95)', bordercolor='#1e293b', borderwidth=1,
            font=dict(size=11)
        )
    )

    return fig


# ── Main render function ───────────────────────────────────────────────────

def render_gas_storage_tab():
    """Render the Gas Storage sub-view. Call this from the main dashboard."""

    st.markdown(
        '<div class="section-header">UK Gas Storage — Stock & Space</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="info-box">'
        '<strong>Gas Storage Dashboard</strong> — Opening stock levels for UK storage '
        'facilities (Stublach, Rough, Aldbrough, Holford, Hornsea, Humbly Grove, Hill Top). '
        'Bounds are calculated from the 5-year min/max. All values in mcm.</div>',
        unsafe_allow_html=True
    )

    # Load data
    with st.spinner("Loading storage data..."):
        data = load_storage_data()

    if not any(data.values()):
        st.error("⚠️ No storage data available. Check API connectivity.")
        return

    # Date range controls
    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        chart_from = st.date_input(
            "Chart From",
            value=date.today() - timedelta(days=365),
            key="storage_from"
        )
    with col2:
        chart_to = st.date_input(
            "Chart To",
            value=date.today(),
            key="storage_to"
        )
    with col3:
        preset = st.radio(
            "Quick Range",
            ["90d", "6m", "1y", "2y", "5y", "10y"],
            horizontal=True,
            index=2,
            key="storage_preset",
            label_visibility="collapsed"
        )
        preset_days = {"90d": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1826, "10y": 3652}
        # Note: preset selection updates on rerun

    # Calculate bounds
    bounds, bounds_from, bounds_to = calculate_bounds(data)

    # Bounds table
    st.markdown(
        f"**Working Volumes** — bounds: {bounds_from} → {bounds_to}"
    )

    ordered = sorted(FACILITIES, key=lambda f: bounds[f["name"]]["wv"], reverse=True)
    table_data = []
    for fac in ordered:
        b = bounds[fac["name"]]
        fill_pct = ((b["cur"] - b["min"]) / b["wv"] * 100) if b["wv"] > 0 else 0
        table_data.append({
            "Facility": fac["name"],
            "5yr Min": round(b["min"], 1),
            "5yr Max": round(b["max"], 1),
            "Working Vol": round(b["wv"], 1),
            "Latest": round(b["cur"], 1),
            "Fill %": f"{fill_pct:.1f}%"
        })

    st.dataframe(
        pd.DataFrame(table_data),
        use_container_width=True,
        hide_index=True,
        column_config={
            "5yr Min": st.column_config.NumberColumn(format="%.1f"),
            "5yr Max": st.column_config.NumberColumn(format="%.1f"),
            "Working Vol": st.column_config.NumberColumn(format="%.1f"),
            "Latest": st.column_config.NumberColumn(format="%.1f"),
        }
    )

    # Get chart data
    cf_str = chart_from.isoformat()
    ct_str = chart_to.isoformat()
    dates, series = get_chart_data(data, cf_str, ct_str)

    if not dates:
        st.warning("No data in selected range.")
        return

    st.markdown(
        f'<div class="info-box">Showing <strong>{len(dates)}</strong> days '
        f'({dates[0]} → {dates[-1]})</div>',
        unsafe_allow_html=True
    )

    # Stock chart
    fig_stock = create_stacked_area_chart(dates, series, bounds, "stock")
    st.plotly_chart(fig_stock, use_container_width=True, theme=None)

    # Space chart
    fig_space = create_stacked_area_chart(dates, series, bounds, "space")
    st.plotly_chart(fig_space, use_container_width=True, theme=None)
