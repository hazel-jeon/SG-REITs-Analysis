import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime

def get_reit_analysis(reits_info, benchmark="CLR.SI"):
    results = []
    # 벤치마크 데이터 가져오기 및 수익률 계산
    bench = yf.Ticker(benchmark).history(period="1y")['Close']
    bench_ret = bench.pct_change()
    
    for ticker, name in reits_info.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")['Close']
            ret = hist.pct_change()
            
            # 🔥 데이터 정렬 (리츠와 벤치마크의 날짜를 맞춤)
            combined = pd.concat([ret, bench_ret], axis=1).dropna()
            combined.columns = ['reit', 'benchmark']

            aligned_ret = combined['reit']
            aligned_bench = combined['benchmark']

            # 지표 계산
            vol = aligned_ret.std() * np.sqrt(252)
            cum_ret = (hist.iloc[-1] / hist.iloc[0] - 1)
            
            # Beta 계산
            matrix = np.cov(aligned_ret, aligned_bench)
            beta = matrix[0, 1] / matrix[1, 1] if matrix[1, 1] != 0 else 0
            
            # Sharpe Ratio (무위험 수익률 3% 가정)
            sharpe = (cum_ret - 0.03) / vol if vol != 0 else 0
            
            results.append({
                "Ticker": ticker, 
                "Name": name[:20], # 이름이 너무 길면 테이블이 깨지므로 제한
                "Return(%)": round(cum_ret*100, 2),
                "Vol(%)": round(vol*100, 2),
                "Beta": round(beta, 2), 
                "Sharpe": round(sharpe, 2)
            })
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            
    return pd.DataFrame(results)

def generate_pdf_report(df):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'SG-REITs Automation Report', 0, 1, 'C')
            self.set_font('Arial', 'I', 10)
            self.cell(0, 10, f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'R')
            self.ln(5)

    # 1. 차트 생성 및 저장
    plt.figure(figsize=(10, 5))
    plt.bar(df['Name'], df['Return(%)'], color='navy')
    plt.title('1Y Cumulative Performance (%)')
    plt.xticks(rotation=15, fontsize=8)
    plt.ylabel('Return (%)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("chart.png")
    plt.close() # 메모리 절약

    # 2. PDF 작성
    pdf = PDF()
    pdf.add_page()
    
    # 테이블 헤더 작성
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 220, 255)
    cols = ["Ticker", "Name", "Return(%)", "Vol(%)", "Beta", "Sharpe"]
    col_width = 31
    
    for col in cols:
        pdf.cell(col_width, 10, col, 1, 0, 'C', True)
    pdf.ln()
    
    # 테이블 데이터 작성
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        for col in cols:
            pdf.cell(col_width, 10, str(row[col]), 1, 0, 'C')
        pdf.ln()
    
    # 차트 삽입
    pdf.ln(10)
    pdf.image("chart.png", x=10, y=None, w=190)
    
    # 리포트 출력
    pdf.output("SG_REITs_Analysis.pdf")