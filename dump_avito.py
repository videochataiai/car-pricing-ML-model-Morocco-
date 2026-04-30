import asyncio
from playwright.async_api import async_playwright

async def get_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.avito.ma/fr/maroc/voitures")
        await page.wait_for_timeout(3000)
        html = await page.content()
        with open("avito_dump.html", "w") as f:
            f.write(html)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_html())
