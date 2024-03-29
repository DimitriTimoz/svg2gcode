import math
from random import randint
from xmlrpc.client import MAXINT
from svgelements import *

secZ=1.
depth=-.2

t_diamteter=.25
px, pz, py = 0, 0, 0
scale=1

header="""%{}
(Made by D. Timoz)

(Generated by svg2gcode.py)
""".format(randint(0,MAXINT))
target_size = (23, 23) # (width, height) in mm 
origin = (11.5,11.5) # an origin offset in mm
print("Name of the file to convert in G-Code:")
file=input()
svg = SVG.parse(file)
scale = target_size[0]/svg.width
nl = 1
file = file.removesuffix('.svg')
f=open(file+".gcode", "a")
f.truncate(0)
def write(*s):
    global nl
    f = open( file + ".gcode", "a")
    print('N',nl*10, end=" ", sep="",file=f)
    for e in s:
        print(e, end="", sep="",file=f)
    print(file=f)
    nl += 1
def make_bezier(xys):
    # xys should be a sequence of 2-tuples (Bezier control points)
    n = len(xys)
    combinations = pascal_row(n-1)
    def bezier(ts):
        # This uses the generalized formula for bezier curves
        # http://en.wikipedia.org/wiki/B%C3%A9zier_curve#Generalization
        result = []
        for t in ts:
            tpowers = (t**i for i in range(n))
            upowers = reversed([(1-t)**i for i in range(n)])
            coefs = [c*a*b for c, a, b in zip(combinations, tpowers, upowers)]
            result.append(
                tuple(sum([coef*p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
        return result
    return bezier

def pascal_row(n, memo={}):
    # This returns the nth row of Pascal's Triangle
    if n in memo:
        return memo[n]
    result = [1]
    x, numerator = 1, n
    for denominator in range(1, n//2+1):
        x *= numerator
        x /= denominator
        result.append(x)
        numerator -= 1
    if n&1 == 0:
        # n is even
        result.extend(reversed(result[:-1]))
    else:
        result.extend(reversed(result))
    memo[n] = result
    return result


def length(points):
    vectorized = [vectorize(p.x, p.y) for p in points]
    l=0.1
    for i in range(1,len(vectorized)):
        l += ((vectorized[i][0]-vectorized[i-1][0])**2 + (vectorized[i][1]-vectorized[i-1][1])**2)**0.5
    return l

def vectorize(x, y):
    x, y = scale*x, scale*y
    x, y = (x-origin[0], y-origin[1])
    return x, y
    
def draw_circle(cx, cy, r):
    r =  r * scale
    cx, cy = vectorize(cx, cy)
    #get start position
    sx = cx - r
    sy = cy 
    
    #get opposite position
    ox = cx + r
    oy = cy 
    #G-CODE
    move_to_safe(sx, sy)
    move_to(sx,sy, depth)
    write("G3 X{:.2f} Y{:.2f} R{:.2f}".format(ox, oy, r))
    write("G3 X{:.2f} Y{:.2f} R{:.2f}".format(sx, sy, r))
    write("G0 X{:.2f} Y{:.2f} Z{:.2f}".format(sx, sy, secZ))

def draw_rect(x,y,w,h):
    w, h = w*scale, h*scale
    x,y = vectorize(x,y)
    move_to_safe(x,y)
    move_to(x, y, depth)
    move_to(x+w, y, depth)
    move_to(x+w, y+h, depth)
    move_to(x, y+h, depth)
    move_to(x, y, depth)
    move_to_safe(x,y)

def move_to(x,y, z):
    write("G1 X{:.2f} Y{:.2f} Z{:.2f}".format(x,y,z))
    px, py, pz = x, y, z

def move_to_safe(x,y):
    write("G0 Z{:.2f}".format(secZ))
    write("G0 X{:.2f} Y{:.2f} Z{:.2f}".format(x,y,secZ))
    px, py, pz = x, y, secZ
    

def draw_line(x1,y1,x2,y2,b_p=True):
    x1, y1 = vectorize(x1, y1)
    x2, y2 = vectorize(x2, y2)
    if b_p:
        move_to_safe(x1, y1)
    move_to(x1, y1, depth)
    move_to(x2, y2, depth)
    if b_p:
        move_to_safe(x2,y2)
        
def draw_arc(x1, y1, x2, y2, r, delta):
    r =  r * scale
    x1, y1 = vectorize(x1, y1)
    x2, y2 = vectorize(x2, y2)
    if delta > 0:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
    move_to_safe(x1,y1)
    move_to(x1,y1, depth)
    write("G2 X{:.2f} Y{:.2f} R{:.2f}".format(x2,y2, r))
    write("G0 Z{:.2f}".format( secZ))
    px, py, pz = x2, y2, secZ
    
def draw_path(path):
    for e in path:
        if type(e) == Move:
            for p in e:
                p.x, p.y = vectorize(p.x, p.y)
                move_to_safe(p.x,p.y)
        elif type(e) == Line:
            draw_line(e[0].x, e[0].y, e[1].x, e[1].y, b_p=False)
        elif type(e) == CubicBezier:
            l = length(list(e))
            pas = (l*0.75)/(t_diamteter*4)
            func = make_bezier(list(e))
            ts = [t/pas for t in range(int(pas)+1)]
            points = func(ts)
            p0 = points[0]
            for p in points[1:]:
                draw_line(p0[0], p0[1], p[0], p[1], b_p=False)
                p0 = p
        #elif type(e) == Arc:
        #    e: Arc = e
        #    draw_arc(e.start[0], e.start[1], e.end[0], e.end[1], sum(e.radius)/2, e.delta)
        elif type(e) == Close:
            e: Close = e
            draw_line(e.start[0], e.start[1], e.end[0], e.end[1], b_p=False)
        else:
            write("")
            write("(ERROR: " + str(type(e)) + ")")
            print("ERROR: " + str(type(e)))
    move_to_safe(px, py)

def foreach(els):
    for el in els:
        if type(el) == SimpleLine:
            draw_line(el.x1,el.y1,el.x2,el.y2)        
        elif type(el) == Ellipse:
            write("")
            e: Ellipse = el
            draw_circle(e.cx, e.cy, e.rx)
            
        elif type(el) == Circle:
            e: Circle = el
            r = float(e.values['r'])
            draw_circle(el.cx,el.cy,r)
        elif type(el) == svgelements.Arc:
            continue
        elif type(el) == Rect:
            draw_rect(el.x, el.y, el.width, el.height)
        elif type(el) == Path:
            draw_path(el)
        elif type(el) == Group:
            e: Group = el
            foreach(e)
        else:
            write("(ERROR: " + str(type(el)) + ")")
write(header)
foreach(svg)    

write("G0 Z100")
write("M2")


