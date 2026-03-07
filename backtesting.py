# backtesting.py
"""
DCF 업사이드 신호 백테스팅 모듈.

전략:
  - 과거 특정 시점(entry_date)에 yfinance DPU + Beta 데이터로 DCF 계산
  - DCF 업사이드가 threshold(%) 이상인 종목만 매수 (equal-weight)
  - exit_date(또는 현재)까지 보유 → 수익률 계산
  - 벤치마크(STI ETF: CLR.SI) 대비 Alpha 측정
"""

import yfinance as yf
import pandas as pd
import numpy as np
from dcf_valuation import calculate_wacc, dcf_reit


# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────
def _nearest_price(hist: pd.Series, date: pd.Timestamp) -> float | None:
    """히스토리에서 date에 가장 가까운 종가 반환 (±5 거래일 탐색)."""
    if hist.empty:
        return None
    # timezone 통일
    if hist.index.tz is not None:
        date = date.tz_localize(hist.index.tz) if date.tzinfo is None else date.tz_convert(hist.index.tz)
    else:
        date = date.replace(tzinfo=None)

    for delta in range(0, 6):
        for sign in [0, 1, -1]:
            d = date + pd.Timedelta(days=delta * sign)
            if d in hist.index:
                return float(hist[d])
    # fallback: 가장 가까운 날짜
    idx = hist.index.get_indexer([date], method="nearest")[0]
    return float(hist.iloc[idx]) if idx >= 0 else None


def _get_dpu_at(ticker: str, as_of: pd.Timestamp) -> float | None:
    """
    as_of 시점 기준 trailing DPU 추정.
    yfinance dividends 히스토리에서 as_of 이전 12개월 배당 합산.
    """
    try:
        divs = yf.Ticker(ticker).dividends
        if divs.empty:
            return None
        if divs.index.tz is not None:
            as_of_tz = as_of.tz_localize(divs.index.tz) if as_of.tzinfo is None else as_of
        else:
            as_of_tz = as_of.replace(tzinfo=None)

        window = divs[(divs.index <= as_of_tz) &
                      (divs.index > as_of_tz - pd.DateOffset(years=1))]
        return float(window.sum()) if not window.empty else None
    except Exception:
        return None


# ─────────────────────────────────────────────
# 핵심: 단일 시점 DCF 신호 생성
# ─────────────────────────────────────────────
def compute_dcf_signals(
    reits_config: dict,
    entry_date: pd.Timestamp,
    growth_rate: float = 0.03,
    perpetual_growth: float = 0.025,
    upside_threshold: float = 0.10,   # 10% 이상 업사이드면 매수 신호
) -> pd.DataFrame:
    """
    entry_date 시점 기준으로 각 REIT의 DCF 업사이드를 계산하고
    매수 신호(Signal=1) 여부를 반환.

    Returns: DataFrame with columns
        Ticker, Name, Entry_Price, DCF_Value, Upside(%), Signal
    """
    rows = []
    for ticker, meta in reits_config.items():
        try:
            name = meta["name"] if isinstance(meta, dict) else meta

            # 1. entry_date 기준 가격 히스토리 (entry 포함 과거 2년)
            period_start = entry_date - pd.DateOffset(years=2)
            hist = yf.Ticker(ticker).history(
                start=period_start.strftime("%Y-%m-%d"),
                end=(entry_date + pd.Timedelta(days=10)).strftime("%Y-%m-%d"),
            )["Close"]

            if hist.empty or len(hist) < 20:
                continue

            entry_price = _nearest_price(hist, entry_date)
            if entry_price is None:
                continue

            # 2. entry_date 기준 Beta (과거 1년 수익률로 계산)
            bench_hist = yf.Ticker("CLR.SI").history(
                start=(entry_date - pd.DateOffset(years=1)).strftime("%Y-%m-%d"),
                end=(entry_date + pd.Timedelta(days=10)).strftime("%Y-%m-%d"),
            )["Close"]

            ret       = hist.pct_change().dropna()
            bench_ret = bench_hist.pct_change().dropna()
            combined  = pd.concat([ret, bench_ret], axis=1).dropna()

            if len(combined) < 20:
                beta = 1.0  # 데이터 부족 시 시장 평균으로 가정
            else:
                combined.columns = ["reit", "bench"]
                cov  = np.cov(combined["reit"], combined["bench"])
                beta = cov[0,1] / cov[1,1] if cov[1,1] != 0 else 1.0

            # 3. entry_date 기준 trailing DPU
            dpu = _get_dpu_at(ticker, entry_date)
            if not dpu or dpu <= 0:
                continue

            # 4. DCF 계산
            wacc      = calculate_wacc(beta)
            dcf_value = dcf_reit(dpu, growth_rate, wacc,
                                 years=10, perpetual_growth=perpetual_growth)
            if dcf_value is None:
                continue

            upside = (dcf_value / entry_price - 1)
            signal = 1 if upside >= upside_threshold else 0

            rows.append({
                "Ticker":       ticker,
                "Name":         name[:20],
                "Entry_Price":  round(entry_price, 4),
                "Beta":         round(beta, 3),
                "DPU":          round(dpu, 4),
                "WACC(%)":      round(wacc * 100, 2),
                "DCF_Value":    round(dcf_value, 4),
                "Upside(%)":    round(upside * 100, 2),
                "Signal":       signal,
            })
        except Exception as e:
            print(f"  [Skip] {ticker}: {e}")

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# 핵심: 백테스팅 수익률 계산
# ─────────────────────────────────────────────
def run_backtest(
    signals_df: pd.DataFrame,
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    benchmark: str = "CLR.SI",
) -> dict:
    """
    signals_df의 Signal=1 종목을 equal-weight 매수 후
    exit_date까지 수익률 계산. 벤치마크와 Alpha 비교.

    Returns: dict {
        "portfolio_return"  : float   # 포트폴리오 총 수익률
        "benchmark_return"  : float   # 벤치마크 총 수익률
        "alpha"             : float   # 초과수익
        "details"           : DataFrame  # 종목별 수익률
        "equity_curve"      : DataFrame  # 일별 누적 수익률 곡선
        "benchmark_curve"   : Series     # 벤치마크 누적 수익률 곡선
        "n_long"            : int        # 매수 종목 수
        "n_total"           : int        # 전체 종목 수
        "sharpe"            : float      # 포트폴리오 Sharpe
        "max_drawdown"      : float      # 최대 낙폭
    }
    """
    long_df = signals_df[signals_df["Signal"] == 1].copy()
    n_long  = len(long_df)
    n_total = len(signals_df)

    start_str = entry_date.strftime("%Y-%m-%d")
    end_str   = (exit_date + pd.Timedelta(days=5)).strftime("%Y-%m-%d")

    # ── 벤치마크 수익률 ───────────────────────────
    bench_hist = yf.Ticker(benchmark).history(start=start_str, end=end_str)["Close"]
    bench_entry = _nearest_price(bench_hist, entry_date)
    bench_exit  = _nearest_price(bench_hist, exit_date)
    bench_return = (bench_exit / bench_entry - 1) if (bench_entry and bench_exit) else 0.0

    # 벤치마크 일별 곡선 (정규화)
    bench_curve = bench_hist / bench_hist.iloc[0] - 1

    if n_long == 0:
        return {
            "portfolio_return": 0.0,
            "benchmark_return": bench_return,
            "alpha":            -bench_return,
            "details":          pd.DataFrame(),
            "equity_curve":     pd.DataFrame(),
            "benchmark_curve":  bench_curve,
            "n_long":           0,
            "n_total":          n_total,
            "sharpe":           None,
            "max_drawdown":     None,
        }

    # ── 종목별 수익률 + 일별 가격 ─────────────────
    detail_rows = []
    daily_prices = {}

    for _, row in long_df.iterrows():
        ticker = row["Ticker"]
        try:
            hist = yf.Ticker(ticker).history(start=start_str, end=end_str)["Close"]
            if hist.empty:
                continue

            exit_price  = _nearest_price(hist, exit_date)
            entry_price = row["Entry_Price"]

            if exit_price is None:
                continue

            total_ret = exit_price / entry_price - 1

            detail_rows.append({
                "Ticker":        ticker,
                "Name":          row["Name"],
                "Entry_Price":   entry_price,
                "Exit_Price":    round(exit_price, 4),
                "Return(%)":     round(total_ret * 100, 2),
                "DCF_Upside(%)": row["Upside(%)"],
                "Signal":        row["Signal"],
            })

            # 일별 정규화 가격 (entry=0 기준)
            daily_prices[ticker] = hist / entry_price - 1

        except Exception as e:
            print(f"  [Backtest skip] {ticker}: {e}")

    if not detail_rows:
        return {
            "portfolio_return": 0.0,
            "benchmark_return": bench_return,
            "alpha":            -bench_return,
            "details":          pd.DataFrame(),
            "equity_curve":     pd.DataFrame(),
            "benchmark_curve":  bench_curve,
            "n_long":           0,
            "n_total":          n_total,
            "sharpe":           None,
            "max_drawdown":     None,
        }

    details_df = pd.DataFrame(detail_rows)

    # ── Equal-weight 포트폴리오 일별 수익률 곡선 ──
    price_df     = pd.DataFrame(daily_prices).dropna(how="all")
    eq_curve     = price_df.mean(axis=1)           # equal-weight 평균
    daily_ret    = eq_curve.diff().dropna()

    port_return  = float(eq_curve.iloc[-1]) if not eq_curve.empty else 0.0

    # ── 성과 지표 ─────────────────────────────────
    ann_factor = 252
    sharpe = None
    if len(daily_ret) > 10:
        mean_d = daily_ret.mean()
        std_d  = daily_ret.std()
        if std_d > 0:
            sharpe = round((mean_d / std_d) * np.sqrt(ann_factor), 3)

    max_drawdown = None
    if not eq_curve.empty:
        roll_max  = (1 + eq_curve).cummax()
        drawdown  = (1 + eq_curve) / roll_max - 1
        max_drawdown = round(float(drawdown.min()) * 100, 2)

    alpha = port_return - bench_return

    return {
        "portfolio_return": round(port_return * 100, 2),
        "benchmark_return": round(bench_return * 100, 2),
        "alpha":            round(alpha * 100, 2),
        "details":          details_df,
        "equity_curve":     eq_curve,
        "benchmark_curve":  bench_curve,
        "n_long":           n_long,
        "n_total":          n_total,
        "sharpe":           sharpe,
        "max_drawdown":     max_drawdown,
    }


# ─────────────────────────────────────────────
# 멀티 기간 백테스팅 (롤링)
# ─────────────────────────────────────────────
def rolling_backtest(
    reits_config: dict,
    periods: list[tuple],   # [(entry_date_str, exit_date_str, label), ...]
    upside_threshold: float = 0.10,
    benchmark: str = "CLR.SI",
) -> pd.DataFrame:
    """
    여러 기간에 걸쳐 백테스팅을 반복 실행해
    전략의 일관성을 검증.

    Returns: DataFrame with columns
        Period, Entry, Exit, Portfolio(%), Benchmark(%), Alpha(%), N_Long, Sharpe, MaxDD(%)
    """
    summary_rows = []

    for entry_str, exit_str, label in periods:
        entry_dt = pd.Timestamp(entry_str)
        exit_dt  = pd.Timestamp(exit_str)

        print(f"  Rolling backtest: {label} ({entry_str} → {exit_str})")

        signals = compute_dcf_signals(
            reits_config, entry_dt,
            upside_threshold=upside_threshold,
        )
        if signals.empty:
            continue

        result = run_backtest(signals, entry_dt, exit_dt, benchmark=benchmark)

        summary_rows.append({
            "Period":         label,
            "Entry":          entry_str,
            "Exit":           exit_str,
            "Portfolio(%)":   result["portfolio_return"],
            "Benchmark(%)":   result["benchmark_return"],
            "Alpha(%)":       result["alpha"],
            "N_Long":         result["n_long"],
            "Sharpe":         result["sharpe"],
            "MaxDD(%)":       result["max_drawdown"],
        })

    return pd.DataFrame(summary_rows)


# ─────────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from main import REITS_CONFIG

    entry = pd.Timestamp("2024-01-02")
    exit_ = pd.Timestamp("2024-12-31")

    print("=== DCF 신호 생성 ===")
    signals = compute_dcf_signals(REITS_CONFIG, entry, upside_threshold=0.10)
    print(signals[["Ticker", "Entry_Price", "DCF_Value", "Upside(%)", "Signal"]])

    print(f"\n매수 신호 종목: {signals[signals['Signal']==1]['Ticker'].tolist()}")

    print("\n=== 백테스팅 실행 ===")
    result = run_backtest(signals, entry, exit_)
    print(f"Portfolio Return : {result['portfolio_return']:+.2f}%")
    print(f"Benchmark Return : {result['benchmark_return']:+.2f}%")
    print(f"Alpha            : {result['alpha']:+.2f}%")
    print(f"Sharpe           : {result['sharpe']}")
    print(f"Max Drawdown     : {result['max_drawdown']}%")
    print(result["details"])