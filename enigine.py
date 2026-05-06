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
        player_radius = math.sqrt(player.mass) * 4
        eaten = []

        for food in self.food:
            dx = player.x - food["x"]
            dy = player.y - food["y"]
            distance = math.sqrt(dx * dx + dy * dy)
            food_radius = 5

            if distance < player_radius + food_radius:
                eaten.append(food)
                mass_gain = 1 + (player.mass * 0.01)
                player.mass += mass_gain

        for food in eaten:
            self.food.remove(food)

    def decay_mass(self, player, dt):

        MIN_MASS = 20
        DECAY_RATE = 0.01

        if player.mass > MIN_MASS:
            loss = player.mass * DECAY_RATE * dt
            player.mass = max(MIN_MASS, player.mass - loss)

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)

    def move_player(self, player, direction, dt):
        player.move(direction, dt)

        player_radius = math.sqrt(player.mass) * 4
        if player.x < player_radius: player.x = player_radius
        if player.y < player_radius: player.y = player_radius
        if player.x > self.x - player_radius: player.x = self.x - player_radius
        if player.y > self.y - player_radius: player.y = self.y - player_radius