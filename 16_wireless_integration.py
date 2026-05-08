import socket
import time
import keyboard

# =========================================================
# 🌐 WIFI CONNECTION
# =========================================================

HOST = '192.168.4.1'
PORT = 1234

print("🔌 Connecting to ESP32...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

sock.connect((HOST, PORT))

print("✅ Connected to ESP32")


# =========================================================
# 🎵 MEDIA CONTROL
# =========================================================

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


# =========================================================
# 🎯 KALMAN FILTER
# =========================================================

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


# =========================================================
# ⚙ CONFIG
# =========================================================

# Main gesture threshold
TH = 1200

# Large center dead zone
DEAD_ZONE = 300

# Must return close to center
RETURN_ZONE = 150

# Hold gesture slightly
STABLE_TIME = 0.20

# Delay between actions
DEBOUNCE = 0.8


# =========================================================
# ⚡ SWIPE CONFIG
# =========================================================

# MUCH harder swipe
SWIPE_DELTA = 3500

# Delay between swipes
SWIPE_COOLDOWN = 1.5


# =========================================================
# 📌 STATES
# =========================================================

modes = ["MUSIC", "NORMAL", "PRESENTATION"]

mode_index = 0

current_state = "NEUTRAL"

gesture_locked = False

last_trigger = 0

state_start = 0

last_swipe = 0

prev_ax = 0
prev_ay = 0


# =========================================================
# 🔁 MODE SWITCH
# =========================================================

def switch_mode(direction):

    global mode_index

    if direction == "RIGHT":

        mode_index = (mode_index + 1) % len(modes)

    elif direction == "LEFT":

        mode_index = (mode_index - 1) % len(modes)

    print(f"\n🔁 MODE → {modes[mode_index]}\n")


# =========================================================
# 🚀 MAIN LOOP
# =========================================================

buffer = ""

while True:

    try:

        # =====================================================
        # RECEIVE WIFI DATA
        # =====================================================

        data = sock.recv(1024).decode()

        if not data:
            continue

        buffer += data

        lines = buffer.split("\n")

        buffer = lines[-1]

        for line in lines[:-1]:

            line = line.strip()

            if "," not in line:
                continue

            try:

                ax_raw, ay_raw = map(float, line.split(","))

            except:
                continue


            # =================================================
            # 🎯 FILTERED VALUES
            # =================================================

            ax = kf_ax.update(ax_raw)

            ay = kf_ay.update(ay_raw)

            current_time = time.time()


            # =================================================
            # ⚡ IMPROVED SWIPE DETECTION
            # =================================================

            dx = ax_raw - prev_ax
            dy = ay_raw - prev_ay

            prev_ax = ax_raw
            prev_ay = ay_raw

            # Only detect swipe near center
            near_center = abs(ax) < 500 and abs(ay) < 500

            if near_center:

                # Strong horizontal movement only
                if abs(dx) > SWIPE_DELTA and abs(dx) > abs(dy) * 2:

                    if current_time - last_swipe > SWIPE_COOLDOWN:

                        # Extra fast movement check
                        if abs(dx) > 3500:

                            if dx > 0:

                                print("👉 RIGHT SWIPE")

                                switch_mode("RIGHT")

                            else:

                                print("👈 LEFT SWIPE")

                                switch_mode("LEFT")

                            last_swipe = current_time

                            gesture_locked = True

                            continue


            # =================================================
            # 🎯 DEAD ZONE
            # =================================================

            if abs(ax) < DEAD_ZONE:
                ax = 0

            if abs(ay) < DEAD_ZONE:
                ay = 0


            # =================================================
            # 🔒 WAIT UNTIL RETURN TO CENTER
            # =================================================

            if gesture_locked:

                if abs(ax) < RETURN_ZONE and abs(ay) < RETURN_ZONE:

                    gesture_locked = False

                else:
                    continue


            # =================================================
            # 🎯 DETECT DOMINANT DIRECTION
            # =================================================

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


            # =================================================
            # ⏳ STABILITY CHECK
            # =================================================

            if new_state != current_state:

                current_state = new_state

                state_start = current_time


            # =================================================
            # 🚀 TRIGGER ACTION
            # =================================================

            if current_state != "NEUTRAL":

                if current_time - state_start > STABLE_TIME:

                    if current_time - last_trigger > DEBOUNCE:

                        mode = modes[mode_index]

                        print(f"\n🎯 Gesture: {current_state}")

                        print(f"📌 Mode: {mode}")


                        # =========================================
                        # 🎵 MUSIC MODE
                        # =========================================

                        if mode == "MUSIC":

                            if current_state == "FORWARD":
                                volume_up()

                            elif current_state == "BACKWARD":
                                volume_down()

                            elif current_state == "RIGHT":
                                next_song()

                            elif current_state == "LEFT":
                                prev_song()


                        # =========================================
                        # 💻 NORMAL MODE
                        # =========================================

                        elif mode == "NORMAL":

                            if current_state == "FORWARD":
                                scroll_up()

                            elif current_state == "BACKWARD":
                                scroll_down()

                            elif current_state == "RIGHT":
                                next_page()

                            elif current_state == "LEFT":
                                prev_page()


                        # =========================================
                        # 📽 PRESENTATION MODE
                        # =========================================

                        elif mode == "PRESENTATION":

                            if current_state in ["FORWARD", "RIGHT"]:

                                next_page()

                            else:

                                prev_page()


                        # =========================================
                        # 🔒 LOCK UNTIL CENTERED
                        # =========================================

                        gesture_locked = True

                        last_trigger = current_time

                        current_state = "NEUTRAL"


    except Exception as e:

        print("❌ Error:", e)

        time.sleep(1)