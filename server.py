import asyncio
import random
import time
import socketio
from aiohttp import web
from settings import cfg
from enigine import Engine
from player import Player

# Inicijalizacija Socket.IO servera
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Globalne strukture za praćenje stanja
players = {}
inputs = {}

# Engine se inicijalizuje sa vrednostima iz config-a
engine = Engine(cfg['game']['width'], cfg['game']['height'])

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def join(sid, data):
    name = data.get("name", "Player")
    
    # Spawn pozicija na osnovu granica mape iz config-a
    x = random.randint(100, cfg['game']['width'] - 100)
    y = random.randint(100, cfg['game']['height'] - 100)
    
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
        if sid in inputs: del inputs[sid]
        print(f"Client disconnected: {sid}")

async def game_loop():
    # Učitavamo TICK_RATE iz config-a
    tick_rate = cfg['game'].get('tick_rate_seconds', 0.05)
    last_time = time.monotonic()

    while True:
        await asyncio.sleep(tick_rate)

        now = time.monotonic()
        dt = now - last_time
        last_time = now

        # Pomeranje i fizika
        for sid, player in list(players.items()):
            direction = inputs.get(sid, (0, 0))
            engine.move_player(player, direction, dt)
            engine.eat_food(player)
            engine.decay_mass(player, dt) 

        # Rešavanje sudara igrača
        eaten = engine.resolve_player_collisions()
        
        for dead_player in eaten:
            dead_sid = None
            for sid, p in players.items():
                if p == dead_player:
                    dead_sid = sid
                    break
                    
            if dead_sid:
                await sio.emit("death", to=dead_sid)
                if dead_sid in players: del players[dead_sid]
                if dead_sid in inputs: del inputs[dead_sid]

        # Spawn hrane do limita iz config-a
        engine.spawn_food(max_food=cfg['food'].get('max_food_count', 150))

        # Leaderboard
        sorted_players = sorted(players.values(), key=lambda p: p.mass, reverse=True)
        leaderboard = [
            {"rank": i + 1, "name": p.name, "mass": round(p.mass)}
            for i, p in enumerate(sorted_players[:10])
        ]

        # STANJE KOJE SE ŠALJE KLIJENTU
        state = {
            "players": [
                {"name": p.name, "x": p.x, "y": p.y, "mass": p.mass}
                for p in players.values()
            ],
            "food": engine.food,
            "leaderboard": leaderboard,
            "total_players": len(players),
            # DODATO: Slanje config-a klijentu radi dinamičkog zooma i granica mape
            "config": {
                "zoom_base": cfg['game'].get('zoom_base', 20),
                "map_width": cfg['game']['width'],
                "map_height": cfg['game']['height']
            }
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
    web.run_app(
        app, 
        host=cfg['network'].get('host', '0.0.0.0'), 
        port=cfg['network'].get('port', 8080)
    )