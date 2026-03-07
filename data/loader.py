"""
data/loader.py — yfinance 데이터 로딩 (캐시)
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

from dcf_valuation import calculate_wacc, dcf_reit, nav_discount_premium
from analysis import _get_trailing_dpu
from utils import REITS_CONFIG, DPU_GROWTH_RATE, PERPETUAL_GROWTH, DCF_YEARS


@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    """
    전체 REIT 유니버스 데이터 로드.
    1Y 수익률/변동성/베타/샤프 + DCF 내재가치/NAV 할인율 계산.
    Returns: DataFrame
    """
    rows = []
    bench = yf.Ticker("CLR.SI").history(period="1y")["Close"]
    bench_ret = bench.pct_change()

    for ticker, meta in REITS_CONFIG.items():
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            hist  = stock.history(period="1y")["Close"]

            if hist.empty or len(hist) < 2:
                st.warning(f"{ticker} ({meta['name']}): 가격 데이터 없음 — 사명변경/상장폐지 확인 필요")
                continue

            ret      = hist.pct_change()
            combined = pd.concat([ret, bench_ret], axis=1).dropna()
            combined.columns = ["reit", "bench"]

            vol     = combined["reit"].std() * np.sqrt(252)
            cum_ret = hist.iloc[-1] / hist.iloc[0] - 1
            cov     = np.cov(combined["reit"], combined["bench"])
            beta    = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0
            sharpe  = (cum_ret - 0.03) / vol if vol != 0 else 0

            price  = info.get("regularMarketPrice") or hist.iloc[-1]
            dpu    = _get_trailing_dpu(stock)
            dyield = info.get("trailingAnnualDividendYield")
            nav    = info.get("bookValue")
            wacc   = calculate_wacc(beta)

            dcf_val = None
            if dpu and dpu > 0:
                dcf_val = dcf_reit(dpu, DPU_GROWTH_RATE, wacc, years=DCF_YEARS, perpetual_growth=PERPETUAL_GROWTH)

            nav_disc = nav_discount_premium(price, nav) if nav else None
            upside   = (dcf_val / price - 1) * 100 if dcf_val and price else None

            rows.append({
                "Ticker":      ticker,
                "Name":        meta["name"],
                "Sector":      meta["sector"],
                "Price":       round(price, 3),
                "DPU":         round(dpu, 4) if dpu else None,
                "Yield(%)":    round(dyield * 100, 2) if dyield else None,
                "Return(%)":   round(cum_ret * 100, 2),
                "Vol(%)":      round(vol * 100, 2),
                "Beta":        round(beta, 2),
                "Sharpe":      round(sharpe, 2),
                "WACC(%)":     round(wacc * 100, 2),
                "DCF Value":   dcf_val,
                "Upside(%)":   round(upside, 1) if upside is not None else None,
                "NAV/Unit":    round(nav, 3) if nav else None,
                "NAV Disc(%)": round(nav_disc, 1) if nav_disc is not None else None,
            })
        except Exception as e:
            st.warning(f"{ticker} 로드 실패: {e}")

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def load_price_history(tickers):
    """종목 리스트의 1Y 일별 종가 히스토리 반환. Returns: dict[ticker → Series]"""
    result = {}
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period="1y")["Close"]
            result[t] = h
        except Exception:
            pass
    return result