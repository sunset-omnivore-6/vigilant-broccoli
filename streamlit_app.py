# update: 25/02/2026 — dark mode + button-style navigation

import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import time
import html
from gas_storage import render_gas_storage_tab

st.set_page_config(
    page_title="UK Energy Market Dashboard",
    page_icon="\U0001f534",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Dark mode CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    .css-1d391kg { display: none !important; }

    .stApp { background-color: #0B0F19 !important; }
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1600px; }

    .header-bar {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        padding: 1rem 2rem; border-radius: 8px; margin: -1rem -1rem 1rem -1rem;
        display: flex; justify-content: space-between; align-items: center;
    }
    .header-bar h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: white !important; }
    .header-bar .subtitle { font-size: 0.85rem; color: rgba(255,255,255,0.7); margin-top: 0.2rem; }
    .header-time { text-align: right; color: rgba(255,255,255,0.85); font-size: 0.85rem; }
    .header-time strong { font-size: 1.1rem; color: white; }

    .stTabs [data-baseweb="tab-list"] { gap: 0; background-color: #131825; padding: 0; border-radius: 8px; border: 1px solid #252D44; }
    .stTabs [data-baseweb="tab"] { height: 48px; padding: 0 28px; background-color: transparent; border-radius: 0; border: none; border-right: 1px solid #252D44; font-weight: 500; font-size: 0.95rem; color: #7A8599; }
    .stTabs [data-baseweb="tab"]:hover { background-color: #1A2035; color: #E2E8F0; }
    .stTabs [aria-selected="true"] { background-color: #3B82F6 !important; color: white !important; }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"] { display: none; }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; background-color: #0B0F19; }

    .section-header { background: linear-gradient(90deg, #1A2035 0%, #252D44 100%); padding: 0.875rem 1.25rem; border-radius: 6px; margin: 1rem 0; color: #E2E8F0; font-size: 1.05rem; font-weight: 600; border: 1px solid #252D44; }
    .info-box { background: #131825; border: 1px solid #252D44; border-left: 4px solid #60A5FA; padding: 1rem 1.25rem; border-radius: 0 6px 6px 0; margin: 0.75rem 0; color: #7A8599; }
    .info-box strong { color: #60A5FA; }

    .metric-card { background: linear-gradient(135deg, #1A2035 0%, #252D44 100%); padding: 1.25rem; border-radius: 10px; color: #E2E8F0; text-align: center; border: 1px solid #252D44; margin-bottom: 1rem; }
    .metric-card .label { font-size: 0.85rem; color: #7A8599; margin-bottom: 0.4rem; }
    .metric-card .value { font-size: 1.6rem; font-weight: 700; color: #60A5FA; }

    .nomination-table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 1rem 0; border-radius: 8px; overflow: hidden; }
    .nomination-table th { background-color: #1A2035; color: #7A8599; padding: 12px 14px; text-align: left; font-weight: 600; border-bottom: 1px solid #252D44; }
    .nomination-table td { padding: 10px 14px; border-bottom: 1px solid #1E2640; color: #E2E8F0; }
    .nomination-table .demand { background-color: #1C1708; color: #F59E0B; }
    .nomination-table .demand-total { background-color: #78350F; color: #FCD34D; font-weight: 600; }
    .nomination-table .supply { background-color: #0C1929; color: #60A5FA; }
    .nomination-table .supply-total { background-color: #1E3A5F; color: #93C5FD; font-weight: 600; }
    .nomination-table .balance { background-color: #064E3B; color: #6EE7B7; font-weight: 600; }

    .legend-container { display: flex; flex-wrap: wrap; gap: 1.25rem; padding: 0.875rem 1.25rem; background: #131825; border-radius: 6px; margin-bottom: 1rem; border: 1px solid #252D44; }
    .legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: #7A8599; }
    .legend-box { width: 18px; height: 18px; border-radius: 4px; }

    .no-data { text-align: center; padding: 3rem; background: #131825; border-radius: 10px; border: 2px dashed #252D44; color: #7A8599; }
    .no-data h3 { color: #E2E8F0; margin-bottom: 0.5rem; }

    /* Radio as pill buttons */
    .stRadio > div { display: flex; flex-direction: row; gap: 0; flex-wrap: wrap; }
    .stRadio > label { display: none; }
    div[role="radiogroup"] { display: flex; gap: 0; }
    div[role="radiogroup"] > label { background: #1A2035 !important; border: 1px solid #252D44 !important; padding: 8px 20px !important; cursor: pointer; color: #7A8599 !important; font-size: 13px !important; font-weight: 500 !important; margin: 0 !important; }
    div[role="radiogroup"] > label:first-child { border-radius: 6px 0 0 6px !important; }
    div[role="radiogroup"] > label:last-child { border-radius: 0 6px 6px 0 !important; }
    div[role="radiogroup"] > label:hover { background: #252D44 !important; color: #E2E8F0 !important; }
    div[role="radiogroup"] > label[data-checked="true"], div[role="radiogroup"] > label:has(input:checked) { background: linear-gradient(135deg, #3B82F6, #6366F1) !important; border-color: #3B82F6 !important; color: white !important; font-weight: 600 !important; }
    div[role="radiogroup"] > label > div:first-child { display: none !important; }

    div[data-testid="metric-container"] { background: #131825; border: 1px solid #252D44; border-radius: 8px; padding: 12px; }
    div[data-testid="metric-container"] label { color: #7A8599 !important; }
    div[data-testid="stMetricValue"] { color: #60A5FA !important; }

    details { background: #131825 !important; border: 1px solid #252D44 !important; border-radius: 8px !important; }
    summary { color: #7A8599 !important; }

    .stButton > button { background: #1A2035 !important; color: #7A8599 !important; border: 1px solid #252D44 !important; border-radius: 6px; padding: 0.5rem 1.25rem; font-weight: 500; font-size: 0.85rem; }
    .stButton > button:hover { background: #252D44 !important; color: #E2E8F0 !important; border-color: #60A5FA !important; }
    .stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] { background: linear-gradient(135deg, #3B82F6, #6366F1) !important; color: white !important; border-color: transparent !important; font-weight: 600; }

    .stSpinner > div { color: #60A5FA !important; }
    .stProgress > div > div { background-color: #252D44 !important; }
    .stProgress > div > div > div { background-color: #60A5FA !important; }
    .stMarkdown, .stText, p, span { color: #E2E8F0; }
    h1, h2, h3, h4 { color: #E2E8F0 !important; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# ELECTRICITY DEMAND FUNCTIONS (ELEXON API)
# ============================================================================

@st.cache_data(ttl=300)
def fetch_actual_demand_elexon(from_date, to_date):
    if (to_date - from_date).days > 7:
        to_date = from_date + timedelta(days=7)
    url = f"https://data.elexon.co.uk/bmrs/api/v1/demand/outturn/summary?from={from_date.strftime('%Y-%m-%d')}&to={to_date.strftime('%Y-%m-%d')}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data.get('data', data))
        if len(df) == 0: return pd.DataFrame()
        df['timestamp'] = pd.to_datetime(df['startTime'], utc=True)
        df['demand_mw'] = pd.to_numeric(df['demand'], errors='coerce')
        return df[['timestamp', 'demand_mw']].dropna().sort_values('timestamp').reset_index(drop=True)
    except:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_forecast_demand_elexon(from_datetime, to_datetime):
    from_str = from_datetime.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    to_str = to_datetime.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    url = f"https://data.elexon.co.uk/bmrs/api/v1/forecast/demand/day-ahead/latest?format=json&from={from_str}&to={to_str}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data.get('data', data))
        if len(df) == 0: return pd.DataFrame()
        df['timestamp'] = pd.to_datetime(df['startTime'], utc=True)
        df['demand_mw'] = pd.to_numeric(df['transmissionSystemDemand'], errors='coerce')
        return df[['timestamp', 'demand_mw']].dropna().sort_values('timestamp').reset_index(drop=True)
    except:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_historical_demand_elexon(start_date, end_date, chunk_days=7):
    chunk_days = min(chunk_days, 7)
    date_range = pd.date_range(start=start_date, end=end_date, freq=f'{chunk_days}D')
    if date_range[-1] < pd.Timestamp(end_date):
        date_range = date_range.append(pd.DatetimeIndex([end_date]))
    all_data = []
    for i in range(len(date_range) - 1):
        chunk_start = date_range[i].date()
        chunk_end = date_range[i + 1].date()
        if (chunk_end - chunk_start).days > 7:
            chunk_end = chunk_start + timedelta(days=7)
        chunk_data = fetch_actual_demand_elexon(chunk_start, chunk_end)
        if len(chunk_data) > 0: all_data.append(chunk_data)
        time.sleep(0.2)
    if len(all_data) == 0: return pd.DataFrame()
    result = pd.concat(all_data, ignore_index=True)
    return result.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)


def calculate_seasonal_baseline_electricity(historical_data, target_month, min_observations=5):
    if len(historical_data) == 0: return pd.DataFrame()
    df = historical_data.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['date'] = df['timestamp'].dt.date
    df['gas_day'] = pd.to_datetime(df['date']) - pd.to_timedelta((df['hour'] < 5).astype(int), unit='D')
    df['month'] = df['gas_day'].dt.month
    df['day_name'] = df['gas_day'].dt.day_name()
    df['day_type'] = df['day_name'].apply(lambda x: 'Weekend' if x in ['Saturday', 'Sunday'] else 'Weekday')
    df['hour_bin'] = df['hour']
    month_data = df[df['month'] == target_month].copy()
    if len(month_data) == 0: return pd.DataFrame()
    baseline = month_data.groupby(['day_type', 'hour_bin'])['demand_mw'].agg([
        ('mean_demand', 'mean'), ('q05', lambda x: x.quantile(0.05)), ('q25', lambda x: x.quantile(0.25)),
        ('q75', lambda x: x.quantile(0.75)), ('q95', lambda x: x.quantile(0.95)), ('n_obs', 'count')
    ]).reset_index()
    return baseline[baseline['n_obs'] >= min_observations].copy()


def expand_baseline_to_timeline_electricity(baseline, start_time, end_time):
    if len(baseline) == 0: return pd.DataFrame()
    time_grid = pd.date_range(start=start_time, end=end_time, freq='30T')
    expanded = pd.DataFrame({'timestamp': time_grid})
    expanded['hour_val'] = expanded['timestamp'].dt.hour
    expanded['date'] = expanded['timestamp'].dt.date
    expanded['gas_day'] = pd.to_datetime(expanded['date']) - pd.to_timedelta((expanded['hour_val'] < 5).astype(int), unit='D')
    expanded['day_name'] = expanded['gas_day'].dt.day_name()
    expanded['day_type'] = expanded['day_name'].apply(lambda x: 'Weekend' if x in ['Saturday', 'Sunday'] else 'Weekday')
    expanded['hour_bin'] = expanded['hour_val']
    expanded = expanded.merge(baseline, on=['day_type', 'hour_bin'], how='left')
    expanded = expanded.dropna(subset=['mean_demand']).sort_values('timestamp').reset_index(drop=True)
    if len(expanded) == 0: return pd.DataFrame()
    for col in ['mean_demand', 'q05', 'q25', 'q75', 'q95']:
        if col in expanded.columns:
            expanded[col] = expanded[col].rolling(window=5, center=True, min_periods=1).mean()
    return expanded.ffill().bfill()


def create_electricity_demand_plot(yesterday_actual, today_actual, forecast_data, baseline_expanded):
    fig = go.Figure()
    if len(baseline_expanded) > 0:
        bg = baseline_expanded.copy()
        for col in ['q95', 'q75', 'q25', 'q05', 'mean_demand']: bg[col] = bg[col] / 1000
        fig.add_trace(go.Scatter(x=bg['timestamp'], y=bg['q95'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=bg['timestamp'], y=bg['q05'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(67, 147, 195, 0.15)', name='5-95% Range'))
        fig.add_trace(go.Scatter(x=bg['timestamp'], y=bg['q75'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=bg['timestamp'], y=bg['q25'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(67, 147, 195, 0.25)', name='25-75% Range'))
        fig.add_trace(go.Scatter(x=bg['timestamp'], y=bg['mean_demand'], mode='lines', line=dict(color='#60A5FA', width=3, dash='dash'), name='Seasonal Mean', hovertemplate='<b>Seasonal Mean:</b> %{y:.1f} GW<extra></extra>'))
    if len(yesterday_actual) > 0:
        ya = yesterday_actual.copy(); ya['gw'] = ya['demand_mw'] / 1000
        fig.add_trace(go.Scatter(x=ya['timestamp'], y=ya['gw'], mode='lines', line=dict(color='#7A8599', width=2.5), name='Yesterday Actual', hovertemplate='<b>Yesterday:</b> %{y:.1f} GW<extra></extra>'))
    if len(today_actual) > 0:
        ta = today_actual.copy(); ta['gw'] = ta['demand_mw'] / 1000
        fig.add_trace(go.Scatter(x=ta['timestamp'], y=ta['gw'], mode='lines', line=dict(color='#EF4444', width=4), name='Today Actual', hovertemplate='<b>Actual Today:</b> %{y:.1f} GW<extra></extra>'))
    if len(forecast_data) > 0:
        fc = forecast_data.copy(); fc['gw'] = fc['demand_mw'] / 1000
        fig.add_trace(go.Scatter(x=fc['timestamp'], y=fc['gw'], mode='lines', line=dict(color='#34D399', width=4), name='Forecast', hovertemplate='<b>Forecast:</b> %{y:.1f} GW<extra></extra>'))
    now = datetime.utcnow()
    fig.add_vline(x=now.timestamp() * 1000, line_dash='dot', line_color='#E2E8F0', line_width=2, annotation_text='Now', annotation_position='top', annotation=dict(font=dict(size=11, color='#E2E8F0', family='Arial Black'), bgcolor='#131825', bordercolor='#252D44', borderwidth=1, borderpad=4))
    month_name = datetime.now().strftime('%B')
    year = datetime.now().year
    fig.update_layout(
        title=dict(text=f'<b>UK Electricity Demand: 48-Hour Outlook</b><br><sub>{month_name} {year} seasonal baseline</sub>', font=dict(size=16, color='#E2E8F0')),
        plot_bgcolor='#0B0F19', paper_bgcolor='#131825', font=dict(color='#E2E8F0', size=11), hovermode='x unified', height=500, margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(gridcolor='#1E2640', linecolor='#252D44', linewidth=1, tickformat='%a %d<br>%H:%M', showline=True, tickfont=dict(color='#7A8599')),
        yaxis=dict(title=dict(text='Demand (GW)', font=dict(color='#7A8599')), gridcolor='#1E2640', linecolor='#252D44', linewidth=1, showline=True, tickfont=dict(color='#7A8599')),
        legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='right', x=0.99, bgcolor='#131825', bordercolor='#252D44', borderwidth=1, font=dict(size=11, color='#7A8599'))
    )
    return fig


# ============================================================================
# WIND GENERATION FUNCTIONS (ELEXON API)
# ============================================================================

@st.cache_data(ttl=300)
def fetch_actual_wind_generation(from_date, to_date):
    def get_period(t):
        return (t.hour * 60 + t.minute) // 30 + 1
    url = f"https://data.elexon.co.uk/bmrs/api/v1/generation/actual/per-type/wind-and-solar?from={from_date.strftime('%Y-%m-%d')}&to={to_date.strftime('%Y-%m-%d')}&settlementPeriodFrom=1&settlementPeriodTo={get_period(datetime.utcnow())}"
    try:
        response = requests.get(url, headers={'Accept': 'text/plain'}, timeout=30)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data.get('data', data))
        if len(df) == 0: return pd.DataFrame()
        df['startTime'] = pd.to_datetime(df['startTime'], utc=True)
        df['settlementDate'] = pd.to_datetime(df['settlementDate']).dt.date
        df['settlementPeriod'] = df['settlementPeriod'].astype(int)
        wind_df = df[df['businessType'] == 'Wind generation'].copy()
        if len(wind_df) == 0: return pd.DataFrame()
        actual_summary = wind_df.groupby(['settlementDate', 'settlementPeriod']).agg(wind_actual_mw=('quantity', 'sum')).reset_index()
        actual_summary['timestamp'] = actual_summary.apply(lambda row: pd.Timestamp(row['settlementDate']) + pd.Timedelta(minutes=(row['settlementPeriod'] - 1) * 30), axis=1)
        return actual_summary[['timestamp', 'wind_actual_mw']].sort_values('timestamp').reset_index(drop=True)
    except:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_wind_forecast():
    url = "https://data.elexon.co.uk/bmrs/api/v1/forecast/generation/wind"
    try:
        response = requests.get(url, headers={'Accept': 'text/plain'}, timeout=30)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data.get('data', data))
        if len(df) == 0: return pd.DataFrame()
        df['startTime'] = pd.to_datetime(df['startTime'], utc=True)
        df['settlementDate'] = pd.to_datetime(df['settlementDate']).dt.date
        df['settlementPeriod'] = df['settlementPeriod'].astype(int)
        fs = df.groupby(['settlementDate', 'settlementPeriod']).agg(wind_forecast_mw=('generation', 'sum')).reset_index()
        fs['timestamp'] = fs.apply(lambda row: pd.Timestamp(row['settlementDate']) + pd.Timedelta(minutes=(row['settlementPeriod'] - 1) * 30), axis=1)
        return fs[['timestamp', 'wind_forecast_mw']].sort_values('timestamp').reset_index(drop=True)
    except:
        return pd.DataFrame()


def create_wind_generation_plot(actual_df, forecast_df, gas_day_start, gas_day_end):
    fig = go.Figure()
    if len(forecast_df) > 0:
        fp = forecast_df[(forecast_df['timestamp'] >= gas_day_start) & (forecast_df['timestamp'] <= gas_day_end)].copy()
        fp['gw'] = fp['wind_forecast_mw'] / 1000
    else: fp = pd.DataFrame()
    if len(actual_df) > 0:
        ap = actual_df[actual_df['timestamp'] >= gas_day_start].copy()
        ap['gw'] = ap['wind_actual_mw'] / 1000
    else: ap = pd.DataFrame()
    avg_actual = ap['gw'].mean() if len(ap) > 0 else 0
    if len(fp) > 0:
        fig.add_trace(go.Scatter(x=fp['timestamp'], y=fp['gw'], mode='lines', line=dict(color='#F59E0B', width=2.5, dash='dash'), name='Day-ahead Forecast', hovertemplate='<b>Forecast:</b> %{y:.1f} GW<extra></extra>'))
    if len(ap) > 0:
        fig.add_trace(go.Scatter(x=ap['timestamp'], y=ap['gw'], mode='lines', line=dict(color='#60A5FA', width=3.5), name='Actual Generation', hovertemplate='<b>Actual:</b> %{y:.1f} GW<extra></extra>'))
    if avg_actual > 0:
        fig.add_hline(y=avg_actual, line_dash='dash', line_color='#34D399', line_width=1.5, annotation_text=f"Avg: {avg_actual:.1f} GW", annotation_position='right', annotation=dict(font=dict(size=11, color='#34D399')))
    fig.add_hline(y=9.5, line_dash='dot', line_color='#7A8599', line_width=1.5, annotation_text="Annual avg: 9.5 GW", annotation_position='right', annotation=dict(font=dict(size=11, color='#7A8599')))
    now = datetime.utcnow()
    fig.add_vline(x=now.timestamp() * 1000, line_dash='dot', line_color='#E2E8F0', line_width=2, annotation_text='Now', annotation_position='top', annotation=dict(font=dict(size=11, color='#E2E8F0', family='Arial Black'), bgcolor='#131825', bordercolor='#252D44', borderwidth=1, borderpad=4))
    today_str = datetime.now().strftime('%d %b %Y')
    fig.update_layout(
        title=dict(text=f'<b>UK Wind Generation: Actual vs Forecast</b><br><sub>Blue = Actual | Orange dashed = Forecast | {today_str} gas day</sub>', font=dict(size=16, color='#E2E8F0')),
        plot_bgcolor='#0B0F19', paper_bgcolor='#131825', font=dict(color='#E2E8F0', size=11), hovermode='x unified', height=500, margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(gridcolor='#1E2640', linecolor='#252D44', linewidth=1, tickformat='%H:%M', range=[gas_day_start, gas_day_end], showline=True, tickfont=dict(color='#7A8599')),
        yaxis=dict(title=dict(text='Wind Generation (GW)', font=dict(color='#7A8599')), gridcolor='#1E2640', linecolor='#252D44', linewidth=1, showline=True, rangemode='tozero', tickfont=dict(color='#7A8599')),
        legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='right', x=0.99, bgcolor='#131825', bordercolor='#252D44', borderwidth=1, font=dict(size=11, color='#7A8599'))
    )
    return fig


# ============================================================================
# LNG VESSEL TRACKING FUNCTIONS
# ============================================================================

@st.cache_data(ttl=300)
def get_milford_haven_vessels():
    url = "https://www.mhpa.co.uk/live-information/vessels-arriving/"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, timeout=15)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='timetable-table') or soup.find('table')
        if not table: return None
        headers_row = table.find('thead')
        if headers_row: headers = [th.get_text(strip=True) for th in headers_row.find_all(['th', 'td'])]
        else: headers = [cell.get_text(strip=True) for cell in table.find('tr').find_all(['th', 'td'])]
        rows = table.find_all('tr')
        data = []
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if cells:
                row_data = [cell.get_text(strip=True) for cell in cells]
                if len(row_data) >= len(headers): data.append(row_data[:len(headers)])
                elif len(row_data) > 0: row_data.extend([''] * (len(headers) - len(row_data))); data.append(row_data)
        if not data: return None
        df = pd.DataFrame(data, columns=headers)
        df.columns = [col.strip() for col in df.columns]
        return df
    except:
        return None


@st.cache_data(ttl=300)
def get_lng_vessels():
    vessels_df = get_milford_haven_vessels()
    if vessels_df is None or len(vessels_df) == 0: return None
    ship_type_col = None
    for col in vessels_df.columns:
        if 'type' in col.lower() or 'ship type' in col.lower(): ship_type_col = col; break
    if ship_type_col is None: return vessels_df
    lng_df = vessels_df[vessels_df[ship_type_col].str.lower().str.contains('lng', na=False)].copy()
    return lng_df if len(lng_df) > 0 else None


def render_lng_vessel_table(df):
    if df is None or len(df) == 0:
        st.markdown('<div class="no-data"><h3>No LNG Vessels Found</h3><p>No LNG tankers are currently scheduled.</p></div>', unsafe_allow_html=True)
        return
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object': df[col] = df[col].apply(lambda x: html.unescape(x) if isinstance(x, str) else x)
    ship_col, to_col, datetime_col, from_col = None, None, None, None
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ['ship', 'vessel', 'name', 'vessel name', 'ship name']: ship_col = col
        elif cl == 'to': to_col = col
        elif cl == 'from': from_col = col
        elif any(t in cl for t in ['date', 'time', 'eta', 'arrival']): datetime_col = col
    if not ship_col: ship_col = df.columns[0]
    display_cols = [c for c in [ship_col, to_col, datetime_col, from_col] if c and c in df.columns]
    if len(display_cols) == 0: display_cols = list(df.columns[:4])
    display_df = df[display_cols].copy()
    rename_map = {}
    if to_col and to_col in display_df.columns: rename_map[to_col] = 'Destination'
    if datetime_col and datetime_col in display_df.columns: rename_map[datetime_col] = 'Date/Time'
    if from_col and from_col in display_df.columns: rename_map[from_col] = 'From'
    if ship_col and ship_col in display_df.columns and ship_col.lower() != 'ship': rename_map[ship_col] = 'Ship'
    display_df = display_df.rename(columns=rename_map)
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ============================================================================
# GAS MARKET FUNCTIONS
# ============================================================================

@st.cache_data(ttl=120)
def scrape_gassco_data():
    try:
        session = requests.Session()
        session.get("https://umm.gassco.no/", timeout=10)
        session.get("https://umm.gassco.no/disclaimer/acceptDisclaimer", timeout=10)
        response = session.get("https://umm.gassco.no/", timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        msg_tables = soup.find_all('table', class_='msgTable')
        fields_df = parse_gassco_table(msg_tables[0]) if len(msg_tables) > 0 else None
        terminal_df = parse_gassco_table(msg_tables[1]) if len(msg_tables) > 1 else None
        return fields_df, terminal_df
    except:
        return None, None


def parse_gassco_table(table):
    rows = table.find_all('tr', id=True)
    data = []
    for row in rows:
        cells = row.find_all('td')
        ct = [cell.get_text(strip=True) for cell in cells]
        if len(ct) >= 19:
            data.append({'Affected Asset or Unit': ct[1], 'Event Status': ct[2], 'Type of Unavailability': ct[3], 'Publication date/time': ct[5], 'Event Start': ct[6], 'Event Stop': ct[7], 'Technical Capacity': ct[9], 'Available Capacity': ct[10], 'Unavailable Capacity': ct[11], 'Reason for the unavailability': ct[12]})
    return pd.DataFrame(data) if data else None


def process_remit_data(df):
    if df is None or len(df) == 0: return None
    df = df[df['Event Status'] == 'Active'].copy()
    if len(df) == 0: return None
    df['Publication date/time'] = pd.to_datetime(df['Publication date/time'], format='ISO8601', utc=True)
    df['Event Start'] = pd.to_datetime(df['Event Start'], format='ISO8601', utc=True)
    df['Event Stop'] = pd.to_datetime(df['Event Stop'], format='ISO8601', utc=True)
    for col in ['Technical Capacity', 'Available Capacity', 'Unavailable Capacity']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    cutoff = datetime.now(df['Event Start'].dt.tz) + timedelta(days=14)
    df = df[(df['Event Start'] <= cutoff) | (df['Event Stop'] <= cutoff)]
    if len(df) == 0: return None
    df = df.drop_duplicates()
    df['Duration'] = (df['Event Stop'] - df['Event Start']).dt.total_seconds() / (24 * 3600)
    df['midpoint'] = df['Event Start'] + (df['Event Stop'] - df['Event Start']) / 2
    return df.sort_values('Unavailable Capacity')


@st.cache_data(ttl=120)
def get_gas_data(request_type, max_retries=3):
    url = "https://data.nationalgas.com/api/gas-system-status-graph"
    headers = {"Content-Type": "application/json"}
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json={"request": request_type}, headers=headers, timeout=30)
            response.raise_for_status()
            return pd.DataFrame(response.json()["data"])
        except:
            if attempt < max_retries - 1: time.sleep(1); continue
            return None
    return None


def get_chart_layout(title="", height=450):
    return dict(
        title=dict(text=title, font=dict(size=16, color='#E2E8F0')),
        plot_bgcolor='#0B0F19', paper_bgcolor='#131825', font=dict(color='#E2E8F0', size=11),
        hovermode='x unified', height=height, margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(gridcolor='#1E2640', linecolor='#252D44', linewidth=1, showline=True, tickfont=dict(color='#7A8599')),
        yaxis=dict(gridcolor='#1E2640', linecolor='#252D44', linewidth=1, showline=True, tickfont=dict(color='#7A8599'))
    )


def create_gassco_timeline_plot(df, title_prefix):
    colors = {'Planned': '#60A5FA', 'Unplanned': '#EF4444'}
    fig = go.Figure()
    shown = set()
    for _, row in df.iterrows():
        color = colors.get(row['Type of Unavailability'], '#7A8599')
        show_legend = row['Type of Unavailability'] not in shown
        if show_legend: shown.add(row['Type of Unavailability'])
        fig.add_trace(go.Scatter(
            x=[row['Event Start'], row['Event Stop']], y=[row['Affected Asset or Unit'], row['Affected Asset or Unit']],
            mode='lines', line=dict(color=color, width=20), name=row['Type of Unavailability'], legendgroup=row['Type of Unavailability'], showlegend=show_legend,
            hovertemplate=f"<b>{row['Affected Asset or Unit']}</b><br>Type: {row['Type of Unavailability']}<br>Unavailable: {row['Unavailable Capacity']:.1f} MSm\u00b3/d<extra></extra>"
        ))
        fig.add_annotation(x=row['midpoint'], y=row['Affected Asset or Unit'], text=f"<b>{row['Unavailable Capacity']:.1f}</b>", showarrow=False, font=dict(size=11, color='#E2E8F0'), yshift=22, bgcolor='#131825', bordercolor='#252D44', borderwidth=1, borderpad=4)
    today = datetime.now(df['Event Start'].dt.tz)
    layout = get_chart_layout(f"<b>{title_prefix} Outages Timeline</b>", max(400, len(df) * 60))
    layout['xaxis']['type'] = 'date'
    layout['xaxis']['tickformat'] = '%d %b'
    layout['yaxis']['categoryorder'] = 'array'
    layout['yaxis']['categoryarray'] = df['Affected Asset or Unit'].tolist()
    layout['shapes'] = [dict(type='line', x0=today, x1=today, y0=0, y1=1, yref='paper', line=dict(color='#EF4444', width=2, dash='dash'))]
    fig.update_layout(**layout)
    fig.add_annotation(x=today, y=1.02, yref='paper', text='<b>Today</b>', showarrow=False, font=dict(size=12, color='#EF4444'), bgcolor='#131825', bordercolor='#EF4444', borderwidth=1, borderpad=4)
    return fig


def create_gassco_cumulative_plot(df, title_prefix):
    events = []
    for _, row in df.iterrows():
        events.append({'time': row['Event Start'], 'delta': -row['Unavailable Capacity']})
        events.append({'time': row['Event Stop'], 'delta': row['Unavailable Capacity']})
    events_df = pd.DataFrame(events).groupby('time')['delta'].sum().reset_index().sort_values('time')
    events_df['cumulative'] = events_df['delta'].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=events_df['time'], y=events_df['cumulative'], mode='lines+markers', line=dict(shape='hv', color='#EF4444', width=3), marker=dict(size=8), fill='tozeroy', fillcolor='rgba(239, 68, 68, 0.1)', hovertemplate="<b>Time:</b> %{x|%d %b %Y %H:%M}<br><b>Cumulative:</b> %{y:.1f} MSm\u00b3/d<extra></extra>"))
    today = datetime.now(df['Event Start'].dt.tz)
    layout = get_chart_layout(f"<b>{title_prefix} Cumulative Unavailable</b>", 400)
    layout['xaxis']['type'] = 'date'
    layout['yaxis']['title'] = dict(text='Unavailable Capacity (MSm\u00b3/d)', font=dict(color='#7A8599'))
    layout['shapes'] = [dict(type='line', x0=today, x1=today, y0=0, y1=1, yref='paper', line=dict(color='#E2E8F0', width=2, dash='dash'))]
    layout['showlegend'] = False
    fig.update_layout(**layout)
    return fig


def gas_day_start():
    now = datetime.now()
    if now.hour < 5:
        today = (now - timedelta(days=1)).date()
    else:
        today = now.date()
    return datetime.combine(today, datetime.min.time().replace(hour=5))


def create_flow_chart(df, column_name, chart_title, color='#60A5FA'):
    if column_name not in df.columns: return None, 0, 0, 0
    avg = np.average(df[column_name], weights=df['interval_seconds'])
    start = gas_day_start()
    end = start + timedelta(days=1)
    now = datetime.now()
    elapsed_pct = max(0, min(1, (now - start).total_seconds() / 86400))
    total = avg * elapsed_pct
    fig = go.Figure()
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    fig.add_trace(go.Scatter(x=df['Timestamp'], y=df[column_name], mode='lines', line=dict(color=color, width=3), fill='tozeroy', fillcolor=f'rgba({r},{g},{b},0.15)', hovertemplate='<b>Time:</b> %{x|%H:%M}<br><b>Flow:</b> %{y:.2f} mcm<extra></extra>'))
    fig.add_hline(y=avg, line_dash="dash", line_color="#EF4444", line_width=2, annotation_text=f"<b>Avg: {avg:.2f}</b>", annotation_position="right", annotation=dict(font=dict(size=12, color="#EF4444"), bgcolor="#131825", bordercolor="#EF4444", borderwidth=1))
    fig.add_vline(x=int(now.timestamp() * 1000), line_color="#E2E8F0", line_width=2, annotation_text=f"<b>Now: {total:.2f}</b>", annotation_position="top", annotation=dict(font=dict(size=12, color='#E2E8F0'), bgcolor="#131825", bordercolor="#252D44", borderwidth=1))
    y_max = max(df[column_name].max(), 1)
    layout = get_chart_layout(f"<b>{chart_title}</b>", 400)
    layout['xaxis']['range'] = [start, end]
    layout['xaxis']['tickformat'] = '%H:%M'
    layout['yaxis']['range'] = [0, y_max * 1.25]
    layout['yaxis']['title'] = dict(text='Flow Rate (mcm)', font=dict(color='#7A8599'))
    layout['showlegend'] = False
    fig.update_layout(**layout)
    return fig, avg, total, df[column_name].iloc[-1] if len(df) > 0 else 0


def render_metric_cards(metrics):
    cols = st.columns(len(metrics))
    for col, (label, value, unit) in zip(cols, metrics):
        with col:
            st.markdown(f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value:.2f} {unit}</div></div>', unsafe_allow_html=True)


def render_nomination_table(demand_df, supply_df):
    demand_cols = ["LDZ Offtake", "Power Station", "Industrial", "Storage Injection", "Bacton BBL Export", "Bacton INT Export", "Moffat Export"]
    supply_cols = ["Storage Withdrawal", "LNG", "Bacton BBL Import", "Bacton INT Import", "Beach (UKCS/Norway)"]
    def summarise(df, cols):
        n = len(df) if df is not None else 0
        pct = (n * 2) / 1440 if n > 0 else 0
        results = []
        for col in cols:
            if df is not None and col in df.columns:
                avg = df[col].mean() if not df[col].isna().all() else 0
                comp = avg * pct
                inst = df[col].iloc[-1] if len(df) > 0 and not df[col].isna().all() else 0
            else: avg, comp, inst = 0, 0, 0
            results.append({"Category": col, "Avg": round(avg, 2), "Comp": round(comp, 2), "Inst": round(inst, 2)})
        return pd.DataFrame(results)
    demand_sum = summarise(demand_df, demand_cols)
    supply_sum = summarise(supply_df, supply_cols)
    d_tot = demand_sum[["Avg", "Comp", "Inst"]].sum()
    s_tot = supply_sum[["Avg", "Comp", "Inst"]].sum()
    bal = s_tot - d_tot
    st.markdown("""
    <div class="legend-container">
        <div class="legend-item"><div class="legend-box" style="background-color: #F59E0B;"></div> Demand</div>
        <div class="legend-item"><div class="legend-box" style="background-color: #78350F;"></div> Demand Total</div>
        <div class="legend-item"><div class="legend-box" style="background-color: #60A5FA;"></div> Supply</div>
        <div class="legend-item"><div class="legend-box" style="background-color: #1E3A5F;"></div> Supply Total</div>
        <div class="legend-item"><div class="legend-box" style="background-color: #064E3B;"></div> Balance</div>
    </div>
    """, unsafe_allow_html=True)
    rows = []
    for _, r in demand_sum.iterrows():
        rows.append(f'<tr class="demand"><td>{r["Category"]}</td><td style="text-align:right;">{r["Avg"]:.1f}</td><td style="text-align:right;">{r["Comp"]:.1f}</td><td style="text-align:right;">{r["Inst"]:.1f}</td></tr>')
    rows.append(f'<tr class="demand-total"><td><strong>DEMAND TOTAL</strong></td><td style="text-align:right;"><strong>{d_tot["Avg"]:.1f}</strong></td><td style="text-align:right;"><strong>{d_tot["Comp"]:.1f}</strong></td><td style="text-align:right;"><strong>{d_tot["Inst"]:.1f}</strong></td></tr>')
    for _, r in supply_sum.iterrows():
        rows.append(f'<tr class="supply"><td>{r["Category"]}</td><td style="text-align:right;">{r["Avg"]:.1f}</td><td style="text-align:right;">{r["Comp"]:.1f}</td><td style="text-align:right;">{r["Inst"]:.1f}</td></tr>')
    rows.append(f'<tr class="supply-total"><td><strong>SUPPLY TOTAL</strong></td><td style="text-align:right;"><strong>{s_tot["Avg"]:.1f}</strong></td><td style="text-align:right;"><strong>{s_tot["Comp"]:.1f}</strong></td><td style="text-align:right;"><strong>{s_tot["Inst"]:.1f}</strong></td></tr>')
    rows.append(f'<tr class="balance"><td><strong>BALANCE</strong></td><td style="text-align:right;"><strong>{bal["Avg"]:.1f}</strong></td><td style="text-align:right;"><strong>{bal["Comp"]:.1f}</strong></td><td style="text-align:right;"><strong>{bal["Inst"]:.1f}</strong></td></tr>')
    st.markdown(f'<table class="nomination-table"><thead><tr><th>Category</th><th style="text-align:right;">Avg Rate (mcm)</th><th style="text-align:right;">Completed (mcm)</th><th style="text-align:right;">Instant (mcm)</th></tr></thead><tbody>{"".join(rows)}</tbody></table>', unsafe_allow_html=True)
    return bal


def render_gassco_table(df):
    display_df = df.copy()
    for col in ['Publication date/time', 'Event Start', 'Event Stop']:
        if col in display_df.columns: display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M')
    cols = [c for c in ['Affected Asset or Unit', 'Type of Unavailability', 'Event Start', 'Event Stop', 'Unavailable Capacity', 'Duration', 'Reason for the unavailability'] if c in display_df.columns]
    st.dataframe(display_df[cols], use_container_width=True, hide_index=True)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    st.markdown(f'''
    <div class="header-bar">
        <div>
            <h1>\u26a1 UK Energy Market Dashboard</h1>
            <div class="subtitle">Real-time monitoring of gas and electricity markets</div>
        </div>
        <div class="header-time">
            <strong>{datetime.now().strftime("%H:%M:%S")}</strong><br>
            {datetime.now().strftime("%d %B %Y")}<br>
            Gas Day: {datetime.now().strftime("%d %b") if datetime.now().hour >= 5 else (datetime.now() - timedelta(days=1)).strftime("%d %b")}
        </div>
    </div>
    ''', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([8, 1, 1])
    with col3:
        if st.button("\U0001f504 Refresh"):
            st.cache_data.clear()
            st.rerun()

    tab_gas, tab_elexon, tab_gassco, tab_lng = st.tabs([
        "\U0001f525 National Gas", "\u26a1 Electricity (Elexon)", "\U0001f527 GASSCO Outages", "\U0001f6a2 LNG Vessels"
    ])

    # ── NATIONAL GAS TAB ──
    with tab_gas:
        ng_view = st.radio("Select View", ["Flow Table", "Supply Charts", "Demand Charts", "Gas Storage"], horizontal=True, key="ng_view", label_visibility="collapsed")

        if ng_view == "Gas Storage":
            render_gas_storage_tab()
        else:
            demand_df = get_gas_data("demandCategoryGraph")
            supply_df = get_gas_data("supplyCategoryGraph")
            if demand_df is not None and supply_df is not None:
                if 'Storage' in demand_df.columns:
                    demand_df = demand_df.copy(); demand_df.rename(columns={'Storage': 'Storage Injection'}, inplace=True)
                n = len(demand_df)
                start = gas_day_start()
                ts = [start + timedelta(minutes=2*i) for i in range(n)]
                demand_df = demand_df.copy(); demand_df['Timestamp'] = ts
                demand_df = demand_df.sort_values('Timestamp').reset_index(drop=True)
                demand_df['next_time'] = demand_df['Timestamp'].shift(-1).fillna(demand_df['Timestamp'].iloc[-1] + timedelta(minutes=2))
                demand_df['interval_seconds'] = (demand_df['next_time'] - demand_df['Timestamp']).dt.total_seconds()
                n_s = len(supply_df)
                ts_s = [start + timedelta(minutes=2*i) for i in range(n_s)]
                supply_df = supply_df.copy(); supply_df['Timestamp'] = ts_s
                supply_df = supply_df.sort_values('Timestamp').reset_index(drop=True)
                supply_df['next_time'] = supply_df['Timestamp'].shift(-1).fillna(supply_df['Timestamp'].iloc[-1] + timedelta(minutes=2))
                supply_df['interval_seconds'] = (supply_df['next_time'] - supply_df['Timestamp']).dt.total_seconds()

                if ng_view == "Flow Table":
                    st.markdown('<div class="section-header">UK Gas Flows - Supply, Demand & Balance</div>', unsafe_allow_html=True)
                    st.markdown('<div class="info-box"><strong>Flow Table</strong> \u2014 Current gas day flows from National Gas. All values in mcm.</div>', unsafe_allow_html=True)
                    render_nomination_table(demand_df, supply_df)
                elif ng_view == "Supply Charts":
                    supply_cat = st.radio("Supply Category", ["LNG", "Storage Withdrawal", "Beach Terminal", "IC Import"], horizontal=True, key="supply_cat", label_visibility="collapsed")
                    st.markdown(f'<div class="section-header">Supply - {supply_cat}</div>', unsafe_allow_html=True)
                    if supply_cat == "IC Import":
                        supply_df['Total IC Import'] = supply_df['Bacton BBL Import'] + supply_df['Bacton INT Import']
                        col_name = 'Total IC Import'
                    else:
                        col_name = {"LNG": "LNG", "Storage Withdrawal": "Storage Withdrawal", "Beach Terminal": "Beach (UKCS/Norway)"}.get(supply_cat)
                    if col_name and col_name in supply_df.columns:
                        fig, avg, total, current = create_flow_chart(supply_df, col_name, f'{supply_cat} Flow', '#60A5FA')
                        if fig:
                            render_metric_cards([("Average Flow", avg, "mcm"), ("Total So Far", total, "mcm"), ("Current Flow", current, "mcm")])
                            st.plotly_chart(fig, use_container_width=True, theme=None)
                elif ng_view == "Demand Charts":
                    demand_cat = st.radio("Demand Category", ["CCGT", "Storage Injection", "LDZ", "Industrial", "IC Export"], horizontal=True, key="demand_cat", label_visibility="collapsed")
                    st.markdown(f'<div class="section-header">Demand - {demand_cat}</div>', unsafe_allow_html=True)
                    if demand_cat == "IC Export":
                        demand_df['Total IC Export'] = demand_df['Bacton BBL Export'] + demand_df['Bacton INT Export'] + demand_df['Moffat Export']
                        col_name = 'Total IC Export'
                    else:
                        col_name = {"CCGT": "Power Station", "Storage Injection": "Storage Injection", "LDZ": "LDZ Offtake", "Industrial": "Industrial"}.get(demand_cat)
                    if col_name and col_name in demand_df.columns:
                        fig, avg, total, current = create_flow_chart(demand_df, col_name, f'{demand_cat} Flow', '#F59E0B')
                        if fig:
                            render_metric_cards([("Average Flow", avg, "mcm"), ("Total So Far", total, "mcm"), ("Current Flow", current, "mcm")])
                            st.plotly_chart(fig, use_container_width=True, theme=None)
            else:
                st.error("\u26a0\ufe0f Unable to fetch National Gas data. Please try refreshing.")

    # ── ELEXON TAB ──
    with tab_elexon:
        elexon_view = st.radio("Select View", ["Electricity Demand", "Wind Profile"], horizontal=True, key="elexon_view", label_visibility="collapsed")
        if elexon_view == "Electricity Demand":
            st.markdown('<div class="section-header">UK Electricity Demand: 48-Hour Outlook</div>', unsafe_allow_html=True)
            st.markdown('<div class="info-box"><strong>Electricity Demand Forecast</strong> \u2014 Shows actual demand, 48-hour forecast, and seasonal baseline.</div>', unsafe_allow_html=True)
            progress_container = st.empty()
            with progress_container.container():
                progress_bar = st.progress(0, text="Loading electricity data...")
                today = datetime.utcnow().date()
                current_hour = datetime.utcnow().hour
                gas_day_today = today - timedelta(days=1) if current_hour < 5 else today
                gas_day_yesterday = gas_day_today - timedelta(days=1)
                plot_start = datetime.combine(gas_day_yesterday, datetime.min.time().replace(hour=5))
                plot_end = datetime.combine(gas_day_today + timedelta(days=2), datetime.min.time().replace(hour=5))
                today_gas_day_start = datetime.combine(gas_day_today, datetime.min.time().replace(hour=5))
                progress_bar.progress(10, text="Fetching actual demand...")
                actual_demand = fetch_actual_demand_elexon(gas_day_yesterday, today + timedelta(days=1))
                progress_bar.progress(30, text="Fetching forecast...")
                forecast_demand = fetch_forecast_demand_elexon(plot_start, plot_end)
                progress_bar.progress(50, text="Loading historical baseline...")
                historical_start = (today - timedelta(days=365)).replace(day=1)
                historical_end = gas_day_yesterday - timedelta(days=1)
                historical_demand = fetch_historical_demand_elexon(historical_start, historical_end)
                progress_bar.progress(90, text="Calculating seasonal baseline...")
                baseline = calculate_seasonal_baseline_electricity(historical_demand, today.month)
                baseline_expanded = expand_baseline_to_timeline_electricity(baseline, plot_start, plot_end)
                progress_bar.progress(100, text="Complete!")
            progress_container.empty()
            if len(actual_demand) > 0:
                adc = actual_demand.copy(); adc['timestamp'] = pd.to_datetime(adc['timestamp'], utc=True).dt.tz_localize(None)
                adc = adc[adc['timestamp'] >= plot_start].copy()
                yesterday_actual = adc[adc['timestamp'] < today_gas_day_start].copy()
                today_actual = adc[adc['timestamp'] >= today_gas_day_start].copy()
                latest_actual_time = today_actual['timestamp'].max() if len(today_actual) > 0 else today_gas_day_start
            else:
                yesterday_actual, today_actual = pd.DataFrame(), pd.DataFrame()
                latest_actual_time = today_gas_day_start
            if len(forecast_demand) > 0:
                fc = forecast_demand.copy(); fc['timestamp'] = pd.to_datetime(fc['timestamp'], utc=True).dt.tz_localize(None)
                forecast_plot = fc[(fc['timestamp'] > latest_actual_time) & (fc['timestamp'] <= plot_end)].copy()
            else: forecast_plot = pd.DataFrame()
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Current Demand", f"{today_actual['demand_mw'].iloc[-1] / 1000:.1f} GW" if len(today_actual) > 0 else "N/A")
            with col2: st.metric("Average Today", f"{today_actual['demand_mw'].mean() / 1000:.1f} GW" if len(today_actual) > 0 else "N/A")
            with col3: st.metric("Peak Forecast", f"{forecast_plot['demand_mw'].max() / 1000:.1f} GW" if len(forecast_plot) > 0 else "N/A")
            fig = create_electricity_demand_plot(yesterday_actual, today_actual, forecast_plot, baseline_expanded)
            st.plotly_chart(fig, use_container_width=True, theme=None)
        elif elexon_view == "Wind Profile":
            st.markdown('<div class="section-header">UK Wind Generation: Actual vs Forecast</div>', unsafe_allow_html=True)
            st.markdown('<div class="info-box"><strong>Wind Generation Profile</strong> \u2014 Compare actual wind generation against day-ahead forecast.</div>', unsafe_allow_html=True)
            with st.spinner("Loading wind generation data..."):
                today = datetime.utcnow().date()
                actual_wind = fetch_actual_wind_generation(today, today + timedelta(days=1))
                forecast_wind = fetch_wind_forecast()
                if len(forecast_wind) > 0:
                    forecast_wind = forecast_wind[forecast_wind['timestamp'].dt.date.isin([today, today + timedelta(days=1)])].copy()
                wind_day_start = datetime.combine(today, datetime.min.time().replace(hour=5))
                wind_day_end = datetime.combine(today + timedelta(days=1), datetime.min.time().replace(hour=5))
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Current Wind", f"{actual_wind['wind_actual_mw'].iloc[-1] / 1000:.1f} GW" if len(actual_wind) > 0 else "N/A")
            with col2: st.metric("Avg Actual", f"{actual_wind['wind_actual_mw'].mean() / 1000:.1f} GW" if len(actual_wind) > 0 else "N/A")
            with col3: st.metric("Peak Actual", f"{actual_wind['wind_actual_mw'].max() / 1000:.1f} GW" if len(actual_wind) > 0 else "N/A")
            fig = create_wind_generation_plot(actual_wind, forecast_wind, wind_day_start, wind_day_end)
            st.plotly_chart(fig, use_container_width=True, theme=None)

    # ── GASSCO TAB ──
    with tab_gassco:
        gassco_view = st.radio("Select View", ["Field Outages", "Terminal Outages"], horizontal=True, key="gassco_view", label_visibility="collapsed")
        with st.spinner("Loading GASSCO outage data..."):
            fields_df, terminal_df = scrape_gassco_data()
            fields_proc = process_remit_data(fields_df)
            terminal_proc = process_remit_data(terminal_df)
        if gassco_view == "Field Outages":
            st.markdown('<div class="section-header">GASSCO - Norwegian Field Outages</div>', unsafe_allow_html=True)
            if fields_proc is not None and len(fields_proc) > 0:
                st.markdown(f'<div class="info-box"><strong>{len(fields_proc)} active field outage(s)</strong> scheduled within the next 14 days.</div>', unsafe_allow_html=True)
                st.plotly_chart(create_gassco_timeline_plot(fields_proc, "Field"), use_container_width=True, theme=None)
                st.plotly_chart(create_gassco_cumulative_plot(fields_proc, "Field"), use_container_width=True, theme=None)
                st.markdown("#### Outage Details")
                render_gassco_table(fields_proc)
            else:
                st.markdown('<div class="no-data"><h3>\u2705 No Field Outages</h3><p>No active field outages within 14 days.</p></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="section-header">GASSCO - Terminal Outages</div>', unsafe_allow_html=True)
            if terminal_proc is not None and len(terminal_proc) > 0:
                st.markdown(f'<div class="info-box"><strong>{len(terminal_proc)} active terminal outage(s)</strong> scheduled within the next 14 days.</div>', unsafe_allow_html=True)
                st.plotly_chart(create_gassco_timeline_plot(terminal_proc, "Terminal"), use_container_width=True, theme=None)
                st.plotly_chart(create_gassco_cumulative_plot(terminal_proc, "Terminal"), use_container_width=True, theme=None)
                st.markdown("#### Outage Details")
                render_gassco_table(terminal_proc)
            else:
                st.markdown('<div class="no-data"><h3>\u2705 No Terminal Outages</h3><p>No active terminal outages within 14 days.</p></div>', unsafe_allow_html=True)

    # ── LNG VESSELS TAB ──
    with tab_lng:
        st.markdown('<div class="section-header">LNG Vessels - Milford Haven Port</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box"><strong>LNG Vessel Tracking</strong> \u2014 Shows confirmed LNG tankers arriving at Milford Haven.</div>', unsafe_allow_html=True)
        with st.spinner("Loading vessel data..."):
            lng_df = get_lng_vessels()
        if lng_df is not None and len(lng_df) > 0:
            st.metric("LNG Vessels Expected", len(lng_df))
            st.markdown("---")
            st.markdown("#### LNG Vessel Arrivals")
            render_lng_vessel_table(lng_df)
        else:
            st.markdown('<div class="no-data"><h3>No LNG Vessels Found</h3><p>No LNG tankers are currently scheduled to arrive.</p></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
