import serial
import time
from collections import deque
import keyboard

# 🔌 Serial setup
ser = serial.Serial('COM3', 115200, timeout=1)  # change COM port
time.sleep(2)

# 📊 Flex tracking
flex_min = 4095
flex_max = 0

# smoothing buffer
flex_buffer = deque(maxlen=10)

# gesture states
last_click_time = 0
is_holding = False

CLICK_THRESHOLD = 70
HOLD_THRESHOLD = 85
RELEASE_THRESHOLD = 60

CLICK_COOLDOWN = 0.5  # seconds
HOLD_TIME = 1.0       # seconds

hold_start_time = None


def normalize(val, min_val, max_val):
    if max_val - min_val == 0:
        return 0
    return int((val - min_val) * 100 / (max_val - min_val))


def smooth(val):
    flex_buffer.append(val)
    return sum(flex_buffer) / len(flex_buffer)


print("🚀 Started...")

while True:
    try:
        line = ser.readline().decode().strip()
        if not line:
            continue

        data = line.split(",")

        if len(data) != 6:
            continue

        gx, gy, ax, ay, az, flex_raw = map(int, data)

        # ---------------- FLEX PROCESSING ----------------

        flex_smooth = smooth(flex_raw)

        # dynamic calibration
        flex_min = min(flex_min, flex_smooth)
        flex_max = max(flex_max, flex_smooth)

        flex_percent = normalize(flex_smooth, flex_min, flex_max)

        # ---------------- GESTURES ----------------

        current_time = time.time()

        # CLICK
        if flex_percent > CLICK_THRESHOLD:
            if current_time - last_click_time > CLICK_COOLDOWN:
                keyboard.click()   # mouse click
                print("🖱 CLICK")
                last_click_time = current_time

        # HOLD
        if flex_percent > HOLD_THRESHOLD:
            if hold_start_time is None:
                hold_start_time = current_time

            elif current_time - hold_start_time > HOLD_TIME and not is_holding:
                print("✊ HOLD")
                keyboard.press("left mouse button")
                is_holding = True

        else:
            hold_start_time = None

        # RELEASE HOLD
        if is_holding and flex_percent < RELEASE_THRESHOLD:
            keyboard.release("left mouse button")
            print("✋ RELEASE")
            is_holding = False

        # ---------------- SMOOTH SCROLL ----------------

        # stronger bend = faster scroll
        if flex_percent > 60:
            scroll_speed = int((flex_percent - 60) / 5)

            for _ in range(scroll_speed):
                keyboard.send("down")
                time.sleep(0.01)

        elif flex_percent < 40:
            scroll_speed = int((40 - flex_percent) / 5)

            for _ in range(scroll_speed):
                keyboard.send("up")
                time.sleep(0.01)

        # ---------------- DEBUG ----------------

        print(f"Flex Raw: {flex_raw} | %: {flex_percent}")

    except Exception as e:
        print("Error:", e)