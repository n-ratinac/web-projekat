import asyncio
import websockets
import json
import random
import string

WORLD_WIDTH = 2000
WORLD_HEIGHT = 2000
FOOD_COUNT = 150
PLAYER_START_RADIUS = 22

players = {} 
food = []

COLORS = [
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#96CEB4",
    "#FFEAA7",
    "#DDA0DD",
    "#98D8C8",
    "#F7DC6F",
    "#BB8FCE",
    "#85C1E9",
    "#82E0AA",
    "#F1948A"
]

def generate_id(length=6):
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=length
        )
    )

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
        await asyncio.gather(
            *[ws.send(data) for ws in targets],
            return_exceptions=True
        )


async def send_leaderboard():

    leaderboard = sorted(
        [
            {
                "id": p["id"],
                "name": p["name"],
                "radius": round(p["radius"], 1)
            }
            for p in players.values()
        ],
        key=lambda x: x["radius"],
        reverse=True
    )[:10]

    await broadcast({
        "type": "leaderboard",
        "players": leaderboard
    })


async def handler(websocket):

    state = random_player_state()

    players[websocket] = state

    print(f"[+] Igrač povezan: {state['id']}")
    await websocket.send(json.dumps({
        "type": "init",
        "self": state,
        "players": [
            s for ws, s in players.items()
            if ws != websocket
        ],
        "food": food
    }))

    await broadcast({
        "type": "player_joined",
        "player": state
    }, exclude=websocket)

    await send_leaderboard()

    try:

        async for raw in websocket:

            msg = json.loads(raw)


            if msg.get("type") == "move":

                p = players[websocket]

                p["x"] = msg.get("x", p["x"])
                p["y"] = msg.get("y", p["y"])

                for item in food[:]:

                    dist = (
                        (p["x"] - item["x"]) ** 2 +
                        (p["y"] - item["y"]) ** 2
                    ) ** 0.5

                    if dist < p["radius"]:

                        food.remove(item)

                        p["radius"] += 0.6

                        new_item = generate_food_item()

                        food.append(new_item)

                        await broadcast({
                            "type": "food_update",
                            "eaten": item["id"],
                            "new_item": new_item,
                            "eater": p["id"],
                            "new_radius": p["radius"]
                        })

                        await send_leaderboard()

                await broadcast({
                    "type": "player_moved",
                    "id": p["id"],
                    "x": p["x"],
                    "y": p["y"],
                    "radius": p["radius"]
                }, exclude=websocket)

            elif msg.get("type") == "set_name":

                players[websocket]["name"] = str(
                    msg.get("name", "Igrač")
                )[:15]

                await broadcast({
                    "type": "player_updated",
                    "player": players[websocket]
                })

                await send_leaderboard()

    except Exception as e:

        print("Greška:", e)

    finally:

        state = players.pop(websocket, None)

        if state:

            print(f"[-] Igrač izašao: {state['name']}")

            await broadcast({
                "type": "player_left",
                "id": state["id"]
            })

            await send_leaderboard()


async def main():

    async with websockets.serve(
        handler,
        "localhost",
        8765
    ):

        print("Server running on ws://localhost:8765")

        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())