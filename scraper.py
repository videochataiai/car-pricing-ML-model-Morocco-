import asyncio
import re
from playwright.async_api import async_playwright
from db import register_lead

TARGET_URL = "https://www.avito.ma/fr/maroc/voitures"

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Visible for debugging
        page = await browser.new_page()
        
        await page.goto(TARGET_URL, timeout=60000)
        await page.wait_for_selector("div.sc-1nre5ec-0") # List container

        # Grab links
        links = await page.locator("a.sc-1jge648-0").all()
        urls = [await l.get_attribute("href") for l in links]

        for url in urls[:5]: # Batch size 5
            try:
                await page.goto(url)
                await page.wait_for_load_state("domcontentloaded")
                
                # 1. Extract Data
                title = await page.locator("h1").inner_text()
                
                # Price logic
                try:
                    price_text = await page.locator("p.sc-1x0vz2r-0.lnEFFR").inner_text()
                    price = int(re.sub(r"\D", "", price_text)) # Remove non-digits
                except:
                    price = 0 

                # Year Extraction
                specs_text = await page.locator("div.sc-6p5md9-0").inner_text()
                year_match = re.search(r"\b(199\d|20[0-2]\d)\b", specs_text)
                specs = {'year': int(year_match.group(0))} if year_match else {}

                # 2. Click Phone Button (The Risky Part)
                btn = page.get_by_role("button", name="Afficher le numéro")
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    
                    # Extract from the new element (usually an anchor tag with tel:)
                    phone_el = page.locator("a[href^='tel:']")
                    if await phone_el.count() > 0:
                        phone = await phone_el.inner_text()
                        
                        # 3. Send to Database
                        register_lead(phone, title, price, specs)

            except Exception as e:
                print(f"Skip {url}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
