import serial
import time

# ---------------- KALMAN FILTER ----------------
class Kalman1D:
    def __init__(self, q=0.01, r=1.0):
        self.q = q
        self.r = r
        self.x = 0.0
        self.p = 1.0
        self.k = 0.0

    def update(self, z):
        self.p += self.q
        self.k = self.p / (self.p + self.r)
        self.x += self.k * (z - self.x)
        self.p *= (1 - self.k)
        return self.x


# ---------------- SERIAL ----------------
ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)
ser.reset_input_buffer()

# ---------------- FILTERS ----------------
kf_ax = Kalman1D()
kf_ay = Kalman1D()

# ---------------- CONFIG ----------------
TILT_THRESHOLD = 1200
DEBOUNCE_TIME = 0.5

# separate timers (IMPORTANT FIX)
last_forward = 0
last_backward = 0
last_left = 0
last_right = 0


# ---------------- ACTIONS ----------------
def forward():
    print("👉 FORWARD: Next / Scroll Down / Move Right")

def backward():
    print("👈 BACKWARD: Previous / Scroll Up / Move Left")

def left():
    print("👈 LEFT: Move Left / Previous UI")

def right():
    print("👉 RIGHT: Move Right / Next UI")


# ---------------- MAIN LOOP ----------------
while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    try:
        if not line or "," not in line:
            continue

        parts = line.split(",")
        if len(parts) < 5:
            continue

        data = list(map(float, parts))

        ax_raw = data[2]
        ay_raw = data[3]

        # ---------------- KALMAN FILTER ----------------
        ax = kf_ax.update(ax_raw)
        ay = kf_ay.update(ay_raw)

        current_time = time.time()

        # =====================================================
        # 🔥 IMPORTANT: FIXED AXIS MAPPING (THIS WAS THE BUG)
        # =====================================================

        tilt_x = ay   # Forward / Backward
        tilt_y = ax   # Left / Right

        # ---------------- FORWARD ----------------
        if tilt_x > TILT_THRESHOLD:
            if current_time - last_forward > DEBOUNCE_TIME:
                forward()
                last_forward = current_time

        # ---------------- BACKWARD ----------------
        elif tilt_x < -TILT_THRESHOLD:
            if current_time - last_backward > DEBOUNCE_TIME:
                backward()
                last_backward = current_time

        # ---------------- RIGHT ----------------
        if tilt_y > TILT_THRESHOLD:
            if current_time - last_right > DEBOUNCE_TIME:
                right()
                last_right = current_time

        # ---------------- LEFT ----------------
        elif tilt_y < -TILT_THRESHOLD:
            if current_time - last_left > DEBOUNCE_TIME:
                left()
                last_left = current_time

    except Exception as e:
        print("Error:", e)