import serial
import cv2
import numpy as np
import math
import time

ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)

w, h = 800, 600
canvas = np.zeros((h, w, 3), dtype=np.uint8)

x, y = w // 2, h // 2
px, py = x, y

scale = 0.0008
threshold = 2000

while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    try:
        if not line or "Roll" in line:
            continue

        data = list(map(float, line.split(",")))

        # skip roll/pitch
        ax, ay, az = data[2], data[3], data[4]

        # motion magnitude (IMPORTANT PART)
        motion = math.sqrt(ax*ax + ay*ay + az*az)

        if motion > threshold:

            dx = ax * scale
            dy = ay * scale

            x += int(dx)
            y += int(dy)

            x = max(0, min(w-1, x))
            y = max(0, min(h-1, y))

            cv2.line(canvas, (px, py), (x, y), (0, 255, 0), 2)
            px, py = x, y

    except:
        pass

    cv2.imshow("Motion Trace", canvas)

    if cv2.waitKey(1) == 27:
        break

cv2.destroyAllWindows()