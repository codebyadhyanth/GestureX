import socket
import time
import keyboard
import pygame
import math

# =========================================================
# 🌐 CONNECTION
# =========================================================

HOST = '192.168.4.1'
PORT = 1234

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.settimeout(0.5)

sock.connect((HOST, PORT))


# =========================================================
# 🎮 PYGAME
# =========================================================

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GestureX - AIR MOUSE MODE")

font = pygame.font.SysFont("Arial", 22)
big_font = pygame.font.SysFont("Arial", 30)

clock = pygame.time.Clock()


# =========================================================
# 🧠 FILTER
# =========================================================

class Kalman1D:
    def __init__(self):
        self.x = 0
        self.p = 1
        self.q = 0.02
        self.r = 1

    def update(self, z):
        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x += k * (z - self.x)
        self.p *= (1 - k)
        return self.x


kf_pitch = Kalman1D()
kf_roll = Kalman1D()


# =========================================================
# ⚙ MODES
# =========================================================

modes = ["AIR_MOUSE", "MUSIC", "NORMAL", "PRESENTATION"]
mode_index = 0

current_state = "NEUTRAL"
ARMED = True

last_trigger = 0
last_swipe = 0

cursor_x = WIDTH // 2
cursor_y = HEIGHT // 2

vx = 0
vy = 0


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


# =========================================================
# 🚀 MAIN LOOP
# =========================================================

while True:

    try:

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                exit()


        # =====================================================
        # RECEIVE DATA
        # =====================================================

        data = sock.recv(1024).decode(errors='ignore')
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
            # PITCH / ROLL
            # =================================================

            pitch = kf_pitch.update(
                math.degrees(math.atan2(ax, math.sqrt(ay*ay + az*az)))
            )

            roll = kf_roll.update(
                math.degrees(math.atan2(ay, math.sqrt(ax*ax + az*az)))
            )

            t = time.time()


            # =================================================
            # SWIPE MODE CHANGE (Flick)
            # =================================================

            if abs(pitch) < 10:

                if abs(roll) > 45 and t - last_swipe > 1.5:

                    switch_mode("RIGHT" if roll > 0 else "LEFT")

                    last_swipe = t
                    ARMED = False
                    continue


            # =================================================
            # RESET SYSTEM
            # =================================================

            if not ARMED:
                if abs(pitch) < 8 and abs(roll) < 8:
                    ARMED = True


            # =================================================
            # 🎯 AIR MOUSE MODE
            # =================================================

            if modes[mode_index] == "AIR_MOUSE" and ARMED:

                # sensitivity tuning
                sensitivity = 6.0

                vx = roll / sensitivity
                vy = -pitch / sensitivity

                # inertia
                cursor_x += vx
                cursor_y += vy

                vx *= 0.85
                vy *= 0.85

                # clamp
                cursor_x = max(0, min(WIDTH, cursor_x))
                cursor_y = max(0, min(HEIGHT, cursor_y))

                # move system cursor
                pygame.mouse.set_pos(int(cursor_x), int(cursor_y))


            # =================================================
            # NORMAL GESTURE MODES
            # =================================================

            else:

                new_state = "NEUTRAL"

                if abs(pitch) > abs(roll):

                    if pitch > 15:
                        new_state = "FORWARD"
                    elif pitch < -15:
                        new_state = "BACKWARD"

                else:

                    if roll > 15:
                        new_state = "RIGHT"
                    elif roll < -15:
                        new_state = "LEFT"


                if new_state != "NEUTRAL" and ARMED:

                    mode = modes[mode_index]

                    print("Gesture:", new_state, "Mode:", mode)

                    if mode == "MUSIC":

                        if new_state == "FORWARD":
                            keyboard.send("volume up")
                        elif new_state == "BACKWARD":
                            keyboard.send("volume down")
                        elif new_state == "RIGHT":
                            keyboard.send("next track")
                        elif new_state == "LEFT":
                            keyboard.send("previous track")

                    elif mode == "NORMAL":

                        if new_state == "FORWARD":
                            keyboard.send("page up")
                        elif new_state == "BACKWARD":
                            keyboard.send("page down")
                        elif new_state == "RIGHT":
                            keyboard.send("right")
                        elif new_state == "LEFT":
                            keyboard.send("left")

                    elif mode == "PRESENTATION":

                        if new_state in ["FORWARD", "RIGHT"]:
                            keyboard.send("right")
                        else:
                            keyboard.send("left")

                    ARMED = False


        # =====================================================
        # 🎨 UI (CLEAN + CURSOR FEEDBACK)
        # =====================================================

        screen.fill((12, 12, 18))

        cx, cy = WIDTH//2, HEIGHT//2

        # axes
        pygame.draw.line(screen, (100,100,140), (0,cy), (WIDTH,cy), 3)
        pygame.draw.line(screen, (100,100,140), (cx,0), (cx,HEIGHT), 3)

        # control circle
        pygame.draw.circle(screen, (70,70,90), (cx,cy), 200, 2)

        # cursor (only in air mouse mode)
        if modes[mode_index] == "AIR_MOUSE":
            pygame.draw.circle(screen, (0,200,255), (int(cursor_x), int(cursor_y)), 10)

        # header
        screen.blit(big_font.render(f"MODE: {modes[mode_index]}", True, (0,200,255)), (20,20))

        # debug
        screen.blit(font.render(f"Pitch: {pitch:.2f}", True, (255,255,255)), (20,80))
        screen.blit(font.render(f"Roll : {roll:.2f}", True, (255,255,255)), (20,110))
        screen.blit(font.render(f"ARMED: {ARMED}", True, (200,200,200)), (20,140))

        pygame.display.flip()
        clock.tick(60)


    except Exception as e:
        print("Error:", e)
        time.sleep(0.5)