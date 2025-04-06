import asyncio
from flask import Flask, render_template, url_for, request
from scrapers import flights as flights_scrape, \
                     hotels as hotels_scrape, \
                     attractions as attractions_scrape
import datetime
import requests

app = Flask(__name__, static_url_path='/static')

## WEBSITE ROUTES ##

@app.route('/')
def index():
    # load index.html
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    # load index.html
    return render_template('chatbot.html')

@app.route('/faq')
def faq():
    # load index.html
    return render_template('faq.html')

@app.route('/apitest')
def apitest():
    # Perform a GET to /api/find_flights with requests with example data
    response = requests.get(
        "http://localhost:5000/api/find_flights",
        json={
            "destination": "Vancouver",
            "departures": ["Pisa", "Roma", "Firenze"],
            "passengers": [3,0], # adults, kids
            "date": ["flessibile", "luglio", "weekend"] # flexible, month, week
        }
    )


## API ROUTES
api_base = "/api"

@app.route(api_base + "/find_flights", methods=['GET'])
async def find_flights():
    #if request.method == 'GET':
    if True:
        '''
        EXAMPLE DATA
        {
            destination: "Vancouver",
            departures: ["Pisa", "Roma", "Firenze"],
            passengers: [3,0] # adults, kids
            date: ["flessibile", "luglio", "weekend"] or ["specifica", "2023-06-01", "2023-06-05"]
        }
        '''
    

        data = {
            "destination": "Vancouver",
            "departures": ["Pisa", "Roma", "Firenze"],
            "passengers": [3,0], # adults, kids
            "date": ["flessibile", "luglio", "weekend"] or ["specifica", "2023-06-01", "2023-06-05"]
        }
        destination = data['destination']
        departures = data['departures']
        passengers = data['passengers']
        date = data['date']

        # Process the data

        def parse_lists(to_parse):
            print(to_parse)
            parsed = to_parse[1:-1] # remove first and last brackets
            try:
                parsed = parsed.split(", ")
            except AttributeError:
                pass
    
            return parsed
        
        #departures = parse_lists(departures)
        #passengers = parse_lists(passengers)

        date = parse_lists(date)
        if date[0] == "flessibile":
            month_current = datetime.datetime.now().month

            month_lookup = {
                "gennaio": 1,
                "febbraio": 2,
                "marzo": 3,
                "aprile": 4,
                "maggio": 5,
                "giugno": 6,
                "luglio": 7,
                "agosto": 8,
                "settembre": 9,
                "ottobre": 10,
                "novembre": 11,
                "dicembre": 12
            }

            target_month = month_lookup[date[1].lower()]

            if 0 < target_month - month_current < 6:
                date = {
                    "flight_type": "flexible",
                    "month": date[1],
                    "duration": date[2]
                }
        
        elif date[0] == "specifica":
            date = {
                "flight_type": "specific",
                "departure": date[1],
                "return": date[2]
            }
        
        flight_data = flights_scrape.FlightParams(
            departure=departures,
            destination=destination,
            passengers=passengers,
            date=date
        )

        flight_scraper = flights_scrape.Scraper(flight_data)
        flights = await flight_scraper.search_flights()

        parsed_text = []
        # Parse flight data
        for flight in flights:
            parsed = ["Partenza: " + flight[4],
                      "Arrivo: " + flight[5],
                      "Linea/e: " + flight[0],
                      "Durata: " + flight[3],
                      "Scali: " + flights[1] + flight[2],
                      "Prezzo: " + flight[6],
                      "Link: [Clicca qui]({})".format(flight[7])
                      ] 

            parsed = "\n".join(parsed)
            parsed_text.append(parsed)

        parsed_text = "\n\n".join(parsed_text)

        with open("parsed_flights.txt", "w") as f:
            f.write(parsed_text)

        return 200


if __name__ == '__main__':
    #app.run(debug=True)
    asyncio.run(find_flights())
