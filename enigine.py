class Engine:
    def __init__(self, x,y):
        self.x = x
        self.y = y
        self.players= []

    def start(self):
        print(f"{self.name} engine started.")

    def stop(self):
        print(f"{self.name} engine stopped.")
    
    def add_player(self, player):
        self.players.append(player)
        print(f"Player {player.name} added to the engine.")

    def move_player(self, player , direction):
        player.move(direction)