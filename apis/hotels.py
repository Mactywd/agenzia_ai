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
    url = "https://api.geoapify.com/v1/geocode/search?text="+city+"&apiKey="+os.getenv('GEOAPIFY_API_KEY')
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
    lat, lng = get_latlng(city)

    # Get hotel list
    try:
        response = amadeus.get(
            "/v1/reference-data/locations/hotels/by-geocode",
            latitude=lat,
            longitude=lng,
            ratings=[3,4,5])
        #print(response.data)
        with open("hotel_api_output.json", "w") as f:
            json.dump(response.data, f, indent=2)
    
    except ResponseError as error:
        raise error
    
    # Get hotel ids
    ids = []
    for hotel in response.data:
        ids.append(hotel["hotelId"])
    
    # Get hotels info
    # try:
    #     response = amadeus.get(
    #         "/v3/shopping/hotel-offers",
    #         hotelIds=ids[1],
    #         adults=1)
    #     print(response.data)
    #     with open("hotel_info_output.json", "w") as f:
    #         json.dump(response.data, f, indent=2)
        
    #     return response

    # except ResponseError as error:
    #     raise error
    
    return response

    # class Response:
    #     def __init__(self, data):
    #         self.data = data

    # with open("api_output.json", "r") as f:
    #     response = Response(json.load(f))
    
    # return response
    

def parse_data(response):
    hotels = []
    for hotel in response.data:
        hotels.append({
            "name": hotel["name"],
            "lat": hotel["geoCode"]["latitude"],
            "lng": hotel["geoCode"]["longitude"],
            "stars": hotel["rating"],
        })
    
    print(hotels)
    with open("hotels.json", "w") as f:
        json.dump(hotels, f, indent=2)

    return hotels


if __name__ == '__main__':
    # Get latlong
    city = "Rome"

    response = get_data(
        city
    )

    parsed = parse_data(response)

    print(parsed)