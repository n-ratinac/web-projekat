import asyncio
import websockets
import json
import random
import string

WORLD_WIDTH = 2000
WORLD_HEIGHT = 2000

players = {}  # { websocket: { id, x, y, name, color } }

COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
    "#BB8FCE", "#85C1E9", "#82E0AA", "#F1948A",
]

def generate_id(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def random_player_state(name="Igrač"):
    return {
        "id": generate_id(),
        "x": random.randint(50, WORLD_WIDTH - 50),
        "y": random.randint(50, WORLD_HEIGHT - 50),
        "name": name,
        "color": random.choice(COLORS),
    }

async def broadcast(message: dict, exclude=None):
    """Pošalji poruku svim konektovanim igračima osim exclude."""
    data = json.dumps(message)
    targets = [ws for ws in players if ws != exclude]
    if targets:
        await asyncio.gather(*[ws.send(data) for ws in targets], return_exceptions=True)

async def handler(websocket):
    # Novi igrač se konektovao
    state = random_player_state()
    players[websocket] = state

    print(f"[+] Igrač {state['name']} ({state['id']}) konektovan na ({state['x']}, {state['y']})")

    # Pošalji novom igraču njegovo stanje + listu svih postojećih igrača
    await websocket.send(json.dumps({
        "type": "init",
        "self": state,
        "players": [s for ws, s in players.items() if ws != websocket],
    }))

    # Obavesti ostale igrače o novom igraču
    await broadcast({
        "type": "player_joined",
        "player": state,
    }, exclude=websocket)

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            # Klijent želi da promeni ime
            if msg_type == "set_name":
                new_name = str(msg.get("name", "Igrač"))[:20].strip() or "Igrač"
                players[websocket]["name"] = new_name
                await broadcast({
                    "type": "player_updated",
                    "player": players[websocket],
                })

            # Klijent šalje update pozicije (za buduću upotrebu)
            elif msg_type == "move":
                players[websocket]["x"] = msg.get("x", players[websocket]["x"])
                players[websocket]["y"] = msg.get("y", players[websocket]["y"])
                await broadcast({
                    "type": "player_moved",
                    "id": players[websocket]["id"],
                    "x": players[websocket]["x"],
                    "y": players[websocket]["y"],
                }, exclude=websocket)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        state = players.pop(websocket, None)
        if state:
            print(f"[-] Igrač {state['name']} ({state['id']}) diskonektovan")
            await broadcast({
                "type": "player_left",
                "id": state["id"],
            })

async def main():
    print("=== Agar.io Server ===")
    print(f"Svet: {WORLD_WIDTH}x{WORLD_HEIGHT}")
    print("Slušam na ws://localhost:8765 ...")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # radi zauvek

if __name__ == "__main__":
    asyncio.run(main())
