import math
from settings import cfg

class Player:
    def __init__(self, name, x, y):
        """
        Inicijalizacija igrača koristeći vrednosti iz config.json.
        """
        self.name = name
        self.x = x
        self.y = y
        # Vučemo početnu masu iz config-a
        self.mass = cfg['player']['initial_mass']

    @property
    def speed(self):
        
        base_speed = cfg['player']['base_speed']
        base_mass = cfg['player']['initial_mass']
        min_speed = cfg['player']['min_speed']
        
        # Kalkulacija brzine
        calculated_speed = base_speed * math.sqrt(base_mass / self.mass)
        
        # Obezbeđujemo da igrač ne uspori ispod granice definisane u config-u
        return max(min_speed, calculated_speed)

    def move(self, direction, dt):
       
        dx, dy = direction
        
        # Koristimo @property speed za kretanje
        current_speed = self.speed
        
        self.x += dx * current_speed * dt
        self.y += dy * current_speed * dt

    def to_dict(self):
       
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "mass": self.mass,
            "speed": self.speed
        }