class Player:
    def __init__(self, name, x, y, speed=200):
        self.name = name
        self.x = x
        self.y = y
        # speed is now in pixels per second (not pixels per tick)
        self.speed = speed
 
    def move(self, direction, dt):
        """
        direction: tuple (dx, dy), normalized floats from the client.
        dt: delta time in seconds since the last tick.
        Movement = direction * speed * dt, making it tick-rate independent.
        """
        dx, dy = direction
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt