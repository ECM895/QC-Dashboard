import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import base64

status_color_map = {
    "A-Approved": "#10B981",
    "B-Approved with Comments": "#0EA5E9",
    "Closed": "#10B981",
    "Valid": "#10B981",
    "Approved": "#10B981",
    "C-Revise and Resubmit": "#F59E0B",
    "Pending": "#F59E0B",
    "Under Review": "#F59E0B",
    "Expiring Soon": "#F59E0B",
    "D-Rejected": "#EF4444",
    "Rejected": "#EF4444",
    "Open": "#EF4444",
    "Expired": "#EF4444",
    "Overdue": "#DC2626"
}

PLOTLY_CONFIG = {
    'displayModeBar': False,
    'responsive': True,
    'showAxisDragHandles': False
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"], div.stMarkdown, div.stText, p,
span:not([class*="material"]):not([data-testid="stIcon"]):not([class*="Material"]) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

.block-container {
  padding-top: 0.8rem !important;
  padding-bottom: 3rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
  max-width: 1600px;
}

.stApp {
  background: #F0F4F8 !important;
}

#MainMenu, footer, header[data-testid="stHeader"] {
  visibility: hidden !important;
  display: none !important;
}

[data-testid="stStatusWidget"], .stDeployButton {
  display: none !important;
  visibility: hidden !important;
}

/* Completely remove sidebar and toggle button */
[data-testid="stSidebar"], section[data-testid="stSidebar"], [data-testid="collapsedControl"] {
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  height: 0 !important;
  pointer-events: none !important;
}

/* Form input styling */
[data-testid="stTextInput"] input, [data-baseweb="input"] input, [data-baseweb="select"] {
  background-color: #FFFFFF !important;
  color: #0F172A !important;
  border: 1.5px solid #CBD5E1 !important;
  border-radius: 8px !important;
  font-size: 0.90rem !important;
  font-weight: 500 !important;
  box-shadow: 0 1px 3px rgba(15,23,42,0.04) !important;
  transition: all 0.15s ease !important;
}

[data-testid="stTextInput"] input:focus, [data-baseweb="input"] input:focus {
  border-color: #2563EB !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.18) !important;
  outline: none !important;
}

[data-testid="stTextInput"] label, [data-testid="stWidgetLabel"] label {
  color: #1E293B !important;
  font-weight: 700 !important;
  font-size: 0.84rem !important;
}

/* Streamlit Button Styling */
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 700 !important;
  font-size: 0.78rem !important;
  letter-spacing: -0.01em !important;
  padding: 7px 12px !important;
  box-shadow: 0 2px 6px rgba(37,99,235,0.22) !important;
  color: #FFFFFF !important;
  transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

[data-testid="stBaseButton-primary"]:hover {
  box-shadow: 0 4px 12px rgba(37,99,235,0.35) !important;
  transform: translateY(-1px) !important;
}

[data-testid="stBaseButton-secondary"] {
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 0.78rem !important;
  letter-spacing: -0.01em !important;
  padding: 7px 12px !important;
  border: 1.5px solid #CBD5E1 !important;
  background: #FFFFFF !important;
  color: #334155 !important;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04) !important;
  transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

[data-testid="stBaseButton-secondary"]:hover {
  background: #F8FAFC !important;
  border-color: #94A3B8 !important;
  color: #0F172A !important;
  transform: translateY(-1px) !important;
}

/* Executive Header */
.exec-header {
  background: linear-gradient(125deg, #0F172A 0%, #1E293B 45%, #1A3666 100%);
  border-radius: 16px;
  padding: 20px 26px;
  color: white;
  margin-bottom: 16px;
  box-shadow: 0 10px 30px -8px rgba(15,23,42,0.4), 0 1px 0 rgba(255,255,255,0.06) inset;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  border: 1px solid rgba(255,255,255,0.07);
  position: relative;
  overflow: hidden;
}

.exec-header::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 35%;
  background: radial-gradient(ellipse at top right, rgba(59,130,246,0.14) 0%, transparent 70%);
  pointer-events: none;
}

.exec-header-title {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0;
  line-height: 1.2;
  color: #FFFFFF;
}

.exec-header-subtitle {
  font-size: 0.82rem;
  color: #94A3B8;
  margin-top: 4px;
  font-weight: 400;
}

.exec-header-subtitle strong {
  color: #CBD5E1;
  font-weight: 600;
}

.exec-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(59,130,246,0.18);
  border: 1px solid rgba(96,165,250,0.3);
  color: #93C5FD;
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.exec-date-badge {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.14);
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #E2E8F0;
}

/* Executive PPT-Matched NCR Table */
.ppt-ncr-table-container {
  width: 100%;
  overflow-x: auto;
  border-radius: 8px;
  box-shadow: 0 4px 14px rgba(15,23,42,0.06);
  margin-top: 10px;
  margin-bottom: 24px;
  background: #FFFFFF;
}

.ppt-ncr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
  text-align: left;
}

.ppt-ncr-table thead tr {
  background: #14355A !important;
  color: #FFFFFF !important;
}

.ppt-ncr-table th {
  padding: 12px 14px;
  font-weight: 700;
  border-right: 1px solid rgba(255,255,255,0.12);
  letter-spacing: -0.01em;
}

.ppt-ncr-table th:last-child {
  border-right: none;
}

.ppt-ncr-table tbody tr {
  border-bottom: 1px solid #EDF2F7;
  transition: background 0.15s ease;
}

.ppt-ncr-table tbody tr:nth-child(even) {
  background: #F8FAFC;
}

.ppt-ncr-table tbody tr:hover {
  background: #EFF6FF;
}

.ppt-ncr-table td {
  padding: 12px 14px;
  vertical-align: top;
  color: #1E293B;
  line-height: 1.45;
}

.ppt-ncr-doc-no {
  font-weight: 700;
  color: #14355A;
}

.ppt-ncr-badge-overdue {
  color: #DC2626;
  font-weight: 700;
}

.ppt-ncr-badge-active {
  color: #475569;
  font-weight: 600;
}

.ppt-ncr-status-alert {
  color: #DC2626;
  font-weight: 600;
}

/* Section Title */
.page-section-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0F172A;
  letter-spacing: -0.01em;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 18px 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #E2E8F0;
}

.page-section-title .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #2563EB;
  display: inline-block;
  flex-shrink: 0;
}

/* Hero Metric Cards Grid (Responsive) */
.hero-metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}

@media (max-width: 1200px) {
  .hero-metric-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .hero-metric-grid { grid-template-columns: 1fr; }
}

.hero-metric-card {
  background: #FFFFFF;
  border-radius: 14px;
  padding: 18px 20px;
  border: 1px solid #E8EDF2;
  box-shadow: 0 2px 8px rgba(15,23,42,0.04);
  position: relative;
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-metric-card:hover {
  box-shadow: 0 8px 20px rgba(15,23,42,0.08);
  transform: translateY(-2px);
}

.hero-metric-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.hero-metric-icon {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
}

.hero-metric-label {
  font-size: 0.70rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94A3B8;
  margin-bottom: 8px;
}

.hero-metric-val {
  font-size: 1.95rem;
  font-weight: 800;
  color: #0F172A;
  line-height: 1;
  letter-spacing: -0.03em;
}

.hero-metric-sub {
  font-size: 0.73rem;
  color: #94A3B8;
  margin-top: 7px;
}

.hero-pill {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 5px;
  font-size: 0.68rem;
  font-weight: 700;
}

/* Category Bento Box Card */
.bento-card {
  background: #FFFFFF;
  border: 1px solid #E8EDF2;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(15,23,42,0.04);
  margin-bottom: 14px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  text-decoration: none;
  color: inherit;
  display: block;
}

.bento-card:hover {
  border-color: #3B82F6;
  box-shadow: 0 8px 24px -4px rgba(37,99,235,0.16), 0 0 0 1px rgba(59,130,246,0.25);
  transform: translateY(-2px);
}

.bento-header {
  padding: 12px 16px;
  background: #FAFBFC;
  border-bottom: 1px solid #F0F4F8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bento-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bento-icon-badge {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #EFF6FF;
  color: #2563EB;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  flex-shrink: 0;
}

.bento-title {
  font-size: 0.90rem;
  font-weight: 700;
  color: #0F172A;
  line-height: 1.3;
}

.bento-rate-badge {
  font-size: 0.74rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 9999px;
  white-space: nowrap;
  flex-shrink: 0;
}

.bento-body {
  padding: 14px 12px 10px 12px;
  display: grid;
  gap: 8px;
  text-align: center;
}

.bento-metric-val {
  font-size: 1.40rem;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.bento-metric-label {
  font-size: 0.62rem;
  font-weight: 700;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 3px;
}

.bento-progress-container {
  padding: 0 16px 12px 16px;
}

.bento-progress-track {
  height: 4px;
  border-radius: 9999px;
  background: #F1F5F9;
  overflow: hidden;
}

.bento-progress-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

/* Detail KPI Card */
.detail-kpi-card {
  background: #FFFFFF;
  border: 1px solid #E8EDF2;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 2px 6px rgba(15,23,42,0.04);
  border-top: 3px solid #2563EB;
  transition: all 0.18s ease;
}

.detail-kpi-card:hover {
  box-shadow: 0 6px 16px rgba(15,23,42,0.08);
  transform: translateY(-1px);
}

.detail-kpi-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 4px;
}

.detail-kpi-value {
  font-size: 1.70rem;
  font-weight: 800;
  color: #0F172A;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.detail-kpi-sub {
  font-size: 0.72rem;
  color: #94A3B8;
  margin-top: 4px;
  font-weight: 400;
}

/* Lessons Learned Card */
.ll-card {
  background: #FFFFFF;
  border: 1px solid #E8EDF2;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(15,23,42,0.04);
  margin-bottom: 18px;
  overflow: hidden;
  transition: all 0.22s ease;
}

.ll-card:hover {
  box-shadow: 0 10px 26px rgba(15,23,42,0.08);
  border-color: #CBD5E1;
  transform: translateY(-2px);
}

.ll-card-header {
  padding: 14px 20px;
  background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
  border-bottom: 1px solid #E8EDF2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.ll-id-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #0F172A;
  color: #FFFFFF;
  font-weight: 800;
  font-size: 0.76rem;
  padding: 4px 10px;
  border-radius: 6px;
}

.ll-discipline-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #EFF6FF;
  color: #1D4ED8;
  border: 1px solid #BFDBFE;
  font-weight: 700;
  font-size: 0.72rem;
  padding: 4px 10px;
  border-radius: 9999px;
}

.ll-card-body {
  padding: 20px;
}

.ll-title {
  font-size: 1.05rem;
  font-weight: 800;
  color: #0F172A;
  line-height: 1.35;
  margin-bottom: 14px;
}

.ll-dual-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

@media (max-width: 768px) {
  .ll-dual-box { grid-template-columns: 1fr; }
}

.ll-problem-box {
  background: #FEF2F2;
  border-left: 4px solid #EF4444;
  border-radius: 0 10px 10px 0;
  padding: 12px 16px;
}

.ll-solution-box {
  background: #ECFDF5;
  border-left: 4px solid #10B981;
  border-radius: 0 10px 10px 0;
  padding: 12px 16px;
}

.ll-section-tag {
  font-size: 0.70rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.ll-meta-bar {
  background: #F8FAFC;
  border: 1px solid #E8EDF2;
  border-radius: 10px;
  padding: 10px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 0.75rem;
  color: #475569;
}

[data-testid="stTabs"] [data-testid="stTab"] {
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  padding: 8px 16px !important;
}

[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
  color: #2563EB !important;
  border-bottom: 2px solid #2563EB !important;
}

[data-testid="stDataFrame"] {
  border-radius: 10px !important;
  border: 1px solid #E2E8F0 !important;
  box-shadow: 0 1px 4px rgba(15,23,42,0.04) !important;
}

hr {
  border-color: #E2E8F0 !important;
  margin: 18px 0 !important;
}
</style>
"""

def inject_custom_css():
    """Injects high-contrast executive styling into Streamlit DOM."""
    st.markdown(CSS, unsafe_allow_html=True)

def render_hero_header(project_name="Royal Diriyah Opera House", pmc="DII-Jasara", date_range_text="All Time"):
    """Renders the executive top header with project branding and active timeframe."""
    logo_html = ""
    logo_path = os.path.join(os.path.dirname(__file__), "ecm_logo.png")
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as lf:
                b64 = base64.b64encode(lf.read()).decode("utf-8")
                logo_html = (
                    f'<div style="background:rgba(255,255,255,.95);padding:6px 12px;border-radius:10px;' +
                    f'box-shadow:0 2px 8px rgba(0,0,0,.15);display:flex;align-items:center;flex-shrink:0;">' +
                    f'<img src="data:image/png;base64,{b64}" alt="ECM JV" style="height:36px;object-fit:contain;">' +
                    f'</div>'
                )
        except Exception:
            pass

    html = (
        f'<div class="exec-header">' +
        f'  <div style="display:flex;align-items:center;gap:16px;position:relative;z-index:1;">' +
        f'    {logo_html}' +
        f'    <div>' +
        f'      <div class="exec-header-title">QA/QC Opera House Executive Dashboard</div>' +
        f'      <div class="exec-header-subtitle">Project: <strong>{project_name}</strong>' +
        f'        &nbsp;&bull;&nbsp; PMC: <strong>{pmc}</strong>' +
        f'        &nbsp;&bull;&nbsp; Contractor: <strong>ECM-JV</strong>' +
        f'      </div>' +
        f'    </div>' +
        f'  </div>' +
        f'  <div style="display:flex;align-items:center;gap:10px;position:relative;z-index:1;">' +
        f'    <div class="exec-badge">📋 ACONEX MASTER REGISTER</div>' +
        f'    <div class="exec-date-badge">📅 {date_range_text}</div>' +
        f'  </div>' +
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def _hero_card(accent, icon_emoji, icon_bg, label, value_html, sub, pill_text=None, pill_style=""):
    pill = f'<span class="hero-pill" style="{pill_style}">{pill_text}</span>' if pill_text else ""
    return (
        f'<div class="hero-metric-card">' +
        f'  <div class="hero-metric-accent" style="background:{accent};"></div>' +
        f'  <div class="hero-metric-icon" style="background:{icon_bg};">{icon_emoji}</div>' +
        f'  <div class="hero-metric-label">{label} {pill}</div>' +
        f'  <div class="hero-metric-val">{value_html}</div>' +
        f'  <div class="hero-metric-sub">{sub}</div>' +
        f'</div>'
    )

def render_hero_metric_cards(total_inspections, overall_approval_rate, open_ncrs, concrete_volume):
    """Renders the 4 primary KPI cards at the top of the Overview page."""
    c1 = _hero_card(
        "#2563EB", "📋", "#EFF6FF", "Total Quality Submittals",
        f"{total_inspections:,}", "Active & archived Aconex records",
        "ALL", "background:#DBEAFE;color:#1D4ED8;"
    )
    rc = "#059669" if overall_approval_rate >= 85 else ("#D97706" if overall_approval_rate >= 65 else "#DC2626")
    c2 = _hero_card(
        rc, "🎯", "#ECFDF5", "Quality Compliance (A+B)",
        f'<span style="color:{rc};">{overall_approval_rate:.1f}%</span>',
        "Code A (clean) + Code B (comments)", "TARGET: 85%",
        "background:#ECFDF5;color:#059669;"
    )
    nc = "#DC2626" if open_ncrs > 0 else "#059669"
    c3 = _hero_card(
        nc, "⚠️", "#FEF2F2", "Active Open NCRs",
        f'<span style="color:{nc};">{open_ncrs:,}</span>',
        "Non-conformances pending closeout", "HOLD POINTS",
        "background:#FEF2F2;color:#DC2626;"
    )
    c4 = _hero_card(
        "#0D9488", "🏗️", "#F0FDFA", "Total Concrete Cast",
        f'<span style="color:#0F766E;">{concrete_volume:,.1f} <span style="font-size:1rem;font-weight:600;">m³</span></span>',
        "Volume placed in filtered period", "CASTING LOG",
        "background:#CCFBF1;color:#0F766E;"
    )
    st.markdown(f'<div class="hero-metric-grid">{c1}{c2}{c3}{c4}</div>', unsafe_allow_html=True)

def render_category_box(title, total_val, val1, val2, val3, val4, rate,
                        is_alt_color=False, is_ncr=False, cat_id=None):
    """Renders interactive Bento Box category performance card."""
    icons = {"WIR":"📋", "MIR":"📦", "MAR":"📑", "MST":"📄", "ITP":"🛡️", "SHD":"📐", "NCR":"⚠️"}
    icon = icons.get(cat_id, "📊")
    
    try:
        rate_num = float(str(rate).replace("%", "").strip())
    except Exception:
        rate_num = 0.0

    if is_ncr:
        pc = "#10B981" if rate_num >= 80 else ("#F59E0B" if rate_num >= 50 else "#EF4444")
    else:
        pc = "#10B981" if rate_num >= 80 else ("#F59E0B" if rate_num >= 60 else "#EF4444")
        
    bb = "#EFF6FF" if is_alt_color else "#ECFDF5"
    bc = "#1D4ED8" if is_alt_color else "#059669"
    bbd = "#BFDBFE" if is_alt_color else "#A7F3D0"
    rl = "Closure Rate" if is_ncr else "Approval Rate"

    def mc(value, label, color="#0F172A"):
        return (
            f'<div style="text-align:center;">' +
            f'  <div class="bento-metric-val" style="color:{color};">{value}</div>' +
            f'  <div class="bento-metric-label">{label}</div>' +
            f'</div>'
        )

    cells = [mc(total_val, "TOTAL")]
    if is_ncr:
        cells += [mc(val1, "CLOSED", "#10B981"), mc(val2, "OPEN", "#F59E0B")]
        if val3:
            cells += [mc(val3, "OVERDUE (>60d)", "#EF4444")]
            gc = "repeat(4,1fr)"
        else:
            gc = "repeat(3,1fr)"
    else:
        cells += [
            mc(val1, "CODE A", "#10B981"),
            mc(val2, "CODE B", "#0EA5E9"),
            mc(val3, "CODE C", "#F59E0B"),
            mc(val4, "CODE D", "#EF4444")
        ]
        gc = "repeat(5,1fr)"

    body = "".join(cells)
    html = (
        f'<div class="bento-card">' +
        f'  <div class="bento-header">' +
        f'    <div class="bento-title-group">' +
        f'      <div class="bento-icon-badge">{icon}</div>' +
        f'      <div>' +
        f'        <div class="bento-title">{title}</div>' +
        f'        <div style="font-size:0.68rem;color:#64748B;font-weight:600;margin-top:1px;">Category Code: {cat_id} &bull; Aconex Register</div>' +
        f'      </div>' +
        f'    </div>' +
        f'    <div class="bento-rate-badge" style="background:{bb};color:{bc};border:1px solid {bbd};">' +
        f'      {rl}: {rate}</div>' +
        f'  </div>' +
        f'  <div class="bento-body" style="grid-template-columns:{gc};">{body}</div>' +
        f'  <div class="bento-progress-container">' +
        f'    <div class="bento-progress-track">' +
        f'      <div class="bento-progress-fill" style="width:{min(rate_num, 100)}%;background:{pc};"></div>' +
        f'    </div>' +
        f'  </div>' +
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    return html

def section_title(text):
    """Renders high-visibility section title with blue accent dot."""
    st.markdown(
        f'<div class="page-section-title"><span class="dot"></span>{text}</div>',
        unsafe_allow_html=True
    )

def apply_chart_style(fig, title, height=340):
    """Applies executive styling and layout parameters to Plotly figure."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(family="Inter, sans-serif", size=13, color="#0F172A"),
            x=0.0, y=0.97, xanchor="left"
        ),
        font=dict(family="Inter, sans-serif", color="#64748B", size=11),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(t=48, b=28, l=36, r=20),
        height=height,
        hoverlabel=dict(
            bgcolor="#0F172A",
            font_size=12,
            font_family="Inter, sans-serif",
            font_color="#FFFFFF",
            bordercolor="rgba(0,0,0,0)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#64748B"),
            bgcolor="rgba(0,0,0,0)"
        )
    )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0", tickfont=dict(size=11, color="#64748B"), ticklen=0)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#F1F5F9", linecolor="rgba(0,0,0,0)", tickfont=dict(size=11, color="#64748B"))
    return fig

def plot_donut_chart(labels, values, title, colors, height=330):
    """Generates an executive pseudo-3D donut chart with isometric pull and shadow layering."""
    total = sum(values) if values is not None else 0
    # Slightly pull segments for 3D extrusion illusion
    pull_factors = [0.03 if idx == 0 else 0.015 for idx in range(len(labels))] if labels is not None else None
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.60,
        pull=pull_factors,
        marker=dict(
            colors=colors,
            line=dict(color="#FFFFFF", width=3),
            # 3D surface depth pattern
            pattern=dict(shape="")
        ),
        textinfo="percent+label",
        textposition="outside",
        textfont=dict(size=11, family="Inter", color="#1E293B", weight=700),
        hoverinfo="label+value+percent",
        rotation=35
    )])
    fig.add_annotation(
        text=f"<b style='font-size:24px;color:#0F172A;'>{total:,}</b><br><span style='font-size:10px;color:#64748B;font-weight:800;letter-spacing:0.05em;'>TOTAL CUMULATIVE</span>",
        x=0.5, y=0.5,
        font=dict(family="Inter"),
        showarrow=False
    )
    apply_chart_style(fig, title, height=height)
    fig.update_layout(showlegend=False, margin=dict(t=50, b=25, l=25, r=25))
    return fig

def plot_100p_stacked_bar(df, x_col, y_col, color_col, title, color_map, height=360, count_col='Count'):
    """Generates 100% normalized proportional stacked bar chart with 3D embossed bars and borders."""
    plot_df = df.copy()
    if count_col in plot_df.columns:
        x_totals = plot_df.groupby(x_col, observed=False)[count_col].sum().to_dict()
        display_map = {
            val: f"{val}<br><span style='font-size:10px;color:#64748B;font-weight:600;'>Total: {x_totals.get(val, 0):,}</span>"
            for val in plot_df[x_col].unique()
        }
        plot_df[f'{x_col}_Display'] = plot_df[x_col].map(display_map)
        if isinstance(plot_df[x_col].dtype, pd.CategoricalDtype):
            new_cats = [display_map[c] for c in plot_df[x_col].cat.categories if c in display_map]
            plot_df[f'{x_col}_Display'] = pd.Categorical(plot_df[f'{x_col}_Display'], categories=new_cats, ordered=True)
            
        plot_df['BarText'] = plot_df.apply(
            lambda r: f"{r[y_col]:.0f}%<br><span style='font-size:9px;'>({int(r[count_col]):,})</span>"
            if r[y_col] > 11 else (f"{r[y_col]:.0f}%" if r[y_col] > 6 else ""),
            axis=1
        )
        fig = px.bar(
            plot_df, x=f'{x_col}_Display', y=y_col, color=color_col,
            color_discrete_map=color_map, text='BarText',
            custom_data=[count_col]
        )
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Status: %{fullData.name}<br>Proportion: %{y:.1f}%<br>Count: %{customdata[0]:,} records<extra></extra>",
            marker=dict(line=dict(color="rgba(255,255,255,0.85)", width=2))
        )
    else:
        fig = px.bar(
            plot_df, x=x_col, y=y_col, color=color_col, color_discrete_map=color_map,
            text=plot_df[y_col].apply(lambda x: f'{x:.0f}%' if x > 6 else "")
        )
        fig.update_traces(
            marker=dict(line=dict(color="rgba(255,255,255,0.85)", width=2))
        )
        
    fig.update_traces(
        textposition="inside",
        textfont=dict(size=11, family="Inter", color="#FFFFFF", weight=700)
    )
    apply_chart_style(fig, title, height=height)
    fig.update_yaxes(title="Proportion (%)", range=[0, 100])
    fig.update_xaxes(title="")
    return fig

def plot_grouped_bar_chart(df, x_col, y_col, color_col, title, color_map, height=350):
    """Generates 3D-styled grouped bar chart with embossed shadow borders."""
    fig = px.bar(
        df, x=x_col, y=y_col, color=color_col, barmode="group",
        color_discrete_map=color_map, text_auto=".1f"
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=10, family="Inter", color="#0F172A", weight=700),
        marker=dict(
            line=dict(width=1.5, color="rgba(15,23,42,0.25)")
        ),
        cliponaxis=False
    )
    apply_chart_style(fig, title, height=height)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Volume (m³)")
    return fig

def plot_bar_chart(df, x_col, y_col, title, color="#2563EB", height=330):
    """Generates 3D-styled vertical bar chart with rich bevel edges."""
    fig = px.bar(df, x=x_col, y=y_col, text_auto=True)
    fig.update_traces(
        marker_color=color,
        marker=dict(
            line=dict(color="rgba(15,23,42,0.25)", width=1.5)
        ),
        textposition="outside",
        textfont=dict(size=11, family="Inter", color="#0F172A", weight=700),
        cliponaxis=False
    )
    apply_chart_style(fig, title, height=height)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Count")
    return fig

def plot_pareto_chart(df, x_col, y_col, cum_col, title, height=350):
    """Generates 80/20 Pareto distribution with 3D bevel and dual axes."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df[x_col], y=df[y_col], name="Issue Count",
            marker_color="#2563EB",
            marker=dict(line=dict(color="#1D4ED8", width=1.5)),
            text=df[y_col],
            textposition="inside", textfont=dict(color="#FFFFFF", weight=700)
        ),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(
            x=df[x_col], y=df[cum_col], name="Cumulative %",
            marker=dict(color="#F59E0B", size=9, line=dict(color="#FFFFFF", width=2.5)),
            line=dict(color="#D97706", width=3), mode="lines+markers+text",
            text=[f"{v:.0f}%" for v in df[cum_col]], textposition="top center",
            textfont=dict(size=10, color="#92400E", weight=700)
        ),
        secondary_y=True
    )
    apply_chart_style(fig, title, height=height)
    fig.update_yaxes(title_text="Issue Count", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative %", range=[0, 115], secondary_y=True)
    fig.update_xaxes(title="")
    return fig

def plot_post_pour_status(df, height=350):
    """Generates post-pour structural defects resolution chart with 3D embossed stacking."""
    status_counts = df.groupby(["Zone", "Status"]).size().reset_index(name="Count")
    color_map = {"Open": "#EF4444", "Repaired": "#F59E0B", "Inspected": "#10B981"}
    fig = px.bar(
        status_counts, x="Zone", y="Count", color="Status",
        color_discrete_map=color_map, barmode="stack", text_auto=True
    )
    fig.update_traces(
        textposition="inside", 
        textfont=dict(color="#FFFFFF", weight=700),
        marker=dict(line=dict(color="rgba(255,255,255,0.7)", width=1.5))
    )
    apply_chart_style(fig, "POST-POUR DEFECTS BY ZONE", height=height)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Defect Count")
    return fig

def render_lesson_learned_card(item):
    """Renders formatted graphical card for Lessons Learned item."""
    ll_id = item.get("Lesson Learned ID", "LL-000")
    title = item.get("Lesson Learned Title", "Untitled Lesson")
    domain = item.get("Discipline / Domain", "General Quality")
    impact_cat = item.get("Impact Category", "Quality & Engineering")
    problem = item.get("Systemic Root Cause / Problem Statement", "N/A")
    consequence = item.get("Detailed Operational Impact & Failure Mechanism", "N/A")
    controls = item.get("Streamlined Engineering & Management Control (Corrective & Preventive Actions)", "N/A")
    governance = item.get("Mandatory Verification & Governance Mechanism", "N/A")
    scope = item.get("Applicability Scope & Phase", "All Works")
    source = item.get("Originating Reference / Source Mapping", "Project Site")
    controls_html = "<br>".join([f"&bull; {l.strip()}" for l in str(controls).split("\n") if l.strip()])
    
    html = f"""
    <div class="ll-card">
        <div class="ll-card-header">
            <div style="display:flex;align-items:center;gap:10px;">
                <span class="ll-id-badge">📌 {ll_id}</span>
                <span class="ll-discipline-badge">🏗️ {domain}</span>
            </div>
            <span style="font-size:.72rem;font-weight:700;color:#DC2626;background:#FEF2F2;padding:4px 10px;border-radius:9999px;border:1px solid #FECACA;">⚠️ {impact_cat}</span>
        </div>
        <div class="ll-card-body">
            <div class="ll-title">{title}</div>
            <div class="ll-dual-box">
                <div class="ll-problem-box">
                    <div class="ll-section-tag" style="color:#DC2626;">⚠️ Root Cause &amp; Operational Impact</div>
                    <div style="font-size:.85rem;color:#1E293B;line-height:1.5;margin-bottom:8px;"><strong>Root Cause:</strong> {problem}</div>
                    <div style="font-size:.80rem;color:#64748B;line-height:1.45;"><strong>Consequence:</strong> {consequence}</div>
                </div>
                <div class="ll-solution-box">
                    <div class="ll-section-tag" style="color:#059669;">🛡️ Mandatory Preventive Controls (CAPA)</div>
                    <div style="font-size:.82rem;color:#064E3B;line-height:1.5;">{controls_html}</div>
                </div>
            </div>
            <div class="ll-meta-bar">
                <div><strong>Governance:</strong> <span style="color:#0F172A;">{governance}</span></div>
                <div style="display:flex;gap:14px;">
                    <span><strong>Scope:</strong> {scope}</span>
                    <span><strong>Source:</strong> <span style="color:#2563EB;">{source}</span></span>
                </div>
            </div>
        </div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

def render_best_practice_card(item):
    """Renders formatted graphical card for Best Practice item."""
    bp_id = item.get("Best Practice ID", "BP-000")
    title = item.get("Best Practice Title", "Standard Practice")
    domain = item.get("Discipline / Domain", "General Quality")
    context = item.get("Operational Context & Challenge Addressed", "N/A")
    methodology = item.get("Standardized Methodology / Execution Protocol", "N/A")
    benefits = item.get("Measurable Benefits & Value Added", "N/A")
    governance = item.get("Implementation & Governance Mechanism", "N/A")
    scope = item.get("Applicability Scope", "All Works")
    source = item.get("Originating Reference / Source Mapping", "Field Proven")
    method_html = "<br>".join([f"&bull; {l.strip()}" for l in str(methodology).split("\n") if l.strip()])
    
    html = f"""
    <div class="ll-card" style="border-top:4px solid #10B981;">
        <div class="ll-card-header" style="background:linear-gradient(135deg,#F0FDF4 0%,#ECFDF5 100%);">
            <div style="display:flex;align-items:center;gap:10px;">
                <span class="ll-id-badge" style="background:#065F46;">🌟 {bp_id}</span>
                <span class="ll-discipline-badge" style="background:#FFFFFF;color:#059669;border-color:#A7F3D0;">📐 {domain}</span>
            </div>
            <span style="font-size:.72rem;font-weight:700;color:#059669;background:#FFFFFF;padding:4px 10px;border-radius:9999px;border:1px solid #A7F3D0;">✓ Proven Standard</span>
        </div>
        <div class="ll-card-body">
            <div class="ll-title" style="color:#064E3B;">{title}</div>
            <div class="ll-dual-box">
                <div style="background:#F8FAFC;border-left:4px solid #3B82F6;border-radius:0 10px 10px 0;padding:12px 16px;">
                    <div class="ll-section-tag" style="color:#2563EB;">🎯 Challenge Addressed</div>
                    <div style="font-size:.85rem;color:#1E293B;line-height:1.5;margin-bottom:8px;">{context}</div>
                    <div style="font-size:.82rem;color:#047857;margin-top:10px;background:#ECFDF5;padding:8px 10px;border-radius:8px;"><strong>Measurable Benefit:</strong> {benefits}</div>
                </div>
                <div class="ll-solution-box" style="border-left-color:#10B981;">
                    <div class="ll-section-tag" style="color:#059669;">🛠️ Execution Protocol &amp; SOP</div>
                    <div style="font-size:.82rem;color:#064E3B;line-height:1.5;">{method_html}</div>
                </div>
            </div>
            <div class="ll-meta-bar">
                <div><strong>Implementation Gate:</strong> <span style="color:#0F172A;">{governance}</span></div>
                <div style="display:flex;gap:14px;">
                    <span><strong>Scope:</strong> {scope}</span>
                    <span><strong>Derived From:</strong> <span style="color:#059669;">{source}</span></span>
                </div>
            </div>
        </div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)


def plot_isometric_3d_kpi_pillars(df, height=480):
    """
    Renders an authentic, vibrant 3D isometric pillar chart replicating the
    user's visual design (media_1790676019867.png) with glowing prism columns,
    isometric 3D perspective shading, floating metric badges, and interactive inspection.
    """
    if df is None or len(df) == 0:
        return None

    pillar_palettes = [
        {"top": "#FDE68A", "front": "#F59E0B", "side": "#D97706", "accent": "#B45309", "icon": "✓"},
        {"top": "#93C5FD", "front": "#2563EB", "side": "#1D4ED8", "accent": "#1E40AF", "icon": "🔍"},
        {"top": "#6EE7B7", "front": "#10B981", "side": "#059669", "accent": "#047857", "icon": "📊"},
        {"top": "#FDA4AF", "front": "#F43F5E", "side": "#E11D48", "accent": "#BE123C", "icon": "📈"},
        {"top": "#A5F3FC", "front": "#06B6D4", "side": "#0891B2", "accent": "#0E7490", "icon": "⚙️"},
        {"top": "#FBCFE8", "front": "#EC4899", "side": "#DB2777", "accent": "#9D174D", "icon": "📦"},
        {"top": "#DDD6FE", "front": "#8B5CF6", "side": "#7C3AED", "accent": "#6D28D9", "icon": "📋"},
        {"top": "#BAE6FD", "front": "#0EA5E9", "side": "#0284C7", "accent": "#0369A1", "icon": "📐"},
    ]

    fig = go.Figure()
    col_width = 0.55
    col_depth = 0.55

    for idx, row in df.reset_index(drop=True).iterrows():
        cat = row.get('KPI Category', f'Cat {idx+1}')
        rate = float(row.get('_rate_num', 0))
        total = int(row.get('Total', 0))
        ca = int(row.get('Code A', 0))
        cb = int(row.get('Code B', 0))
        cc = int(row.get('Code C', 0))
        cd = int(row.get('Code D', 0))
        ur = int(row.get('Under Review', 0))

        h = max(rate, 4.0)
        x_center = idx * 1.3
        y_center = 0.0

        x0 = x_center - col_width / 2
        x1 = x_center + col_width / 2
        y0 = y_center - col_depth / 2
        y1 = y_center + col_depth / 2

        pal = pillar_palettes[idx % len(pillar_palettes)]

        vx = [x0, x1, x1, x0, x0, x1, x1, x0]
        vy = [y0, y0, y1, y1, y0, y0, y1, y1]
        vz = [0,  0,  0,  0,  h,  h,  h,  h]

        i = [0, 0, 1, 1, 4, 4, 0, 0, 2, 2, 0, 0]
        j = [1, 5, 2, 6, 5, 6, 4, 7, 3, 7, 3, 2]
        k = [5, 4, 6, 5, 6, 7, 7, 3, 7, 6, 2, 1]

        hover_info = (
            f"<b>{cat}</b><br>" +
            f"━━━━━━━━━━━━━━━━━━<br>" +
            f"<b>Approved % (A & B):</b> {rate:.1f}%<br>" +
            f"Total Submissions: {total:,}<br>" +
            f"Code A (Approved): {ca:,}<br>" +
            f"Code B (Approved w/ Notes): {cb:,}<br>" +
            f"Code C (Revise & Resubmit): {cc:,}<br>" +
            f"Code D (Rejected): {cd:,}<br>" +
            f"Under Review (Deducted): {ur:,}"
        )

        fig.add_trace(go.Mesh3d(
            x=vx, y=vy, z=vz,
            i=i, j=j, k=k,
            color=pal['front'],
            flatshading=True,
            lighting=dict(
                ambient=0.65,
                diffuse=0.9,
                specular=0.5,
                roughness=0.25,
                fresnel=0.3
            ),
            lightposition=dict(x=10, y=-20, z=50),
            opacity=0.92,
            name=cat,
            hoverinfo="text",
            hovertext=hover_info,
            showscale=False
        ))

        # Floating percentage label on top of each 3D pillar (like the reference graphic)
        fig.add_trace(go.Scatter3d(
            x=[x_center],
            y=[y_center],
            z=[h + 7],
            mode="text+markers",
            text=[f"<b>{rate:.0f}%</b>"],
            textposition="middle center",
            textfont=dict(family="Inter, sans-serif", size=13, color="#0F172A"),
            marker=dict(
                size=12,
                color=pal['top'],
                line=dict(color=pal['front'], width=2),
                symbol="circle"
            ),
            hoverinfo="text",
            hovertext=hover_info,
            showlegend=False
        ))

        # Dashed antenna / pin indicator reaching upwards like in the user's image
        fig.add_trace(go.Scatter3d(
            x=[x_center, x_center],
            y=[y_center, y_center],
            z=[h, h + 14],
            mode="lines",
            line=dict(color="#94A3B8", width=3, dash="dot"),
            hoverinfo="none",
            showlegend=False
        ))

        # Category icon/badge symbol floating on top pin
        fig.add_trace(go.Scatter3d(
            x=[x_center],
            y=[y_center],
            z=[h + 16],
            mode="text",
            text=[pal['icon']],
            textfont=dict(size=14, color=pal['accent']),
            hoverinfo="text",
            hovertext=f"{cat} KPI Pillar",
            showlegend=False
        ))

        # Category Base Tag at bottom
        fig.add_trace(go.Scatter3d(
            x=[x_center],
            y=[y_center],
            z=[-4],
            mode="text",
            text=[f"<b>{cat}</b>"],
            textposition="bottom center",
            textfont=dict(family="Inter, sans-serif", size=11, color="#334155"),
            hoverinfo="none",
            showlegend=False
        ))

    # Executive camera view: Isometric elevation angle
    fig.update_layout(
        scene=dict(
            xaxis=dict(showbackground=False, showticklabels=False, title="", showgrid=False, zeroline=False),
            yaxis=dict(showbackground=False, showticklabels=False, title="", showgrid=False, zeroline=False),
            zaxis=dict(showbackground=True, backgroundcolor="#F8FAFC", title="", showticklabels=False, showgrid=False, zeroline=False, range=[-8, 125]),
            camera=dict(
                eye=dict(x=1.65, y=-1.85, z=1.2),
                center=dict(x=0.0, y=0.0, z=-0.1),
                up=dict(x=0, y=0, z=1)
            ),
            aspectratio=dict(x=2.2, y=1.0, z=1.1)
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=False
    )
    return fig


def render_executive_kpi_table(df, title_label="KPI — CUMULATIVE MASTER STATUS"):
    """
    Renders an executive, large, high-contrast, polished HTML table for KPI submittals.
    Includes large typography, vivid status pills, bold totals, and clear percentage bars.
    """
    if df is None or len(df) == 0:
        st.info("No KPI records available to display.")
        return

    disp_df = df.copy()

    # Calculate summary totals row
    tot_all = int(disp_df['Total'].sum())
    ca_all = int(disp_df['Code A'].sum())
    cb_all = int(disp_df['Code B'].sum())
    cc_all = int(disp_df['Code C'].sum())
    cd_all = int(disp_df['Code D'].sum())
    ur_all = int(disp_df['Under Review'].sum())
    decided_all = tot_all - ur_all
    total_rate = ((ca_all + cb_all) / decided_all * 100) if decided_all > 0 else 0

    rows_html = []
    for _, r in disp_df.iterrows():
        cat = r.get('KPI Category', '')
        tot = int(r.get('Total', 0))
        ca = int(r.get('Code A', 0))
        cb = int(r.get('Code B', 0))
        cc = int(r.get('Code C', 0))
        cd = int(r.get('Code D', 0))
        ur = int(r.get('Under Review', 0))
        rate_val = float(r.get('_rate_num', 0))

        if rate_val >= 80:
            badge_bg = "#ECFDF5"
            badge_color = "#047857"
            badge_border = "#A7F3D0"
        elif rate_val >= 50:
            badge_bg = "#FFFBEB"
            badge_color = "#B45309"
            badge_border = "#FDE68A"
        else:
            badge_bg = "#FEF2F2"
            badge_color = "#B91C1C"
            badge_border = "#FECACA"

        rows_html.append(
            '<tr style="border-bottom: 1px solid #E2E8F0;">'
            f'<td style="padding: 14px 18px; font-weight: 700; color: #0F172A; font-size: 0.96rem;"><span style="display:inline-block; width: 8px; height: 8px; border-radius: 50%; background: #2563EB; margin-right: 8px;"></span>{cat}</td>'
            f'<td style="padding: 14px 14px; text-align: center; font-weight: 700; font-size: 0.98rem; color: #0F172A;">{tot:,}</td>'
            f'<td style="padding: 14px 14px; text-align: center; font-weight: 700; font-size: 0.95rem; color: #059669;"><span style="background: #ECFDF5; padding: 4px 10px; border-radius: 6px; border: 1px solid #A7F3D0;">{ca:,}</span></td>'
            f'<td style="padding: 14px 14px; text-align: center; font-weight: 700; font-size: 0.95rem; color: #0284C7;"><span style="background: #F0F9FF; padding: 4px 10px; border-radius: 6px; border: 1px solid #BAE6FD;">{cb:,}</span></td>'
            f'<td style="padding: 14px 14px; text-align: center; font-weight: 700; font-size: 0.95rem; color: #D97706;"><span style="background: #FFFBEB; padding: 4px 10px; border-radius: 6px; border: 1px solid #FDE68A;">{cc:,}</span></td>'
            f'<td style="padding: 14px 14px; text-align: center; font-weight: 700; font-size: 0.95rem; color: #DC2626;"><span style="background: #FEF2F2; padding: 4px 10px; border-radius: 6px; border: 1px solid #FECACA;">{cd:,}</span></td>'
            f'<td style="padding: 14px 14px; text-align: center; font-weight: 700; font-size: 0.95rem; color: #64748B;"><span style="background: #F1F5F9; padding: 4px 10px; border-radius: 6px; border: 1px solid #CBD5E1;">{ur:,}</span></td>'
            f'<td style="padding: 14px 18px; text-align: center;"><div style="display: inline-flex; align-items: center; gap: 8px;"><span style="display: inline-block; background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; font-weight: 800; font-size: 0.95rem; padding: 4px 12px; border-radius: 8px; min-width: 60px;">{rate_val:.0f}%</span><div style="width: 70px; height: 8px; background: #E2E8F0; border-radius: 9999px; overflow: hidden; display: inline-block;"><div style="width: {min(max(rate_val, 0), 100)}%; height: 100%; background: {badge_color}; border-radius: 9999px;"></div></div></div></td>'
            '</tr>'
        )

    tot_rate_color = "#047857" if total_rate >= 75 else "#B45309"
    tot_rate_bg = "#ECFDF5" if total_rate >= 75 else "#FFFBEB"
    tot_rate_border = "#A7F3D0" if total_rate >= 75 else "#FDE68A"

    total_row_html = (
        '<tr style="background: #F8FAFC; border-top: 3px solid #0F172A; border-bottom: 2px solid #0F172A;">'
        '<td style="padding: 16px 18px; font-weight: 900; color: #0F172A; font-size: 1.05rem; letter-spacing: 0.03em;">🌟 PROJECT TOTAL</td>'
        f'<td style="padding: 16px 14px; text-align: center; font-weight: 900; font-size: 1.15rem; color: #0F172A;">{tot_all:,}</td>'
        f'<td style="padding: 16px 14px; text-align: center; font-weight: 900; font-size: 1.05rem; color: #059669;">{ca_all:,}</td>'
        f'<td style="padding: 16px 14px; text-align: center; font-weight: 900; font-size: 1.05rem; color: #0284C7;">{cb_all:,}</td>'
        f'<td style="padding: 16px 14px; text-align: center; font-weight: 900; font-size: 1.05rem; color: #D97706;">{cc_all:,}</td>'
        f'<td style="padding: 16px 14px; text-align: center; font-weight: 900; font-size: 1.05rem; color: #DC2626;">{cd_all:,}</td>'
        f'<td style="padding: 16px 14px; text-align: center; font-weight: 900; font-size: 1.05rem; color: #64748B;">{ur_all:,}</td>'
        f'<td style="padding: 16px 18px; text-align: center;"><div style="display: inline-flex; align-items: center; gap: 8px;"><span style="display: inline-block; background: {tot_rate_bg}; color: {tot_rate_color}; border: 2px solid {tot_rate_border}; font-weight: 900; font-size: 1.08rem; padding: 6px 14px; border-radius: 8px; min-width: 70px;">{total_rate:.0f}%</span><div style="width: 70px; height: 10px; background: #CBD5E1; border-radius: 9999px; overflow: hidden; display: inline-block;"><div style="width: {min(max(total_rate, 0), 100)}%; height: 100%; background: {tot_rate_color}; border-radius: 9999px;"></div></div></div></td>'
        '</tr>'
    )

    all_rows = "".join(rows_html) + total_row_html

    table_container_html = (
        '<div style="background: #FFFFFF; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 20px rgba(15,23,42,0.08); border: 1px solid #E2E8F0; margin-bottom: 16px;">'
        '<div style="background: linear-gradient(135deg, #B45309 0%, #D97706 100%); padding: 14px 24px; color: #FFFFFF; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.05em; display: flex; align-items: center; justify-content: space-between;">'
        f'<span>📋 {title_label}</span>'
        '<span style="font-size: 0.78rem; font-weight: 600; background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 9999px;">OFFICIAL ACONEX MASTER AUDIT</span>'
        '</div>'
        '<div style="overflow-x: auto;">'
        '<table style="width: 100%; border-collapse: collapse; font-family: Inter, -apple-system, sans-serif; text-align: left;">'
        '<thead>'
        '<tr style="background: #0F172A; color: #F8FAFC; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.06em;">'
        '<th style="padding: 14px 18px; font-weight: 700;">Submittal / Document Type</th>'
        '<th style="padding: 14px 14px; text-align: center; font-weight: 700;">Total</th>'
        '<th style="padding: 14px 14px; text-align: center; font-weight: 700; color: #34D399;">Code A (Appr.)</th>'
        '<th style="padding: 14px 14px; text-align: center; font-weight: 700; color: #38BDF8;">Code B (Notes)</th>'
        '<th style="padding: 14px 14px; text-align: center; font-weight: 700; color: #FBBF24;">Code C (Revise)</th>'
        '<th style="padding: 14px 14px; text-align: center; font-weight: 700; color: #F87171;">Code D (Reject)</th>'
        '<th style="padding: 14px 14px; text-align: center; font-weight: 700; color: #CBD5E1;">Under Review</th>'
        '<th style="padding: 14px 18px; text-align: center; font-weight: 700; color: #60A5FA;">Approved % (A &amp; B)</th>'
        '</tr>'
        '</thead>'
        f'<tbody>{all_rows}</tbody>'
        '</table>'
        '</div>'
        '</div>'
    )
    st.markdown(table_container_html, unsafe_allow_html=True)


