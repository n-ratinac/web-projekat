class Engine:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)

    def move_player(self, player, direction, dt):
        player.move(direction, dt)