import asyncio
import re
import os
from playwright.async_api import async_playwright
from db import register_lead

TARGET_URL = "https://www.avito.ma/fr/maroc/voitures-%C3%A0_vendre?price_min=10000"
VISITED_FILE = "scraped_urls.txt"

def load_visited():
    if os.path.exists(VISITED_FILE):
        with open(VISITED_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_visited(url):
    with open(VISITED_FILE, "a") as f:
        f.write(url + "\n")

async def scrape():
    visited = load_visited()
    successful_scrapes = 0
    target_scrapes = 10
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # --- SPEED OPTIMIZATION ---
        # Allow stylesheets so layout doesn't break, but block heavy media
        await page.route("**/*", lambda route: route.abort() 
            if route.request.resource_type in ["image", "font", "media"] 
            else route.continue_())

        await page.goto(TARGET_URL, timeout=60000)
        await page.wait_for_selector("a[href*='voitures_d_occasion']", timeout=30000) 

        links = await page.locator("a[href*='voitures_d_occasion']").all()
        urls = [await l.get_attribute("href") for l in links]

        for url in urls:
            if url in visited:
                continue # Skip already processed URLs
                
            if successful_scrapes >= target_scrapes:
                print("🎯 Reached target of 10 successful scrapes!")
                break
                
            try:
                await page.goto(url)
                await page.wait_for_load_state("domcontentloaded")
                
                title = await page.locator("h1").text_content()
                body_text = await page.locator("body").text_content()
                
                # --- SMARTER PRICE LOGIC ---
                # A page might have "500 DH frais" and "150 000 DH prix". 
                # We extract ALL prices and take the maximum one.
                all_prices_text = re.findall(r"(\d[\d\s,.]*)\s*(?:DH|MAD)", body_text, re.IGNORECASE)
                prices = []
                for pt in all_prices_text:
                    try:
                        clean_num = int(re.sub(r"\D", "", pt))
                        prices.append(clean_num)
                    except:
                        pass
                
                price = max(prices) if prices else 0

                # Quality Control
                if price < 10000:
                    print(f"⏭️ Skipping {title} - Max price found was only {price} DH. Likely unlisted.")
                    # We save it so we don't keep trying to scrape this useless ad
                    save_visited(url)
                    visited.add(url)
                    continue

                # Year Extraction
                year_match = re.search(r"(?:Année-Modèle|Modèle|Année)[\s\S]{0,20}?(199\d|20[0-2]\d)", body_text, re.IGNORECASE)
                if not year_match:
                    year_match = re.search(r"\b(199\d|20[0-2]\d)\b", body_text)
                specs = {'year': int(year_match.group(1))} if year_match else {}

                # Click Phone Button
                btn = page.get_by_role("button", name="Afficher le numéro")
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    
                    phone_el = page.locator("a[href^='tel:']")
                    if await phone_el.count() > 0:
                        phone = await phone_el.inner_text()
                        register_lead(phone, title, price, specs)
                        
                        # Mark as successful
                        save_visited(url)
                        visited.add(url)
                        successful_scrapes += 1
                        print(f"✅ Successfully scraped {title} ({price} DH) [{successful_scrapes}/{target_scrapes}]")

            except Exception as e:
                print(f"⚠️ Failed on {url}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
