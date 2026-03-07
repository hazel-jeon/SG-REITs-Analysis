"""
ui/tab_dcf.py — Tab 2: DCF Valuation
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render(df):
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown('<p class="section-title">DCF Upside vs Current Price</p>', unsafe_allow_html=True)
        dcf_df = df[df["DCF Value"].notna()].sort_values("Upside(%)", ascending=False)

        if not dcf_df.empty:
            bar_colors = ["#059669" if u >= 0 else "#dc2626" for u in dcf_df["Upside(%)"]]
            fig = go.Figure(go.Bar(
                x=dcf_df["Upside(%)"],
                y=dcf_df["Name"],
                orientation="h",
                marker=dict(color=bar_colors, opacity=0.85),
                text=[f"{v:+.1f}%" for v in dcf_df["Upside(%)"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>DCF Upside: %{x:.1f}%<extra></extra>",
            ))
            fig.add_vline(x=0, line_color="#94a3b8", line_width=1.5)
            fig.update_layout(
                height=400, margin=dict(l=0, r=60, t=10, b=10),
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%", title=None),
                yaxis=dict(showgrid=False, title=None, tickfont=dict(size=11)),
                font=dict(family="DM Sans"),
            )
            st.plotly_chart(fig, use_container_width=True)

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
                return f'<span class="pill-up">{v:.1f}%</span>'
            elif v > 10:
                return f'<span class="pill-down">+{v:.1f}%</span>'
            return f'<span class="pill-neu">{v:+.1f}%</span>'

        html_rows = ""
        for _, r in df.sort_values("Upside(%)", ascending=False, na_position="last").iterrows():
            dcf_str   = f"${r['DCF Value']:.3f}" if pd.notna(r.get("DCF Value")) else "N/A"
            price_str = f"${r['Price']:.3f}"     if pd.notna(r.get("Price"))     else "N/A"
            wacc_str  = f"{r['WACC(%)']:.2f}%"  if pd.notna(r.get("WACC(%)"))   else "N/A"
            dpu_str   = f"${r['DPU']:.4f}"       if pd.notna(r.get("DPU"))       else "N/A"
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

        th = "padding:8px 10px;text-align:left;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em"
        st.markdown(f"""
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:0.83rem;font-family:DM Sans,sans-serif">
          <thead>
            <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0">
              <th style="{th}">Ticker</th>
              <th style="{th}">Name</th>
              <th style="{th};text-align:center">Price</th>
              <th style="{th};text-align:center">DPU</th>
              <th style="{th};text-align:center">WACC</th>
              <th style="{th};text-align:center">DCF Value</th>
              <th style="{th};text-align:center">Upside</th>
              <th style="{th};text-align:center">NAV Disc</th>
            </tr>
          </thead>
          <tbody>{html_rows}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

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