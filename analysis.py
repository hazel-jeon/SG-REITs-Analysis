import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from fpdf import FPDF
import datetime
import os

from dcf_valuation import calculate_wacc, dcf_reit, nav_discount_premium


# ─────────────────────────────────────────────
# 1. 시장 데이터 분석 (기존 + DCF 연동)
# ─────────────────────────────────────────────
def get_reit_analysis(reits_info, benchmark="CLR.SI"):
    """
    각 REIT의 1Y 수익률/변동성/베타/샤프 + DCF 내재가치/NAV 할인율 계산.
    Returns: DataFrame
    """
    results = []

    # 벤치마크 수익률
    bench = yf.Ticker(benchmark).history(period="1y")["Close"]
    if bench.empty:
        print(f"  [Error] 벤치마크 {benchmark} 데이터 없음")
        return pd.DataFrame()
    bench_ret = bench.pct_change()

    for ticker, name in reits_info.items():
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            hist  = stock.history(period="1y")["Close"]

            # 가격 데이터 없으면 skip (사명변경·상장폐지 등)
            if hist.empty or len(hist) < 2:
                print(f"  [Skip] {ticker}: 가격 데이터 없음 — 사명변경/상장폐지 확인 필요")
                continue

            ret   = hist.pct_change()
            combined = pd.concat([ret, bench_ret], axis=1).dropna()
            combined.columns = ["reit", "benchmark"]
            aligned_ret   = combined["reit"]
            aligned_bench = combined["benchmark"]

            # ── 기본 지표 ────────────────────────────────
            vol     = aligned_ret.std() * np.sqrt(252)
            cum_ret = hist.iloc[-1] / hist.iloc[0] - 1

            cov_matrix = np.cov(aligned_ret, aligned_bench)
            beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0

            sharpe = (cum_ret - 0.03) / vol if vol != 0 else 0

            # ── DCF 계산 ─────────────────────────────────
            current_price = info.get("regularMarketPrice") or hist.iloc[-1]
            dpu           = info.get("trailingAnnualDividendRate")
            nav_raw       = info.get("bookValue")          # fallback NAV

            wacc          = calculate_wacc(beta)
            growth_rate   = 0.03                           # 3% 기본 배당 성장률 가정

            dcf_value = None
            if dpu and dpu > 0:
                dcf_value = dcf_reit(
                    dpu_current      = dpu,
                    growth_rate      = growth_rate,
                    discount_rate    = wacc,
                    years            = 10,
                    perpetual_growth = 0.025,
                )

            nav_disc = None
            if nav_raw and nav_raw > 0:
                nav_disc = nav_discount_premium(current_price, nav_raw)

            # ── 업사이드 (DCF 기준) ───────────────────────
            upside = None
            if dcf_value and current_price and current_price > 0:
                upside = (dcf_value / current_price - 1) * 100

            results.append({
                "Ticker":       ticker,
                "Name":         name[:20],
                "Price":        round(current_price, 3) if current_price else None,
                "Return(%)":    round(cum_ret * 100, 2),
                "Vol(%)":       round(vol * 100, 2),
                "Beta":         round(beta, 2),
                "Sharpe":       round(sharpe, 2),
                "WACC(%)":      round(wacc * 100, 2),
                "DPU":          round(dpu, 4) if dpu else None,
                "DCF Value":    dcf_value,
                "Upside(%)":    round(upside, 1) if upside is not None else None,
                "NAV/Unit":     round(nav_raw, 3) if nav_raw else None,
                "NAV Disc(%)":  round(nav_disc, 1) if nav_disc is not None else None,
            })

        except Exception as e:
            print(f"  [Error] {ticker}: {e}")

    return pd.DataFrame(results)


# ─────────────────────────────────────────────
# 2. 차트 생성
# ─────────────────────────────────────────────
def _build_charts(df, perf_path="chart.png", dcf_path="chart_dcf.png"):
    """수익률 차트 + DCF 업사이드 차트 저장."""

    # ① 1Y 수익률 바 차트 (기존)
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = ["#003087" if r >= 0 else "#c0392b" for r in df["Return(%)"]]
    ax.bar(df["Name"], df["Return(%)"], color=colors)
    ax.set_title("1Y Cumulative Performance (%)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Return (%)")
    ax.tick_params(axis="x", rotation=20, labelsize=7.5)
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    ax.axhline(0, color="black", linewidth=0.8)
    plt.tight_layout()
    plt.savefig(perf_path, dpi=150)
    plt.close()

    # ② DCF Upside 차트 (DCF Value 있는 종목만)
    dcf_df = df[df["DCF Value"].notna() & df["Upside(%)"].notna()].copy()
    if not dcf_df.empty:
        fig2, ax2 = plt.subplots(figsize=(12, 5))
        up_colors = ["#27ae60" if u >= 0 else "#e74c3c" for u in dcf_df["Upside(%)"]]
        ax2.bar(dcf_df["Name"], dcf_df["Upside(%)"], color=up_colors)
        ax2.set_title("DCF Upside vs Current Price (%)", fontsize=13, fontweight="bold")
        ax2.set_ylabel("Upside (%)")
        ax2.tick_params(axis="x", rotation=20, labelsize=7.5)
        ax2.grid(axis="y", linestyle="--", alpha=0.6)
        ax2.axhline(0, color="black", linewidth=0.8)
        plt.tight_layout()
        plt.savefig(dcf_path, dpi=150)
        plt.close()
        return True   # DCF 차트 존재
    return False


# ─────────────────────────────────────────────
# 3. PDF 리포트 생성
# ─────────────────────────────────────────────
def generate_pdf_report(df, output_path="SG_REITs_Analysis.pdf"):

    has_dcf_chart = _build_charts(df)

    # ── PDF 클래스 ────────────────────────────────
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 15)
            self.cell(0, 10, "SG-REITs Automation Report", 0, 1, "C")
            self.set_font("Arial", "I", 10)
            self.cell(
                0, 8,
                f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d')}",
                0, 1, "R",
            )
            self.ln(3)

        def footer(self):
            self.set_y(-12)
            self.set_font("Arial", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")
            self.set_text_color(0, 0, 0)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ════════════════════════════════════════════
    # Section 1: 성과 요약 테이블
    # ════════════════════════════════════════════
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "  1. Performance Summary", 0, 1, "L", True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    perf_cols   = ["Ticker", "Name", "Return(%)", "Vol(%)", "Beta", "Sharpe"]
    perf_widths = [20, 46, 28, 22, 18, 22]  # 합계 = 156

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 215, 255)
    for col, w in zip(perf_cols, perf_widths):
        pdf.cell(w, 9, col, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", size=8)
    for i, (_, row) in enumerate(df.iterrows()):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 247, 255) if fill else pdf.set_fill_color(255, 255, 255)
        vals = [row["Ticker"], row["Name"],
                f"{row['Return(%)']}%", f"{row['Vol(%)']}%",
                str(row["Beta"]), str(row["Sharpe"])]
        for val, w in zip(vals, perf_widths):
            pdf.cell(w, 8, str(val), 1, 0, "C", fill)
        pdf.ln()

    # 1Y 수익률 차트
    pdf.ln(5)
    pdf.image("chart.png", x=10, w=190)

    # ════════════════════════════════════════════
    # Section 2: DCF 밸류에이션 테이블
    # ════════════════════════════════════════════
    pdf.add_page()
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "  2. DCF Valuation & NAV Analysis", 0, 1, "L", True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # 방법론 주석
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(
        0, 5,
        "Assumptions: Risk-free rate 2.5% | Market risk premium 6.0% | "
        "DPU growth 3.0% p.a. | Perpetual growth 2.5% | Projection period 10Y",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    dcf_cols   = ["Ticker", "Name", "Price", "DPU", "WACC(%)", "DCF Value", "Upside(%)", "NAV/Unit", "NAV Disc(%)"]
    dcf_widths = [18, 38, 16, 14, 18, 20, 18, 18, 20]  # 합계 = 180

    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 215, 255)
    for col, w in zip(dcf_cols, dcf_widths):
        pdf.cell(w, 9, col, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", size=7.5)
    for i, (_, row) in enumerate(df.iterrows()):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 247, 255) if fill else pdf.set_fill_color(255, 255, 255)

        def fmt(v, suffix=""):
            return f"{v}{suffix}" if pd.notna(v) and v is not None else "N/A"

        dcf_val_str = f"${row['DCF Value']:.3f}" if pd.notna(row.get("DCF Value")) and row.get("DCF Value") is not None else "N/A"
        nav_disc_str = fmt(row.get("NAV Disc(%)"), "%")

        # Upside 색상 표시
        upside = row.get("Upside(%)")
        if pd.notna(upside) and upside is not None:
            upside_str = f"{upside}%"
            if upside >= 10:
                pdf.set_text_color(0, 140, 0)
            elif upside <= -10:
                pdf.set_text_color(180, 0, 0)
            else:
                pdf.set_text_color(0, 0, 0)
        else:
            upside_str = "N/A"

        vals = [
            row["Ticker"],
            row["Name"],
            fmt(row.get("Price"), ""),
            fmt(row.get("DPU"), ""),
            fmt(row.get("WACC(%)"), "%"),
            dcf_val_str,
            upside_str,
            fmt(row.get("NAV/Unit"), ""),
            nav_disc_str,
        ]
        for val, w in zip(vals, dcf_widths):
            pdf.cell(w, 8, str(val), 1, 0, "C", fill)
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    # DCF 업사이드 차트
    if has_dcf_chart and os.path.exists("chart_dcf.png"):
        pdf.ln(5)
        pdf.image("chart_dcf.png", x=10, w=190)

    # ════════════════════════════════════════════
    # Section 3: 면책 조항
    # ════════════════════════════════════════════
    pdf.ln(8)
    pdf.set_font("Arial", "I", 7.5)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(
        0, 4.5,
        "Disclaimer: This report is generated automatically for informational purposes only "
        "and does not constitute investment advice. DCF valuations are based on simplified "
        "assumptions and should not be used as the sole basis for investment decisions. "
        "Past performance is not indicative of future results.",
    )

    pdf.output(output_path)
    print(f"  PDF saved → {output_path}")