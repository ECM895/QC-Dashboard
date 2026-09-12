import streamlit as st
import datetime
import pandas as pd
import math
import os
import shutil
from data_handler import (
    process_uploaded_logs, filter_data, get_ncr_master_data,
    get_training_data, get_lessons_learned_data
)
from visualizations import (
    inject_custom_css, render_hero_header, render_hero_metric_cards,
    render_category_box, section_title,
    plot_donut_chart, plot_bar_chart, plot_grouped_bar_chart,
    plot_100p_stacked_bar, plot_pareto_chart,
    render_ncr_warning_table, render_lesson_learned_card,
    render_best_practice_card, status_color_map
)

from auth_manager import (
    authenticate_user, log_user_access, add_user, 
    delete_user, get_all_users_df, get_access_stats
)

st.set_page_config(
    page_title="QA/QC Opera House Dashboard | Royal Diriyah Opera House",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()

# ── Authentication Gate ────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None

if not st.session_state.authenticated:
    _, center_col, _ = st.columns([1, 1.3, 1])
    with center_col:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        if os.path.exists("ecm_logo.png"):
            st.image("ecm_logo.png", use_container_width=True)
        st.markdown("""
            <div style='text-align: center; margin-bottom: 24px;'>
                <div style='font-size: 1.4rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;'>
                    Royal Diriyah Opera House
                </div>
                <div style='font-size: 0.88rem; font-weight: 600; color: #64748B;'>
                    QA/QC Executive Management Platform &bull; ECM-JV
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #1E293B; margin-bottom: 12px;'>🔒 Sign In to Access Dashboard</div>", unsafe_allow_html=True)
            login_username = st.text_input("Username or Email", placeholder="e.g. uzair087 or name@ecm-jv.com", key="input_login_user")
            login_password = st.text_input("Password", type="password", placeholder="Enter your password", key="input_login_pass")
            
            if st.button("Sign In ➔", type="primary", use_container_width=True):
                if not login_username or not login_password:
                    st.error("Please enter both username/email and password.")
                else:
                    success, user_dict = authenticate_user(login_username, login_password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_info = user_dict
                        log_user_access(user_dict["username"], user_dict.get("email", ""))
                        st.success(f"Welcome back, {user_dict['username']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username/email or password. Please contact QA/QC administration.")

        st.markdown("""
            <div style='text-align: center; font-size: 0.78rem; color: #94A3B8; margin-top: 18px;'>
                Restricted Project Access &bull; All sessions are monitored & logged for quality assurance.
            </div>
        """, unsafe_allow_html=True)
    st.stop()

# State Initialization
cat_param = st.query_params.get("category", None)
if cat_param:
    if cat_param == "NCR":
        st.session_state.current_view = "NCR"
    elif cat_param in ["WIR", "MIR", "MAR", "MST", "ITP", "SHD"]:
        st.session_state.current_view = "DRILLDOWN"
        st.session_state.selected_category = cat_param
    st.query_params.clear()

if 'current_view' not in st.session_state:
    st.session_state.current_view = "OVERVIEW"
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = "WIR"
if 'page_num' not in st.session_state:
    st.session_state.page_num = 1
if 'ppt_data' not in st.session_state:
    st.session_state.ppt_data = None
if 'saved_upload_names' not in st.session_state:
    st.session_state.saved_upload_names = set()

# Ensure folders exist
AUTO_DIR = "auto_logs"
LOGS_DIR = "logs"
UPLOAD_DIR = ".temp_uploads"
for d in [AUTO_DIR, LOGS_DIR, UPLOAD_DIR]:
    os.makedirs(d, exist_ok=True)

# -------------------------------------------------------------
# MODAL POPUP DIALOG FOR FILTERED RECORDS
# -------------------------------------------------------------
@st.dialog("📋 Submittal Records Breakdown", width="large")
def show_status_popup(cat, status_name, filtered_records):
    st.markdown(f"<div style='font-size: 1.25rem; font-weight: 800; color: #0F172A; margin-bottom: 2px;'>{cat} — {status_name}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size: 0.85rem; color: #64748B; margin-bottom: 14px;'>Filtered dataset containing <strong>{len(filtered_records):,}</strong> records.</div>", unsafe_allow_html=True)
    
    col_d1, col_d2 = st.columns([2.5, 1.5])
    with col_d2:
        csv_data = filtered_records.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"⬇️ Download CSV ({len(filtered_records):,} rows)",
            data=csv_data,
            file_name=f"{cat}_{status_name.replace(' ', '_')}_{datetime.date.today()}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
    
    st.dataframe(filtered_records, use_container_width=True, hide_index=True)

# Sidebar
with st.sidebar:
    # ECM JV Logo in Sidebar
    if os.path.exists("ecm_logo.png"):
        st.image("ecm_logo.png", use_container_width=True)
        st.markdown("<div style='text-align: center; font-size: 0.72rem; font-weight: 700; color: #64748B; margin-top: -8px; margin-bottom: 14px;'>EL SEIF - CSCEC - MIDMAC JV</div>", unsafe_allow_html=True)

    # User Profile & Logout section
    cur_user = st.session_state.get("user_info", {})
    user_name = cur_user.get("username", "User")
    user_role = cur_user.get("role", "viewer").upper()
    user_email = cur_user.get("email", "")
    badge_color = "#2563EB" if user_role == "ADMIN" else "#64748B"

    st.markdown(f"""
        <div style='background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 10px; padding: 10px 12px; margin-bottom: 14px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='font-size: 0.85rem; font-weight: 700; color: #0F172A;'>👤 {user_name}</span>
                <span style='background: {badge_color}; color: #FFFFFF; font-size: 0.68rem; font-weight: 800; padding: 2px 7px; border-radius: 6px;'>{user_role}</span>
            </div>
            <div style='font-size: 0.75rem; color: #64748B; margin-top: 3px; word-break: break-all;'>{user_email}</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔒 Sign Out", key="btn_signout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

    st.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;margin-top:12px;margin-bottom:10px;'>🎛️ Navigation</div>", unsafe_allow_html=True)
    nav_items = [
        ("OVERVIEW", "📊 Executive Overview"),
        ("DRILLDOWN", "🔍 Category Wise"),
        ("NCR", "⚠️ Client NCR Register"),
        ("CONCRETE", "🏗️ Concrete Placement"),
        ("TRAINING", "🎓 Quality Training & TBT"),
        ("LESSONS", "💡 Lessons Learned"),
        ("MONTHLY", "📅 Monthly Status Report")
    ]
    if user_role == "ADMIN":
        nav_items.append(("ADMIN", "👥 User & Access Audit"))

    for key, label in nav_items:
        b_type = "primary" if st.session_state.current_view == key else "secondary"
        if st.button(label, key=f"side_nav_{key}", use_container_width=True, type=b_type):
            st.session_state.current_view = key
            st.session_state.page_num = 1
            st.rerun()

    st.markdown("---")
    st.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;margin-top:16px;margin-bottom:6px;'>📁 Master Log Sync</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.8rem; color: #64748B; margin-bottom: 8px;'>Place raw Aconex logs in <code>auto_logs/</code> or upload below.</div>", unsafe_allow_html=True)

    if st.button("🔄 Sync Logs from Folder", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.success("Synchronized logs from folder!")
        st.rerun()

    st.markdown("<div style='font-size: 0.8rem; color: #64748B; margin-top: 14px; margin-bottom: 4px;'>Upload Aconex export files:</div>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload Register", accept_multiple_files=True, type=['xlsx', 'xls'], label_visibility="collapsed")
    if uploaded_files:
        new_files_saved = 0
        for uf in uploaded_files:
            file_sig = f"{uf.name}_{uf.size}"
            if file_sig not in st.session_state.saved_upload_names:
                target_path = os.path.join(AUTO_DIR, uf.name)
                with open(target_path, "wb") as f_out:
                    f_out.write(uf.getbuffer())
                st.session_state.saved_upload_names.add(file_sig)
                new_files_saved += 1
        if new_files_saved > 0:
            st.cache_data.clear()
            st.success(f"Saved {new_files_saved} new file(s) to auto_logs/!")

    # Collect all Excel files across auto_logs, logs, and .temp_uploads
    file_metadata = []
    scanned_files = []
    for d in [AUTO_DIR, LOGS_DIR, UPLOAD_DIR]:
        if os.path.exists(d):
            for fn in os.listdir(d):
                if fn.startswith("~$") or fn.startswith("."): continue
                if fn.endswith('.xlsx') or fn.endswith('.xls'):
                    fp = os.path.join(d, fn)
                    if os.path.isfile(fp) and fp not in scanned_files:
                        scanned_files.append(fp)
                        file_metadata.append((fp, fn, os.path.getmtime(fp)))

@st.cache_data(show_spinner=False)
def load_and_cache_data(metadata):
    _files = []
    for path, name, _ in metadata:
        class MockFile:
            def __init__(self, path, name):
                self.path = path
                self.name = name
            def read(self):
                with open(self.path, 'rb') as file: return file.read()
        _files.append(MockFile(path, name))
    return process_uploaded_logs(_files)

with st.spinner("Processing Aconex master registers..."):
    df, calibration_data, concrete_df, is_mock = load_and_cache_data(tuple(file_metadata))

df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
valid_dates = df['Date'].dropna().copy()
if concrete_df is not None and len(concrete_df) > 0:
    concrete_df['Date'] = pd.to_datetime(concrete_df['Date'], errors='coerce')
    valid_dates = pd.concat([valid_dates, concrete_df['Date'].dropna()])

min_date = valid_dates.min().date() if len(valid_dates) > 0 else (datetime.date.today() - datetime.timedelta(days=365))
max_date = valid_dates.max().date() if len(valid_dates) > 0 else datetime.date.today()

if 'start_date' not in st.session_state or st.session_state.start_date is None:
    st.session_state.start_date = min_date
if 'end_date' not in st.session_state or st.session_state.end_date is None:
    st.session_state.end_date = max_date

# Date bounds protection
if st.session_state.start_date < min_date: st.session_state.start_date = min_date
if st.session_state.start_date > max_date: st.session_state.start_date = max_date
if st.session_state.end_date < min_date: st.session_state.end_date = min_date
if st.session_state.end_date > max_date: st.session_state.end_date = max_date

def apply_preset_cumulative():
    st.session_state.start_date = min_date
    st.session_state.end_date = max_date

def apply_preset_30d():
    st.session_state.start_date = max(min_date, max_date - datetime.timedelta(days=30))
    st.session_state.end_date = max_date

def apply_preset_90d():
    st.session_state.start_date = max(min_date, max_date - datetime.timedelta(days=90))
    st.session_state.end_date = max_date

date_filtered_df = filter_data(df, st.session_state.start_date, st.session_state.end_date, "ALL")

# Top Header
date_range_str = f"{st.session_state.start_date.strftime('%d %b %Y')} – {st.session_state.end_date.strftime('%d %b %Y')}"
render_hero_header("Royal Diriyah Opera House", "DII-Jasara", date_range_str)

# ── Professional Interactive Navigation Tab Bar ──────────────────────────────
user_is_admin = (st.session_state.get("user_info", {}).get("role") == "admin")
nav_definitions = [
    ("OVERVIEW",   "📊 Executive Overview"),
    ("DRILLDOWN",  "🔍 Category Wise"),
    ("NCR",        "⚠️ Client NCR Register"),
    ("CONCRETE",   "🏗️ Concrete Placement"),
    ("TRAINING",   "🎓 Quality Training & TBT"),
    ("LESSONS",    "💡 Lessons Learned"),
    ("MONTHLY",    "📅 Monthly Status Report")
]
if user_is_admin:
    nav_definitions.append(("ADMIN", "👥 User & Access Audit"))

nav_cols = st.columns(len(nav_definitions))
for idx, (k, lbl) in enumerate(nav_definitions):
    with nav_cols[idx]:
        is_cur = (st.session_state.current_view == k)
        b_type = "primary" if is_cur else "secondary"
        if st.button(lbl, key=f"top_nav_{k}", type=b_type, use_container_width=True):
            st.session_state.current_view = k
            st.session_state.page_num = 1
            st.rerun()

st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)



# ── Filter Toolbar ────────────────────────────────────────────────────────────
st.markdown("<div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:14px 18px;margin-bottom:16px;box-shadow:0 2px 6px rgba(15,23,42,.04);'>", unsafe_allow_html=True)
fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([1.2, 1.2, 1.0, 1.0, 1.4, 1.4])
with fc1:
    st.date_input("Start Date", key="start_date", min_value=min_date, max_value=max_date)
with fc2:
    st.date_input("End Date", key="end_date", min_value=min_date, max_value=max_date)
with fc3:
    st.write("")
    st.write("")
    st.button("Cumulative", key="btn_cum", on_click=apply_preset_cumulative, use_container_width=True)
with fc4:
    st.write("")
    st.write("")
    st.button("Last 30D", key="btn_30d", on_click=apply_preset_30d, use_container_width=True)
with fc5:
    st.write("")
    st.write("")
    if st.button("📊 Generate PPT", key="btn_gen_ppt", use_container_width=True):
        with st.spinner("Compiling PowerPoint slide deck..."):
            try:
                from ppt_exporter import generate_ppt
                st.session_state.ppt_data = generate_ppt(df, concrete_df, st.session_state.start_date, st.session_state.end_date)
                st.success("Slide deck ready!")
            except Exception as e:
                st.error(f"PPT error: {e}")
with fc6:
    st.write("")
    st.write("")
    if st.session_state.ppt_data is not None:
        st.download_button(
            label="⬇️ Download PPT",
            data=st.session_state.ppt_data,
            file_name=f"Quality_Report_{datetime.date.today()}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
            type="primary"
        )
    else:
        st.button("⬇️ Download PPT", disabled=True, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)  # Close filter card


def get_cat_status_counts(category, target_df):
    df_cat = target_df[target_df['Category'] == category]
    if category == 'NCR':
        success = df_cat[df_cat['Status'] == 'Closed'].shape[0]
        fail = df_cat[df_cat['Status'] == 'Open'].shape[0]
        return success, fail, 0, 0
    else:
        a_app = df_cat[df_cat['Status'] == 'A-Approved'].shape[0]
        b_app = df_cat[df_cat['Status'] == 'B-Approved with Comments'].shape[0]
        c_rev = df_cat[df_cat['Status'] == 'C-Revise and Resubmit'].shape[0]
        d_rej = df_cat[df_cat['Status'] == 'D-Rejected'].shape[0]
        return a_app, b_app, c_rev, d_rej

# -------------------------------------------------------------
# VIEW 1: EXECUTIVE OVERVIEW
# -------------------------------------------------------------
if st.session_state.current_view == "OVERVIEW":
    non_ncr_df = date_filtered_df[date_filtered_df['Category'] != 'NCR']
    ncr_df = date_filtered_df[date_filtered_df['Category'] == 'NCR']
    
    total_submittals = len(date_filtered_df)
    total_approved = len(non_ncr_df[non_ncr_df['Status'].isin(['A-Approved', 'B-Approved with Comments', 'Approved'])])
    overall_approval_rate = (total_approved / len(non_ncr_df) * 100) if len(non_ncr_df) > 0 else 0
    open_ncrs = len(ncr_df[ncr_df['Status'] == 'Open'])
    
    concrete_vol = 0.0
    if concrete_df is not None and len(concrete_df) > 0:
        c_filtered = concrete_df[(pd.to_datetime(concrete_df['Date']).dt.date >= st.session_state.start_date) & (pd.to_datetime(concrete_df['Date']).dt.date <= st.session_state.end_date)]
        if len(c_filtered) > 0:
            concrete_vol = float(c_filtered['Volume'].sum())
            
    render_hero_metric_cards(total_submittals, overall_approval_rate, open_ncrs, concrete_vol)

    section_title("📦 QA/QC KPI's — Category Performance Overview")
    
    categories = [
        ("WIR - Work Inspection Requests", "WIR", False),
        ("MIR - Material Inspection Requests", "MIR", False),
        ("MAR - Material Approval Requests", "MAR", False),
        ("MST - Method Statements", "MST", False),
        ("ITP - Inspection & Test Plans", "ITP", False),
        ("SHD - Shop Drawing Submittals", "SHD", False),
        ("NCR - Non-Conformance Reports", "NCR", True)
    ]
    
    for i in range(0, len(categories), 2):
        col1, col2 = st.columns(2)
        with col1:
            title, cat, is_ncr = categories[i]
            a, b, c, d = get_cat_status_counts(cat, date_filtered_df)
            total = a + b + c + d
            if is_ncr:
                rate = f"{(a / total * 100):.1f}%" if total > 0 else "0.0%"
                render_category_box(title, f"{total:,}", f"{a:,}", f"{b:,}", "", "", rate, is_alt_color=(i % 4 >= 2), is_ncr=True, cat_id=cat)
            else:
                rate = f"{((a + b) / total * 100):.1f}%" if total > 0 else "0.0%"
                render_category_box(title, f"{total:,}", f"{a:,}", f"{b:,}", f"{c:,}", f"{d:,}", rate, is_alt_color=(i % 4 >= 2), is_ncr=False, cat_id=cat)
            
            if st.button(f"🔍 Open {cat} Analysis & Register ➔", key=f"btn_nav_cat_{cat}", use_container_width=True):
                if cat == "NCR":
                    st.session_state.current_view = "NCR"
                else:
                    st.session_state.current_view = "DRILLDOWN"
                    st.session_state.selected_category = cat
                st.session_state.page_num = 1
                st.rerun()

        with col2:
            if i + 1 < len(categories):
                title, cat, is_ncr = categories[i+1]
                a, b, c, d = get_cat_status_counts(cat, date_filtered_df)
                total = a + b + c + d
                if is_ncr:
                    rate = f"{(a / total * 100):.1f}%" if total > 0 else "0.0%"
                    render_category_box(title, f"{total:,}", f"{a:,}", f"{b:,}", "", "", rate, is_alt_color=((i+1) % 4 >= 2), is_ncr=True, cat_id=cat)
                else:
                    rate = f"{((a + b) / total * 100):.1f}%" if total > 0 else "0.0%"
                    render_category_box(title, f"{total:,}", f"{a:,}", f"{b:,}", f"{c:,}", f"{d:,}", rate, is_alt_color=((i+1) % 4 >= 2), is_ncr=False, cat_id=cat)

                if st.button(f"🔍 Open {cat} Analysis & Register ➔", key=f"btn_nav_cat_{cat}", use_container_width=True):
                    if cat == "NCR":
                        st.session_state.current_view = "NCR"
                    else:
                        st.session_state.current_view = "DRILLDOWN"
                        st.session_state.selected_category = cat
                    st.session_state.page_num = 1
                    st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    section_title("📈 Performance Analytics & Proportional Status Distribution")
    
    chart_c1, chart_c2 = st.columns([1.4, 1.0])
    with chart_c1:
        valid_7_cats = ['WIR', 'MIR', 'MAR', 'MST', 'ITP', 'SHD', 'NCR']
        cat_data = date_filtered_df[date_filtered_df['Category'].isin(valid_7_cats)].groupby(['Category', 'Status']).size().reset_index(name='Count')
        if len(cat_data) > 0:
            cat_totals = cat_data.groupby('Category')['Count'].transform('sum')
            cat_data['Percentage'] = (cat_data['Count'] / cat_totals) * 100
            # Order categories logically
            cat_data['Category'] = pd.Categorical(cat_data['Category'], categories=valid_7_cats, ordered=True)
            cat_data = cat_data.sort_values('Category')
            fig_bar = plot_100p_stacked_bar(cat_data, 'Category', 'Percentage', 'Status', "PROPORTIONAL QUALITY STATUS BY CATEGORY", status_color_map, height=350)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No submittal records found for the selected timeframe.")
    with chart_c2:
        overall_status = date_filtered_df['Status'].value_counts().reset_index()
        overall_status.columns = ['Status', 'Count']
        if len(overall_status) > 0:
            colors = [status_color_map.get(s, '#94A3B8') for s in overall_status['Status']]
            fig_donut = plot_donut_chart(overall_status['Status'], overall_status['Count'], "OVERALL STATUS DISTRIBUTION", colors, height=350)
            st.plotly_chart(fig_donut, use_container_width=True)

    # Executive NCR Summary by Zone on First Page
    st.markdown("<hr>", unsafe_allow_html=True)
    section_title("⚠️ Executive NCR Quality Summary by Zone")
    st.markdown("<p style='color: #64748B; font-size: 0.85rem; margin-top: -6px;'>High-level status of non-conformances by project structural zone. For full details and CAPA actions, see the dedicated <a href='?nav=NCR' target='_self' style='color:#2563EB;font-weight:600;'>Client NCR Register</a>.</p>", unsafe_allow_html=True)

    ncr_exec_df = get_ncr_master_data(df)
    if len(ncr_exec_df) > 0:
        exec_zone_sum = ncr_exec_df.groupby('Zone').agg(
            Total_NCR=('Document No', 'count'),
            Open_NCR=('Status', lambda s: (s == 'Open').sum()),
            Closed_NCR=('Status', lambda s: (s == 'Closed').sum()),
            Overdue_NCR=('Aging Category', lambda a: (a == 'Overdue (> 2 Months)').sum())
        ).reset_index()
        exec_zone_sum['Resolution Rate'] = (exec_zone_sum['Closed_NCR'] / exec_zone_sum['Total_NCR'] * 100).round(1)
        exec_zone_sum = exec_zone_sum.sort_values(by=['Open_NCR', 'Total_NCR'], ascending=[False, False])
        
        # Display side-by-side: table and mini bar chart
        ncr_sc1, ncr_sc2 = st.columns([1.35, 1.0])
        with ncr_sc1:
            st.dataframe(
                exec_zone_sum,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Zone": st.column_config.TextColumn("Structural Zone", width="medium"),
                    "Total_NCR": st.column_config.NumberColumn("Total Raised", format="%d"),
                    "Open_NCR": st.column_config.NumberColumn("Active Open", format="%d"),
                    "Closed_NCR": st.column_config.NumberColumn("Closed / Verified", format="%d"),
                    "Overdue_NCR": st.column_config.NumberColumn("Overdue (>60d)", format="%d"),
                    "Resolution Rate": st.column_config.ProgressColumn("Resolution Rate", min_value=0, max_value=100, format="%.1f%%")
                }
            )
        with ncr_sc2:
            exec_zone_status = ncr_exec_df.groupby(['Zone', 'Status']).size().reset_index(name='Count')
            color_map = {'Open': '#EF4444', 'Closed': '#10B981'}
            fig_exec_ncr = plot_grouped_bar_chart(exec_zone_status, 'Zone', 'Count', 'Status', "NCRs BY ZONE (OPEN VS CLOSED)", color_map, height=310)
            st.plotly_chart(fig_exec_ncr, use_container_width=True)


# -------------------------------------------------------------
# VIEW 2: CATEGORY WISE (WITH INTERACTIVE POPUPS & CLEAN REGISTERS)
# -------------------------------------------------------------
elif st.session_state.current_view == "DRILLDOWN":
    section_title("🔍 Category Wise Inspection & Submittal Analysis")
    st.markdown("<p style='color:#64748B;font-size:0.85rem;margin:-8px 0 18px 0;'>Detailed breakdown by QA/QC category with status analysis, discipline distribution, and master document registers.</p>", unsafe_allow_html=True)
    
    cat_options = ["WIR", "MIR", "MAR", "MST", "ITP", "SHD", "NCR"]
    top_c1, top_c2 = st.columns([3, 1])
    with top_c1:
        selected_cat = st.selectbox("Select QA/QC Category to Inspect", cat_options, index=cat_options.index(st.session_state.selected_category) if st.session_state.selected_category in cat_options else 0)
        st.session_state.selected_category = selected_cat
    with top_c2:
        st.write("")
        st.write("")
        if st.button("⬅️ Return to Overview", use_container_width=True):
            st.session_state.current_view = "OVERVIEW"
            st.rerun()

    cat = st.session_state.selected_category
    cat_df = date_filtered_df[date_filtered_df['Category'] == cat]
    a, b, c, d = get_cat_status_counts(cat, date_filtered_df)
    total = a + b + c + d
    rate = f"{(a / total * 100):.1f}%" if cat == 'NCR' and total > 0 else f"{((a + b) / total * 100):.1f}%" if total > 0 else "0.0%"

    st.markdown(f"<div style='font-size: 0.85rem; color: #64748B; margin-bottom: 8px;'>💡 <em>Click any metric card below to pop out the filtered list and download the data:</em></div>", unsafe_allow_html=True)

    # Render Interactive Cards with Popup Buttons
    if cat == 'NCR':
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        with col_k1:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #2563EB;"><div class="detail-kpi-title">TOTAL NCRS</div><div class="detail-kpi-value" style="color: #2563EB;">{total:,}</div><div class="detail-kpi-sub">All submissions</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View All Total", key="btn_popup_tot", use_container_width=True):
                show_status_popup(cat, "Total Records", cat_df)
        with col_k2:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #EF4444;"><div class="detail-kpi-title">OPEN (ACTIVE)</div><div class="detail-kpi-value" style="color: #EF4444;">{d:,}</div><div class="detail-kpi-sub">Requires action</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View Open NCRs", key="btn_popup_open", use_container_width=True):
                show_status_popup(cat, "Open Issues", cat_df[cat_df['Status'] == 'Open'])
        with col_k3:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #10B981;"><div class="detail-kpi-title">CLOSED</div><div class="detail-kpi-value" style="color: #10B981;">{(a+b):,}</div><div class="detail-kpi-sub">Verified & Closed</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View Closed", key="btn_popup_closed", use_container_width=True):
                show_status_popup(cat, "Closed & Verified", cat_df[cat_df['Status'] == 'Closed'])
        with col_k4:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #6366F1;"><div class="detail-kpi-title">CLOSURE RATE</div><div class="detail-kpi-value" style="color: #6366F1;">{rate}</div><div class="detail-kpi-sub">Resolution index</div></div>', unsafe_allow_html=True)
            st.button("📊 Closure Index", key="btn_popup_rate", use_container_width=True, disabled=True)
    else:
        col_k1, col_k2, col_k3, col_k4, col_k5, col_k6 = st.columns(6)
        with col_k1:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #2563EB;"><div class="detail-kpi-title">TOTAL {cat}</div><div class="detail-kpi-value" style="color: #2563EB;">{total:,}</div><div class="detail-kpi-sub">All submittals</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View All", key="btn_popup_tot", use_container_width=True):
                show_status_popup(cat, "Total Submissions", cat_df)
        with col_k2:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #10B981;"><div class="detail-kpi-title">CODE A (PASS)</div><div class="detail-kpi-value" style="color: #10B981;">{a:,}</div><div class="detail-kpi-sub">Approved clean</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View Code A", key="btn_popup_a", use_container_width=True):
                show_status_popup(cat, "Code A (Approved)", cat_df[cat_df['Status'] == 'A-Approved'])
        with col_k3:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #0EA5E9;"><div class="detail-kpi-title">CODE B (CMT)</div><div class="detail-kpi-value" style="color: #0EA5E9;">{b:,}</div><div class="detail-kpi-sub">App w/ notes</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View Code B", key="btn_popup_b", use_container_width=True):
                show_status_popup(cat, "Code B (Approved with Comments)", cat_df[cat_df['Status'] == 'B-Approved with Comments'])
        with col_k4:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #F59E0B;"><div class="detail-kpi-title">CODE C (REVISE)</div><div class="detail-kpi-value" style="color: #F59E0B;">{c:,}</div><div class="detail-kpi-sub">Revise & resubmit</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View Code C", key="btn_popup_c", use_container_width=True):
                show_status_popup(cat, "Code C (Revise and Resubmit)", cat_df[cat_df['Status'] == 'C-Revise and Resubmit'])
        with col_k5:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #EF4444;"><div class="detail-kpi-title">CODE D (REJECT)</div><div class="detail-kpi-value" style="color: #EF4444;">{d:,}</div><div class="detail-kpi-sub">Rejected</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View Code D", key="btn_popup_d", use_container_width=True):
                show_status_popup(cat, "Code D (Rejected)", cat_df[cat_df['Status'] == 'D-Rejected'])
        with col_k6:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #6366F1;"><div class="detail-kpi-title">COMPLIANCE</div><div class="detail-kpi-value" style="color: #6366F1;">{rate}</div><div class="detail-kpi-sub">A+B Pass Rate</div></div>', unsafe_allow_html=True)
            if st.button("🔍 View (A+B)", key="btn_popup_ab", use_container_width=True):
                show_status_popup(cat, "Approved Submissions (Code A + B)", cat_df[cat_df['Status'].isin(['A-Approved', 'B-Approved with Comments'])])

    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

    if len(cat_df) > 0:
        disc_status = cat_df.groupby(['Discipline', 'Status']).size().reset_index(name='Count')
        disc_totals = disc_status.groupby('Discipline')['Count'].transform('sum')
        disc_status['Percentage'] = (disc_status['Count'] / disc_totals) * 100
        fig_detail = plot_100p_stacked_bar(disc_status, 'Discipline', 'Percentage', 'Status', f"{cat} PROPORTIONAL STATUS BY ENGINEERING DISCIPLINE", status_color_map, height=340)
        st.plotly_chart(fig_detail, use_container_width=True)

        if cat == 'NCR':
            ncr_r1c1, ncr_r1c2 = st.columns(2)
            with ncr_r1c1:
                root_counts = cat_df['Root Cause'].value_counts().reset_index()
                root_counts.columns = ['Root Cause', 'Count']
                root_counts = root_counts.sort_values(by='Count', ascending=False)
                root_counts['Cumulative %'] = (root_counts['Count'].cumsum() / root_counts['Count'].sum()) * 100
                fig_pareto = plot_pareto_chart(root_counts, 'Root Cause', 'Count', 'Cumulative %', "PARETO ROOT CAUSE BREAKDOWN (80/20 RULE)")
                st.plotly_chart(fig_pareto, use_container_width=True)

            with ncr_r1c2:
                open_ncrs = cat_df[cat_df['Status'] == 'Open'].copy()
                if len(open_ncrs) > 0:
                    today_date = pd.Timestamp(datetime.date.today())
                    open_ncrs['Days Open'] = (today_date - pd.to_datetime(open_ncrs['Date'])).dt.days
                    def bucketize(days):
                        if days < 7: return '<7 days'
                        if days <= 14: return '8-14 days'
                        if days <= 30: return '15-30 days'
                        return '>30 days (Critical)'
                    open_ncrs['Aging Bucket'] = open_ncrs['Days Open'].apply(bucketize)
                    bucket_counts = open_ncrs['Aging Bucket'].value_counts().reset_index()
                    bucket_counts.columns = ['Aging Bucket', 'Count']
                    bucket_order = ['<7 days', '8-14 days', '15-30 days', '>30 days (Critical)']
                    bucket_counts['Aging Bucket'] = pd.Categorical(bucket_counts['Aging Bucket'], categories=bucket_order, ordered=True)
                    bucket_counts = bucket_counts.sort_values('Aging Bucket')
                    fig_aging = plot_bar_chart(bucket_counts, 'Aging Bucket', 'Count', "OPEN NCR AGING BUCKETS", color='#EF4444', height=350)
                    st.plotly_chart(fig_aging, use_container_width=True)
                else:
                    st.info("No open NCRs to calculate aging distribution.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"#### 📑 Detailed {cat} Document Register")
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        search_query = st.text_input("🔍 Search Reference No., Subject or Area", "")
    with sc2:
        st.write("")
        st.write("")
        csv = cat_df.to_csv(index=False).encode('utf-8')
        st.download_button(label=f"⬇️ Export {cat} CSV", data=csv, file_name=f"{cat}_Data_{st.session_state.start_date}_to_{st.session_state.end_date}.csv", mime="text/csv", use_container_width=True)

    # Standard clean display columns: exclude messy Unnamed / foreign headers
    clean_preferred = ['Reference No', 'Description', 'Status', 'Date', 'Area', 'Discipline', 'Contractor', 'Revision']
    table_cols = [c for c in clean_preferred if c in cat_df.columns]
    if not table_cols:
        table_cols = [c for c in cat_df.columns if not str(c).startswith('Unnamed') and 'Learning Event' not in str(c) and 'Training' not in str(c)]
    
    display_df = cat_df[table_cols].copy()
    if search_query:
        ref_col = 'Reference No' if 'Reference No' in display_df.columns else display_df.columns[0]
        desc_col = 'Description' if 'Description' in display_df.columns else (display_df.columns[1] if len(display_df.columns) > 1 else ref_col)
        display_df = display_df[display_df[ref_col].astype(str).str.contains(search_query, case=False, na=False) | display_df[desc_col].astype(str).str.contains(search_query, case=False, na=False)]

    items_per_page = 12
    total_items = len(display_df)
    total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
    if st.session_state.page_num > total_pages:
        st.session_state.page_num = total_pages
    start_idx = (st.session_state.page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    st.dataframe(display_df.iloc[start_idx:end_idx], use_container_width=True, hide_index=True)

    pc1, pc2, pc3 = st.columns([1, 2, 1])
    with pc1:
        if st.button("⬅️ Previous", disabled=(st.session_state.page_num <= 1)):
            st.session_state.page_num -= 1
            st.rerun()
    with pc2:
        st.markdown(f"<div style='text-align:center; color:#64748B; padding-top:8px;'>Page <strong>{st.session_state.page_num}</strong> of {total_pages} &nbsp;(Total: {total_items:,} items)</div>", unsafe_allow_html=True)
    with pc3:
        if st.button("Next ➡️", disabled=(st.session_state.page_num >= total_pages)):
            st.session_state.page_num += 1
            st.rerun()

# -------------------------------------------------------------
# VIEW 3: DEDICATED NCR MANAGEMENT PAGE
# -------------------------------------------------------------
elif st.session_state.current_view == "NCR":
    section_title("⚠️ Non-Conformance Reports (NCR) Executive Center")
    st.markdown("<p style='color:#64748B;font-size:0.85rem;margin:-8px 0 18px 0;'>Live synchronization across open NCR tracker slides and cumulative Aconex master registers.</p>", unsafe_allow_html=True)

    # Reconcile NCR master data
    ncr_master = get_ncr_master_data(df)

    # Key Metrics
    tot_ncrs = len(ncr_master)
    overdue_ncrs = ncr_master[ncr_master['Aging Category'] == 'Overdue (> 2 Months)']
    active_ncrs = ncr_master[ncr_master['Aging Category'] == 'Active (< 2 Months)']
    closed_ncrs = ncr_master[ncr_master['Status'] == 'Closed']
    
    overdue_count = len(overdue_ncrs)
    active_count = len(active_ncrs)
    closed_count = len(closed_ncrs)
    open_total = overdue_count + active_count
    closure_rate = (closed_count / tot_ncrs * 100) if tot_ncrs > 0 else 0

    # Metric KPI Row
    nk1, nk2, nk3, nk4, nk5 = st.columns(5)
    with nk1:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #2563EB;"><div class="detail-kpi-title">TOTAL NCRs RAISED</div><div class="detail-kpi-value" style="color: #2563EB;">{tot_ncrs:,}</div><div class="detail-kpi-sub">Cumulative Master Log</div></div>', unsafe_allow_html=True)
    with nk2:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #EF4444;"><div class="detail-kpi-title">OVERDUE (> 2 MONTHS)</div><div class="detail-kpi-value" style="color: #EF4444;">{overdue_count:,}</div><div class="detail-kpi-sub">Age: 60+ days pending</div></div>', unsafe_allow_html=True)
    with nk3:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #F59E0B;"><div class="detail-kpi-title">ACTIVE (< 2 MONTHS)</div><div class="detail-kpi-value" style="color: #F59E0B;">{active_count:,}</div><div class="detail-kpi-sub">Age: under 60 days</div></div>', unsafe_allow_html=True)
    with nk4:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #10B981;"><div class="detail-kpi-title">CLOSED / VERIFIED</div><div class="detail-kpi-value" style="color: #10B981;">{closed_count:,}</div><div class="detail-kpi-sub">Consultant verified</div></div>', unsafe_allow_html=True)
    with nk5:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #6366F1;"><div class="detail-kpi-title">CLOSURE KPI</div><div class="detail-kpi-value" style="color: #6366F1;">{closure_rate:.1f}%</div><div class="detail-kpi-sub">Target: > 90%</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

    def render_ncr_table_with_export(target_df, title_prefix, default_export_name):
        fcol1, fcol2, fcol3, fcol4 = st.columns([1.8, 1.1, 1.1, 1.1])
        with fcol1:
            q = st.text_input(f"🔍 Search {title_prefix}", key=f"q_{default_export_name}", placeholder="Filter Ref No, Description, CAPA, Status...")
        with fcol2:
            origins = ["ALL Origins"] + sorted(list(target_df['Origin'].unique()))
            sel_origin = st.selectbox("Origin", origins, key=f"org_{default_export_name}")
        with fcol3:
            zones_list = ["ALL Zones"] + sorted(list(target_df['Zone'].unique())) if 'Zone' in target_df.columns else ["ALL Zones"]
            sel_zone = st.selectbox("Zone", zones_list, key=f"zne_{default_export_name}")
        with fcol4:
            st.write("")
            st.write("")
            csv_data = target_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"⬇️ CSV ({len(target_df):,})",
                data=csv_data,
                file_name=f"{default_export_name}_{datetime.date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )

        df_disp = target_df.copy()
        if sel_origin != "ALL Origins":
            df_disp = df_disp[df_disp['Origin'] == sel_origin]
        if 'Zone' in df_disp.columns and sel_zone != "ALL Zones":
            df_disp = df_disp[df_disp['Zone'] == sel_zone]
        if q:
            df_disp = df_disp[
                df_disp['Document No'].str.contains(q, case=False, na=False) |
                df_disp['Description'].str.contains(q, case=False, na=False) |
                df_disp['Corrective Action'].str.contains(q, case=False, na=False) |
                df_disp['Current Status'].str.contains(q, case=False, na=False)
            ]

        # Order columns to strictly follow the PPT format with Zone intelligence
        ppt_display_cols = [
            'Document No', 'Zone', 'Discipline', 'Description', 'Corrective Action', 
            'Issue Date', 'Days Open', 'Current Status', 'Origin'
        ]
        cols_present = [c for c in ppt_display_cols if c in df_disp.columns]
        
        st.dataframe(
            df_disp[cols_present],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Document No": st.column_config.TextColumn("NCR Document No.", width="medium"),
                "Zone": st.column_config.TextColumn("Zone / Area", width="small"),
                "Description": st.column_config.TextColumn("NCR Description", width="large"),
                "Corrective Action": st.column_config.TextColumn("Corrective Action (CAPA)", width="large"),
                "Issue Date": st.column_config.DateColumn("Issue Date", format="YYYY-MM-DD"),
                "Days Open": st.column_config.NumberColumn("Days Passed", format="%d d"),
                "Current Status": st.column_config.TextColumn("Current Status / Remarks", width="medium"),
                "Origin": st.column_config.TextColumn("Origin", width="small")
            }
        )

    # Sub-tabs with Zone Analytics Dashboard and PPT-aligned views
    tab_zone, tab_overdue, tab_active, tab_closed, tab_master = st.tabs([
        "🗺️ NCR Zone Analytics Dashboard",
        f"🚨 Overdue NCRs (> 2 Months) [{overdue_count}]",
        f"⏳ Active Open NCRs (< 2 Months) [{active_count}]",
        f"✅ Closed NCRs [{closed_count}]",
        f"📋 Full Cumulative Master Register [{tot_ncrs}]"
    ])

    # ── TAB: ZONE ANALYTICS DASHBOARD ─────────────────────────
    with tab_zone:
        st.markdown("##### 🗺️ Geographic & Zone-Wise Quality Conformance Analytics")
        st.markdown("<p style='color: #64748B; font-size: 0.82rem; margin-top: -6px;'>Identify location hotspots, pending corrective actions, and closure rates by Opera House structural zone.</p>", unsafe_allow_html=True)
        
        # Zone overview summary cards
        zone_summary = ncr_master.groupby('Zone').agg(
            Total_NCR=('Document No', 'count'),
            Open_NCR=('Status', lambda s: (s == 'Open').sum()),
            Closed_NCR=('Status', lambda s: (s == 'Closed').sum()),
            Overdue_NCR=('Aging Category', lambda a: (a == 'Overdue (> 2 Months)').sum())
        ).reset_index()
        
        zone_summary['Closure_Rate'] = (zone_summary['Closed_NCR'] / zone_summary['Total_NCR'] * 100).round(1)
        zone_summary = zone_summary.sort_values(by=['Open_NCR', 'Total_NCR'], ascending=[False, False])
        
        # Primary Zone Matrix Table: Rows = Zones, Columns = Total NCR, Open, Closed
        st.markdown("###### 📊 Structural Zone Non-Conformance Summary Matrix")
        st.dataframe(
            zone_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Zone": st.column_config.TextColumn("Zone / Area (Row)", width="medium"),
                "Total_NCR": st.column_config.NumberColumn("Total NCR", format="%d", help="Total non-conformances logged for this zone"),
                "Open_NCR": st.column_config.NumberColumn("Open NCR", format="%d", help="Active non-conformances pending rectification"),
                "Closed_NCR": st.column_config.NumberColumn("Closed NCR", format="%d", help="Resolved non-conformances verified by consultant"),
                "Overdue_NCR": st.column_config.NumberColumn("Overdue (>60d)", format="%d", help="NCRs open more than 60 days"),
                "Closure_Rate": st.column_config.ProgressColumn("Closure Rate", min_value=0, max_value=100, format="%.1f%%")
            }
        )
        
        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

        st.markdown("##### 📍 Interactive Zone Inspector & Breakdown Table")
        
        selected_zone_filter = st.selectbox(
            "Filter NCR Details by Zone:",
            ["All Zones"] + sorted(list(ncr_master['Zone'].unique())),
            key="ncr_zone_inspect_filter"
        )
        
        filtered_zone_ncr = ncr_master.copy()
        if selected_zone_filter != "All Zones":
            filtered_zone_ncr = filtered_zone_ncr[filtered_zone_ncr['Zone'] == selected_zone_filter]
            
        z_k1, z_k2, z_k3, z_k4 = st.columns(4)
        with z_k1:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #2563EB;"><div class="detail-kpi-title">TOTAL IN {selected_zone_filter.upper()}</div><div class="detail-kpi-value" style="color: #2563EB;">{len(filtered_zone_ncr):,}</div><div class="detail-kpi-sub">Total Submittals</div></div>', unsafe_allow_html=True)
        with z_k2:
            z_open = len(filtered_zone_ncr[filtered_zone_ncr['Status'] == 'Open'])
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #EF4444;"><div class="detail-kpi-title">ACTIVE OPEN</div><div class="detail-kpi-value" style="color: #EF4444;">{z_open:,}</div><div class="detail-kpi-sub">Pending Rectification</div></div>', unsafe_allow_html=True)
        with z_k3:
            z_closed = len(filtered_zone_ncr[filtered_zone_ncr['Status'] == 'Closed'])
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #10B981;"><div class="detail-kpi-title">CLOSED & RESOLVED</div><div class="detail-kpi-value" style="color: #10B981;">{z_closed:,}</div><div class="detail-kpi-sub">Consultant Verified</div></div>', unsafe_allow_html=True)
        with z_k4:
            z_rate = (z_closed / len(filtered_zone_ncr) * 100) if len(filtered_zone_ncr) > 0 else 0
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #6366F1;"><div class="detail-kpi-title">ZONE RESOLUTION RATE</div><div class="detail-kpi-value" style="color: #6366F1;">{z_rate:.1f}%</div><div class="detail-kpi-sub">Target: > 90%</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        render_ncr_table_with_export(filtered_zone_ncr, f"NCRs for {selected_zone_filter}", f"NCR_{selected_zone_filter.replace(' ', '_')}")

    with tab_overdue:
        st.markdown("##### 🚨 Critical Action Items: Non-Conformances Open More Than 60 Days")
        st.markdown("<p style='color: #991B1B; font-size: 0.8rem; margin-top: -6px;'>These non-conformances have exceeded the 2-month threshold and require high-priority closeout meetings.</p>", unsafe_allow_html=True)
        render_ncr_table_with_export(overdue_ncrs, "Overdue NCRs", "Overdue_NCRs_Report")

    with tab_active:
        st.markdown("##### ⏳ Active Non-Conformances Under Resolution (< 2 Months)")
        st.markdown("<p style='color: #475569; font-size: 0.8rem; margin-top: -6px;'>Items undergoing active corrective action plan implementation, repair mock-ups, or consultant WIR verification.</p>", unsafe_allow_html=True)
        render_ncr_table_with_export(active_ncrs, "Active NCRs", "Active_NCRs_Report")

    with tab_closed:
        st.markdown("##### ✅ Successfully Resolved & Closed NCRs")
        st.markdown("<p style='color: #065F46; font-size: 0.8rem; margin-top: -6px;'>Completed non-conformances with approved closeout signatures and consultant concurrence.</p>", unsafe_allow_html=True)
        render_ncr_table_with_export(closed_ncrs, "Closed NCRs", "Closed_NCRs_Report")

    with tab_master:
        st.markdown("##### 📋 Complete Client Quality NCR Cumulative Register")
        st.markdown("<p style='color: #475569; font-size: 0.8rem; margin-top: -6px;'>Complete register of Client / Consultant (BV-BSW-105-0000-SOA-NCR-QL) non-conformances synchronized from master logs and slide updates.</p>", unsafe_allow_html=True)
        render_ncr_table_with_export(ncr_master, "All NCRs", "Client_NCR_Master_Register")

# -------------------------------------------------------------
# VIEW: DEDICATED CONCRETE PLACEMENT & DEFECTS PAGE
# -------------------------------------------------------------
elif st.session_state.current_view == "CONCRETE":
    section_title("🏗️ Structural Concrete Placement & Quality Control Center")
    st.markdown("<p style='color:#64748B;font-size:0.85rem;margin:-8px 0 18px 0;'>Production volumes, pouring progression by element and zone, and post-pour defect resolution logs.</p>", unsafe_allow_html=True)

    if concrete_df is not None and len(concrete_df) > 0:
        c_df = concrete_df[(pd.to_datetime(concrete_df['Date']).dt.date >= st.session_state.start_date) & (pd.to_datetime(concrete_df['Date']).dt.date <= st.session_state.end_date)].copy()
        total_poured = c_df['Volume'].sum() if len(c_df) > 0 else 0
        pours_count = len(c_df)
        avg_pour = total_poured / pours_count if pours_count > 0 else 0
        unique_zones = c_df['Zone'].nunique() if len(c_df) > 0 else 0

        # KPI metric cards row
        ck1, ck2, ck3, ck4 = st.columns(4)
        with ck1:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #0D9488;"><div class="detail-kpi-title">TOTAL VOLUME CAST</div><div class="detail-kpi-value" style="color: #0F766E;">{total_poured:,.1f} <span style="font-size:1rem;">m³</span></div><div class="detail-kpi-sub">Filtered timeframe volume</div></div>', unsafe_allow_html=True)
        with ck2:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #2563EB;"><div class="detail-kpi-title">TOTAL POURS LOGGED</div><div class="detail-kpi-value" style="color: #2563EB;">{pours_count:,}</div><div class="detail-kpi-sub">Authorized pour records</div></div>', unsafe_allow_html=True)
        with ck3:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #F59E0B;"><div class="detail-kpi-title">AVG VOLUME PER POUR</div><div class="detail-kpi-value" style="color: #D97706;">{avg_pour:.1f} <span style="font-size:1rem;">m³</span></div><div class="detail-kpi-sub">Mean batch size</div></div>', unsafe_allow_html=True)
        with ck4:
            st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #6366F1;"><div class="detail-kpi-title">ACTIVE POUR ZONES</div><div class="detail-kpi-value" style="color: #6366F1;">{unique_zones}</div><div class="detail-kpi-sub">Distinct structural zones</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

        tab_conc_analytics, tab_conc_log, tab_post_pour = st.tabs([
            "📊 Concrete Volume & Element Analytics",
            f"📋 Daily Pouring Register [{pours_count}]",
            "🔍 Post-Pour Inspection & Defect Tracker"
        ])

        with tab_conc_analytics:
            if len(c_df) > 0:
                c_df['Month'] = pd.to_datetime(c_df['Date']).dt.strftime('%b %Y')
                c_df['Month_Sort'] = pd.to_datetime(c_df['Date']).dt.to_period('M')
                conc_c1, conc_c2 = st.columns(2)
                color_map = {'Columns': '#1E3A8A', 'Walls': '#2563EB', 'Slab': '#60A5FA'}
                with conc_c1:
                    zone_el = c_df.groupby(['Zone', 'Element'])['Volume'].sum().reset_index()
                    fig_c1 = plot_grouped_bar_chart(zone_el, 'Zone', 'Volume', 'Element', "CONCRETE PLACEMENT BY ZONE & ELEMENT (m³)", color_map, height=360)
                    st.plotly_chart(fig_c1, use_container_width=True)
                with conc_c2:
                    month_el = c_df.groupby(['Month_Sort', 'Month', 'Element'])['Volume'].sum().reset_index()
                    month_el = month_el.sort_values('Month_Sort')
                    fig_c2 = plot_grouped_bar_chart(month_el, 'Month', 'Volume', 'Element', "MONTHLY POURING PROGRESSION (m³)", color_map, height=360)
                    st.plotly_chart(fig_c2, use_container_width=True)

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                st.markdown("###### 📊 Structural Zone Concrete Production Summary")
                zone_conc_sum = c_df.groupby('Zone').agg(
                    Total_Volume=('Volume', 'sum'),
                    Pour_Count=('Volume', 'count'),
                    Avg_Pour=('Volume', 'mean')
                ).reset_index().sort_values(by='Total_Volume', ascending=False)
                zone_conc_sum['Total_Volume'] = zone_conc_sum['Total_Volume'].round(1)
                zone_conc_sum['Avg_Pour'] = zone_conc_sum['Avg_Pour'].round(1)
                st.dataframe(
                    zone_conc_sum,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Zone": st.column_config.TextColumn("Structural Zone", width="medium"),
                        "Total_Volume": st.column_config.NumberColumn("Total Volume (m³)", format="%.1f m³"),
                        "Pour_Count": st.column_config.NumberColumn("Pour Events", format="%d"),
                        "Avg_Pour": st.column_config.NumberColumn("Avg per Pour", format="%.1f m³")
                    }
                )
            else:
                st.info("No concrete pour logs found for the selected date range.")

        with tab_conc_log:
            st.markdown("###### 📋 Daily Concrete Pouring Register")
            cq1, cq2 = st.columns([3, 1])
            with cq1:
                cq_text = st.text_input("🔍 Filter concrete pours", placeholder="Filter by Zone, Element, Date...")
            with cq2:
                st.write("")
                st.write("")
                csv_conc = c_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Concrete CSV", data=csv_conc, file_name=f"Concrete_Log_{datetime.date.today()}.csv", mime="text/csv", use_container_width=True)

            c_display = c_df.copy()
            if cq_text:
                c_display = c_display[
                    c_display['Zone'].astype(str).str.contains(cq_text, case=False, na=False) |
                    c_display['Element'].astype(str).str.contains(cq_text, case=False, na=False) |
                    c_display['Date'].astype(str).str.contains(cq_text, case=False, na=False)
                ]
            st.dataframe(c_display, use_container_width=True, hide_index=True)

        with tab_post_pour:
            st.markdown("###### 🔍 Post-Pour Structural Inspection & Repair Tracking")
            post_pour_df = get_post_pour_data()
            if len(post_pour_df) > 0:
                ppc1, ppc2 = st.columns([1.4, 1.0])
                with ppc1:
                    fig_post_pour = plot_post_pour_status(post_pour_df, height=340)
                    st.plotly_chart(fig_post_pour, use_container_width=True)
                with ppc2:
                    st.markdown("###### Post-Pour Status Summary")
                    pp_sum = post_pour_df.groupby('Status').size().reset_index(name='Count')
                    st.dataframe(pp_sum, use_container_width=True, hide_index=True)
                st.dataframe(post_pour_df, use_container_width=True, hide_index=True)
            else:
                st.info("No post-pour defects logged.")
    else:
        st.info("No structural concrete placement data available in current logs.")

# -------------------------------------------------------------
# VIEW 4: QUALITY TRAINING & TOOLBOX TALKS (TBT)
# -------------------------------------------------------------
elif st.session_state.current_view == "TRAINING":
    section_title("🎓 ECM JV Quality Training & Toolbox Talks (TBT) Register")
    st.markdown("<p style='color:#64748B;font-size:0.85rem;margin:-8px 0 18px 0;'>Annual Training Schedule & Competency Tracking for Royal Diriyah Opera House (CSC & Contractor).</p>", unsafe_allow_html=True)

    df_qms, df_func = get_training_data()
    total_qms = len(df_qms)
    total_func = len(df_func)
    total_sessions = total_qms + total_func

    # Upcoming scheduled count
    upcoming_qms = len(df_qms[df_qms['Schedule Status'] == 'Upcoming Scheduled']) if 'Schedule Status' in df_qms.columns else 0
    upcoming_func = len(df_func[df_func['Schedule Status'] == 'Upcoming Scheduled']) if 'Schedule Status' in df_func.columns else 0
    total_upcoming = upcoming_qms + upcoming_func

    # Summary KPIs
    tk1, tk2, tk3, tk4 = st.columns(4)
    with tk1:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #2563EB;"><div class="detail-kpi-title">TOTAL SESSIONS LOGGED</div><div class="detail-kpi-value" style="color: #2563EB;">{total_sessions:,}</div><div class="detail-kpi-sub">QMS + Site Functional TBTs</div></div>', unsafe_allow_html=True)
    with tk2:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #F59E0B;"><div class="detail-kpi-title">UPCOMING SCHEDULED SESSIONS</div><div class="detail-kpi-value" style="color: #D97706;">{total_upcoming:,}</div><div class="detail-kpi-sub">Next scheduled dates identified</div></div>', unsafe_allow_html=True)
    with tk3:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #10B981;"><div class="detail-kpi-title">QMS FORMAL TRAININGS</div><div class="detail-kpi-value" style="color: #10B981;">{total_qms:,}</div><div class="detail-kpi-sub">Inductions & Quality Audits</div></div>', unsafe_allow_html=True)
    with tk4:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #6366F1;"><div class="detail-kpi-title">FUNCTIONAL & TBT SESSIONS</div><div class="detail-kpi-value" style="color: #6366F1;">{total_func:,}</div><div class="detail-kpi-sub">Tradesmen & Site Supervisors</div></div>', unsafe_allow_html=True)

    # Next Schedule Spotlight Banner
    combined_train = pd.concat([df_qms, df_func], ignore_index=True) if len(df_qms) > 0 or len(df_func) > 0 else pd.DataFrame()
    if len(combined_train) > 0 and 'Schedule Status' in combined_train.columns:
        upcoming_items = combined_train[combined_train['Schedule Status'] == 'Upcoming Scheduled']
        if len(upcoming_items) > 0:
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            banner_html = f"""
            <div style="background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%); border: 1.5px solid #FCD34D; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.08);">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.4rem;">📅</span>
                        <div>
                            <div style="font-size: 0.95rem; font-weight: 800; color: #92400E;">UPCOMING TRAINING SCHEDULE SPOTLIGHT ({len(upcoming_items)} Sessions Scheduled)</div>
                            <div style="font-size: 0.8rem; color: #B45309;">Track next planned delivery dates and ensure site readiness before execution.</div>
                        </div>
                    </div>
                    <span style="font-size: 0.75rem; font-weight: 700; background: #92400E; color: #FFFFFF; padding: 4px 12px; border-radius: 9999px;">2026 Annual Master Calendar</span>
                </div>
            </div>
            """
            st.markdown(banner_html, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    tab_func, tab_qms = st.tabs([
        f"🛠️ Functional & Site TBT Topics [{total_func}]",
        f"📋 QMS Core Procedures & Inductions [{total_qms}]"
    ])

    with tab_func:
        st.markdown("##### 🛠️ Site Functional Trainings & Trade Toolbox Talks")
        st.markdown("<p style='color: #64748B; font-size: 0.8rem; margin-top: -6px;'>Hands-on technical workshops covering waterproofing, rebar mechanical couplers, post-installed chemical anchors, SF3 architectural finish, and formwork safety.</p>", unsafe_allow_html=True)
        if len(df_func) > 0:
            tc1, tc2, tc3 = st.columns([2.5, 1.2, 1.3])
            with tc1:
                q_func = st.text_input("🔍 Search Functional Training Topics", key="q_func_train", placeholder="e.g. Coupler, SF3, Water Stop, MEP, Concrete...")
            with tc2:
                status_filter_f = st.selectbox("Schedule Filter", ["All Sessions", "Upcoming Scheduled Only", "Fully Completed Only"], key="filter_status_f")
            with tc3:
                st.write("")
                st.write("")
                st.download_button(
                    label=f"⬇️ Download CSV ({len(df_func)} items)",
                    data=df_func.to_csv(index=False).encode('utf-8'),
                    file_name=f"Functional_Training_Schedule_{datetime.date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            disp_f = df_func.copy()
            if q_func:
                disp_f = disp_f[disp_f['Topic / Target Group'].str.contains(q_func, case=False, na=False)]
            if status_filter_f == "Upcoming Scheduled Only":
                disp_f = disp_f[disp_f['Schedule Status'] == 'Upcoming Scheduled']
            elif status_filter_f == "Fully Completed Only":
                disp_f = disp_f[disp_f['Schedule Status'] == 'Fully Completed']

            # Column ordering with Next Schedule front and center
            cols_order = [c for c in ['S.N.', 'Topic / Target Group', 'Next Schedule', 'Schedule Status', 'Total Staff', 'Total Plan', 'Total Conducted', '% Conducted'] if c in disp_f.columns]
            st.dataframe(disp_f[cols_order], use_container_width=True, hide_index=True)
        else:
            st.info("Functional training schedule log not found.")

    with tab_qms:
        st.markdown("##### 📋 Quality Management System (QMS) Scheduled Trainings")
        st.markdown("<p style='color: #64748B; font-size: 0.8rem; margin-top: -6px;'>Quality policy orientations, submittal review gatekeeping, non-conformance closure procedures, and subcontractor QMS compliance.</p>", unsafe_allow_html=True)
        if len(df_qms) > 0:
            qc1, qc2, qc3 = st.columns([2.5, 1.2, 1.3])
            with qc1:
                q_qms = st.text_input("🔍 Search QMS Topics", key="q_qms_train", placeholder="Filter by Topic or Organization...")
            with qc2:
                status_filter_q = st.selectbox("Schedule Filter", ["All Sessions", "Upcoming Scheduled Only", "Fully Completed Only"], key="filter_status_q")
            with qc3:
                st.write("")
                st.write("")
                st.download_button(
                    label=f"⬇️ Download CSV ({len(df_qms)} items)",
                    data=df_qms.to_csv(index=False).encode('utf-8'),
                    file_name=f"QMS_Training_Schedule_{datetime.date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            disp_q = df_qms.copy()
            if q_qms:
                disp_q = disp_q[disp_q['Topic / Target Group'].str.contains(q_qms, case=False, na=False)]
            if status_filter_q == "Upcoming Scheduled Only":
                disp_q = disp_q[disp_q['Schedule Status'] == 'Upcoming Scheduled']
            elif status_filter_q == "Fully Completed Only":
                disp_q = disp_q[disp_q['Schedule Status'] == 'Fully Completed']

            cols_order_q = [c for c in ['S.N.', 'Topic / Target Group', 'Next Schedule', 'Schedule Status', 'Total Staff', 'Total Plan', 'Total Conducted', '% Conducted'] if c in disp_q.columns]
            st.dataframe(disp_q[cols_order_q], use_container_width=True, hide_index=True)
        else:
            st.info("QMS training schedule log not found.")

# -------------------------------------------------------------
# VIEW 5: LESSONS LEARNED (GRAPHIC DESIGNED SHOWCASE)
# -------------------------------------------------------------
elif st.session_state.current_view == "LESSONS":
    section_title("💡 Lessons Learned & Best Practices")
    st.markdown("<p style='color:#64748B;font-size:0.85rem;margin:-8px 0 18px 0;'>Executive Engineering Knowledge Base & Standardized Site Controls (Project: DD-2023-329).</p>", unsafe_allow_html=True)

    df_ll, df_bp = get_lessons_learned_data()
    total_ll = len(df_ll)
    total_bp = len(df_bp)

    # Summary KPIs
    lk1, lk2, lk3, lk4 = st.columns(4)
    with lk1:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #EF4444;"><div class="detail-kpi-title">CONSOLIDATED LESSONS LEARNED</div><div class="detail-kpi-value" style="color: #EF4444;">{total_ll:,}</div><div class="detail-kpi-sub">Systemic root causes analyzed</div></div>', unsafe_allow_html=True)
    with lk2:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #10B981;"><div class="detail-kpi-title">STANDARDIZED BEST PRACTICES</div><div class="detail-kpi-value" style="color: #10B981;">{total_bp:,}</div><div class="detail-kpi-sub">Site execution protocols</div></div>', unsafe_allow_html=True)
    with lk3:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #2563EB;"><div class="detail-kpi-title">GOVERNANCE STANDARD</div><div class="detail-kpi-value" style="font-size: 1.25rem; color: #2563EB;">DGDA QA/QC</div><div class="detail-kpi-sub">Master Specifications Compliant</div></div>', unsafe_allow_html=True)
    with lk4:
        st.markdown(f'<div class="detail-kpi-card" style="border-top-color: #6366F1;"><div class="detail-kpi-title">KEY DISCIPLINES</div><div class="detail-kpi-value" style="font-size: 1.25rem; color: #6366F1;">Civil • Arch • MEP</div><div class="detail-kpi-sub">Multi-discipline integration</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

    tab_ll, tab_bp = st.tabs([
        f"⚠️ Lessons Learned Showcase [{total_ll}]",
        f"🌟 Best Practices Showcase [{total_bp}]"
    ])

    with tab_ll:
        st.markdown("##### ⚠️ Graphical Lessons Learned Showcase")
        st.markdown("<p style='color: #64748B; font-size: 0.8rem; margin-top: -6px;'>Engineered case studies detailing root causes, operational impacts, and mandatory corrective & preventive actions (CAPA).</p>", unsafe_allow_html=True)
        if len(df_ll) > 0:
            lc1, lc2, lc3 = st.columns([2.5, 1.2, 1.3])
            with lc1:
                q_ll = st.text_input("🔍 Search Lessons Learned", key="q_ll_search", placeholder="Filter by Title, Discipline, ID, or Failure Mechanism...")
            with lc2:
                disc_options = ["All Disciplines"] + sorted(list(df_ll['Discipline / Domain'].dropna().unique()))
                selected_disc = st.selectbox("Discipline", disc_options, key="ll_disc_filter")
            with lc3:
                view_mode_ll = st.radio("Display View", ["🎨 Magazine Cards", "📊 Raw Table"], horizontal=True, key="view_mode_ll")

            disp_ll = df_ll.copy()
            if q_ll:
                disp_ll = disp_ll[
                    disp_ll['Lesson Learned Title'].str.contains(q_ll, case=False, na=False) |
                    disp_ll['Discipline / Domain'].str.contains(q_ll, case=False, na=False) |
                    disp_ll['Lesson Learned ID'].str.contains(q_ll, case=False, na=False) |
                    disp_ll['Systemic Root Cause / Problem Statement'].str.contains(q_ll, case=False, na=False)
                ]
            if selected_disc != "All Disciplines":
                disp_ll = disp_ll[disp_ll['Discipline / Domain'] == selected_disc]

            # Download button
            st.download_button(
                label=f"⬇️ Download Lessons Learned CSV ({len(disp_ll)} items)",
                data=disp_ll.to_csv(index=False).encode('utf-8'),
                file_name=f"Opera_House_Lessons_Learned_{datetime.date.today()}.csv",
                mime="text/csv",
                key="btn_dl_ll"
            )

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

            if view_mode_ll == "🎨 Magazine Cards":
                for _, row in disp_ll.iterrows():
                    render_lesson_learned_card(row.to_dict())
            else:
                st.dataframe(disp_ll, use_container_width=True, hide_index=True)
        else:
            st.info("Lessons Learned log not found.")

    with tab_bp:
        st.markdown("##### 🌟 Graphical Best Practices Showcase")
        st.markdown("<p style='color: #64748B; font-size: 0.8rem; margin-top: -6px;'>Standardized site execution protocols, lockout procedures, modular staging, and concrete quality assurance protocols.</p>", unsafe_allow_html=True)
        if len(df_bp) > 0:
            bc1, bc2, bc3 = st.columns([2.5, 1.2, 1.3])
            with bc1:
                q_bp = st.text_input("🔍 Search Best Practices", key="q_bp_search", placeholder="Filter by Title, Discipline, ID, or Protocol...")
            with bc2:
                disc_options_bp = ["All Disciplines"] + sorted(list(df_bp['Discipline / Domain'].dropna().unique()))
                selected_disc_bp = st.selectbox("Discipline", disc_options_bp, key="bp_disc_filter")
            with bc3:
                view_mode_bp = st.radio("Display View", ["🎨 Magazine Cards", "📊 Raw Table"], horizontal=True, key="view_mode_bp")

            disp_bp = df_bp.copy()
            if q_bp:
                disp_bp = disp_bp[
                    disp_bp['Best Practice Title'].str.contains(q_bp, case=False, na=False) |
                    disp_bp['Discipline / Domain'].str.contains(q_bp, case=False, na=False) |
                    disp_bp['Best Practice ID'].str.contains(q_bp, case=False, na=False) |
                    disp_bp['Standardized Methodology / Execution Protocol'].str.contains(q_bp, case=False, na=False)
                ]
            if selected_disc_bp != "All Disciplines":
                disp_bp = disp_bp[disp_bp['Discipline / Domain'] == selected_disc_bp]

            st.download_button(
                label=f"⬇️ Download Best Practices CSV ({len(disp_bp)} items)",
                data=disp_bp.to_csv(index=False).encode('utf-8'),
                file_name=f"Opera_House_Best_Practices_{datetime.date.today()}.csv",
                mime="text/csv",
                key="btn_dl_bp"
            )

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

            if view_mode_bp == "🎨 Magazine Cards":
                for _, row in disp_bp.iterrows():
                    render_best_practice_card(row.to_dict())
            else:
                st.dataframe(disp_bp, use_container_width=True, hide_index=True)
        else:
            st.info("Best Practices register not found.")

# -------------------------------------------------------------
# VIEW 6: MONTHLY QUALITY STATUS REPORT
# -------------------------------------------------------------
elif st.session_state.current_view == "MONTHLY":
    section_title("📅 Monthly Quality Status Report — Master Register Extract")
    st.markdown("<p style='color:#64748B;font-size:0.85rem;margin:-8px 0 20px 0;'>Aggregated quality performance indicators extracted from cumulative master logs.</p>", unsafe_allow_html=True)

    def get_metrics(cat, df_target):
        cat_df = df_target[df_target['Category'] == cat]
        total = len(cat_df)
        approved = len(cat_df[cat_df['Status'].isin(['A-Approved', 'B-Approved with Comments', 'Closed', 'Valid', 'Approved'])])
        open_count = len(cat_df[cat_df['Status'].isin(['Open', 'Pending', 'Under Review'])])
        rate = (approved / total * 100) if total > 0 else 0
        return total, approved, open_count, rate

    st.markdown("### 📂 Section 2: QMS & Engineering Submittals")
    qms_categories = [
        ("Method Statements (MS / MST)", "MST", 90.0),
        ("Inspection & Test Plans (ITP)", "ITP", 90.0),
        ("Material Approval Requests (MAR)", "MAR", 85.0),
        ("Shop Drawings (SDW / SHD)", "SHD", 85.0)
    ]
    qms_data = []
    for name, cat, target in qms_categories:
        p_tot, p_app, _, p_rate = get_metrics(cat, date_filtered_df)
        c_tot, c_app, _, c_rate = get_metrics(cat, df)
        qms_data.append({
            "Submittal Category": name,
            "Period Submissions": f"{p_tot:,}",
            "Period Approved (A+B)": f"{p_app:,}",
            "Period Compliance": f"{p_rate:.1f}%",
            "Cumulative Submissions": f"{c_tot:,}",
            "Cumulative Approved (A+B)": f"{c_app:,}",
            "Cumulative Rate": f"{c_rate:.1f}%",
            "Target Rate": f"{target:.0f}%"
        })
    st.dataframe(pd.DataFrame(qms_data), use_container_width=True, hide_index=True)

    st.markdown("### 🏗️ Section 3 & 4: Inspections & Non-Conformance Tracking")
    insp_data = []
    ncr_p_tot, _, ncr_p_open, _ = get_metrics("NCR", date_filtered_df)
    ncr_c_tot, ncr_c_closed, ncr_c_open, _ = get_metrics("NCR", df)
    ncr_closure = (ncr_c_closed / ncr_c_tot * 100) if ncr_c_tot > 0 else 0
    insp_data.append({
        "Quality Area": "Non-Conformance Reports (NCR)",
        "Period Raised": f"{ncr_p_tot:,}",
        "Period Open/Action": f"{ncr_p_open:,}",
        "Cumulative Raised": f"{ncr_c_tot:,}",
        "Cumulative Closed": f"{ncr_c_closed:,}",
        "Closure %": f"{ncr_closure:.1f}%"
    })
    mir_p_tot, mir_p_app, _, mir_p_rate = get_metrics("MIR", date_filtered_df)
    mir_c_tot, mir_c_app, _, mir_c_rate = get_metrics("MIR", df)
    insp_data.append({
        "Quality Area": "Material Inspection Requests (MIR)",
        "Period Raised": f"{mir_p_tot:,}",
        "Period Open/Action": f"{mir_p_app:,} Approved",
        "Cumulative Raised": f"{mir_c_tot:,}",
        "Cumulative Closed": f"{mir_c_app:,} Approved",
        "Closure %": f"{mir_c_rate:.1f}%"
    })
    wir_p_tot, wir_p_app, _, wir_p_rate = get_metrics("WIR", date_filtered_df)
    wir_c_tot, wir_c_app, _, wir_c_rate = get_metrics("WIR", df)
    insp_data.append({
        "Quality Area": "Work Inspection Requests (WIR)",
        "Period Raised": f"{wir_p_tot:,}",
        "Period Open/Action": f"{wir_p_app:,} Approved",
        "Cumulative Raised": f"{wir_c_tot:,}",
        "Cumulative Closed": f"{wir_c_app:,} Approved",
        "Closure %": f"{wir_c_rate:.1f}%"
    })
    st.dataframe(pd.DataFrame(insp_data), use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# VIEW 7: USER MANAGEMENT & ACCESS AUDIT (ADMIN ONLY)
# -------------------------------------------------------------
elif st.session_state.current_view == "ADMIN":
    current_role = st.session_state.get("user_info", {}).get("role", "viewer")
    if current_role != "admin":
        st.error("⛔ Unauthorized Access: This section is strictly reserved for QA/QC Administrators.")
    else:
        section_title("👥 User Account Management & Access Tracking")
        st.markdown("<p style='color:#64748B;font-size:0.85rem;margin:-8px 0 20px 0;'>Manage project team user access, provision email passwords, and audit login activity per day and month.</p>", unsafe_allow_html=True)

        admin_tab1, admin_tab2 = st.tabs(["🔐 User Accounts & Registration", "📈 Access Tracking & Audit Logs"])

        with admin_tab1:
            st.markdown("#### ➕ Create or Update User Credentials")
            with st.form("form_add_user", clear_on_submit=True):
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    new_username = st.text_input("Username", placeholder="e.g. j.doe")
                    new_email = st.text_input("User Email Address", placeholder="e.g. j.doe@ecm-jv.com")
                with col_u2:
                    new_password = st.text_input("Assign Password", type="password", placeholder="Assign login password")
                    new_role = st.selectbox("Role", ["viewer", "admin"], index=0, help="Admins can create users and view audit logs.")
                
                submitted = st.form_submit_button("Save / Update User", type="primary", use_container_width=True)
                if submitted:
                    if not new_username or not new_email or not new_password:
                        st.error("Please fill in username, email, and password.")
                    else:
                        ok, msg = add_user(new_username, new_email, new_password, new_role)
                        if ok:
                            st.success(f"✅ User '{new_username}' saved successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

            st.markdown("#### 📋 Registered User Accounts")
            users_df = get_all_users_df()
            if not users_df.empty:
                col_t, col_del = st.columns([3.2, 1.2])
                with col_t:
                    st.dataframe(users_df, use_container_width=True, hide_index=True)
                with col_del:
                    with st.container(border=True):
                        st.markdown("<div style='font-size: 0.88rem; font-weight: 700; color: #EF4444; margin-bottom: 8px;'>🗑️ Delete User</div>", unsafe_allow_html=True)
                        user_list = [u for u in users_df['username'].tolist() if u != 'uzair087']
                        if user_list:
                            del_target = st.selectbox("Select user to remove", user_list)
                            if st.button(f"Confirm Delete '{del_target}'", type="secondary", use_container_width=True):
                                delete_user(del_target)
                                st.warning(f"User '{del_target}' removed.")
                                st.rerun()
                        else:
                            st.caption("No deletable secondary users.")
            else:
                st.info("No registered users found.")

        with admin_tab2:
            st.markdown("#### 📊 Project Team Access Analytics")
            user_counts, daily_counts, monthly_counts, recent_logs = get_access_stats()

            # KPI Summary Cards
            tot_logins = int(user_counts['total_logins'].sum()) if not user_counts.empty else 0
            unique_users = len(user_counts) if not user_counts.empty else 0
            active_today = len(daily_counts[daily_counts['access_date'] == datetime.date.today().isoformat()]) if not daily_counts.empty else 0

            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Total Login Sessions", f"{tot_logins:,}")
            with k2:
                st.metric("Unique Active Users", f"{unique_users}")
            with k3:
                st.metric("User Logins Today", f"{active_today}")

            st.markdown("<br>", unsafe_allow_html=True)
            col_graph1, col_graph2 = st.columns(2)

            with col_graph1:
                st.markdown("<div style='font-weight:700; font-size: 0.95rem; color: #1E293B; margin-bottom: 8px;'>📅 Daily Access Activity (Per User)</div>", unsafe_allow_html=True)
                if not daily_counts.empty:
                    st.dataframe(daily_counts, use_container_width=True, hide_index=True)
                else:
                    st.info("No daily logs recorded yet.")

            with col_graph2:
                st.markdown("<div style='font-weight:700; font-size: 0.95rem; color: #1E293B; margin-bottom: 8px;'>🗓️ Monthly Access Summary (Per User)</div>", unsafe_allow_html=True)
                if not monthly_counts.empty:
                    st.dataframe(monthly_counts, use_container_width=True, hide_index=True)
                else:
                    st.info("No monthly logs recorded yet.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div style='font-weight:700; font-size: 0.95rem; color: #1E293B; margin-bottom: 8px;'>⏱️ Recent Audit Trail (Last 150 Logins)</div>", unsafe_allow_html=True)
            if not recent_logs.empty:
                st.dataframe(recent_logs, use_container_width=True, hide_index=True)
            else:
                st.info("No access logs found.")

st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown("""
<div style='display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: #94A3B8;'>
    <div>Royal Diriyah Opera House &nbsp;|&nbsp; QA/QC Digital Platform</div>
    <div>Status Legend: &nbsp; 🟢 Code A (Pass) &nbsp;|&nbsp; 🔵 Code B (Comments) &nbsp;|&nbsp; 🟡 Code C (Revise) &nbsp;|&nbsp; 🔴 Code D / NCR (Rejected)</div>
</div>
""", unsafe_allow_html=True)
