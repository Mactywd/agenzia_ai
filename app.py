import asyncio
from flask import Flask, render_template, url_for, request
from apis import flights as flights_api
from apis import hotels as hotels_api
from apis import activities as activities_api
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
        params={
            "destination": "DXB",
            "departures": "FCO",
            "date": "2025-07-15"
        }
    )
    return str(response)


## API ROUTES
api_base = "/api"

@app.route(api_base + "/find_flights", methods=['GET'])
def find_flights():
    if request.method == 'GET':
        destination = request.values.get('destination')
        departures = request.values.get('departure')
        date = request.values.get('date')

        print(request.values)

        print(destination, departures, date)

        flights = flights_api.get_data(departures, destination, date)
        parsed = flights_api.parse_data(flights)

        return parsed
    
@app.route(api_base + "/find_hotel", methods=['GET'])
def find_hotels():
    if request.method == 'GET':
        city = request.values.get("city")

        hotels = hotels_api.get_data(city)
        parsed = hotels_api.parse_data(hotels)

        return parsed

@app.route(api_base + "/find_activities", methods=['GET'])
def find_activities():
    if request.method == 'GET':
        city = request.values.get("city")

        activities = activities_api.get_data(city)
        parsed = activities_api.parse_data(activities)

        return parsed

if __name__ == '__main__':
    #app.run(debug=True)
    find_flights()
