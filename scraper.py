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
            print(f"\n--- Scraping Page {current_page} ---", flush=True)
            
            try:
                await page.goto(page_url, timeout=60000)
                # Wait for the listing to actually render
                await page.wait_for_selector("a[href*='/voitures_d_occasion/']", timeout=30000)
                
                # Scroll down a bit to trigger any lazy-loading of links
                await page.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"Error loading page {current_page}: {e}", flush=True)
                break

            # Find all links that look like car ads
            links = await page.locator("a[href*='/voitures_d_occasion/']").all()
            
            urls = []
            for l in links:
                href = await l.get_attribute("href")
                if href and "/voitures_d_occasion/" in href:
                    # Force absolute URL
                    full_url = href if href.startswith("http") else f"https://www.avito.ma{href}"
                    if full_url not in urls:
                        urls.append(full_url)

            print(f"Found {len(urls)} potential car ads on this page.", flush=True)

            if not urls:
                print("No more car links found on this page. Stopping.", flush=True)
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
                    title_el = page.locator("h1")
                    title = await title_el.text_content() if await title_el.count() > 0 else "Unknown Title"
                    print(f"   Scanning: {title[:50]}...", flush=True)

                    body_text = await page.locator("body").text_content()
                    
                    # --- PRICE EXTRACTION (Smarter) ---
                    price = 0
                    # Primary check: Bold price elements
                    price_els = page.locator("p:has-text('DH')")
                    for i in range(await price_els.count()):
                        txt = await price_els.nth(i).text_content()
                        if txt and "Ref" not in txt and "Annonce" not in txt:
                            match = re.search(r"(\d[\d\s,.]*)\s*(?:DH|MAD)", txt, re.IGNORECASE)
                            if match:
                                val = int(re.sub(r"\D", "", match.group(1)))
                                if 10000 < val < 2000000: # Tighten range to ignore IDs
                                    price = val
                                    break
                    
                    if price == 0: 
                        # Fallback: Extract from body but ignore the footer/reference area
                        head_text = body_text[:2000] # Usually prices are at the top
                        all_prices_text = re.findall(r"(\d[\d\s,.]*)\s*(?:DH|MAD)", head_text, re.IGNORECASE)
                        valid_prices = []
                        for pt in all_prices_text:
                            try:
                                val = int(re.sub(r"\D", "", pt))
                                if 10000 < val < 2000000: valid_prices.append(val)
                            except: pass
                        price = max(valid_prices) if valid_prices else 0

                    # --- SPECS EXTRACTION ---
                    year_match = re.search(r"(?:Annee-Modele|Modele|Annee)[\s\S]{0,20}?(199\d|20[0-2]\d)", body_text, re.IGNORECASE)
                    if not year_match:
                        year_match = re.search(r"\b(199\d|20[0-2]\d)\b", body_text)
                    specs = {}
                    if year_match:
                        specs['year'] = int(year_match.group(1) if year_match.groups() else year_match.group(0))
                    
                    mileage_match = re.search(r"(\d[\d\s,.]*)\s*(?:km|kilometrage)", body_text, re.IGNORECASE)
                    if mileage_match:
                        try:
                            specs['mileage'] = int(re.sub(r"\D", "", mileage_match.group(1)))
                        except: pass

                    print(f"      Extracted: Price={price} DH | Specs={specs}", flush=True)

                    if price < 10000:
                        print(f"      Skipping - Price too low or unlisted.", flush=True)
                        save_visited(url)
                        visited.add(url)
                        continue

                    # 2. Click Phone Button (Fixed Strict Mode)
                    btn = page.locator("[data-testid='ShowPhoneCTA']").first
                    if await btn.count() == 0:
                        btn = page.get_by_role("button", name=re.compile(r"numero|Contacter|Appeler", re.I)).first

                    if await btn.count() > 0:
                        await btn.click()
                        await page.wait_for_timeout(1000)
                        
                        phone_el = page.locator("a[href^='tel:']").first
                        if await phone_el.count() > 0:
                            phone = await phone_el.inner_text()
                            print(f"      Phone Found: {phone}", flush=True)
                            
                            # --- SELLER EXTRACTION ---
                            seller_name = "Unknown"
                            try:
                                seller_name = await page.evaluate('''() => {
                                    let dl = window.dataLayer || [];
                                    for(let i = 0; i < dl.length; i++) {
                                        if(dl[i].seller_name) return dl[i].seller_name;
                                    }
                                    return "Unknown";
                                }''')
                            except Exception:
                                pass
                                
                            print(f"      Seller Found: {seller_name}", flush=True)
                            
                            register_lead(phone, title, price, specs, seller_name)
                            save_visited(url)
                            visited.add(url)
                            successful_scrapes += 1
                            print(f"      [{successful_scrapes}/{target_scrapes}] Lead Saved Successfully.\n", flush=True)
                        else:
                            print(f"      Could not find phone number after click.", flush=True)
                    else:
                        print(f"      Phone button missing.", flush=True)

                except Exception as e:
                    print(f"      Error scanning car: {e}", flush=True)

            current_page += 1
            if current_page > 10: # Safety cap
                print("Safety cap reached (Page 10). Stopping.", flush=True)
                break

        await browser.close()
        if successful_scrapes > 0:
            print(f"\nFinished! Recorded {successful_scrapes} new leads today.", flush=True)
        else:
            print("\nFinished! No new leads found.", flush=True)

if __name__ == "__main__":
    asyncio.run(scrape())
