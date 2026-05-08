import socket
import time
import keyboard
import pygame
import math

# =========================================================
# 🌐 WIFI CONNECTION
# =========================================================

HOST = '192.168.4.1'
PORT = 1234

print("🔌 Connecting to ESP32...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 🚀 IMPORTANT FIX: reduces lag from buffering
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.settimeout(0.5)

sock.connect((HOST, PORT))

print("✅ Connected to ESP32")


# =========================================================
# 🎮 PYGAME VISUALIZER
# =========================================================

pygame.init()

WIDTH = 900
HEIGHT = 700

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("ESP32 MPU6050 Tilt Visualizer")

font = pygame.font.SysFont("Arial", 28)

clock = pygame.time.Clock()


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

TH = 1200
DEAD_ZONE = 300
RETURN_ZONE = 150
STABLE_TIME = 0.20
DEBOUNCE = 0.8

SWIPE_DELTA = 3500
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


def switch_mode(direction):
    global mode_index

    if direction == "RIGHT":
        mode_index = (mode_index + 1) % len(modes)
    else:
        mode_index = (mode_index - 1) % len(modes)

    print(f"\n🔁 MODE → {modes[mode_index]}\n")


# =========================================================
# 🔁 BUFFER (FIXED STREAM HANDLING)
# =========================================================

buffer = ""


# =========================================================
# 🚀 MAIN LOOP
# =========================================================

tilt_x = 0
tilt_y = 0

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
        # 🧠 FIXED DATA READING (IMPORTANT PART)
        # =====================================================

        try:
            data = sock.recv(1024).decode(errors='ignore')

        except socket.timeout:
            continue

        except Exception:
            continue

        if not data:
            continue

        buffer += data

        # split safely
        lines = buffer.split("\n")
        buffer = lines[-1]   # keep incomplete line

        for line in lines[:-1]:

            line = line.strip().replace("\r", "")

            parts = line.split(",")

            # ESP32 sends 6 values → we only need AX, AY
            if len(parts) < 2:
                continue

            try:
                ax_raw = float(parts[0])
                ay_raw = float(parts[1])

            except:
                continue


            # =================================================
            # FILTER
            # =================================================

            ax = kf_ax.update(ax_raw)
            ay = kf_ay.update(ay_raw)

            current_time = time.time()


            # =================================================
            # VISUALIZATION
            # =================================================

            tilt_x = max(min(ax / 15, 250), -250)
            tilt_y = max(min(ay / 15, 250), -250)


            # =================================================
            # SWIPE DETECTION
            # =================================================

            dx = ax_raw - prev_ax
            dy = ay_raw - prev_ay

            prev_ax = ax_raw
            prev_ay = ay_raw

            near_center = abs(ax) < 500 and abs(ay) < 500

            if near_center:

                if abs(dx) > SWIPE_DELTA and abs(dx) > abs(dy) * 2:

                    if current_time - last_swipe > SWIPE_COOLDOWN:

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
            # DEAD ZONE
            # =================================================

            if abs(ax) < DEAD_ZONE:
                ax = 0

            if abs(ay) < DEAD_ZONE:
                ay = 0


            # =================================================
            # LOCK LOGIC
            # =================================================

            if gesture_locked:
                if abs(ax) < RETURN_ZONE and abs(ay) < RETURN_ZONE:
                    gesture_locked = False
                else:
                    continue


            # =================================================
            # DIRECTION DETECTION
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
            # STABILITY CHECK
            # =================================================

            if new_state != current_state:
                current_state = new_state
                state_start = current_time


            # =================================================
            # ACTION TRIGGER
            # =================================================

            if current_state != "NEUTRAL":

                if current_time - state_start > STABLE_TIME:

                    if current_time - last_trigger > DEBOUNCE:

                        mode = modes[mode_index]

                        print(f"\n🎯 Gesture: {current_state}")
                        print(f"📌 Mode: {mode}")


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
                            else:
                                prev_page()

                        gesture_locked = True
                        last_trigger = current_time
                        current_state = "NEUTRAL"


        # =====================================================
        # VISUALIZER
        # =====================================================

        screen.fill((15, 15, 20))

        center_x = WIDTH // 2
        center_y = HEIGHT // 2

        pygame.draw.line(screen, (80, 80, 80), (0, center_y), (WIDTH, center_y), 2)
        pygame.draw.line(screen, (80, 80, 80), (center_x, 0), (center_x, HEIGHT), 2)

        pygame.draw.circle(screen, (60, 60, 60), (center_x, center_y), 250, 3)
        pygame.draw.circle(screen, (40, 120, 40), (center_x, center_y), 40)

        ball_x = int(center_x + tilt_x)
        ball_y = int(center_y + tilt_y)

        pygame.draw.circle(screen, (0, 200, 255), (ball_x, ball_y), 25)

        screen.blit(font.render(f"Gesture: {current_state}", True, (255,255,255)), (20, 20))
        screen.blit(font.render(f"Mode: {modes[mode_index]}", True, (255,255,0)), (20, 60))

        pygame.display.flip()
        clock.tick(60)


    except Exception as e:
        print("❌ Error:", e)
        time.sleep(1)