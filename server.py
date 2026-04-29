import asyncio
import random
import time
import socketio
from aiohttp import web
from enigine import Engine
from player import Player

sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# sid -> Player
players = {}
# sid -> (dx, dy)
inputs = {}

engine = Engine(800, 600)


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")


@sio.event
async def join(sid, data):
    name = data.get("name", "Player")
    # Spawn at a random position so players don't overlap
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
    TICK_RATE = 0.05  # seconds between ticks (20 ticks/sec)
    last_time = time.monotonic()

    while True:
        await asyncio.sleep(TICK_RATE)

        now = time.monotonic()
        dt = now - last_time  # actual elapsed seconds (handles jitter)
        last_time = now

        # Move every player with delta time so speed is tick-rate independent
        for sid, player in list(players.items()):
            direction = inputs.get(sid, (0, 0))
            engine.move_player(player, direction, dt)

        # Broadcast the authoritative world state to all clients
        state = [
            {"name": p.name, "x": p.x, "y": p.y}
            for p in players.values()
        ]
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