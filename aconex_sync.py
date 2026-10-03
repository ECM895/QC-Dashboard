import asyncio
from playwright.async_api import async_playwright
import os
import sys
import time
import shutil

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_logs')

async def sync_aconex():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    username = os.environ.get('ACONEX_USER', 'uzair_ahmad@cscec6bcd.cn')
    password = os.environ.get('ACONEX_PASSWORD', '*Ayisha@123*')

    print("=" * 60)
    print("STARTING LIVE ACONEX SYNC FOR PROJECT 105 (OPERA HOUSE)")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
            accept_downloads=True
        )
        page = await context.new_page()

        aconex_page = None
        try:
            print("1. Navigating to Oracle Lobby Login...")
            await page.goto("https://constructionandengineering.oraclecloud.com/idcsLogin")

            print(f"2. Submitting username: {username}...")
            user_input = page.locator('input[autocomplete="username"], input[placeholder*="user@company.com"]').first
            await user_input.wait_for(state="visible", timeout=30000)
            await user_input.fill(username)
            await page.keyboard.press("Enter")

            await asyncio.sleep(4)
            print("3. Submitting password...")
            pwd_input = page.locator('input[type="password"]').first
            await pwd_input.wait_for(state="visible", timeout=30000)
            await pwd_input.fill(password)
            await page.keyboard.press("Enter")

            print("4. Waiting for Lobby to load projects...")
            await page.wait_for_selector("text=DG Phase 2", timeout=45000)
            print("Found DG Phase 2 project card.")

            print("5. Launching DG Phase 2 in Aconex...")
            async with context.expect_page() as new_page_info:
                await page.click("text=DG Phase 2")
            aconex_page = await new_page_info.value
            await aconex_page.wait_for_load_state("networkidle")
            print("Aconex Hub Loaded! URL:", aconex_page.url)

            print("6. Navigating to Document Register...")
            docs_btn = aconex_page.locator('button:has-text("Documents"), a:has-text("Documents"), [id*="nav-bar-DOC"]').first
            await docs_btn.click()
            await asyncio.sleep(1)
            await aconex_page.click('#nav-bar-DOC-DOC-SEARCH')

            print("Waiting for Document Register frame...")
            await asyncio.sleep(6)

            main_frame = None
            for f in aconex_page.frames:
                if "SearchControlledDoc" in f.url:
                    main_frame = f
                    break

            if not main_frame:
                raise Exception("Main Document Register frame (SearchControlledDoc) not found!")

            print("7. Opening Reports dropdown...")
            reports_btn = main_frame.locator('button:has-text("Reports")').first
            await reports_btn.click()
            await asyncio.sleep(1.5)

            print("8. Triggering 'Export to Excel' download...")
            export_link = main_frame.locator('a:has-text("Export to Excel"), text="Export to Excel"').first
            
            timestamp = time.strftime("%Y%m%d_%H-%M")
            target_filename = f"ExportDocs-{timestamp}.xlsx"
            target_path = os.path.join(DOWNLOAD_DIR, target_filename)

            async with aconex_page.expect_download(timeout=180000) as download_info:
                # Force click if needed or dispatch event
                try:
                    await export_link.click(timeout=5000)
                except:
                    print("Direct click timed out, evaluating exportXLS() in frame...")
                    await main_frame.evaluate("exportXLS()")

            download = await download_info.value
            await download.save_as(target_path)
            print(f"9. SUCCESS! Export downloaded and saved to: {target_path}")

            latest_path = os.path.join(DOWNLOAD_DIR, "ExportDocs_latest.xlsx")
            if os.path.exists(latest_path):
                try:
                    os.remove(latest_path)
                except:
                    pass
            shutil.copy2(target_path, latest_path)
            print(f"Updated latest master copy at: {latest_path}")

            print("=" * 60)
            print("ACONEX SYNC COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            return target_path

        except Exception as e:
            print(f"ERROR during Aconex Sync: {e}")
            if aconex_page:
                try:
                    await aconex_page.screenshot(path="aconex_sync_error.png")
                except:
                    pass
            else:
                await page.screenshot(path="aconex_sync_error.png")
            raise e
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(sync_aconex())
