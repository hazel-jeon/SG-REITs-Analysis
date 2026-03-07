# dcf_valuation.py
import numpy as np
import pandas as pd

RISK_FREE_RATE   = 0.025   # 싱가포르 10년 국채 (2026 기준)
MARKET_RISK_PREM = 0.06    # 아시아 시장 위험 프리미엄


def calculate_wacc(beta: float,
                   risk_free_rate: float = RISK_FREE_RATE,
                   market_risk_premium: float = MARKET_RISK_PREM) -> float:
    """CAPM 기반 WACC 추정."""
    return risk_free_rate + beta * market_risk_premium


def dcf_reit(dpu_current: float,
             growth_rate: float,
             discount_rate: float,
             years: int = 10,
             perpetual_growth: float = 0.025) -> float | None:
    """
    Gordon Growth Model + DCF로 REIT 내재가치(per unit) 계산.

    Args:
        dpu_current:     현재 연간 DPU (SGD)
        growth_rate:     예상 배당 성장률
        discount_rate:   WACC 또는 요구수익률
        years:           예측 기간 (기본 10년)
        perpetual_growth: 영구 성장률 (discount_rate보다 반드시 작아야 함)

    Returns:
        내재가치 (float) 또는 None (계산 불가 시)
    """
    if discount_rate <= perpetual_growth:
        return None
    if dpu_current is None or dpu_current <= 0:
        return None

    future_dpus = [dpu_current * (1 + growth_rate) ** t for t in range(1, years + 1)]
    pv_dpus     = [dpu / (1 + discount_rate) ** t for t, dpu in enumerate(future_dpus, 1)]

    # Terminal Value (Gordon Growth Model)
    tv    = future_dpus[-1] * (1 + perpetual_growth) / (discount_rate - perpetual_growth)
    pv_tv = tv / (1 + discount_rate) ** years

    return round(float(np.sum(pv_dpus)) + pv_tv, 4)


def nav_discount_premium(current_price: float, nav_per_unit: float) -> float | None:
    """
    현재가 대비 NAV 할인/프리미엄 비율(%).
    양수 = 프리미엄, 음수 = 할인.
    """
    if not nav_per_unit or nav_per_unit == 0:
        return None
    return round((current_price - nav_per_unit) / nav_per_unit * 100, 2)


# ─────────────────────────────────────────────
# 테스트용
# ─────────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "ticker":        "C38U.SI",
        "current_price": 1.85,
        "dpu_current":   0.098,
        "growth_rate":   0.03,
        "beta":          0.75,
        "nav_per_unit":  2.10,
    }

    wacc      = calculate_wacc(sample["beta"])
    dcf_value = dcf_reit(
        dpu_current      = sample["dpu_current"],
        growth_rate      = sample["growth_rate"],
        discount_rate    = wacc,
        years            = 10,
        perpetual_growth = 0.025,
    )
    disc_pct = nav_discount_premium(sample["current_price"], sample["nav_per_unit"])

    print(f"{sample['ticker']} 분석 결과:")
    print(f"  추정 WACC       : {wacc:.2%}")
    print(f"  DCF 내재가치    : ${dcf_value:.3f}" if dcf_value else "  DCF 계산 불가")
    print(f"  NAV Discount    : {disc_pct:.1f}%" if disc_pct is not None else "  NAV 데이터 없음")