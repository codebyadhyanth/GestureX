import serial
import time
import keyboard

# ---------------- MEDIA CONTROL ----------------
def volume_up():
    keyboard.send("volume up")
    print("🔊 Volume UP")

def volume_down():
    keyboard.send("volume down")
    print("🔉 Volume DOWN")

def next_song():
    keyboard.send("next track")
    print("⏭ Next Song")

def prev_song():
    keyboard.send("previous track")
    print("⏮ Previous Song")

def scroll_up():
    keyboard.send("page up")
    print("⬆ Scroll Up")

def scroll_down():
    keyboard.send("page down")
    print("⬇ Scroll Down")

def next_page():
    keyboard.send("right")
    print("➡ Next Page")

def prev_page():
    keyboard.send("left")
    print("⬅ Previous Page")


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

    def update(self, z):
        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x += k * (z - self.x)
        self.p *= (1 - k)
        return self.x


kf_ax = Kalman1D()
kf_ay = Kalman1D()


# ---------------- CONFIG ----------------
TH = 1200
DEAD_ZONE = 200
STABLE_TIME = 0.12
DEBOUNCE = 0.3

# 🔥 SWIPE (SIMPLIFIED & WORKING)
SWIPE_DELTA = 6000
SWIPE_COOLDOWN = 0.8

# ---------------- STATE ----------------
modes = ["MUSIC", "NORMAL", "PRESENTATION"]
mode_index = 0

current_state = "NEUTRAL"

last_trigger = 0
state_start = 0
last_swipe = 0

prev_ax = 0
prev_ay = 0


# ---------------- MODE SWITCH ----------------
def switch_mode(direction):
    global mode_index

    if direction == "RIGHT":
        mode_index = (mode_index + 1) % len(modes)
    elif direction == "LEFT":
        mode_index = (mode_index - 1) % len(modes)

    print(f"\n🔁 MODE → {modes[mode_index]}\n")


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

        # RAW (for swipe)
        ax_raw = data[2]
        ay_raw = data[3]

        # FILTERED (for tilt)
        ax = kf_ax.update(ax_raw)
        ay = kf_ay.update(ay_raw)

        current_time = time.time()

        # =====================================================
        # ⚡ SWIPE DETECTION (SIMPLIFIED & RELIABLE)
        # =====================================================
        dx = ax_raw - prev_ax
        dy = ay_raw - prev_ay

        prev_ax = ax_raw
        prev_ay = ay_raw

        if abs(dx) > SWIPE_DELTA and abs(dx) > abs(dy):
            if current_time - last_swipe > SWIPE_COOLDOWN:

                if dx > 0:
                    print("👉 RIGHT SWIPE")
                    switch_mode("RIGHT")
                else:
                    print("👈 LEFT SWIPE")
                    switch_mode("LEFT")

                last_swipe = current_time
                continue


        # =====================================================
        # 🎯 TILT DETECTION
        # =====================================================
        if abs(ax) < DEAD_ZONE:
            ax = 0
        if abs(ay) < DEAD_ZONE:
            ay = 0

        abs_x = abs(ay)
        abs_y = abs(ax)

        new_state = "NEUTRAL"

        if abs_x > abs_y:
            if ay > TH:
                new_state = "FORWARD"
            elif ay < -TH:
                new_state = "BACKWARD"
        else:
            if ax > TH:
                new_state = "RIGHT"
            elif ax < -TH:
                new_state = "LEFT"

        # stability
        if new_state != current_state:
            current_state = new_state
            state_start = current_time

        if current_state != "NEUTRAL":
            if current_time - state_start > STABLE_TIME:
                if current_time - last_trigger > DEBOUNCE:

                    mode = modes[mode_index]

                    # ---------------- MODE ACTIONS ----------------
                    if mode == "MUSIC":
                        if current_state == "FORWARD":
                            volume_up()
                        elif current_state == "BACKWARD":
                            volume_down()
                        elif current_state == "RIGHT":
                            next_song()
                        elif current_state == "LEFT":
                            prev_song()

                    elif mode == "NORMAL":
                        if current_state == "FORWARD":
                            scroll_up()
                        elif current_state == "BACKWARD":
                            scroll_down()
                        elif current_state == "RIGHT":
                            next_page()
                        elif current_state == "LEFT":
                            prev_page()

                    elif mode == "PRESENTATION":
                        if current_state in ["FORWARD", "RIGHT"]:
                            next_page()
                        elif current_state in ["BACKWARD", "LEFT"]:
                            prev_page()

                    last_trigger = current_time
                    current_state = "NEUTRAL"

    except Exception as e:
        print("Error:", e)