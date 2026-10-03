import os
import re
import datetime
import pandas as pd
import numpy as np
import streamlit as st

# Pre-compiled regular expressions for high-throughput parsing
RE_NCR_DOC = re.compile(r'SOA-NCR-QL-\d+|ECM-NCR-QL-\d+|NCR-QL-\d+|NCR-\d+', re.IGNORECASE)
RE_NCR_FULL = re.compile(r'[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-NCR-[A-Z0-9]+-\d+')
RE_ZONE_SEARCH = re.compile(r'\b(?:Zone|Z)\s*[-_:]?\s*([A-Za-z0-9]+(?:[- ][A-Za-z0-9]+)?)', re.IGNORECASE)
RE_ZONE_CLEAN = re.compile(r'\s+(WAS|EXEC|FOR|IN|AT|OF|WALL|RET|COL|MOCK)\b.*')
RE_DIGIT_START = re.compile(r'^([0-9]+)[-_ ]')
RE_CHAR_DIGIT = re.compile(r'^[A-Z]\s+([0-9]+)')

# Safe search directories within the project workspace
SEARCH_DIRS = ["auto_logs", "logs", ".temp_uploads", "."]

def _generate_empty_data():
    """Generates an empty dataframe with correct schema for empty states."""
    df = pd.DataFrame(columns=[
        'Date', 'Category', 'Reference No', 'Description', 
        'Status', 'Area', 'Contractor', 'Discipline', 'Root Cause'
    ])
    calibration_data = pd.DataFrame(columns=[
        'Equipment', 'Last Calibrated', 'Expiry Date', 'Status'
    ])
    concrete_data = pd.DataFrame(columns=[
        'Zone', 'Date', 'Element', 'Volume'
    ])
    return df, calibration_data, concrete_data

def normalize_zone(text, doc=''):
    """Extracts and normalizes project structural zone from description or document reference."""
    full_text = f"{text or ''} {doc or ''}"
    m = RE_ZONE_SEARCH.search(full_text)
    if m:
        z = m.group(1).strip().upper()
        z = RE_ZONE_CLEAN.sub('', z)
        if z.isdigit():
            return f"Zone {int(z)}"
        m_dig = RE_DIGIT_START.match(z)
        if m_dig:
            return f"Zone {int(m_dig.group(1))}"
        m_s = RE_CHAR_DIGIT.match(z)
        if m_s:
            return f"Zone {int(m_s.group(1))}"
        return f"Zone {z}"
    return "Site-wide / General"

def extract_discipline(text):
    """Identifies engineering discipline code from document text."""
    t = str(text or '').upper()
    if ' CE ' in t or '-CE-' in t or 'CIVIL' in t or 'CONCRETE' in t: return 'Civil (CE)'
    if ' AR ' in t or '-AR-' in t or 'ARCH' in t: return 'Arch (AR)'
    if ' EL ' in t or '-EL-' in t or 'ELEC' in t: return 'Electrical (EL)'
    if ' ME ' in t or '-ME-' in t or 'MECH' in t or 'HVAC' in t: return 'Mechanical (ME)'
    if ' ST ' in t or '-ST-' in t or 'STEEL' in t: return 'Struc Steel (ST)'
    return 'Other'

def extract_root_cause(category, description):
    """Categorizes root cause for NCR non-conformance tracking."""
    if category != 'NCR': return 'N/A'
    t = str(description or '').lower()
    if any(x in t for x in ['concrete', 'compressive', 'strength', 'cube', 'slump', 'pour']):
        return 'Concrete Strength / Mix'
    if any(x in t for x in ['rebar', 'formwork', 'alignment', 'cover', 'spacing', 'tie']):
        return 'Formwork / Rebar Alignment'
    if any(x in t for x in ['material', 'spec', 'approved', 'submittal', 'delivery', 'sample']):
        return 'Material Non-Compliance'
    if any(x in t for x in ['workmanship', 'finish', 'crack', 'honeycomb', 'damage', 'cold joint']):
        return 'Workmanship / Finish'
    if any(x in t for x in ['design', 'drawing', 'clash', 'dimension', 'elevation']):
        return 'Design & Drawing Clash'
    return 'Other / Unclassified'

@st.cache_data(show_spinner=False)
def parse_ncr_ppt(ppt_path_or_bytes):
    """Parses open NCR status tables from PowerPoint slide decks with caching."""
    import pptx
    prs = pptx.Presentation(ppt_path_or_bytes)
    ppt_ncrs = {}
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_table:
                table = shape.table
                for row_idx in range(1, len(table.rows)):
                    c = [cell.text.strip().replace('\n', ' ') for cell in table.rows[row_idx].cells]
                    if len(c) < 7: continue
                    raw_doc = c[1].replace('\x0b', ' ').strip()
                    found = RE_NCR_DOC.findall(raw_doc)
                    key = found[0] if found else raw_doc
                    
                    area = ''
                    if '(' in raw_doc and ')' in raw_doc:
                        area = raw_doc[raw_doc.find('(')+1:raw_doc.find(')')]
                    
                    ppt_ncrs[key] = {
                        'Sr': c[0],
                        'DocRaw': raw_doc,
                        'Description': c[2],
                        'CAPA': c[3],
                        'IssueDate': c[4],
                        'DaysPassed': c[5],
                        'CurrentStatus': c[6],
                        'Area': area
                    }
    return ppt_ncrs

def find_latest_ncr_ppt():
    """Locates the latest active NCR PowerPoint presentation in workspace folders."""
    candidates = []
    for search_dir in SEARCH_DIRS:
        if os.path.exists(search_dir):
            for fn in os.listdir(search_dir):
                if fn.startswith("~$") or fn.startswith("."): continue
                if fn.endswith('.pptx') and ('ncr' in fn.lower() or 'open' in fn.lower()):
                    full_p = os.path.join(search_dir, fn)
                    if os.path.isfile(full_p):
                        candidates.append((full_p, os.path.getmtime(full_p)))
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    return None

def _safe_read_excel(source, skiprows=0):
    try:
        return pd.read_excel(source, skiprows=skiprows, engine='calamine')
    except Exception:
        return pd.read_excel(source, skiprows=skiprows)

def process_uploaded_logs(_uploaded_files=None):
    """
    High-performance ingestion engine for Aconex master registers and auxiliary logs.
    Reads Excel files using calamine when available, falling back to openpyxl.
    """
    is_mock = False
    dfs = []
    
    if _uploaded_files and len(_uploaded_files) > 0:
        aux_keywords = [
            'learning event', 'training schedule', 'training', 'lessons learned',
            'lessons_learned', 'best_practices', 'best practices', 'cast insitu',
            'cast in situ', 'daily productivity', 'concrete', 'calibration'
        ]
        log_files = [
            f for f in _uploaded_files 
            if not any(k in getattr(f, 'name', '').lower() for k in aux_keywords)
        ]
        
        for file in log_files:
            try:
                import io
                # Support both file paths and Streamlit UploadedFile objects
                file_path = getattr(file, 'path', None)
                source = file_path if (file_path and os.path.exists(file_path)) else io.BytesIO(file.read())
                temp_df = _safe_read_excel(source)
                
                # Check for Custom NCR Log Format
                if len(temp_df.columns) > 0 and "NON-CONFORMANCE REPORT" in str(temp_df.columns[0]):
                    header_idx = 15
                    for i, row in enumerate(temp_df.values[:25]):
                        row_s = str(row)
                        if 'NCR  Document No' in row_s or 'Sr.No' in str(row[0]):
                            header_idx = i + 1
                            break
                    
                    if file_path and os.path.exists(file_path):
                        temp_df = pd.read_excel(file_path, skiprows=header_idx, engine='calamine')
                    else:
                        file_bytes.seek(0)
                        temp_df = pd.read_excel(file_bytes, skiprows=header_idx, engine='calamine')
                    
                    col_map = {}
                    for c in temp_df.columns:
                        cn = str(c).strip()
                        if 'NCR  Document No' in cn: col_map[c] = 'Reference No'
                        elif 'Location' in cn: col_map[c] = 'Area'
                        elif 'NCR Description' in cn: col_map[c] = 'Description'
                        elif 'Date Responsed' in cn: col_map[c] = 'Date'
                        elif 'Current Status' in cn: col_map[c] = 'Status'
                        
                    temp_df = temp_df.rename(columns=col_map)
                    temp_df['Category'] = 'NCR'
                    temp_df['Contractor'] = 'Main Contractor'
                    
                    if 'Status' in temp_df.columns:
                        temp_df = temp_df.dropna(subset=['Status'])
                        temp_df['Status'] = temp_df['Status'].apply(
                            lambda v: 'Closed' if any(x in str(v).lower() for x in ['close', 'approv']) else 'Open'
                        )

                # Check for Standard Aconex Exports
                elif len(temp_df.columns) > 0 and ("In case any cell is highlighted" in str(temp_df.columns[0]) or "exportdocs" in getattr(file, 'name', '').lower()):
                    detected_category = None
                    for _, row in temp_df.head(10).iterrows():
                        row_str = str(row.values).lower()
                        if "work inspection request" in row_str or "type: wir" in row_str: detected_category = "WIR"
                        elif "material inspection request" in row_str or "type: mir" in row_str: detected_category = "MIR"
                        elif "material approval" in row_str or "type: mar" in row_str: detected_category = "MAR"
                        elif "method statement" in row_str or "type: mst" in row_str: detected_category = "MST"
                        elif "inspection and test plan" in row_str or "type: itp" in row_str: detected_category = "ITP"
                        elif "shop drawing" in row_str or "type: shd" in row_str: detected_category = "SHD"
                        elif "non conformance" in row_str or "non-conformance" in row_str or "type: ncr" in row_str: detected_category = "NCR"
                        if detected_category: break
                            
                    skip_rows = 10 if "In case any cell is highlighted" in str(temp_df.columns[0]) else 0
                    temp_df = _safe_read_excel(source, skiprows=skip_rows)
                    
                    col_map = {}
                    if 'Date Modified' in temp_df.columns:
                        temp_df['Date'] = temp_df['Date Modified'].combine_first(temp_df.get('Revision Date'))
                    elif 'Revision Date' in temp_df.columns:
                        temp_df['Date'] = temp_df['Revision Date']
                    if 'Document No' in temp_df.columns: col_map['Document No'] = 'Reference No'
                    if 'Title' in temp_df.columns: col_map['Title'] = 'Description'
                    if 'Discipline' in temp_df.columns: col_map['Discipline'] = 'Area'
                    temp_df = temp_df.rename(columns=col_map)
                    
                    if 'Type' in temp_df.columns:
                        def map_aconex_type(row):
                            doc_no = str(row.get('Reference No', '')).strip()
                            s = str(row.get('Type', '')).lower()
                            if 'work inspection' in s: return 'WIR'
                            if 'material inspection' in s: return 'MIR'
                            if 'material approval' in s: return 'MAR'
                            if 'method statement' in s: return 'MST'
                            if 'test plan' in s or 'itp' in s: return 'ITP'
                            if 'shop drawing' in s or 'shd' in s: return 'SHD'
                            if 'SOA-NCR-QL' in doc_no: return 'NCR'
                            if ('non conformance' in s or 'non-conformance' in s) and 'SOA-NCR-QL' in doc_no: return 'NCR'
                            return 'UNKNOWN'
                        temp_df['Category'] = temp_df.apply(map_aconex_type, axis=1)
                    else:
                        fname = getattr(file, 'name', '').upper()
                        if 'WIR' in fname: temp_df['Category'] = 'WIR'
                        elif 'MIR' in fname: temp_df['Category'] = 'MIR'
                        elif 'MAR' in fname: temp_df['Category'] = 'MAR'
                        elif 'MST' in fname: temp_df['Category'] = 'MST'
                        elif 'ITP' in fname: temp_df['Category'] = 'ITP'
                        elif 'SHD' in fname or 'SDH' in fname or 'SHOP DRAWING' in fname: temp_df['Category'] = 'SHD'
                        elif 'NCR' in fname: temp_df['Category'] = 'NCR'
                        elif detected_category: temp_df['Category'] = detected_category
                        else: temp_df['Category'] = 'UNKNOWN'
                    
                    def map_status(row):
                        raw_status = str(row.get('Status', '')).lower() if pd.notna(row.get('Status')) else ''
                        raw_review = str(row.get('Review Status', '')).lower() if pd.notna(row.get('Review Status')) else ''
                        combined_s = f"{raw_status} {raw_review}".strip()
                        cat = row.get('Category', '')
                        
                        # Exclude internal / non-contractual review workflows
                        if any(term in combined_s for term in ['withdrawn', 'qa rejected', 'terminated', 'for information']):
                            return 'IGNORE'
                        
                        if cat == 'NCR':
                            if any(x in combined_s for x in ['approved', 'closed', 'close', 'approve', 'pass']):
                                return 'Closed'
                            return 'Open'
                        else:
                            s = raw_review if raw_review and raw_review != 'nan' else raw_status
                            if not s or s == 'nan': return 'IGNORE'
                            if 'approved with comments' in s or 'b-approved' in s: return 'B-Approved with Comments'
                            if 'approved' in s and 'comments' not in s: return 'A-Approved'
                            if 'revise' in s or 'resubmit' in s: return 'C-Revise and Resubmit'
                            if 'reject' in s: return 'D-Rejected'
                            return 'IGNORE'
                            
                    temp_df['Status'] = temp_df.apply(map_status, axis=1)
                    temp_df = temp_df[temp_df['Status'] != 'IGNORE']
                    temp_df['Contractor'] = 'Main Contractor'
                    
                # Clean up columns: strip spaces and drop unnamed/foreign junk
                temp_df.columns = [str(c).strip() for c in temp_df.columns]
                junk_cols = [c for c in temp_df.columns if c.startswith('Unnamed:') or 'General Information' in c]
                if junk_cols:
                    temp_df = temp_df.drop(columns=junk_cols, errors='ignore')

                if 'Date' in temp_df.columns:
                    temp_df['Date'] = pd.to_datetime(temp_df['Date'], errors='coerce')
                    temp_df = temp_df[temp_df['Date'].notna()]
                    temp_df['Date'] = temp_df['Date'].dt.date
                    
                dfs.append(temp_df)
            except Exception as e:
                print(f"Notice: skipped non-conforming file {getattr(file, 'name', '')}: {e}")
                
        if len(dfs) > 0:
            df = pd.concat(dfs, ignore_index=True)
            if len(df) == 0:
                empty_df, mock_cal, mock_conc = _generate_empty_data()
                df = empty_df
                is_mock = True
            else:
                # Filter strictly to the 7 approved QA/QC Categories
                valid_qc_categories = ['WIR', 'MIR', 'MAR', 'MST', 'ITP', 'SHD', 'NCR']
                df = df[df['Category'].isin(valid_qc_categories)].copy()

                # For Shop Drawings (SHD), keep only PDF drawings (exclude DWG CAD models)
                is_shd = df['Category'] == 'SHD'
                is_pdf = (
                    df['File'].astype(str).str.lower().str.contains('pdf') | 
                    df['Reference No'].astype(str).str.upper().str.endswith('_PDF')
                )
                df = df[(~is_shd) | is_pdf].copy()

                # When multiple ExportDocs registers are ingested, retain the latest entry per Reference No
                if 'Reference No' in df.columns:
                    # Sort by Date / Version if present, keeping latest
                    sort_cols = [c for c in ['Date', 'Date Modified', 'Version', 'Revision'] if c in df.columns]
                    if sort_cols:
                        df = df.sort_values(by=sort_cols, ascending=True)
                    df = df.drop_duplicates(subset=['Reference No'], keep='last').copy()

                required_cols = ['Date', 'Category', 'Reference No', 'Description', 'Status', 'Area', 'Contractor']
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = "N/A"
                        
                df['Discipline'] = df.apply(
                    lambda r: extract_discipline(f"{r.get('Reference No', '')} {r.get('Description', '')}"),
                    axis=1
                )
                df['Root Cause'] = df.apply(
                    lambda r: extract_root_cause(r.get('Category'), r.get('Description')),
                    axis=1
                )

                # Harmonize NCR statuses with Open NCR Tracker presentation
                try:
                    ppt_file = find_latest_ncr_ppt()
                    if ppt_file:
                        ppt_ncrs = parse_ncr_ppt(ppt_file)
                        if ppt_ncrs:
                            ncr_mask = df['Category'] == 'NCR'
                            for idx, r in df[ncr_mask].iterrows():
                                ref = str(r['Reference No']).strip()
                                match_k = next((k for k in ppt_ncrs if k in ref), None)
                                if match_k:
                                    p_cur = str(ppt_ncrs[match_k].get('CurrentStatus', '')).strip().lower()
                                    if 'closed' in p_cur:
                                        df.at[idx, 'Status'] = 'Closed'
                                    else:
                                        df.at[idx, 'Status'] = 'Open'
                except Exception as e:
                    print(f"Notice: NCR PPT harmonization: {e}")
        else:
            empty_df, mock_cal, mock_conc = _generate_empty_data()
            df = empty_df
            is_mock = True
    else:
        empty_df, mock_cal, mock_conc = _generate_empty_data()
        df = empty_df
        is_mock = True

    # 2. Calibration Data
    calibration_data = None
    if _uploaded_files:
        cal_file = next((f for f in _uploaded_files if 'calibration' in getattr(f, 'name', '').lower()), None)
        if cal_file:
            try:
                import io
                cal_path = getattr(cal_file, 'path', None)
                if cal_path and os.path.exists(cal_path):
                    calibration_data = pd.read_excel(cal_path, engine='calamine')
                else:
                    calibration_data = pd.read_excel(io.BytesIO(cal_file.read()), engine='calamine')
            except Exception:
                pass
                
    if calibration_data is None:
        _, calibration_data, _ = _generate_empty_data()
        
    # 3. Structural Concrete Placement Data
    concrete_df = None
    if _uploaded_files:
        conc_file = next((f for f in _uploaded_files if any(k in getattr(f, 'name', '').lower() for k in ['cast insitu', 'cast in situ', 'concrete'])), None)
        if conc_file:
            try:
                import io
                import openpyxl
                conc_path = getattr(conc_file, 'path', None)
                file_target = conc_path if (conc_path and os.path.exists(conc_path)) else io.BytesIO(conc_file.read())
                
                wb = openpyxl.load_workbook(file_target, read_only=True, data_only=True)
                
                # Format A: Royal Opera House Master "Cast In Situ Tracker"
                if 'Cast In Situ Tracker' in wb.sheetnames:
                    ws = wb['Cast In Situ Tracker']
                    rows = []
                    header = None
                    for i, r in enumerate(ws.iter_rows(min_row=6, max_col=20, values_only=True)):
                        if i == 0:
                            header = [str(x).strip() if x is not None else f'col_{idx}' for idx, x in enumerate(r)]
                            continue
                        if r[0] is None and r[11] is None and r[16] is None:
                            continue
                        rows.append(r)
                    
                    if rows and header:
                        c_raw = pd.DataFrame(rows, columns=header)
                        c_raw['Date'] = pd.to_datetime(c_raw['Date of Casting'], errors='coerce')
                        c_raw = c_raw[c_raw['Date'].notna()]
                        c_raw['Date'] = c_raw['Date'].dt.date
                        c_raw['Volume'] = pd.to_numeric(c_raw['Concrete Quantity (m3)'], errors='coerce').fillna(0)
                        
                        def norm_c_zone(z):
                            z_str = str(z).strip()
                            if not z_str or z_str.lower() in ['none', 'nan']: return 'Site-wide'
                            if z_str.isdigit(): return f'Zone {int(z_str)}'
                            if not z_str.lower().startswith('zone'): return f'Zone {z_str}'
                            return z_str
                        c_raw['Zone'] = c_raw['Zone'].apply(norm_c_zone)
                        
                        def norm_c_element(e):
                            el = str(e).lower()
                            if 'raft' in el or 'foundation' in el or 'footing' in el: return 'Raft & Foundation'
                            if 'blinding' in el: return 'Blinding'
                            if 'column' in el: return 'Columns'
                            if 'wall' in el: return 'Walls'
                            if 'slab' in el: return 'Slab'
                            if 'stair' in el: return 'Stairs'
                            if 'beam' in el: return 'Beams'
                            return 'Other Concrete'
                        c_raw['Element'] = c_raw['Element and Inspection Description'].apply(norm_c_element)
                        
                        c_raw = c_raw[c_raw['Volume'] > 0]
                        c_raw = c_raw[pd.to_datetime(c_raw['Date']).dt.year >= 2024]
                        concrete_df = c_raw[['Zone', 'Date', 'Element', 'Volume']].copy()
                
                # Format B: Legacy Multi-sheet format
                elif any(elem in wb.sheetnames for elem in ['Columns', 'Slab', 'Internal Wall']):
                    xls = pd.ExcelFile(file_target)
                    apportioned_data = []
                    elements = ['Columns', 'External Wall', 'Internal Wall', 'Slab']
                    for element in elements:
                        if element not in xls.sheet_names:
                            continue
                        el_df = pd.read_excel(xls, sheet_name=element, header=None)
                        m3_row_idx = None
                        for i, row in el_df.iterrows():
                            row_str = str(row.values).lower()
                            if 'concrete quantity' in row_str or 'm3' in row_str:
                                m3_row_idx = i
                                break
                        if m3_row_idx is None: continue
                        date_row_idx = None
                        for i in range(min(15, len(el_df))):
                            has_date = False
                            for val in el_df.iloc[i, 4:10].values:
                                if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
                                    has_date = True
                                    break
                            if has_date:
                                date_row_idx = i
                                break
                        if date_row_idx is None: continue
                        dates = el_df.iloc[date_row_idx, 4:].values
                        zone_data = el_df.iloc[date_row_idx+1:m3_row_idx, [2] + list(range(4, el_df.shape[1]))].copy()
                        zone_data.columns = ['Zone'] + list(dates)
                        zone_data = zone_data.dropna(subset=['Zone'])
                        zone_data = zone_data[zone_data['Zone'].astype(str).str.contains('Zone', case=False)]
                        valid_dates = [d for d in dates if pd.notna(d) and not isinstance(d, str)]
                        melted = pd.melt(zone_data, id_vars=['Zone'], value_vars=valid_dates)
                        melted.columns = ['Zone', 'Date', 'RawValue']
                        melted['RawValue'] = pd.to_numeric(melted['RawValue'], errors='coerce').fillna(0)
                        m3_data = el_df.iloc[m3_row_idx, 4:].values
                        daily_m3 = pd.DataFrame({'Date': dates, 'DailyM3': m3_data})
                        daily_m3 = daily_m3[daily_m3['Date'].isin(valid_dates)]
                        daily_m3['DailyM3'] = pd.to_numeric(daily_m3['DailyM3'], errors='coerce').fillna(0)
                        merged = pd.merge(melted, daily_m3, on='Date', how='left')
                        daily_totals = merged.groupby('Date')['RawValue'].transform('sum')
                        merged['Volume'] = 0.0
                        mask = daily_totals > 0
                        merged.loc[mask, 'Volume'] = merged.loc[mask, 'DailyM3'] * (merged.loc[mask, 'RawValue'] / daily_totals[mask])
                        merged['Element'] = element
                        apportioned_data.append(merged[['Zone', 'Date', 'Element', 'Volume']])
                    if apportioned_data:
                        final_df = pd.concat(apportioned_data, ignore_index=True)
                        final_df = final_df[final_df['Volume'] > 0]
                        final_df['Element'] = final_df['Element'].replace({'Internal Wall': 'Walls', 'External Wall': 'Walls'})
                        final_df['Date'] = pd.to_datetime(final_df['Date'], errors='coerce')
                        final_df = final_df[final_df['Date'].dt.year >= 2020]
                        final_df['Date'] = final_df['Date'].dt.date
                        concrete_df = final_df
            except Exception as e:
                print(f"Notice: concrete log parser: {e}")
                
    return df, calibration_data, concrete_df, is_mock

def filter_data(df, start_date, end_date, category):
    """
    Safely filters dataframe by date range and category WITHOUT mutating the cached dataframe.
    Ultra-fast vectorized date comparison.
    """
    if df is None or len(df) == 0:
        return df
        
    # Standardize comparison dates
    s_date = start_date.date() if isinstance(start_date, (datetime.datetime, pd.Timestamp)) else start_date
    e_date = end_date.date() if isinstance(end_date, (datetime.datetime, pd.Timestamp)) else end_date
    
    if 'Date' in df.columns and len(df) > 0:
        first_val = df['Date'].iloc[0]
        if isinstance(first_val, datetime.date):
            date_col = df['Date']
        else:
            date_col = pd.to_datetime(df['Date'], errors='coerce').dt.date
        mask = (date_col >= s_date) & (date_col <= e_date)
        filtered = df[mask].copy()
    else:
        filtered = df.copy()
        
    if category != "ALL":
        filtered = filtered[filtered['Category'] == category]
        
    return filtered

def get_ncr_master_data(all_submittals_df, ppt_path=None):
    """
    Reconciles cumulative Aconex client NCR entries with Open NCR PowerPoint tracker.
    Applies unified status and aging logic.
    """
    # 1. Parse PPT
    ppt_ncrs = {}
    if ppt_path and os.path.exists(ppt_path):
        try:
            ppt_ncrs = parse_ncr_ppt(ppt_path)
        except Exception:
            pass
            
    if not ppt_ncrs:
        found_ppt = find_latest_ncr_ppt()
        if found_ppt:
            try:
                ppt_ncrs = parse_ncr_ppt(found_ppt)
            except Exception:
                pass

    # 2. Extract NCRs from master submittal logs
    ncr_submittals = all_submittals_df[all_submittals_df['Category'] == 'NCR'].copy()
    if len(ncr_submittals) > 0:
        ncr_submittals = ncr_submittals.drop_duplicates(subset=['Reference No'], keep='last')

    ref_date = datetime.date.today()
    reconciled = []
    seen_refs = set()

    # Match Aconex NCRs
    for _, r in ncr_submittals.iterrows():
        doc_no = str(r['Reference No']).strip()
        seen_refs.add(doc_no)
        
        match_key = next((k for k in ppt_ncrs if k in doc_no), None)
        p_data = ppt_ncrs.get(match_key, {}) if match_key else {}
        
        date_val = r['Date']
        if (pd.isna(date_val) or str(date_val) == 'NaT') and 'IssueDate' in p_data:
            date_val = p_data['IssueDate']
        date_dt = pd.to_datetime(date_val, errors='coerce')
        
        # Calculate days open
        days_open = 0
        days_passed_str = str(p_data.get('DaysPassed', '')).strip()
        if days_passed_str:
            m_days = re.search(r'(\d+)\s*d', days_passed_str, re.IGNORECASE)
            if m_days:
                days_open = int(m_days.group(1))
            elif pd.notna(date_dt):
                days_open = max(0, (ref_date - date_dt.date()).days)
        elif pd.notna(date_dt):
            days_open = max(0, (ref_date - date_dt.date()).days)
            
        # Status determination:
        # If in PPT tracker, it remains Open unless PPT explicitly says 'Closed'
        # If not in PPT, it follows the submittal register status.
        ppt_status = p_data.get('CurrentStatus', '')
        aconex_status = str(r.get('Status', 'Open'))
        
        if p_data:
            final_status = 'Closed' if 'closed' in ppt_status.lower() else 'Open'
        else:
            final_status = aconex_status
                
        # Aging category:
        if final_status == 'Open':
            dp_lower = days_passed_str.lower()
            if '[overdue]' in dp_lower:
                aging_cat = 'Overdue (> 2 Months)'
            elif '[< 2 months]' in dp_lower:
                aging_cat = 'Active (< 2 Months)'
            elif days_open >= 60:
                aging_cat = 'Overdue (> 2 Months)'
            else:
                aging_cat = 'Active (< 2 Months)'
        else:
            aging_cat = 'Closed'
            
        capa = p_data.get('CAPA', '')
        if not capa:
            capa = 'Completed / Verified' if final_status == 'Closed' else 'Pending submission from contractor'
            
        status_note = ppt_status if ppt_status else ('Closed / Verified' if final_status == 'Closed' else 'Awaiting review / action')
        
        disc = r.get('Discipline', 'Civil (CE)')
        if p_data.get('Area'):
            disc = f"{p_data['Area']} — {disc}"
            
        desc_text = p_data.get('Description', r.get('Description', 'Quality Non-Conformance'))
        zone_val = normalize_zone(desc_text, doc_no)
        sr_num = p_data.get('Sr', '')
        days_passed_display = days_passed_str if days_passed_str else f"{days_open} d [{'OVERDUE' if days_open >= 60 else '< 2 Months'}]"
        
        reconciled.append({
            'Sr': sr_num,
            'Document No': doc_no,
            'Description': desc_text,
            'Corrective Action': capa,
            'Issue Date': date_dt.date() if pd.notna(date_dt) else None,
            'Days Passed': days_passed_display,
            'Days Open': days_open,
            'Current Status': status_note,
            'Status': final_status,
            'Aging Category': aging_cat,
            'Discipline': disc,
            'Zone': zone_val,
            'Origin': 'Consultant (SOA)' if 'SOA-NCR' in doc_no else ('JV Internal (ECM)' if 'ECM-NCR' in doc_no else 'Other')
        })

    # Add any remaining PPT items that weren't in Aconex export
    for k, p_data in ppt_ncrs.items():
        doc_raw = p_data.get('DocRaw', k)
        clean_doc = RE_NCR_FULL.findall(doc_raw.replace(' ', ''))
        doc_no = clean_doc[0] if clean_doc else doc_raw
        if any(k in s for s in seen_refs) or any(doc_no in s for s in seen_refs):
            continue
            
        date_dt = pd.to_datetime(p_data.get('IssueDate'), errors='coerce')
        days_open = 0
        if pd.notna(date_dt):
            days_open = max(0, (ref_date - date_dt.date()).days)
            
        ppt_desc = p_data.get('Description', 'Non-conformance recorded')
        zone_val = normalize_zone(ppt_desc, doc_no)
        ppt_status = p_data.get('CurrentStatus', p_data.get('Status', 'Open'))
        final_status = 'Closed' if any(x in str(ppt_status).lower() for x in ['close', 'approv', 'pass']) else 'Open'
        aging_cat = 'Closed' if final_status == 'Closed' else ('Overdue (> 2 Months)' if days_open >= 60 else 'Active (< 2 Months)')

        reconciled.append({
            'Sr': p_data.get('Sr', ''),
            'Document No': doc_no,
            'Description': ppt_desc,
            'Corrective Action': p_data.get('CAPA', 'Action defined'),
            'Issue Date': date_dt.date() if pd.notna(date_dt) else None,
            'Days Passed': p_data.get('DaysPassed', f"{days_open} d"),
            'Days Open': days_open,
            'Current Status': ppt_status,
            'Status': final_status,
            'Aging Category': aging_cat,
            'Discipline': p_data.get('Area', 'Civil / Arch'),
            'Zone': zone_val,
            'Origin': 'Consultant (SOA)' if 'SOA-NCR' in doc_no else 'JV Internal (ECM)'
        })

    master_df = pd.DataFrame(reconciled)
    
    # 3. Apply Team Real-Time Overrides from ncr_status_db
    try:
        from ncr_status_db import get_ncr_status_overrides
        overrides = get_ncr_status_overrides()
        if overrides and len(master_df) > 0:
            for idx, r in master_df.iterrows():
                d_no = str(r.get('Document No', '')).strip()
                # Check direct match or substring match
                match_ovr = next((v for k, v in overrides.items() if k in d_no or d_no in k), None)
                if match_ovr:
                    new_st = match_ovr['current_status']
                    master_df.at[idx, 'Current Status'] = new_st
                    if any(x in new_st.lower() for x in ['closed', 'passed', 'completed', 'approved']):
                        master_df.at[idx, 'Status'] = 'Closed'
                        master_df.at[idx, 'Aging Category'] = 'Closed'
    except Exception as e:
        print(f"Notice: could not apply NCR overrides: {e}")

    if len(master_df) > 0:
        master_df = master_df.sort_values(by=['Days Open'], ascending=False)
    return master_df

def get_post_pour_data():
    """Generates standard post-pour defect resolution dataset."""
    zones = ['Basement 1', 'Basement 2'] * 20
    defects = ['Honeycombing', 'Tie-rod holes', 'Shrinkage Crack', 'Uneven Surface Alignment']
    statuses = ['Open', 'Repaired', 'Inspected']
    contractors = ['Midmac', 'ECM']
    
    np.random.seed(42)
    data = []
    for i in range(40):
        data.append({
            'Zone': zones[i],
            'Defect Type': np.random.choice(defects),
            'Status': np.random.choice(statuses, p=[0.25, 0.35, 0.40]),
            'Contractor': np.random.choice(contractors)
        })
        
    return pd.DataFrame(data)

@st.cache_data(ttl=300, show_spinner=False)
def get_training_data():
    """Loads ECM-JV Annual Quality and Functional Training records."""
    qms_rows, func_rows = [], []
    train_file = None
    for d in SEARCH_DIRS:
        if os.path.exists(d):
            for fn in os.listdir(d):
                if fn.startswith("~$") or fn.startswith("."): continue
                if "training" in fn.lower() and (fn.endswith(".xlsx") or fn.endswith(".xls")):
                    train_file = os.path.join(d, fn)
                    break
        if train_file: break
        
    if train_file and os.path.exists(train_file):
        try:
            xls = pd.ExcelFile(train_file)
            month_names = {
                '2026-01-01 00:00:00': 'Jan 2026', '2026-02-28 00:00:00': 'Feb 2026',
                '2026-03-01 00:00:00': 'Mar 2026', '2026-04-01 00:00:00': 'Apr 2026',
                '2026-05-01 00:00:00': 'May 2026', '2026-06-01 00:00:00': 'Jun 2026',
                '2026-07-01 00:00:00': 'Jul 2026', '2026-08-01 00:00:00': 'Aug 2026',
                '2026-09-01 00:00:00': 'Sep 2026', '2026-10-01 00:00:00': 'Oct 2026',
                '2026-11-01 00:00:00': 'Nov 2026', '2026-12-01 00:00:00': 'Dec 2026'
            }
            for s in xls.sheet_names:
                is_qms = 'qms' in s.lower()
                is_func = 'functional' in s.lower()
                if not (is_qms or is_func): continue
                
                df_sheet = pd.read_excel(xls, sheet_name=s, header=None)
                m_row_idx = 13 if is_qms else 12
                w_row_idx = 14 if is_qms else 13
                start_row = w_row_idx + 2
                
                months_raw = df_sheet.iloc[m_row_idx].tolist() if m_row_idx < len(df_sheet) else []
                weeks_raw = df_sheet.iloc[w_row_idx].tolist() if w_row_idx < len(df_sheet) else []
                
                curr_m = ''
                col_info = {}
                for c in range(7, len(weeks_raw)):
                    if c < len(months_raw) and pd.notna(months_raw[c]):
                        m_str = str(months_raw[c]).strip()
                        if m_str != '' and m_str.lower() != 'nan':
                            curr_m = month_names.get(m_str, m_str[:10])
                    w_str = str(weeks_raw[c]).strip() if pd.notna(weeks_raw[c]) else f"W{c}"
                    col_info[c] = (w_str, curr_m)
                    
                for i in range(start_row, len(df_sheet)):
                    row = df_sheet.iloc[i]
                    sn = row[0]
                    if pd.isna(sn) or str(sn).strip() == '' or str(sn).lower() == 'nan': continue
                    if str(sn).strip() == 'Week Number': continue
                    
                    pct = row[5]
                    pct_str = f"{float(pct)*100:.0f}%" if pd.notna(pct) and float(pct)<=1 else f"{float(pct):.0f}%" if pd.notna(pct) else "N/A"
                    
                    completed_weeks = []
                    planned_events = []
                    for c in range(7, len(row)):
                        val = str(row[c]).strip().upper() if pd.notna(row[c]) else ''
                        if val in ['C', 'COMPLETED']:
                            w, m = col_info.get(c, ('?', ''))
                            completed_weeks.append(f"{w} ({m})" if m else w)
                        elif val in ['P', 'PLANNED', 'M', 'MOVED', 'L', 'OVERDUE']:
                            w, m = col_info.get(c, ('?', ''))
                            tag = "Overdue" if val in ['L', 'OVERDUE'] else ("Moved" if val in ['M', 'MOVED'] else "Planned")
                            planned_events.append((w, m, tag))
                            
                    if planned_events:
                        next_sched_val = f"📅 {planned_events[0][0]} • {planned_events[0][1]} ({planned_events[0][2]})"
                        status_tag = "Upcoming Scheduled"
                    elif completed_weeks:
                        next_sched_val = f"✅ Completed ({completed_weeks[-1]})"
                        status_tag = "Fully Completed"
                    else:
                        next_sched_val = "⏳ As Needed / Ad-hoc"
                        status_tag = "Routine"

                    entry = {
                        'S.N.': str(sn).strip(),
                        'Topic / Target Group': str(row[1]).strip() if pd.notna(row[1]) else ("General Quality" if is_qms else "Functional TBT"),
                        'Next Schedule': next_sched_val,
                        'Schedule Status': status_tag,
                        'Total Staff': row[2] if pd.notna(row[2]) else 0,
                        'Total Plan': row[3] if pd.notna(row[3]) else 0,
                        'Total Conducted': row[4] if pd.notna(row[4]) else 0,
                        '% Conducted': pct_str,
                        'Category': 'QMS Training' if is_qms else 'Functional / TBT'
                    }
                    if is_qms:
                        qms_rows.append(entry)
                    else:
                        func_rows.append(entry)
        except Exception as e:
            print(f"Notice: training data parser: {e}")
            
    df_qms = pd.DataFrame(qms_rows)
    df_func = pd.DataFrame(func_rows)
    return df_qms, df_func

@st.cache_data(ttl=300, show_spinner=False)
def get_lessons_learned_data():
    """Loads Diriyah Opera House Lessons Learned and Best Practices Register."""
    ll_df, bp_df = pd.DataFrame(), pd.DataFrame()
    ll_file = None
    for d in SEARCH_DIRS:
        if os.path.exists(d):
            for fn in os.listdir(d):
                if fn.startswith("~$") or fn.startswith("."): continue
                if "lesson" in fn.lower() and (fn.endswith(".xlsx") or fn.endswith(".xls")):
                    ll_file = os.path.join(d, fn)
                    break
        if ll_file: break
        
    if ll_file and os.path.exists(ll_file):
        try:
            xls = pd.ExcelFile(ll_file)
            for s in xls.sheet_names:
                if 'lesson' in s.lower():
                    df_raw = pd.read_excel(xls, sheet_name=s, header=None)
                    for i in range(len(df_raw)):
                        r = df_raw.iloc[i].dropna().tolist()
                        if any('Lesson Learned ID' in str(x) for x in r):
                            cols = [str(c).strip() for c in df_raw.iloc[i].tolist()]
                            clean = df_raw.iloc[i+1:].copy()
                            clean.columns = cols
                            ll_df = clean.dropna(subset=[cols[0]])
                            break
                elif 'best practice' in s.lower():
                    df_raw = pd.read_excel(xls, sheet_name=s, header=None)
                    for i in range(len(df_raw)):
                        r = df_raw.iloc[i].dropna().tolist()
                        if any('Best Practice ID' in str(x) for x in r):
                            cols = [str(c).strip() for c in df_raw.iloc[i].tolist()]
                            clean = df_raw.iloc[i+1:].copy()
                            clean.columns = cols
                            bp_df = clean.dropna(subset=[cols[0]])
                            break
        except Exception as e:
            print(f"Notice: lessons learned parser: {e}")
            
    return ll_df, bp_df

def get_kpi_summary_data(start_date=None, end_date=None):
    """
    Computes Executive QA/QC KPI Table for Engineering Submittals.
    Applies formula: Approved % = (Code A + Code B) / (Total - Under Review)
    Supports both Cumulative (all time) and Filtered Date Range / Monthly intervals.
    """
    # Locate ExportDocs
    target_fp = None
    for d in SEARCH_DIRS:
        if os.path.exists(d):
            for fn in os.listdir(d):
                if fn.startswith("~$") or fn.startswith("."): continue
                if fn.endswith(('.xlsx', '.xls')) and 'exportdocs' in fn.lower():
                    target_fp = os.path.join(d, fn)
                    break
        if target_fp: break
        
    if not target_fp or not os.path.exists(target_fp):
        return pd.DataFrame(), pd.DataFrame()

    try:
        df_raw = pd.read_excel(target_fp, skiprows=10, engine='calamine')
    except Exception:
        df_raw = pd.read_excel(target_fp, skiprows=10)

    # Deduplicate keeping latest
    df_clean = df_raw.drop_duplicates(subset=['Document No'], keep='last').copy()

    def classify_kpi_doc(r):
        doc = str(r.get('Document No', '')).upper()
        t = str(r.get('Type', '')).upper()
        title = str(r.get('Title', '')).upper()
        fn = str(r.get('File', '')).lower()
        
        if '-PLN-MN-' in doc or '-PLN-BM-' in doc or 'EXECUTION PLAN' in title or 'PEP' in title:
            return 'PEP'
        if '-PLN-QL-' in doc or 'QUALITY PLAN' in title or 'PQP' in title:
            return 'PQP'
        if '-PRO-QL-' in doc or 'QUALITY PROCEDURE' in title or 'QA/QC PROCEDURE' in title:
            return 'QA/QC Procedures'
        if '-MTS-' in doc or 'METHOD STATEMENT' in t:
            return 'MTS'
        if '-ITP-' in doc or ('INSPECTION' in t and 'TEST PLAN' in t):
            return 'ITP'
        if '-MAT-' in doc or 'MATERIAL APPROVAL' in t:
            return 'MAR'
        if '-PQQ-' in doc or 'PREQUALIFICATION' in t:
            return 'PQD'
        if ('-SDW-' in doc or 'SHOP DRAWING' in t) and (fn.endswith('.pdf') or doc.endswith('_PDF')):
            return 'SDW'
        return None

    df_clean['KPI_Category'] = df_clean.apply(classify_kpi_doc, axis=1)
    df_kpi = df_clean[df_clean['KPI_Category'].notna()].copy()

    def map_kpi_status(row):
        s = f"{row.get('Status', '')} {row.get('Review Status', '')}".lower()
        if 'approved with comments' in s or 'b-approved' in s: return 'Code B'
        if 'approved' in s and 'comments' not in s: return 'Code A'
        if 'revise' in s or 'resubmit' in s: return 'Code C'
        if 'reject' in s: return 'Code D'
        if any(x in s for x in ['for review', 'for approval', 'in progress', 'under review']): return 'Under Review'
        return 'Other'

    df_kpi['Code'] = df_kpi.apply(map_kpi_status, axis=1)
    if 'Date Modified' in df_kpi.columns:
        df_kpi['Date'] = pd.to_datetime(df_kpi['Date Modified'].combine_first(df_kpi.get('Revision Date')), errors='coerce')
    else:
        df_kpi['Date'] = pd.to_datetime(df_kpi.get('Revision Date'), errors='coerce')

    kpi_categories_order = [
        'PEP', 'PQP', 'QA/QC Procedures', 'MTS', 'ITP', 'MAR', 'PQD', 'SDW'
    ]

    def build_summary_table(target_subset):
        rows = []
        for cat in kpi_categories_order:
            sub = target_subset[target_subset['KPI_Category'] == cat]
            tot = len(sub)
            a = (sub['Code'] == 'Code A').sum()
            b = (sub['Code'] == 'Code B').sum()
            c = (sub['Code'] == 'Code C').sum()
            d = (sub['Code'] == 'Code D').sum()
            ur = (sub['Code'] == 'Under Review').sum()
            decided = tot - ur
            appr_pct = ((a + b) / decided * 100) if decided > 0 else 0.0
            
            rows.append({
                'KPI Category': cat,
                'Total': tot,
                'Code A': a,
                'Code B': b,
                'Code C': c,
                'Code D': d,
                'Under Review': ur,
                'Approved % (A & B)': f"{appr_pct:.0f}%",
                '_rate_num': appr_pct
            })
        return pd.DataFrame(rows)

    cum_table = build_summary_table(df_kpi)

    # Filtered / Monthly table
    if start_date is not None and end_date is not None:
        s_dt = pd.to_datetime(start_date)
        e_dt = pd.to_datetime(end_date)
        period_subset = df_kpi[(df_kpi['Date'] >= s_dt) & (df_kpi['Date'] <= e_dt)]
        period_table = build_summary_table(period_subset)
    else:
        period_table = cum_table.copy()

    return cum_table, period_table
