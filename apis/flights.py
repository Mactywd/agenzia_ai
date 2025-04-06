from amadeus import Client, ResponseError
from load_dotenv import load_dotenv
import os
import json

load_dotenv()

amadeus = Client(
    client_id=os.getenv('AMADEUS_CLIENT_ID'),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
)

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




def get_data(origin, destination, date):
    try:
        response = amadeus.get(
            "/v2/shopping/flight-offers",
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=date,
            adults=1,
            max=20)
        #print(response.data)
        with open("api_output.json", "w") as f:
            json.dump(response.data, f, indent=2)
        return response
    
    except ResponseError as error:
        raise error
    
    # class Response:
    #     def __init__(self, data):
    #         self.data = data

    # with open("api_output.json", "r") as f:
    #     response = Response(json.load(f))
    
    # return response
    

def parse_data(response):

    final_data = []
    items = 0
    for i in range(len(response.data)):
        skip_loop = False
        current_data = response.data[i]
        itinerary = current_data['itineraries'][0]
        segments = itinerary['segments']
        first_segment = segments[0]
        last_segment = segments[-1]

        departure_airport = first_segment['departure']['iataCode']
        departure_time = first_segment['departure']['at']

        arrival_airport = last_segment['arrival']['iataCode']
        arrival_time = last_segment['arrival']['at']

        carriers = [segment["carrierCode"] for segment in itinerary['segments']]

        duration = itinerary['duration']

        price = current_data['price']['grandTotal']

        for element in final_data:
            print(departure_time, element["departure_time"], departure_time==element["departure_time"])
            print(arrival_time, element["arrival_time"], arrival_time==element["arrival_time"])
            if (element["departure_time"] == departure_time) and (element["arrival_time"] == arrival_time):
                print("here")
                skip_loop = True
        
        if skip_loop:
            continue
        else:
            items += 1

        final_data.append({
            "departure_airport": departure_airport,
            "departure_time": departure_time,

            "arrival_airport": arrival_airport,
            "arrival_time": arrival_time,

            "carriers": carriers,
            "duration": duration,
            "price": price
        })

        if items >= 3:
            break

    with open("parsed_api_output.json", "w") as f:
        json.dump(final_data, f, indent=2)

    final_message = []
    for i, flight in enumerate(final_data):
        message = [
            "Volo " + str(i + 1),
            "Partenza: " + flight["departure_airport"] + " alle " + flight["departure_time"],
            "Arrivo: " + flight["arrival_airport"] + " alle " + flight["arrival_time"],
            "Linea/e: " + ", ".join(flight["carriers"]),
            "Durata: " + flight["duration"][2:],
            "Scali: " + str(len(flight["carriers"]) - 1),
            "Prezzo: " + flight["price"],
            ]
        
        message = "\n".join(message)
        final_message.append(message)
    
    final_message = "\n\n\n\n".join(final_message)

    with open("parsed_flights.txt", "w") as f:
        f.write(final_message)
    
    print(final_message)

    return {"data": final_message}

if __name__ == '__main__':
    response = get_data(
        origin="YVR",
        destination="FCO",
        date="2025-07-15"
    )

    parsed = parse_data(response)

    print(parsed)