import asyncio
from playwright.async_api import async_playwright
import os
import time

DOWNLOAD_DIR = os.path.join(os.getcwd(), 'auto_logs')

async def extract_log(page, doc_type):
    print(f"\n--- Extracting {doc_type} ---")
    
    # 1. Clear filters
    print("Clearing filters...")
    try:
        await page.click('text="Clear all filters"')
        await page.wait_for_timeout(2000)
    except:
        pass
        
    # 2. Fill Type
    print(f"Setting Type to: {doc_type}")
    # The exact selector for "Type" is tricky. Let's find the input near the label "Type"
    # Aconex uses complex inputs, but we can try clicking the field and typing
    # In the screenshot, Type is a tokenized input box. 
    try:
        # Try to click the input field for Type
        # Usually it's next to the label 'Type'
        type_input = page.locator('label:has-text("Type")').locator('..').locator('input').first
        await type_input.fill(doc_type)
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(1000)
    except Exception as e:
        print(f"Failed to set Type: {e}")
        return False
        
    # 3. Click Search
    print("Clicking Search...")
    try:
        await page.click('button:has-text("Search")')
        await page.wait_for_timeout(5000) # Wait for results to load
    except Exception as e:
        print(f"Failed to search: {e}")
        return False
        
    # 4. Export to Excel
    print("Exporting...")
    try:
        await page.click('button:has-text("Reports")')
        await page.wait_for_timeout(1000)
        
        async with page.expect_download(timeout=60000) as download_info:
            await page.click('text="Export to Excel"')
        download = await download_info.value
        
        file_path = os.path.join(DOWNLOAD_DIR, f"{doc_type.replace(' ', '_')}_{int(time.time())}.xlsx")
        await download.save_as(file_path)
        print(f"Saved to {file_path}")
        return True
    except Exception as e:
        print(f"Failed to export: {e}")
        return False

async def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Clean old logs
    for f in os.listdir(DOWNLOAD_DIR):
        os.remove(os.path.join(DOWNLOAD_DIR, f))
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        try:
            print("Logging in...")
            await page.goto('https://ksa1.aconex.com/Logon')
            await page.wait_for_timeout(3000)
            
            await page.click('#userName')
            await page.keyboard.type('uzair_ahmad')
            
            await page.click('#password')
            await page.keyboard.type('*Abubakar@123*')
            
            await page.click('#login')
            await page.wait_for_timeout(10000)
            
            print("Navigating to Document Register...")
            # Click Documents -> Document Register
            await page.click('text="Documents"')
            await page.wait_for_timeout(1000)
            await page.click('text="Document Register"')
            await page.wait_for_timeout(5000)
            
            # Map exact Aconex types to their standard Dashboard abbreviations
            types_to_extract = {
                "Work Inspection Request": "WIR",
                "Material Inspection Request": "MIR",
                "Material Approval Request": "MAR", 
                "Method Statement": "MST",
                "Inspection and Test Plan": "ITP",
                "Shop Drawing": "SHD",
                "Non Conformance Report": "NCR"
            }
            
            for doc_type, abbreviation in types_to_extract.items():
                print(f"\n--- Extracting {doc_type} ({abbreviation}) ---")
                
                # 1. Clear filters
                print("Clearing filters...")
                try:
                    await page.click('text="Clear all filters"')
                    await page.wait_for_timeout(2000)
                except:
                    pass
                    
                # 2. Fill Type
                print(f"Setting Type to: {doc_type}")
                try:
                    type_input = page.locator('label:has-text("Type")').locator('..').locator('input').first
                    await type_input.fill(doc_type)
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"Failed to set Type: {e}")
                    continue
                    
                # 3. Click Search
                print("Clicking Search...")
                try:
                    await page.click('button:has-text("Search")')
                    await page.wait_for_timeout(5000) # Wait for results
                except Exception as e:
                    print(f"Failed to search: {e}")
                    continue
                    
                # 4. Export to Excel
                print("Exporting...")
                try:
                    await page.click('button:has-text("Reports")')
                    await page.wait_for_timeout(1000)
                    
                    async with page.expect_download(timeout=60000) as download_info:
                        await page.click('text="Export to Excel"')
                    download = await download_info.value
                    
                    # Prefix the filename with the abbreviation (e.g. WIR_xxx.xlsx)
                    # This ensures data_handler.py perfectly categorizes the file.
                    file_path = os.path.join(DOWNLOAD_DIR, f"{abbreviation}_{doc_type.replace(' ', '_')}_{int(time.time())}.xlsx")
                    await download.save_as(file_path)
                    print(f"Saved to {file_path}")
                except Exception as e:
                    print(f"Failed to export: {e}")
                
        except Exception as e:
            print(f"Critical error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
