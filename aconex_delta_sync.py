import asyncio
import os
import sys
import time
import sqlite3
from datetime import datetime
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_logs', 'qc_master.db')
TIMESTAMP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_logs', 'last_sync_timestamp.txt')
EXPORT_EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_logs', 'ExportDocs.xlsx')

def get_last_sync_time():
    """Returns the most recent Date Modified from SQLite or timestamp file."""
    if os.path.exists(TIMESTAMP_FILE):
        try:
            with open(TIMESTAMP_FILE, 'r') as f:
                ts = f.read().strip()
                if ts: return ts
        except:
            pass

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute('SELECT MAX("Date Modified") FROM documents').fetchone()
            conn.close()
            if row and row[0]:
                return str(row[0])[:19]
        except:
            pass
    return "2026-10-01 00:00:00"

def save_last_sync_time(ts):
    with open(TIMESTAMP_FILE, 'w') as f:
        f.write(str(ts))

def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d 00:00:00")
    except:
        return date_str

async def scrape_aconex_screen(cutoff_date_str=None):
    """
    Connects to Aconex Document Register, sorts descending by Date Modified,
    and extracts all newest documents directly from the screen table without downloading.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[SYNC] Playwright is not installed on this cloud environment. Skipping browser automation.")
        return []

    if cutoff_date_str is None:
        cutoff_date_str = get_last_sync_time()[:10]

    username = os.environ.get('ACONEX_USER', 'uzair_ahmad@cscec6bcd.cn')
    password = os.environ.get('ACONEX_PASSWORD', '*Ayisha@123*')

    print(f"[SYNC] Starting Fast Screen-Read Sync (cutoff: {cutoff_date_str})...")

    all_scraped_docs = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()

        try:
            print("[SYNC] 1. Logging into Aconex...")
            await page.goto("https://constructionandengineering.oraclecloud.com/idcsLogin")
            user_input = page.locator('input[autocomplete="username"], input[placeholder*="user@company.com"]').first
            await user_input.wait_for(state="visible", timeout=30000)
            await user_input.fill(username)
            await page.keyboard.press("Enter")
            await asyncio.sleep(4)
            pwd_input = page.locator('input[type="password"]').first
            await pwd_input.wait_for(state="visible", timeout=30000)
            await pwd_input.fill(password)
            await page.keyboard.press("Enter")

            print("[SYNC] 2. Entering DG Phase 2...")
            await page.wait_for_selector("text=DG Phase 2", timeout=45000)
            async with context.expect_page() as new_page_info:
                await page.click("text=DG Phase 2")
            aconex_page = await new_page_info.value
            await asyncio.sleep(6)

            print("[SYNC] 3. Navigating to Document Register...")
            docs_btn = aconex_page.locator('button:has-text("Documents"), a:has-text("Documents"), [id*="nav-bar-DOC"]').first
            await docs_btn.click()
            await asyncio.sleep(1.5)
            await aconex_page.click('#nav-bar-DOC-DOC-SEARCH')
            await asyncio.sleep(6)

            frame = aconex_page.frame(name="main")
            if not frame:
                for f in aconex_page.frames:
                    if "SearchControlledDoc" in f.url:
                        frame = f
                        break
            if not frame:
                raise Exception("main frame not found")

            print("[SYNC] 4. Clearing search inputs and default filters...")
            await frame.evaluate("""() => {
                for (const i of document.querySelectorAll('input')) {
                    if (i.value === '*' || i.value === 'BV*') {
                        i.value = '';
                        i.dispatchEvent(new Event('input', { bubbles: true }));
                        i.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
                const closeButtons = document.querySelectorAll('.ui-select-match-close, a.select2-search-choice-close, .close');
                for (const b of closeButtons) {
                    if (b.parentElement && b.parentElement.innerText.includes('Prequalification Submittal')) {
                        b.click();
                    }
                }
            }""")
            await asyncio.sleep(2)

            print("[SYNC] 5. Triggering Search...")
            btn = frame.locator('#searchButton').first
            await btn.click()
            await asyncio.sleep(8)

            print("[SYNC] 6. Sorting by Date Modified DESC...")
            hdr_locator = frame.locator('.ag-header-cell[col-id="registered"]').first
            if await hdr_locator.count() == 0:
                hdr_locator = frame.locator('.ag-header-cell:has-text("Date Modified")').first
            await hdr_locator.click()
            await asyncio.sleep(6)

            async def grab_current_page():
                return await frame.evaluate("""() => {
                    const rowMap = {};
                    const cells = Array.from(document.querySelectorAll('[role="gridcell"]'));
                    for (const c of cells) {
                        const row = c.closest('.ag-row');
                        if (!row) continue;
                        const rIdx = row.getAttribute('row-index');
                        if (rIdx === null) continue;
                        rowMap[rIdx] = rowMap[rIdx] || {};
                        const colId = c.getAttribute('col-id');
                        const txt = c.innerText.trim();
                        if (colId) {
                            rowMap[rIdx][colId] = txt;
                        }
                    }
                    const indices = Object.keys(rowMap).map(Number).sort((a,b) => a - b);
                    return indices.map(i => rowMap[i]).filter(r => r.docno);
                }""")

            docs_first = await grab_current_page()
            if docs_first and (docs_first[0].get('registered', '').endswith('2024') or docs_first[0].get('registered', '').endswith('2025')):
                print("[SYNC] Ascending sort detected. Re-clicking header for descending...")
                await hdr_locator.click()
                await asyncio.sleep(6)

            # Scrape pages
            for page_num in range(1, 15):
                print(f"[SYNC] Reading Page {page_num} directly from screen...")
                docs = await grab_current_page()
                print(f"[SYNC] Page {page_num} yielded {len(docs)} documents.")
                
                reached_older = False
                for d in docs:
                    docno = d.get('docno')
                    reg_date = d.get('registered')
                    parsed_reg = parse_date(reg_date)
                    if docno:
                        all_scraped_docs[docno] = {
                            'Document No': docno,
                            'Revision': d.get('revision', ''),
                            'Title': d.get('title', ''),
                            'Type': d.get('doctype', ''),
                            'Status': d.get('docstatus', ''),
                            'Discipline': d.get('discipline', ''),
                            'Revision Date': parse_date(d.get('revisiondate', '')),
                            'Date Modified': parsed_reg
                        }
                    if parsed_reg and parsed_reg < cutoff_date_str:
                        reached_older = True

                if reached_older:
                    print(f"[SYNC] Reached records prior to {cutoff_date_str}. Complete!")
                    break

                next_btn = frame.locator('button.auiPagination-next.enabled')
                if await next_btn.count() > 0:
                    await next_btn.first.click()
                    await asyncio.sleep(5)
                else:
                    break

            print(f"[SYNC] Successfully captured {len(all_scraped_docs)} documents directly from screen.")

        except Exception as e:
            print(f"[SYNC ERROR]: {e}")
        finally:
            await browser.close()

    return list(all_scraped_docs.values())

def upsert_delta_to_db(docs):
    """Upserts captured document rows into SQLite qc_master.db and syncs ExportDocs.xlsx."""
    if not docs:
        print("[DB] No new documents to upsert.")
        return 0

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    upserted = 0
    max_date = None
    for d in docs:
        docno = d['Document No']
        cursor.execute('SELECT [Document No] FROM documents WHERE [Document No] = ?', (docno,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE documents
                SET [Revision] = ?, [Title] = ?, [Type] = ?, [Status] = ?, [Discipline] = ?, [Revision Date] = ?, [Date Modified] = ?
                WHERE [Document No] = ?
            ''', (d['Revision'], d['Title'], d['Type'], d['Status'], d['Discipline'], d['Revision Date'], d['Date Modified'], docno))
        else:
            cursor.execute('''
                INSERT INTO documents ([Document No], [Revision], [Title], [Type], [Status], [Discipline], [Revision Date], [Date Modified])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (docno, d['Revision'], d['Title'], d['Type'], d['Status'], d['Discipline'], d['Revision Date'], d['Date Modified']))
        upserted += 1
        if d['Date Modified']:
            if max_date is None or d['Date Modified'] > max_date:
                max_date = d['Date Modified']

    conn.commit()
    
    # Export to ExportDocs.xlsx so Excel-based workflows and Streamlit caches refresh instantly
    print("[DB] Refreshing ExportDocs.xlsx...")
    df_all = pd.read_sql_query('SELECT * FROM documents', conn)
    conn.close()
    
    df_all.to_excel(EXPORT_EXCEL_PATH, index=False)
    if max_date:
        save_last_sync_time(max_date)

    print(f"[DB] Upserted {upserted} documents. Total master records: {len(df_all)}.")
    return upserted

def ensure_playwright_installed():
    """Ensures playwright python package and chromium binaries are installed on cloud."""
    try:
        import playwright
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "playwright"], check=True)
    
    # Check if chromium browser is installed or install it
    import subprocess
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, timeout=120)
    except Exception as e:
        pass

def sync_from_aconex_screen(cutoff_date_str=None):
    """Convenience synchronous wrapper to run fast screen sync."""
    ensure_playwright_installed()
    docs = asyncio.run(scrape_aconex_screen(cutoff_date_str=cutoff_date_str))
    return upsert_delta_to_db(docs)

# Backward-compatible alias
fetch_delta_from_aconex = sync_from_aconex_screen


if __name__ == "__main__":
    sync_from_aconex_screen()


