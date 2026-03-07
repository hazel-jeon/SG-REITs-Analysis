"""
ui/tab_optimizer.py — Tab 7: Portfolio Optimizer
"""

import streamlit as st
import plotly.graph_objects as go

from portfolio_optimizer import run_optimization, summarize_weights
from data.loader import load_price_history
from ui.styles import SECTOR_COLORS
from utils import RISK_FREE_RATE


STRAT_COLORS = {
    "Equal Weight":   "#94a3b8",
    "Max Sharpe":     "#2563eb",
    "Min Volatility": "#059669",
    "DCF Weighted":   "#7c3aed",
}


def render(df):
    st.markdown('<p class="section-title">포트폴리오 최적화 — 효율적 프론티어 & 전략 비교</p>', unsafe_allow_html=True)

    oc1, oc2, oc3 = st.columns([2, 2, 1])
    with oc1:
        min_w = st.slider("종목 최소 비중 (%)", 0, 10, 0, 1) / 100
    with oc2:
        max_w = st.slider("종목 최대 비중 (%)", 20, 100, 40, 5) / 100
    with oc3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_opt = st.button("▶  Run Optimizer", use_container_width=True, type="primary")

    st.markdown("---")

    opt_cache_key = f"opt_{','.join(df['Ticker'])}_{min_w}_{max_w}"
    if run_opt or st.session_state.get("opt_cache_key") != opt_cache_key:
        with st.spinner("📡 가격 데이터 수집 + 포트폴리오 최적화 중..."):
            opt_hist   = load_price_history(tuple(df["Ticker"]))
            opt_result = run_optimization(df, opt_hist, min_weight=min_w, max_weight=max_w)
            st.session_state["opt_cache_key"] = opt_cache_key
            st.session_state["opt_result"]    = opt_result
    else:
        opt_result = st.session_state.get("opt_result", {})

    if not opt_result:
        st.error("최적화 결과가 없습니다. 데이터를 확인하거나 필터를 조정해 주세요.")
        return

    strategies  = opt_result["strategies"]
    frontier_df = opt_result["frontier"]

    # ── 행 1: 효율적 프론티어 + KPI ──────────────
    col_frontier, col_kpi = st.columns([3, 2])

    with col_frontier:
        st.markdown('<p class="section-title">효율적 프론티어</p>', unsafe_allow_html=True)

        fig_ef = go.Figure()

        if not frontier_df.empty:
            fig_ef.add_trace(go.Scatter(
                x=frontier_df["Volatility"], y=frontier_df["Return"],
                mode="lines", name="Efficient Frontier",
                line=dict(color="#e2e8f0", width=2.5),
                fill="tozeroy", fillcolor="rgba(226,232,240,0.15)",
                hovertemplate="Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra>Frontier</extra>",
            ))

        for key, res in strategies.items():
            color = STRAT_COLORS.get(res["strategy"], "#64748b")
            fig_ef.add_trace(go.Scatter(
                x=[res["volatility"] * 100], y=[res["return"] * 100],
                mode="markers+text",
                name=res["strategy"],
                text=[res["strategy"]],
                textposition="top center",
                textfont=dict(size=10, color=color),
                marker=dict(
                    size=14, color=color,
                    symbol="diamond" if key == "max_sharpe" else "circle",
                    line=dict(width=2, color="white"),
                ),
                hovertemplate=(
                    f"<b>{res['strategy']}</b><br>"
                    f"Return: {res['return']*100:.2f}%<br>"
                    f"Vol: {res['volatility']*100:.2f}%<br>"
                    f"Sharpe: {res['sharpe']:.3f}<extra></extra>"
                ),
            ))

        fig_ef.update_layout(
            height=400, margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(title="Volatility (%)", showgrid=True, gridcolor="#f1f5f9", ticksuffix="%"),
            yaxis=dict(title="Expected Return (%)", showgrid=True, gridcolor="#f1f5f9", ticksuffix="%"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0, font=dict(size=10)),
            font=dict(family="DM Sans"), hovermode="closest",
        )
        st.plotly_chart(fig_ef, use_container_width=True)

    with col_kpi:
        st.markdown('<p class="section-title">전략별 성과 비교</p>', unsafe_allow_html=True)
        best_sharpe = max(r["sharpe"] for r in strategies.values())

        for _, res in strategies.items():
            color = STRAT_COLORS.get(res["strategy"], "#64748b")
            badge = " 🏆" if res["sharpe"] == best_sharpe else ""
            st.markdown(f"""
            <div style="padding:0.85rem 1rem;margin-bottom:0.6rem;background:white;
                        border-radius:12px;border:1px solid #e2e8f0;border-left:4px solid {color}">
              <div style="font-size:0.75rem;color:{color};font-weight:700;
                          text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px">
                {res['strategy']}{badge}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
                <div>
                  <div style="font-size:0.68rem;color:#94a3b8">Exp. Return</div>
                  <div style="font-size:1rem;font-weight:700;color:{'#059669' if res['return']>=0 else '#dc2626'}">
                    {res['return']*100:+.2f}%</div>
                </div>
                <div>
                  <div style="font-size:0.68rem;color:#94a3b8">Volatility</div>
                  <div style="font-size:1rem;font-weight:700;color:#0f172a">
                    {res['volatility']*100:.2f}%</div>
                </div>
                <div>
                  <div style="font-size:0.68rem;color:#94a3b8">Sharpe</div>
                  <div style="font-size:1rem;font-weight:700;color:{color}">
                    {res['sharpe']:.3f}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── 행 2: 비중 차트 ───────────────────────────
    st.markdown('<p class="section-title">종목별 비중 비교</p>', unsafe_allow_html=True)
    weight_df = summarize_weights(opt_result)

    col_bar, col_pie = st.columns(2)

    with col_bar:
        fig_w = go.Figure()
        strat_cols = [
            ("Equal Weight(%)",  "Equal Weight",   "#94a3b8"),
            ("Max Sharpe(%)",    "Max Sharpe",      "#2563eb"),
            ("Min Vol(%)",       "Min Volatility",  "#059669"),
            ("DCF Weighted(%)",  "DCF Weighted",    "#7c3aed"),
        ]
        for col_name, label, color in strat_cols:
            fig_w.add_trace(go.Bar(
                name=label, x=weight_df["Name"], y=weight_df[col_name],
                marker_color=color, opacity=0.85,
                hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:.1f}}%<extra></extra>",
            ))
        fig_w.update_layout(
            barmode="group", height=360, margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(tickangle=-30, tickfont=dict(size=9), showgrid=False),
            yaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#f1f5f9", title="Weight (%)"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.4, x=0, font=dict(size=10)),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_w, use_container_width=True)

    with col_pie:
        st.markdown("<div style='font-size:0.82rem;font-weight:600;color:#0f172a;margin-bottom:0.5rem'>Max Sharpe 비중 분포</div>", unsafe_allow_html=True)
        ms_weights = weight_df[weight_df["Max Sharpe(%)"] > 0.5]
        fig_pie = go.Figure(go.Pie(
            labels=ms_weights["Name"],
            values=ms_weights["Max Sharpe(%)"],
            hole=0.45,
            textinfo="label+percent",
            textfont=dict(size=10),
            marker=dict(
                colors=[
                    SECTOR_COLORS.get(
                        df[df["Ticker"] == t]["Sector"].values[0]
                        if len(df[df["Ticker"] == t]) > 0 else "", "#94a3b8"
                    ) for t in ms_weights["Ticker"]
                ],
                line=dict(color="white", width=1.5),
            ),
            pull=[0.03] * len(ms_weights),
            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        ))
        fig_pie.update_layout(
            height=360, margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="white", showlegend=False,
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── 행 3: 비중 테이블 ─────────────────────────
    with st.expander("📋  전략별 종목 비중 상세 테이블", expanded=False):
        st.dataframe(
            weight_df.style.format({
                "Equal Weight(%)": "{:.1f}%",
                "Max Sharpe(%)":   "{:.1f}%",
                "Min Vol(%)":      "{:.1f}%",
                "DCF Weighted(%)": "{:.1f}%",
            }).background_gradient(subset=["Max Sharpe(%)"], cmap="Blues"),
            use_container_width=True, hide_index=True,
        )

    # ── 행 4: 방법론 노트 ─────────────────────────
    st.markdown(f"""
    <div style="margin-top:1rem;padding:1rem 1.4rem;background:#f8fafc;
                border:1px solid #e2e8f0;border-radius:10px;
                font-size:0.78rem;color:#64748b;line-height:1.9">
      <b>최적화 방법론</b><br>
      &nbsp;① <b>Max Sharpe</b>: scipy.optimize SLSQP로 샤프 비율 최대화.
          단일 종목 최대 {int(max_w*100)}%, 최소 {int(min_w*100)}% 제약 적용<br>
      &nbsp;② <b>Min Volatility</b>: 동일 제약 하에 포트폴리오 연환산 변동성 최소화<br>
      &nbsp;③ <b>DCF Weighted</b>: DCF 업사이드(%) 비례 규칙 기반 가중. 음수 종목 0 처리 후 정규화<br>
      &nbsp;④ <b>Equal Weight</b>: 기준선 포트폴리오 (1/N)<br>
      &nbsp;⑤ <b>입력 데이터</b>: 1Y 일별 수익률 기반 평균·공분산.
          무위험수익률 {RISK_FREE_RATE*100:.1f}% (싱가포르 10년 국채)<br>
      &nbsp;⑥ <b>한계</b>: 과거 수익률 기반 추정. 거래비용·세금 미반영. 수익률 정규분포 가정
    </div>
    """, unsafe_allow_html=True)