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
    current_page = 1
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # --- SPEED OPTIMIZATION ---
        await page.route("**/*", lambda route: route.abort() 
            if route.request.resource_type in ["image", "font", "media"] 
            else route.continue_())

        while successful_scrapes < target_scrapes:
            # Construct URL with pagination
            page_url = f"{TARGET_URL}&o={current_page}" if current_page > 1 else TARGET_URL
            print(f"\n--- 📄 Scraping Page {current_page} ---")
            
            try:
                await page.goto(page_url, timeout=60000)
                await page.wait_for_selector("a[href*='voitures_d_occasion']", timeout=30000) 
            except Exception as e:
                print(f"❌ Error loading page {current_page}: {e}")
                break

            links = await page.locator("a[href*='voitures_d_occasion']").all()
            urls = []
            for l in links:
                href = await l.get_attribute("href")
                if href:
                    # Force absolute URL
                    full_url = href if href.startswith("http") else f"https://www.avito.ma{href}"
                    urls.append(full_url)

            if not urls:
                print("No more car links found. Stopping.")
                break

            for url in urls:
                if url in visited:
                    continue 
                    
                if successful_scrapes >= target_scrapes:
                    break
                    
                try:
                    await page.goto(url)
                    await page.wait_for_load_state("domcontentloaded")
                    
                    # 1. Extract Data
                    title = await page.locator("h1").text_content()
                    body_text = await page.locator("body").text_content()
                    
                    # --- SMARTER PRICE LOGIC ---
                    all_prices_text = re.findall(r"(\d[\d\s,.]*)\s*(?:DH|MAD)", body_text, re.IGNORECASE)
                    prices = []
                    for pt in all_prices_text:
                        try:
                            clean_num = int(re.sub(r"\D", "", pt))
                            prices.append(clean_num)
                        except: pass
                    
                    price = max(prices) if prices else 0

                    if price < 10000:
                        print(f"⏭️ Skipping {title} - Max price {price} DH (Too low/Unlisted)")
                        save_visited(url)
                        visited.add(url)
                        continue

                    # Year Extraction
                    year_match = re.search(r"(?:Année-Modèle|Modèle|Année)[\s\S]{0,20}?(199\d|20[0-2]\d)", body_text, re.IGNORECASE)
                    if not year_match:
                        year_match = re.search(r"\b(199\d|20[0-2]\d)\b", body_text)
                    specs = {'year': int(year_match.group(1))} if year_match else {}

                    # 2. Click Phone Button
                    btn = page.get_by_role("button", name="Afficher le numéro")
                    if await btn.count() > 0:
                        await btn.click()
                        await page.wait_for_timeout(1000)
                        
                        phone_el = page.locator("a[href^='tel:']")
                        if await phone_el.count() > 0:
                            phone = await phone_el.inner_text()
                            
                            # 3. Save to Database
                            register_lead(phone, title, price, specs)
                            
                            save_visited(url)
                            visited.add(url)
                            successful_scrapes += 1
                            print(f"✅ [{successful_scrapes}/{target_scrapes}] Saved: {title} ({price} DH)")

                except Exception as e:
                    print(f"⚠️ Failed on {url}: {e}")

            current_page += 1
            if current_page > 10: # Safety cap
                print("Safety cap reached (Page 10). Stopping.")
                break

        await browser.close()
        if successful_scrapes > 0:
            print(f"\n🏁 Finished! Recorded {successful_scrapes} new leads today.")
        else:
            print("\n🏁 Finished! No new leads found.")

if __name__ == "__main__":
    asyncio.run(scrape())
