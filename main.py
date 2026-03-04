# 파일 연결 (Import)
from analysis import get_reit_analysis, generate_pdf_report
from mailer import send_analysis_email

# 설정
REITS_CONFIG = {
    "C38U.SI": "CapitaLand Integrated",
    "A17U.SI": "CapitaLand Ascendas",
    "N2IU.SI": "Mapletree Pan Asia",
    "M44U.SI": "Mapletree Logistics",
    "ME8U.SI": "Mapletree Industrial"
}

def run_pipeline():
    print("Step 1: Analyzing Market Data...")
    df = get_reit_analysis(REITS_CONFIG)
    
    print("Step 2: Generating PDF Report...")
    generate_pdf_report(df)
    
    print("Step 3: Sending Email...")
    send_analysis_email("SG_REITs_Analysis.pdf")
    
    print("Success: All steps completed.")

if __name__ == "__main__":
    run_pipeline()