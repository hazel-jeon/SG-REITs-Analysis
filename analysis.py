import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime

def get_reit_analysis(reits_info, benchmark="CLR.SI"):
    results = []
    bench = yf.Ticker(benchmark).history(period="1y")['Close']
    bench_ret = bench.pct_change().dropna()
    
    for ticker, name in reits_info.items():
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")['Close']
        ret = hist.pct_change().dropna()
        
        vol = ret.std() * np.sqrt(252)
        cum_ret = (hist.iloc[-1] / hist.iloc[0] - 1)
        matrix = np.cov(ret, bench_ret)
        beta = matrix[0, 1] / matrix[1, 1]
        sharpe = (cum_ret - 0.03) / vol # 무위험 수익률 3% 가정
        
        results.append({
            "Ticker": ticker, "Name": name,
            "Return(%)": round(cum_ret*100, 2),
            "Vol(%)": round(vol*100, 2),
            "Beta": round(beta, 2), "Sharpe": round(sharpe, 2)
        })
    return pd.DataFrame(results)

def generate_pdf_report(df):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'SG-REITs Automation Report', 0, 1, 'C')
            self.ln(5)

    # 차트 생성
    plt.figure(figsize=(10, 5))
    plt.bar(df['Name'], df['Return(%)'], color='navy')
    plt.title('1Y Performance')
    plt.savefig("chart.png")

    # PDF 작성
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    # 데이터 테이블 추가 로직 생략(위의 코드 활용)
    pdf.image("chart.png", x=10, y=50, w=180)
    pdf.output("SG_REITs_Analysis.pdf")