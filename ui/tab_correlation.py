"""
ui/tab_correlation.py — Tab 4: Correlation
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from utils import REITS_CONFIG
from data.loader import load_price_history


def render(df):
    with st.spinner("수익률 상관계수 계산 중..."):
        tickers  = list(df["Ticker"])
        hist_all = load_price_history(tuple(tickers))

        name_map = {
            t: REITS_CONFIG[t]["name"][:13]
            for t in tickers if t in hist_all
        }
        price_df = pd.DataFrame({
            name_map[t]: h
            for t, h in hist_all.items() if t in name_map
        }).dropna(how="all").ffill().dropna()

        ret_df = price_df.pct_change().dropna()
        corr   = ret_df.corr()

        ticker_sector = {
            REITS_CONFIG[t]["name"][:13]: REITS_CONFIG[t]["sector"]
            for t in tickers if t in hist_all
        }
        sorted_names = sorted(corr.columns, key=lambda n: (ticker_sector.get(n, "Z"), n))
        corr = corr.loc[sorted_names, sorted_names]

    # ── 히트맵 ────────────────────────────────────
    col_heat, col_info = st.columns([3, 1])

    with col_heat:
        st.markdown('<p class="section-title">수익률 상관계수 매트릭스 (섹터 기준 정렬)</p>', unsafe_allow_html=True)

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
        for b in sector_boundaries:
            fig7.add_shape(type="line", x0=b, x1=b, y0=-0.5, y1=len(corr) - 0.5,
                           line=dict(color="#1e293b", width=1.5))
            fig7.add_shape(type="line", y0=b, y1=b, x0=-0.5, x1=len(corr) - 0.5,
                           line=dict(color="#1e293b", width=1.5))
        fig7.update_layout(
            height=520, margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="white",
            xaxis=dict(tickfont=dict(size=9), tickangle=-40, side="bottom"),
            yaxis=dict(tickfont=dict(size=9), autorange="reversed"),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig7, use_container_width=True)

    # ── 낮은/높은 상관 페어 ───────────────────────
    with col_info:
        pairs = []
        cols_ = corr.columns.tolist()
        for i in range(len(cols_)):
            for j in range(i + 1, len(cols_)):
                pairs.append((cols_[i], cols_[j], corr.iloc[i, j]))

        pairs_df = pd.DataFrame(pairs, columns=["A", "B", "Corr"]).sort_values("Corr")

        st.markdown('<p class="section-title">📌 낮은 상관 페어 TOP 5</p>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.75rem;color:#94a3b8;margin-bottom:0.7rem'>포트폴리오 분산 효과가 큰 종목 조합</div>", unsafe_allow_html=True)

        for _, pr in pairs_df.head(5).iterrows():
            c_val   = pr["Corr"]
            c_color = "#059669" if c_val < 0.3 else "#d97706"
            st.markdown(f"""
            <div style="padding:0.65rem 0.8rem;margin-bottom:0.5rem;background:white;
                        border-radius:10px;border:1px solid #e2e8f0;border-left:3px solid {c_color}">
              <div style="font-size:0.75rem;font-weight:700;color:#0f172a">{pr['A']}</div>
              <div style="font-size:0.7rem;color:#94a3b8;margin:1px 0">+ {pr['B']}</div>
              <div style="font-size:1rem;font-weight:800;color:{c_color}">{c_val:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<p class="section-title" style="margin-top:1rem">📌 높은 상관 페어 TOP 5</p>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.75rem;color:#94a3b8;margin-bottom:0.7rem'>중복 보유 시 분산 효과 낮은 조합</div>", unsafe_allow_html=True)

        for _, pr in pairs_df[pairs_df["Corr"] < 1.0].tail(5).iloc[::-1].iterrows():
            c_color = "#dc2626"
            st.markdown(f"""
            <div style="padding:0.65rem 0.8rem;margin-bottom:0.5rem;background:white;
                        border-radius:10px;border:1px solid #e2e8f0;border-left:3px solid {c_color}">
              <div style="font-size:0.75rem;font-weight:700;color:#0f172a">{pr['A']}</div>
              <div style="font-size:0.7rem;color:#94a3b8;margin:1px 0">+ {pr['B']}</div>
              <div style="font-size:1rem;font-weight:800;color:{c_color}">{pr['Corr']:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── 섹터 간 평균 상관계수 히트맵 ─────────────
    st.markdown('<p class="section-title">섹터 간 평균 상관계수</p>', unsafe_allow_html=True)

    sec_corr_data = {}
    for t1 in tickers:
        if t1 not in hist_all:
            continue
        n1 = name_map[t1]
        s1 = REITS_CONFIG[t1]["sector"]
        for t2 in tickers:
            if t2 not in hist_all or t1 == t2:
                continue
            n2 = name_map[t2]
            s2 = REITS_CONFIG[t2]["sector"]
            if n1 in corr.index and n2 in corr.columns:
                sec_corr_data.setdefault((s1, s2), []).append(corr.loc[n1, n2])

    sectors_u  = sorted(set(REITS_CONFIG[t]["sector"] for t in tickers))
    sec_matrix = pd.DataFrame(index=sectors_u, columns=sectors_u, dtype=float)
    for (s1, s2), vals in sec_corr_data.items():
        sec_matrix.loc[s1, s2] = round(np.mean(vals), 3)
    np.fill_diagonal(sec_matrix.values, 1.0)

    fig_sec = go.Figure(go.Heatmap(
        z=sec_matrix.values.astype(float),
        x=sec_matrix.columns.tolist(),
        y=sec_matrix.index.tolist(),
        colorscale=[[0.0, "#f8fafc"], [0.5, "#93c5fd"], [1.0, "#1d4ed8"]],
        zmin=0, zmax=1,
        text=np.round(sec_matrix.values.astype(float), 2),
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        colorbar=dict(thickness=12, title=dict(text="Avg Corr")),
    ))
    fig_sec.update_layout(
        height=320, margin=dict(l=0, r=0, t=10, b=10),
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