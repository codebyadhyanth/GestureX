import serial
import cv2
import numpy as np
import time
import math

ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)

W, H = 800, 600
canvas = np.zeros((H, W, 3), dtype=np.uint8)

x, y = W//2, H//2
px, py = x, y

path = []
MAX_PATH = 120

vx, vy = 0, 0
scale = 0.001

motion_threshold = 3000

last_motion_time = time.time()
GESTURE_TIMEOUT = 0.4  # seconds of inactivity = gesture end

def detect_shape(path):
    if len(path) < 60:
        return None

    start = path[0]
    end = path[-1]

    xs = [p[0] for p in path]
    ys = [p[1] for p in path]

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    straight = math.dist(start, end)

    total = 0
    for i in range(1, len(path)):
        total += math.dist(path[i], path[i-1])

    # CIRCLE
    if straight < 60 and width > 80 and height > 80:
        return "CIRCLE"

    # LINE
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

        # 🟢 ACTIVE MOTION PHASE
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

            if len(path) > MAX_PATH:
                path.pop(0)

        # 🔵 MSR TRIGGER (gesture ended)
        if time.time() - last_motion_time > GESTURE_TIMEOUT:

            if len(path) > 50:
                shape = detect_shape(path)

                if shape:
                    print("GESTURE:", shape)

            path.clear()

        cv2.imshow("MSR Layer Active", canvas)

        if cv2.waitKey(1) == 27:
            break

    except:
        pass

cv2.destroyAllWindows()