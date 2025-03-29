import asyncio
from dataclasses import dataclass
import json
from playwright.async_api import async_playwright, expect
from bs4 import BeautifulSoup

class Scraper:
    def __init__(self, params):
        self.params = params
    
    async def _create_page(self, p):
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        return (browser, await context.new_page())

    async def _accept_google_cookies(self, page):
        """Simulate a click on the 'Accept all' button to accept Google cookies on the page."""
        await page.wait_for_selector('button[aria-label="Accept all"]')
        await page.click('button[aria-label="Accept all"]')

    async def _fill_hotel_form(self, page):
        
        # Get initial state
        await page.wait_for_selector(".GDEAO")

        text_element = await page.query_selector('.GDEAO')
        initial_subtitle = await text_element.text_content()


        # Location
        await page.click('input[aria-label="Search for places, hotels and more"]')
        buttons = await page.query_selector_all('button[aria-label="Clear"]')
        await buttons[1].click()


        await page.wait_for_selector('button[aria-label="Clear"]', state='hidden')
        await page.wait_for_timeout(1000)
        await page.keyboard.type(self.params.location)
        await page.keyboard.press("Enter")
        print(self.params.location)
        
        print(initial_subtitle)
        await expect(page.locator('.GDEAO')).not_to_have_text(initial_subtitle)


        hotels_info = page.locator('.K1smNd')
        
        hotels_content = await hotels_info.inner_html()

        print("starting bs4")
        await self._extract_hotels(str(hotels_content))
        print("finished bs4")

    async def _extract_hotels(self, hotels_content):
        

        soup = BeautifulSoup(str(hotels_content), 'html.parser')

        hotel_names = soup.find_all('h2', class_='BgYkof ogfYpf ykx2he')
        hotel_prices = soup.find_all('div', class_='CQYfx UDzrdc')[::2] # only even elements
        hotel_stars = soup.find_all('span', class_='ta47le')[-len(hotel_names):] # first elements are usually ads, leave them out
        hotel_amenities = soup.find_all('span', class_='lXJaOd')
        hotel_url = soup.find_all('a', class_='PVOOXe')

        print(len(hotel_names), len(hotel_prices), len(hotel_stars), len(hotel_amenities), len(hotel_url))

        hotel_info = {}
        for i in range(len(hotel_names)):
            try:
                hotel_info[hotel_names[i].text] = {
                    'price': hotel_prices[i].text,
                    'stars': hotel_stars[i]['aria-label'],
                    'amenities': hotel_amenities[i].text,
                    'url': "https://www.google.com" + hotel_url[i]['href']
                }
            except IndexError:
                print("IndexError at i =", i)

        # with open("hotels.json", "w") as f:
        #     json.dump(hotel_info, f, indent=2)

        await self._process_hotel_data(hotel_info)

    async def _process_hotel_data(self, hotel_info):
        '''
        Rearrange data to be more easily readable

        FIRSTLY: creates a new, more manageable dict 
        name (dict key): stays the same
        price: "\u20ac80 total" -> 80
        stars: "4.5 out of 5 stars from 1,970 reviews" -> 4.5 stars 1970 reviews
        amenities: "Amenities for {hotel_name}, a {stars} hotel.: {amenity}, {amenity}, {amenity}, ... -> {stars}, {amenity}, {amenity}, {amenity}, ...
        url: stays the same
        

        FINALLY: creates a single string, contaning everything
        **{hotel_name}**
        Cost: {price}
        Stars: {stars}
        Amenities: {amenities}

        **{hotel2_name}**
        Cost: {price2}
        ... 
        '''

        # FIRST SECTION

        new_info = {name: {} for name in hotel_info.keys()}

        for name, info in hotel_info.items():
            try:
                new_info[name]['price'] = info['price'].split(' ')[0]

                new_info[name]['stars'] = "{} stars".format(info['stars'].split(' ')[0])
                
                hotel_stars = info['amenities'].split(', a ')[1]
                hotel_stars = hotel_stars.split(" hotel.")[0]

                amenities = info['amenities'].split('hotel.: ')[1]
                amenities = amenities.split(", ")

                new_info[name]['amenities'] = [hotel_stars, *amenities]

                new_info[name]['url'] = info['url']

            except IndexError:
                print("Error with {}: {}".format(name, info))

        hotel_info = new_info
        
        # with open("hotels_processed.json", "w") as f:
        #     json.dump(hotel_info, f, indent=2)

        # SECOND SECTION

        strings = []

        for hotel in new_info.keys():
            try:
                hotel_string = (f"**{hotel}**",
                f"Cost: {new_info[hotel]['price']}",
                f"Stars: {new_info[hotel]['stars']}",
                f"Amenities: {", ".join(new_info[hotel]['amenities'])}",
                f"Link: {new_info[hotel]['url']}")
   
                strings.append("\n".join(hotel_string))

            except KeyError:
                print("KeyError")

        final_string = "\n\n".join(strings)

        with open("output.txt", "w") as f:
            f.write(final_string)

    async def search_hotels(self):

        async with async_playwright() as p:
            browser, page = await self._create_page(p)
            await page.goto('https://www.google.com/travel/hotels')

            await self._accept_google_cookies(page)
            await self._fill_hotel_form(page)
            await browser.close()

@dataclass
class HotelParams:
    location: str

async def main():
    """
    PARAMS:
    
    location: client's destination city
    """


    params = HotelParams(
        location="Vancouver"
    )
    
    scraper = Scraper(params)
    await scraper.search_hotels()

if __name__ == '__main__':
    asyncio.run(main())