import random
import time
class Engine:
    def __init__(self, x, y):
        self.x = x 
        self.y = y 
        self.players = []
        self.food = []  # Lista koja čuva koordinate hrane
        random.seed(time.time())
    def spawn_food(self, max_food=150):
        # Dodaje hranu dok ne dostigne limit
        while len(self.food) < max_food:
            self.food.append({
                "x": random.randint(20, self.x - 20),
                "y": random.randint(20, self.y - 20),
                "id": random.getrandbits(32)
            })
    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)

    def move_player(self, player, direction, dt):
        # Prvo pomeri igrača koristeći njegovu move metodu
        player.move(direction, dt)
    
        # Definisanje granica mape (4000x4000)[cite: 13, 15]
        radius = 20 # Pretpostavljeni radijus igrača
    
        # Clamp logika: Drži igrača unutar koordinata[cite: 15]
        if player.x < radius: player.x = radius
        if player.y < radius: player.y = radius
        if player.x > self.x - radius: player.x = self.x - radius
        if player.y > self.y - radius: player.y = self.y - radius