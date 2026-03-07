"""
app.py — SG-REITs Analysis Dashboard
Run: streamlit run app.py
"""

import streamlit as st
import datetime

from utils import REITS_CONFIG
from data.loader import load_data
from ui.styles import CSS
from ui import tab_performance, tab_dcf, tab_sector, tab_correlation, tab_montecarlo, tab_backtesting, tab_optimizer

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SG-REITs Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏙️ SG-REITs")
    st.markdown("---")

    all_sectors = sorted({v["sector"] for v in REITS_CONFIG.values()})
    sel_sectors = st.multiselect("Sector Filter", options=all_sectors, default=all_sectors)

    st.markdown("---")
    min_yield  = st.slider("Min Dividend Yield (%)", 0.0, 10.0, 0.0, 0.5)
    min_sharpe = st.slider("Min Sharpe Ratio", -1.0, 3.0, 0.0, 0.1)

    st.markdown("---")
    st.selectbox("Benchmark", ["CLR.SI (STI ETF)", "ES3.SI (STI)"], index=0)

    st.markdown("---")
    if st.button("🔄  Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"<div style='font-size:0.72rem;color:#475569;margin-top:1rem'>"
        f"Last updated<br>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</div>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# Load + filter
# ─────────────────────────────────────────────
with st.spinner("📡 Fetching market data..."):
    df_all = load_data()

if df_all.empty or "Sector" not in df_all.columns:
    st.error("데이터를 불러오지 못했습니다. 네트워크 상태를 확인하거나 잠시 후 🔄 Refresh를 눌러주세요.")
    st.stop()

df = df_all[df_all["Sector"].isin(sel_sectors)].copy()
if min_yield > 0:
    df = df[df["Yield(%)"].fillna(0) >= min_yield]
if min_sharpe > 0:
    df = df[df["Sharpe"].fillna(-99) >= min_sharpe]

if df.empty:
    st.warning("선택한 필터 조건에 맞는 REIT가 없습니다. 필터를 조정해 주세요.")
    st.stop()

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown(f"""
<div class="dash-header">
    <div class="badge">Singapore Exchange · S-REIT Universe</div>
    <h1>SG-REITs Analysis Dashboard</h1>
    <p>Real-time performance, DCF valuation & NAV analysis · {len(df)} REITs · Data via Yahoo Finance</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────
avg_ret    = df["Return(%)"].mean()
avg_yield  = df["Yield(%)"].dropna().mean()
avg_sharpe = df["Sharpe"].mean()
n_underval = df[df["Upside(%)"].fillna(0) > 10].shape[0]

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card blue">
    <div class="kpi-label">Avg 1Y Return</div>
    <div class="kpi-value">{"+" if avg_ret>0 else ""}{avg_ret:.1f}%</div>
    <div class="kpi-sub">{len(df)} REITs tracked</div>
  </div>
  <div class="kpi-card green">
    <div class="kpi-label">Avg Dividend Yield</div>
    <div class="kpi-value">{avg_yield:.2f}%</div>
    <div class="kpi-sub">Trailing 12M</div>
  </div>
  <div class="kpi-card amber">
    <div class="kpi-label">Avg Sharpe Ratio</div>
    <div class="kpi-value">{avg_sharpe:.2f}</div>
    <div class="kpi-sub">Risk-free 2.5%</div>
  </div>
  <div class="kpi-card red">
    <div class="kpi-label">DCF Undervalued</div>
    <div class="kpi-value">{n_underval}</div>
    <div class="kpi-sub">Upside &gt; 10%</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈  Performance",
    "💰  DCF Valuation",
    "🗺️  Sector Analysis",
    "📊  Correlation",
    "🎲  Monte Carlo DCF",
    "⏱️  Backtesting",
    "⚖️  Portfolio Optimizer",
])

with tab1:
    tab_performance.render(df)

with tab2:
    tab_dcf.render(df)

with tab3:
    tab_sector.render(df)

with tab4:
    tab_correlation.render(df)

with tab5:
    tab_montecarlo.render(df)

with tab6:
    tab_backtesting.render(df)

with tab7:
    tab_optimizer.render(df)