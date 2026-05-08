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

# ---------------- STATE MACHINE ----------------
state = "NEUTRAL"


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

        # ---------------- DETECT STATE ----------------
        new_state = "NEUTRAL"

        if tilt_x > TH:
            new_state = "FORWARD"

        elif tilt_x < -TH:
            new_state = "BACKWARD"

        elif tilt_y > TH:
            new_state = "RIGHT"

        elif tilt_y < -TH:
            new_state = "LEFT"


        # ---------------- EDGE TRIGGER (MAIN FIX) ----------------
        if new_state != state:
            state = new_state

            if state == "FORWARD":
                volume_up()

            elif state == "BACKWARD":
                volume_down()

            elif state == "RIGHT":
                next_song()

            elif state == "LEFT":
                prev_song()

    except Exception as e:
        print("Error:", e)