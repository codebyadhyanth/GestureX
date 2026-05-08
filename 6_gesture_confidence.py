import serial
import cv2
import numpy as np
import time
import math

ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)

W, H = 800, 600
canvas = np.zeros((H, W, 3), dtype=np.uint8)

CENTER_X, CENTER_Y = W // 2, H // 2

x, y = CENTER_X, CENTER_Y
px, py = x, y

path = []

vx, vy = 0, 0

scale = 0.001
motion_threshold = 3000

last_motion_time = time.time()
IDLE_TIME = 0.5


# ---------------- RESET ----------------
def reset_to_center():
    global x, y, px, py, vx, vy, canvas

    x, y = CENTER_X, CENTER_Y
    px, py = x, y
    vx, vy = 0, 0

    # 🧹 CLEAR CANVAS (FIXED)
    canvas[:] = 0


# ---------------- SHAPE DETECTION + CONFIDENCE ----------------
def detect_shape_with_confidence(path):
    if len(path) < 60:
        return None, 0.0

    start = path[0]
    end = path[-1]

    straight = math.dist(start, end)
    total = sum(math.dist(path[i], path[i - 1]) for i in range(1, len(path)))

    xs = [p[0] for p in path]
    ys = [p[1] for p in path]

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    # ---------------- LINE ----------------
    line_score = straight / (total + 1e-6)

    if line_score > 0.85:
        confidence = min(1.0, line_score)
        return "LINE", confidence

    # ---------------- CIRCLE ----------------
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)

    radius_variance = sum(
        abs(math.dist(p, (center_x, center_y)) - np.mean([math.dist(p, (center_x, center_y)) for p in path]))
        for p in path
    ) / len(path)

    circle_score = 1 / (1 + radius_variance)

    if straight < 80 and width > 80 and height > 80:
        confidence = min(1.0, circle_score)
        return "CIRCLE", confidence

    return None, 0.0


# ---------------- MAIN LOOP ----------------
while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    try:
        if not line or "Roll" in line:
            continue

        # 🧹 ignore junk lines
        if "," not in line:
            continue

        parts = line.split(",")

        # must have at least 5 values (ax, ay, az etc.)
        if len(parts) < 5:
            continue

        try:
            data = list(map(float, parts))
        except:
            continue
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

            x = max(0, min(W - 1, x))
            y = max(0, min(H - 1, y))

            cv2.line(canvas, (px, py), (x, y), (0, 255, 0), 2)

            px, py = x, y

            path.append((x, y))

            if len(path) > 120:
                path.pop(0)

        # 🔵 IDLE STATE → ANALYZE + RESET
        if time.time() - last_motion_time > IDLE_TIME:

            if len(path) > 50:
                gesture, confidence = detect_shape_with_confidence(path)

                if gesture:
                    if confidence > 0.6:
                        print(f"GESTURE: {gesture} | CONFIDENCE: {confidence:.2f}")
                    else:
                        print(f"WEAK GESTURE: {gesture} | CONFIDENCE: {confidence:.2f}")

            path.clear()
            reset_to_center()

        cv2.imshow("CENTER MSR SYSTEM", canvas)

        if cv2.waitKey(1) == 27:
            break

    except Exception as e:
        print("Error:", e)

cv2.destroyAllWindows()