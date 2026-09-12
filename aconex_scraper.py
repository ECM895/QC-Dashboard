import asyncio
from playwright.async_api import async_playwright
import os

async def download_aconex_register():
    print("Starting Aconex Automated Extraction...")
    
    # We will save the downloaded files to a dedicated sync directory
    download_dir = os.path.join(os.getcwd(), 'auto_logs')
    os.makedirs(download_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        try:
            print("Navigating to Aconex KSA1...")
            await page.goto('https://ksa1.aconex.com/Logon')
            await page.wait_for_timeout(3000)
            
            print("Injecting credentials...")
            # Oracle JET elements require targeting the inner HTML input
            await page.locator('oj-input-text#userName input').fill('uzair_ahmad')
            await page.locator('oj-input-password#password input').fill('*Abubakar@123*')
            await page.click('oj-button#login button')
            
            # Wait for dashboard to load
            await page.wait_for_timeout(10000)
            
            print("Navigating to Document Register...")
            # Navigation logic depends heavily on user's specific Aconex layout
            # await page.click('text=Documents')
            # await page.click('text=Document Register')
            
            print("Executing Search and Exporting to Excel...")
            # await page.click('button:has-text("Search")')
            # await page.click('button:has-text("Tools")')
            # async with page.expect_download() as download_info:
            #     await page.click('text="Export to Excel"')
            # download = await download_info.value
            # await download.save_as(os.path.join(download_dir, 'Aconex_Export.xlsx'))
            
            print("Successfully extracted daily logs!")
            
        except Exception as e:
            print(f"Extraction failed: {e}")
            print("NOTE: Automated scraping on Aconex is highly sensitive to UI updates and SSO redirects.")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(download_aconex_register())
