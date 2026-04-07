"""
ui/tab_montecarlo.py — Tab 5: Monte Carlo DCF
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from dcf_valuation import monte_carlo_dcf
from utils import REITS_CONFIG


def render(df):
    st.markdown('<p class="section-title">Monte Carlo DCF Simulation</p>', unsafe_allow_html=True)

    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    with ctrl1:
        mc_ticker = st.selectbox(
            "Select REIT",
            options=list(df["Ticker"]),
            format_func=lambda t: f"{t}  —  {REITS_CONFIG[t]['name']}",
        )
    with ctrl2:
        n_sims = st.select_slider(
            "Number of Simulations",
            options=[1000, 3000, 5000, 10000, 20000],
            value=10000,
        )
    with ctrl3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_mc = st.button("Run Simulation", use_container_width=True, type="primary")

    st.markdown("---")

    with st.expander("Advanced Parameters", expanded=False):
        p1, p2, p3, p4, p5 = st.columns(5)
        with p1:
            g_mean = st.number_input("Growth Rate Mean (%)", value=3.0, step=0.5) / 100
            g_std  = st.number_input("Growth Rate Std (%)", value=1.0, step=0.5) / 100
        with p2:
            w_std  = st.number_input("WACC Noise Sigma (%)", value=0.5, step=0.1) / 100
        with p3:
            pg_mean = st.number_input("Perpetual Growth Mean (%)", value=2.5, step=0.5) / 100
            pg_std  = st.number_input("Perpetual Growth Sigma (%)", value=0.5, step=0.1) / 100
        with p4:
            sim_years = st.number_input("Projection Period (years)", value=10, min_value=5, max_value=30, step=1)
        with p5:
            rand_seed = st.number_input("Random Seed", value=42, step=1)

    row       = df[df["Ticker"] == mc_ticker].iloc[0]
    dpu_val   = row.get("DPU")
    beta_val  = row.get("Beta")
    cur_price = row.get("Price")

    if not dpu_val or pd.isna(dpu_val):
        st.warning(f"{mc_ticker}: DPU data unavailable. Cannot run simulation.")
        return

    cache_key = f"mc_{mc_ticker}_{n_sims}_{g_mean}_{g_std}_{w_std}_{pg_mean}_{pg_std}_{sim_years}_{rand_seed}"
    if run_mc or st.session_state.get("mc_cache_key") != cache_key:
        with st.spinner(f"Running {n_sims:,} simulations..."):
            mc_result = monte_carlo_dcf(
                dpu_current=dpu_val, beta=beta_val, n=n_sims,
                years=sim_years, growth_mean=g_mean, growth_std=g_std,
                wacc_std=w_std, pg_mean=pg_mean, pg_std=pg_std,
                seed=int(rand_seed),
            )
            st.session_state["mc_cache_key"] = cache_key
            st.session_state["mc_result"]    = mc_result
    else:
        mc_result = st.session_state.get("mc_result", {})

    if not mc_result:
        st.error("No simulation results. Please check parameters.")
        return

    p10      = mc_result["p10"]
    p50      = mc_result["p50"]
    p90      = mc_result["p90"]
    mean_val = mc_result["mean"]
    std_val  = mc_result["std"]
    n_valid  = mc_result["n_valid"]
    values   = mc_result["values"]
    params   = mc_result["params"]

    # ── KPI 카드 ──────────────────────────────────
    def upside_str(v, price):
        if price is None or pd.isna(price):
            return ""
        pct = (v / price - 1) * 100
        return f"({'up' if pct>=0 else 'down'} {abs(pct):.1f}% vs price)"

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, label, val, color_cls in [
        (k1, "P10 (Bear)", p10,      "red"),
        (k2, "P50 (Base)", p50,      "blue"),
        (k3, "P90 (Bull)", p90,      "green"),
        (k4, "Mean",       mean_val, "amber"),
        (k5, "Std Dev",    std_val,  "amber"),
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

    col_chart, col_info = st.columns([3, 1])

    with col_chart:
        st.markdown('<p class="section-title">Intrinsic Value Distribution</p>', unsafe_allow_html=True)

        # x축 클리핑 — P5~P95 범위만 표시
        p5_val, p95_val = np.percentile(values, [5, 95])
        x_min = max(0, min(cur_price * 0.7 if cur_price else p5_val, p5_val * 0.8))
        x_max = p95_val * 1.05
        clipped = [v for v in values if x_min <= v <= x_max]

        fig_mc = go.Figure()

        # 메인 히스토그램
        fig_mc.add_trace(go.Histogram(
            x=clipped, nbinsx=80,
            marker=dict(color="rgba(37,99,235,0.55)", line=dict(color="rgba(37,99,235,0.8)", width=0.3)),
            name="Simulation",
            hovertemplate="Value: $%{x:.3f}<br>Count: %{y}<extra></extra>",
        ))

        # Bear 구간 (P10 이하) 색칠
        bear_vals = [v for v in clipped if v <= p10]
        if bear_vals:
            fig_mc.add_trace(go.Histogram(
                x=bear_vals, nbinsx=30,
                marker=dict(color="rgba(220,38,38,0.35)"),
                showlegend=False,
                hoverinfo="skip",
            ))

        # Bull 구간 (P90 이상) 색칠
        bull_vals = [v for v in clipped if v >= p90]
        if bull_vals:
            fig_mc.add_trace(go.Histogram(
                x=bull_vals, nbinsx=30,
                marker=dict(color="rgba(5,150,105,0.35)"),
                showlegend=False,
                hoverinfo="skip",
            ))

        # 수직선 + 레이블 박스 (y위치 번갈아 배치로 겹침 방지)
        vlines = [
            (p10,       "P10 Bear", "#dc2626", "top"),
            (p50,       "P50 Base", "#1e40af", "top right"),
            (p90,       "P90 Bull", "#059669", "top"),
        ]
        if cur_price and not pd.isna(cur_price):
            vlines.insert(0, (cur_price, "Current Price", "#f59e0b", "top left"))

        for i, (val, label, color, pos) in enumerate(vlines):
            if x_min <= val <= x_max:
                fig_mc.add_vline(
                    x=val,
                    line=dict(
                        color=color,
                        width=2.5 if label in ("P50 Base", "Current Price") else 1.8,
                        dash="solid" if label in ("P50 Base", "Current Price") else "dash",
                    ),
                    annotation=dict(
                        text=f"<b>{label}</b><br>${val:.3f}",
                        font=dict(size=10, color=color),
                        bgcolor="white",
                        bordercolor=color,
                        borderwidth=1.2,
                        yshift=(-30 * (i % 2)),
                    ),
                    annotation_position=pos,
                )

        fig_mc.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=50, b=10),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(
                title="Intrinsic Value (SGD)",
                showgrid=True,
                gridcolor="#f1f5f9",
                tickprefix="$",
                range=[x_min, x_max],
            ),
            yaxis=dict(title="Frequency", showgrid=True, gridcolor="#f1f5f9"),
            barmode="overlay",
            showlegend=False,
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_mc, use_container_width=True)

    with col_info:
        st.markdown('<p class="section-title">Scenario Interpretation</p>', unsafe_allow_html=True)

        def interp_vs_price(pval, price, label):
            if price is None or pd.isna(price):
                return ""
            pct = (pval / price - 1) * 100
            color = "#059669" if pct >= 10 else ("#dc2626" if pct <= -10 else "#d97706")
            arrow = "up" if pct >= 10 else ("down" if pct <= -10 else "flat")
            return f"""
            <div style="padding:0.7rem 0.9rem;margin-bottom:0.6rem;border-radius:10px;
                        border:1px solid #e2e8f0;background:white">
              <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                          letter-spacing:0.07em;margin-bottom:4px">{label}</div>
              <div style="font-size:1.1rem;font-weight:700;color:#0f172a">${pval:.3f}</div>
              <div style="font-size:0.8rem;font-weight:600;color:{color}">
                {abs(pct):.1f}% {'upside' if pct>=0 else 'downside'}
              </div>
            </div>"""

        prob_above = (np.array(values) > cur_price).mean() * 100 if cur_price else None
        st.markdown(
            interp_vs_price(p10, cur_price, "Bear (P10)") +
            interp_vs_price(p50, cur_price, "Base (P50)") +
            interp_vs_price(p90, cur_price, "Bull (P90)"),
            unsafe_allow_html=True,
        )
        if prob_above is not None:
            bar_color = "#059669" if prob_above >= 50 else "#dc2626"
            st.markdown(f"""
            <div style="padding:0.7rem 0.9rem;border-radius:10px;border:1px solid #e2e8f0;
                        background:white;margin-top:0.4rem">
              <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                          letter-spacing:0.07em;margin-bottom:6px">P(IV &gt; Current Price)</div>
              <div style="font-size:1.4rem;font-weight:700;color:{bar_color}">{prob_above:.1f}%</div>
              <div style="background:#e2e8f0;border-radius:4px;height:6px;margin-top:6px">
                <div style="background:{bar_color};width:{min(prob_above,100):.1f}%;height:6px;border-radius:4px"></div>
              </div>
              <div style="font-size:0.73rem;color:#64748b;margin-top:4px">
                {int(n_valid*prob_above/100):,} / {n_valid:,} runs
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:1rem;padding:0.9rem 1.2rem;background:#f8fafc;
                border:1px solid #e2e8f0;border-radius:10px;font-size:0.78rem;color:#64748b;line-height:1.8">
      <b>Simulation Parameters</b> &nbsp;·&nbsp;
      Valid runs: <b>{n_valid:,}/{n_sims:,}</b> &nbsp;·&nbsp;
      Base WACC: <b>{params['base_wacc']:.2%}</b> &nbsp;·&nbsp;
      Growth rate: <b>N({g_mean:.1%}, {g_std:.1%})</b> &nbsp;·&nbsp;
      WACC noise: <b>sigma={w_std:.1%}</b> &nbsp;·&nbsp;
      Perpetual growth: <b>N({pg_mean:.1%}, {pg_std:.1%})</b> &nbsp;·&nbsp;
      Projection: <b>{sim_years}Y</b>
    </div>
    """, unsafe_allow_html=True)
