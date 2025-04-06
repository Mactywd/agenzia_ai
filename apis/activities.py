from amadeus import Client, ResponseError
from load_dotenv import load_dotenv
import os
import json
import requests
from requests.structures import CaseInsensitiveDict


load_dotenv()

amadeus = Client(
    client_id=os.getenv('AMADEUS_CLIENT_ID'),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
)

def get_latlng(city):
    url = "https://api.geoapify.com/v1/geocode/search?text="+city+"&apiKey="+os.environ('GEOAPIFY_API_KEY')
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    resp = requests.get(url, headers=headers)

    with open("geocodingAPI.json", "w") as f:
        json.dump(resp.json(), f, indent=2)

    print(resp.status_code)

    data = resp.json()["features"][0]["geometry"]["coordinates"]

    lng = data[0]
    lat = data[1]

    return lat,lng

# try:
#     response = amadeus.shopping.flight_offers_search.get(
#         originLocationCode='PSA',
#         destinationLocationCode='CDG',
#         departureDate='2025-07-15',
#         adults=1)
#     print(response.data)
#     with open("api_output.json", "w") as f:
#         json.dump(response.data, f, indent=2)
# except ResponseError as error:
#     print(error)




def get_data(city):
    # Get activities list
    lat, lng = get_latlng(city)

    try:
        response = amadeus.get(
            "/v1/shopping/activities",
            latitude=lat,
            longitude=lng,
            radius=20)
        #print(response.data)
        with open("activities_api_output.json", "w") as f:
            json.dump(response.data, f, indent=2)
    
    except ResponseError as error:
        raise error
    
    return response

    # class Response:
    #     def __init__(self, data):
    #         self.data = data

    # with open("activities_api_output.json", "r") as f:
    #     response = Response(json.load(f))
    
    # return response
    

def parse_data(response):
    activities = []
    for activity in response.data:
        name = activity["name"]
        description = activity.get("description") if activity.get("description") is not None else ""
        lat = activity["geoCode"]["latitude"]
        lng = activity["geoCode"]["longitude"]
        print(activity["price"], activity["price"]=={})
        price = activity["price"]["amount"] if activity["price"] != {} else ""
        minimumDuration = activity.get("minimumDuration") if activity.get("minimumDuration") is not None else ""

        activities.append({
            "name": name,
            "description": description,
            "lat": lat,
            "lng": lng,
            "price": price,
            "minimumDuration": minimumDuration
        })
        
    
    print(activities)
    with open("activities.json", "w") as f:
        json.dump(activities, f, indent=2)

    return {"data": activities}


if __name__ == '__main__':

    city = "Rome"

    response = get_data(
        city
    )

    parsed = parse_data(response)

    print(parsed)