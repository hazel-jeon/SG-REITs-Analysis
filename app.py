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
from dcf_valuation import calculate_wacc, dcf_reit, nav_discount_premium

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
    "C38U.SI": {"name": "CapitaLand Integrated",    "sector": "Retail/Office"},
    "A17U.SI": {"name": "CapitaLand Ascendas",      "sector": "Industrial"},
    "N2IU.SI": {"name": "Mapletree Pan Asia",        "sector": "Retail/Office"},
    "M44U.SI": {"name": "Mapletree Logistics",       "sector": "Logistics"},
    "ME8U.SI": {"name": "Mapletree Industrial",      "sector": "Industrial"},
    "BUOU.SI": {"name": "Frasers Centrepoint",       "sector": "Retail/Office"},
    "AJBU.SI": {"name": "Keppel DC REIT",            "sector": "Data Centre"},
    "J69U.SI": {"name": "Frasers Logistics",         "sector": "Logistics"},
    "M1GU.SI": {"name": "Sabana Industrial",         "sector": "Industrial"},
    "HMN.SI":  {"name": "OUE Hospitality",           "sector": "Hospitality"},
    "C2PU.SI": {"name": "Parkway Life REIT",         "sector": "Healthcare"},
    "T82U.SI": {"name": "Suntec REIT",               "sector": "Retail/Office"},
    "J91U.SI": {"name": "ESR-LOGOS REIT",            "sector": "Logistics"},
    "TS0U.SI": {"name": "OUE REIT",                  "sector": "Hospitality"},
    "CY6U.SI": {"name": "CapitaLand India Trust",    "sector": "Industrial"},
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
tab1, tab2, tab3, tab4 = st.tabs([
    "📈  Performance",
    "💰  DCF Valuation",
    "🗺️  Sector Analysis",
    "📊  Correlation",
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
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-title">Market Cap by Sector</p>', unsafe_allow_html=True)
        sector_counts = df.groupby("Sector").size().reset_index(name="Count")
        fig5 = px.pie(
            sector_counts, names="Sector", values="Count",
            color="Sector", color_discrete_map=SECTOR_COLORS,
            hole=0.55,
        )
        fig5.update_traces(textposition="outside", textinfo="label+percent",
                           textfont_size=11, pull=[0.03]*len(sector_counts))
        fig5.update_layout(
            height=340, margin=dict(l=20,r=20,t=20,b=20),
            showlegend=False, paper_bgcolor="white",
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">Sector Avg Metrics</p>', unsafe_allow_html=True)
        sec_agg = df.groupby("Sector").agg(
            Avg_Return  = ("Return(%)", "mean"),
            Avg_Yield   = ("Yield(%)", "mean"),
            Avg_Sharpe  = ("Sharpe", "mean"),
            Avg_Beta    = ("Beta", "mean"),
            Count       = ("Ticker", "count"),
        ).round(2).reset_index()

        fig6 = go.Figure()
        metrics = ["Avg_Return", "Avg_Yield", "Avg_Sharpe"]
        labels  = ["Avg Return (%)", "Avg Yield (%)", "Avg Sharpe"]
        for m, lbl in zip(metrics, labels):
            fig6.add_trace(go.Bar(
                name=lbl, x=sec_agg["Sector"], y=sec_agg[m],
                text=[f"{v:.2f}" for v in sec_agg[m]],
                textposition="outside", textfont_size=9,
            ))
        fig6.update_layout(
            barmode="group", height=340,
            margin=dict(l=0,r=0,t=10,b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0, font=dict(size=10)),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig6, use_container_width=True)

    # Sector table
    st.markdown('<p class="section-title">Sector Summary Table</p>', unsafe_allow_html=True)
    st.dataframe(
        sec_agg.rename(columns={
            "Avg_Return": "Avg Return (%)",
            "Avg_Yield":  "Avg Yield (%)",
            "Avg_Sharpe": "Avg Sharpe",
            "Avg_Beta":   "Avg Beta",
            "Count":      "# REITs",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ══════════════════════════════════════════════
# TAB 4: Correlation
# ══════════════════════════════════════════════
with tab4:
    st.markdown('<p class="section-title">Return Correlation Matrix</p>', unsafe_allow_html=True)

    with st.spinner("Computing correlations..."):
        tickers = list(df["Ticker"])
        hist_all = load_price_history(tickers)
        price_df = pd.DataFrame({
            REITS_CONFIG[t]["name"][:15]: h
            for t, h in hist_all.items()
        }).dropna()
        corr = price_df.pct_change().corr()

    fig7 = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        colorscale=[
            [0.0,  "#dc2626"],
            [0.5,  "#f8fafc"],
            [1.0,  "#2563eb"],
        ],
        zmin=-1, zmax=1,
        text=np.round(corr.values, 2),
        texttemplate="%{text}",
        textfont=dict(size=9),
        hoverongaps=False,
        colorbar=dict(title="Corr", thickness=12),
    ))
    fig7.update_layout(
        height=500, margin=dict(l=0,r=0,t=10,b=10),
        paper_bgcolor="white",
        xaxis=dict(tickfont=dict(size=9.5), tickangle=-35),
        yaxis=dict(tickfont=dict(size=9.5)),
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig7, use_container_width=True)

    st.markdown("""
    <div style="padding:0.9rem 1.2rem;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;font-size:0.78rem;color:#64748b">
    <b>읽는 법</b> &nbsp;·&nbsp;
    <span style="color:#2563eb;font-weight:600">파란색 (1.0)</span> = 완전 양의 상관 &nbsp;·&nbsp;
    <span style="color:#dc2626;font-weight:600">빨간색 (-1.0)</span> = 완전 음의 상관 &nbsp;·&nbsp;
    상관계수가 낮은 종목 조합이 포트폴리오 분산 효과가 큽니다.
    </div>
    """, unsafe_allow_html=True)