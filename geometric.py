import math


def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2)


def is_point_in_rect(p, x1, x2, y1, y2, margin = 3):
    return min(x1, x2)-margin <= p[0] <= max(x1, x2)+margin and min(y1, y2)-margin <= p[1] <= max(y1, y2)+margin
