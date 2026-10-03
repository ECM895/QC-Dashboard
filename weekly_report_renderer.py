import json
import os
import streamlit as st
import pandas as pd

REPORT_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weekly_report_data.json')

def load_weekly_report_data():
    if os.path.exists(REPORT_JSON_PATH):
        with open(REPORT_JSON_PATH, 'r') as f:
            return json.load(f)
    return []

def render_comparison_table(table_matrix, title=""):
    """
    Renders the exact 2-tier header table from PPT:
    Period | Last Week (17 Sep to 22 Sep) | This Week (24 Sep to 30 Sep) | KPI
    """
    if not table_matrix or len(table_matrix) < 2:
        return

    html = ['<div class="ppt-ncr-table-container">']
    if title:
        html.append(f'<div style="padding: 10px 14px; font-weight: 800; font-size: 0.92rem; color: #14355A; background: #F8FAFC; border-bottom: 2px solid #CBD5E1;">{title}</div>')
    
    html.append('<table class="ppt-ncr-table">')
    
    # Process Rows
    # Determine header rows (usually first 1 or 2 rows)
    num_cols = max(len(r) for r in table_matrix)
    
    html.append('<thead>')
    r0 = table_matrix[0]
    r1 = table_matrix[1] if len(table_matrix) > 1 else []
    
    # Check if 2-tier header
    if any(k in ' '.join(r0).lower() for k in ['last week', 'previous week', 'this week', 'kpi']):
        html.append('<tr>')
        # Render r0 with colspans
        idx = 0
        while idx < len(r0):
            val = r0[idx].strip()
            # Count empty follower cells for colspan
            colspan = 1
            while (idx + colspan < len(r0)) and (r0[idx + colspan].strip() == ''):
                colspan += 1
            align = "center" if any(k in val.lower() for k in ['week', 'kpi', 'period']) else "left"
            bg = "#0F2942" if "this week" in val.lower() else "#14355A"
            html.append(f'<th colspan="{colspan}" style="text-align:{align}; background:{bg}; border-right:1px solid rgba(255,255,255,0.15);">{val}</th>')
            idx += colspan
        html.append('</tr>')

        # Subheaders r1
        if r1:
            html.append('<tr>')
            for col_val in r1:
                align = "center" if col_val.strip() not in ['Period', 'Discipline', ''] else "left"
                html.append(f'<th style="text-align:{align}; font-size:0.75rem; background:#1E3A8A; border-right:1px solid rgba(255,255,255,0.12);">{col_val}</th>')
            html.append('</tr>')
            start_row = 2
        else:
            start_row = 1
    else:
        # Standard single row header
        html.append('<tr>')
        for col_val in r0:
            html.append(f'<th>{col_val}</th>')
        html.append('</tr>')
        start_row = 1
        
    html.append('</thead><tbody>')

    # Data Rows
    for r_idx in range(start_row, len(table_matrix)):
        row_vals = table_matrix[r_idx]
        html.append('<tr>')
        for c_idx, cell_val in enumerate(row_vals):
            c_text = cell_val.strip()
            # Highlight KPI / percentage / overdue
            style = ""
            if any(k in c_text for k in ['%', '95%', '96%', '98%', '92%']):
                style = "font-weight: 700; color: #10B981; text-align: center;"
            elif c_idx == 0:
                style = "font-weight: 700; color: #1E293B;"
            elif c_text.isdigit():
                style = "text-align: center; font-weight: 600;"
            else:
                style = "text-align: left;"
                
            html.append(f'<td style="{style}">{c_text}</td>')
        html.append('</tr>')

    html.append('</tbody></table></div>')
    st.markdown('\n'.join(html), unsafe_allow_html=True)


def render_weekly_report_view():
    """
    Renders the complete scrollable Weekly Quality Report exactly as per the PowerPoint presentation.
    """
    st.markdown("""
    <div style='background: linear-gradient(135deg, #14355A 0%, #1E40AF 100%); padding: 18px 22px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(20,53,90,0.15);'>
        <div style='font-size: 1.35rem; font-weight: 800; letter-spacing: -0.01em;'>📋 Weekly Quality Status Report</div>
        <div style='font-size: 0.85rem; opacity: 0.9; margin-top: 4px;'>Project: <strong>Royal Diriyah Opera House (105)</strong> &nbsp;&bull;&nbsp; Comparison: <strong>Previous Week (17–22 Sep) vs. Current Week (24–30 Sep)</strong> &nbsp;&bull;&nbsp; Cumulative Progress &amp; KPI Metrics</div>
    </div>
    """, unsafe_allow_html=True)

    slides = load_weekly_report_data()
    if not slides:
        st.warning("Weekly Quality Report data is being loaded or file not found in auto_logs.")
        return

    # Table of Contents Quick Pills
    toc_titles = [
        ("MTS", "Method Statements", 5),
        ("ITP", "Inspection & Test Plans", 6),
        ("NCR", "External NCRs", 7),
        ("SOR", "Site Observations", 8),
        ("NCR-INT", "Internal NCRs", 9),
        ("TEST", "Test Reports", 10),
        ("PQD", "Prequalifications", 11),
        ("MAR", "Material Approvals", 12),
        ("MSA", "Material Samples", 13),
        ("MIR", "Material Inspections", 14),
        ("RFI", "Requests for Information", 15),
        ("SHD", "Shop Drawings", 16),
        ("WIR", "Work Inspections", 17),
        ("AUDIT", "Audit Plans", 20),
        ("CONCERNS", "Area of Concerns", 25)
    ]

    pills_html = ["<div style='display:flex; flex-wrap:wrap; gap:8px; margin-bottom:24px;'>"]
    for code, lbl, slide_no in toc_titles:
        pills_html.append(f"<a href='#slide-{slide_no}' style='text-decoration:none; padding:5px 12px; background:#FFFFFF; border:1px solid #CBD5E1; border-radius:20px; font-size:0.75rem; font-weight:700; color:#1E3A8A; box-shadow:0 1px 3px rgba(0,0,0,0.05); transition:all 0.2s;'>📌 {code} — {lbl}</a>")
    pills_html.append("</div>")
    st.markdown("".join(pills_html), unsafe_allow_html=True)

    # Render Each Slide as a Section
    for slide in slides:
        slide_no = slide['slide_number']
        title = slide['title']
        tables = slide['tables']
        texts = slide['text_blocks']

        # Skip cover page or empty thank you
        if slide_no in [1, 2, 27]:
            continue

        st.markdown(f"<div id='slide-{slide_no}' style='margin-top: 28px; padding-top: 10px; border-top: 2px solid #E2E8F0;'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 1.15rem; font-weight: 800; color: #14355A; display:flex; align-items:center; gap:8px;'><span style='background:#14355A; color:#FFFFFF; font-size:0.72rem; padding:3px 8px; border-radius:4px;'>SLIDE {slide_no}</span> {title}</div>", unsafe_allow_html=True)

        # Context texts if any
        if texts:
            for txt in texts:
                if txt.strip() and not txt.startswith("DD-2023"):
                    st.markdown(f"<p style='font-size:0.85rem; color:#475569; margin: 4px 0 10px 0;'>{txt}</p>", unsafe_allow_html=True)

        # Render Tables
        if tables:
            for t_idx, tbl in enumerate(tables):
                render_comparison_table(tbl)
        else:
            if slide_no in [18, 19]:
                st.info("🎓 Training, Induction and Compliance records synchronized.")
            elif slide_no in [23]:
                st.info("👷 Quality Resources Deployment active on site.")
            elif slide_no in [24]:
                st.info("📑 Field Change Requests (FCR) tracking active.")
            elif slide_no in [26]:
                st.info("📌 Any Other Business (AOB) items logged.")

    st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)
