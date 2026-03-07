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
# Monte Carlo DCF 시뮬레이션
# ─────────────────────────────────────────────
def monte_carlo_dcf(
    dpu_current: float,
    beta: float,
    n: int = 10000,
    years: int = 10,
    # 성장률 분포 파라미터
    growth_mean: float = 0.03,
    growth_std: float  = 0.01,
    # WACC 노이즈 파라미터
    wacc_std: float    = 0.005,
    # 영구성장률 분포 파라미터
    pg_mean: float     = 0.025,
    pg_std: float      = 0.005,
    seed: int          = 42,
) -> dict:
    """
    Monte Carlo 시뮬레이션으로 DCF 내재가치 분포 계산.

    Args:
        dpu_current : 현재 연간 DPU (SGD)
        beta        : REIT 베타 (WACC 기준값 계산에 사용)
        n           : 시뮬레이션 횟수 (기본 10,000회)
        growth_mean : 배당 성장률 평균
        growth_std  : 배당 성장률 표준편차
        wacc_std    : WACC 노이즈 표준편차
        pg_mean     : 영구 성장률 평균
        pg_std      : 영구 성장률 표준편차
        seed        : 재현성을 위한 랜덤 시드

    Returns:
        {
          "values"  : np.array  # 유효한 시뮬레이션 결과 전체
          "p10"     : float     # 10th percentile (비관 시나리오)
          "p50"     : float     # 50th percentile (중립, 중앙값)
          "p90"     : float     # 90th percentile (낙관 시나리오)
          "mean"    : float     # 평균 내재가치
          "std"     : float     # 표준편차
          "n_valid" : int       # 유효 시뮬레이션 수
          "params"  : dict      # 사용된 파라미터 기록
        }
    """
    if dpu_current is None or dpu_current <= 0:
        return {}

    rng        = np.random.default_rng(seed)
    base_wacc  = calculate_wacc(beta)

    # 파라미터 샘플링 (벡터화로 속도 최적화)
    growth_samples = rng.normal(growth_mean, growth_std,  n)
    wacc_noise     = rng.normal(0,           wacc_std,    n)
    pg_samples     = rng.normal(pg_mean,     pg_std,      n)
    wacc_samples   = base_wacc + wacc_noise

    results = []
    for g, wacc, pg in zip(growth_samples, wacc_samples, pg_samples):
        # 필수 조건: WACC > 영구성장률, 영구성장률 > 0
        if wacc <= pg or pg <= 0 or wacc <= 0:
            continue
        val = dcf_reit(dpu_current, g, wacc, years=years, perpetual_growth=pg)
        if val and val > 0:
            results.append(val)

    if not results:
        return {}

    arr = np.array(results)
    return {
        "values":  arr,
        "p10":     float(np.percentile(arr, 10)),
        "p50":     float(np.percentile(arr, 50)),
        "p90":     float(np.percentile(arr, 90)),
        "mean":    float(np.mean(arr)),
        "std":     float(np.std(arr)),
        "n_valid": len(arr),
        "params": {
            "base_wacc":   round(base_wacc, 4),
            "growth_mean": growth_mean,
            "growth_std":  growth_std,
            "wacc_std":    wacc_std,
            "pg_mean":     pg_mean,
            "pg_std":      pg_std,
            "n_total":     n,
        },
    }

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