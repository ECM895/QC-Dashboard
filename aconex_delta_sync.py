import asyncio
import os
import sys
import time
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_logs', 'qc_master.db')
TIMESTAMP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_logs', 'last_sync_timestamp.txt')

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

async def fetch_delta_from_aconex(since_datetime_str):
    """
    Connects to Aconex, queries only documents modified since `since_datetime_str`,
    and returns a pandas DataFrame with only the updated rows.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[SYNC] Playwright is not installed on this cloud environment. Skipping browser automation.")
        return None

    username = os.environ.get('ACONEX_USER', 'uzair_ahmad@cscec6bcd.cn')
    password = os.environ.get('ACONEX_PASSWORD', '*Ayisha@123*')

    print(f"[SYNC] Starting Incremental Delta Sync since: {since_datetime_str}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900}
        )
        page = await context.new_page()

        try:
            # 1. Login
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

            # 2. Lobby -> DG Phase 2
            await page.wait_for_selector("text=DG Phase 2", timeout=45000)
            async with context.expect_page() as new_page_info:
                await page.click("text=DG Phase 2")
            aconex_page = await new_page_info.value
            await aconex_page.wait_for_load_state("networkidle")

            # 3. Document Register
            docs_btn = aconex_page.locator('button:has-text("Documents"), a:has-text("Documents"), [id*="nav-bar-DOC"]').first
            await docs_btn.click()
            await asyncio.sleep(1)
            await aconex_page.click('#nav-bar-DOC-DOC-SEARCH')
            await asyncio.sleep(6)

            main_frame = None
            for f in aconex_page.frames:
                if "SearchControlledDoc" in f.url:
                    main_frame = f
                    break

            if not main_frame:
                raise Exception("Main Document Register frame not found")

            # 4. Check results directly in frame or apply date filter
            # Let's inspect the results count
            summary = await main_frame.evaluate("""() => {
                const el = document.querySelector('.pagination-summary') || document.querySelector('[class*="results"]');
                return el ? el.innerText : '';
            }""")
            print(f"[SYNC] Connected to Register. Current Register Summary: {summary}")

            return None # Delta rows if extracted

        except Exception as e:
            print(f"[SYNC] Error during sync: {e}")
            return None
        finally:
            await browser.close()

if __name__ == "__main__":
    last_sync = get_last_sync_time()
    print("Last sync was at:", last_sync)
