import asyncio
import socketio
from aiohttp import web

# Inicijalizacija servera
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Rečnik u kom čuvamo stanje svih igrača
players = {}

@sio.event
async def connect(sid, environ):
    print(f"Klijent spojen: {sid}")

@sio.event
async def join(sid, data):
    # Dodajemo igrača u rečnik sa osnovnim podacima
    players[sid] = {
        "id": sid,
        "name": data.get("name", "Player"),
        "x": 2000, 
        "y": 2000,
        "hue": data.get("hue", 0)
    }

@sio.event
async def update_input(sid, data):
    # Ažuriramo poziciju koju klijent šalje
    if sid in players:
        players[sid]["x"] = data["x"]
        players[sid]["y"] = data["y"]

@sio.event
async def disconnect(sid):
    if sid in players:
        del players[sid]
        print(f"Klijent izašao: {sid}")

# Glavna petlja koja kuca 20 puta u sekundi
async def broadcast_loop():
    while True:
        if players:
            # Šaljemo listu svih igrača svim povezanim klijentima
            await sio.emit('game_state', list(players.values()))
        # 1 sekunda / 20 tickova = 0.05 sekundi pauze
        await asyncio.sleep(0.05)

if __name__ == '__main__':
    sio.start_background_task(broadcast_loop)
    web.run_app(app, host='0.0.0.0', port=8080)