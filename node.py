class Node(object):
    pos = (10, 10)
    size = (100, 100)
    active = False

    def __init__(self, pos=(10, 10), size=(100, 100)):
        self.pos = pos
        self.size = size

    def get_pos(self):
        return self.pos

    def set_pos(self, pos):
        self.pos = pos

    def get_size(self):
        return self.size

    def set_size(self, size):
        self.size = size

    def is_overlap(self, point):
        h = (point[0] >= self.pos[0]) and (point[0] <= self.pos[0] + self.size[0])
        w = (point[1] >= self.pos[1]) and (point[1] <= self.pos[1] + self.size[1])
        return h and w
