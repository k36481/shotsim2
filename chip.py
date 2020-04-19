class Chip(object):
    # pixel corrd
    pos_x = 0
    pos_y = 0
    # chip corrd
    x = 0
    y = 0
    contact_cnt = 0
    selected = False
    marked = False

    def __init__(self, x, y, x_, y_):
        self.pos_x = x
        self.pos_y = y
        self.x = x_
        self.y = y_

    def Pos(self):
        return self.pos_x, self.pos_y

    def Coord(self):
        return self.x, self.y

    def get_selected(self):
        return self.selected

    def set_selected(self, b):
        self.selected = b

    def GetMarked(self):
        return self.marked

    def SetMarked(self, b):
        self.marked = b

    def set_contact_cnt(self, i):
        self.contact_cnt = i

    def get_contact_cnt(self):
        return self.contact_cnt
