import serial
import time

# 🔌 Match Arduino baud rate
ser = serial.Serial('COM3', 115200, timeout=1)

time.sleep(2)  # allow connection to stabilize

# 🎯 thresholds (tune these)
TILT_THRESHOLD = 15
CENTER_ZONE = 5

last_action = ""

while True:
    try:
        line = ser.readline().decode().strip()

        if not line or "Roll" in line:
            continue  # skip header / empty

        values = line.split(",")

        # we only need first 2 (roll, pitch)
        roll = float(values[0])
        pitch = float(values[1])

        action = "CENTER"

        # 👉 LEFT / RIGHT
        if roll > TILT_THRESHOLD:
            action = "RIGHT"
        elif roll < -TILT_THRESHOLD:
            action = "LEFT"

        # 👉 UP / DOWN
        elif pitch > TILT_THRESHOLD:
            action = "DOWN"
        elif pitch < -TILT_THRESHOLD:
            action = "UP"

        # 👉 CENTER (dead zone)
        if abs(roll) < CENTER_ZONE and abs(pitch) < CENTER_ZONE:
            action = "CENTER"

        # 🖨 print only if changed (avoid spam)
        if action != last_action:
            print(action)
            last_action = action

    except Exception as e:
        # silently ignore bad lines
        pass