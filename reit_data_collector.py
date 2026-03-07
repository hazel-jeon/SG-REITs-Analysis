# reit_data_collector.py
"""
sginvestors.io 크롤링으로 Gearing Ratio & NAV per Unit 수집.
yfinance 기본 데이터(가격, DPU, Beta, 시총)도 함께 수집해
sg_reits_data.csv로 저장. DCF 입력값으로 활용 가능.
"""

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

from utils import REITS_CONFIG, SGX_CODE_MAP, RISK_FREE_RATE, MARKET_RISK_PREM, PERPETUAL_GROWTH

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ─────────────────────────────────────────────
# 1. sginvestors.io 크롤링: Gearing Ratio & NAV
# ─────────────────────────────────────────────
def scrape_sginvestors(sgx_code: str) -> dict:
    """
    sginvestors.io/sgx/reit/{code}/overview 에서
    Gearing Ratio(%)와 NAV per Unit(SGD) 파싱.
    실패 시 None 반환.
    """
    result = {"gearing_ratio": None, "nav_per_unit": None}
    url = f"https://sginvestors.io/sgx/reit/{sgx_code}/overview"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                if "gearing" in label:
                    m = re.search(r"[\d.]+", value)
                    if m:
                        result["gearing_ratio"] = float(m.group()) / 100

                if "nav" in label and "unit" in label:
                    m = re.search(r"[\d.]+", value)
                    if m:
                        result["nav_per_unit"] = float(m.group())

        # 대안: <span> / <div> 방식 페이지 구조 대응
        if result["gearing_ratio"] is None:
            for tag in soup.find_all(string=re.compile(r"(?i)gearing")):
                parent = tag.find_parent()
                if parent:
                    sibling = parent.find_next_sibling()
                    if sibling:
                        m = re.search(r"[\d.]+", sibling.get_text())
                        if m:
                            result["gearing_ratio"] = float(m.group()) / 100
                            break

        if result["nav_per_unit"] is None:
            for tag in soup.find_all(string=re.compile(r"(?i)nav per unit")):
                parent = tag.find_parent()
                if parent:
                    sibling = parent.find_next_sibling()
                    if sibling:
                        m = re.search(r"[\d.]+", sibling.get_text())
                        if m:
                            result["nav_per_unit"] = float(m.group())
                            break

    except requests.exceptions.RequestException as e:
        print(f"  [HTTP Error] {sgx_code}: {e}")
    except Exception as e:
        print(f"  [Parse Error] {sgx_code}: {e}")

    return result


# ─────────────────────────────────────────────
# 2. Yahoo Finance fallback: bookValue → NAV
# ─────────────────────────────────────────────
def get_nav_from_yfinance(ticker: str) -> float | None:
    """
    yfinance info의 bookValue를 NAV per unit 대용으로 사용.
    sginvestors에서 NAV를 못 가져왔을 때 fallback.
    """
    try:
        info = yf.Ticker(ticker).info
        bv = info.get("bookValue")
        return float(bv) if bv else None
    except Exception:
        return None


# ─────────────────────────────────────────────
# 3. 메인 데이터 수집
# ─────────────────────────────────────────────
def collect_all(reits_config: dict = REITS_CONFIG) -> pd.DataFrame:
    """
    REITS_CONFIG 기준으로 Yahoo Finance + sginvestors.io 데이터를 수집하고
    DataFrame으로 반환. sg_reits_data.csv에도 저장.
    """
    tickers = list(reits_config.keys())
    data = pd.DataFrame(index=tickers)

    print("=== Yahoo Finance 기본 데이터 수집 ===")
    for ticker in tickers:
        info = yf.Ticker(ticker).info
        data.loc[ticker, "Name"]             = reits_config[ticker]["name"]
        data.loc[ticker, "Sector"]           = reits_config[ticker]["sector"]
        data.loc[ticker, "Current Price"]    = info.get("regularMarketPrice")
        data.loc[ticker, "DPU (Trailing)"]   = info.get("trailingAnnualDividendRate")
        data.loc[ticker, "Dividend Yield"]   = info.get("trailingAnnualDividendYield")
        data.loc[ticker, "Beta"]             = info.get("beta")
        data.loc[ticker, "Market Cap"]       = info.get("marketCap")
        print(f"  {ticker} ({reits_config[ticker]['name']}) ✓")

    print("\n=== Gearing & NAV 크롤링 (sginvestors.io) ===")
    for ticker in tickers:
        sgx_code = SGX_CODE_MAP.get(ticker, ticker.replace(".SI", "").lower())
        scraped  = scrape_sginvestors(sgx_code)

        gearing = scraped["gearing_ratio"]
        nav     = scraped["nav_per_unit"]

        # NAV fallback: yfinance bookValue
        if nav is None:
            nav = get_nav_from_yfinance(ticker)
            if nav:
                print(f"  {ticker}: NAV fallback → yfinance bookValue = {nav:.4f}")

        data.loc[ticker, "Gearing Ratio"] = gearing
        data.loc[ticker, "NAV per Unit"]  = nav

        status_g = f"{gearing:.1%}" if gearing else "N/A"
        status_n = f"{nav:.4f}" if nav else "N/A"
        print(f"  {ticker}: Gearing={status_g}, NAV={status_n}")
        time.sleep(0.5)

    print("\n=== WACC 추정 ===")
    for ticker in tickers:
        beta = data.loc[ticker, "Beta"]
        if pd.notna(beta):
            wacc = RISK_FREE_RATE + float(beta) * MARKET_RISK_PREM
            data.loc[ticker, "Estimated WACC"] = round(wacc, 4)

    data["Perpetual Growth"] = PERPETUAL_GROWTH

    data.to_csv("sg_reits_data.csv")
    print("\n=== 수집 완료 → sg_reits_data.csv 저장 ===")
    print(data.to_string())
    return data


if __name__ == "__main__":
    collect_all()