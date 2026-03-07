"""
app.py — SG-REITs Analysis Dashboard
Run: streamlit run app.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import datetime
from dcf_valuation import calculate_wacc, dcf_reit, nav_discount_premium, monte_carlo_dcf
from backtesting import compute_dcf_signals, run_backtest, rolling_backtest

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SG-REITs Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

REITS_CONFIG = {
    "C38U.SI":   {"name": "CapitaLand Integrated",    "sector": "Retail/Office"},
    "A17U.SI":   {"name": "CapitaLand Ascendas",      "sector": "Industrial"},
    "N2IU.SI":   {"name": "Mapletree Pan Asia",        "sector": "Retail/Office"},
    "M44U.SI":   {"name": "Mapletree Logistics",       "sector": "Logistics"},
    "ME8U.SI":   {"name": "Mapletree Industrial",      "sector": "Industrial"},
    "BUOU.SI":   {"name": "Frasers Centrepoint",       "sector": "Retail/Office"},
    "AJBU.SI":   {"name": "Keppel DC REIT",            "sector": "Data Centre"},
    "J69U.SI":   {"name": "Frasers Logistics",         "sector": "Logistics"},
    "C2PU.SI":   {"name": "Parkway Life REIT",         "sector": "Healthcare"},
    "T82U.SI":   {"name": "Suntec REIT",               "sector": "Retail/Office"},
    "TS0U.SI":   {"name": "OUE REIT",                  "sector": "Hospitality"},
    "CY6U.SI":   {"name": "CapitaLand India Trust",    "sector": "Industrial"},
    "HMN.SI":   {"name": "Ascott Trust",              "sector": "Hospitality"},
    "JYEU.SI":  {"name": "Lendlease Global REIT",     "sector": "Retail/Office"},
    "ODBU.SI": {"name": "United Hampshire US REIT",  "sector": "Retail/Office"},
}

SECTOR_COLORS = {
    "Retail/Office": "#2563eb",
    "Industrial":    "#7c3aed",
    "Logistics":     "#059669",
    "Data Centre":   "#dc2626",
    "Hospitality":   "#d97706",
    "Healthcare":    "#0891b2",
}

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1b2a 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #c8d6e5 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #f0f4f8 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label { color: #94a3b8 !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; }

/* Main background */
.main .block-container { background: #f8fafc; padding-top: 1.5rem; }

/* Header */
.dash-header {
    background: linear-gradient(135deg, #0a0f1e 0%, #1a2744 60%, #0f3460 100%);
    border-radius: 16px;
    padding: 2.2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.dash-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%);
    border-radius: 50%;
}
.dash-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: #f0f4f8;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.01em;
}
.dash-header p { color: #94a3b8; font-size: 0.88rem; margin: 0; }
.dash-header .badge {
    display: inline-block;
    background: rgba(37,99,235,0.25);
    border: 1px solid rgba(37,99,235,0.5);
    color: #93c5fd;
    font-size: 0.72rem;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 0.6rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* KPI cards */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    position: relative;
    overflow: hidden;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    border-radius: 12px 0 0 12px;
}
.kpi-card.blue::after  { background: #2563eb; }
.kpi-card.green::after { background: #059669; }
.kpi-card.amber::after { background: #d97706; }
.kpi-card.red::after   { background: #dc2626; }
.kpi-label { font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.35rem; }
.kpi-value { font-size: 1.65rem; font-weight: 600; color: #0f172a; line-height: 1; }
.kpi-sub   { font-size: 0.78rem; color: #64748b; margin-top: 0.3rem; }

/* Section titles */
.section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.15rem;
    color: #0f172a;
    margin: 0 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e2e8f0;
}

/* Upside pill */
.pill-up   { background:#dcfce7; color:#166534; padding:2px 8px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.pill-down { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.pill-neu  { background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:20px; font-size:0.78rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Data loading (cached)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    rows = []
    bench = yf.Ticker("CLR.SI").history(period="1y")["Close"]
    bench_ret = bench.pct_change()

    for ticker, meta in REITS_CONFIG.items():
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            hist  = stock.history(period="1y")["Close"]

            # 가격 데이터 없으면 skip (사명변경·상장폐지 등)
            if hist.empty or len(hist) < 2:
                st.warning(f"{ticker} ({meta['name']}): 가격 데이터 없음 — 사명변경/상장폐지 확인 필요")
                continue

            ret   = hist.pct_change()
            combined = pd.concat([ret, bench_ret], axis=1).dropna()
            combined.columns = ["reit", "bench"]

            vol     = combined["reit"].std() * np.sqrt(252)
            cum_ret = hist.iloc[-1] / hist.iloc[0] - 1
            cov     = np.cov(combined["reit"], combined["bench"])
            beta    = cov[0,1] / cov[1,1] if cov[1,1] != 0 else 0
            sharpe  = (cum_ret - 0.03) / vol if vol != 0 else 0

            price = info.get("regularMarketPrice") or hist.iloc[-1]
            dpu   = info.get("trailingAnnualDividendRate")
            dyield= info.get("trailingAnnualDividendYield")
            nav   = info.get("bookValue")
            wacc  = calculate_wacc(beta)

            dcf_val = None
            if dpu and dpu > 0:
                dcf_val = dcf_reit(dpu, 0.03, wacc, years=10, perpetual_growth=0.025)

            nav_disc = nav_discount_premium(price, nav) if nav else None
            upside   = (dcf_val / price - 1) * 100 if dcf_val and price else None

            rows.append({
                "Ticker":      ticker,
                "Name":        meta["name"],
                "Sector":      meta["sector"],
                "Price":       round(price, 3),
                "DPU":         round(dpu, 4) if dpu else None,
                "Yield(%)":    round(dyield * 100, 2) if dyield else None,
                "Return(%)":   round(cum_ret * 100, 2),
                "Vol(%)":      round(vol * 100, 2),
                "Beta":        round(beta, 2),
                "Sharpe":      round(sharpe, 2),
                "WACC(%)":     round(wacc * 100, 2),
                "DCF Value":   dcf_val,
                "Upside(%)":   round(upside, 1) if upside is not None else None,
                "NAV/Unit":    round(nav, 3) if nav else None,
                "NAV Disc(%)": round(nav_disc, 1) if nav_disc is not None else None,
            })
        except Exception as e:
            st.warning(f"{ticker} 로드 실패: {e}")

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def load_price_history(tickers):
    result = {}
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period="1y")["Close"]
            result[t] = h
        except Exception:
            pass
    return result


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏙️ SG-REITs")
    st.markdown("---")

    all_sectors = sorted({v["sector"] for v in REITS_CONFIG.values()})
    sel_sectors = st.multiselect(
        "Sector Filter",
        options=all_sectors,
        default=all_sectors,
    )

    st.markdown("---")
    min_yield = st.slider("Min Dividend Yield (%)", 0.0, 10.0, 0.0, 0.5)
    min_sharpe = st.slider("Min Sharpe Ratio", -1.0, 3.0, 0.0, 0.1)

    st.markdown("---")
    benchmark = st.selectbox("Benchmark", ["CLR.SI (STI ETF)", "ES3.SI (STI)"], index=0)

    st.markdown("---")
    if st.button("🔄  Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(f"<div style='font-size:0.72rem;color:#475569;margin-top:1rem'>Last updated<br>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Load + filter
# ─────────────────────────────────────────────
with st.spinner("📡 Fetching market data..."):
    df_all = load_data()

# df_all이 비어있거나 Sector 컬럼이 없으면 안전하게 중단
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
# Tab layout
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈  Performance",
    "💰  DCF Valuation",
    "🗺️  Sector Analysis",
    "📊  Correlation",
    "🎲  Monte Carlo DCF",
    "⏱️  Backtesting",
])


# ══════════════════════════════════════════════
# TAB 1: Performance
# ══════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<p class="section-title">1Y Cumulative Return</p>', unsafe_allow_html=True)
        df_sorted = df.sort_values("Return(%)", ascending=True)
        colors = [SECTOR_COLORS.get(s, "#2563eb") for s in df_sorted["Sector"]]

        fig = go.Figure(go.Bar(
            x=df_sorted["Return(%)"],
            y=df_sorted["Name"],
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:+.1f}%" for v in df_sorted["Return(%)"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Return: %{x:.2f}%<extra></extra>",
        ))
        fig.add_vline(x=0, line_color="#94a3b8", line_width=1)
        fig.update_layout(
            height=420, margin=dict(l=0,r=60,t=10,b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                       ticksuffix="%", title=None),
            yaxis=dict(showgrid=False, title=None, tickfont=dict(size=11)),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">Risk vs Return</p>', unsafe_allow_html=True)
        fig2 = px.scatter(
            df.dropna(subset=["Vol(%)", "Return(%)"]),
            x="Vol(%)", y="Return(%)",
            color="Sector",
            size=[14]*len(df.dropna(subset=["Vol(%)", "Return(%)"])),
            text="Ticker",
            color_discrete_map=SECTOR_COLORS,
            hover_data={"Name": True, "Sharpe": True},
        )
        fig2.update_traces(textposition="top center", textfont_size=9,
                           marker=dict(line=dict(width=1, color="white")))
        fig2.update_layout(
            height=420, margin=dict(l=0,r=0,t=10,b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%", title="Volatility (%)"),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%", title="Return (%)"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, x=0),
            font=dict(family="DM Sans"),
        )
        fig2.add_hline(y=0, line_dash="dot", line_color="#94a3b8", line_width=1)
        st.plotly_chart(fig2, use_container_width=True)

    # Price history chart
    st.markdown('<p class="section-title">Price History (Normalized, 1Y)</p>', unsafe_allow_html=True)
    selected = st.multiselect(
        "Select REITs to compare",
        options=list(df["Ticker"]),
        default=list(df["Ticker"])[:5],
        format_func=lambda t: f"{t} — {REITS_CONFIG[t]['name']}",
    )
    if selected:
        with st.spinner("Loading price history..."):
            hist_data = load_price_history(selected)
        fig3 = go.Figure()
        for ticker, prices in hist_data.items():
            norm = prices / prices.iloc[0] * 100
            name = REITS_CONFIG.get(ticker, {}).get("name", ticker)
            fig3.add_trace(go.Scatter(
                x=norm.index, y=norm.values,
                name=f"{ticker}",
                mode="lines",
                hovertemplate=f"<b>{name}</b><br>%{{x|%Y-%m-%d}}<br>Idx: %{{y:.1f}}<extra></extra>",
                line=dict(width=1.8),
            ))
        fig3.add_hline(y=100, line_dash="dot", line_color="#94a3b8", line_width=1)
        fig3.update_layout(
            height=340, margin=dict(l=0,r=0,t=10,b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Normalized (Base=100)"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0, font=dict(size=10)),
            font=dict(family="DM Sans"),
            hovermode="x unified",
        )
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 2: DCF Valuation
# ══════════════════════════════════════════════
with tab2:
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown('<p class="section-title">DCF Upside vs Current Price</p>', unsafe_allow_html=True)
        dcf_df = df[df["DCF Value"].notna()].sort_values("Upside(%)", ascending=False)

        if not dcf_df.empty:
            bar_colors = ["#059669" if u >= 0 else "#dc2626" for u in dcf_df["Upside(%)"]]
            fig4 = go.Figure(go.Bar(
                x=dcf_df["Upside(%)"],
                y=dcf_df["Name"],
                orientation="h",
                marker=dict(color=bar_colors, opacity=0.85),
                text=[f"{v:+.1f}%" for v in dcf_df["Upside(%)"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>DCF Upside: %{x:.1f}%<extra></extra>",
            ))
            fig4.add_vline(x=0, line_color="#94a3b8", line_width=1.5)
            fig4.update_layout(
                height=400, margin=dict(l=0,r=60,t=10,b=10),
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%", title=None),
                yaxis=dict(showgrid=False, title=None, tickfont=dict(size=11)),
                font=dict(family="DM Sans"),
            )
            st.plotly_chart(fig4, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">Valuation Table</p>', unsafe_allow_html=True)

        def upside_pill(v):
            if pd.isna(v) or v is None:
                return '<span class="pill-neu">N/A</span>'
            if v >= 10:
                return f'<span class="pill-up">▲ {v:.1f}%</span>'
            elif v <= -10:
                return f'<span class="pill-down">▼ {v:.1f}%</span>'
            return f'<span class="pill-neu">{v:+.1f}%</span>'

        def nav_pill(v):
            if pd.isna(v) or v is None:
                return '<span class="pill-neu">N/A</span>'
            if v < -10:
                return f'<span class="pill-up">{v:.1f}%</span>'   # deep discount = cheap
            elif v > 10:
                return f'<span class="pill-down">+{v:.1f}%</span>'
            return f'<span class="pill-neu">{v:+.1f}%</span>'

        html_rows = ""
        for _, r in df.sort_values("Upside(%)", ascending=False, na_position="last").iterrows():
            dcf_str = f"${r['DCF Value']:.3f}" if pd.notna(r.get("DCF Value")) else "N/A"
            price_str = f"${r['Price']:.3f}" if pd.notna(r.get("Price")) else "N/A"
            wacc_str  = f"{r['WACC(%)']:.2f}%" if pd.notna(r.get("WACC(%)")) else "N/A"
            dpu_str   = f"${r['DPU']:.4f}" if pd.notna(r.get("DPU")) else "N/A"
            html_rows += f"""
            <tr>
              <td style="font-weight:600;color:#0f172a">{r['Ticker']}</td>
              <td style="color:#475569;font-size:0.82rem">{r['Name']}</td>
              <td>{price_str}</td>
              <td>{dpu_str}</td>
              <td>{wacc_str}</td>
              <td style="font-weight:600">{dcf_str}</td>
              <td>{upside_pill(r.get('Upside(%)'))}</td>
              <td>{nav_pill(r.get('NAV Disc(%)'))}</td>
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:0.83rem;font-family:DM Sans,sans-serif">
          <thead>
            <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0">
              <th style="padding:8px 10px;text-align:left;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">Ticker</th>
              <th style="padding:8px 10px;text-align:left;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">Name</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">Price</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">DPU</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">WACC</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">DCF Value</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">Upside</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">NAV Disc</th>
            </tr>
          </thead>
          <tbody>{html_rows}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

    # DCF assumptions note
    st.markdown("""
    <div style="margin-top:1rem;padding:0.9rem 1.2rem;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;font-size:0.78rem;color:#64748b">
    <b>DCF Assumptions</b> &nbsp;·&nbsp;
    Risk-free rate: 2.5% &nbsp;·&nbsp;
    Market risk premium: 6.0% &nbsp;·&nbsp;
    DPU growth: 3.0% p.a. &nbsp;·&nbsp;
    Perpetual growth: 2.5% &nbsp;·&nbsp;
    Projection: 10 years &nbsp;·&nbsp;
    NAV proxy: Book value per share (Yahoo Finance)
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 3: Sector Analysis
# ══════════════════════════════════════════════
with tab3:

    # ── 섹터 집계 ─────────────────────────────────
    sec_agg = df.groupby("Sector").agg(
        Avg_Return  = ("Return(%)", "mean"),
        Avg_Yield   = ("Yield(%)", "mean"),
        Avg_Sharpe  = ("Sharpe", "mean"),
        Avg_Beta    = ("Beta", "mean"),
        Avg_Vol     = ("Vol(%)", "mean"),
        Avg_Upside  = ("Upside(%)", "mean"),
        Count       = ("Ticker", "count"),
    ).round(2).reset_index()

    # ── 행 1: 도넛 + 레이더 ───────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-title">섹터 구성 (종목 수)</p>', unsafe_allow_html=True)
        sector_counts = df.groupby("Sector").size().reset_index(name="Count")
        fig5 = px.pie(
            sector_counts, names="Sector", values="Count",
            color="Sector", color_discrete_map=SECTOR_COLORS,
            hole=0.55,
        )
        fig5.update_traces(
            textposition="outside", textinfo="label+value",
            textfont_size=11, pull=[0.03]*len(sector_counts),
        )
        fig5.update_layout(
            height=340, margin=dict(l=20,r=20,t=20,b=20),
            showlegend=False, paper_bgcolor="white",
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">섹터 레이더 차트 (다차원 비교)</p>', unsafe_allow_html=True)

        # 0~1 정규화 (레이더용)
        radar_metrics = ["Avg_Return","Avg_Yield","Avg_Sharpe","Avg_Upside"]
        radar_labels  = ["Return","Yield","Sharpe","DCF Upside"]
        radar_df = sec_agg[["Sector"] + radar_metrics].copy()
        for m in radar_metrics:
            mn, mx = radar_df[m].min(), radar_df[m].max()
            radar_df[m] = (radar_df[m] - mn) / (mx - mn + 1e-9)

        def hex_to_rgba(hex_color, alpha=0.15):
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"

        fig_radar = go.Figure()
        for _, row in radar_df.iterrows():
            vals = [row[m] for m in radar_metrics]
            vals += [vals[0]]  # 닫기
            sector_color = SECTOR_COLORS.get(row["Sector"], "#94a3b8")
            fig_radar.add_trace(go.Scatterpolar(
                r=vals,
                theta=radar_labels + [radar_labels[0]],
                fill="toself",
                name=row["Sector"],
                line=dict(color=sector_color, width=2),
                fillcolor=hex_to_rgba(sector_color, alpha=0.15),
                opacity=0.85,
            ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0,1], tickfont=dict(size=8), showticklabels=False),
                angularaxis=dict(tickfont=dict(size=11)),
                bgcolor="white",
            ),
            height=340, margin=dict(l=30,r=30,t=20,b=20),
            paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, x=0, font=dict(size=10)),
            font=dict(family="DM Sans"),
            showlegend=True,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── 행 2: 섹터별 Sharpe vs Yield 버블 차트 ────
    st.markdown('<p class="section-title">섹터별 Sharpe vs Yield (버블 = 평균 Return 크기)</p>', unsafe_allow_html=True)

    bubble_df = sec_agg.copy()
    bubble_df["bubble_size"] = bubble_df["Avg_Return"].clip(lower=1) * 4

    fig_bubble = go.Figure()
    for _, row in bubble_df.iterrows():
        fig_bubble.add_trace(go.Scatter(
            x=[row["Avg_Yield"]],
            y=[row["Avg_Sharpe"]],
            mode="markers+text",
            name=row["Sector"],
            text=[row["Sector"]],
            textposition="top center",
            textfont=dict(size=10),
            marker=dict(
                size=max(row["bubble_size"], 12),
                color=SECTOR_COLORS.get(row["Sector"], "#94a3b8"),
                opacity=0.82,
                line=dict(width=1.5, color="white"),
            ),
            hovertemplate=(
                f"<b>{row['Sector']}</b><br>"
                f"Avg Yield: {row['Avg_Yield']:.2f}%<br>"
                f"Avg Sharpe: {row['Avg_Sharpe']:.2f}<br>"
                f"Avg Return: {row['Avg_Return']:.2f}%<br>"
                f"# REITs: {int(row['Count'])}<extra></extra>"
            ),
        ))
    fig_bubble.add_hline(y=0, line_dash="dot", line_color="#94a3b8", line_width=1)
    fig_bubble.update_layout(
        height=340,
        margin=dict(l=0,r=0,t=10,b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(title="Avg Dividend Yield (%)", showgrid=True, gridcolor="#f1f5f9", ticksuffix="%"),
        yaxis=dict(title="Avg Sharpe Ratio", showgrid=True, gridcolor="#f1f5f9"),
        showlegend=False,
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_bubble, use_container_width=True)

    # ── 행 3: 섹터별 종목 상세 카드 ──────────────
    st.markdown('<p class="section-title">섹터별 종목 상세</p>', unsafe_allow_html=True)

    sector_list = sorted(df["Sector"].unique())
    tabs_sector = st.tabs(sector_list)

    for tab_s, sector_name in zip(tabs_sector, sector_list):
        with tab_s:
            sector_df = df[df["Sector"] == sector_name].sort_values("Sharpe", ascending=False)
            s_color   = SECTOR_COLORS.get(sector_name, "#64748b")

            cards_html = ""
            for _, r in sector_df.iterrows():
                ret_color  = "#059669" if r["Return(%)"] >= 0 else "#dc2626"
                up_val     = r.get("Upside(%)")
                up_str     = f"{up_val:+.1f}%" if pd.notna(up_val) and up_val is not None else "N/A"
                up_color   = "#059669" if (pd.notna(up_val) and up_val and up_val >= 0) else "#dc2626"
                yield_str  = f"{r['Yield(%)']:.2f}%" if pd.notna(r.get("Yield(%)")) else "N/A"

                cards_html += f"""
                <div style="display:inline-block;width:calc(20% - 12px);min-width:160px;
                            margin:0 6px 12px 0;padding:1rem;background:white;
                            border-radius:12px;border:1px solid #e2e8f0;
                            border-top:3px solid {s_color};vertical-align:top;
                            box-shadow:0 1px 3px rgba(0,0,0,0.05)">
                  <div style="font-size:0.72rem;color:#94a3b8;margin-bottom:2px">{r['Ticker']}</div>
                  <div style="font-size:0.88rem;font-weight:700;color:#0f172a;margin-bottom:8px;
                              line-height:1.2">{r['Name']}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:0.78rem">
                    <div><span style="color:#94a3b8">Return</span><br>
                      <b style="color:{ret_color}">{r['Return(%)']}%</b></div>
                    <div><span style="color:#94a3b8">Yield</span><br>
                      <b style="color:#0f172a">{yield_str}</b></div>
                    <div><span style="color:#94a3b8">Sharpe</span><br>
                      <b style="color:#0f172a">{r['Sharpe']}</b></div>
                    <div><span style="color:#94a3b8">DCF↑</span><br>
                      <b style="color:{up_color}">{up_str}</b></div>
                  </div>
                </div>"""

            st.markdown(f'<div style="line-height:1">{cards_html}</div>', unsafe_allow_html=True)

    # ── 행 4: 섹터 요약 테이블 ───────────────────
    st.markdown('<p class="section-title">섹터 요약 테이블</p>', unsafe_allow_html=True)
    st.dataframe(
        sec_agg.rename(columns={
            "Avg_Return":  "Avg Return (%)",
            "Avg_Yield":   "Avg Yield (%)",
            "Avg_Sharpe":  "Avg Sharpe",
            "Avg_Beta":    "Avg Beta",
            "Avg_Vol":     "Avg Vol (%)",
            "Avg_Upside":  "Avg DCF Upside (%)",
            "Count":       "# REITs",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ══════════════════════════════════════════════
# TAB 4: Correlation
# ══════════════════════════════════════════════
with tab4:

    with st.spinner("수익률 상관계수 계산 중..."):
        tickers  = list(df["Ticker"])
        hist_all = load_price_history(tickers)

        # 섹터 레이블 포함 이름 매핑
        name_map = {
            t: f"{REITS_CONFIG[t]['name'][:13]}"
            for t in tickers if t in hist_all
        }
        price_df = pd.DataFrame({
            name_map[t]: h
            for t, h in hist_all.items() if t in name_map
        }).dropna(how="all").fillna(method="ffill").dropna()

        ret_df = price_df.pct_change().dropna()
        corr   = ret_df.corr()

        # 섹터 순서로 정렬 (같은 섹터끼리 모이게)
        ticker_sector = {
            REITS_CONFIG[t]["name"][:13]: REITS_CONFIG[t]["sector"]
            for t in tickers if t in hist_all
        }
        sorted_names = sorted(
            corr.columns,
            key=lambda n: (ticker_sector.get(n, "Z"), n)
        )
        corr = corr.loc[sorted_names, sorted_names]

    # ── 히트맵 ────────────────────────────────────
    col_heat, col_info = st.columns([3, 1])

    with col_heat:
        st.markdown('<p class="section-title">수익률 상관계수 매트릭스 (섹터 기준 정렬)</p>', unsafe_allow_html=True)

        # 섹터 경계선 위치 계산
        sector_boundaries = []
        prev_sector = None
        for i, name in enumerate(corr.columns):
            sec = ticker_sector.get(name, "")
            if sec != prev_sector and i > 0:
                sector_boundaries.append(i - 0.5)
            prev_sector = sec

        fig7 = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale=[
                [0.0,  "#dc2626"],
                [0.35, "#fca5a5"],
                [0.5,  "#f8fafc"],
                [0.65, "#93c5fd"],
                [1.0,  "#1d4ed8"],
            ],
            zmin=-1, zmax=1,
            text=np.round(corr.values, 2),
            texttemplate="%{text}",
            textfont=dict(size=8.5),
            hoverongaps=False,
            colorbar=dict(
                title=dict(text="Corr", side="right"),
                thickness=14,
                tickvals=[-1, -0.5, 0, 0.5, 1],
            ),
        ))

        # 섹터 경계선 추가
        for b in sector_boundaries:
            fig7.add_shape(type="line", x0=b, x1=b, y0=-0.5, y1=len(corr)-0.5,
                           line=dict(color="#1e293b", width=1.5))
            fig7.add_shape(type="line", y0=b, y1=b, x0=-0.5, x1=len(corr)-0.5,
                           line=dict(color="#1e293b", width=1.5))

        fig7.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="white",
            xaxis=dict(tickfont=dict(size=9), tickangle=-40, side="bottom"),
            yaxis=dict(tickfont=dict(size=9), autorange="reversed"),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig7, use_container_width=True)

    # ── 분산 효과 추천 페어 ───────────────────────
    with col_info:
        st.markdown('<p class="section-title">📌 낮은 상관 페어 TOP 5</p>', unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.75rem;color:#94a3b8;margin-bottom:0.7rem'>"
            "포트폴리오 분산 효과가 큰 종목 조합</div>",
            unsafe_allow_html=True
        )

        # 상삼각 행렬에서 페어 추출
        pairs = []
        cols_ = corr.columns.tolist()
        for i in range(len(cols_)):
            for j in range(i+1, len(cols_)):
                pairs.append((cols_[i], cols_[j], corr.iloc[i, j]))

        pairs_df = pd.DataFrame(pairs, columns=["A","B","Corr"]).sort_values("Corr")

        for _, pr in pairs_df.head(5).iterrows():
            c_val  = pr["Corr"]
            c_color = "#059669" if c_val < 0.3 else "#d97706"
            st.markdown(f"""
            <div style="padding:0.65rem 0.8rem;margin-bottom:0.5rem;background:white;
                        border-radius:10px;border:1px solid #e2e8f0;
                        border-left:3px solid {c_color}">
              <div style="font-size:0.75rem;font-weight:700;color:#0f172a">{pr['A']}</div>
              <div style="font-size:0.7rem;color:#94a3b8;margin:1px 0">+ {pr['B']}</div>
              <div style="font-size:1rem;font-weight:800;color:{c_color}">{c_val:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<p class="section-title" style="margin-top:1rem">📌 높은 상관 페어 TOP 5</p>', unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.75rem;color:#94a3b8;margin-bottom:0.7rem'>"
            "중복 보유 시 분산 효과 낮은 조합</div>",
            unsafe_allow_html=True
        )
        for _, pr in pairs_df[pairs_df["Corr"] < 1.0].tail(5).iloc[::-1].iterrows():
            c_val   = pr["Corr"]
            c_color = "#dc2626"
            st.markdown(f"""
            <div style="padding:0.65rem 0.8rem;margin-bottom:0.5rem;background:white;
                        border-radius:10px;border:1px solid #e2e8f0;
                        border-left:3px solid {c_color}">
              <div style="font-size:0.75rem;font-weight:700;color:#0f172a">{pr['A']}</div>
              <div style="font-size:0.7rem;color:#94a3b8;margin:1px 0">+ {pr['B']}</div>
              <div style="font-size:1rem;font-weight:800;color:{c_color}">{c_val:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── 섹터 간 평균 상관계수 히트맵 ─────────────
    st.markdown('<p class="section-title">섹터 간 평균 상관계수</p>', unsafe_allow_html=True)

    sec_corr_data = {}
    for t1 in tickers:
        if t1 not in hist_all:
            continue
        n1  = name_map[t1]
        s1  = REITS_CONFIG[t1]["sector"]
        for t2 in tickers:
            if t2 not in hist_all or t1 == t2:
                continue
            n2 = name_map[t2]
            s2 = REITS_CONFIG[t2]["sector"]
            if n1 in corr.index and n2 in corr.columns:
                sec_corr_data.setdefault((s1, s2), []).append(corr.loc[n1, n2])

    sectors_u = sorted(set(REITS_CONFIG[t]["sector"] for t in tickers))
    sec_matrix = pd.DataFrame(index=sectors_u, columns=sectors_u, dtype=float)
    for (s1, s2), vals in sec_corr_data.items():
        sec_matrix.loc[s1, s2] = round(np.mean(vals), 3)
    np.fill_diagonal(sec_matrix.values, 1.0)

    fig_sec = go.Figure(go.Heatmap(
        z=sec_matrix.values.astype(float),
        x=sec_matrix.columns.tolist(),
        y=sec_matrix.index.tolist(),
        colorscale=[
            [0.0, "#f8fafc"], [0.5, "#93c5fd"], [1.0, "#1d4ed8"]
        ],
        zmin=0, zmax=1,
        text=np.round(sec_matrix.values.astype(float), 2),
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        colorbar=dict(thickness=12, title=dict(text="Avg Corr")),
    ))
    fig_sec.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="white",
        xaxis=dict(tickfont=dict(size=10.5)),
        yaxis=dict(tickfont=dict(size=10.5), autorange="reversed"),
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_sec, use_container_width=True)

    st.markdown("""
    <div style="padding:0.9rem 1.2rem;background:#f8fafc;border:1px solid #e2e8f0;
                border-radius:10px;font-size:0.78rem;color:#64748b;line-height:1.8">
      <b>읽는 법</b> &nbsp;·&nbsp;
      <span style="color:#1d4ed8;font-weight:600">짙은 파랑 (1.0)</span> = 완전 양의 상관 &nbsp;·&nbsp;
      <span style="color:#64748b;font-weight:600">흰색 (0)</span> = 무상관 &nbsp;·&nbsp;
      섹터 경계선(실선)은 같은 섹터 클러스터를 나타냅니다. &nbsp;·&nbsp;
      <b>분산 투자</b>: 낮은 상관 페어 조합으로 변동성을 낮추고 위험 조정 수익률을 높일 수 있습니다.
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 5: Monte Carlo DCF
# ══════════════════════════════════════════════
with tab5:

    st.markdown('<p class="section-title">Monte Carlo DCF 시뮬레이션</p>', unsafe_allow_html=True)

    # ── 컨트롤 패널 ───────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    with ctrl1:
        mc_ticker = st.selectbox(
            "분석할 REIT 선택",
            options=list(df["Ticker"]),
            format_func=lambda t: f"{t}  —  {REITS_CONFIG[t]['name']}",
        )
    with ctrl2:
        n_sims = st.select_slider(
            "시뮬레이션 횟수",
            options=[1000, 3000, 5000, 10000, 20000],
            value=10000,
        )
    with ctrl3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_mc = st.button("▶  Run Simulation", use_container_width=True, type="primary")

    st.markdown("---")

    # ── 파라미터 조정 expander ────────────────────
    with st.expander("⚙️  파라미터 직접 조정 (고급)", expanded=False):
        p1, p2, p3, p4, p5 = st.columns(5)
        with p1:
            g_mean = st.number_input("성장률 평균 (%)", value=3.0, step=0.5) / 100
            g_std  = st.number_input("성장률 표준편차 (%)", value=1.0, step=0.5) / 100
        with p2:
            w_std  = st.number_input("WACC 노이즈 σ (%)", value=0.5, step=0.1) / 100
        with p3:
            pg_mean = st.number_input("영구성장률 평균 (%)", value=2.5, step=0.5) / 100
            pg_std  = st.number_input("영구성장률 σ (%)", value=0.5, step=0.1) / 100
        with p4:
            sim_years = st.number_input("예측 기간 (년)", value=10, min_value=5, max_value=30, step=1)
        with p5:
            rand_seed = st.number_input("랜덤 시드", value=42, step=1)

    # ── 시뮬레이션 실행 ───────────────────────────
    row = df[df["Ticker"] == mc_ticker].iloc[0]
    dpu_val  = row.get("DPU")
    beta_val = row.get("Beta")
    cur_price = row.get("Price")

    # 데이터 없으면 안내
    if not dpu_val or pd.isna(dpu_val):
        st.warning(f"**{mc_ticker}**: DPU 데이터가 없어 시뮬레이션을 실행할 수 없습니다.")
    else:
        # 세션 상태로 결과 캐싱 (같은 파라미터면 재계산 안 함)
        cache_key = f"mc_{mc_ticker}_{n_sims}_{g_mean}_{g_std}_{w_std}_{pg_mean}_{pg_std}_{sim_years}_{rand_seed}"
        if run_mc or ("mc_cache_key" not in st.session_state) or (st.session_state.get("mc_cache_key") != cache_key):
            with st.spinner(f"🎲 {n_sims:,}회 시뮬레이션 중..."):
                mc_result = monte_carlo_dcf(
                    dpu_current = dpu_val,
                    beta        = beta_val,
                    n           = n_sims,
                    years       = sim_years,
                    growth_mean = g_mean,
                    growth_std  = g_std,
                    wacc_std    = w_std,
                    pg_mean     = pg_mean,
                    pg_std      = pg_std,
                    seed        = int(rand_seed),
                )
                st.session_state["mc_cache_key"] = cache_key
                st.session_state["mc_result"]    = mc_result
        else:
            mc_result = st.session_state.get("mc_result", {})

        if not mc_result:
            st.error("시뮬레이션 결과가 없습니다. 파라미터를 확인해 주세요.")
        else:
            p10 = mc_result["p10"]
            p50 = mc_result["p50"]
            p90 = mc_result["p90"]
            mean_val = mc_result["mean"]
            std_val  = mc_result["std"]
            n_valid  = mc_result["n_valid"]
            values   = mc_result["values"]
            params   = mc_result["params"]

            # ── KPI 결과 카드 ─────────────────────────
            k1, k2, k3, k4, k5 = st.columns(5)

            def upside_color(v, price):
                if price is None or pd.isna(price):
                    return "#64748b"
                pct = (v / price - 1) * 100
                return "#059669" if pct >= 0 else "#dc2626"

            def upside_str(v, price):
                if price is None or pd.isna(price):
                    return ""
                pct = (v / price - 1) * 100
                return f"({'▲' if pct>=0 else '▼'} {abs(pct):.1f}% vs price)"

            for col, label, val, color_cls in [
                (k1, "P10 (Bear)", p10, "red"),
                (k2, "P50 (Base)", p50, "blue"),
                (k3, "P90 (Bull)", p90, "green"),
                (k4, "Mean",  mean_val, "amber"),
                (k5, "Std Dev", std_val, "amber"),
            ]:
                with col:
                    sub = upside_str(val, cur_price) if label != "Std Dev" else f"{n_valid:,} valid runs"
                    st.markdown(f"""
                    <div class="kpi-card {color_cls}" style="padding:0.9rem 1rem">
                      <div class="kpi-label">{label}</div>
                      <div class="kpi-value" style="font-size:1.35rem">${val:.3f}</div>
                      <div class="kpi-sub">{sub}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

            # ── 히스토그램 + 현재가 + percentile 선 ──
            col_chart, col_info = st.columns([3, 1])

            with col_chart:
                st.markdown('<p class="section-title">내재가치 분포 (히스토그램)</p>', unsafe_allow_html=True)

                fig_mc = go.Figure()

                # 히스토그램
                fig_mc.add_trace(go.Histogram(
                    x=values,
                    nbinsx=80,
                    marker=dict(
                        color="rgba(37,99,235,0.55)",
                        line=dict(color="rgba(37,99,235,0.8)", width=0.3),
                    ),
                    name="Simulation",
                    hovertemplate="Value: $%{x:.3f}<br>Count: %{y}<extra></extra>",
                ))

                # Percentile 수직선
                for pval, plabel, pcolor in [
                    (p10, "P10 Bear", "#dc2626"),
                    (p50, "P50 Base", "#2563eb"),
                    (p90, "P90 Bull", "#059669"),
                ]:
                    fig_mc.add_vline(
                        x=pval,
                        line=dict(color=pcolor, width=2, dash="dash"),
                        annotation=dict(
                            text=f"<b>{plabel}</b><br>${pval:.3f}",
                            font=dict(size=10, color=pcolor),
                            bgcolor="white",
                            bordercolor=pcolor,
                            borderwidth=1,
                        ),
                        annotation_position="top",
                    )

                # 현재가 수직선
                if cur_price and not pd.isna(cur_price):
                    fig_mc.add_vline(
                        x=cur_price,
                        line=dict(color="#f59e0b", width=2.5),
                        annotation=dict(
                            text=f"<b>Current</b><br>${cur_price:.3f}",
                            font=dict(size=10, color="#92400e"),
                            bgcolor="#fef3c7",
                            bordercolor="#f59e0b",
                            borderwidth=1,
                        ),
                        annotation_position="top right",
                    )

                fig_mc.update_layout(
                    height=380,
                    margin=dict(l=0, r=0, t=40, b=10),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    xaxis=dict(
                        title="Intrinsic Value (SGD)",
                        showgrid=True, gridcolor="#f1f5f9",
                        tickprefix="$",
                    ),
                    yaxis=dict(
                        title="Frequency",
                        showgrid=True, gridcolor="#f1f5f9",
                    ),
                    showlegend=False,
                    font=dict(family="DM Sans"),
                )
                st.plotly_chart(fig_mc, use_container_width=True)

            # ── 시나리오 해석 패널 ────────────────────
            with col_info:
                st.markdown('<p class="section-title">시나리오 해석</p>', unsafe_allow_html=True)

                def interp_vs_price(pval, price, label):
                    if price is None or pd.isna(price):
                        return ""
                    pct = (pval / price - 1) * 100
                    if pct >= 10:
                        color, icon = "#059669", "▲"
                    elif pct <= -10:
                        color, icon = "#dc2626", "▼"
                    else:
                        color, icon = "#d97706", "→"
                    return f"""
                    <div style="padding:0.7rem 0.9rem;margin-bottom:0.6rem;
                                border-radius:10px;border:1px solid #e2e8f0;background:white">
                      <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                                  letter-spacing:0.07em;margin-bottom:4px">{label}</div>
                      <div style="font-size:1.1rem;font-weight:700;color:#0f172a">${pval:.3f}</div>
                      <div style="font-size:0.8rem;font-weight:600;color:{color}">
                        {icon} {abs(pct):.1f}% {'upside' if pct>=0 else 'downside'}
                      </div>
                    </div>"""

                prob_above = (values > cur_price).mean() * 100 if cur_price else None

                st.markdown(
                    interp_vs_price(p10, cur_price, "🐻 Bear (P10)") +
                    interp_vs_price(p50, cur_price, "⚖️ Base (P50)") +
                    interp_vs_price(p90, cur_price, "🐂 Bull (P90)"),
                    unsafe_allow_html=True,
                )

                if prob_above is not None:
                    bar_color = "#059669" if prob_above >= 50 else "#dc2626"
                    st.markdown(f"""
                    <div style="padding:0.7rem 0.9rem;border-radius:10px;
                                border:1px solid #e2e8f0;background:white;margin-top:0.4rem">
                      <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                                  letter-spacing:0.07em;margin-bottom:6px">현재가 상회 확률</div>
                      <div style="font-size:1.4rem;font-weight:700;color:{bar_color}">{prob_above:.1f}%</div>
                      <div style="background:#e2e8f0;border-radius:4px;height:6px;margin-top:6px">
                        <div style="background:{bar_color};width:{prob_above:.1f}%;
                                    height:6px;border-radius:4px"></div>
                      </div>
                      <div style="font-size:0.73rem;color:#64748b;margin-top:4px">
                        {n_valid:,}회 중 {int(n_valid*prob_above/100):,}회
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            # ── 파라미터 가정 요약 ────────────────────
            st.markdown(f"""
            <div style="margin-top:1rem;padding:0.9rem 1.2rem;background:#f8fafc;
                        border:1px solid #e2e8f0;border-radius:10px;
                        font-size:0.78rem;color:#64748b;line-height:1.8">
              <b>시뮬레이션 파라미터</b> &nbsp;·&nbsp;
              유효 실행: <b>{n_valid:,}/{n_sims:,}회</b> &nbsp;·&nbsp;
              Base WACC: <b>{params['base_wacc']:.2%}</b> &nbsp;·&nbsp;
              성장률: <b>N({g_mean:.1%}, {g_std:.1%})</b> &nbsp;·&nbsp;
              WACC 노이즈: <b>σ={w_std:.1%}</b> &nbsp;·&nbsp;
              영구성장률: <b>N({pg_mean:.1%}, {pg_std:.1%})</b> &nbsp;·&nbsp;
              예측기간: <b>{sim_years}Y</b>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 6: Backtesting
# ══════════════════════════════════════════════
with tab6:
    st.markdown('<p class="section-title">DCF 신호 백테스팅 — "업사이드 신호가 실제로 유효했는가?"</p>', unsafe_allow_html=True)

    # ── 컨트롤 패널 ───────────────────────────────
    bc1, bc2, bc3, bc4 = st.columns([2, 2, 1, 1])
    with bc1:
        bt_entry = st.date_input(
            "Entry Date (매수 시점)",
            value=datetime.date(2024, 1, 2),
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date.today() - datetime.timedelta(days=30),
        )
    with bc2:
        bt_exit = st.date_input(
            "Exit Date (청산 시점)",
            value=datetime.date(2024, 12, 31),
            min_value=datetime.date(2020, 6, 1),
            max_value=datetime.date.today(),
        )
    with bc3:
        bt_threshold = st.number_input(
            "매수 신호 기준 Upside (%)",
            min_value=0, max_value=50, value=10, step=5,
        )
    with bc4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_bt = st.button("▶  Run Backtest", use_container_width=True, type="primary")

    # ── 롤링 백테스팅 옵션 ─────────────────────────
    with st.expander("📅  롤링 백테스팅 (여러 기간 동시 검증)", expanded=False):
        st.markdown("""
        <div style="font-size:0.82rem;color:#64748b;margin-bottom:0.8rem">
        아래 기간들을 한꺼번에 백테스팅해 전략의 <b>일관성</b>을 검증합니다.
        기간이 많을수록 데이터 요청이 많아 시간이 걸립니다.
        </div>
        """, unsafe_allow_html=True)

        default_periods = [
            ("2022-01-03", "2022-12-30", "2022 Full Year"),
            ("2023-01-02", "2023-12-29", "2023 Full Year"),
            ("2024-01-02", "2024-12-31", "2024 Full Year"),
            ("2023-07-03", "2024-06-28", "2023H2~2024H1"),
        ]
        run_rolling = st.button("▶  Run Rolling Backtest (전체 기간)", use_container_width=False)

    st.markdown("---")

    # ── 단일 백테스트 실행 ────────────────────────
    if run_bt or st.session_state.get("bt_ran"):
        entry_dt = pd.Timestamp(bt_entry)
        exit_dt  = pd.Timestamp(bt_exit)

        if entry_dt >= exit_dt:
            st.error("Entry Date가 Exit Date보다 앞이어야 합니다.")
        else:
            bt_cache_key = f"bt_{bt_entry}_{bt_exit}_{bt_threshold}"
            if run_bt or st.session_state.get("bt_cache_key") != bt_cache_key:
                with st.spinner("📡 과거 데이터 수집 + DCF 신호 계산 중... (약 30~60초 소요)"):
                    bt_signals = compute_dcf_signals(
                        {k: v for k, v in REITS_CONFIG.items()},
                        entry_dt,
                        upside_threshold=bt_threshold / 100,
                    )
                with st.spinner("📊 백테스팅 수익률 계산 중..."):
                    bt_result = run_backtest(bt_signals, entry_dt, exit_dt)

                st.session_state["bt_cache_key"] = bt_cache_key
                st.session_state["bt_signals"]   = bt_signals
                st.session_state["bt_result"]    = bt_result
                st.session_state["bt_ran"]       = True
            else:
                bt_signals = st.session_state["bt_signals"]
                bt_result  = st.session_state["bt_result"]

            port_ret  = bt_result["portfolio_return"]
            bench_ret = bt_result["benchmark_return"]
            alpha     = bt_result["alpha"]
            n_long    = bt_result["n_long"]
            n_total   = bt_result["n_total"]
            sharpe    = bt_result["sharpe"]
            mdd       = bt_result["max_drawdown"]

            # ── 결과 KPI ─────────────────────────────
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            kpi_data = [
                (k1, "Portfolio Return",  f"{port_ret:+.2f}%",  "blue",  f"DCF Signal Long"),
                (k2, "Benchmark Return",  f"{bench_ret:+.2f}%", "amber", "CLR.SI (STI ETF)"),
                (k3, "Alpha",             f"{alpha:+.2f}%",     "green" if alpha >= 0 else "red",
                                                                          "초과수익"),
                (k4, "Sharpe Ratio",      f"{sharpe:.2f}" if sharpe else "N/A", "blue", "연율화"),
                (k5, "Max Drawdown",      f"{mdd:.1f}%" if mdd else "N/A",      "red",  "최대 낙폭"),
                (k6, "Long Positions",    f"{n_long}/{n_total}",                "amber", f"Upside≥{bt_threshold}%"),
            ]
            for col, label, val, cls, sub in kpi_data:
                with col:
                    st.markdown(f"""
                    <div class="kpi-card {cls}" style="padding:0.85rem 1rem">
                      <div class="kpi-label">{label}</div>
                      <div class="kpi-value" style="font-size:1.25rem">{val}</div>
                      <div class="kpi-sub">{sub}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

            # ── 누적 수익률 곡선 ─────────────────────
            col_curve, col_detail = st.columns([3, 2])

            with col_curve:
                st.markdown('<p class="section-title">누적 수익률 곡선</p>', unsafe_allow_html=True)

                eq_curve    = bt_result["equity_curve"]
                bench_curve = bt_result["benchmark_curve"]
                fig_bt = go.Figure()

                # 포트폴리오 곡선
                if not eq_curve.empty:
                    fig_bt.add_trace(go.Scatter(
                        x=eq_curve.index,
                        y=(eq_curve * 100).values,
                        name="DCF Strategy",
                        line=dict(color="#2563eb", width=2.5),
                        fill="tozeroy",
                        fillcolor="rgba(37,99,235,0.07)",
                        hovertemplate="%{x|%Y-%m-%d}<br>Return: %{y:.2f}%<extra>Portfolio</extra>",
                    ))

                # 벤치마크 곡선
                if not bench_curve.empty:
                    fig_bt.add_trace(go.Scatter(
                        x=bench_curve.index,
                        y=(bench_curve * 100).values,
                        name="STI ETF (CLR.SI)",
                        line=dict(color="#f59e0b", width=2, dash="dash"),
                        hovertemplate="%{x|%Y-%m-%d}<br>Return: %{y:.2f}%<extra>Benchmark</extra>",
                    ))

                fig_bt.add_hline(y=0, line_color="#94a3b8", line_width=1)
                fig_bt.update_layout(
                    height=360,
                    margin=dict(l=0, r=0, t=10, b=10),
                    plot_bgcolor="white", paper_bgcolor="white",
                    xaxis=dict(showgrid=False, title=None),
                    yaxis=dict(showgrid=True, gridcolor="#f1f5f9",
                               ticksuffix="%", title="Cumulative Return (%)"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
                    font=dict(family="DM Sans"),
                    hovermode="x unified",
                )
                st.plotly_chart(fig_bt, use_container_width=True)

            # ── 종목별 수익률 테이블 ─────────────────
            with col_detail:
                st.markdown('<p class="section-title">종목별 수익률</p>', unsafe_allow_html=True)

                detail_df = bt_result["details"]
                if not detail_df.empty:
                    # 수익률 기준 정렬
                    detail_sorted = detail_df.sort_values("Return(%)", ascending=False)

                    html_rows = ""
                    for _, r in detail_sorted.iterrows():
                        ret = r["Return(%)"]
                        ret_color = "#059669" if ret >= 0 else "#dc2626"
                        ret_icon  = "▲" if ret >= 0 else "▼"
                        up_str    = f"{r['DCF_Upside(%)']:+.1f}%"

                        html_rows += f"""
                        <tr style="border-bottom:1px solid #f1f5f9">
                          <td style="padding:7px 8px;font-weight:600;color:#0f172a;font-size:0.82rem">{r['Ticker']}</td>
                          <td style="padding:7px 8px;color:#475569;font-size:0.78rem">{r['Name']}</td>
                          <td style="padding:7px 8px;text-align:center;color:#64748b;font-size:0.8rem">${r['Entry_Price']:.3f}</td>
                          <td style="padding:7px 8px;text-align:center;color:#64748b;font-size:0.8rem">${r['Exit_Price']:.3f}</td>
                          <td style="padding:7px 8px;text-align:center;font-weight:700;color:{ret_color};font-size:0.85rem">{ret_icon} {abs(ret):.1f}%</td>
                          <td style="padding:7px 8px;text-align:center;color:#7c3aed;font-size:0.8rem">{up_str}</td>
                        </tr>"""

                    st.markdown(f"""
                    <div style="overflow-y:auto;max-height:340px">
                    <table style="width:100%;border-collapse:collapse;font-family:DM Sans,sans-serif">
                      <thead style="position:sticky;top:0;background:#f8fafc;z-index:1">
                        <tr style="border-bottom:2px solid #e2e8f0">
                          <th style="padding:8px;text-align:left;color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em">Ticker</th>
                          <th style="padding:8px;text-align:left;color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em">Name</th>
                          <th style="padding:8px;text-align:center;color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em">Entry</th>
                          <th style="padding:8px;text-align:center;color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em">Exit</th>
                          <th style="padding:8px;text-align:center;color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em">Return</th>
                          <th style="padding:8px;text-align:center;color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em">DCF Upside</th>
                        </tr>
                      </thead>
                      <tbody>{html_rows}</tbody>
                    </table>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("매수 신호 종목이 없거나 가격 데이터를 가져오지 못했습니다.")

            # ── DCF 신호 테이블 (전체) ───────────────
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            with st.expander("🔍  전체 DCF 신호 테이블 (신호 미발생 포함)", expanded=False):
                if not bt_signals.empty:
                    display_df = bt_signals.copy()
                    display_df["Signal"] = display_df["Signal"].map({1: "✅ Buy", 0: "—"})
                    display_df["Upside(%)"] = display_df["Upside(%)"].apply(
                        lambda x: f"{x:+.1f}%"
                    )
                    st.dataframe(
                        display_df[["Ticker","Name","Entry_Price","DPU","WACC(%)","DCF_Value","Upside(%)","Signal"]],
                        use_container_width=True,
                        hide_index=True,
                    )

    # ── 롤링 백테스팅 ────────────────────────────
    if run_rolling:
        st.markdown("---")
        st.markdown('<p class="section-title">롤링 백테스팅 결과</p>', unsafe_allow_html=True)

        with st.spinner("📡 여러 기간 백테스팅 중... (2~3분 소요)"):
            rolling_df = rolling_backtest(
                {k: v for k, v in REITS_CONFIG.items()},
                periods=default_periods,
                upside_threshold=bt_threshold / 100,
            )

        if not rolling_df.empty:
            # 성과 요약 차트
            fig_roll = go.Figure()
            fig_roll.add_trace(go.Bar(
                name="Portfolio",
                x=rolling_df["Period"],
                y=rolling_df["Portfolio(%)"],
                marker_color=["#059669" if v >= 0 else "#dc2626" for v in rolling_df["Portfolio(%)"]],
                text=[f"{v:+.1f}%" for v in rolling_df["Portfolio(%)"]],
                textposition="outside",
            ))
            fig_roll.add_trace(go.Bar(
                name="Benchmark",
                x=rolling_df["Period"],
                y=rolling_df["Benchmark(%)"],
                marker_color="rgba(245,158,11,0.7)",
                text=[f"{v:+.1f}%" for v in rolling_df["Benchmark(%)"]],
                textposition="outside",
            ))
            fig_roll.add_trace(go.Scatter(
                name="Alpha",
                x=rolling_df["Period"],
                y=rolling_df["Alpha(%)"],
                mode="lines+markers",
                line=dict(color="#7c3aed", width=2.5, dash="dot"),
                marker=dict(size=8),
                yaxis="y2",
            ))
            fig_roll.update_layout(
                barmode="group",
                height=380,
                margin=dict(l=0, r=0, t=20, b=10),
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%", title="Return (%)"),
                yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                            title="Alpha (%)", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
                font=dict(family="DM Sans"),
            )
            st.plotly_chart(fig_roll, use_container_width=True)

            # 롤링 요약 테이블
            avg_alpha = rolling_df["Alpha(%)"].mean()
            win_rate  = (rolling_df["Alpha(%)"] > 0).mean() * 100
            st.markdown(f"""
            <div style="padding:0.9rem 1.2rem;background:#f8fafc;border:1px solid #e2e8f0;
                        border-radius:10px;font-size:0.82rem;color:#64748b;margin-bottom:1rem">
              <b>롤링 요약</b> &nbsp;·&nbsp;
              평균 Alpha: <b style="color:{'#059669' if avg_alpha>=0 else '#dc2626'}">{avg_alpha:+.2f}%</b> &nbsp;·&nbsp;
              Alpha 양(+) 비율: <b>{win_rate:.0f}%</b> ({int(win_rate/100*len(rolling_df))}/{len(rolling_df)} 기간) &nbsp;·&nbsp;
              전략 기준: DCF Upside ≥ {bt_threshold}%, Equal-weight Long-only
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(rolling_df, use_container_width=True, hide_index=True)

    # ── 방법론 노트 ───────────────────────────────
    st.markdown("""
    <div style="margin-top:1.2rem;padding:1rem 1.4rem;background:#f8fafc;
                border:1px solid #e2e8f0;border-radius:10px;font-size:0.78rem;
                color:#64748b;line-height:1.9">
      <b>백테스팅 방법론</b><br>
      &nbsp;① <b>신호 생성</b>: Entry Date 기준 과거 1Y Beta + 과거 12M 배당 합산 DPU로 DCF 계산 →
          Upside ≥ threshold인 종목에 매수 신호 부여<br>
      &nbsp;② <b>포트폴리오</b>: 신호 종목 Equal-weight Long-only, 리밸런싱 없음<br>
      &nbsp;③ <b>벤치마크</b>: CLR.SI (STI ETF), 동일 기간 Buy &amp; Hold<br>
      &nbsp;④ <b>Alpha</b>: Portfolio Return − Benchmark Return (단순 초과수익)<br>
      &nbsp;⑤ <b>한계</b>: 거래비용·슬리피지 미반영, 생존자 편향 주의, 과거 성과가 미래를 보장하지 않음
    </div>
    """, unsafe_allow_html=True)