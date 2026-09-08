"""Authored one-stage flight, independent of VDP packing and player rendering.

This demo bakes camera/world projection into ROM. A future game can reuse these
event definitions and replace autopilot() with live input; no collisions yet.
Coordinates are world units until projected by generate.py.
"""
from dataclasses import dataclass
import math

FPS = 30
FRAMES = 1536
HORIZON = 96
FOCAL = 180.0
CAMERA_HEIGHT = 14.0


@dataclass(frozen=True)
class Event:
    pass_frame: int
    kind: str
    x: float
    altitude: float
    height: float
    phase: float = 0.0


PHASES = [
    {"id": 0, "name": "Unexpected levitation", "start": 0, "end": 120},
    {"id": 1, "name": "The orbital pantry", "start": 120, "end": 900},
    {"id": 2, "name": "His Extremely Fishy Majesty", "start": 900, "end": 1320},
    {"id": 3, "name": "Enlightenment, apparently", "start": 1320, "end": FRAMES},
]

# Irregular, hand-authored formations instead of an endlessly repeating loop.
EVENTS = [Event(180+i*24, 'can' if i%3==0 else 'fish',
                (-1 if i%2==0 else 1)*(18+(i%3)*5),
                3 if i%3==0 else 10+(i%4)*4,
                29+(i%4)*3, i*.79) for i in range(33)]


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3-2*t)


def travel(frame):
    """Shared ground/object travel; units advance monotonically."""
    # Almost three times the initial version's world speed; no video speed-up.
    return frame * 1.85 + .0002 * min(frame, 1000)**2


def scene(frame):
    return next(p['id'] for p in PHASES if p['start'] <= frame < p['end'])


def autopilot(frame):
    """Return onscreen left, top, per-strip width and total height."""
    if frame < 120:
        q = smooth(frame / 75)
        stride = round(18 - 2*q)
        height = round(72 - 8*q)
        cx = 128 + 24*math.sin(frame/32)*q
        top = round(182 - 60*q)
    elif frame < 1320:
        stride, height = 16, 64
        cx = 128 + 48*math.sin(frame/47) + 10*math.sin(frame/19)
        top = round(119 + 13*math.sin(frame/39) + 5*math.sin(frame/17))
        if frame >= 990:
            cx = 128 + 54*math.sin(frame/39)
            top += 3
    else:
        q = smooth((frame-1370)/140)
        stride = round(16 - 10*q)
        height = round(64 - 40*q)
        cx = 128 + (1-q)*44*math.sin(frame/42)
        top = round(126 - 42*q + (1-q)*3*math.sin(frame/19))
    return round(cx-stride*1.5), top, stride, height


def world_objects(frame):
    """Nearest first. One shared projection governs floor and flying props."""
    objects = []
    if 75 <= frame < 970:
        for e in EVENTS:
            z = travel(e.pass_frame) + 18 - travel(frame)
            if not 18 <= z <= 350:
                continue
            # Prop hover is explicit; the ground still uses the shared travel.
            altitude = e.altitude + (2.5*math.sin(frame/29+e.phase) if e.kind == 'fish' else 0)
            scale = FOCAL / z
            h = min(240, round(e.height*scale))
            w = max(2, round(h/2))
            cx = 128 + e.x*scale
            bottom = HORIZON + (CAMERA_HEIGHT-altitude)*scale
            if cx+w/2 < -10 or cx-w/2 > 266:
                continue
            objects.append(dict(kind=e.kind, x=round(cx-w/2), y=round(bottom-h), w=w, h=h, z=z))
    objects.sort(key=lambda e: e['z'])
    return objects[:3]


def boss(frame):
    if not 900 <= frame < 1330:
        return None
    q = smooth((frame-900)/170)
    h = round(8 + 158*q)
    w = round(h/2)
    cx = 128 + 48*math.sin((frame-900)/33)*q
    top = round(64 - 48*q + 9*math.sin(frame/21)*q)
    if frame >= 1260:
        retreat = smooth((frame-1260)/70)
        h = round(h*(1-retreat))
        w = max(1, round(h/2))
        top = round(top-45*retreat)
    return dict(kind='boss', x=round(cx-w/2), y=top, w=max(4,w), h=max(4,h))


def laser_active(frame):
    return (120 <= frame < 890 and frame%42 < 30) or 1030 <= frame < 1280
