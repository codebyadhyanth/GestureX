# =========================================================
# 🚀 GestureX Ultimate AI Dashboard
# 🔥 REAL-TIME LETTER DETECTION + STEP VOLUME SYSTEM
# =========================================================

import socket
import time
import keyboard
import pygame
import math
import subprocess
import webbrowser
import ctypes
import winsound

from collections import deque

# =========================================================
# 🖱 WINDOWS MOUSE API
# =========================================================

user32 = ctypes.windll.user32

SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)

mouse_x = SCREEN_W // 2
mouse_y = SCREEN_H // 2

# =========================================================
# 🌐 WIFI CONNECTION
# =========================================================

HOST = '192.168.4.1'
PORT = 1234

print("🔌 Connecting to ESP32...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.settimeout(0.5)

sock.connect((HOST, PORT))

print("✅ Connected to ESP32")

# =========================================================
# 🎮 PYGAME INIT
# =========================================================

pygame.init()

WIDTH = 1280
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
YELLOW = (255, 255, 0)

GRID = (60, 60, 80)

# =========================================================
# 🪵 LOGS
# =========================================================

logs = deque(maxlen=14)

def add_log(msg):

    timestamp = time.strftime("%H:%M:%S")

    full = f"[{timestamp}] {msg}"

    print(full)

    logs.appendleft(full)

# =========================================================
# 🔊 ALERT
# =========================================================

last_alert = 0

def calibration_alert():

    global last_alert

    now = time.time()

    if now - last_alert > 5:

        winsound.Beep(1200, 300)

        add_log("⚠ CALIBRATION REQUIRED")

        last_alert = now

# =========================================================
# 🔊 STEP-UP VOLUME SYSTEM
# =========================================================

volume_boost = 2
last_volume_time = 0

BOOST_RESET_TIME = 2.0
MAX_VOLUME_BOOST = 8

def adaptive_volume():

    global volume_boost
    global last_volume_time

    now = time.time()

    # RESET IF USER PAUSES
    if now - last_volume_time > BOOST_RESET_TIME:

        volume_boost = 2

    else:

        # STEP-UP LOGIC
        if volume_boost == 2:

            volume_boost = 4

        elif volume_boost == 4:

            volume_boost = 8

        else:

            volume_boost = MAX_VOLUME_BOOST

    last_volume_time = now

    return volume_boost

def volume_up():

    step = adaptive_volume()

    for _ in range(step):

        keyboard.send("volume up")

    add_log(f"🔊 Volume UP +{step}")

def volume_down():

    step = adaptive_volume()

    for _ in range(step):

        keyboard.send("volume down")

    add_log(f"🔉 Volume DOWN -{step}")

# =========================================================
# 🧠 KALMAN FILTER
# =========================================================

class Kalman1D:

    def __init__(self, q=0.003, r=4.5):

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

THRESHOLD = 26
WARNING_ZONE = 18
BASE_RESET_ZONE = 14

CENTER_SNAP = 0.22

OUTER_TRIGGER = 42

POINTER_SCALE = 3

LETTER_START_ZONE = 28

MOUSE_SENSITIVITY = 1.0
MOUSE_SMOOTHING = 0.20

SWIPE_COOLDOWN = 1.5
DEBOUNCE = 0.8

CALIBRATION_THRESHOLD = 18

PATH_TIMEOUT = 1.4
MIN_PATH_POINTS = 20

# =========================================================
# 📌 STATES
# =========================================================

modes = [
    "MUSIC",
    "NORMAL",
    "PRESENTATION",
    "MOUSE"
]

mode_index = 0

ARMED = True
CONNECTED = True

current_state = "NEUTRAL"

last_trigger = 0
last_swipe = 0

buffer = ""

pitch = 0
roll = 0

trail = deque(maxlen=40)
noise_history = deque(maxlen=60)

# =========================================================
# ✍ LETTER STATES
# =========================================================

path_points = []

recording_path = False

path_start_time = 0

LETTER_COOLDOWN = 3

last_letter_trigger = 0

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
# ✍ NORMALIZE PATH
# =========================================================

def normalize_path(points):

    if len(points) < 10:
        return []

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    min_x = min(xs)
    max_x = max(xs)

    min_y = min(ys)
    max_y = max(ys)

    width = max_x - min_x
    height = max_y - min_y

    if width == 0:
        width = 1

    if height == 0:
        height = 1

    normalized = []

    for x, y in points:

        nx = (x - min_x) / width
        ny = (y - min_y) / height

        normalized.append((nx, ny))

    return normalized

# =========================================================
# ✍ LETTER RECOGNITION
# =========================================================

def recognize_letter(points):

    if len(points) < 20:
        return None

    pts = normalize_path(points)

    if not pts:
        return None

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    start_x, start_y = pts[0]
    end_x, end_y = pts[-1]

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    direction_changes_x = 0
    direction_changes_y = 0

    last_dx = 0
    last_dy = 0

    upward_moves = 0
    downward_moves = 0

    for i in range(1, len(pts)):

        dx = pts[i][0] - pts[i - 1][0]
        dy = pts[i][1] - pts[i - 1][1]

        if dx * last_dx < 0:
            direction_changes_x += 1

        if dy * last_dy < 0:
            direction_changes_y += 1

        if dy < 0:
            upward_moves += 1
        else:
            downward_moves += 1

        last_dx = dx
        last_dy = dy

    # N
    if (
        width > 0.55 and
        height > 0.65 and
        direction_changes_x <= 2 and
        upward_moves > 5 and
        downward_moves > 5 and
        start_y > 0.75 and
        end_y > 0.75
    ):
        return "N"

    # M
    peaks = 0

    for i in range(1, len(ys)-1):

        if ys[i] < ys[i-1] and ys[i] < ys[i+1]:
            peaks += 1

    if (
        peaks >= 2 and
        width > 0.5 and
        height > 0.5
    ):
        return "M"

    # C
    if (
        start_x > 0.7 and
        end_x > 0.7 and
        width > 0.5 and
        height > 0.5 and
        direction_changes_x <= 1
    ):
        return "C"

    # Y
    if (
        start_y < 0.3 and
        end_y > 0.7 and
        width > 0.4 and
        direction_changes_y >= 1
    ):
        return "Y"

    # S
    if (
        direction_changes_x >= 2 and
        width > 0.45 and
        height > 0.45
    ):
        return "S"

    return None

# =========================================================
# 🚀 LETTER ACTIONS
# =========================================================

def launch_letter_action(letter):

    global last_letter_trigger

    now = time.time()

    if now - last_letter_trigger < LETTER_COOLDOWN:
        return

    last_letter_trigger = now

    if letter == "N":

        add_log("🚀 Opening Notepad")
        subprocess.Popen("notepad.exe")

    elif letter == "M":

        add_log("🔇 Muting System")
        keyboard.send("volume mute")

    elif letter == "C":

        add_log("🌐 Opening Chrome")
        subprocess.Popen("start chrome", shell=True)

    elif letter == "Y":

        add_log("▶ Opening YouTube")
        webbrowser.open("https://youtube.com")

    elif letter == "S":

        add_log("🎵 Opening Spotify")
        subprocess.Popen("start spotify", shell=True)

# =========================================================
# 🖱 MOUSE CONTROL
# =========================================================

smooth_dx = 0
smooth_dy = 0

def update_mouse(rx, py):

    global mouse_x
    global mouse_y

    global smooth_dx
    global smooth_dy

    if abs(rx) < 6:
        rx = 0

    if abs(py) < 6:
        py = 0

    dx = rx * MOUSE_SENSITIVITY
    dy = py * MOUSE_SENSITIVITY

    smooth_dx += (dx - smooth_dx) * MOUSE_SMOOTHING
    smooth_dy += (dy - smooth_dy) * MOUSE_SMOOTHING

    mouse_x += int(smooth_dx)
    mouse_y += int(smooth_dy)

    mouse_x = max(0, min(SCREEN_W, mouse_x))
    mouse_y = max(0, min(SCREEN_H, mouse_y))

    user32.SetCursorPos(mouse_x, mouse_y)

# =========================================================
# 🚀 MAIN LOOP
# =========================================================

while True:

    try:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                pygame.quit()
                exit()

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

            pitch = magnetic_snap(pitch)
            roll = magnetic_snap(roll)

            # =================================================
            # 🧠 DEADZONE
            # =================================================

            noise_history.append(abs(pitch) + abs(roll))

            avg_noise = sum(noise_history) / len(noise_history)

            RESET_ZONE = max(
                BASE_RESET_ZONE,
                avg_noise * 0.45
            )

            # =================================================
            # 📉 TRAIL
            # =================================================

            trail.append((roll, pitch))

            # =================================================
            # 🖱 MOUSE MODE
            # =================================================

            if modes[mode_index] == "MOUSE":

                update_mouse(
                    roll,
                    -pitch
                )

            # =================================================
            # ✍ REAL-TIME LETTER TRACKING
            # =================================================

            px2 = int(roll * POINTER_SCALE)
            py2 = int(pitch * POINTER_SCALE)

            movement_strength = math.sqrt(
                (roll * roll) + (pitch * pitch)
            )

            if movement_strength > LETTER_START_ZONE:

                if not recording_path:

                    recording_path = True

                    path_start_time = time.time()

                    path_points.clear()

                    add_log("✍ Letter Tracking Started")

                path_points.append((px2, py2))

            if recording_path:

                if len(path_points) > MIN_PATH_POINTS:

                    detected = recognize_letter(path_points)

                    if detected:

                        winsound.Beep(1800, 120)

                        add_log(f"🧠 LETTER → {detected}")

                        launch_letter_action(detected)

                        recording_path = False

                        path_points.clear()

            if recording_path:

                if time.time() - path_start_time > PATH_TIMEOUT:

                    recording_path = False

                    path_points.clear()

                    add_log("⌛ Letter Timeout")

            # =================================================
            # ⚠ CALIBRATION
            # =================================================

            idle_state = abs(pitch) < 3 and abs(roll) < 3

            pointer_drift = math.sqrt(
                (roll * roll) + (pitch * pitch)
            )

            if idle_state and pointer_drift > CALIBRATION_THRESHOLD:

                calibration_alert()

            current_time = time.time()

            # =================================================
            # 🔓 REARM
            # =================================================

            if not ARMED:

                if abs(pitch) < RESET_ZONE and abs(roll) < RESET_ZONE:

                    ARMED = True

                    add_log("🟢 System Re-Armed")

            # =================================================
            # 🔁 MODE SWITCH
            # =================================================

            distance = math.sqrt(
                (roll * roll) + (pitch * pitch)
            )

            if current_time - last_swipe > SWIPE_COOLDOWN:

                if distance > OUTER_TRIGGER:

                    if abs(roll) > abs(pitch):

                        if roll > 0:
                            switch_mode("RIGHT")
                        else:
                            switch_mode("LEFT")

                        ARMED = False
                        last_swipe = current_time

            # =================================================
            # 🎯 GESTURES
            # =================================================

            if ARMED:

                gesture = "NEUTRAL"

                if distance > THRESHOLD:

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

                if gesture != "NEUTRAL":

                    if current_time - last_trigger > DEBOUNCE:

                        mode = modes[mode_index]

                        current_state = gesture

                        add_log(f"🎯 {gesture}")
                        add_log(f"📌 {mode}")

                        # =================================================
                        # 🎵 MUSIC MODE
                        # =================================================

                        if mode == "MUSIC":

                            if gesture == "FORWARD":

                                volume_up()

                            elif gesture == "BACKWARD":

                                volume_down()

                            elif gesture == "LEFT":

                                keyboard.send("previous track")
                                add_log("⏮ Previous Track")

                            elif gesture == "RIGHT":

                                keyboard.send("next track")
                                add_log("⏭ Next Track")

                        # =================================================
                        # 📄 NORMAL MODE
                        # =================================================

                        elif mode == "NORMAL":

                            if gesture == "FORWARD":

                                keyboard.send("page up")

                            elif gesture == "BACKWARD":

                                keyboard.send("page down")

                            elif gesture == "LEFT":

                                keyboard.send("left")

                            elif gesture == "RIGHT":

                                keyboard.send("right")

                        # =================================================
                        # 📊 PRESENTATION MODE
                        # =================================================

                        elif mode == "PRESENTATION":

                            if gesture in ["FORWARD", "RIGHT"]:

                                keyboard.send("right")

                            else:

                                keyboard.send("left")

                        # =================================================
                        # 🖱 MOUSE MODE
                        # =================================================

                        elif mode == "MOUSE":

                            if gesture == "FORWARD":

                                user32.mouse_event(2, 0, 0, 0, 0)
                                user32.mouse_event(4, 0, 0, 0, 0)

                                add_log("🖱 LEFT CLICK")

                            elif gesture == "RIGHT":

                                user32.mouse_event(8, 0, 0, 0, 0)
                                user32.mouse_event(16, 0, 0, 0, 0)

                                add_log("🖱 RIGHT CLICK")

                        ARMED = False

                        last_trigger = current_time

        # =====================================================
        # 🎨 UI
        # =====================================================

        screen.fill(BG)

        LEFT_W = 860

        pygame.draw.rect(screen, PANEL, (0, 0, LEFT_W, HEIGHT))

        pygame.draw.rect(
            screen,
            (18, 20, 28),
            (LEFT_W, 0, WIDTH - LEFT_W, HEIGHT)
        )

        CX = 420
        CY = 320

        OUTER_RADIUS = int(OUTER_TRIGGER * 3)

        pygame.draw.line(screen, GRID, (0, CY), (LEFT_W, CY), 1)
        pygame.draw.line(screen, GRID, (CX, 0), (CX, HEIGHT), 1)

        pygame.draw.circle(screen, GRID, (CX, CY), OUTER_RADIUS, 2)

        pygame.draw.circle(
            screen,
            ORANGE,
            (CX, CY),
            int(WARNING_ZONE * 3),
            2
        )

        pygame.draw.circle(
            screen,
            GREEN,
            (CX, CY),
            int(RESET_ZONE * 3),
            2
        )

        for rx, ry in trail:

            tx = int(CX + rx * POINTER_SCALE)
            ty = int(CY - ry * POINTER_SCALE)

            pygame.draw.circle(
                screen,
                (0, 180, 255),
                (tx, ty),
                3
            )

        if len(path_points) > 1:

            for i in range(1, len(path_points)):

                x1 = CX + path_points[i-1][0]
                y1 = CY - path_points[i-1][1]

                x2 = CX + path_points[i][0]
                y2 = CY - path_points[i][1]

                pygame.draw.line(
                    screen,
                    YELLOW,
                    (x1, y1),
                    (x2, y2),
                    3
                )

        px = int(CX + roll * POINTER_SCALE)
        py = int(CY - pitch * POINTER_SCALE)

        pygame.draw.circle(screen, CYAN, (px, py), 18)

        pygame.draw.circle(
            screen,
            (0, 120, 180),
            (px, py),
            30,
            2
        )

        pygame.draw.circle(screen, WHITE, (CX, CY), 4)

        pygame.draw.rect(
            screen,
            CARD,
            (30, 560, 780, 170),
            border_radius=18
        )

        screen.blit(
            big_font.render("SYSTEM STATUS", True, WHITE),
            (50, 580)
        )

        screen.blit(
            font.render(
                f"Mode: {modes[mode_index]}",
                True,
                CYAN
            ),
            (50, 630)
        )

        screen.blit(
            font.render(
                f"Pitch: {pitch:.2f}",
                True,
                WHITE
            ),
            (50, 665)
        )

        screen.blit(
            font.render(
                f"Roll: {roll:.2f}",
                True,
                WHITE
            ),
            (250, 665)
        )

        screen.blit(
            big_font.render("LIVE LOGS", True, WHITE),
            (930, 25)
        )

        log_y = 80

        for lg in logs:

            txt = small_font.render(
                lg,
                True,
                (210, 210, 210)
            )

            screen.blit(txt, (900, log_y))

            log_y += 32

        if recording_path:

            pygame.draw.circle(
                screen,
                RED,
                (790, 40),
                10
            )

            screen.blit(
                small_font.render(
                    "RECORDING LETTER PATH",
                    True,
                    RED
                ),
                (810, 32)
            )

        pygame.display.flip()

        clock.tick(60)

    except Exception as e:

        add_log(f"❌ Error: {e}")

        time.sleep(1)

# =========================================================
# ✅ END
# =========================================================