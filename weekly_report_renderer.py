import json
import os
import streamlit as st
import pandas as pd
import datetime

REPORT_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weekly_report_data.json')

def load_weekly_report_data():
    if os.path.exists(REPORT_JSON_PATH):
        with open(REPORT_JSON_PATH, 'r') as f:
            return json.load(f)
    return []

def calculate_dynamic_weekly_matrix(master_df, category_code, prev_start, prev_end, curr_start, curr_end):
    """
    Computes exact 2-tier comparison matrix dynamically from live master data:
    Period | Previous Week (prev_start to prev_end) | Current Week (curr_start to curr_end) | KPI
    """
    if master_df is None or len(master_df) == 0:
        return None

    # Filter to category
    sub = master_df[master_df['Category'] == category_code].copy()
    if len(sub) == 0:
        return None

    sub['Date_Obj'] = pd.to_datetime(sub['Date'], errors='coerce').dt.date

    # Helper to calculate stats
    def calc_stats(data_subset):
        tot = len(data_subset)
        a = (data_subset['Status'] == 'A-Approved').sum()
        b = (data_subset['Status'] == 'B-Approved with Comments').sum()
        c = (data_subset['Status'] == 'C-Revise and Resubmit').sum()
        d = (data_subset['Status'] == 'D-Rejected').sum()
        ur = tot - (a + b + c + d)
        
        # Approved % = (A + B) / (Total - UR)
        decided = tot - ur
        appr_pct = f"{round((a + b) / decided * 100)}%" if decided > 0 else "-%"
        rej_pct = f"{round((c + d) / decided * 100)}%" if decided > 0 else "-%"
        return [str(tot), str(a), str(b), str(c), str(ur), appr_pct, rej_pct]

    # Prev Week data
    prev_cum = sub[sub['Date_Obj'] <= prev_end]
    prev_wk = sub[(sub['Date_Obj'] >= prev_start) & (sub['Date_Obj'] <= prev_end)]

    # Curr Week data
    curr_cum = sub[sub['Date_Obj'] <= curr_end]
    curr_wk = sub[(sub['Date_Obj'] >= curr_start) & (sub['Date_Obj'] <= curr_end)]

    p_cum_stats = calc_stats(prev_cum)
    p_wk_stats = calc_stats(prev_wk)
    c_cum_stats = calc_stats(curr_cum)
    c_wk_stats = calc_stats(curr_wk)

    prev_lbl = f"Previous Week ({prev_start.strftime('%d %b')} to {prev_end.strftime('%d %b')})"
    curr_lbl = f"Current Week ({curr_start.strftime('%d %b')} to {curr_end.strftime('%d %b')})"

    if category_code == 'NCR':
        def calc_ncr(data_subset):
            tot = len(data_subset)
            closed = (data_subset['Status'] == 'Closed').sum()
            opened = (data_subset['Status'] == 'Open').sum()
            resp = closed + opened
            ur = 0
            return [str(tot), str(resp), str(closed), str(opened), str(ur)]

        p_c = calc_ncr(prev_cum)
        p_w = calc_ncr(prev_wk)
        c_c = calc_ncr(curr_cum)
        c_w = calc_ncr(curr_wk)

        return [
            ["Period", prev_lbl, "", "", "", "", curr_lbl, "", "", "", ""],
            ["", "Total Issued", "Respond", "Closed", "Open", "U/R", "Total Issued", "Respond", "Closed", "Open", "U/R"],
            ["Cumulative", p_c[0], p_c[1], p_c[2], p_c[3], p_c[4], c_c[0], c_c[1], c_c[2], c_c[3], c_c[4]],
            ["Weekly", p_w[0], p_w[1], p_w[2], p_w[3], p_w[4], c_w[0], c_w[1], c_w[2], c_w[3], c_w[4]]
        ]

    matrix = [
        ["Period", prev_lbl, "", "", "", "", curr_lbl, "", "", "", "", "KPI", ""],
        ["", "Total", "Code A", "Code B", "Code C", "U/R", "Total", "Code A", "Code B", "Code C", "U/R", "% Approved", "% Rejection"],
        ["Cumulative", p_cum_stats[0], p_cum_stats[1], p_cum_stats[2], p_cum_stats[3], p_cum_stats[4], c_cum_stats[0], c_cum_stats[1], c_cum_stats[2], c_cum_stats[3], c_cum_stats[4], c_cum_stats[5], c_cum_stats[6]],
        ["Weekly", p_wk_stats[0], p_wk_stats[1], p_wk_stats[2], p_wk_stats[3], p_wk_stats[4], c_wk_stats[0], c_wk_stats[1], c_wk_stats[2], c_wk_stats[3], c_wk_stats[4], c_wk_stats[5], c_wk_stats[6]]
    ]
    return matrix


def update_table_headers_with_dates(table_matrix, prev_start, prev_end, curr_start, curr_end):
    """
    Dynamically updates row 0 headers in all comparison tables to match the active confirmed dates.
    Replaces static text like '17 Sep to 22 Sep' or '24 Sep to 30 Sep' with the confirmed intervals.
    """
    if not table_matrix or len(table_matrix) == 0:
        return table_matrix

    prev_lbl = f"Previous Week ({prev_start.strftime('%d %b')} to {prev_end.strftime('%d %b')})"
    curr_lbl = f"Current Week ({curr_start.strftime('%d %b')} to {curr_end.strftime('%d %b')})"

    new_matrix = [list(r) for r in table_matrix]
    r0 = new_matrix[0]

    found_first = False
    for idx, cell in enumerate(r0):
        c_lower = cell.lower().strip()
        if not c_lower or c_lower in ['period', 'discipline', 'sr. no', 'kpi']:
            continue

        if any(k in c_lower for k in ['last week', 'previous week', '17 sep', 'first week']) or (not found_first and 'week' in c_lower):
            r0[idx] = prev_lbl
            found_first = True
        elif any(k in c_lower for k in ['this week', 'current week', '24 sep', 'second week']) or (found_first and 'week' in c_lower):
            r0[idx] = curr_lbl

    return new_matrix


def render_comparison_table(table_matrix, title=""):
    """
    Renders the exact 2-tier header table from PPT:
    Period | Previous Week (prev_start to prev_end) | Current Week (curr_start to curr_end) | KPI
    """
    if not table_matrix or len(table_matrix) < 2:
        return

    html = ['<div class="ppt-ncr-table-container">']
    if title:
        html.append(f'<div style="padding: 10px 14px; font-weight: 800; font-size: 0.92rem; color: #14355A; background: #F8FAFC; border-bottom: 2px solid #CBD5E1;">{title}</div>')
    
    html.append('<table class="ppt-ncr-table">')
    
    # Process Rows
    num_cols = max(len(r) for r in table_matrix)
    
    html.append('<thead>')
    r0 = table_matrix[0]
    r1 = table_matrix[1] if len(table_matrix) > 1 else []
    
    # Check if 2-tier header
    if any(k in ' '.join(r0).lower() for k in ['last week', 'previous week', 'this week', 'current week', 'kpi']):
        html.append('<tr>')
        idx = 0
        while idx < len(r0):
            val = r0[idx].strip()
            colspan = 1
            while (idx + colspan < len(r0)) and (r0[idx + colspan].strip() == ''):
                colspan += 1
            align = "center" if any(k in val.lower() for k in ['week', 'kpi', 'period']) else "left"
            bg = "#0F2942" if ("this week" in val.lower() or "current week" in val.lower()) else "#14355A"
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
            style = ""
            if any(k in c_text for k in ['%', '95%', '96%', '98%', '92%', '85%']):
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


def render_weekly_report_view(master_df=None):
    """
    Renders the complete scrollable Weekly Quality Report with dynamic Previous vs. Current Week filters
    and explicit confirmation/submit controls.
    """
    # ── Session State Initialization for Confirmed Dates ──────────────────────────
    default_p_start = datetime.date(2026, 9, 17)
    default_p_end = datetime.date(2026, 9, 22)
    default_c_start = datetime.date(2026, 9, 24)
    default_c_end = datetime.date(2026, 9, 30)

    if 'wr_confirmed_prev_start' not in st.session_state:
        st.session_state.wr_confirmed_prev_start = default_p_start
    if 'wr_confirmed_prev_end' not in st.session_state:
        st.session_state.wr_confirmed_prev_end = default_p_end
    if 'wr_confirmed_curr_start' not in st.session_state:
        st.session_state.wr_confirmed_curr_start = default_c_start
    if 'wr_confirmed_curr_end' not in st.session_state:
        st.session_state.wr_confirmed_curr_end = default_c_end
    if 'wr_confirmed_live_sync' not in st.session_state:
        st.session_state.wr_confirmed_live_sync = True

    c_p_start = st.session_state.wr_confirmed_prev_start
    c_p_end = st.session_state.wr_confirmed_prev_end
    c_c_start = st.session_state.wr_confirmed_curr_start
    c_c_end = st.session_state.wr_confirmed_curr_end
    use_live_calc = st.session_state.wr_confirmed_live_sync

    prev_badge = f"{c_p_start.strftime('%d %b')} – {c_p_end.strftime('%d %b')}"
    curr_badge = f"{c_c_start.strftime('%d %b')} – {c_c_end.strftime('%d %b')}"

    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #14355A 0%, #1E40AF 100%); padding: 18px 22px; border-radius: 12px; color: white; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(20,53,90,0.15);'>
        <div style='font-size: 1.35rem; font-weight: 800; letter-spacing: -0.01em;'>📋 Weekly Quality Status Report</div>
        <div style='font-size: 0.85rem; opacity: 0.95; margin-top: 5px;'>
            Project: <strong>Royal Diriyah Opera House (105)</strong> &nbsp;&bull;&nbsp; 
            Comparison: <strong>Previous Week ({prev_badge})</strong> vs. <strong>Current Week ({curr_badge})</strong> &nbsp;&bull;&nbsp; 
            <span style='background:rgba(255,255,255,0.2); padding:2px 8px; border-radius:12px; font-weight:700;'>⚡ Active Report Interval</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Interactive Week Selection Form Toolbar with Confirm/Submit Button ─────────
    with st.form(key="wr_date_configuration_form"):
        st.markdown("<div style='font-weight:700; font-size:0.9rem; color:#1E3A8A; margin-bottom:4px;'>🗓️ Configure Comparison Intervals (Previous Week vs. Current Week)</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.78rem; color:#64748B; margin-bottom:12px;'>Select comparison date intervals and click <strong>Confirm & Update Report</strong> to update all table headers and KPI calculations across the entire report.</div>", unsafe_allow_html=True)
        
        wcol1, wcol2, wcol3, wcol4, wcol5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.4])
        
        with wcol1:
            form_prev_start = st.date_input("Previous Week Start", value=c_p_start, key="wr_inp_prev_start")
        with wcol2:
            form_prev_end = st.date_input("Previous Week End", value=c_p_end, key="wr_inp_prev_end")
        with wcol3:
            form_curr_start = st.date_input("Current Week Start", value=c_c_start, key="wr_inp_curr_start")
        with wcol4:
            form_curr_end = st.date_input("Current Week End", value=c_c_end, key="wr_inp_curr_end")
        with wcol5:
            st.write("")
            st.write("")
            submit_dates = st.form_submit_button("✅ Confirm & Update Report", type="primary", use_container_width=True)

        chk_col1, chk_col2 = st.columns([2, 1])
        with chk_col1:
            form_live_sync = st.checkbox("⚡ Live Calculate metrics from Aconex submittals register", value=use_live_calc, key="wr_chk_live")
        with chk_col2:
            st.caption(f"Active Report Dates: **{prev_badge}** vs. **{curr_badge}**")

        if submit_dates:
            st.session_state.wr_confirmed_prev_start = form_prev_start
            st.session_state.wr_confirmed_prev_end = form_prev_end
            st.session_state.wr_confirmed_curr_start = form_curr_start
            st.session_state.wr_confirmed_curr_end = form_curr_end
            st.session_state.wr_confirmed_live_sync = form_live_sync
            st.rerun()

    # Reset button outside the form
    r_col1, r_col2 = st.columns([4, 1.5])
    with r_col2:
        if st.button("↩️ Reset to Baseline PPT (17-22 / 24-30 Sep)", key="btn_wr_reset", use_container_width=True):
            st.session_state.wr_confirmed_prev_start = default_p_start
            st.session_state.wr_confirmed_prev_end = default_p_end
            st.session_state.wr_confirmed_curr_start = default_c_start
            st.session_state.wr_confirmed_curr_end = default_c_end
            st.session_state.wr_confirmed_live_sync = True
            st.rerun()

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

    # Slide to Category mapping for live dynamic calculation
    slide_cat_map = {
        5: 'MST',
        6: 'ITP',
        7: 'NCR',
        12: 'MAR',
        14: 'MIR',
        16: 'SHD',
        17: 'WIR'
    }

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

        # Check if live calculation requested for this slide's category
        if use_live_calc and (slide_no in slide_cat_map) and (master_df is not None):
            cat_code = slide_cat_map[slide_no]
            dynamic_matrix = calculate_dynamic_weekly_matrix(master_df, cat_code, c_p_start, c_p_end, c_c_start, c_c_end)
            if dynamic_matrix:
                render_comparison_table(dynamic_matrix, title=f"⚡ LIVE ACONEX SYNC TABLE: {cat_code}")
            elif tables:
                for tbl in tables:
                    updated_tbl = update_table_headers_with_dates(tbl, c_p_start, c_p_end, c_c_start, c_c_end)
                    render_comparison_table(updated_tbl)
        else:
            # Render Baseline PPT Tables with dynamically updated headers
            if tables:
                for tbl in tables:
                    updated_tbl = update_table_headers_with_dates(tbl, c_p_start, c_p_end, c_c_start, c_c_end)
                    render_comparison_table(updated_tbl)
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
