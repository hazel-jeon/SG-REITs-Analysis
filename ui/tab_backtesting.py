"""
ui/tab_backtesting.py — Tab 6: Backtesting
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import datetime

from backtesting import compute_dcf_signals, run_backtest, rolling_backtest
from utils import REITS_CONFIG


def render(df):
    st.markdown('<p class="section-title">DCF 신호 백테스팅 — "업사이드 신호가 실제로 유효했는가?"</p>', unsafe_allow_html=True)

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

    default_periods = [
        ("2022-01-03", "2022-12-30", "2022 Full Year"),
        ("2023-01-02", "2023-12-29", "2023 Full Year"),
        ("2024-01-02", "2024-12-31", "2024 Full Year"),
        ("2023-07-03", "2024-06-28", "2023H2~2024H1"),
    ]

    with st.expander("📅  롤링 백테스팅 (여러 기간 동시 검증)", expanded=False):
        st.markdown("""
        <div style="font-size:0.82rem;color:#64748b;margin-bottom:0.8rem">
        아래 기간들을 한꺼번에 백테스팅해 전략의 <b>일관성</b>을 검증합니다.
        </div>
        """, unsafe_allow_html=True)
        run_rolling = st.button("▶  Run Rolling Backtest (전체 기간)", use_container_width=False)

    st.markdown("---")

    # ── 단일 백테스트 ─────────────────────────────
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
                        dict(REITS_CONFIG), entry_dt,
                        upside_threshold=bt_threshold / 100,
                    )
                with st.spinner("📊 백테스팅 수익률 계산 중..."):
                    bt_result = run_backtest(bt_signals, entry_dt, exit_dt)

                st.session_state.update({
                    "bt_cache_key": bt_cache_key,
                    "bt_signals":   bt_signals,
                    "bt_result":    bt_result,
                    "bt_ran":       True,
                })
            else:
                bt_signals = st.session_state["bt_signals"]
                bt_result  = st.session_state["bt_result"]

            port_ret  = bt_result["portfolio_return"]
            bench_ret = bt_result["benchmark_return"]
            alpha     = bt_result["alpha"]
            dcf_ret   = bt_result.get("dcf_return", port_ret)
            dcf_alpha = bt_result.get("dcf_alpha", alpha)
            n_long    = bt_result["n_long"]
            n_total   = bt_result["n_total"]
            sharpe    = bt_result["sharpe"]

            # KPI
            k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
            kpi_data = [
                (k1, "EW Return",      f"{port_ret:+.2f}%",   "blue",                               "Equal-Weight 전략"),
                (k2, "DCF-W Return",   f"{dcf_ret:+.2f}%",    "blue",                               "DCF 가중 전략"),
                (k3, "Benchmark",      f"{bench_ret:+.2f}%",  "amber",                              "CLR.SI (STI ETF)"),
                (k4, "EW Alpha",       f"{alpha:+.2f}%",      "green" if alpha >= 0 else "red",     "Equal-Weight 초과수익"),
                (k5, "DCF-W Alpha",    f"{dcf_alpha:+.2f}%",  "green" if dcf_alpha >= 0 else "red", "DCF 가중 초과수익"),
                (k6, "Sharpe (EW)",    f"{sharpe:.2f}" if sharpe else "N/A", "blue",                "연율화"),
                (k7, "Long Positions", f"{n_long}/{n_total}",                "amber",               f"Upside≥{bt_threshold}%"),
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

            # 누적 수익률 곡선
            col_curve, col_detail = st.columns([3, 2])

            with col_curve:
                st.markdown('<p class="section-title">누적 수익률 곡선</p>', unsafe_allow_html=True)
                eq_curve    = bt_result["equity_curve"]
                bench_curve = bt_result["benchmark_curve"]
                fig_bt = go.Figure()

                if not eq_curve.empty:
                    fig_bt.add_trace(go.Scatter(
                        x=eq_curve.index, y=(eq_curve * 100).values,
                        name="Equal-Weight DCF Signal",
                        line=dict(color="#2563eb", width=2.5),
                        fill="tozeroy", fillcolor="rgba(37,99,235,0.07)",
                        hovertemplate="%{x|%Y-%m-%d}<br>Return: %{y:.2f}%<extra>Equal-Weight</extra>",
                    ))

                dcf_curve = bt_result.get("dcf_curve")
                if dcf_curve is not None and not dcf_curve.empty:
                    fig_bt.add_trace(go.Scatter(
                        x=dcf_curve.index, y=(dcf_curve * 100).values,
                        name="DCF Weighted",
                        line=dict(color="#7c3aed", width=2.5, dash="dot"),
                        hovertemplate="%{x|%Y-%m-%d}<br>Return: %{y:.2f}%<extra>DCF Weighted</extra>",
                    ))

                if not bench_curve.empty:
                    fig_bt.add_trace(go.Scatter(
                        x=bench_curve.index, y=(bench_curve * 100).values,
                        name="STI ETF (CLR.SI)",
                        line=dict(color="#f59e0b", width=2, dash="dash"),
                        hovertemplate="%{x|%Y-%m-%d}<br>Return: %{y:.2f}%<extra>Benchmark</extra>",
                    ))

                fig_bt.add_hline(y=0, line_color="#94a3b8", line_width=1)
                fig_bt.update_layout(
                    height=360, margin=dict(l=0, r=0, t=10, b=10),
                    plot_bgcolor="white", paper_bgcolor="white",
                    xaxis=dict(showgrid=False, title=None),
                    yaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%", title="Cumulative Return (%)"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
                    font=dict(family="DM Sans"), hovermode="x unified",
                )
                st.plotly_chart(fig_bt, use_container_width=True)

            with col_detail:
                st.markdown('<p class="section-title">종목별 수익률</p>', unsafe_allow_html=True)
                detail_df = bt_result["details"]
                if not detail_df.empty:
                    detail_sorted = detail_df.sort_values("Return(%)", ascending=False)
                    html_rows = ""
                    for _, r in detail_sorted.iterrows():
                        ret       = r["Return(%)"]
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
                    th = "padding:8px;text-align:left;color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em"
                    st.markdown(f"""
                    <div style="overflow-y:auto;max-height:340px">
                    <table style="width:100%;border-collapse:collapse;font-family:DM Sans,sans-serif">
                      <thead style="position:sticky;top:0;background:#f8fafc;z-index:1">
                        <tr style="border-bottom:2px solid #e2e8f0">
                          <th style="{th}">Ticker</th>
                          <th style="{th}">Name</th>
                          <th style="{th};text-align:center">Entry</th>
                          <th style="{th};text-align:center">Exit</th>
                          <th style="{th};text-align:center">Return</th>
                          <th style="{th};text-align:center">DCF Upside</th>
                        </tr>
                      </thead>
                      <tbody>{html_rows}</tbody>
                    </table>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("매수 신호 종목이 없거나 가격 데이터를 가져오지 못했습니다.")

            with st.expander("🔍  전체 DCF 신호 테이블 (신호 미발생 포함)", expanded=False):
                if not bt_signals.empty:
                    display_df = bt_signals.copy()
                    display_df["Signal"]    = display_df["Signal"].map({1: "✅ Buy", 0: "—"})
                    display_df["Upside(%)"] = display_df["Upside(%)"].apply(lambda x: f"{x:+.1f}%")
                    st.dataframe(
                        display_df[["Ticker", "Name", "Entry_Price", "DPU", "WACC(%)", "DCF_Value", "Upside(%)", "Signal"]],
                        use_container_width=True, hide_index=True,
                    )

    # ── 롤링 백테스팅 ────────────────────────────
    if "run_rolling" in dir() and run_rolling:
        _render_rolling(bt_threshold, default_periods)

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
      &nbsp;⑤ <b>한계</b>: 거래비용·슬리피지 미반영, 생존자 편향 주의
    </div>
    """, unsafe_allow_html=True)


def _render_rolling(bt_threshold, default_periods):
    st.markdown("---")
    st.markdown('<p class="section-title">롤링 백테스팅 결과</p>', unsafe_allow_html=True)

    with st.spinner("📡 여러 기간 백테스팅 중... (2~3분 소요)"):
        rolling_df = rolling_backtest(
            dict(REITS_CONFIG),
            periods=default_periods,
            upside_threshold=bt_threshold / 100,
        )

    if rolling_df.empty:
        return

    fig_roll = go.Figure()
    fig_roll.add_trace(go.Bar(
        name="Portfolio", x=rolling_df["Period"], y=rolling_df["Portfolio(%)"],
        marker_color=["#059669" if v >= 0 else "#dc2626" for v in rolling_df["Portfolio(%)"]],
        text=[f"{v:+.1f}%" for v in rolling_df["Portfolio(%)"]],
        textposition="outside",
    ))
    fig_roll.add_trace(go.Bar(
        name="Benchmark", x=rolling_df["Period"], y=rolling_df["Benchmark(%)"],
        marker_color="rgba(245,158,11,0.7)",
        text=[f"{v:+.1f}%" for v in rolling_df["Benchmark(%)"]],
        textposition="outside",
    ))
    fig_roll.add_trace(go.Scatter(
        name="Alpha", x=rolling_df["Period"], y=rolling_df["Alpha(%)"],
        mode="lines+markers",
        line=dict(color="#7c3aed", width=2.5, dash="dot"),
        marker=dict(size=8), yaxis="y2",
    ))
    fig_roll.update_layout(
        barmode="group", height=380, margin=dict(l=0, r=0, t=20, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%", title="Return (%)"),
        yaxis2=dict(overlaying="y", side="right", ticksuffix="%", title="Alpha (%)", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_roll, use_container_width=True)

    avg_alpha = rolling_df["Alpha(%)"].mean()
    win_rate  = (rolling_df["Alpha(%)"] > 0).mean() * 100
    st.markdown(f"""
    <div style="padding:0.9rem 1.2rem;background:#f8fafc;border:1px solid #e2e8f0;
                border-radius:10px;font-size:0.82rem;color:#64748b;margin-bottom:1rem">
      <b>롤링 요약</b> &nbsp;·&nbsp;
      평균 Alpha: <b style="color:{'#059669' if avg_alpha>=0 else '#dc2626'}">{avg_alpha:+.2f}%</b> &nbsp;·&nbsp;
      Alpha 양(+) 비율: <b>{win_rate:.0f}%</b> ({int(win_rate/100*len(rolling_df))}/{len(rolling_df)} 기간)
    </div>
    """, unsafe_allow_html=True)
    st.dataframe(rolling_df, use_container_width=True, hide_index=True)