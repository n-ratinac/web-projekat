import asyncio
import websockets
import json
import random
import string

WORLD_WIDTH = 2000
WORLD_HEIGHT = 2000
FOOD_COUNT = 150
PLAYER_START_RADIUS = 22

players = {}  # { websocket: { id, x, y, name, color, radius } }
food = []

COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9", "#82E0AA", "#F1948A"]

def generate_id(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_food_item():
    return {
        "id": generate_id(8),
        "x": random.randint(15, WORLD_WIDTH - 15),
        "y": random.randint(15, WORLD_HEIGHT - 15),
        "color": random.choice(COLORS)
    }

for _ in range(FOOD_COUNT):
    food.append(generate_food_item())

def random_player_state(name="Igrač"):
    return {
        "id": generate_id(),
        "x": random.randint(100, WORLD_WIDTH - 100),
        "y": random.randint(100, WORLD_HEIGHT - 100),
        "name": name,
        "color": random.choice(COLORS),
        "radius": PLAYER_START_RADIUS
    }

async def broadcast(message: dict, exclude=None):
    data = json.dumps(message)
    targets = [ws for ws in players if ws != exclude]
    if targets:
        await asyncio.gather(*[ws.send(data) for ws in targets], return_exceptions=True)

async def handler(websocket):
    state = random_player_state()
    players[websocket] = state
    print(f"[+] Igrač {state['name']} povezan")

    await websocket.send(json.dumps({
        "type": "init",
        "self": state,
        "players": [s for ws, s in players.items() if ws != websocket],
        "food": food 
    }))

    await broadcast({"type": "player_joined", "player": state}, exclude=websocket)

    try:
        async for raw in websocket:
            msg = json.loads(raw)
            if msg.get("type") == "move":
                p = players[websocket]
                p["x"], p["y"] = msg.get("x", p["x"]), msg.get("y", p["y"])
                
                # Provera hrane i rasta
                for item in food[:]:
                    dist = ((p["x"] - item["x"])**2 + (p["y"] - item["y"])**2)**0.5
                    if dist < p["radius"]:
                        food.remove(item)
                        p["radius"] += 0.6 # Rast
                        new_item = generate_food_item()
                        food.append(new_item)
                        await broadcast({
                            "type": "food_update",
                            "eaten": item["id"],
                            "new_item": new_item,
                            "eater": p["id"],
                            "new_radius": p["radius"]
                        })

                # Provera jedenja drugih igraca
                for ws_other, other in list(players.items()):
                    if ws_other == websocket: continue
                    dist = ((p["x"] - other["x"])**2 + (p["y"] - other["y"])**2)**0.5
                    if dist < p["radius"] and p["radius"] > other["radius"] * 1.25:
                        # Jedemo drugog igraca
                        p["radius"] += other["radius"] * 0.5  # Rast za pola radiusa pojedenog
                        eaten_ws = ws_other
                        eaten_state = players.pop(eaten_ws, None)
                        if eaten_ws:
                            try:
                                await eaten_ws.send(json.dumps({"type": "died"}))
                            except: pass
                        await broadcast({
                            "type": "player_eaten",
                            "eater": p["id"],
                            "eaten": other["id"],
                            "new_radius": p["radius"]
                        })

                await broadcast({
                    "type": "player_moved",
                    "id": p["id"], "x": p["x"], "y": p["y"], "radius": p["radius"]
                }, exclude=websocket)

            elif msg.get("type") == "set_name":
                players[websocket]["name"] = str(msg.get("name", "Igrač"))[:15]
                await broadcast({"type": "player_updated", "player": players[websocket]})
    except: pass
    finally:
        state = players.pop(websocket, None)
        if state: await broadcast({"type": "player_left", "id": state["id"]})

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())