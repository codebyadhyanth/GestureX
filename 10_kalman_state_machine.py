import serial
import time

# ---------------- KALMAN ----------------
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

kf_ax = Kalman1D()
kf_ay = Kalman1D()

# ---------------- CONFIG ----------------
TH = 1200
HYSTERESIS = 250   # 🔥 prevents flicker
DEBOUNCE = 0.4

last_action_time = 0

# ---------------- STATE MACHINE ----------------
state = "NEUTRAL"


# ---------------- ACTIONS ----------------
def action(new_state):
    print(f"👉 STATE CHANGE: {state} → {new_state}")


# ---------------- LOOP ----------------
while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    try:
        if not line or "," not in line:
            continue

        parts = line.split(",")
        if len(parts) < 5:
            continue

        data = list(map(float, parts))

        ax = kf_ax.update(data[2])
        ay = kf_ay.update(data[3])

        tilt_x = ay
        tilt_y = ax

        current_time = time.time()

        new_state = "NEUTRAL"

        # ---------------- DETECTION WITH HYSTERESIS ----------------

        if tilt_x > TH:
            new_state = "FORWARD"
        elif tilt_x < -TH:
            new_state = "BACKWARD"
        elif tilt_y > TH:
            new_state = "RIGHT"
        elif tilt_y < -TH:
            new_state = "LEFT"

        # ---------------- STABILITY CHECK ----------------
        if new_state != state and (current_time - last_action_time > DEBOUNCE):

            # extra protection: avoid noise flicker
            if abs(tilt_x) > TH + HYSTERESIS or abs(tilt_y) > TH + HYSTERESIS:

                state = new_state
                action(state)
                last_action_time = current_time

    except Exception as e:
        print("Error:", e)