import asyncio
from playwright.async_api import async_playwright
import re

async def test_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Specific ad from user error
        url = "https://www.avito.ma/fr/zerhounia/voitures_d_occasion/MERCEDES_C220_M12_2014_D2020_56387968.htm"
        await page.goto(url, timeout=60000)
        
        body_text = await page.locator("body").inner_text()
        
        # Test Price extraction
        price_match = re.search(r"([\d\s,]+)\s*(DH|MAD)", body_text, re.IGNORECASE)
        print("Price Match:", price_match.group(1).strip() if price_match else "None")
        
        # Test Year extraction
        # Let's look for "Modele", "Annee", or just typical list patterns
        year_match = re.search(r"(?:Annee-Modele|Modele|Annee)[\s\S]{0,20}?(199\d|20[0-2]\d)", body_text, re.IGNORECASE)
        if not year_match:
            # Fallback, just look for 20xx near other car specs
            year_match = re.search(r"\b(199\d|20[0-2]\d)\b", body_text)
            
        print("Year Match:", year_match.group(1) if year_match else "None")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scrape())
