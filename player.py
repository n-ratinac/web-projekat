import math
import time
BASE_SPEED = 200 
BASE_MASS  = 20    
MIN_SPEED  = 50    

class Cell:
    def __init__(self, x, y, mass):
        self.x = x
        self.y = y
        self.mass = mass

    @property
    def speed(self):
        return max(MIN_SPEED, BASE_SPEED * math.sqrt(BASE_MASS / self.mass))

    @property
    def radius(self):
        return math.sqrt(self.mass) * 4

class Player:
    def __init__(self, name, x, y):
        self.name = name
        self.cells = [Cell(x, y, BASE_MASS)]

    import math

BASE_SPEED = 200 
BASE_MASS  = 20    
MIN_SPEED  = 50    

class Cell:
    def __init__(self, x, y, mass):
        self.x = x
        self.y = y
        self.mass = mass
        self.birth_time = time.time()
    @property
    def speed(self):
        return max(MIN_SPEED, BASE_SPEED * math.sqrt(BASE_MASS / self.mass))

    @property
    def radius(self):
        return math.sqrt(self.mass) * 4

class Player:
    def __init__(self, name, x, y):
        self.name = name
        self.cells = [Cell(x, y, BASE_MASS)]

    def split(self):
        new_cells = []
        for cell in self.cells:
            if cell.mass >= 40:  # Minimum za split
                cell.mass /= 2
                # Pomeramo novu ćeliju da se ne preklapaju potpuno
                shift = math.sqrt(cell.mass) * 4
                new_cells.append(Cell(cell.x + shift, cell.y + shift, cell.mass))
        
        self.cells.extend(new_cells)