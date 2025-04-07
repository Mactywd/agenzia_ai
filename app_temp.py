# app.py
import time
import json
import uuid
from queue import Queue
from threading import Lock
import os

from flask import Flask, Response, render_template, request, redirect, url_for

app = Flask(__name__)

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

# Create our SSE manager
sse_manager = SSEManager()

@app.route('/')
def index():
    """Main page that redirects to sender or receiver"""
    return render_template('test.html')

@app.route('/sender')
def sender():
    """Sender page - can only send messages"""
    # Get active chat IDs for dropdown
    active_chats = sse_manager.get_active_chat_ids()
    return render_template('send.html', active_chats=active_chats)

@app.route('/receiver')
def receiver():
    """Receiver setup page - ask for chat ID before connecting"""
    return render_template('receive.html')

@app.route('/listen/<chat_id>')
def listen(chat_id):
    """Receiver page - can only receive messages for a specific chat ID"""
    return render_template('listen.html', chat_id=chat_id)

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

if __name__ == '__main__':
    # Use the port provided by Heroku
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)