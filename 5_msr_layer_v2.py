import serial
import cv2
import numpy as np
import time
import math

ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)

W, H = 800, 600
canvas = np.zeros((H, W, 3), dtype=np.uint8)

CENTER_X, CENTER_Y = W//2, H//2

x, y = CENTER_X, CENTER_Y
px, py = x, y

path = []

vx, vy = 0, 0

scale = 0.001
motion_threshold = 3000

last_motion_time = time.time()
IDLE_TIME = 0.5

def reset_to_center():
    global x, y, px, py, vx, vy
    x, y = CENTER_X, CENTER_Y
    px, py = x, y
    vx, vy = 0, 0


def detect_shape(path):
    if len(path) < 60:
        return None

    start = path[0]
    end = path[-1]

    straight = math.dist(start, end)

    total = sum(math.dist(path[i], path[i-1]) for i in range(1, len(path)))

    xs = [p[0] for p in path]
    ys = [p[1] for p in path]

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    if straight < 60 and width > 80 and height > 80:
        return "CIRCLE"

    if straight / (total + 1e-6) > 0.85:
        return "LINE"

    return None


while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    try:
        if not line or "Roll" in line:
            continue

        data = list(map(float, line.split(",")))

        ax, ay, az = data[2], data[3], data[4]

        motion = abs(ax) + abs(ay)

        # 🟢 ACTIVE MOTION
        if motion > motion_threshold:

            last_motion_time = time.time()

            dx = ax * scale
            dy = ay * scale

            vx = vx * 0.7 + dx
            vy = vy * 0.7 + dy

            x += int(vx)
            y += int(vy)

            x = max(0, min(W-1, x))
            y = max(0, min(H-1, y))

            cv2.line(canvas, (px, py), (x, y), (0, 255, 0), 2)

            px, py = x, y

            path.append((x, y))

            if len(path) > 120:
                path.pop(0)

        # 🔵 IDLE STATE → RESET TO CENTER
        if time.time() - last_motion_time > IDLE_TIME:

            if len(path) > 50:
                shape = detect_shape(path)

                if shape:
                    print("GESTURE:", shape)

            path.clear()
            reset_to_center()

        cv2.imshow("CENTER MSR SYSTEM", canvas)

        if cv2.waitKey(1) == 27:
            break

    except:
        pass

cv2.destroyAllWindows()