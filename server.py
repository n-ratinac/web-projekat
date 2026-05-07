"""
server.py — Multiplayer WebSocket server za agar.io klon
Pokretanje: python server.py
Zahteva: pip install websockets
"""

import asyncio
import json
import math
import random
import time
import websockets
from websockets.server import WebSocketServerProtocol

# ─── CONFIG ───────────────────────────────────────────────────────────────────
WORLD         = 4000
FOOD_COUNT    = 0  # privremeno isključeno
VIRUS_COUNT   = 18
TICK_RATE     = 1 / 20        # 60 ticks/s
DECAY_RATE    = 0.0001
DECAY_THRESH  = 200
MERGE_TIME    = 10.0          # sekunde
EJECT_COST    = 18
EJECT_MASS    = 14
SPLIT_MIN     = 36
MAX_SPLITS    = 16
VIRUS_SPLIT_M = 133

HOST = "0.0.0.0"
PORT = 8765

# ─── UTILS ────────────────────────────────────────────────────────────────────
def rnd(a, b):   return random.uniform(a, b)
def rndint(a,b): return random.randint(a, b-1)
def dist(a, b):  return math.hypot(a["x"]-b["x"], a["y"]-b["y"])
def mass_to_r(m):return math.sqrt(m / math.pi) * 4
def clamp(v,lo,hi): return max(lo, min(hi, v))

# ─── GAME STATE ───────────────────────────────────────────────────────────────
food    = []     # list of dicts
viruses = []     # list of dicts
players = {}     # ws -> player dict

next_food_id   = 0
next_virus_id  = 0
next_player_id = 0

def new_food_id():
    global next_food_id
    next_food_id += 1
    return next_food_id

def new_virus_id():
    global next_virus_id
    next_virus_id += 1
    return next_virus_id

def new_player_id():
    global next_player_id
    next_player_id += 1
    return next_player_id

# ─── INIT ─────────────────────────────────────────────────────────────────────
def make_food():
    r = random.random()
    mass = 1 if r < 0.6 else (3 if r < 0.9 else 5)
    return {
        "id":  new_food_id(),
        "x":   rnd(20, WORLD-20),
        "y":   rnd(20, WORLD-20),
        "mass": mass,
        "r":   mass_to_r(mass),
        "hue": rndint(0, 360),
        "ejected": False,
        "vx": 0, "vy": 0,
    }

def make_virus():
    mass = 100
    return {
        "id":  new_virus_id(),
        "x":   rnd(100, WORLD-100),
        "y":   rnd(100, WORLD-100),
        "mass": mass,
        "r":   mass_to_r(mass),
        "spikes": 12,
        "fed": 0,
    }

def spawn_food(n):
    global food
    for _ in range(n):
        food.append(make_food())

def spawn_viruses():
    global viruses
    viruses = [make_virus() for _ in range(VIRUS_COUNT)]

def make_player_cell(x, y, mass, hue, name):
    return {
        "x": x, "y": y,
        "mass": mass,
        "r": mass_to_r(mass),
        "hue": hue,
        "name": name,
        "vx": 0, "vy": 0,
        "mergeTimer": 0.0,
    }

def make_player(name):
    """Kreira igrača na NASUMIČNIM koordinatama."""
    hue = rndint(0, 360)
    # nasumična pozicija (100px od ivice)
    x = rnd(100, WORLD - 100)
    y = rnd(100, WORLD - 100)
    pid = new_player_id()
    return {
        "id":   pid,
        "name": name,
        "hue":  hue,
        "dead": False,
        "cells": [make_player_cell(x, y, 50, hue, name)],
        "target_x": x,
        "target_y": y,
    }

# ─── PHYSICS ──────────────────────────────────────────────────────────────────
def update_cell(c, tx, ty, dt):
    dx = tx - c["x"]
    dy = ty - c["y"]
    d  = math.hypot(dx, dy) or 1
    sp = (16 / math.sqrt(c["mass"])) * 60 * dt
    nx, ny = dx/d, dy/d
    c["vx"] = (c["vx"] + nx*sp*0.5) * 0.95
    c["vy"] = (c["vy"] + ny*sp*0.5) * 0.95
    maxSp = (15 / math.sqrt(c["mass"])) * 3
    spd = math.hypot(c["vx"], c["vy"])
    if spd > maxSp:
        c["vx"] *= maxSp / spd
        c["vy"] *= maxSp / spd
    c["x"] = clamp(c["x"] + c["vx"], c["r"], WORLD - c["r"])
    c["y"] = clamp(c["y"] + c["vy"], c["r"], WORLD - c["r"])
    c["r"] = mass_to_r(c["mass"])
    if c["mass"] > DECAY_THRESH:
        c["mass"] -= c["mass"] * DECAY_RATE * dt * 60
        if c["mass"] < DECAY_THRESH:
            c["mass"] = DECAY_THRESH
    if c["mergeTimer"] > 0:
        c["mergeTimer"] -= dt

def merge_cells(cells):
    i = 0
    while i < len(cells):
        j = i + 1
        while j < len(cells):
            a, b = cells[i], cells[j]
            if a["mergeTimer"] <= 0 and b["mergeTimer"] <= 0:
                d = dist(a, b)
                if d < a["r"] + b["r"] - min(a["r"], b["r"]) * 0.5:
                    a["mass"] += b["mass"]
                    a["r"] = mass_to_r(a["mass"])
                    cells.pop(j)
                    continue
            j += 1
        i += 1

def update_ejected_food(dt):
    global food
    for f in food:
        if not f["ejected"]:
            continue
        f["x"] = clamp(f["x"] + f["vx"], f["r"], WORLD - f["r"])
        f["y"] = clamp(f["y"] + f["vy"], f["r"], WORLD - f["r"])
        f["vx"] *= 0.9
        f["vy"] *= 0.9
        for v in viruses:
            if dist(f, v) < v["r"] + f["r"]:
                f["ejected"] = False
                f["mass"] = 1
                v["fed"] += 1
                if v["fed"] >= 7:
                    v["fed"] = 0
                    viruses.append(make_virus())
    while len(food) < FOOD_COUNT:
        food.append(make_food())

def eat_food(cells):
    global food
    new_food = []
    for f in food:
        eaten = False
        for c in cells:
            if dist(c, f) < c["r"]:
                c["mass"] += f["mass"]
                eaten = True
                break
        if not eaten:
            new_food.append(f)
    food[:] = new_food

def check_virus_collision(cells):
    for v in viruses:
        for c in cells:
            if c["mass"] > VIRUS_SPLIT_M and dist(c, v) < c["r"]:
                if len(cells) < MAX_SPLITS:
                    pop_cell(c, cells)

def pop_cell(c, cell_array):
    if c not in cell_array:
        return
    pops = min(8, MAX_SPLITS - len(cell_array) + 1)
    orig_mass = c["mass"]
    c["mass"] = orig_mass / (pops + 1)
    c["mergeTimer"] = MERGE_TIME
    for i in range(pops):
        angle = (i / pops) * math.pi * 2
        child = make_player_cell(c["x"], c["y"], orig_mass/(pops+1), c["hue"], c["name"])
        child["vx"] = math.cos(angle) * (8/math.sqrt(child["mass"])) * 8
        child["vy"] = math.sin(angle) * (8/math.sqrt(child["mass"])) * 8
        child["mergeTimer"] = MERGE_TIME
        cell_array.append(child)

def check_eating_between_players(dt):
    """Igrači jedu jedni druge."""
    all_players = list(players.values())
    for p in all_players:
        if p["dead"]: continue
        # jede hranu
        # eat_food(p["cells"])  # privremeno isključeno
        check_virus_collision(p["cells"])
        # jede ćelije drugih igrača
        for other in all_players:
            if other is p or other["dead"]: continue
            survived = []
            for prey in other["cells"]:
                eaten = False
                for pred in p["cells"]:
                    if pred["mass"] > prey["mass"]*1.15 and dist(pred,prey) < pred["r"] - prey["r"]*0.3:
                        pred["mass"] += prey["mass"]
                        eaten = True
                        break
                if not eaten:
                    survived.append(prey)
            other["cells"] = survived
            if not other["cells"]:
                other["dead"] = True

# ─── MAIN TICK ────────────────────────────────────────────────────────────────
async def game_loop():
    last = time.monotonic()
    while True:
        now = time.monotonic()
        dt  = now - last
        last = now

        # update svaki živi igrač
        for p in list(players.values()):
            if p["dead"]: continue
            for c in p["cells"]:
                update_cell(c, p["target_x"], p["target_y"], dt)
            if len(p["cells"]) > 1:
                merge_cells(p["cells"])

        update_ejected_food(dt)  # privremeno isključeno
        check_eating_between_players(dt)

        # broadcast stanje svim klijentima
        state = build_state()
        dead_ids = [p["id"] for p in players.values() if p["dead"]]

        to_remove = []
        for ws, p in list(players.items()):
            try:
                msg = {"type": "state", "state": state}
                if p["dead"]:
                    msg["you_died"] = True
                await ws.send(json.dumps(msg))
                if p["dead"]:
                    to_remove.append(ws)
            except Exception:
                to_remove.append(ws)

        for ws in to_remove:
            players.pop(ws, None)

        await asyncio.sleep(TICK_RATE)

def build_state():
    return {
        "food": [],  # privremeno isključeno
        # "food": [
        #     {"id":f["id"],"x":f["x"],"y":f["y"],"r":f["r"],"hue":f["hue"]}
        #     for f in food
        # ],
        "viruses": [
            {"id":v["id"],"x":v["x"],"y":v["y"],"r":v["r"]}
            for v in viruses
        ],
        "players": [
            {
                "id":   p["id"],
                "name": p["name"],
                "hue":  p["hue"],
                "cells":[
                    {"x":c["x"],"y":c["y"],"r":c["r"],"mass":c["mass"],"name":c["name"]}
                    for c in p["cells"]
                ],
            }
            for p in players.values() if not p["dead"]
        ],
    }

# ─── WS HANDLER ───────────────────────────────────────────────────────────────
async def handler(ws: WebSocketServerProtocol):
    player = None
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            mtype = msg.get("type")

            if mtype == "join":
                name = (msg.get("name") or "Player")[:16]
                player = make_player(name)
                players[ws] = player
                await ws.send(json.dumps({
                    "type": "joined",
                    "id":   player["id"],
                    "x":    player["cells"][0]["x"],
                    "y":    player["cells"][0]["y"],
                    "hue":  player["hue"],
                }))

            elif mtype == "move" and player and not player["dead"]:
                player["target_x"] = float(msg.get("x", player["target_x"]))
                player["target_y"] = float(msg.get("y", player["target_y"]))

            elif mtype == "split" and player and not player["dead"]:
                new_cells = []
                tx = player["target_x"]
                ty = player["target_y"]
                for c in player["cells"]:
                    if c["mass"] < SPLIT_MIN * 2: continue
                    if len(player["cells"]) + len(new_cells) >= MAX_SPLITS: break
                    dx = tx - c["x"]; dy = ty - c["y"]
                    d  = math.hypot(dx, dy) or 1
                    half = c["mass"] / 2
                    c["mass"] = half
                    c["mergeTimer"] = MERGE_TIME
                    child = make_player_cell(c["x"], c["y"], half, c["hue"], c["name"])
                    child["vx"] = (dx/d) * (8/math.sqrt(half)) * 12
                    child["vy"] = (dy/d) * (8/math.sqrt(half)) * 12
                    child["mergeTimer"] = MERGE_TIME
                    new_cells.append(child)
                player["cells"].extend(new_cells)

            elif mtype == "eject" and player and not player["dead"]:
                tx = player["target_x"]
                ty = player["target_y"]
                for c in player["cells"]:
                    if c["mass"] < EJECT_COST + 20: continue
                    dx = tx - c["x"]; dy = ty - c["y"]
                    d  = math.hypot(dx, dy) or 1
                    c["mass"] -= EJECT_COST
                    ef = make_food()
                    ef["x"] = c["x"] + (dx/d)*(c["r"]+5)
                    ef["y"] = c["y"] + (dy/d)*(c["r"]+5)
                    ef["mass"] = EJECT_MASS
                    ef["r"]    = mass_to_r(EJECT_MASS)
                    ef["hue"]  = c["hue"]
                    ef["vx"]   = (dx/d) * 8
                    ef["vy"]   = (dy/d) * 8
                    ef["ejected"] = True
                    food.append(ef)

            elif mtype == "respawn" and player:
                # ponovo se pojavljuje na nasumičnim koordinatama
                x = rnd(100, WORLD-100)
                y = rnd(100, WORLD-100)
                player["dead"] = False
                player["cells"] = [make_player_cell(x, y, 50, player["hue"], player["name"])]
                player["target_x"] = x
                player["target_y"] = y
                players[ws] = player
                await ws.send(json.dumps({
                    "type": "respawned",
                    "x": x, "y": y,
                }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        players.pop(ws, None)

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
async def main():
    # spawn_food(FOOD_COUNT)  # privremeno isključeno
    spawn_viruses()
    print(f"[server] Pokrenuto na ws://{HOST}:{PORT}")
    async with websockets.serve(handler, HOST, PORT):
        await game_loop()

if __name__ == "__main__":
    asyncio.run(main())
