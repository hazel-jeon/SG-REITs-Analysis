"""
ui/tab_sector.py — Tab 3: Sector Analysis
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from ui.styles import SECTOR_COLORS


def render(df):
    sec_agg = df.groupby("Sector").agg(
        Avg_Return=("Return(%)", "mean"),
        Avg_Yield=("Yield(%)", "mean"),
        Avg_Sharpe=("Sharpe", "mean"),
        Avg_Beta=("Beta", "mean"),
        Avg_Vol=("Vol(%)", "mean"),
        Avg_Upside=("Upside(%)", "mean"),
        Count=("Ticker", "count"),
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
            textfont_size=11, pull=[0.03] * len(sector_counts),
        )
        fig5.update_layout(
            height=340, margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False, paper_bgcolor="white",
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">섹터 레이더 차트 (다차원 비교)</p>', unsafe_allow_html=True)

        radar_metrics = ["Avg_Return", "Avg_Yield", "Avg_Sharpe", "Avg_Upside"]
        radar_labels  = ["Return", "Yield", "Sharpe", "DCF Upside"]
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
            vals = [row[m] for m in radar_metrics] + [row[radar_metrics[0]]]
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
                radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=8), showticklabels=False),
                angularaxis=dict(tickfont=dict(size=11)),
                bgcolor="white",
            ),
            height=340, margin=dict(l=30, r=30, t=20, b=20),
            paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, x=0, font=dict(size=10)),
            font=dict(family="DM Sans"),
            showlegend=True,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── 행 2: 버블 차트 ──────────────────────────
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
        height=340, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(title="Avg Dividend Yield (%)", showgrid=True, gridcolor="#f1f5f9", ticksuffix="%"),
        yaxis=dict(title="Avg Sharpe Ratio", showgrid=True, gridcolor="#f1f5f9"),
        showlegend=False,
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_bubble, use_container_width=True)

    # ── 행 3: 섹터별 종목 카드 ───────────────────
    st.markdown('<p class="section-title">섹터별 종목 상세</p>', unsafe_allow_html=True)

    sector_list = sorted(df["Sector"].unique())
    tabs_sector = st.tabs(sector_list)

    for tab_s, sector_name in zip(tabs_sector, sector_list):
        with tab_s:
            sector_df = df[df["Sector"] == sector_name].sort_values("Sharpe", ascending=False)
            s_color   = SECTOR_COLORS.get(sector_name, "#64748b")

            cards_html = ""
            for _, r in sector_df.iterrows():
                ret_color = "#059669" if r["Return(%)"] >= 0 else "#dc2626"
                up_val    = r.get("Upside(%)")
                up_str    = f"{up_val:+.1f}%" if pd.notna(up_val) and up_val is not None else "N/A"
                up_color  = "#059669" if (pd.notna(up_val) and up_val and up_val >= 0) else "#dc2626"
                yield_str = f"{r['Yield(%)']:.2f}%" if pd.notna(r.get("Yield(%)")) else "N/A"

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