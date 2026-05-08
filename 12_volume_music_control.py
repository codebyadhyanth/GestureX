import serial
import time
import os

# ---------------- MEDIA CONTROL ----------------
def volume_up():
    os.system('powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]175)')
    print("🔊 Volume UP")

def volume_down():
    os.system('powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]174)')
    print("🔉 Volume DOWN")

def next_song():
    os.system('powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]176)')
    print("⏭ Next Song")

def prev_song():
    os.system('powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]177)')
    print("⏮ Previous Song")


# ---------------- SERIAL ----------------
ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)
ser.reset_input_buffer()


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


kf_ax = Kalman1D()
kf_ay = Kalman1D()

# ---------------- CONFIG ----------------
TH = 1200
DEAD_ZONE = 200
STABLE_TIME = 0.15  # must persist 150ms

last_trigger_time = 0
current_state = "NEUTRAL"
state_start_time = 0


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

        # ---------------- DEAD ZONE ----------------
        if abs(ax) < DEAD_ZONE:
            ax = 0
        if abs(ay) < DEAD_ZONE:
            ay = 0

        # ---------------- DOMINANT AXIS SELECTION ----------------
        abs_x = abs(ay)
        abs_y = abs(ax)

        dominant_state = "NEUTRAL"

        # Only ONE axis allowed to control at a time
        if abs_x > abs_y:
            if ay > TH:
                dominant_state = "FORWARD"
            elif ay < -TH:
                dominant_state = "BACKWARD"

        else:
            if ax > TH:
                dominant_state = "RIGHT"
            elif ax < -TH:
                dominant_state = "LEFT"

        current_time = time.time()

        # ---------------- STABILITY FILTER ----------------
        if dominant_state != current_state:
            current_state = dominant_state
            state_start_time = current_time

        # Only trigger if stable for some time
        if current_state != "NEUTRAL":
            if current_time - state_start_time > STABLE_TIME:
                if current_time - last_trigger_time > 0.4:

                    if current_state == "FORWARD":
                        volume_up()

                    elif current_state == "BACKWARD":
                        volume_down()

                    elif current_state == "RIGHT":
                        next_song()

                    elif current_state == "LEFT":
                        prev_song()

                    last_trigger_time = current_time
                    current_state = "NEUTRAL"

    except Exception as e:
        print("Error:", e)