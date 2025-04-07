import os
import flask
from flask import Flask, redirect, render_template, url_for, request, Response
from apis import flights as flights_api
from apis import hotels as hotels_api
from apis import activities as activities_api
import datetime
from load_dotenv import load_dotenv
import requests
import json
import time
import json
import uuid
from queue import Queue
from threading import Lock
import os

app = Flask(__name__, static_url_path='/static')


# In-memory storage for messages and client connections
# In a production app, you might want to use a more robust solution

# In-memory storage for messages and client connections
class SSEManager:
    def __init__(self):
        self.clients = {}  # dictionary to store client queues by chat_id
        self.lock = Lock()  # thread safety

    def register_client(self, chat_id):
        """Register a new client with a specific chat_id"""
        client_id = str(uuid.uuid4())
        with self.lock:
            if chat_id not in self.clients:
                self.clients[chat_id] = {}
            self.clients[chat_id][client_id] = Queue()
        return client_id

    def unregister_client(self, chat_id, client_id):
        """Remove a client when they disconnect"""
        with self.lock:
            if chat_id in self.clients and client_id in self.clients[chat_id]:
                del self.clients[chat_id][client_id]
                # Clean up empty chat rooms
                if not self.clients[chat_id]:
                    del self.clients[chat_id]

    def publish_message(self, chat_id, message, event_type="message"):
        """Send a message to all clients in a specific chat room"""
        with self.lock:
            if chat_id not in self.clients:
                return False  # No clients in this chat room
                
            # Format the SSE message
            sse_message = self._format_sse(message, event_type)
            
            # Add message to each client's queue in this chat room
            for client_id, queue in self.clients[chat_id].items():
                queue.put(sse_message)
            
            return True
    
    def get_message_for_client(self, chat_id, client_id, timeout=None):
        """Get the next message for a specific client"""
        if chat_id not in self.clients or client_id not in self.clients[chat_id]:
            return None
        try:
            return self.clients[chat_id][client_id].get(timeout=timeout)
        except:
            return None

    def get_active_chat_ids(self):
        """Return a list of active chat IDs"""
        with self.lock:
            return list(self.clients.keys())

    def _format_sse(self, data, event=None):
        """Format data according to SSE spec"""
        message = ""
        # Optional event type
        if event:
            message += f"event: {event}\n"
        
        # Data field is required
        if isinstance(data, dict):
            data = json.dumps(data)
        message += f"data: {data}\n\n"
        return message




## WEBSITE ROUTES ##

@app.route('/')
def index():
    # load index.html
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    # load index.html
    chat_id = os.urandom(16).hex()
    return redirect(url_for('chatbot_with_id', chat_id=chat_id))

@app.route('/chatbot/<chat_id>')
def chatbot_with_id(chat_id):
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

        requests.post(
            "https://learninguniversalconnectingexperiences.site/publish",
            json={
                "chat_id": chat_id,
                "message": parsed["data"]
            }
        )

        return parsed

@app.route(api_base + "/find_activities", methods=['GET'])
def find_activities():
    if request.method == 'GET':
        city = request.values.get("city")

        activities = activities_api.get_data(city)
        parsed = activities_api.parse_data(activities)

        return parsed


# Create our SSE manager

sse_manager = SSEManager()

@app.route('/events/<chat_id>')
def events(chat_id):
    """SSE endpoint for a specific chat ID"""
    client_id = sse_manager.register_client(chat_id)
    
    def stream():
        try:
            # Send an initial message
            yield sse_manager._format_sse({'message': f'Connected to chat room: {chat_id}'}, 'connected')
            
            # Keep the connection alive
            while True:
                # Get message from queue (blocking with timeout)
                message = sse_manager.get_message_for_client(chat_id, client_id, timeout=20)
                
                if message:
                    yield message
                else:
                    # No message received, send a heartbeat
                    yield sse_manager._format_sse('', 'heartbeat')
                    
        except:
            # Client disconnected
            pass
        finally:
            # Clean up when client disconnects
            sse_manager.unregister_client(chat_id, client_id)
    
    response = Response(stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/publish', methods=['POST'])
def publish():
    """Endpoint to publish new messages to a specific chat ID"""
    data = request.json or {}
    message = data.get('message', '')
    chat_id = data.get('chat_id', '')
    event_type = data.get('event', 'message')
    
    if not message or not chat_id:
        return {'status': 'error', 'message': 'Missing message or chat ID'}, 400
        
    success = sse_manager.publish_message(chat_id, message, event_type)
    if success:
        return {'status': 'ok'}
    return {'status': 'warning', 'message': 'No active listeners for this chat ID'}, 200

@app.route('/create_chat', methods=['POST'])
def create_chat():
    """Create a new chat room if not exists"""
    chat_id = request.form.get('chat_id', '')
    if not chat_id:
        return redirect(url_for('receiver'))
    
    return redirect(url_for('listen', chat_id=chat_id))

@app.route('/active_chats')
def active_chats():
    """API endpoint to get active chat IDs"""
    active_chats = sse_manager.get_active_chat_ids()
    return {'chats': active_chats}



@app.route('/sender')
def sender():
    """Sender page - can only send messages"""
    # Get active chat IDs for dropdown
    active_chats = sse_manager.get_active_chat_ids()
    return render_template('send.html', active_chats=active_chats)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", threaded=True)
    #find_flights()
