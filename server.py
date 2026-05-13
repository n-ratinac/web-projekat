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

players = {}
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
            engine.eat_food(player)
            engine.decay_mass(player, dt)  # Mass decay svaki tick

        # ---> Rešavamo jedenje igrača nakon svih pomeranja <---
        eaten = engine.resolve_player_collisions()
        
        for dead_player in eaten:
            dead_sid = None
            # Trazimo sid (Socket ID) na osnovu instance igrača
            for sid, p in players.items():
                if p == dead_player:
                    dead_sid = sid
                    break
                    
            if dead_sid:
                # Emitujemo 'death' event tom klijentu
                await sio.emit("death", to=dead_sid)
                
                # Brišemo ga sa servera i iz rečnika inputa
                del players[dead_sid]
                if dead_sid in inputs:
                    del inputs[dead_sid]

        engine.spawn_food(max_food=150)

        # Emitovanje trenutnog stanja klijentima
        state = {
            "players": [
                {"name": p.name, "x": p.x, "y": p.y, "mass": p.mass}
                for p in players.values()
            ],
            "food": engine.food
        }
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