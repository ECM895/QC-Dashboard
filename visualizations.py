import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

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
    "Overdue": "#EF4444"
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html,body,[class*="css"],div.stMarkdown,div.stText,p,
span:not([class*="material"]):not([data-testid="stIcon"]):not([class*="Material"]){
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif!important;
}
.block-container{
  padding-top:.8rem!important;padding-bottom:3rem!important;
  padding-left:2.2rem!important;padding-right:2.2rem!important;
  max-width:1600px;
}
.stApp{background:#F0F4F8!important;}
#MainMenu{visibility:hidden!important;display:none!important;}
footer{visibility:hidden!important;display:none!important;}
header[data-testid="stHeader"]{background:transparent!important;z-index:99999!important;}
[data-testid="stStatusWidget"],.stDeployButton{display:none!important;visibility:hidden!important;}

/* Completely Remove Sidebar and Toggle Button */
[data-testid="stSidebar"], section[data-testid="stSidebar"], [data-testid="collapsedControl"]{
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  height: 0 !important;
  pointer-events: none !important;
}

/* Global buttons */
[data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,#2563EB 0%,#1D4ED8 100%)!important;
  border:none!important;border-radius:9px!important;font-weight:700!important;
  font-size:.82rem!important;letter-spacing:-.01em!important;padding:8px 10px!important;
  box-shadow:0 2px 8px rgba(37,99,235,.28)!important;color:#FFFFFF!important;
  white-space:nowrap!important;text-overflow:clip!important;overflow:visible!important;
  transition:all .15s ease!important;}
[data-testid="stBaseButton-primary"]:hover{
  box-shadow:0 4px 14px rgba(37,99,235,.4)!important;transform:translateY(-1px);}
[data-testid="stBaseButton-secondary"]{
  border-radius:9px!important;font-weight:600!important;font-size:.82rem!important;
  letter-spacing:-.01em!important;padding:8px 10px!important;
  border:1.5px solid #CBD5E1!important;background:#FFFFFF!important;color:#334155!important;
  white-space:nowrap!important;text-overflow:clip!important;overflow:visible!important;
  transition:all .15s ease!important;}
[data-testid="stBaseButton-secondary"]:hover{
  background:#F8FAFC!important;border-color:#94A3B8!important;color:#0F172A!important;}

/* Navigation Tabs as Real Interactive Buttons */
.nav-tab-bar{
  display:flex;gap:8px;background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;
  padding:6px;margin-bottom:16px;box-shadow:0 2px 6px rgba(15,23,42,.04);
}
.nav-tab{
  flex:1;text-align:center;padding:10px 14px;border-radius:8px;font-size:0.84rem;
  font-weight:600;color:#475569!important;text-decoration:none!important;
  display:flex;align-items:center;justify-content:center;gap:6px;
  background:#F8FAFC;border:1px solid #E2E8F0;
  box-shadow:0 1px 2px rgba(0,0,0,0.04);
  transition:all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
  cursor:pointer!important;
}
.nav-tab:hover{
  background:#EEF2F6!important;color:#1E293B!important;
  border-color:#CBD5E1!important;transform:translateY(-1px);
  box-shadow:0 3px 8px rgba(0,0,0,0.06);
}
.nav-tab.active{
  background:linear-gradient(135deg,#2563EB 0%,#1D4ED8 100%)!important;
  color:#FFFFFF!important;border:1px solid #1D4ED8!important;
  box-shadow:0 3px 10px rgba(37,99,235,0.35)!important;
  transform:translateY(-1px);
}

/* Section titles */
.page-section-title{
  font-size:1.05rem;font-weight:700;color:#0F172A;letter-spacing:-.01em;
  display:flex;align-items:center;gap:8px;margin:20px 0 14px 0;
  padding-bottom:10px;border-bottom:2px solid #E2E8F0;}
.page-section-title .dot{
  width:6px;height:6px;border-radius:50%;background:#2563EB;
  display:inline-block;flex-shrink:0;}

/* Executive header */
.exec-header{
  background:linear-gradient(125deg,#0F172A 0%,#1E293B 45%,#1A3666 100%);
  border-radius:16px;padding:22px 28px;color:white;margin-bottom:18px;
  box-shadow:0 10px 30px -8px rgba(15,23,42,.4),0 1px 0 rgba(255,255,255,.06) inset;
  display:flex;justify-content:space-between;align-items:center;
  flex-wrap:wrap;gap:16px;border:1px solid rgba(255,255,255,.07);
  position:relative;overflow:hidden;}
.exec-header::before{
  content:'';position:absolute;top:0;right:0;bottom:0;width:35%;
  background:radial-gradient(ellipse at top right,rgba(59,130,246,.12) 0%,transparent 70%);
  pointer-events:none;}
.exec-header-title{font-size:1.55rem;font-weight:800;letter-spacing:-.03em;margin:0;line-height:1.2;color:#FFFFFF;}
.exec-header-subtitle{font-size:.82rem;color:#94A3B8;margin-top:5px;font-weight:400;}
.exec-header-subtitle strong{color:#CBD5E1;font-weight:600;}
.exec-badge{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(59,130,246,.18);border:1px solid rgba(96,165,250,.3);
  color:#93C5FD;padding:6px 14px;border-radius:9999px;
  font-size:.72rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;}
.exec-date-badge{
  background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);
  padding:6px 14px;border-radius:9999px;font-size:.75rem;font-weight:600;color:#E2E8F0;}

/* Hero metric grid */
.hero-metric-grid{
  display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px;}
.hero-metric-card{
  background:#FFFFFF;border-radius:14px;padding:18px 20px;
  border:1px solid #E8EDF2;box-shadow:0 2px 10px rgba(15,23,42,.05);
  position:relative;overflow:hidden;transition:box-shadow .2s ease;}
.hero-metric-card:hover{box-shadow:0 6px 20px rgba(15,23,42,.1);}
.hero-metric-accent{position:absolute;top:0;left:0;right:0;height:3px;}
.hero-metric-icon{
  position:absolute;top:16px;right:16px;width:36px;height:36px;
  border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;}
.hero-metric-label{
  font-size:.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;color:#94A3B8;margin-bottom:8px;}
.hero-metric-val{font-size:2rem;font-weight:800;color:#0F172A;line-height:1;letter-spacing:-.03em;}
.hero-metric-sub{font-size:.73rem;color:#94A3B8;margin-top:7px;}
.hero-pill{display:inline-block;padding:2px 8px;border-radius:5px;font-size:.68rem;font-weight:700;}

/* Bento cards */
.bento-card{
  background:#FFFFFF;border:1px solid #E8EDF2;border-radius:14px;overflow:hidden;
  box-shadow:0 2px 8px rgba(15,23,42,.04);margin-bottom:14px;
  transition:all .2s cubic-bezier(.4,0,.2,1);cursor:pointer;
  text-decoration:none;color:inherit;display:block;}
.bento-card:hover{
  border-color:#3B82F6;
  box-shadow:0 8px 24px -4px rgba(37,99,235,.16),0 0 0 1px rgba(59,130,246,.3);
  transform:translateY(-3px);}
.bento-header{
  padding:13px 16px;background:#FAFBFC;border-bottom:1px solid #F0F4F8;
  display:flex;justify-content:space-between;align-items:center;}
.bento-title-group{display:flex;align-items:center;gap:10px;}
.bento-icon-badge{
  width:34px;height:34px;border-radius:8px;background:#EFF6FF;color:#2563EB;
  display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;}
.bento-title{font-size:.9rem;font-weight:700;color:#0F172A;line-height:1.3;}
.bento-arrow{font-size:.78rem;color:#94A3B8;font-weight:400;margin-left:4px;}
.bento-rate-badge{font-size:.75rem;font-weight:700;padding:4px 10px;border-radius:9999px;white-space:nowrap;flex-shrink:0;}
.bento-body{padding:16px 14px 12px 14px;display:grid;gap:8px;text-align:center;}
.bento-metric-val{font-size:1.45rem;font-weight:800;line-height:1.1;letter-spacing:-.02em;}
.bento-metric-label{font-size:.62rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.04em;margin-top:3px;}
.bento-progress-container{padding:0 16px 14px 16px;}
.bento-progress-track{height:4px;border-radius:9999px;background:#F1F5F9;overflow:hidden;}
.bento-progress-fill{height:100%;border-radius:9999px;}

/* Detail KPI cards */
.detail-kpi-card{
  background:#FFFFFF;border:1px solid #E8EDF2;border-radius:12px;padding:16px;
  box-shadow:0 2px 6px rgba(15,23,42,.04);border-top:3px solid #2563EB;
  transition:box-shadow .15s ease;}
.detail-kpi-card:hover{box-shadow:0 6px 16px rgba(15,23,42,.09);}
.detail-kpi-title{font-size:.68rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;}
.detail-kpi-value{font-size:1.75rem;font-weight:800;color:#0F172A;line-height:1.1;letter-spacing:-.02em;}
.detail-kpi-sub{font-size:.72rem;color:#94A3B8;margin-top:5px;font-weight:400;}

/* Lessons cards */
.ll-card{
  background:#FFFFFF;border:1px solid #E8EDF2;border-radius:16px;
  box-shadow:0 4px 16px rgba(15,23,42,.04);margin-bottom:20px;overflow:hidden;
  transition:all .25s ease;}
.ll-card:hover{box-shadow:0 10px 28px rgba(15,23,42,.09);border-color:#CBD5E1;transform:translateY(-2px);}
.ll-card-header{
  padding:16px 22px;background:linear-gradient(135deg,#F8FAFC 0%,#F1F5F9 100%);
  border-bottom:1px solid #E8EDF2;display:flex;justify-content:space-between;
  align-items:center;flex-wrap:wrap;gap:10px;}
.ll-id-badge{
  display:inline-flex;align-items:center;gap:6px;background:#0F172A;color:#FFFFFF;
  font-weight:800;font-size:.76rem;padding:4px 10px;border-radius:6px;letter-spacing:.04em;}
.ll-discipline-badge{
  display:inline-flex;align-items:center;gap:5px;background:#EFF6FF;color:#1D4ED8;
  border:1px solid #BFDBFE;font-weight:700;font-size:.72rem;padding:4px 10px;border-radius:9999px;}
.ll-card-body{padding:22px;}
.ll-title{font-size:1.1rem;font-weight:800;color:#0F172A;line-height:1.35;margin-bottom:16px;}
.ll-dual-box{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;}
.ll-problem-box{background:#FEF2F2;border-left:4px solid #EF4444;border-radius:0 10px 10px 0;padding:12px 16px;}
.ll-solution-box{background:#ECFDF5;border-left:4px solid #10B981;border-radius:0 10px 10px 0;padding:12px 16px;}
.ll-section-tag{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;margin-bottom:7px;display:flex;align-items:center;gap:5px;}
.ll-meta-bar{
  background:#F8FAFC;border:1px solid #E8EDF2;border-radius:10px;padding:10px 16px;
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;
  font-size:.75rem;color:#475569;}
.schedule-upcoming-pill{
  background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;padding:3px 8px;
  border-radius:6px;font-weight:700;font-size:.7rem;display:inline-flex;align-items:center;gap:4px;}
.schedule-done-pill{
  background:#ECFDF5;color:#065F46;border:1px solid #A7F3D0;padding:3px 8px;
  border-radius:6px;font-weight:700;font-size:.7rem;display:inline-flex;align-items:center;gap:4px;}

[data-testid="stTabs"] [data-testid="stTab"]{font-weight:600!important;font-size:.875rem!important;}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"]{color:#2563EB!important;border-bottom-color:#2563EB!important;}
[data-testid="stDataFrame"]{border-radius:10px!important;border:1px solid #E2E8F0!important;box-shadow:0 2px 6px rgba(15,23,42,.04)!important;}
hr{border-color:#E8EDF2!important;margin:20px 0!important;}
</style>
"""

def inject_custom_css():
    st.markdown(CSS, unsafe_allow_html=True)

def render_hero_header(project_name="Royal Diriyah Opera House", pmc="DII-Jasara", date_range_text="All Time"):
    import base64
    logo_html = ""
    logo_path = os.path.join(os.path.dirname(__file__), "ecm_logo.png")
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as lf:
                b64 = base64.b64encode(lf.read()).decode("utf-8")
                logo_html = (
                    f'<div style="background:rgba(255,255,255,.95);padding:7px 14px;border-radius:10px;' +
                    f'box-shadow:0 2px 10px rgba(0,0,0,.18);display:flex;align-items:center;flex-shrink:0;">' +
                    f'<img src="data:image/png;base64,{b64}" alt="ECM JV" style="height:40px;object-fit:contain;">' +
                    f'</div>'
                )
        except Exception:
            pass
    html = (
        f'<div class="exec-header">' +
        f'  <div style="display:flex;align-items:center;gap:18px;position:relative;z-index:1;">' +
        f'    {logo_html}' +
        f'    <div>' +
        f'      <div class="exec-header-title">QA/QC Opera House Dashboard</div>' +
        f'      <div class="exec-header-subtitle">Project: <strong>{project_name}</strong>' +
        f'        &nbsp;&nbsp;•&nbsp;&nbsp; PMC: <strong>{pmc}</strong>' +
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
    c1 = _hero_card("#2563EB","📋","#EFF6FF","Total Quality Submittals",f'{total_inspections:,}',
                    "Active & archived Aconex records","ALL","background:#DBEAFE;color:#1D4ED8;")
    rc = "#059669" if overall_approval_rate >= 85 else ("#D97706" if overall_approval_rate >= 65 else "#DC2626")
    c2 = _hero_card(rc,"🎯","#ECFDF5","Quality Approval Rate (A+B)",
                    f'<span style="color:{rc};">{overall_approval_rate:.1f}%</span>',
                    "Compliant first-time & comment passes","TARGET: 85%","background:#ECFDF5;color:#059669;")
    nc = "#DC2626" if open_ncrs > 0 else "#059669"
    c3 = _hero_card(nc,"⚠️","#FEF2F2","Active Open NCRs",
                    f'<span style="color:{nc};">{open_ncrs:,}</span>',
                    "Non-conformances pending closure","HOLD POINTS","background:#FEF2F2;color:#DC2626;")
    c4 = _hero_card("#0D9488","🏗️","#F0FDFA","Total Concrete Placed",
                    f'<span style="color:#0F766E;">{concrete_volume:,.1f} <span style="font-size:1rem;font-weight:600;">m³</span></span>',
                    "Volume cast in filtered period","CASTING LOG","background:#CCFBF1;color:#0F766E;")
    st.markdown(f'<div class="hero-metric-grid">{c1}{c2}{c3}{c4}</div>', unsafe_allow_html=True)

def render_category_box(title, total_val, val1, val2, val3, val4, rate,
                        is_alt_color=False, is_ncr=False, cat_id=None):
    icons = {"WIR":"📋","MIR":"📦","MAR":"📑","MST":"📄","ITP":"🛡️","SHD":"📐","NCR":"⚠️"}
    icon = icons.get(cat_id, "📊")
    rate_num = float(str(rate).replace("%","")) if "%" in str(rate) else 0
    if is_ncr:
        pc = "#10B981" if rate_num >= 80 else ("#F59E0B" if rate_num >= 50 else "#EF4444")
    else:
        pc = "#10B981" if rate_num >= 80 else ("#F59E0B" if rate_num >= 60 else "#EF4444")
    bb = "#EFF6FF" if is_alt_color else "#ECFDF5"
    bc = "#1D4ED8" if is_alt_color else "#059669"
    bbd = "#BFDBFE" if is_alt_color else "#A7F3D0"
    rl = "Closure Rate" if is_ncr else "Approval Rate"

    def mc(value, label, color="#0F172A"):
        return (f'<div style="text-align:center;">' +
                f'<div class="bento-metric-val" style="color:{color};">{value}</div>' +
                f'<div class="bento-metric-label">{label}</div></div>')

    cells = [mc(total_val,"TOTAL")]
    if is_ncr:
        cells += [mc(val1,"CLOSED","#10B981"), mc(val2,"OPEN","#EF4444")]
        gc = "repeat(3,1fr)"
    else:
        cells += [mc(val1,"CODE A","#10B981"), mc(val2,"CODE B","#0EA5E9"),
                  mc(val3,"CODE C","#F59E0B"), mc(val4,"CODE D","#EF4444")]
        gc = "repeat(5,1fr)"

    body = "".join(cells)
    html = (
        f'<div class="bento-card">' +
        f'  <div class="bento-header">' +
        f'    <div class="bento-title-group">' +
        f'      <div class="bento-icon-badge">{icon}</div>' +
        f'      <div class="bento-title">{title}</div>' +
        f'    </div>' +
        f'    <div class="bento-rate-badge" style="background:{bb};color:{bc};border:1px solid {bbd};">' +
        f'      {rl}: {rate}</div>' +
        f'  </div>' +
        f'  <div class="bento-body" style="grid-template-columns:{gc};">{body}</div>' +
        f'  <div class="bento-progress-container">' +
        f'    <div class="bento-progress-track">' +
        f'      <div class="bento-progress-fill" style="width:{min(rate_num,100)}%;background:{pc};"></div>' +
        f'    </div></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def section_title(text):
    st.markdown(
        f'<div class="page-section-title"><span class="dot"></span>{text}</div>',
        unsafe_allow_html=True
    )

def render_detail_kpi_cards(cat, total, a, b, c, d, rate):
    labels = {
        "WIR":"TOTAL WORK INSPECTIONS","MIR":"TOTAL MATERIAL INSPECTIONS",
        "NCR":"TOTAL NON-CONFORMANCES","SHD":"TOTAL SHOP DRAWINGS",
        "MAR":"TOTAL MATERIAL APPROVALS","MST":"TOTAL METHOD STATEMENTS",
        "ITP":"TOTAL INSPECTION PLANS"
    }
    t1 = labels.get(cat, f"TOTAL {cat} RECORDS")
    def kpi(accent, title, val_html, sub):
        return (f'<div class="detail-kpi-card" style="border-top-color:{accent};">' +
                f'<div class="detail-kpi-title">{title}</div>' +
                f'<div class="detail-kpi-value" style="color:{accent};">{val_html}</div>' +
                f'<div class="detail-kpi-sub">{sub}</div></div>')
    cards = [kpi("#2563EB",t1,f"{total:,}","All submissions combined")]
    if cat == "NCR":
        cards.append(kpi("#EF4444","OPEN (ACTIVE)",f"{d:,}","Requires contractor action"))
        cards.append(kpi("#10B981","CLOSED & VERIFIED",f"{a+b:,}","Rectification approved"))
    else:
        cards.append(kpi("#10B981","CODE A — APPROVED",f"{a:,}","Clean pass, no comments"))
        cards.append(kpi("#0EA5E9","CODE B — APP W/ CMT",f"{b:,}","Approved with notes"))
        cards.append(kpi("#F59E0B","CODE C — REVISE",f"{c:,}","Revise and resubmit"))
        cards.append(kpi("#EF4444","CODE D — REJECTED",f"{d:,}","Non-compliant, rejected"))
    lbl = "Closure Rate" if cat=="NCR" else "Quality Compliance (A+B)"
    cards.append(kpi("#6366F1","COMPLIANCE INDEX",str(rate),lbl))
    html = f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px;">{"".join(cards)}</div>'
    st.markdown(html, unsafe_allow_html=True)

def apply_chart_style(fig, title, height=340):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>",
                   font=dict(family="Inter,sans-serif",size=13,color="#0F172A"),
                   x=0.0,y=0.97,xanchor="left"),
        font=dict(family="Inter,sans-serif",color="#64748B",size=11),
        plot_bgcolor="#FFFFFF",paper_bgcolor="#FFFFFF",
        margin=dict(t=50,b=30,l=40,r=20),height=height,
        hoverlabel=dict(bgcolor="#0F172A",font_size=12,
                        font_family="Inter,sans-serif",font_color="#FFFFFF",bordercolor="rgba(15,23,42,0)"),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,
                    font=dict(size=10,color="#64748B"),bgcolor="rgba(0,0,0,0)")
    )
    fig.update_xaxes(showgrid=False,linecolor="#E2E8F0",tickfont=dict(size=11,color="#64748B"),ticklen=0)
    fig.update_yaxes(showgrid=True,gridwidth=1,gridcolor="#F1F5F9",
                     linecolor="rgba(0,0,0,0)",tickfont=dict(size=11,color="#64748B"))
    return fig

def plot_donut_chart(labels, values, title, colors, height=320):
    total = sum(values) if values is not None else 0
    fig = go.Figure(data=[go.Pie(
        labels=labels,values=values,hole=0.65,
        marker=dict(colors=colors,line=dict(color="#FFFFFF",width=2.5)),
        textinfo="percent",textfont=dict(size=11,family="Inter",color="#FFFFFF",weight=700),
        hoverinfo="label+value+percent"
    )])
    fig.add_annotation(
        text=f"<b style='font-size:22px;color:#0F172A;'>{total:,}</b><br><span style='font-size:10px;color:#94A3B8;'>TOTAL</span>",
        x=0.5,y=0.5,font=dict(family="Inter"),showarrow=False
    )
    apply_chart_style(fig,title,height=height)
    fig.update_layout(showlegend=True,margin=dict(t=50,b=20,l=20,r=20))
    return fig

def plot_100p_stacked_bar(df, x_col, y_col, color_col, title, color_map, height=360):
    fig = px.bar(df,x=x_col,y=y_col,color=color_col,color_discrete_map=color_map,
                 text=df[y_col].apply(lambda x: f'{x:.0f}%' if x > 6 else ""))
    fig.update_traces(textposition="inside",
                      textfont=dict(size=11,family="Inter",color="#FFFFFF",weight=700),
                      marker=dict(line=dict(color="#FFFFFF",width=1)))
    apply_chart_style(fig,title,height=height)
    fig.update_yaxes(title="Proportion (%)",range=[0,100])
    fig.update_xaxes(title="")
    return fig

def plot_grouped_bar_chart(df, x_col, y_col, color_col, title, color_map, height=340):
    fig = px.bar(df,x=x_col,y=y_col,color=color_col,barmode="group",
                 color_discrete_map=color_map,text_auto=".1f")
    fig.update_traces(textposition="outside",textfont=dict(size=10,family="Inter"),
                      marker=dict(line=dict(width=0)),cliponaxis=False)
    apply_chart_style(fig,title,height=height)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Volume (m³)")
    return fig

def plot_bar_chart(df, x_col, y_col, title, color="#2563EB", height=320):
    fig = px.bar(df,x=x_col,y=y_col,text_auto=True)
    fig.update_traces(marker_color=color,textposition="outside",
                      textfont=dict(size=11,family="Inter",color="#0F172A",weight=700),
                      cliponaxis=False)
    apply_chart_style(fig,title,height=height)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Count")
    return fig

def plot_pareto_chart(df, x_col, y_col, cum_col, title, height=350):
    fig = make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=df[x_col],y=df[y_col],name="Issue Count",marker_color="#2563EB",
                         text=df[y_col],textposition="inside",textfont=dict(color="#FFFFFF",weight=700)),secondary_y=False)
    fig.add_trace(go.Scatter(x=df[x_col],y=df[cum_col],name="Cumulative %",
                             marker=dict(color="#F59E0B",size=8,line=dict(color="#FFFFFF",width=2)),
                             line=dict(color="#F59E0B",width=2.5),mode="lines+markers+text",
                             text=[f"{v:.0f}%" for v in df[cum_col]],textposition="top center",
                             textfont=dict(size=10,color="#B45309",weight=700)),secondary_y=True)
    apply_chart_style(fig,title,height=height)
    fig.update_yaxes(title_text="Issue Count",secondary_y=False)
    fig.update_yaxes(title_text="Cumulative %",range=[0,115],secondary_y=True)
    fig.update_xaxes(title="")
    return fig

def plot_post_pour_status(df, height=350):
    status_counts = df.groupby(["Zone","Status"]).size().reset_index(name="Count")
    color_map = {"Open":"#EF4444","Repaired":"#F59E0B","Inspected":"#10B981"}
    fig = px.bar(status_counts,x="Zone",y="Count",color="Status",
                 color_discrete_map=color_map,barmode="stack",text_auto=True)
    fig.update_traces(textposition="inside",textfont=dict(color="#FFFFFF",weight=700))
    apply_chart_style(fig,"POST-POUR DEFECTS BY ZONE",height=height)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Defect Count")
    return fig

def render_ncr_warning_table(df):
    def highlight_row(row):
        is_overdue = row.get("Days Open",0) > 7
        s = "background-color:#FEF2F2;color:#991B1B;font-weight:600;" if is_overdue else ""
        return [s for _ in row]
    styled_df = df.style.apply(highlight_row,axis=1)
    st.dataframe(styled_df,use_container_width=True,hide_index=True)

def render_lesson_learned_card(item):
    ll_id       = item.get("Lesson Learned ID","LL-000")
    title       = item.get("Lesson Learned Title","Untitled Lesson")
    domain      = item.get("Discipline / Domain","General Quality")
    impact_cat  = item.get("Impact Category","Quality & Engineering")
    problem     = item.get("Systemic Root Cause / Problem Statement","N/A")
    consequence = item.get("Detailed Operational Impact & Failure Mechanism","N/A")
    controls    = item.get("Streamlined Engineering & Management Control (Corrective & Preventive Actions)","N/A")
    governance  = item.get("Mandatory Verification & Governance Mechanism","N/A")
    scope       = item.get("Applicability Scope & Phase","All Works")
    source      = item.get("Originating Reference / Source Mapping","Project Site")
    controls_html = "<br>".join([f"• {l.strip()}" for l in str(controls).split("\n") if l.strip()])
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
                    <div style="font-size:.8rem;color:#64748B;line-height:1.45;"><strong>Consequence:</strong> {consequence}</div>
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
    bp_id       = item.get("Best Practice ID","BP-000")
    title       = item.get("Best Practice Title","Standard Practice")
    domain      = item.get("Discipline / Domain","General Quality")
    context     = item.get("Operational Context & Challenge Addressed","N/A")
    methodology = item.get("Standardized Methodology / Execution Protocol","N/A")
    benefits    = item.get("Measurable Benefits & Value Added","N/A")
    governance  = item.get("Implementation & Governance Mechanism","N/A")
    scope       = item.get("Applicability Scope","All Works")
    source      = item.get("Originating Reference / Source Mapping","Field Proven")
    method_html = "<br>".join([f"• {l.strip()}" for l in str(methodology).split("\n") if l.strip()])
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
