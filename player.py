import math

BASE_SPEED = 200 
BASE_MASS  = 20    
MIN_SPEED  = 50    

class Player:
    def __init__(self, name, x, y):
        self.name = name
        self.x = x
        self.y = y
        self.mass = BASE_MASS

    @property
    def speed(self):
        return max(MIN_SPEED, BASE_SPEED * math.sqrt(BASE_MASS / self.mass))

    def move(self, direction, dt):
        dx, dy = direction
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt