import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

# 분석할 REIT 티커 리스트
reits = [
    "C38U.SI",  # CapitaLand Integrated Commercial Trust
    "A17U.SI",  # CapitaLand Ascendas REIT
    "N2IU.SI",  # Mapletree Pan Asia Commercial Trust
    "M44U.SI",  # Mapletree Logistics Trust
    "ME8U.SI",  # Mapletree Industrial Trust
    "BUOU.SI",  # Frasers Centrepoint Trust
    "AJBU.SI",  # Keppel DC REIT
    "J69U.SI",  # Frasers Logistics & Commercial Trust
    "M1GU.SI",  # Sabana Industrial REIT
    "HMN.SI",   # OUE Hospitality Trust
    "C2PU.SI",  # Parkway Life REIT
    "T82U.SI",  # Suntec REIT
    "J91U.SI",  # ESR-LOGOS REIT
    "TS0U.SI",  # OUE REIT
    "CY6U.SI",  # CapitaLand India Trust
]

# SGX 코드 매핑 (티커 → SGX 단축코드, sginvestors.io URL용)
SGX_CODE_MAP = {
    "C38U.SI": "c38u",
    "A17U.SI": "a17u",
    "N2IU.SI": "n2iu",
    "M44U.SI": "m44u",
    "ME8U.SI": "me8u",
    "BUOU.SI": "buou",
    "AJBU.SI": "ajbu",
    "J69U.SI": "j69u",
    "M1GU.SI": "m1gu",
    "HMN.SI":  "hmn",
    "C2PU.SI": "c2pu",
    "T82U.SI": "t82u",
    "J91U.SI": "j91u",
    "TS0U.SI": "ts0u",
    "CY6U.SI": "cy6u",
}

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

        # ── Gearing Ratio ──────────────────────────────
        # sginvestors 구조: <td>Gearing Ratio</td><td>XX.X%</td>
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                if "gearing" in label:
                    m = re.search(r"[\d.]+", value)
                    if m:
                        result["gearing_ratio"] = float(m.group()) / 100  # 0.XX 형태

                if "nav" in label and "unit" in label:
                    m = re.search(r"[\d.]+", value)
                    if m:
                        result["nav_per_unit"] = float(m.group())

        # ── 대안: <span> / <div> 방식 페이지 구조 대응 ──
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
data = pd.DataFrame(index=reits)

print("=== Yahoo Finance 기본 데이터 수집 ===")
for reit in reits:
    ticker = yf.Ticker(reit)
    info = ticker.info

    data.loc[reit, "Current Price"]    = info.get("regularMarketPrice")
    data.loc[reit, "DPU (Trailing)"]   = info.get("trailingAnnualDividendRate")
    data.loc[reit, "Dividend Yield"]   = info.get("trailingAnnualDividendYield")
    data.loc[reit, "Beta"]             = info.get("beta")
    data.loc[reit, "Market Cap"]       = info.get("marketCap")
    print(f"  {reit} ✓")

# ─────────────────────────────────────────────
# 4. Gearing & NAV 크롤링 (sginvestors.io)
# ─────────────────────────────────────────────
print("\n=== Gearing & NAV 크롤링 (sginvestors.io) ===")
for reit in reits:
    sgx_code = SGX_CODE_MAP.get(reit, reit.replace(".SI", "").lower())
    scraped = scrape_sginvestors(sgx_code)

    gearing = scraped["gearing_ratio"]
    nav     = scraped["nav_per_unit"]

    # NAV fallback: yfinance bookValue
    if nav is None:
        nav = get_nav_from_yfinance(reit)
        if nav:
            print(f"  {reit}: NAV fallback → yfinance bookValue = {nav:.4f}")

    data.loc[reit, "Gearing Ratio"] = gearing if gearing else None
    data.loc[reit, "NAV per Unit"]  = nav if nav else None

    status_g = f"{gearing:.1%}" if gearing else "N/A"
    status_n = f"{nav:.4f}" if nav else "N/A"
    print(f"  {reit}: Gearing={status_g}, NAV={status_n}")

    time.sleep(0.5)  # 서버 부하 방지

# ─────────────────────────────────────────────
# 5. WACC 추정 & 영구 성장률
# ─────────────────────────────────────────────
RISK_FREE_RATE    = 0.025
MARKET_RISK_PREM  = 0.06
PERPETUAL_GROWTH  = 0.025

for reit in reits:
    beta = data.loc[reit, "Beta"]
    if pd.notna(beta):
        wacc = RISK_FREE_RATE + float(beta) * MARKET_RISK_PREM
        data.loc[reit, "Estimated WACC"] = round(wacc, 4)

data["Perpetual Growth"] = PERPETUAL_GROWTH

# ─────────────────────────────────────────────
# 6. 결과 저장
# ─────────────────────────────────────────────
data.to_csv("sg_reits_dcf_inputs.csv")
print("\n=== 수집 완료 → sg_reits_dcf_inputs.csv 저장 ===")
print(data.to_string())