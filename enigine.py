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
        """
        Checks if the player overlaps any food item.
        If yes: removes the food and increases player mass based on their current mass.
        Player radius = sqrt(mass) * 4  (same formula as the client uses)
        """
        player_radius = math.sqrt(player.mass) * 4
        eaten = []

        for food in self.food:
            dx = player.x - food["x"]
            dy = player.y - food["y"]
            distance = math.sqrt(dx * dx + dy * dy)
            food_radius = 5  # matches client arc radius

            if distance < player_radius + food_radius:
                eaten.append(food)
                
                # Formula: Vrednost hrane opada kako masa igrača raste.
                # Sa početnom masom 20, igrač dobija 0.5 mase po hrani.
                # Sa masom 100, dobija 0.1 mase po hrani.
                # Donja granica je 0.05 (nikada ne pada ispod toga).
                mass_gain = 1 + (player.mass * 0.01)
                player.mass += mass_gain

        for food in eaten:
            self.food.remove(food)

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)

    def move_player(self, player, direction, dt):
        player.move(direction, dt)

        # Clamp player inside map bounds using actual radius
        player_radius = math.sqrt(player.mass) * 4
        if player.x < player_radius: player.x = player_radius
        if player.y < player_radius: player.y = player_radius
        if player.x > self.x - player_radius: player.x = self.x - player_radius
        if player.y > self.y - player_radius: player.y = self.y - player_radius