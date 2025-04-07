import os
import flask
from flask import Flask, render_template, url_for, request
from apis import flights as flights_api
from apis import hotels as hotels_api
from apis import activities as activities_api
import datetime
from load_dotenv import load_dotenv
import requests
import redis

app = Flask(__name__, static_url_path='/static')
red = redis.StrictRedis()


## WEBSITE ROUTES ##

@app.route('/')
def index():
    # load index.html
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    # load index.html
    chat_id = os.urandom(16).hex()
    return render_template('chatbot.html', chat_id=chat_id)

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
        chat_id = request.values.get("chat_id")

        hotels = hotels_api.get_data(city)
        parsed = hotels_api.parse_data(hotels)

        print(chat_id)
        print(parsed)
        print(str(parsed))

        red.publish(chat_id, parsed)


        return parsed

@app.route(api_base + "/find_activities", methods=['GET'])
def find_activities():
    if request.method == 'GET':
        city = request.values.get("city")

        activities = activities_api.get_data(city)
        parsed = activities_api.parse_data(activities)

        return parsed

## SERVER-SIDE-EVENTS HANDLER ##

def event_stream(chat_id):
    pubsub = red.pubsub()
    pubsub.subscribe(chat_id)
    for message in pubsub.listen():
        print(message)
        yield 'data: %s\n\n' % message['data']


@app.route('/post')
def post():
    message = "hello"
    
    red.publish("chat_id", message)


    return "<p>Message sent</p>"


@app.route('/stream/<chat_id>')
def stream(chat_id):
    return flask.Response(event_stream(chat_id),
                          mimetype="text/event-stream")

@app.route("/test")
def test():
    return render_template("test.html", chat_id="1")

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", threaded=True)
    #find_flights()
