import socket
import time
import keyboard
import pygame
import math
from collections import deque
import winsound

# =========================================================
# 🌐 WIFI CONNECTION
# =========================================================

HOST = '192.168.4.1'
PORT = 1234

print("🔌 Connecting to ESP32...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 🚀 LOW LATENCY
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.settimeout(0.5)

sock.connect((HOST, PORT))

print("✅ Connected to ESP32")


# =========================================================
# 🎮 PYGAME INIT
# =========================================================

pygame.init()

WIDTH = 1200
HEIGHT = 760

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GestureX Ultimate Dashboard")

clock = pygame.time.Clock()

font = pygame.font.SysFont("consolas", 18)
small_font = pygame.font.SysFont("consolas", 15)
big_font = pygame.font.SysFont("consolas", 30)


# =========================================================
# 🎨 COLORS
# =========================================================

BG = (12, 14, 22)
PANEL = (20, 22, 32)
CARD = (28, 32, 46)

WHITE = (240, 240, 240)
GRAY = (170, 170, 170)

CYAN = (0, 200, 255)
GREEN = (0, 255, 120)
ORANGE = (255, 150, 0)
RED = (255, 80, 80)

GRID = (60, 60, 80)


# =========================================================
# 🪵 LOG SYSTEM
# =========================================================

logs = deque(maxlen=14)

def add_log(msg):

    timestamp = time.strftime("%H:%M:%S")

    full = f"[{timestamp}] {msg}"

    print(full)

    logs.appendleft(full)


# =========================================================
# 🔊 ALERT SYSTEM
# =========================================================

last_alert = 0
CALIBRATION_ALERT_COOLDOWN = 5

def calibration_alert():

    global last_alert

    now = time.time()

    if now - last_alert > CALIBRATION_ALERT_COOLDOWN:

        winsound.Beep(1200, 300)

        add_log("⚠ CALIBRATION REQUIRED")

        last_alert = now


# =========================================================
# 🚀 ADAPTIVE VOLUME SYSTEM
# =========================================================

volume_boost = 2
last_volume_time = 0

BOOST_RESET_TIME = 2.0
MAX_VOLUME_BOOST = 12

def adaptive_volume():

    global volume_boost
    global last_volume_time

    now = time.time()

    # reset boost after pause
    if now - last_volume_time > BOOST_RESET_TIME:

        volume_boost = 2

    else:

        if volume_boost < 4:
            volume_boost = 4

        elif volume_boost < 8:
            volume_boost = 8

        else:
            volume_boost = min(volume_boost + 4, MAX_VOLUME_BOOST)

    last_volume_time = now

    return volume_boost


# =========================================================
# 🎵 ACTIONS
# =========================================================

def volume_up():

    step = adaptive_volume()

    for _ in range(step):
        keyboard.send("volume up")

    add_log(f"🔊 Volume UP x{step}")


def volume_down():

    step = adaptive_volume()

    for _ in range(step):
        keyboard.send("volume down")

    add_log(f"🔉 Volume DOWN x{step}")


def next_song():

    keyboard.send("next track")

    add_log("⏭ Next Song")


def prev_song():

    keyboard.send("previous track")

    add_log("⏮ Previous Song")


def scroll_up():

    keyboard.send("page up")

    add_log("⬆ Scroll Up")


def scroll_down():

    keyboard.send("page down")

    add_log("⬇ Scroll Down")


def next_page():

    keyboard.send("right")

    add_log("➡ Next Page")


def prev_page():

    keyboard.send("left")

    add_log("⬅ Previous Page")


# =========================================================
# 🧠 KALMAN FILTER
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


kf_pitch = Kalman1D()
kf_roll = Kalman1D()


# =========================================================
# ⚙ CONFIG
# =========================================================

THRESHOLD = 15
WARNING_ZONE = 11

BASE_RESET_ZONE = 6

SWIPE_COOLDOWN = 1.5

DEBOUNCE = 0.8

CENTER_SNAP = 0.06

CALIBRATION_THRESHOLD = 18

OUTER_TRIGGER = 48


# =========================================================
# 📌 STATES
# =========================================================

modes = ["MUSIC", "NORMAL", "PRESENTATION"]

mode_index = 0

ARMED = True
CONNECTED = True

current_state = "NEUTRAL"

last_trigger = 0
last_swipe = 0

buffer = ""

pitch = 0
roll = 0

trail = deque(maxlen=30)

noise_history = deque(maxlen=60)


# =========================================================
# 🔁 MODE SWITCH
# =========================================================

def switch_mode(direction):

    global mode_index

    if direction == "RIGHT":
        mode_index = (mode_index + 1) % len(modes)

    else:
        mode_index = (mode_index - 1) % len(modes)

    add_log(f"🔁 MODE → {modes[mode_index]}")


# =========================================================
# 🧲 CENTER SNAP
# =========================================================

def magnetic_snap(value):

    return value * (1 - CENTER_SNAP)


# =========================================================
# 🚀 MAIN LOOP
# =========================================================

while True:

    try:

        # =====================================================
        # WINDOW EVENTS
        # =====================================================

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                pygame.quit()
                exit()


        # =====================================================
        # RECEIVE DATA
        # =====================================================

        try:

            data = sock.recv(1024).decode(errors='ignore')

        except socket.timeout:

            continue

        except Exception:

            CONNECTED = False
            continue

        if not data:
            continue

        CONNECTED = True

        buffer += data

        lines = buffer.split("\n")

        buffer = lines[-1]


        for line in lines[:-1]:

            parts = line.strip().replace("\r", "").split(",")

            if len(parts) < 6:
                continue

            try:

                ax = float(parts[0])
                ay = float(parts[1])
                az = float(parts[2])

            except:
                continue


            # =================================================
            # 📐 PITCH + ROLL
            # =================================================

            pitch_raw = math.degrees(
                math.atan2(ax, math.sqrt(ay * ay + az * az))
            )

            roll_raw = math.degrees(
                math.atan2(ay, math.sqrt(ax * ax + az * az))
            )

            pitch = kf_pitch.update(pitch_raw)
            roll = kf_roll.update(roll_raw)


            # =================================================
            # 🧲 MAGNETIC SNAP
            # =================================================

            pitch = magnetic_snap(pitch)
            roll = magnetic_snap(roll)


            # =================================================
            # 🧠 ADAPTIVE DEADZONE
            # =================================================

            noise_history.append(abs(pitch) + abs(roll))

            avg_noise = sum(noise_history) / len(noise_history)

            RESET_ZONE = max(BASE_RESET_ZONE, avg_noise * 0.45)


            # =================================================
            # 📉 TRAIL
            # =================================================

            trail.append((roll, pitch))


            # =================================================
            # ⚠ CALIBRATION ALERT
            # =================================================

            idle_state = abs(pitch) < 3 and abs(roll) < 3

            pointer_drift = math.sqrt(
                (roll * roll) + (pitch * pitch)
            )

            if idle_state and pointer_drift > CALIBRATION_THRESHOLD:

                calibration_alert()


            current_time = time.time()


            # =================================================
            # 🔓 RESET SYSTEM
            # =================================================

            if not ARMED:

                if abs(pitch) < RESET_ZONE and abs(roll) < RESET_ZONE:

                    ARMED = True

                    add_log("🟢 System Re-Armed")


            # =================================================
            # 🔁 OUTER RING MODE SWITCH
            # =================================================

            distance = math.sqrt(
                (roll * roll) + (pitch * pitch)
            )

            if current_time - last_swipe > SWIPE_COOLDOWN:

                if distance > OUTER_TRIGGER:

                    if abs(roll) > abs(pitch):

                        if roll > 0:

                            switch_mode("RIGHT")

                            add_log("👉 OUTER RING EXIT → MODE RIGHT")

                        else:

                            switch_mode("LEFT")

                            add_log("👈 OUTER RING EXIT → MODE LEFT")

                        ARMED = False

                        last_swipe = current_time


            # =================================================
            # 🎯 GESTURE DETECTION
            # =================================================

            if ARMED:

                gesture = "NEUTRAL"

                # SAME TILT LOGIC
                # FORWARD  -> VOL UP
                # BACKWARD -> VOL DOWN
                # LEFT     -> PREV SONG
                # RIGHT    -> NEXT SONG

                if abs(pitch) > abs(roll):

                    if pitch > THRESHOLD:
                        gesture = "FORWARD"

                    elif pitch < -THRESHOLD:
                        gesture = "BACKWARD"

                else:

                    if roll > THRESHOLD:
                        gesture = "RIGHT"

                    elif roll < -THRESHOLD:
                        gesture = "LEFT"


                # =================================================
                # ACTION TRIGGER
                # =================================================

                if gesture != "NEUTRAL":

                    if current_time - last_trigger > DEBOUNCE:

                        mode = modes[mode_index]

                        current_state = gesture

                        add_log(f"🎯 Gesture: {gesture}")
                        add_log(f"📌 Mode: {mode}")


                        # =========================================
                        # 🎵 MUSIC MODE
                        # =========================================

                        if mode == "MUSIC":

                            if gesture == "FORWARD":
                                volume_up()

                            elif gesture == "BACKWARD":
                                volume_down()

                            elif gesture == "LEFT":
                                prev_song()

                            elif gesture == "RIGHT":
                                next_song()


                        # =========================================
                        # 💻 NORMAL MODE
                        # =========================================

                        elif mode == "NORMAL":

                            if gesture == "FORWARD":
                                scroll_up()

                            elif gesture == "BACKWARD":
                                scroll_down()

                            elif gesture == "LEFT":
                                prev_page()

                            elif gesture == "RIGHT":
                                next_page()


                        # =========================================
                        # 📽 PRESENTATION MODE
                        # =========================================

                        elif mode == "PRESENTATION":

                            if gesture in ["FORWARD", "RIGHT"]:
                                next_page()

                            else:
                                prev_page()


                        ARMED = False

                        last_trigger = current_time


        # =====================================================
        # 🎨 UI
        # =====================================================

        screen.fill(BG)

        LEFT_W = 820

        pygame.draw.rect(
            screen,
            PANEL,
            (0, 0, LEFT_W, HEIGHT)
        )

        pygame.draw.rect(
            screen,
            (18, 20, 28),
            (LEFT_W, 0, WIDTH - LEFT_W, HEIGHT)
        )


        # =====================================================
        # 🎯 VISUALIZER
        # =====================================================

        CX = 400
        CY = 320

        OUTER_RADIUS = int(OUTER_TRIGGER * 5)

        # AXIS
        pygame.draw.line(
            screen,
            GRID,
            (0, CY),
            (LEFT_W, CY),
            1
        )

        pygame.draw.line(
            screen,
            GRID,
            (CX, 0),
            (CX, HEIGHT),
            1
        )

        # OUTER RING
        pygame.draw.circle(
            screen,
            GRID,
            (CX, CY),
            OUTER_RADIUS,
            2
        )

        # WARNING ZONE
        pygame.draw.circle(
            screen,
            ORANGE,
            (CX, CY),
            int(WARNING_ZONE * 5),
            2
        )

        # INNER SAFE ZONE
        pygame.draw.circle(
            screen,
            GREEN,
            (CX, CY),
            int(RESET_ZONE * 5),
            2
        )


        # =====================================================
        # 📉 MOTION TRAIL
        # =====================================================

        for i, (rx, ry) in enumerate(trail):

            tx = int(CX + rx * 5)
            ty = int(CY - ry * 5)

            pygame.draw.circle(
                screen,
                (0, 180, 255),
                (tx, ty),
                3
            )


        # =====================================================
        # 🧲 POINTER
        # =====================================================

        px = int(CX + roll * 5)
        py = int(CY - pitch * 5)

        pygame.draw.circle(
            screen,
            CYAN,
            (px, py),
            18
        )


        # =====================================================
        # 📦 STATUS CARD
        # =====================================================

        pygame.draw.rect(
            screen,
            CARD,
            (30, 560, 740, 170),
            border_radius=18
        )

        screen.blit(
            big_font.render("SYSTEM STATUS", True, WHITE),
            (50, 580)
        )

        status_color = GREEN if CONNECTED else RED

        screen.blit(
            font.render(
                f"Device: {'CONNECTED' if CONNECTED else 'DISCONNECTED'}",
                True,
                status_color
            ),
            (50, 625)
        )

        screen.blit(
            font.render(
                f"Mode: {modes[mode_index]}",
                True,
                CYAN
            ),
            (50, 650)
        )

        screen.blit(
            font.render(
                f"Gesture State: {current_state}",
                True,
                WHITE
            ),
            (320, 650)
        )

        screen.blit(
            font.render(
                f"ARMED: {ARMED}",
                True,
                GREEN
            ),
            (550, 650)
        )

        screen.blit(
            font.render(
                f"Pitch: {pitch:.2f}",
                True,
                GRAY
            ),
            (50, 685)
        )

        screen.blit(
            font.render(
                f"Roll: {roll:.2f}",
                True,
                GRAY
            ),
            (250, 685)
        )

        screen.blit(
            font.render(
                f"Adaptive DeadZone: {RESET_ZONE:.2f}",
                True,
                GRAY
            ),
            (450, 685)
        )


        # =====================================================
        # 🪵 LOG PANEL
        # =====================================================

        screen.blit(
            big_font.render("LIVE LOGS", True, WHITE),
            (860, 25)
        )

        log_y = 80

        for lg in logs:

            txt = small_font.render(
                lg,
                True,
                (210, 210, 210)
            )

            screen.blit(txt, (845, log_y))

            log_y += 32


        pygame.display.flip()

        clock.tick(60)


    except Exception as e:

        add_log(f"❌ Error: {e}")

        time.sleep(1)