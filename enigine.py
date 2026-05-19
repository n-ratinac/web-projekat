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
        # IZMENA: iterira kroz sve ćelije igrača — svaka ćelija jede hranu posebno
        # (pre: koristilo player.x/y/mass što je samo cells[0], split ćelije nisu jele)
        radius_factor = cfg['game'].get('radius_factor', 4)
        base_gain = cfg['food'].get('base_mass_gain', 1)
        percent_gain = cfg['food'].get('percent_mass_gain', 0.01)

        for cell in player.cells:
            cell_radius = math.sqrt(cell.mass) * radius_factor
            eaten = []

            for food in self.food:
                dx = cell.x - food["x"]
                dy = cell.y - food["y"]
                distance = math.sqrt(dx * dx + dy * dy)
                food_radius = 5

                if distance < cell_radius + food_radius:
                    eaten.append(food)
                    # Balansiranje rasta mase preko config-a
                    # Formula: fiksni gain + (procenat trenutne mase)
                    cell.mass += (base_gain + (cell.mass * percent_gain))

            for food in eaten:
                if food in self.food:
                    self.food.remove(food)

    def decay_mass(self, player, dt):
        # IZMENA: iterira kroz sve ćelije — svaka ćelija gubi masu posebno
        # (pre: koristilo player.mass što je samo cells[0])
        min_mass = cfg['player'].get('initial_mass', 20)
        decay_rate = cfg['player'].get('mass_decay_rate', 0.01)

        for cell in player.cells:
            if cell.mass > min_mass:
                loss = cell.mass * decay_rate * dt
                cell.mass = max(min_mass, cell.mass - loss)

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

        # DODATO: granice mape za split ćelije — strogo neophodna zavisnost
        # (bez ovoga split ćelije izlaze van granica mape)
        for cell in player.cells[1:]:
            cell_radius = math.sqrt(cell.mass) * radius_factor
            if cell.x < cell_radius: cell.x = cell_radius
            if cell.y < cell_radius: cell.y = cell_radius
            if cell.x > self.x - cell_radius: cell.x = self.x - cell_radius
            if cell.y > self.y - cell_radius: cell.y = self.y - cell_radius

    def merge_cells(self, player):
        # DODATO: spaja ćelije istog igrača nakon isteka merge_cooldown perioda
        # Ćelija se ne može spojiti dok nije dovoljno "stara" (birth_time)
        if len(player.cells) <= 1:
            return

        merge_cooldown = cfg['player'].get('merge_cooldown', 15)
        radius_factor = cfg['game'].get('radius_factor', 4)
        now = time.time()

        i = 0
        while i < len(player.cells):
            j = i + 1
            while j < len(player.cells):
                c1 = player.cells[i]
                c2 = player.cells[j]

                age_ok = (now - c1.birth_time > merge_cooldown and
                          now - c2.birth_time > merge_cooldown)
                if age_ok:
                    dx = c1.x - c2.x
                    dy = c1.y - c2.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    r1 = math.sqrt(c1.mass) * radius_factor
                    r2 = math.sqrt(c2.mass) * radius_factor

                    if distance < (r1 + r2) * 0.8:
                        c1.mass += c2.mass
                        c1.birth_time = now
                        player.cells.pop(j)
                        continue
                j += 1
            i += 1