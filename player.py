class Player:
    def __init__(self, ime, x=0.0, y=0.0):
        self.ime = ime
        self.x = float(x)
        self.y = float(y)

    def move(self, smer):
        # 'smer' je vektor od 2 dimenzije, npr. (dx, dy)
        dx, dy = smer
        
        # Dodajemo komponente vektora na trenutnu poziciju
        self.x += dx
        self.y += dy

    def __str__(self):
        # Formatiramo ispis na dve decimale radi lakšeg čitanja
        return f"Igrač: {self.ime} | Pozicija: ({self.x:.2f}, {self.y:.2f})"