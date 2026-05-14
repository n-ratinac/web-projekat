import asyncio
import json
import math
import random
import string
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from mimetypes import guess_type
import websockets

PORT = 8000
WS_PORT = 3000
PUBLIC_DIR = Path(__file__).parent
WORLD_SIZE = 4000
FOOD_COUNT = 800
BOT_COUNT = 15
TICK_RATE = 1 / 60

clients = {}
food = []
bots = []
BOT_NAMES = [
    'Bot1', 'Bot2', 'Bot3', 'Bot4', 'Bot5', 'Bot6', 'Bot7', 'Bot8', 'Bot9', 'Bot10'
]


def random_color() -> str:
    hue = random.randint(0, 339)
    return f'hsl({hue}, 75%, 55%)'


def generate_id(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_bot_name() -> str:
    return random.choice(BOT_NAMES)


def mass_to_radius(mass: float) -> float:
    return math.sqrt(mass / math.pi) * 4


def radius_to_mass(radius: float) -> float:
    return math.pi * (radius / 4) ** 2


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def spawn_food() -> None:
    for _ in range(FOOD_COUNT):
        food.append({
            'id': generate_id(),
            'x': random.uniform(50, WORLD_SIZE - 50),
            'y': random.uniform(50, WORLD_SIZE - 50),
            'mass': 1 if random.random() < 0.8 else 3 if random.random() < 0.95 else 5,
            'color': random_color(),
        })


def spawn_bots() -> None:
    for _ in range(BOT_COUNT):
        bots.append({
            'id': generate_id(),
            'x': random.uniform(200, WORLD_SIZE - 200),
            'y': random.uniform(200, WORLD_SIZE - 200),
            'mass': random.uniform(20, 70),
            'color': random_color(),
            'name': random_bot_name(),
            'vx': 0.0,
            'vy': 0.0,
            'targetX': random.uniform(0, WORLD_SIZE),
            'targetY': random.uniform(0, WORLD_SIZE),
            'lastThink': asyncio.get_event_loop().time(),
        })


def update_bots() -> None:
    now = asyncio.get_event_loop().time()
    for bot in bots:
        # Vary think time based on bot mass (smaller bots think faster)
        think_interval = random.uniform(0.3, 2.0) * (1.0 + bot['mass'] / 100)
        if now - bot['lastThink'] > think_interval:
            bot['lastThink'] = now
            
            # Different behaviors: sometimes chase food area, sometimes random wander, sometimes stay
            behavior = random.random()
            if behavior < 0.6:
                # Random wander (most common)
                bot['targetX'] = random.uniform(0, WORLD_SIZE)
                bot['targetY'] = random.uniform(0, WORLD_SIZE)
            elif behavior < 0.9:
                # Wander in a smaller area (more localized)
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(200, 600)
                bot['targetX'] = clamp(bot['x'] + math.cos(angle) * distance, 0, WORLD_SIZE)
                bot['targetY'] = clamp(bot['y'] + math.sin(angle) * distance, 0, WORLD_SIZE)
            # else: keep current target

        dx = bot['targetX'] - bot['x']
        dy = bot['targetY'] - bot['y']
        dist = math.hypot(dx, dy)
        if dist > 0:
            speed = 2 / math.sqrt(bot['mass'])
            # Vary acceleration based on mass
            accel = 0.3 + (100 - bot['mass']) / 200  # Smaller bots accelerate more
            bot['vx'] += dx / dist * speed * accel
            bot['vy'] += dy / dist * speed * accel

        # Vary friction based on mass
        friction = 0.80 + bot['mass'] / 1000  # Heavier bots have more friction
        bot['vx'] *= friction
        bot['vy'] *= friction

        bot['x'] = clamp(bot['x'] + bot['vx'], 0, WORLD_SIZE)
        bot['y'] = clamp(bot['y'] + bot['vy'], 0, WORLD_SIZE)

        if bot['mass'] > 200:
            bot['mass'] -= bot['mass'] * 0.0001


def update_clients() -> None:
    for client in clients.values():
        if client['targetX'] is not None and client['targetY'] is not None:
            dx = client['targetX'] - client['x']
            dy = client['targetY'] - client['y']
            dist = math.hypot(dx, dy)
            if dist > 0:
                speed = 2 / math.sqrt(client['mass'])
                client['vx'] += dx / dist * speed * 1.5
                client['vy'] += dy / dist * speed * 1.5

        client['vx'] *= 0.85
        client['vy'] *= 0.85
        client['x'] = clamp(client['x'] + client['vx'], 0, WORLD_SIZE)
        client['y'] = clamp(client['y'] + client['vy'], 0, WORLD_SIZE)

        if client['mass'] > 200:
            client['mass'] -= client['mass'] * 0.0001


def check_collisions() -> None:
    for client in clients.values():
        for f in food:
            dx = f['x'] - client['x']
            dy = f['y'] - client['y']
            dist = math.hypot(dx, dy)
            if dist < mass_to_radius(client['mass']):
                client['mass'] += f['mass']
                f['x'] = random.uniform(50, WORLD_SIZE - 50)
                f['y'] = random.uniform(50, WORLD_SIZE - 50)

    for bot in bots:
        for f in food:
            dx = f['x'] - bot['x']
            dy = f['y'] - bot['y']
            dist = math.hypot(dx, dy)
            if dist < mass_to_radius(bot['mass']):
                bot['mass'] += f['mass']
                f['x'] = random.uniform(50, WORLD_SIZE - 50)
                f['y'] = random.uniform(50, WORLD_SIZE - 50)

    for client in clients.values():
        for bot in bots:
            if client['mass'] > bot['mass'] * 1.2:
                dx = bot['x'] - client['x']
                dy = bot['y'] - client['y']
                dist = math.hypot(dx, dy)
                if dist < mass_to_radius(client['mass']):
                    client['mass'] += bot['mass']
                    bot['x'] = random.uniform(100, WORLD_SIZE - 100)
                    bot['y'] = random.uniform(100, WORLD_SIZE - 100)
                    bot['mass'] = random.uniform(20, 70)

    for bot in bots:
        for client in clients.values():
            if bot['mass'] > client['mass'] * 1.2:
                dx = client['x'] - bot['x']
                dy = client['y'] - bot['y']
                dist = math.hypot(dx, dy)
                if dist < mass_to_radius(bot['mass']):
                    bot['mass'] += client['mass']
                    client['x'] = random.uniform(200, WORLD_SIZE - 200)
                    client['y'] = random.uniform(200, WORLD_SIZE - 200)
                    client['mass'] = 20.0
                    client['dead'] = True


def public_player_state(client: dict) -> dict:
    return {
        'id': client['id'],
        'name': client['name'],
        'color': client['color'],
        'x': client['x'],
        'y': client['y'],
        'mass': client['mass'],
        'dead': client['dead'],
    }


def build_leaderboard() -> list:
    # Combine clients and bots, sort by mass
    all_entities = []
    for client in clients.values():
        all_entities.append({
            'id': client['id'],
            'name': client['name'],
            'mass': client['mass']
        })
    for bot in bots:
        all_entities.append({
            'id': bot['id'],
            'name': bot['name'],
            'mass': bot['mass']
        })
    
    sorted_entities = sorted(all_entities, key=lambda e: e['mass'], reverse=True)
    return [
        {'id': e['id'], 'name': e['name'], 'mass': round(e['mass'])}
        for e in sorted_entities[:10]
    ]


async def broadcast_state() -> None:
    state = {
        'type': 'state',
        'players': [public_player_state(client) for client in clients.values() if not client['dead']],
        'bots': [
            {
                'id': bot['id'],
                'x': bot['x'],
                'y': bot['y'],
                'mass': bot['mass'],
                'color': bot['color'],
                'name': bot['name'],
            }
            for bot in bots
        ],
        'food': food,
        'leaderboard': build_leaderboard(),
    }

    closed = []
    message = json.dumps(state)
    for client_id, client in clients.items():
        ws = client['ws']
        try:
            await ws.send(message)
        except Exception:
            closed.append(client_id)

    # Send death notification to dead players
    for client_id, client in clients.items():
        if client['dead']:
            try:
                death_msg = json.dumps({'type': 'death'})
                await client['ws'].send(death_msg)
            except Exception:
                if client_id not in closed:
                    closed.append(client_id)

    for client_id in closed:
        clients.pop(client_id, None)


async def game_loop() -> None:
    while True:
        update_bots()
        update_clients()
        check_collisions()
        await broadcast_state()
        await asyncio.sleep(TICK_RATE)


async def websocket_handler(websocket, path) -> None:
    client_id = generate_id()
    clients[client_id] = {
        'id': client_id,
        'ws': websocket,
        'name': 'Player',
        'color': random_color(),
        'x': random.uniform(200, WORLD_SIZE - 200),
        'y': random.uniform(200, WORLD_SIZE - 200),
        'mass': 20.0,
        'vx': 0.0,
        'vy': 0.0,
        'targetX': None,
        'targetY': None,
        'joined': False,
        'dead': False,
    }

    await websocket.send(json.dumps({
        'type': 'welcome',
        'id': client_id,
        'worldSize': WORLD_SIZE,
        'players': [public_player_state(client) for client in clients.values()],
        'bots': [
            {
                'id': bot['id'],
                'x': bot['x'],
                'y': bot['y'],
                'mass': bot['mass'],
                'color': bot['color'],
                'name': bot['name'],
            }
            for bot in bots
        ],
        'food': food,
    }))

    try:
        async for msg in websocket:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            if data.get('type') == 'join':
                name = str(data.get('name', 'Player')).strip()[:16]
                clients[client_id]['name'] = name or 'Player'
                clients[client_id]['joined'] = True
                clients[client_id]['dead'] = False
                # Reset position and mass on respawn
                clients[client_id]['x'] = random.uniform(200, WORLD_SIZE - 200)
                clients[client_id]['y'] = random.uniform(200, WORLD_SIZE - 200)
                clients[client_id]['mass'] = 20.0
                clients[client_id]['vx'] = 0.0
                clients[client_id]['vy'] = 0.0
            elif data.get('type') == 'move':
                target_x = data.get('x')
                target_y = data.get('y')
                if isinstance(target_x, (int, float)) and isinstance(target_y, (int, float)):
                    clients[client_id]['targetX'] = clamp(float(target_x), 0, WORLD_SIZE)
                    clients[client_id]['targetY'] = clamp(float(target_y), 0, WORLD_SIZE)
    finally:
        clients.pop(client_id, None)


async def cleanup_background_tasks(task) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


class StaticFileHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == '/' or self.path == '':
            file_path = PUBLIC_DIR / 'index.html'
        else:
            file_path = PUBLIC_DIR / self.path.lstrip('/')
        
        if file_path.exists() and file_path.is_file():
            mime_type, _ = guess_type(str(file_path))
            mime_type = mime_type or 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-type', mime_type)
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        pass  # Suppress logging


def run_http_server() -> None:
    server = HTTPServer(('localhost', PORT), StaticFileHandler)
    print(f'HTTP server running at http://localhost:{PORT}')
    server.serve_forever()


async def run_ws_server() -> None:
    game_task = asyncio.create_task(game_loop())
    async with websockets.serve(websocket_handler, 'localhost', WS_PORT):
        print(f'WebSocket server running at ws://localhost:{WS_PORT}')
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            pass
        finally:
            await cleanup_background_tasks(game_task)


def main() -> None:
    if not food:
        spawn_food()
    if not bots:
        spawn_bots()

    # Start HTTP server in a background thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Start WebSocket server and game loop
    print(f'Starting server on http://localhost:{PORT}')
    try:
        asyncio.run(run_ws_server())
    except KeyboardInterrupt:
        print('Server stopped')


if __name__ == '__main__':
    main()
