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
TILT_THRESHOLD = 1200   # adjust based on your sensor
DEBOUNCE_TIME = 0.4     # prevents spam triggers

last_action_time = 0


# ---------------- ACTION FUNCTIONS ----------------
def forward_action():
    print("👉 FORWARD: Next / Scroll Down / Move Right")

def backward_action():
    print("👈 BACKWARD: Previous / Scroll Up / Move Left")


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

        # ---------------- RIGHT TILT ----------------
        if ax > TILT_THRESHOLD:
            if current_time - last_action_time > DEBOUNCE_TIME:
                forward_action()
                last_action_time = current_time

        # ---------------- LEFT TILT ----------------
        elif ax < -TILT_THRESHOLD:
            if current_time - last_action_time > DEBOUNCE_TIME:
                backward_action()
                last_action_time = current_time

    except Exception as e:
        print("Error:", e)