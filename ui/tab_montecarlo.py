"""
ui/tab_montecarlo.py — Tab 5: Monte Carlo DCF
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from dcf_valuation import monte_carlo_dcf
from utils import REITS_CONFIG


def render(df):
    st.markdown('<p class="section-title">Monte Carlo DCF 시뮬레이션</p>', unsafe_allow_html=True)

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

    row       = df[df["Ticker"] == mc_ticker].iloc[0]
    dpu_val   = row.get("DPU")
    beta_val  = row.get("Beta")
    cur_price = row.get("Price")

    if not dpu_val or pd.isna(dpu_val):
        st.warning(f"**{mc_ticker}**: DPU 데이터가 없어 시뮬레이션을 실행할 수 없습니다.")
        return

    cache_key = f"mc_{mc_ticker}_{n_sims}_{g_mean}_{g_std}_{w_std}_{pg_mean}_{pg_std}_{sim_years}_{rand_seed}"
    if run_mc or st.session_state.get("mc_cache_key") != cache_key:
        with st.spinner(f"🎲 {n_sims:,}회 시뮬레이션 중..."):
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
        st.error("시뮬레이션 결과가 없습니다. 파라미터를 확인해 주세요.")
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
        return f"({'▲' if pct>=0 else '▼'} {abs(pct):.1f}% vs price)"

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
        st.markdown('<p class="section-title">내재가치 분포 (히스토그램)</p>', unsafe_allow_html=True)
        fig_mc = go.Figure()
        fig_mc.add_trace(go.Histogram(
            x=values, nbinsx=80,
            marker=dict(color="rgba(37,99,235,0.55)", line=dict(color="rgba(37,99,235,0.8)", width=0.3)),
            name="Simulation",
            hovertemplate="Value: $%{x:.3f}<br>Count: %{y}<extra></extra>",
        ))
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
                    bgcolor="white", bordercolor=pcolor, borderwidth=1,
                ),
                annotation_position="top",
            )
        if cur_price and not pd.isna(cur_price):
            fig_mc.add_vline(
                x=cur_price,
                line=dict(color="#f59e0b", width=2.5),
                annotation=dict(
                    text=f"<b>Current</b><br>${cur_price:.3f}",
                    font=dict(size=10, color="#92400e"),
                    bgcolor="#fef3c7", bordercolor="#f59e0b", borderwidth=1,
                ),
                annotation_position="top right",
            )
        fig_mc.update_layout(
            height=380, margin=dict(l=0, r=0, t=40, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(title="Intrinsic Value (SGD)", showgrid=True, gridcolor="#f1f5f9", tickprefix="$"),
            yaxis=dict(title="Frequency", showgrid=True, gridcolor="#f1f5f9"),
            showlegend=False, font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_mc, use_container_width=True)

    with col_info:
        st.markdown('<p class="section-title">시나리오 해석</p>', unsafe_allow_html=True)

        def interp_vs_price(pval, price, label):
            if price is None or pd.isna(price):
                return ""
            pct = (pval / price - 1) * 100
            color = "#059669" if pct >= 10 else ("#dc2626" if pct <= -10 else "#d97706")
            icon  = "▲" if pct >= 10 else ("▼" if pct <= -10 else "→")
            return f"""
            <div style="padding:0.7rem 0.9rem;margin-bottom:0.6rem;border-radius:10px;
                        border:1px solid #e2e8f0;background:white">
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
            <div style="padding:0.7rem 0.9rem;border-radius:10px;border:1px solid #e2e8f0;
                        background:white;margin-top:0.4rem">
              <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                          letter-spacing:0.07em;margin-bottom:6px">현재가 상회 확률</div>
              <div style="font-size:1.4rem;font-weight:700;color:{bar_color}">{prob_above:.1f}%</div>
              <div style="background:#e2e8f0;border-radius:4px;height:6px;margin-top:6px">
                <div style="background:{bar_color};width:{prob_above:.1f}%;height:6px;border-radius:4px"></div>
              </div>
              <div style="font-size:0.73rem;color:#64748b;margin-top:4px">
                {n_valid:,}회 중 {int(n_valid*prob_above/100):,}회
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:1rem;padding:0.9rem 1.2rem;background:#f8fafc;
                border:1px solid #e2e8f0;border-radius:10px;font-size:0.78rem;color:#64748b;line-height:1.8">
      <b>시뮬레이션 파라미터</b> &nbsp;·&nbsp;
      유효 실행: <b>{n_valid:,}/{n_sims:,}회</b> &nbsp;·&nbsp;
      Base WACC: <b>{params['base_wacc']:.2%}</b> &nbsp;·&nbsp;
      성장률: <b>N({g_mean:.1%}, {g_std:.1%})</b> &nbsp;·&nbsp;
      WACC 노이즈: <b>σ={w_std:.1%}</b> &nbsp;·&nbsp;
      영구성장률: <b>N({pg_mean:.1%}, {pg_std:.1%})</b> &nbsp;·&nbsp;
      예측기간: <b>{sim_years}Y</b>
    </div>
    """, unsafe_allow_html=True)