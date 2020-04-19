import math

def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2)

for i in range(10,100):
    for j in range(10, 100):
        if distance((i,j),(45,45))<30:
            print(i,j)