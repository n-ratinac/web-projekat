const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname);
const WORLD_SIZE = 4000;
const FOOD_COUNT = 800;
const BOT_COUNT = 15;
const TICK_RATE = 1000 / 60; // 60 FPS
const clients = new Map();
const food = [];
const bots = [];

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function randomColor() {
  const hue = Math.floor(Math.random() * 340);
  return `hsl(${hue}, 75%, 55%)`;
}

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

function randomBotName() {
  const names = ['Bot1', 'Bot2', 'Bot3', 'Bot4', 'Bot5', 'Bot6', 'Bot7', 'Bot8', 'Bot9', 'Bot10'];
  return names[Math.floor(Math.random() * names.length)];
}

function massToRadius(mass) {
  return Math.sqrt(mass / Math.PI) * 4;
}

function radiusToMass(radius) {
  return Math.PI * (radius / 4) ** 2;
}

function spawnFood() {
  for (let i = 0; i < FOOD_COUNT; i++) {
    food.push({
      id: generateId(),
      x: Math.random() * (WORLD_SIZE - 100) + 50,
      y: Math.random() * (WORLD_SIZE - 100) + 50,
      mass: Math.random() < 0.8 ? 1 : Math.random() < 0.95 ? 3 : 5,
      color: randomColor(),
    });
  }
}

function spawnBots() {
  for (let i = 0; i < BOT_COUNT; i++) {
    bots.push({
      id: generateId(),
      x: Math.random() * (WORLD_SIZE - 200) + 100,
      y: Math.random() * (WORLD_SIZE - 200) + 100,
      mass: Math.random() * 50 + 20,
      color: randomColor(),
      name: randomBotName(),
      vx: 0,
      vy: 0,
      targetX: Math.random() * WORLD_SIZE,
      targetY: Math.random() * WORLD_SIZE,
      lastThink: Date.now(),
    });
  }
}

function updateBots() {
  const now = Date.now();
  bots.forEach(bot => {
    // Think every 500-1000ms
    if (now - bot.lastThink > Math.random() * 500 + 500) {
      bot.lastThink = now;
      bot.targetX = Math.random() * WORLD_SIZE;
      bot.targetY = Math.random() * WORLD_SIZE;
    }

    // Move towards target
    const dx = bot.targetX - bot.x;
    const dy = bot.targetY - bot.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist > 0) {
      const speed = 2 / Math.sqrt(bot.mass);
      const nx = dx / dist;
      const ny = dy / dist;
      bot.vx += nx * speed * 0.5;
      bot.vy += ny * speed * 0.5;
    }

    // Apply friction
    bot.vx *= 0.85;
    bot.vy *= 0.85;

    // Update position
    bot.x = Math.max(0, Math.min(WORLD_SIZE, bot.x + bot.vx));
    bot.y = Math.max(0, Math.min(WORLD_SIZE, bot.y + bot.vy));

    // Decay mass
    if (bot.mass > 200) {
      bot.mass -= bot.mass * 0.0001;
    }
  });
}

function updateClients() {
  clients.forEach(client => {
    if (client.targetX !== undefined && client.targetY !== undefined) {
      const dx = client.targetX - client.x;
      const dy = client.targetY - client.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist > 0) {
        const speed = 2 / Math.sqrt(client.mass);
        const nx = dx / dist;
        const ny = dy / dist;
        client.vx += nx * speed * 0.5;
        client.vy += ny * speed * 0.5;
      }
    }

    client.vx *= 0.85;
    client.vy *= 0.85;

    client.x = Math.max(0, Math.min(WORLD_SIZE, client.x + client.vx));
    client.y = Math.max(0, Math.min(WORLD_SIZE, client.y + client.vy));

    // Decay mass
    if (client.mass > 200) {
      client.mass -= client.mass * 0.0001;
    }
  });
}

function checkCollisions() {
  // Players eat food
  clients.forEach(client => {
    food.forEach(f => {
      const dx = f.x - client.x;
      const dy = f.y - client.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < massToRadius(client.mass)) {
        client.mass += f.mass;
        f.x = Math.random() * (WORLD_SIZE - 100) + 50;
        f.y = Math.random() * (WORLD_SIZE - 100) + 50;
      }
    });
  });

  // Bots eat food
  bots.forEach(bot => {
    food.forEach(f => {
      const dx = f.x - bot.x;
      const dy = f.y - bot.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < massToRadius(bot.mass)) {
        bot.mass += f.mass;
        f.x = Math.random() * (WORLD_SIZE - 100) + 50;
        f.y = Math.random() * (WORLD_SIZE - 100) + 50;
      }
    });
  });

  // Players eat bots (if bigger)
  clients.forEach(client => {
    bots.forEach(bot => {
      if (client.mass > bot.mass * 1.2) {
        const dx = bot.x - client.x;
        const dy = bot.y - client.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < massToRadius(client.mass)) {
          client.mass += bot.mass;
          bot.x = Math.random() * (WORLD_SIZE - 200) + 100;
          bot.y = Math.random() * (WORLD_SIZE - 200) + 100;
          bot.mass = Math.random() * 50 + 20;
        }
      }
    });
  });

  // Bots eat players (if bigger)
  bots.forEach(bot => {
    clients.forEach(client => {
      if (bot.mass > client.mass * 1.2) {
        const dx = client.x - bot.x;
        const dy = client.y - bot.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < massToRadius(bot.mass)) {
          bot.mass += client.mass;
          client.x = Math.random() * (WORLD_SIZE - 200) + 100;
          client.y = Math.random() * (WORLD_SIZE - 200) + 100;
          client.mass = 20;
        }
      }
    });
  });
}

function send(ws, payload) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  }
}

function broadcast() {
  const allPlayers = Array.from(clients.values()).map(client => ({
    id: client.id,
    x: client.x,
    y: client.y,
    mass: client.mass,
    color: client.color,
    name: client.name,
  }));

  const allBots = bots.map(bot => ({
    id: bot.id,
    x: bot.x,
    y: bot.y,
    mass: bot.mass,
    color: bot.color,
    name: bot.name,
  }));

  const leaderboard = [...allPlayers, ...allBots]
    .sort((a, b) => b.mass - a.mass)
    .slice(0, 10);

  const payload = {
    type: 'state',
    players: allPlayers,
    bots: allBots,
    food: food,
    leaderboard: leaderboard,
    worldSize: WORLD_SIZE,
  };

  for (const client of clients.values()) {
    send(client.ws, payload);
  }
}

const server = http.createServer((req, res) => {
  let filePath = path.join(PUBLIC_DIR, req.url === '/' ? 'index.html' : decodeURIComponent(req.url));

  if (filePath.endsWith(path.sep)) {
    filePath = path.join(filePath, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
  const type = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not found');
      return;
    }

    res.writeHead(200, { 'Content-Type': type });
    res.end(content);
  });
});

const wss = new WebSocket.Server({ noServer: true });

wss.on('connection', (ws) => {
  const id = generateId();
  const client = {
    id,
    x: Math.random() * (WORLD_SIZE - 200) + 100,
    y: Math.random() * (WORLD_SIZE - 200) + 100,
    mass: 20,
    color: randomColor(),
    name: `Player-${id}`,
    vx: 0,
    vy: 0,
    targetX: undefined,
    targetY: undefined,
    ws,
  };

  clients.set(id, client);
  send(ws, {
    type: 'welcome',
    id,
    worldSize: WORLD_SIZE,
    players: Array.from(clients.values()).map(c => ({
      id: c.id,
      x: c.x,
      y: c.y,
      mass: c.mass,
      color: c.color,
      name: c.name,
    })),
    bots: bots.map(b => ({
      id: b.id,
      x: b.x,
      y: b.y,
      mass: b.mass,
      color: b.color,
      name: b.name,
    })),
    food: food,
  });
  broadcast();

  ws.on('message', (message) => {
    let data;
    try {
      data = JSON.parse(message.toString());
    } catch (error) {
      return;
    }

    if (data.type === 'join') {
      client.name = String(data.name || client.name).slice(0, 16) || client.name;
      broadcast();
      return;
    }

    if (data.type === 'move') {
      client.targetX = Number(data.x);
      client.targetY = Number(data.y);
    }
  });

  ws.on('close', () => {
    clients.delete(id);
    broadcast();
  });
});

server.on('upgrade', (req, socket, head) => {
  wss.handleUpgrade(req, socket, head, (ws) => {
    wss.emit('connection', ws, req);
  });
});

// Initialize game
spawnFood();
spawnBots();

// Game loop
setInterval(() => {
  updateBots();
  updateClients();
  checkCollisions();
  broadcast();
}, TICK_RATE);

server.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
