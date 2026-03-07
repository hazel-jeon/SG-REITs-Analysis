# portfolio_optimizer.py
"""
포트폴리오 최적화 모듈.

세 가지 전략:
  1. Max Sharpe  — 샤프 비율 최대화 (Mean-Variance)
  2. Min Vol     — 최소 분산 포트폴리오
  3. DCF Weighted — DCF 업사이드 비례 가중 (음수 업사이드 종목 제외)

효율적 프론티어도 계산해 시각화 데이터를 제공.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
from utils import RISK_FREE_RATE


# ─────────────────────────────────────────────
# 1. 핵심 계산 유틸
# ─────────────────────────────────────────────
def _portfolio_performance(weights: np.ndarray,
                           mean_returns: np.ndarray,
                           cov_matrix: np.ndarray,
                           risk_free: float = RISK_FREE_RATE,
                           ann_factor: int = 252) -> tuple[float, float, float]:
    """
    포트폴리오 연환산 수익률, 변동성, 샤프 반환.
    Returns: (return, volatility, sharpe)
    """
    port_return = np.dot(weights, mean_returns) * ann_factor
    port_vol    = np.sqrt(weights @ cov_matrix @ weights) * np.sqrt(ann_factor)
    sharpe      = (port_return - risk_free) / port_vol if port_vol > 0 else 0.0
    return float(port_return), float(port_vol), float(sharpe)


def _base_constraints_and_bounds(n: int,
                                  min_weight: float = 0.0,
                                  max_weight: float = 1.0) -> tuple:
    """기본 제약 조건 (비중 합 = 1) 및 경계값 반환."""
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = tuple((min_weight, max_weight) for _ in range(n))
    return constraints, bounds


# ─────────────────────────────────────────────
# 2. 전략별 최적화
# ─────────────────────────────────────────────
def max_sharpe(mean_returns: np.ndarray,
               cov_matrix: np.ndarray,
               risk_free: float = RISK_FREE_RATE,
               min_weight: float = 0.0,
               max_weight: float = 0.4) -> dict:
    """
    샤프 비율 최대화 포트폴리오.
    max_weight: 단일 종목 최대 비중 (기본 40%, 과집중 방지)
    """
    n = len(mean_returns)
    constraints, bounds = _base_constraints_and_bounds(n, min_weight, max_weight)

    def neg_sharpe(w):
        _, vol, sharpe = _portfolio_performance(w, mean_returns, cov_matrix, risk_free)
        return -sharpe

    w0 = np.ones(n) / n  # equal-weight 초기값
    result = minimize(neg_sharpe, w0, method="SLSQP",
                      bounds=bounds, constraints=constraints,
                      options={"maxiter": 1000, "ftol": 1e-12})

    weights = result.x
    ret, vol, sharpe = _portfolio_performance(weights, mean_returns, cov_matrix, risk_free)
    return {
        "weights":    weights,
        "return":     ret,
        "volatility": vol,
        "sharpe":     sharpe,
        "strategy":   "Max Sharpe",
        "success":    result.success,
    }


def min_volatility(mean_returns: np.ndarray,
                   cov_matrix: np.ndarray,
                   risk_free: float = RISK_FREE_RATE,
                   min_weight: float = 0.0,
                   max_weight: float = 0.4) -> dict:
    """최소 분산 포트폴리오."""
    n = len(mean_returns)
    constraints, bounds = _base_constraints_and_bounds(n, min_weight, max_weight)

    def port_vol(w):
        return np.sqrt(w @ cov_matrix @ w) * np.sqrt(252)

    w0 = np.ones(n) / n
    result = minimize(port_vol, w0, method="SLSQP",
                      bounds=bounds, constraints=constraints,
                      options={"maxiter": 1000, "ftol": 1e-12})

    weights = result.x
    ret, vol, sharpe = _portfolio_performance(weights, mean_returns, cov_matrix, risk_free)
    return {
        "weights":    weights,
        "return":     ret,
        "volatility": vol,
        "sharpe":     sharpe,
        "strategy":   "Min Volatility",
        "success":    result.success,
    }


def dcf_weighted(mean_returns: np.ndarray,
                 cov_matrix: np.ndarray,
                 upsides: np.ndarray,
                 risk_free: float = RISK_FREE_RATE) -> dict:
    """
    DCF 업사이드 비례 가중 포트폴리오.
    - 업사이드 양수 종목만 포함
    - 비중 = 업사이드 / sum(양수 업사이드)
    - 최적화 없음 (규칙 기반)
    """
    upside_clipped = np.maximum(upsides, 0)  # 음수 → 0
    total = upside_clipped.sum()

    if total <= 0:
        # 업사이드 양수 종목이 없으면 equal-weight 폴백
        weights = np.ones(len(mean_returns)) / len(mean_returns)
    else:
        weights = upside_clipped / total

    ret, vol, sharpe = _portfolio_performance(weights, mean_returns, cov_matrix, risk_free)
    return {
        "weights":    weights,
        "return":     ret,
        "volatility": vol,
        "sharpe":     sharpe,
        "strategy":   "DCF Weighted",
        "success":    True,
    }


def equal_weight(mean_returns: np.ndarray,
                 cov_matrix: np.ndarray,
                 risk_free: float = RISK_FREE_RATE) -> dict:
    """Equal-weight 기준선 포트폴리오."""
    n = len(mean_returns)
    weights = np.ones(n) / n
    ret, vol, sharpe = _portfolio_performance(weights, mean_returns, cov_matrix, risk_free)
    return {
        "weights":    weights,
        "return":     ret,
        "volatility": vol,
        "sharpe":     sharpe,
        "strategy":   "Equal Weight",
        "success":    True,
    }


# ─────────────────────────────────────────────
# 3. 효율적 프론티어
# ─────────────────────────────────────────────
def efficient_frontier(mean_returns: np.ndarray,
                       cov_matrix: np.ndarray,
                       n_points: int = 80,
                       min_weight: float = 0.0,
                       max_weight: float = 0.4) -> pd.DataFrame:
    """
    목표 수익률 범위에서 최소 변동성 포트폴리오를 반복 계산해
    효율적 프론티어 곡선 데이터를 반환.

    Returns: DataFrame(columns=["Return", "Volatility", "Sharpe"])
    """
    n = len(mean_returns)
    ann_mean = mean_returns * 252

    ret_min = float(ann_mean.min()) * 0.8
    ret_max = float(ann_mean.max()) * 1.1
    target_returns = np.linspace(ret_min, ret_max, n_points)

    frontier_rows = []

    for target in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, mean_returns) * 252 - t},
        ]
        bounds = tuple((min_weight, max_weight) for _ in range(n))

        result = minimize(
            lambda w: np.sqrt(w @ cov_matrix @ w) * np.sqrt(252),
            np.ones(n) / n,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-10},
        )

        if result.success:
            vol = float(np.sqrt(result.x @ cov_matrix @ result.x) * np.sqrt(252))
            sharpe = (target - RISK_FREE_RATE) / vol if vol > 0 else 0.0
            frontier_rows.append({
                "Return":     round(target * 100, 3),
                "Volatility": round(vol * 100, 3),
                "Sharpe":     round(sharpe, 3),
            })

    return pd.DataFrame(frontier_rows)


# ─────────────────────────────────────────────
# 4. 전체 최적화 실행 (메인 인터페이스)
# ─────────────────────────────────────────────
def run_optimization(df: pd.DataFrame,
                     price_histories: dict,
                     min_weight: float = 0.0,
                     max_weight: float = 0.4) -> dict:
    """
    df: load_data()에서 반환된 REIT 분석 DataFrame
    price_histories: {ticker: pd.Series(Close)}

    Returns: {
        "tickers"   : list[str],
        "names"     : list[str],
        "mean_ret"  : np.ndarray,
        "cov"       : np.ndarray,
        "frontier"  : pd.DataFrame,
        "strategies": {
            "equal_weight" : dict,
            "max_sharpe"   : dict,
            "min_vol"      : dict,
            "dcf_weighted" : dict,
        }
    }
    """
    # ── 1. 수익률 매트릭스 구성 ───────────────────
    # price_histories에 있는 ticker만 사용 (데이터 없는 종목 제외)
    valid_tickers = [
        t for t in df["Ticker"]
        if t in price_histories and not price_histories[t].empty
    ]

    if len(valid_tickers) < 2:
        return {}

    # 일별 수익률 DataFrame
    price_df = pd.DataFrame({t: price_histories[t] for t in valid_tickers})
    ret_df   = price_df.pct_change().dropna()

    # 데이터 부족 종목 제거 (60 거래일 미만)
    valid_tickers = [t for t in valid_tickers if ret_df[t].count() >= 60]
    ret_df = ret_df[valid_tickers].dropna()

    if len(valid_tickers) < 2:
        return {}

    mean_ret  = ret_df.mean().values          # 일별 평균 수익률
    cov       = ret_df.cov().values           # 일별 공분산 행렬
    names     = df.set_index("Ticker").loc[valid_tickers, "Name"].tolist()

    # ── 2. DCF 업사이드 벡터 ─────────────────────
    dcf_map  = df.set_index("Ticker")["Upside(%)"].to_dict()
    upsides  = np.array([dcf_map.get(t, 0) or 0 for t in valid_tickers])

    # ── 3. 각 전략 최적화 ────────────────────────
    strategies = {
        "equal_weight": equal_weight(mean_ret, cov),
        "max_sharpe":   max_sharpe(mean_ret, cov,
                                   min_weight=min_weight, max_weight=max_weight),
        "min_vol":      min_volatility(mean_ret, cov,
                                       min_weight=min_weight, max_weight=max_weight),
        "dcf_weighted": dcf_weighted(mean_ret, cov, upsides),
    }

    # ── 4. 효율적 프론티어 ───────────────────────
    frontier = efficient_frontier(mean_ret, cov,
                                  min_weight=min_weight, max_weight=max_weight)

    return {
        "tickers":    valid_tickers,
        "names":      names,
        "mean_ret":   mean_ret,
        "cov":        cov,
        "upsides":    upsides,
        "frontier":   frontier,
        "strategies": strategies,
    }


# ─────────────────────────────────────────────
# 5. 결과 요약 DataFrame 생성 (UI용)
# ─────────────────────────────────────────────
def summarize_weights(opt_result: dict) -> pd.DataFrame:
    """
    각 전략의 종목별 비중을 비교하는 DataFrame 반환.
    columns: Ticker, Name, EqualWeight(%), MaxSharpe(%), MinVol(%), DCFWeighted(%)
    """
    tickers    = opt_result["tickers"]
    names      = opt_result["names"]
    strategies = opt_result["strategies"]

    rows = []
    for i, (ticker, name) in enumerate(zip(tickers, names)):
        rows.append({
            "Ticker":          ticker,
            "Name":            name,
            "Equal Weight(%)": round(strategies["equal_weight"]["weights"][i] * 100, 1),
            "Max Sharpe(%)":   round(strategies["max_sharpe"]["weights"][i] * 100, 1),
            "Min Vol(%)":      round(strategies["min_vol"]["weights"][i] * 100, 1),
            "DCF Weighted(%)": round(strategies["dcf_weighted"]["weights"][i] * 100, 1),
        })
    return pd.DataFrame(rows)


def summarize_performance(opt_result: dict) -> pd.DataFrame:
    """
    각 전략의 수익률/변동성/샤프 비교 DataFrame 반환.
    """
    strategies = opt_result["strategies"]
    rows = []
    for key, res in strategies.items():
        rows.append({
            "Strategy":      res["strategy"],
            "Exp Return(%)": round(res["return"] * 100, 2),
            "Volatility(%)": round(res["volatility"] * 100, 2),
            "Sharpe":        round(res["sharpe"], 3),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import yfinance as yf
    from utils import REITS_CONFIG

    print("=== 포트폴리오 최적화 테스트 ===")

    # 간단한 더미 데이터로 테스트
    tickers = list(REITS_CONFIG.keys())[:8]
    price_histories = {}
    for t in tickers:
        h = yf.Ticker(t).history(period="1y")["Close"]
        if not h.empty:
            price_histories[t] = h

    # 더미 df
    rows = []
    for t in tickers:
        if t in price_histories:
            rows.append({"Ticker": t, "Name": REITS_CONFIG[t]["name"],
                         "Upside(%)": np.random.uniform(-20, 50)})
    df = pd.DataFrame(rows)

    result = run_optimization(df, price_histories)
    if result:
        print("\n--- 전략별 성과 ---")
        print(summarize_performance(result).to_string(index=False))
        print("\n--- 종목별 비중 ---")
        print(summarize_weights(result).to_string(index=False))
        print(f"\n효율적 프론티어 포인트 수: {len(result['frontier'])}")