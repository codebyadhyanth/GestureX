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
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.settimeout(0.5)

sock.connect((HOST, PORT))

print("✅ Connected to ESP32")


# =========================================================
# 🎮 UI INIT
# =========================================================

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GestureX - Pitch & Roll Controller")

font = pygame.font.SysFont("Arial", 22)
big_font = pygame.font.SysFont("Arial", 30)

clock = pygame.time.Clock()


# =========================================================
# 🎵 MEDIA CONTROLS
# =========================================================

def volume_up(): keyboard.send("volume up")
def volume_down(): keyboard.send("volume down")
def next_song(): keyboard.send("next track")
def prev_song(): keyboard.send("previous track")
def scroll_up(): keyboard.send("page up")
def scroll_down(): keyboard.send("page down")
def next_page(): keyboard.send("right")
def prev_page(): keyboard.send("left")


# =========================================================
# 🧠 KALMAN FILTER
# =========================================================

class Kalman1D:
    def __init__(self, q=0.02, r=1.0):
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

TH = 15              # gesture threshold
RESET_ZONE = 8       # must return inside this to reset
SWIPE_THRESHOLD = 45

STABLE_TIME = 0.2
DEBOUNCE = 0.8
SWIPE_COOLDOWN = 1.5


# =========================================================
# 📌 STATES
# =========================================================

modes = ["MUSIC", "NORMAL", "PRESENTATION"]
mode_index = 0

current_state = "NEUTRAL"

ARMED = True
last_trigger = 0
last_swipe = 0
state_start = 0


def switch_mode(direction):
    global mode_index

    if direction == "RIGHT":
        mode_index = (mode_index + 1) % len(modes)
    else:
        mode_index = (mode_index - 1) % len(modes)

    print(f"\n🔁 MODE → {modes[mode_index]}\n")


# =========================================================
# 📡 BUFFER
# =========================================================

buffer = ""

pitch = 0
roll = 0


# =========================================================
# 🚀 MAIN LOOP
# =========================================================

while True:

    try:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()


        # =====================================================
        # 📡 RECEIVE DATA
        # =====================================================

        try:
            data = sock.recv(1024).decode(errors='ignore')
        except:
            continue

        if not data:
            continue

        buffer += data
        lines = buffer.split("\n")
        buffer = lines[-1]


        for line in lines[:-1]:

            line = line.strip().replace("\r", "")
            parts = line.split(",")

            if len(parts) < 6:
                continue

            try:
                ax = float(parts[0])
                ay = float(parts[1])
                az = float(parts[2])
            except:
                continue


            # =================================================
            # 📐 PITCH & ROLL
            # =================================================

            pitch_raw = math.degrees(
                math.atan2(ax, math.sqrt(ay*ay + az*az))
            )

            roll_raw = math.degrees(
                math.atan2(ay, math.sqrt(ax*ax + az*az))
            )


            pitch = kf_pitch.update(pitch_raw)
            roll = kf_roll.update(roll_raw)

            current_time = time.time()


            # =================================================
            # 🔓 RESET LOGIC (MUST PASS THROUGH CENTER ZONE)
            # =================================================

            if not ARMED:
                if abs(pitch) < RESET_ZONE and abs(roll) < RESET_ZONE:
                    ARMED = True


            # =================================================
            # 🎯 GESTURE DETECTION (ONLY IF ARMED)
            # =================================================

            if ARMED:

                new_state = "NEUTRAL"

                if abs(pitch) > abs(roll):

                    if pitch > TH:
                        new_state = "FORWARD"
                    elif pitch < -TH:
                        new_state = "BACKWARD"

                else:

                    if roll > TH:
                        new_state = "RIGHT"
                    elif roll < -TH:
                        new_state = "LEFT"


                if new_state != "NEUTRAL":

                    if current_time - last_trigger > DEBOUNCE:

                        mode = modes[mode_index]

                        print(f"\n🎯 Gesture: {new_state}")
                        print(f"📌 Mode: {mode}")


                        # ============================
                        # 🎵 MUSIC MODE
                        # ============================

                        if mode == "MUSIC":

                            if new_state == "FORWARD":
                                volume_up()
                            elif new_state == "BACKWARD":
                                volume_down()
                            elif new_state == "RIGHT":
                                next_song()
                            elif new_state == "LEFT":
                                prev_song()


                        # ============================
                        # 💻 NORMAL MODE
                        # ============================

                        elif mode == "NORMAL":

                            if new_state == "FORWARD":
                                scroll_up()
                            elif new_state == "BACKWARD":
                                scroll_down()
                            elif new_state == "RIGHT":
                                next_page()
                            elif new_state == "LEFT":
                                prev_page()


                        # ============================
                        # 📽 PRESENTATION MODE
                        # ============================

                        elif mode == "PRESENTATION":

                            if new_state in ["FORWARD", "RIGHT"]:
                                next_page()
                            else:
                                prev_page()


                        ARMED = False
                        last_trigger = current_time
                        current_state = new_state


            # =================================================
            # 🔁 MODE SWITCH (SWIPE BASED ON ROLL)
            # =================================================

            if abs(pitch) < 10:

                if abs(roll) > SWIPE_THRESHOLD and current_time - last_swipe > SWIPE_COOLDOWN:

                    if roll > 0:
                        switch_mode("RIGHT")
                    else:
                        switch_mode("LEFT")

                    last_swipe = current_time
                    ARMED = False


        # =====================================================
        # 🎨 CLEAN AXIS UI
        # =====================================================

        screen.fill((10, 10, 16))

        w, h = WIDTH, HEIGHT
        CX, CY = w // 2, h // 2

        AXIS = (80, 80, 110)
        BOLD = (140, 140, 180)
        ACCENT = (0, 200, 255)
        TEXT = (240, 240, 240)


        # FULL SCREEN AXIS
        pygame.draw.line(screen, BOLD, (0, CY), (w, CY), 3)
        pygame.draw.line(screen, BOLD, (CX, 0), (CX, h), 3)


        # CONTROL CIRCLE
        pygame.draw.circle(screen, AXIS, (CX, CY), 220, 2)
        pygame.draw.circle(screen, (30, 30, 45), (CX, CY), 60, 1)


        # POINTER
        x = int(CX + roll * 4)
        y = int(CY - pitch * 4)

        pygame.draw.circle(screen, ACCENT, (x, y), 18)


        # HEADER
        pygame.draw.rect(screen, (18, 18, 26), (0, 0, w, 60))

        screen.blit(big_font.render(f"MODE: {modes[mode_index]}", True, ACCENT), (20, 15))
        screen.blit(big_font.render(f"STATE: {current_state}", True, TEXT), (280, 15))


        # INFO PANEL
        screen.blit(font.render(f"Pitch: {pitch:.2f}", True, TEXT), (20, 90))
        screen.blit(font.render(f"Roll : {roll:.2f}", True, TEXT), (20, 120))
        screen.blit(font.render(f"ARMED: {ARMED}", True, TEXT), (20, 150))


        pygame.display.flip()
        clock.tick(60)


    except Exception as e:
        print("❌ Error:", e)
        time.sleep(1)