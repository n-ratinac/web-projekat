import asyncio
import random
import time
import socketio
from aiohttp import web
from enigine import Engine # Proveri da li je fajl engine.py ili enigine.py
from player import Player

sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# sid -> Player
players = {}
# sid -> (dx, dy)
inputs = {}

engine = Engine(4000, 4000)

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def join(sid, data):
    name = data.get("name", "Player")
    x = random.randint(100, 700)
    y = random.randint(100, 500)
    player = Player(name, x, y)
    players[sid] = player
    engine.add_player(player)
    inputs[sid] = (0, 0)
    print(f"[join] {name} at ({x}, {y})")

@sio.event
async def update_input(sid, data):
    if sid in players:
        dx = float(data.get("dx", 0))
        dy = float(data.get("dy", 0))
        inputs[sid] = (dx, dy)

@sio.event
async def disconnect(sid):
    if sid in players:
        engine.remove_player(players[sid])
        del players[sid]
        del inputs[sid]
        print(f"Client disconnected: {sid}")

async def game_loop():
    TICK_RATE = 0.05  
    last_time = time.monotonic()

    while True:
        await asyncio.sleep(TICK_RATE)

        now = time.monotonic()
        dt = now - last_time  
        last_time = now

        for sid, player in list(players.items()):
            direction = inputs.get(sid, (0, 0))
            engine.move_player(player, direction, dt)
        engine.spawn_food(max_food=150)

        # Kreiranje stanja (pazi na mass!)[cite: 3, 6]
        state = {
            "players": [
                {"name": p.name, "x": p.x, "y": p.y, "mass": p.mass} 
                for p in players.values()
            ],
            "food": engine.food 
        }

        # Ova linija mora biti poravnata sa 'state' blokom iznad
        await sio.emit("state", state)

async def start_game_loop(app):
    app["game_loop"] = asyncio.ensure_future(game_loop())

async def stop_game_loop(app):
    app["game_loop"].cancel()
    try:
        await app["game_loop"]
    except asyncio.CancelledError:
        pass

app.on_startup.append(start_game_loop)
app.on_cleanup.append(stop_game_loop)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)