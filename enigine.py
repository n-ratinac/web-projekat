import random
import time
import math
from settings import cfg

class Engine:
    def __init__(self, x, y):
        self.x = x 
        self.y = y 
        self.players = []
        self.food = []
        random.seed(time.time())

    def spawn_food(self, max_food=None):
        # Ako nije prosleđeno, uzmi iz config-a
        if max_food is None:
            max_food = cfg['food'].get('max_food_count', 150)
            
        while len(self.food) < max_food:
            self.food.append({
                "x": random.randint(20, self.x - 20),
                "y": random.randint(20, self.y - 20),
                "id": random.getrandbits(32)
            })

    def eat_food(self, player):
        radius_factor = cfg['game'].get('radius_factor', 4)
        player_radius = math.sqrt(player.mass) * radius_factor
        eaten = []

        for food in self.food:
            dx = player.x - food["x"]
            dy = player.y - food["y"]
            distance = math.sqrt(dx * dx + dy * dy)
            food_radius = 5

            if distance < player_radius + food_radius:
                eaten.append(food)
                # Balansiranje rasta mase preko config-a
                # Formula: fiksni gain + (procenat trenutne mase)
                base_gain = cfg['food'].get('base_mass_gain', 1)
                percent_gain = cfg['food'].get('percent_mass_gain', 0.01)
                
                player.mass += (base_gain + (player.mass * percent_gain))

        for food in eaten:
            self.food.remove(food)

    def decay_mass(self, player, dt):
        min_mass = cfg['player'].get('initial_mass', 20)
        decay_rate = cfg['player'].get('mass_decay_rate', 0.01)

        if player.mass > min_mass:
            loss = player.mass * decay_rate * dt
            player.mass = max(min_mass, player.mass - loss)

    def resolve_player_collisions(self):
        eaten_players = []
        
        radius_factor = cfg['game'].get('radius_factor', 4)
        eat_ratio = cfg['game'].get('eat_mass_ratio', 1.25)
        
        for i in range(len(self.players)):
            p1 = self.players[i]
            if p1 in eaten_players: 
                continue
            
            for j in range(i + 1, len(self.players)):
                p2 = self.players[j]
                if p2 in eaten_players: 
                    continue
                
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                r1 = math.sqrt(p1.mass) * radius_factor
                r2 = math.sqrt(p2.mass) * radius_factor
                
                # p1 jede p2
                if p1.mass >= p2.mass * eat_ratio:
                    if distance < r1:
                        p1.mass += p2.mass
                        eaten_players.append(p2)
                        
                # p2 jede p1
                elif p2.mass >= p1.mass * eat_ratio:
                    if distance < r2:
                        p2.mass += p1.mass
                        eaten_players.append(p1)
                        break 
                        
        for p in eaten_players:
            self.remove_player(p)
            
        return eaten_players
        
    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)

    def move_player(self, player, direction, dt):
        player.move(direction, dt)

        radius_factor = cfg['game'].get('radius_factor', 4)
        player_radius = math.sqrt(player.mass) * radius_factor
        
        # Granice mape
        if player.x < player_radius: player.x = player_radius
        if player.y < player_radius: player.y = player_radius
        if player.x > self.x - player_radius: player.x = self.x - player_radius
        if player.y > self.y - player_radius: player.y = self.y - player_radius