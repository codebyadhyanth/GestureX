import serial
import cv2
import numpy as np
import time
import math

ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)

ser.reset_input_buffer()

# ---------------- CANVAS ----------------
W, H = 800, 600
canvas = np.zeros((H, W, 3), dtype=np.uint8)

CENTER_X, CENTER_Y = W // 2, H // 2

x, y = CENTER_X, CENTER_Y
px, py = x, y

path = []

# ---------------- MOTION STATE ----------------
vx, vy = 0.0, 0.0

scale = 0.0004          # 🔥 reduced sensitivity
alpha = 0.85            # 🔥 smoothing factor

motion_threshold = 3500
dead_zone = 400

last_motion_time = time.time()
IDLE_TIME = 0.6


# ---------------- RESET ----------------
def reset_to_center():
    global x, y, px, py, vx, vy, canvas, path

    x, y = CENTER_X, CENTER_Y
    px, py = x, y
    vx, vy = 0.0, 0.0
    path.clear()

    # clear canvas
    canvas[:] = 0


# ---------------- SHAPE DETECTION ----------------
def detect_shape(path):
    if len(path) < 60:
        return None

    start = path[0]
    end = path[-1]

    straight = math.dist(start, end)
    total = sum(math.dist(path[i], path[i - 1]) for i in range(1, len(path)))

    xs = [p[0] for p in path]
    ys = [p[1] for p in path]

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    # LINE
    if straight / (total + 1e-6) > 0.86:
        return "LINE"

    # CIRCLE
    if straight < 80 and width > 80 and height > 80:
        return "CIRCLE"

    return None


# ---------------- MAIN LOOP ----------------
while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    try:
        # -------- FILTER BAD LINES --------
        if not line or "," not in line:
            continue

        if "rst" in line or "load" in line or "ets" in line:
            continue

        parts = line.split(",")

        if len(parts) < 5:
            continue

        try:
            data = list(map(float, parts))
        except:
            continue

        ax, ay, az = data[2], data[3], data[4]

        # -------- DEAD ZONE FILTER --------
        if abs(ax) < dead_zone:
            ax = 0
        if abs(ay) < dead_zone:
            ay = 0

        motion = abs(ax) + abs(ay)

        # ---------------- ACTIVE MOTION ----------------
        if motion > motion_threshold:

            last_motion_time = time.time()

            dx = ax * scale
            dy = ay * scale

            # 🔥 SMOOTH VELOCITY (low-pass filter)
            vx = vx * alpha + dx
            vy = vy * alpha + dy

            # 🔥 smoother position update (important fix)
            x = int(x + vx * 0.6)
            y = int(y + vy * 0.6)

            x = max(0, min(W - 1, x))
            y = max(0, min(H - 1, y))

            # draw only if movement is real
            if abs(vx) + abs(vy) > 0.5:
                cv2.line(canvas, (px, py), (x, y), (0, 255, 0), 2)

            px, py = x, y

            path.append((x, y))

            if len(path) > 120:
                path.pop(0)

        # ---------------- IDLE → ANALYZE ----------------
        if time.time() - last_motion_time > IDLE_TIME:

            if len(path) > 60:
                gesture = detect_shape(path)
                if gesture:
                    print("GESTURE:", gesture)

            reset_to_center()

        cv2.imshow("STABLE GESTURE TRACKER", canvas)

        if cv2.waitKey(1) == 27:
            break

    except Exception as e:
        print("Error:", e)

cv2.destroyAllWindows()