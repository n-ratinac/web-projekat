class Player:
    def __init__(self, name, x, y, speed=4):
        self.name = name
        self.x = x
        self.y = y
        self.speed = speed

    def move(self, direction):
        """
        direction: tuple (dx, dy), normalized floats from the client.
        Multiplied by speed to get actual pixel movement per tick.
        """
        dx, dy = direction
        self.x += dx * self.speed
        self.y += dy * self.speed