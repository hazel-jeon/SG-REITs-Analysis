# utils.py
"""
프로젝트 전체에서 공유되는 상수 및 유틸리티.
dcf_valuation.py, reit_data_collector.py 등에서 import해서 사용.
"""

# ── 시장 파라미터 ─────────────────────────────
RISK_FREE_RATE    = 0.025   # 싱가포르 10년 국채 (2026 기준)
MARKET_RISK_PREM  = 0.06    # 아시아-태평양 시장 위험 프리미엄
PERPETUAL_GROWTH  = 0.025   # 싱가포르 장기 GDP 성장률
DPU_GROWTH_RATE   = 0.03    # 기본 배당 성장률 가정
DCF_YEARS         = 10      # DCF 예측 기간
BENCHMARK_TICKER  = "CLR.SI"  # STI ETF

# ── REIT 유니버스 ─────────────────────────────
# 모든 모듈의 단일 진실 공급원(Single Source of Truth)
REITS_CONFIG = {
    "C38U.SI": {"name": "CapitaLand Integrated",   "sector": "Retail/Office"},
    "A17U.SI": {"name": "CapitaLand Ascendas",     "sector": "Industrial"},
    "N2IU.SI": {"name": "Mapletree Pan Asia",       "sector": "Retail/Office"},
    "M44U.SI": {"name": "Mapletree Logistics",      "sector": "Logistics"},
    "ME8U.SI": {"name": "Mapletree Industrial",     "sector": "Industrial"},
    "BUOU.SI": {"name": "Frasers Centrepoint",      "sector": "Retail/Office"},
    "AJBU.SI": {"name": "Keppel DC REIT",           "sector": "Data Centre"},
    "J69U.SI": {"name": "Frasers Logistics",        "sector": "Logistics"},
    "C2PU.SI": {"name": "Parkway Life REIT",        "sector": "Healthcare"},
    "T82U.SI": {"name": "Suntec REIT",              "sector": "Retail/Office"},
    "TS0U.SI": {"name": "OUE REIT",                 "sector": "Hospitality"},
    "CY6U.SI": {"name": "CapitaLand India Trust",   "sector": "Industrial"},
    "HMN.SI":  {"name": "CapitaLand Ascott Trust",  "sector": "Hospitality"},
    "JYEU.SI": {"name": "Lendlease Global REIT",    "sector": "Retail/Office"},
    "Q5T.SI":  {"name": "Far East Hospitality",     "sector": "Hospitality"},
}

# ── SGX 코드 매핑 (sginvestors.io 크롤링용) ──
SGX_CODE_MAP = {
    "C38U.SI": "c38u",
    "A17U.SI": "a17u",
    "N2IU.SI": "n2iu",
    "M44U.SI": "m44u",
    "ME8U.SI": "me8u",
    "BUOU.SI": "buou",
    "AJBU.SI": "ajbu",
    "J69U.SI": "j69u",
    "C2PU.SI": "c2pu",
    "T82U.SI": "t82u",
    "TS0U.SI": "ts0u",
    "CY6U.SI": "cy6u",
    "HMN.SI":  "hmn",
    "JYEU.SI": "jyeu",
    "Q5T.SI":  "q5t",
}