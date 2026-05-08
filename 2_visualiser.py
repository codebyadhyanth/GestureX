import cv2
import serial
import numpy as np

# 🔌 Match Arduino
ser = serial.Serial('COM3', 115200)

# Canvas
width, height = 800, 600
canvas = np.zeros((height, width, 3), dtype=np.uint8)

x, y = width // 2, height // 2
prev_x, prev_y = x, y

# tuning
sensitivity = 0.4
dead_zone = 2

while True:
    line = ser.readline().decode().strip()

    try:
        if not line or "Roll" in line:
            continue

        roll, pitch = map(float, line.split(",")[:2])

        # dead zone
        dx = roll if abs(roll) > dead_zone else 0
        dy = pitch if abs(pitch) > dead_zone else 0

        # update position
        x += int(dx * sensitivity)
        y += int(dy * sensitivity)

        # keep inside screen
        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))

        # draw line (smooth trail)
        cv2.line(canvas, (prev_x, prev_y), (x, y), (0, 255, 0), 2)

        prev_x, prev_y = x, y

    except:
        pass

    # show
    cv2.imshow("Air Trace", canvas)

    key = cv2.waitKey(1)

    if key == 27:  # ESC
        break
    elif key == ord('c'):  # clear screen
        canvas[:] = 0

cv2.destroyAllWindows()