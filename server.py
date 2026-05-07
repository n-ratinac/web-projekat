import socketio
import eventlet
from flask import Flask, send_from_directory
import random
import time
import threading

# Create a Socket.IO server
sio = socketio.Server(cors_allowed_origins='*', async_mode='eventlet')
app = Flask(__name__)

WORLD = 4000
FOOD_COUNT = 600

players = {}  # {sid: {'name': name, 'x': x, 'y': y, 'mass': mass}}
food = []

def massToR(m):
    import math
    return math.sqrt(m / math.pi) * 4

# Generate initial food
for _ in range(FOOD_COUNT):
    sansa = random.random()
    mass = 1 if sansa < 0.6 else 3 if sansa < 0.9 else 5
    food.append({
        'x': random.uniform(20, WORLD - 20),
        'y': random.uniform(20, WORLD - 20),
        'mass': mass,
        'hue': random.randint(0, 360)
    })

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@sio.event
def connect(sid, environ):
    print(f'Client connected: {sid}')
    # Initialize player with random position
    players[sid] = {
        'name': f'Player_{random.randint(1000,9999)}',
        'x': random.uniform(100, WORLD - 100),
        'y': random.uniform(100, WORLD - 100),
        'mass': 20
    }
    sio.emit('player_init', {'player': players[sid], 'food': food}, to=sid)

@sio.event
def disconnect(sid):
    print(f'Client disconnected: {sid}')
    if sid in players:
        del players[sid]

@sio.event
def move(sid, data):
    if sid in players:
        players[sid]['x'] = data['x']
        players[sid]['y'] = data['y']
        players[sid]['mass'] = data.get('mass', 20)
        # Check for eating food
        r_player = massToR(players[sid]['mass'])
        food_to_remove = []
        for f in food:
            dx = players[sid]['x'] - f['x']
            dy = players[sid]['y'] - f['y']
            d = (dx**2 + dy**2)**0.5
            r_food = massToR(f['mass'])
            if d < r_player + r_food:
                players[sid]['mass'] += f['mass']
                food_to_remove.append(f)
        for f in food_to_remove:
            food.remove(f)
            # Regenerate food
            sansa = random.random()
            mass = 1 if sansa < 0.6 else 3 if sansa < 0.9 else 5
            food.append({
                'x': random.uniform(20, WORLD - 20),
                'y': random.uniform(20, WORLD - 20),
                'mass': mass,
                'hue': random.randint(0, 360)
            })

@sio.event
def name(sid, name):
    if sid in players:
        players[sid]['name'] = name

def broadcast_positions():
    while True:
        sio.emit('update', {'players': players, 'food': food})
        time.sleep(0.05)  # 20 times per second

# Wrap Flask app with Socket.IO
app = socketio.WSGIApp(sio, app)

if __name__ == '__main__':
    # Start broadcasting thread
    threading.Thread(target=broadcast_positions, daemon=True).start()
    eventlet.wsgi.server(eventlet.listen(('', 5001)), app)