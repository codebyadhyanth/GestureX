import socket
import time
import keyboard
import pygame
import math
import pyautogui   # ✅ REAL CURSOR CONTROL

pyautogui.FAILSAFE = False


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
# 🎮 UI
# =========================================================

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GestureX AIR MOUSE")

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

ARMED = True
last_swipe = 0

pitch = 0
roll = 0


# =========================================================
# 🖱 REAL CURSOR STATE
# =========================================================

cursor_x, cursor_y = pyautogui.position()

mouse_path = []   # 🔥 PATH TRAIL


def switch_mode(direction):
    global mode_index

    if direction == "RIGHT":
        mode_index = (mode_index + 1) % len(modes)
    else:
        mode_index = (mode_index - 1) % len(modes)

    print("MODE →", modes[mode_index])


# =========================================================
# BUFFER
# =========================================================

buffer = ""


# =========================================================
# 🚀 LOOP
# =========================================================

while True:

    try:

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                exit()


        data = sock.recv(1024).decode(errors='ignore')
        buffer += data

        lines = buffer.split("\n")
        buffer = lines[-1]


        for line in lines[:-1]:

            parts = line.strip().split(",")
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
            # MODE SWITCH (FLICK)
            # =================================================

            if abs(pitch) < 10:

                if abs(roll) > 45 and t - last_swipe > 1.5:

                    switch_mode("RIGHT" if roll > 0 else "LEFT")
                    last_swipe = t
                    ARMED = False


            # =================================================
            # RESET ARMING
            # =================================================

            if not ARMED:
                if abs(pitch) < 8 and abs(roll) < 8:
                    ARMED = True


            # =================================================
            # 🖱 AIR MOUSE MODE (REAL SYSTEM CONTROL)
            # =================================================

            if modes[mode_index] == "AIR_MOUSE" and ARMED:

                sensitivity = 8.0

                dx = roll / sensitivity
                dy = -pitch / sensitivity

                cursor_x += dx
                cursor_y += dy

                # smooth clamp
                cursor_x = max(0, min(pyautogui.size().width, cursor_x))
                cursor_y = max(0, min(pyautogui.size().height, cursor_y))

                # MOVE REAL MOUSE (NOT PYGAME)
                pyautogui.moveTo(cursor_x, cursor_y)

                # store path for UI
                mouse_path.append((cursor_x * WIDTH / pyautogui.size().width,
                                   cursor_y * HEIGHT / pyautogui.size().height))

                if len(mouse_path) > 200:
                    mouse_path.pop(0)


            # =================================================
            # OTHER MODES (UNCHANGED LOGIC SIMPLIFIED)
            # =================================================

            else:
                pass  # keep your gesture logic here if needed


        # =====================================================
        # 🎨 UI + PATH TRACING
        # =====================================================

        screen.fill((12, 12, 18))

        cx, cy = WIDTH//2, HEIGHT//2

        # axes
        pygame.draw.line(screen, (100,100,140), (0,cy), (WIDTH,cy), 3)
        pygame.draw.line(screen, (100,100,140), (cx,0), (cx,HEIGHT), 3)

        pygame.draw.circle(screen, (80,80,100), (cx,cy), 220, 2)


        # =================================================
        # 🔥 PATH TRAIL DRAWING
        # =================================================

        if len(mouse_path) > 1:

            for i in range(1, len(mouse_path)):
                pygame.draw.line(screen,
                                 (0, 200, 255),
                                 mouse_path[i-1],
                                 mouse_path[i],
                                 2)


        # =================================================
        # HEADER
        # =================================================

        screen.blit(big_font.render(f"MODE: {modes[mode_index]}", True, (0,200,255)), (20,20))

        screen.blit(font.render(f"Pitch: {pitch:.2f}", True, (255,255,255)), (20,80))
        screen.blit(font.render(f"Roll : {roll:.2f}", True, (255,255,255)), (20,110))
        screen.blit(font.render(f"ARMED: {ARMED}", True, (200,200,200)), (20,140))


        pygame.display.flip()
        clock.tick(60)


    except Exception as e:
        print("Error:", e)
        time.sleep(0.5)