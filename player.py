import math
import time
from settings import cfg

# ─── DODATO: Cell klasa — strogo neophodna zavisnost za split ────────────────────
class Cell:
    def __init__(self, x, y, mass):
        self.x = x
        self.y = y
        self.mass = mass
        self.birth_time = time.time()  # DODATO: potrebno za merge cooldown
# ─────────────────────────────────────────────────────────────────────────────────

class Player:
    def __init__(self, name, x, y):
        """
        Inicijalizacija igrača koristeći vrednosti iz config.json.
        """
        self.name = name
        # Vučemo početnu masu iz config-a
        # IZMENA: self.x, self.y, self.mass su sada @property-ji koji delegiraju
        # na cells[0] — strogo neophodna zavisnost kako bi engine.py i dalje
        # radio nepromenjeno (pristupa player.x, player.y, player.mass direktno)
        self.cells = [Cell(x, y, cfg['player']['initial_mass'])]

    # DODATO: @property-ji za backward kompatibilnost — engine.py radi
    # sa player.x, player.y, player.mass bez ikakvih izmena u engine.py logici
    @property
    def x(self):
        return self.cells[0].x

    @x.setter
    def x(self, value):
        self.cells[0].x = value

    @property
    def y(self):
        return self.cells[0].y

    @y.setter
    def y(self, value):
        self.cells[0].y = value

    @property
    def mass(self):
        return self.cells[0].mass

    @mass.setter
    def mass(self, value):
        self.cells[0].mass = value

    @property
    def total_mass(self):
        return sum(cell.mass for cell in self.cells)

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

        # DODATO: pomera sve split ćelije — strogo neophodna zavisnost
        # (bez ovoga split ćelije ostaju zamrznute na mestu)
        for cell in self.cells[1:]:
            base_speed = cfg['player']['base_speed']
            base_mass  = cfg['player']['initial_mass']
            min_speed  = cfg['player']['min_speed']
            cell_speed = max(min_speed, base_speed * math.sqrt(base_mass / cell.mass))
            cell.x += dx * cell_speed * dt
            cell.y += dy * cell_speed * dt

    def to_dict(self):
       
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "mass": self.mass,
            "speed": self.speed
        }

    # DODATO: split metoda — direktna split funkcionalnost iz 'commit' grane
    def split(self):
        new_cells = []
        for cell in self.cells:
            if cell.mass >= 40:
                cell.mass /= 2
                shift = math.sqrt(cell.mass) * 4
                new_cells.append(Cell(cell.x + shift, cell.y + shift, cell.mass))
        self.cells.extend(new_cells)