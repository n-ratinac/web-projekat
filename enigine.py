import random
import time
import math

class Engine:
    def __init__(self, x, y):
        self.x = x 
        self.y = y 
        self.players = []
        self.food = []
        random.seed(time.time())

    def spawn_food(self, max_food=150):
        while len(self.food) < max_food:
            self.food.append({
                "x": random.randint(20, self.x - 20),
                "y": random.randint(20, self.y - 20),
                "id": random.getrandbits(32)
            })

    def eat_food(self, player):
        # Moramo proveriti svaku ćeliju igrača posebno
        for cell in player.cells:
            cell_radius = math.sqrt(cell.mass) * 4
            eaten = []

            for food in self.food:
                dx = cell.x - food["x"]
                dy = cell.y - food["y"]
                distance = math.sqrt(dx * dx + dy * dy)
                food_radius = 5

                if distance < cell_radius + food_radius:
                    eaten.append(food)
                    # Svaka ćelija raste posebno
                    mass_gain = 1 + (cell.mass * 0.01)
                    cell.mass += mass_gain

            for food in eaten:
                if food in self.food:
                    self.food.remove(food)

    def move_player(self, player, direction, dt):
        # Pomera svaku ćeliju igrača
        for cell in player.cells:
            dx, dy = direction
            
            # Brzina zavisi od mase te konkretne ćelije
            speed = max(50, 200 * math.sqrt(20 / cell.mass)) 
            
            cell.x += dx * speed * dt
            cell.y += dy * speed * dt

            # Granice mape za svaku ćeliju
            radius = math.sqrt(cell.mass) * 4
            if cell.x < radius: cell.x = radius
            if cell.y < radius: cell.y = radius
            if cell.x > self.x - radius: cell.x = self.x - radius
            if cell.y > self.y - radius: cell.y = self.y - radius
            
    def decay_mass(self, player, dt):
        MIN_MASS = 20
        DECAY_RATE = 0.01
        for cell in player.cells:
            if cell.mass > MIN_MASS:
                loss = cell.mass * DECAY_RATE * dt
                cell.mass = max(MIN_MASS, cell.mass - loss)
    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)
    def merge_cells(self, player):
        if len(player.cells) <= 1:
            return

        now = time.time()
        MERGE_COOLDOWN = 15  # Koliko sekundi mora da prođe pre spajanja
        
        merged_any = False
        i = 0
        while i < len(player.cells):
            j = i + 1
            while j < len(player.cells):
                c1 = player.cells[i]
                c2 = player.cells[j]

                # Provera vremena: obe ćelije moraju biti "starije" od 15s
                if (now - c1.birth_time > MERGE_COOLDOWN and 
                    now - c2.birth_time > MERGE_COOLDOWN):
                    
                    dx = c1.x - c2.x
                    dy = c1.y - c2.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    
                    # Ako se dodiruju (rastojanje manje od zbira radijusa)
                    if distance < (c1.radius + c2.radius) * 0.8:
                        c1.mass += c2.mass # Spoji masu u prvu ćeliju
                        c1.birth_time = now # Resetuj vreme (opciono)
                        player.cells.pop(j) # Izbaci drugu ćeliju
                        merged_any = True
                        continue # Nastavi proveru bez povećanja j
                j += 1
            i += 1
   