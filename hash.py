import math


class Hash(object):

    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.grid = {}

    def key(self, pos):
        cell_size = self.cell_size
        return (
            int((math.floor(pos[0] / cell_size)) * cell_size),
            int((math.floor(pos[1] / cell_size)) * cell_size)
        )

    def keys(self, pos):
        cell_size = self.cell_size
        keys = []
        for i in range(-1, 2):
            for j in range(-1, 2):
                key = (
                    int((math.floor(pos[0] / cell_size)) * cell_size) + i * cell_size,
                    int((math.floor(pos[1] / cell_size)) * cell_size) + j * cell_size
                )
                keys.append(key)
        return keys

    def insert(self, chip):
        for k in self.keys(chip.Pos()):
            if k not in self.grid:
                self.grid[k] = []
            self.grid[k].append(chip)

    def query(self, pos):
        return self.grid.get(self.key(pos))
