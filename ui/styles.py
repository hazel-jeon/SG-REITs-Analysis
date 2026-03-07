"""
ui/styles.py — CSS 상수 및 색상 매핑
"""

SECTOR_COLORS = {
    "Retail/Office": "#2563eb",
    "Industrial":    "#7c3aed",
    "Logistics":     "#059669",
    "Data Centre":   "#dc2626",
    "Hospitality":   "#d97706",
    "Healthcare":    "#0891b2",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1b2a 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #c8d6e5 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #f0f4f8 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label { color: #94a3b8 !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; }

/* Main background */
.main .block-container { background: #f8fafc; padding-top: 1.5rem; }

/* Header */
.dash-header {
    background: linear-gradient(135deg, #0a0f1e 0%, #1a2744 60%, #0f3460 100%);
    border-radius: 16px;
    padding: 2.2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.dash-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%);
    border-radius: 50%;
}
.dash-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: #f0f4f8;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.01em;
}
.dash-header p { color: #94a3b8; font-size: 0.88rem; margin: 0; }
.dash-header .badge {
    display: inline-block;
    background: rgba(37,99,235,0.25);
    border: 1px solid rgba(37,99,235,0.5);
    color: #93c5fd;
    font-size: 0.72rem;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 0.6rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* KPI cards */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    position: relative;
    overflow: hidden;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    border-radius: 12px 0 0 12px;
}
.kpi-card.blue::after  { background: #2563eb; }
.kpi-card.green::after { background: #059669; }
.kpi-card.amber::after { background: #d97706; }
.kpi-card.red::after   { background: #dc2626; }
.kpi-label { font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.35rem; }
.kpi-value { font-size: 1.65rem; font-weight: 600; color: #0f172a; line-height: 1; }
.kpi-sub   { font-size: 0.78rem; color: #64748b; margin-top: 0.3rem; }

/* Section titles */
.section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.15rem;
    color: #0f172a;
    margin: 0 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e2e8f0;
}

/* Upside pill */
.pill-up   { background:#dcfce7; color:#166534; padding:2px 8px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.pill-down { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.pill-neu  { background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:20px; font-size:0.78rem; font-weight:600; }
</style>
"""