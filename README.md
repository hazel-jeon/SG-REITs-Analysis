# 🏙️ SG-REITs Analysis Dashboard

> An end-to-end investment analysis pipeline covering **performance tracking → DCF valuation → Monte Carlo simulation → strategy backtesting** across 15 Singapore-listed REITs.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![yfinance](https://img.shields.io/badge/yfinance-0.2.x-4B8BBE?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 📌 Overview

The Singapore REIT (S-REIT) market is one of the largest in Asia, offering stable dividend income and diversified sector exposure. This project was built to answer four core investment questions:

- **"Which S-REITs are currently undervalued?"** → DCF intrinsic value vs. current price
- **"What is the range of intrinsic value under uncertainty?"** → Monte Carlo DCF simulation
- **"Has the DCF upside signal actually worked in practice?"** → Strategy backtesting & alpha measurement
- **"How effective is cross-sector diversification?"** → Return correlation matrix

---

## ✨ Features

### 📈 Tab 1 — Performance
- 1Y cumulative return bar chart with sector-based colour coding
- Risk vs. Return scatter plot
- Normalised price history comparison with multi-REIT selection

### 💰 Tab 2 — DCF Valuation
- CAPM-based WACC estimation (Risk-free rate 2.5%, Market risk premium 6.0%)
- Gordon Growth Model + 10-year DCF to derive per-unit intrinsic value
- Auto colour-coded upside/downside, NAV discount/premium analysis

### 🗺️ Tab 3 — Sector Analysis
- Sector composition donut chart + radar chart (Return / Yield / Sharpe / DCF Upside)
- Sharpe vs. Yield bubble chart for risk-adjusted return positioning
- Per-sector REIT detail cards with clickable sub-tabs

### 📊 Tab 4 — Correlation
- Return correlation heatmap sorted by sector with boundary lines
- Auto-extracted Top 5 low-correlation pairs (best diversification) & Top 5 high-correlation pairs
- Sector-level average correlation heatmap

### 🎲 Tab 5 — Monte Carlo DCF
- Normal-distribution noise on growth rate, WACC, and perpetual growth → 10,000 simulations
- Intrinsic value distribution with P10 (Bear) / P50 (Base) / P90 (Bull) scenarios
- Real-time probability of exceeding current price
- All parameters adjustable via expander panel

### ⏱️ Tab 6 — Backtesting
- Trailing DPU calculated from historical dividend records as of Entry Date — no look-ahead bias
- Equal-weight long-only portfolio for REITs with DCF upside ≥ threshold
- Alpha measured against STI ETF (CLR.SI) benchmark
- Cumulative return curve and per-ticker return table
- Rolling backtest across 2022 / 2023 / 2024 to validate strategy consistency

### 🤖 Automation Pipeline (`main.py`)
- Data collection → PDF report generation → automated email delivery
- Scheduled daily via GitHub Actions cron

---

## 🗂️ Project Structure

```
SG-REITs-Analysis/
│
├── app.py                  # Streamlit dashboard (main UI)
├── main.py                 # Automation pipeline entry point
│
├── analysis.py             # Market data analysis + PDF report generation
├── dcf_valuation.py        # DCF / WACC / NAV / Monte Carlo calculation module
├── backtesting.py          # DCF signal backtesting module
├── reit_data_collector.py  # Gearing Ratio / NAV scraping (sginvestors.io)
├── mailer.py               # Gmail SMTP email delivery
├── utils.py                # Shared utilities
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/hazel-jeon/SG-REITs-Analysis.git
cd SG-REITs-Analysis
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the dashboard
```bash
streamlit run app.py
```

### 4. Run the automation pipeline (PDF + email)
```bash
python main.py
```

---

## 🔐 Email Automation Setup

Generate a Gmail App Password and set the following environment variables.

**Local:**
```bash
export EMAIL_USER="your@gmail.com"
export EMAIL_PASS="your-16-char-app-password"
```

**GitHub Actions:**  
Add both secrets under `Settings → Secrets and variables → Actions`
```
EMAIL_USER  →  your@gmail.com
EMAIL_PASS  →  your-16-char-app-password
```

---

## 🤖 GitHub Actions Scheduling

Add `.github/workflows/daily_report.yml` to automatically generate and email the analysis report every morning.

```yaml
name: Daily SG-REITs Report

on:
  schedule:
    - cron: '0 1 * * *'   # Daily at UTC 01:00 (SGT 09:00)
  workflow_dispatch:        # Manual trigger also supported

jobs:
  run-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          EMAIL_USER: ${{ secrets.EMAIL_USER }}
          EMAIL_PASS: ${{ secrets.EMAIL_PASS }}
```

---

## 📐 Methodology

### DCF Valuation
```
Intrinsic Value = Σ [DPU_t / (1+WACC)^t]  +  Terminal Value
                                         
Terminal Value = DPU_10 × (1+g) / (WACC - g)

WACC = Rf + β × (Rm - Rf)
     = 2.5% + β × 6.0%        (CAPM, Singapore market)
```

| Parameter | Value | Rationale |
|---|---|---|
| Risk-free rate | 2.5% | Singapore 10-year government bond yield |
| Market risk premium | 6.0% | Asia-Pacific equity risk premium |
| DPU growth rate | 3.0% | Conservative dividend growth assumption |
| Perpetual growth | 2.5% | Singapore long-run GDP growth rate |
| Projection period | 10 years | Standard DCF horizon |

### Monte Carlo Simulation

Each simulation draws parameters from a normal distribution to estimate the full distribution of intrinsic value.

```
g     ~ N(3.0%, 1.0%)     # DPU growth rate
WACC  ~ N(base, 0.5%)     # WACC noise
g_p   ~ N(2.5%, 0.5%)     # Perpetual growth rate
```

### Backtesting Strategy
- **Signal**: Trailing DPU computed from prior 12-month dividend history as of Entry Date; buy signal when DCF upside ≥ 10%
- **Portfolio**: Equal-weight long-only, no rebalancing
- **Benchmark**: CLR.SI (STI ETF) Buy & Hold
- **Alpha**: Portfolio Return − Benchmark Return

---

## ⚠️ Limitations & Disclaimers

- Transaction costs, slippage, and taxes are not modelled
- DCF relies on simplified assumptions and may diverge from true intrinsic value
- NAV is proxied by yfinance `bookValue` and may differ from officially reported NAV per unit
- Survivorship bias: analysis covers only currently listed REITs
- Past performance does not guarantee future results

---

## 🛠️ Tech Stack

| Category | Libraries |
|---|---|
| Data Collection | `yfinance`, `requests`, `BeautifulSoup4` |
| Data Processing | `pandas`, `numpy` |
| Visualisation | `plotly`, `matplotlib` |
| Dashboard | `streamlit` |
| Report Generation | `fpdf` |
| Email Delivery | `smtplib` (Gmail SMTP) |
| Automation | GitHub Actions |

---

## 📊 Coverage Universe (15 S-REITs)

| Ticker | Name | Sector |
|---|---|---|
| C38U.SI | CapitaLand Integrated Commercial Trust | Retail/Office |
| A17U.SI | CapitaLand Ascendas REIT | Industrial |
| N2IU.SI | Mapletree Pan Asia Commercial Trust | Retail/Office |
| M44U.SI | Mapletree Logistics Trust | Logistics |
| ME8U.SI | Mapletree Industrial Trust | Industrial |
| BUOU.SI | Frasers Centrepoint Trust | Retail/Office |
| AJBU.SI | Keppel DC REIT | Data Centre |
| J69U.SI | Frasers Logistics & Commercial Trust | Logistics |
| M1GU.SI | Sabana Industrial REIT | Industrial |
| HMN.SI | OUE Hospitality Trust | Hospitality |
| C2PU.SI | Parkway Life REIT | Healthcare |
| T82U.SI | Suntec REIT | Retail/Office |
| J91U.SI | ESR-REIT (formerly ESR-LOGOS) | Logistics |
| TS0U.SI | OUE REIT | Hospitality |
| CY6U.SI | CapitaLand India Trust | Industrial |

---

## 📄 License

MIT License © 2026 [hazel-jeon](https://github.com/hazel-jeon)