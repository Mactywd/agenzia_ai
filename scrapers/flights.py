import asyncio
from dataclasses import dataclass
import json
from playwright.async_api import async_playwright
import airportsdata
import pycountry
from typing import Literal
from datetime import datetime

@dataclass
class FlightData:
    airline: str
    type: str
    layovers: int
    duration: str
    departure: str
    arrival: str
    price: str
    url: str

    def __iter__(self):
        return iter(self.__dict__.values())


class Scraper:
    def __init__(self, params):
        self.params = params
        self.airports = airportsdata.load('IATA')
        self.cities = []
        self.countries = []
        self.continents = ["Europe", "Asia", "North America", "South America", "Africa", "Oceania"]

        for airport in self.airports:
            country_short = self.airports[airport]["country"]
            if country_short == "XK":
                country_short = "Kosovo"
            else:
                country_short = pycountry.countries.get(alpha_2=country_short).name
            if country_short not in self.countries:
                self.countries.append(country_short)

            if self.airports[airport]["city"] not in self.cities:
                self.cities.append(self.airports[airport]["city"])
        
    async def _extract_airports(self, flight_info):
        airports = []
        # get all occurrences of 3 consecutive uppercase letters
        for info in flight_info.split("–"):
            airports.append(info[0:3])
        
        return airports


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
   
    async def _fill_airports_form(self, page):
        """Fill out the Google Flights search form with the given parameters."""
        
        # Departure(s)
        await page.wait_for_selector('input[aria-label="Where from?"]')
        await page.click('input[aria-label="Where from?"]')
        await page.click('button[aria-label="Origin, Select multiple airports"]')
        await page.click("div[jscontroller='e2jnoe']")
        
        for airport in self.params.departure:
            await page.keyboard.type(airport)
            await page.keyboard.press("ArrowDown")
            await page.keyboard.press("Enter")
            await page.click("button[aria-label='Done']")
        
        # Filters
        buttons = await page.query_selector_all('button[aria-label="All filters"]')
        button = buttons[1]
        await button.click()        
        
        await page.wait_for_selector('#P30xpf0')
        
        # Stops
        options = {
            "any": "input[aria-label='Any number of stops']",
            "nonstop": "input[aria-label='Nonstop only']",
            "1": "input[aria-label='1 stop or fewer']",
            "2": "input[aria-label='2 stops or fewer']",
        }
        await page.click(options[self.params.stops])

        # Travel mode
        options = {
            "any": "input[aria-label='All']",
            "flight_only": "input[aria-label='Flights only']"
        }
        await page.click(options[self.params.trip_type])
        await page.click('button[aria-label="Close dialog"]')

        # Flight Class
        buttons = await page.query_selector_all(".VfPpkd-aPP78e")
        button = buttons[1]
        await button.click()

        options = {
            "economy": 2,
            "premium_economy": 3,
            "business": 4,
            "first": 5
        }
        buttons = await page.query_selector_all(".MCs1Pd")
        button = buttons[options[self.params.flight_class]]
        await button.click()

        # Passengers
        buttons = await page.query_selector_all(".VfPpkd-RLmnJb")
        button = buttons[8]
        await button.click()

        options = {
            "adults": 1,
            "kids": 3,
            "babies_noseat": 5,
            "babies_seat": 7,
        }

        buttons = await page.query_selector_all(".g2ZhCc.NMm5M")
        for person_type in options:
            button_type = buttons[options[person_type]]
            for _ in range(self.params.passengers[person_type]):
                await button_type.click()
        
        await button.click()

        # Date
        await page.click(".uNiB1.iLjaEf")
        buttons = await page.query_selector_all(".VfPpkd-AznF2e")

        # Specific date
        if self.params.date["type"] == "specific":
            button = buttons[0]
            await button.click()

            # Departure date
            buttons = await page.query_selector_all('input[aria-label="Departure"]')
            button = buttons[1]
            await button.click()
            await page.keyboard.type(self.params.date["departure"])

            # Arrival date
            buttons = await page.query_selector_all('input[aria-label="Return"]')
            button = buttons[1]
            await button.click()
            await page.keyboard.type(self.params.date["return"])
            await page.click('.X4feqd.wDt51d')


        # Flexible date
        elif self.params.date["type"] == "flexible":
            button = buttons[1]
            await button.click()

            buttons = await page.query_selector_all('.VfPpkd-LgbsSe')

            # Month (29-35)
            
            if self.params.date["month"] == "all":
                button_index = 29
            else:
                month_now = datetime.now().month
                month_diff = abs(month_now - self.params.date["month"])
                button_index = 30 + month_diff

            button = buttons[button_index]
            await button.click()

            # Duration (36-38)
            durations = ["weekend", "1week", "2weeks"]
            button_index = durations.index(self.params.date["duration"]) + 36
            button = buttons[button_index]
            await button.click()
            

        # Close date picker
        buttons = await page.query_selector_all(".VfPpkd-LgbsSe")
        button = buttons[39]
        await button.click()

        # Destination
        await page.click('input[aria-label="Where to?"]')
        await page.keyboard.type(self.params.destination)
        await page.keyboard.press("ArrowDown")
        await page.keyboard.press("Enter")

    async def _get_flights_info(self, page):

        await page.wait_for_selector(".BgYkof.eIvujf")
        self.flights = []

        await page.wait_for_timeout(1000)
        # check if any flight is available, otherwise return None
        if await page.is_visible(".CQYfx.koW9nb"):
            return self.flights
        
        flights_raw = await page.query_selector_all("a.DvoDQ")
        
        flight_all = await page.query_selector_all("span.yApPxd")
        airline_all = await page.query_selector_all("div.IMgkJe.QB2Jof span")
        price_all = await page.query_selector_all("div.EDKFBb.QB2Jof")
        urls_all = await page.query_selector_all("a.DvoDQ")

        for i in range(len(flights_raw)):
            airline_name = await airline_all[i].text_content()
            flight_info = await flight_all[i].text_content()
            flight_price = await price_all[i].text_content()
            flight_url = await urls_all[i].get_attribute("href")
            
            # parse flight_info
            
            # layovers
            if flight_info[0:7] == "Nonstop":
                flight_type = "Nonstop"
                flight_layovers = 0
                flight_info = flight_info[7:]
                
            
            else:
                flight_type = "Layover"
                flight_layovers, flight_info = flight_info.split(" stop")

            # duration
            try:
                flight_duration, flight_info = flight_info.split("min")
                flight_duration += "min"
            except ValueError:
                temp = flight_info.split("hr")
                flight_duration = temp[0]
                flight_info = "hr".join(temp[1:])

            # departure / arrival airports
            departure_airport, arrival_airport = await self._extract_airports(flight_info)
            
            try:
                flight_departure = f"{departure_airport} ({self.airports[departure_airport]["name"]})"
            except KeyError:
                flight_departure = "Unknown"
            try:
                flight_arrival = f"{arrival_airport} ({self.airports[arrival_airport]["name"]})"
            except KeyError:
                flight_arrival = "Unknown"  

            flight = FlightData(
                airline=airline_name,
                type=flight_type,
                layovers=int(flight_layovers),
                duration=flight_duration,
                departure=flight_departure,
                arrival=flight_arrival,
                price=flight_price,
                url=flight_url
            )

            self.flights.append(list(flight))

        return self.flights

    async def search_flights(self):

        async with async_playwright() as p:
            browser, page = await self._create_page(p)
            await page.goto('https://www.google.com/travel/explore')

            await self._accept_google_cookies(page)
            await self._fill_airports_form(page)
            await self._get_flights_info(page)
            flights = self.flights


            if flights:
                json_data = list(flights)
            else:
                json_data = [None]
            
            with open("flights.json", "w") as f:
                json.dump(json_data, f, indent=2)

            await browser.close()
            return list(flights)

@dataclass
class FlightParams:
    departure: list[str]
    destination: str
    flight_class: Literal["economy", "premium_economy", "business", "first"]
    stops: Literal["any", "nonstop", "1", "2"]
    trip_type: Literal["any", "flight_only"]
    passengers: dict
    date: dict 

async def main():
    """
    PARAMS:
    - departure: list of cities
    - destination: single airport code, city.
    NO- flight_class: economy, premium economy, business, first
    NO- layovers_max: any, nonstop, 1 or 2
    NO- trip_type: all, flight_only
    - passengers: list of passengers
        adults: 12-on
        kids: 2-11
        NO babies_noseat: 0-1 with no seat
        NO babies_seat: 0-1 with seat
    - date: 
        flight_type: flexible or specific
        if flexible:
            month: all or one of the next six months
            duration: weekend, 1week or 2weeks
        
        if specific:
            departure: YYYY-MM-DD
            return: YYYY-MM-DD
        
    """


    params = FlightParams(
        departure=["Roma"], # list of airport codes
        destination="Vancouver", # single airport code, city, country or continent
        flight_class="business",
        stops="any",
        trip_type="flight_only",
        passengers={
            "adults": 5,
            "kids": 1,
            "babies_seat": 0,
            "babies_noseat": 1,
        },
        date={
            "type": "flexible", # flexible or specific
            "month": 4,
            "duration": "2weeks",
        },
    )
    
    scraper = Scraper(params)
    await scraper.search_flights()

if __name__ == '__main__':
    asyncio.run(main())