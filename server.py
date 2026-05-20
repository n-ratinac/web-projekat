import asyncio
import websockets
import json
import random
import string
import math

WORLD_W = 2000
WORLD_H = 2000
FOOD_COUNT = 150
START_R = 22.0
VIRUS_COUNT = 10
VIRUS_R = 50
MAX_PIECES = 16
MERGE_TIME_BASE = 10.0
MERGE_TIME_MF = 0.008
PIECE_R_MIN = 8
TICK_RATE = 20

COLORS = ["#FF6B6B","#4ECDC4","#45B7D1","#96CEB4","#FFEAA7","#DDA0DD",
          "#98D8C8","#F7DC6F","#BB8FCE","#85C1E9","#82E0AA","#F1948A"]

# ── Food ──────────────────────────────────────────────────────────────────────
food_by_id = {}
food_grid  = {}
CELL = 100

def _cell(x, y): return (int(x) // CELL, int(y) // CELL)
def _gid(n=6): return ''.join(random.choices(string.ascii_uppercase+string.digits, k=n))
def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v
def mt(r): return MERGE_TIME_BASE + MERGE_TIME_MF * r * r

def food_add(item):
    food_by_id[item["id"]] = item
    food_grid.setdefault(_cell(item["x"], item["y"]), set()).add(item["id"])

def food_remove(fid):
    item = food_by_id.pop(fid, None)
    if item:
        food_grid.get(_cell(item["x"], item["y"]), set()).discard(fid)

def food_nearby(x, y, r):
    cells = math.ceil(r / CELL) + 1
    cx, cy = int(x) // CELL, int(y) // CELL
    out = []
    for dx in range(-cells, cells+1):
        for dy in range(-cells, cells+1):
            for fid in list(food_grid.get((cx+dx, cy+dy), ())):
                item = food_by_id.get(fid)
                if item: out.append(item)
    return out

def new_food():
    return {"id":_gid(8), "x":random.randint(15,WORLD_W-15),
            "y":random.randint(15,WORLD_H-15), "color":random.choice(COLORS)}

# ── Init ──────────────────────────────────────────────────────────────────────
for _ in range(FOOD_COUNT): food_add(new_food())

viruses = []
while len(viruses) < VIRUS_COUNT:
    x,y = random.randint(VIRUS_R,WORLD_W-VIRUS_R), random.randint(VIRUS_R,WORLD_H-VIRUS_R)
    if all(math.hypot(x-v["x"],y-v["y"]) > VIRUS_R*2+20 for v in viruses):
        viruses.append({"id":_gid(8),"x":x,"y":y,"radius":VIRUS_R})

players = {}   # ws -> state

# ── Factories ──────────────────────────────────────────────────────────────────
def new_player(name="Igrač"):
    return {"id":_gid(),"x":float(random.randint(100,WORLD_W-100)),
            "y":float(random.randint(100,WORLD_H-100)),
            "tx":1000.0,"ty":1000.0,"name":name,
            "color":random.choice(COLORS),"radius":START_R,"pieces":[]}

def make_piece(oid, x, y, r, vx, vy, name, color):
    return {"id":f"{oid}_{_gid(4)}","x":float(x),"y":float(y),
            "radius":float(r),"vx":float(vx),"vy":float(vy),
            "mt":mt(r),"name":name,"color":color}

# ── Broadcast: jedan await, ne create_task ────────────────────────────────────
async def broadcast(msg, exclude=None):
    if not players: return
    data = json.dumps(msg)
    coros = [ws.send(data) for ws in players if ws != exclude]
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)

# ── Eksplozija ────────────────────────────────────────────────────────────────
def explode(state):
    total_r = math.sqrt(state["radius"]**2 + 100)
    n = min(MAX_PIECES, max(8, int(total_r / 7)))
    total_area = total_r**2
    raw = [random.uniform(0.7,1.3) for _ in range(n)]
    s = sum(raw)
    pieces = []
    for w in raw:
        r = max(PIECE_R_MIN, math.sqrt(w/s*total_area))
        angle = random.uniform(0, 2*math.pi)
        speed = clamp(random.uniform(10,20)*(START_R/max(r,START_R)), 6, 22)
        scatter = r * random.uniform(0.5, 1.5)
        px = clamp(state["x"]+math.cos(angle)*scatter, r, WORLD_W-r)
        py = clamp(state["y"]+math.sin(angle)*scatter, r, WORLD_H-r)
        pieces.append(make_piece(state["id"],px,py,r,
                                  math.cos(angle)*speed,math.sin(angle)*speed,
                                  state["name"],state["color"]))
    state["pieces"] = pieces
    state["radius"] = 0.0

# ── Fizika delova ─────────────────────────────────────────────────────────────
def push_apart(pieces):
    n = len(pieces)
    for i in range(n):
        for j in range(i+1, n):
            pi,pj = pieces[i],pieces[j]
            dx = pj["x"]-pi["x"]; dy = pj["y"]-pi["y"]
            d = math.hypot(dx,dy); md = pi["radius"]+pj["radius"]
            if d < md and d > 0.001:
                push=(md-d)*0.5; nx,ny=dx/d,dy/d
                fi=pj["radius"]/md; fj=pi["radius"]/md
                pi["x"]-=nx*push*fi; pi["y"]-=ny*push*fi
                pj["x"]+=nx*push*fj; pj["y"]+=ny*push*fj

def try_merge(state):
    pieces = state["pieces"]
    changed = True; any_merged = False
    while changed and len(pieces) > 1:
        changed = False
        for i in range(len(pieces)):
            for j in range(i+1, len(pieces)):
                pi,pj = pieces[i],pieces[j]
                if pi["mt"] > 0 or pj["mt"] > 0: continue
                if math.hypot(pi["x"]-pj["x"],pi["y"]-pj["y"]) < pi["radius"]+pj["radius"]:
                    ai=pi["radius"]**2; aj=pj["radius"]**2; tot=ai+aj
                    m = make_piece(state["id"],
                        (pi["x"]*ai+pj["x"]*aj)/tot,(pi["y"]*ai+pj["y"]*aj)/tot,
                        math.sqrt(tot),(pi["vx"]*ai+pj["vx"]*aj)/tot,
                        (pi["vy"]*ai+pj["vy"]*aj)/tot,pi["name"],pi["color"])
                    m["mt"] = 0.0
                    pieces.pop(j); pieces.pop(i); pieces.insert(i,m)
                    changed = any_merged = True; break
            if changed: break
    if len(pieces) == 1:
        state["x"]=pieces[0]["x"]; state["y"]=pieces[0]["y"]
        state["radius"]=pieces[0]["radius"]; state["pieces"]=[]
        any_merged = True
    return any_merged

def update_pieces(state, dt):
    pieces = state["pieces"]
    if not pieces: return False
    tx,ty = state["tx"],state["ty"]
    for pc in pieces:
        if pc["mt"] > 0: pc["mt"] = max(0.0, pc["mt"]-dt)
        pc["vx"]*=0.85; pc["vy"]*=0.85
        dx=tx-pc["x"]; dy=ty-pc["y"]; d=math.hypot(dx,dy)
        if d > 1.0:
            spd=clamp(110.0*(START_R/max(pc["radius"],START_R))**0.5, 35.0, 180.0)
            mv=min(spd*dt,d)
            pc["x"]+=dx/d*mv+pc["vx"]*dt; pc["y"]+=dy/d*mv+pc["vy"]*dt
        else:
            pc["x"]+=pc["vx"]*dt; pc["y"]+=pc["vy"]*dt
        pc["x"]=clamp(pc["x"],pc["radius"],WORLD_W-pc["radius"])
        pc["y"]=clamp(pc["y"],pc["radius"],WORLD_H-pc["radius"])
    push_apart(pieces)
    return try_merge(state)

# ── Game tick — jedan await gather na kraju ────────────────────────────────────
async def game_tick():
    dt = 1.0 / TICK_RATE
    # Sve poruke skupljamo u listu, pa jedan gather na kraju tika
    outbox = []  # lista (data_str, exclude_ws_or_None)

    def queue(msg, exclude=None):
        outbox.append((json.dumps(msg), exclude))

    player_list = list(players.items())

    for ws, state in player_list:
        if not state["pieces"]: continue

        update_pieces(state, dt)

        if state["pieces"]:
            # Jedenje hrane — delovi jedu hranu
            for pc in state["pieces"]:
                for item in food_nearby(pc["x"], pc["y"], pc["radius"]):
                    if math.hypot(pc["x"]-item["x"],pc["y"]-item["y"]) < pc["radius"]:
                        food_remove(item["id"])
                        pc["radius"] = min(pc["radius"]+0.5, 300)
                        nf = new_food(); food_add(nf)
                        queue({"type":"food_update","eaten":item["id"],
                               "new_item":nf,"eater":None,"piece_owner":state["id"]})

            # Jedenje/bivanje jedenim od strane drugih igraca (delovi)
            for ws2, other in player_list:
                if ws2 == ws: continue

                # Deo splitovanog jede normalnog manjeg igraca
                if not other["pieces"] and other["radius"] > 0:
                    for pc in state["pieces"]:
                        if (pc["radius"] > other["radius"] * 1.3 and
                                math.hypot(pc["x"]-other["x"],pc["y"]-other["y"]) < pc["radius"]):
                            pc["radius"] = min(pc["radius"] + other["radius"]*0.2, 300)
                            other["x"] = float(random.randint(100,WORLD_W-100))
                            other["y"] = float(random.randint(100,WORLD_H-100))
                            other["radius"] = START_R
                            queue({"type":"player_eaten",
                                   "eaten_id":other["id"],"eater_id":state["id"],
                                   "eater_new_radius":pc["radius"],
                                   "eaten_new_pos":{"x":other["x"],"y":other["y"],"radius":other["radius"]}})
                            break

                # Normalan igrac jede komad koji je manji
                if not other["pieces"] and other["radius"] > 0:
                    ate_pieces = []
                    for pc in state["pieces"][:]:
                        if (other["radius"] > pc["radius"] * 1.3 and
                                math.hypot(other["x"]-pc["x"],other["y"]-pc["y"]) < other["radius"]):
                            other["radius"] = min(other["radius"] + pc["radius"]*0.2, 500)
                            ate_pieces.append(pc["id"])
                    if ate_pieces:
                        state["pieces"] = [pc for pc in state["pieces"] if pc["id"] not in set(ate_pieces)]
                        queue({"type":"piece_eaten",
                               "owner_id":state["id"],"eater_id":other["id"],
                               "eaten_piece_ids":ate_pieces,"eater_new_radius":other["radius"],
                               "pieces_left":len(state["pieces"])})
                        if not state["pieces"]:
                            state["radius"] = START_R
                            state["x"] = float(random.randint(100,WORLD_W-100))
                            state["y"] = float(random.randint(100,WORLD_H-100))

                # Deo splitovanog jede deo drugog splitovanog
                if other["pieces"]:
                    for pc in state["pieces"]:
                        for pc2 in other["pieces"][:]:
                            if (pc["radius"] > pc2["radius"] * 1.3 and
                                    math.hypot(pc["x"]-pc2["x"],pc["y"]-pc2["y"]) < pc["radius"]):
                                pc["radius"] = min(pc["radius"] + pc2["radius"]*0.2, 300)
                                other["pieces"].remove(pc2)
                                queue({"type":"piece_eaten",
                                       "owner_id":other["id"],"eater_id":state["id"],
                                       "eaten_piece_ids":[pc2["id"]],"eater_new_radius":pc["radius"],
                                       "pieces_left":len(other["pieces"])})
                                if not other["pieces"]:
                                    other["radius"] = START_R
                                    other["x"] = float(random.randint(100,WORLD_W-100))
                                    other["y"] = float(random.randint(100,WORLD_H-100))

            # Kompaktni spu update
            queue({"type":"spu","pid":state["id"],
                   "p":[[round(pc["x"],1),round(pc["y"],1),
                         round(pc["radius"],2),round(pc["mt"],2)]
                        for pc in state["pieces"]]})
        else:
            queue({"type":"player_rejoin","player_id":state["id"],
                   "new_pos":{"x":round(state["x"],1),"y":round(state["y"],1),
                              "radius":round(state["radius"],2)}})

    # Jedan gather za sve poruke ovog tika
    if outbox:
        ws_list = list(players.keys())
        coros = []
        for data, exc in outbox:
            for ws in ws_list:
                if ws != exc:
                    coros.append(ws.send(data))
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

async def tick_loop():
    interval = 1.0 / TICK_RATE
    loop = asyncio.get_event_loop()
    while True:
        t0 = loop.time()
        await game_tick()
        await asyncio.sleep(max(0.0, interval-(loop.time()-t0)))

# ── Handler ───────────────────────────────────────────────────────────────────
async def handler(websocket):
    state = new_player()
    players[websocket] = state

    await websocket.send(json.dumps({"type":"init","self":state,
        "players":[s for ws2,s in players.items() if ws2!=websocket],
        "food":list(food_by_id.values()),"viruses":viruses}))
    await broadcast({"type":"player_joined","player":state}, exclude=websocket)

    try:
        async for raw in websocket:
            msg = json.loads(raw)
            t = msg.get("type","")

            if t == "move":
                p = players[websocket]
                if p["pieces"]:
                    p["tx"] = float(msg.get("x", p["tx"]))
                    p["ty"] = float(msg.get("y", p["ty"]))
                else:
                    p["x"] = clamp(float(msg.get("x",p["x"])), p["radius"], WORLD_W-p["radius"])
                    p["y"] = clamp(float(msg.get("y",p["y"])), p["radius"], WORLD_H-p["radius"])

                    # Hrana
                    for item in food_nearby(p["x"],p["y"],p["radius"]):
                        if math.hypot(p["x"]-item["x"],p["y"]-item["y"]) < p["radius"]:
                            food_remove(item["id"]); p["radius"]=min(p["radius"]+0.6,500)
                            nf=new_food(); food_add(nf)
                            await broadcast({"type":"food_update","eaten":item["id"],
                                             "new_item":nf,"eater":p["id"],"new_radius":p["radius"]})

                    # Virus
                    for v in viruses:
                        if (math.hypot(p["x"]-v["x"],p["y"]-v["y"]) < p["radius"]+v["radius"]*0.45
                                and p["radius"] > v["radius"]):
                            explode(p)
                            p["tx"]=p["pieces"][0]["x"]; p["ty"]=p["pieces"][0]["y"]
                            await broadcast({"type":"player_split","player_id":p["id"],
                                             "pieces":p["pieces"]})
                            break

                    if p["pieces"]: continue

                    # Jedenje normalnih igraca
                    for ws2,other in list(players.items()):
                        if ws2!=websocket and not other["pieces"]:
                            if (math.hypot(p["x"]-other["x"],p["y"]-other["y"]) < p["radius"]
                                    and p["radius"] > other["radius"]*1.3):
                                p["radius"]+=other["radius"]*0.2
                                other["x"]=float(random.randint(100,WORLD_W-100))
                                other["y"]=float(random.randint(100,WORLD_H-100))
                                other["radius"]=START_R
                                await broadcast({"type":"player_eaten",
                                    "eaten_id":other["id"],"eater_id":p["id"],
                                    "eater_new_radius":p["radius"],
                                    "eaten_new_pos":{"x":other["x"],"y":other["y"],"radius":other["radius"]}})

                    await broadcast({"type":"player_moved","id":p["id"],
                                     "x":p["x"],"y":p["y"],"radius":p["radius"]},
                                    exclude=websocket)

            elif t == "set_name":
                players[websocket]["name"] = str(msg.get("name","Igrač"))[:15]
                await broadcast({"type":"player_updated","player":players[websocket]})

    except Exception as e:
        print(f"Err: {e}")
    finally:
        s = players.pop(websocket, None)
        if s: await broadcast({"type":"player_left","id":s["id"]})

async def main():
    print("🚀 ws://localhost:8765")
    asyncio.create_task(tick_loop())
    async with websockets.serve(handler,"localhost",8765):
        print("✅ Spreman!"); await asyncio.Future()

if __name__=="__main__":
    asyncio.run(main())