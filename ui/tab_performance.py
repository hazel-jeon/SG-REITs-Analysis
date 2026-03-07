"""
ui/tab_performance.py — Tab 1: Performance
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from ui.styles import SECTOR_COLORS
from utils import REITS_CONFIG
from data.loader import load_price_history


def render(df):
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
            height=420, margin=dict(l=0, r=60, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                       ticksuffix="%", title=None),
            yaxis=dict(showgrid=False, title=None, tickfont=dict(size=11)),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">Risk vs Return</p>', unsafe_allow_html=True)
        df_scatter = df.dropna(subset=["Vol(%)", "Return(%)"])
        fig2 = px.scatter(
            df_scatter,
            x="Vol(%)", y="Return(%)",
            color="Sector",
            size=[14] * len(df_scatter),
            text="Ticker",
            color_discrete_map=SECTOR_COLORS,
            hover_data={"Name": True, "Sharpe": True},
        )
        fig2.update_traces(textposition="top center", textfont_size=9,
                           marker=dict(line=dict(width=1, color="white")))
        fig2.update_layout(
            height=420, margin=dict(l=0, r=0, t=10, b=10),
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
            hist_data = load_price_history(tuple(selected))
        fig3 = go.Figure()
        for ticker, prices in hist_data.items():
            norm = prices / prices.iloc[0] * 100
            name = REITS_CONFIG.get(ticker, {}).get("name", ticker)
            fig3.add_trace(go.Scatter(
                x=norm.index, y=norm.values,
                name=ticker,
                mode="lines",
                hovertemplate=f"<b>{name}</b><br>%{{x|%Y-%m-%d}}<br>Idx: %{{y:.1f}}<extra></extra>",
                line=dict(width=1.8),
            ))
        fig3.add_hline(y=100, line_dash="dot", line_color="#94a3b8", line_width=1)
        fig3.update_layout(
            height=340, margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Normalized (Base=100)"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0, font=dict(size=10)),
            font=dict(family="DM Sans"),
            hovermode="x unified",
        )
        st.plotly_chart(fig3, use_container_width=True)