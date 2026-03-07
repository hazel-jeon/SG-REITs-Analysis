from analysis import get_reit_analysis, generate_pdf_report
from mailer import send_analysis_email

REITS_CONFIG = {
    "C38U.SI": "CapitaLand Integrated",
    "A17U.SI": "CapitaLand Ascendas",
    "N2IU.SI": "Mapletree Pan Asia",
    "M44U.SI": "Mapletree Logistics",
    "ME8U.SI": "Mapletree Industrial",
    "BUOU.SI": "Frasers Centrepoint",
    "AJBU.SI": "Keppel DC REIT",
    "J69U.SI": "Frasers Logistics",
    "C2PU.SI": "Parkway Life REIT",
    "T82U.SI": "Suntec REIT",
    "TS0U.SI": "OUE REIT",
    "CY6U.SI": "CapitaLand India Trust",
    "CLAS.SI": "CapitaLand Ascott Trust",
    "LREIT.SI": "Lendlease Global REIT",
    "UHREIT.SI": "United Hampshire US REIT",
}

OUTPUT_PDF = "SG_REITs_Analysis.pdf"

def run_pipeline():
    print("=" * 50)
    print("Step 1: Analyzing Market Data + DCF Valuation...")
    df = get_reit_analysis(REITS_CONFIG)
    print(df[["Ticker", "Return(%)", "DCF Value", "Upside(%)", "NAV Disc(%)"]].to_string(index=False))

    print("\nStep 2: Generating PDF Report...")
    generate_pdf_report(df, output_path=OUTPUT_PDF)

    print("\nStep 3: Sending Email...")
    send_analysis_email(OUTPUT_PDF)

    print("\n✅ All steps completed.")

if __name__ == "__main__":
    run_pipeline()