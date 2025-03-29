import asyncio
import json
from playwright.async_api import async_playwright
from dataclasses import dataclass

class Scraper:
    def __init__(self, attractions):
        self.attractions = attractions
    
    async def _create_page(self, p):
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        return (browser, await context.new_page())

    async def _fill_attractions_form(self, page):
        await page.click('button[aria-label="Going to"]')
        await page.click("input#destination_form_field")
        await page.keyboard.type(self.attractions.location, delay=100)
        await page.wait_for_timeout(0.231)
        await page.keyboard.press("Enter")

        await page.click("button#search_button")

        '''
        Get top 10 attractions.
        title: h3[data-testid="activity-tile-card--title"]
        duration: div[data-testid="activity-duration--feature"] span span[1]
        rating: div[data-testid="activity-review-rating"] div[0]
        price: span.uitk-lockup-price
        '''

        amount = 10
        await page.wait_for_selector(f'h3[data-testid="activity-tile-card--title"]')

        titles = await page.query_selector_all('h3[data-testid="activity-tile-card--title"]')
        durations = await page.query_selector_all('div[data-testid="activity-duration--feature"] span span:nth-child(1)')
        ratings = await page.query_selector_all('div[data-testid="activity-review-rating"] div:nth-child(1)')
        prices = await page.query_selector_all('span.uitk-lockup-price')

        attractions = []

        for i in range(amount):
            title = await titles[i].text_content()
            duration = await durations[i].text_content()
            rating = await ratings[i].text_content()
            price = await prices[i].text_content()

            attractions.append([title, duration, rating, price])

        with open("attractions.json", "w") as f:
            json.dump(attractions, f, indent=2)

        

    async def search_hotels(self):
        async with async_playwright() as p:
            browser, page = await self._create_page(p)
            await page.goto('https://www.expedia.com/Activities')
            await self._fill_attractions_form(page)
            await browser.close()

@dataclass
class AttractionParams:
    location: str

async def main():
    params = AttractionParams(
        location="Vancouver"
    )

    scraper = Scraper(params)
    await scraper.search_hotels()


if __name__ == '__main__':
    asyncio.run(main())