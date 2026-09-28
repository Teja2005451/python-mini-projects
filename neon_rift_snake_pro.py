
import json
import math
import random
import sys
from pathlib import Path

import pygame

# =========================================================
# NEON RIFT SNAKE
# A single-file advanced Snake game made with pygame-ce.
# Install: py -m pip install pygame-ce
# Run:     py neon_rift_snake.py
# =========================================================

pygame.init()

# -------------------------- CONFIG --------------------------
WINDOW_W, WINDOW_H = 1000, 720
FPS = 60

CELL = 24
GRID_W, GRID_H = 30, 24
BOARD_W, BOARD_H = GRID_W * CELL, GRID_H * CELL
BOARD_X, BOARD_Y = 28, 92

SIDEBAR_X = BOARD_X + BOARD_W + 24
SIDEBAR_W = WINDOW_W - SIDEBAR_X - 24

BG = (5, 8, 20)
PANEL = (12, 18, 38)
PANEL_2 = (16, 24, 48)
GRID = (23, 34, 63)
WHITE = (238, 245, 255)
MUTED = (130, 150, 182)

CYAN = (48, 231, 255)
CYAN_2 = (0, 157, 255)
PURPLE = (170, 80, 255)
MAGENTA = (255, 69, 170)
GREEN = (76, 255, 164)
YELLOW = (255, 218, 77)
RED = (255, 88, 108)
ORANGE = (255, 145, 66)

SAVE_FILE = Path(__file__).with_name("snake_highscore.json")

screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("Neon Rift Snake — Tej Edition")
clock = pygame.time.Clock()

FONT_SM = pygame.font.SysFont("segoeui", 16)
FONT_MD = pygame.font.SysFont("segoeui", 22, bold=True)
FONT_LG = pygame.font.SysFont("segoeui", 36, bold=True)
FONT_XL = pygame.font.SysFont("segoeui", 58, bold=True)
FONT_MONO = pygame.font.SysFont("consolas", 20, bold=True)


# -------------------------- HELPERS --------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def load_high_score():
    try:
        data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        return int(data.get("high_score", 0))
    except Exception:
        return 0


def save_high_score(score):
    try:
        SAVE_FILE.write_text(
            json.dumps({"high_score": int(score)}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def grid_to_px(cell):
    x, y = cell
    return BOARD_X + x * CELL, BOARD_Y + y * CELL


def draw_text(surface, text, font, color, pos, anchor="topleft"):
    img = font.render(str(text), True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(img, rect)
    return rect


def rounded_panel(surface, rect, color, radius=18, border=None):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)


def draw_glow_circle(surface, center, radius, color, strength=4):
    glow = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
    c = (glow.get_width() // 2, glow.get_height() // 2)
    for i in range(strength, 0, -1):
        r = radius + i * 6
        alpha = max(10, 40 - i * 5)
        pygame.draw.circle(glow, (*color, alpha), c, r)
    pygame.draw.circle(glow, (*color, 255), c, radius)
    surface.blit(glow, (center[0] - c[0], center[1] - c[1]))


# -------------------------- PARTICLES --------------------------
class Particle:
    def __init__(self, pos, color, speed=160):
        angle = random.random() * math.tau
        mag = random.uniform(speed * 0.35, speed)
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * mag
        self.life = random.uniform(0.35, 0.75)
        self.max_life = self.life
        self.color = color
        self.radius = random.randint(2, 5)

    def update(self, dt):
        self.life -= dt
        self.pos += self.vel * dt
        self.vel *= 0.94

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        r = max(1, int(self.radius * (self.life / self.max_life)))
        particle = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(
            particle,
            (*self.color, alpha),
            (particle.get_width() // 2, particle.get_height() // 2),
            r,
        )
        surface.blit(
            particle,
            (
                self.pos.x - particle.get_width() // 2,
                self.pos.y - particle.get_height() // 2,
            ),
        )


# -------------------------- GAME --------------------------
class Game:
    def __init__(self):
        self.high_score = load_high_score()
        self.state = "menu"  # menu, playing, paused, gameover
        self.particles = []
        self.reset()

    def reset(self):
        cx, cy = GRID_W // 2, GRID_H // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)

        self.score = 0
        self.level = 1
        self.foods_eaten = 0
        self.combo = 1
        self.combo_timer = 0.0

        self.energy = 100.0
        self.shield = 0
        self.phase_timer = 0.0

        self.food = None
        self.food_kind = "normal"
        self.powerup = None
        self.powerup_kind = None
        self.obstacles = set()

        self.portal_a = None
        self.portal_b = None
        self.portal_cooldown = 0

        self.move_timer = 0.0
        self.flash_timer = 0.0
        self.message = ""
        self.message_timer = 0.0

        self.spawn_food()
        self.particles.clear()

    def start(self):
        self.reset()
        self.state = "playing"

    def occupied_cells(self):
        cells = set(self.snake) | self.obstacles
        if self.portal_a:
            cells.add(self.portal_a)
        if self.portal_b:
            cells.add(self.portal_b)
        if self.food:
            cells.add(self.food)
        if self.powerup:
            cells.add(self.powerup)
        return cells

    def random_free_cell(self, extra_blocked=None):
        blocked = self.occupied_cells()
        if extra_blocked:
            blocked |= set(extra_blocked)
        candidates = [
            (x, y)
            for y in range(GRID_H)
            for x in range(GRID_W)
            if (x, y) not in blocked
        ]
        return random.choice(candidates) if candidates else None

    def spawn_food(self):
        cell = self.random_free_cell()
        if cell is None:
            return
        self.food = cell
        self.food_kind = "gold" if random.random() < 0.14 else "normal"

    def spawn_powerup(self):
        if self.powerup is not None:
            return
        cell = self.random_free_cell()
        if cell is None:
            return
        self.powerup = cell
        self.powerup_kind = random.choice(["shield", "energy"])

    def create_portals(self):
        if self.portal_a or self.score < 40:
            return
        a = self.random_free_cell()
        if not a:
            return
        b = self.random_free_cell(extra_blocked=[a])
        if not b:
            return
        self.portal_a, self.portal_b = a, b
        self.message = "RIFT PORTALS ONLINE"
        self.message_timer = 1.8

    def add_obstacles_for_level(self):
        target = max(0, (self.level - 2) * 2)
        while len(self.obstacles) < target:
            cell = self.random_free_cell()
            if cell and abs(cell[0] - self.snake[0][0]) + abs(cell[1] - self.snake[0][1]) > 5:
                self.obstacles.add(cell)
            else:
                break

    def set_direction(self, direction):
        dx, dy = direction
        cdx, cdy = self.direction
        if (dx, dy) != (-cdx, -cdy):
            self.next_direction = direction

    def cell_center(self, cell):
        x, y = grid_to_px(cell)
        return (x + CELL // 2, y + CELL // 2)

    def burst(self, cell, color, count=18):
        center = self.cell_center(cell)
        for _ in range(count):
            self.particles.append(Particle(center, color))

    def handle_collision(self, cell):
        x, y = cell
        hit_wall = x < 0 or x >= GRID_W or y < 0 or y >= GRID_H
        hit_body = cell in self.snake[:-1]
        hit_obstacle = cell in self.obstacles

        if not (hit_wall or hit_body or hit_obstacle):
            return False

        if self.phase_timer > 0:
            return False

        if self.shield > 0:
            self.shield -= 1
            self.flash_timer = 0.25
            self.message = "SHIELD SAVED YOU"
            self.message_timer = 1.0
            return False

        self.game_over()
        return True

    def normalize_cell(self, cell):
        # During phase mode, crossing the edge wraps around.
        x, y = cell
        if self.phase_timer > 0:
            x %= GRID_W
            y %= GRID_H
        return x, y

    def move_step(self):
        self.direction = self.next_direction
        dx, dy = self.direction
        hx, hy = self.snake[0]
        new_head = self.normalize_cell((hx + dx, hy + dy))

        if self.handle_collision(new_head):
            return

        # If collision was blocked by a shield but still outside board,
        # keep the snake in the valid area.
        x, y = new_head
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            x = clamp(x, 0, GRID_W - 1)
            y = clamp(y, 0, GRID_H - 1)
            new_head = (x, y)

        # Portal travel
        if self.portal_cooldown <= 0:
            if new_head == self.portal_a:
                new_head = self.portal_b
                self.portal_cooldown = 3
                self.phase_timer = max(self.phase_timer, 0.25)
                self.burst(self.portal_b, PURPLE, 24)
            elif new_head == self.portal_b:
                new_head = self.portal_a
                self.portal_cooldown = 3
                self.phase_timer = max(self.phase_timer, 0.25)
                self.burst(self.portal_a, CYAN, 24)

        self.snake.insert(0, new_head)

        grew = False

        # Food
        if new_head == self.food:
            grew = True
            self.foods_eaten += 1

            if self.combo_timer > 0:
                self.combo = min(5, self.combo + 1)
            else:
                self.combo = 1

            self.combo_timer = 4.0

            base = 30 if self.food_kind == "gold" else 10
            gained = base * self.combo
            self.score += gained

            color = YELLOW if self.food_kind == "gold" else MAGENTA
            self.burst(new_head, color, 24 if self.food_kind == "gold" else 16)

            self.spawn_food()

            if self.foods_eaten % 6 == 0:
                self.spawn_powerup()

            new_level = 1 + self.score // 120
            if new_level > self.level:
                self.level = new_level
                self.message = f"LEVEL {self.level}"
                self.message_timer = 1.5
                self.add_obstacles_for_level()

            self.create_portals()

        # Powerup
        if self.powerup and new_head == self.powerup:
            if self.powerup_kind == "shield":
                self.shield = min(2, self.shield + 1)
                self.message = "SHIELD +1"
                self.burst(new_head, CYAN, 24)
            else:
                self.energy = 100
                self.message = "ENERGY FULL"
                self.burst(new_head, GREEN, 24)
            self.message_timer = 1.2
            self.powerup = None
            self.powerup_kind = None

        if not grew:
            self.snake.pop()

        if self.portal_cooldown > 0:
            self.portal_cooldown -= 1

    def dash(self):
        if self.state != "playing" or self.energy < 40:
            return
        self.energy -= 40
        self.phase_timer = 0.6
        self.message = "PHASE DASH"
        self.message_timer = 0.7

        # Move two extra cells immediately in phase mode.
        for _ in range(2):
            if self.state == "playing":
                self.move_step()

        self.burst(self.snake[0], CYAN, 28)

    def game_over(self):
        self.state = "gameover"
        self.burst(self.snake[0], RED, 42)
        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)

    def update(self, dt):
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        if self.state != "playing":
            return

        self.energy = min(100.0, self.energy + 14.0 * dt)
        self.phase_timer = max(0.0, self.phase_timer - dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.message_timer = max(0.0, self.message_timer - dt)

        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 1

        speed_ms = max(62, 150 - (self.level - 1) * 8)
        self.move_timer += dt * 1000
        if self.move_timer >= speed_ms:
            self.move_timer %= speed_ms
            self.move_step()

    # -------------------------- DRAW --------------------------
    def draw_background(self):
        screen.fill(BG)

        # Header
        draw_text(screen, "NEON RIFT SNAKE", FONT_LG, WHITE, (28, 24))
        draw_text(
            screen,
            "TEJ EDITION  //  phase-powered arcade snake",
            FONT_SM,
            MUTED,
            (30, 64),
        )

        board_rect = pygame.Rect(BOARD_X - 8, BOARD_Y - 8, BOARD_W + 16, BOARD_H + 16)
        rounded_panel(screen, board_rect, PANEL, 18, GRID)

        side_rect = pygame.Rect(SIDEBAR_X, BOARD_Y - 8, SIDEBAR_W, BOARD_H + 16)
        rounded_panel(screen, side_rect, PANEL, 18, GRID)

        # Grid
        for x in range(GRID_W + 1):
            px = BOARD_X + x * CELL
            pygame.draw.line(screen, GRID, (px, BOARD_Y), (px, BOARD_Y + BOARD_H), 1)
        for y in range(GRID_H + 1):
            py = BOARD_Y + y * CELL
            pygame.draw.line(screen, GRID, (BOARD_X, py), (BOARD_X + BOARD_W, py), 1)

    def draw_board_objects(self):
        # Obstacles
        for cell in self.obstacles:
            x, y = grid_to_px(cell)
            rect = pygame.Rect(x + 3, y + 3, CELL - 6, CELL - 6)
            pygame.draw.rect(screen, (52, 60, 86), rect, border_radius=5)
            pygame.draw.line(screen, RED, rect.topleft, rect.bottomright, 2)

        # Portals
        if self.portal_a and self.portal_b:
            t = pygame.time.get_ticks() / 1000
            for cell, color in [(self.portal_a, PURPLE), (self.portal_b, CYAN)]:
                cx, cy = self.cell_center(cell)
                radius = 7 + int(2 * math.sin(t * 6))
                draw_glow_circle(screen, (cx, cy), radius, color, 3)
                pygame.draw.circle(screen, BG, (cx, cy), 4)

        # Food
        if self.food:
            center = self.cell_center(self.food)
            color = YELLOW if self.food_kind == "gold" else MAGENTA
            radius = 7 if self.food_kind == "normal" else 9
            draw_glow_circle(screen, center, radius, color, 3)
            if self.food_kind == "gold":
                pygame.draw.circle(screen, WHITE, center, 2)

        # Powerup
        if self.powerup:
            center = self.cell_center(self.powerup)
            color = CYAN if self.powerup_kind == "shield" else GREEN
            draw_glow_circle(screen, center, 8, color, 3)
            symbol = "S" if self.powerup_kind == "shield" else "E"
            draw_text(screen, symbol, FONT_SM, BG, center, "center")

        # Snake body
        for i in range(len(self.snake) - 1, -1, -1):
            cell = self.snake[i]
            x, y = grid_to_px(cell)
            inset = 2 if i == 0 else 4
            rect = pygame.Rect(x + inset, y + inset, CELL - inset * 2, CELL - inset * 2)

            if i == 0:
                color = WHITE if self.phase_timer > 0 else CYAN
                glow = pygame.Surface((CELL * 2, CELL * 2), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow,
                    (*CYAN, 55),
                    pygame.Rect(4, 4, CELL + 8, CELL + 8),
                    border_radius=10,
                )
                screen.blit(glow, (x - CELL // 2, y - CELL // 2))
                pygame.draw.rect(screen, color, rect, border_radius=7)

                # Eyes
                dx, dy = self.direction
                eye_offset_x = 5 if dx >= 0 else -5
                eye_offset_y = 5 if dy >= 0 else -5
                cx, cy = rect.center
                if dx != 0:
                    pygame.draw.circle(screen, BG, (cx + dx * 5, cy - 4), 2)
                    pygame.draw.circle(screen, BG, (cx + dx * 5, cy + 4), 2)
                else:
                    pygame.draw.circle(screen, BG, (cx - 4, cy + dy * 5), 2)
                    pygame.draw.circle(screen, BG, (cx + 4, cy + dy * 5), 2)
            else:
                ratio = 1 - i / max(1, len(self.snake))
                color = (
                    int(CYAN_2[0] + (GREEN[0] - CYAN_2[0]) * ratio),
                    int(CYAN_2[1] + (GREEN[1] - CYAN_2[1]) * ratio),
                    int(CYAN_2[2] + (GREEN[2] - CYAN_2[2]) * ratio),
                )
                pygame.draw.rect(screen, color, rect, border_radius=6)

        # Particles
        for particle in self.particles:
            particle.draw(screen)

    def draw_sidebar(self):
        x = SIDEBAR_X + 18
        y = BOARD_Y + 12

        draw_text(screen, "SCORE", FONT_SM, MUTED, (x, y))
        draw_text(screen, self.score, FONT_XL, WHITE, (x, y + 20))
        y += 94

        draw_text(screen, f"HIGH  {self.high_score}", FONT_MD, YELLOW, (x, y))
        y += 42
        draw_text(screen, f"LEVEL  {self.level}", FONT_MD, CYAN, (x, y))
        y += 42

        if self.combo > 1 and self.combo_timer > 0:
            draw_text(screen, f"COMBO  x{self.combo}", FONT_MD, MAGENTA, (x, y))
        else:
            draw_text(screen, "COMBO  x1", FONT_MD, MUTED, (x, y))
        y += 58

        draw_text(screen, "PHASE ENERGY", FONT_SM, MUTED, (x, y))
        bar = pygame.Rect(x, y + 24, SIDEBAR_W - 36, 15)
        pygame.draw.rect(screen, (31, 40, 65), bar, border_radius=8)
        fill = bar.copy()
        fill.width = int(bar.width * self.energy / 100)
        pygame.draw.rect(screen, CYAN, fill, border_radius=8)
        draw_text(screen, f"{int(self.energy)}%", FONT_SM, WHITE, (bar.right, y + 42), "topright")
        y += 76

        draw_text(screen, "SHIELD", FONT_SM, MUTED, (x, y))
        shield_text = "ON" if self.shield else "OFF"
        shield_color = CYAN if self.shield else MUTED
        draw_text(screen, f"{shield_text}  x{self.shield}", FONT_MD, shield_color, (x, y + 22))
        y += 74

        draw_text(screen, "CONTROLS", FONT_SM, MUTED, (x, y))
        controls = [
            "WASD / Arrows  Move",
            "SPACE          Phase Dash",
            "P              Pause",
            "R              Restart",
            "ESC            Menu",
        ]
        for line in controls:
            y += 26
            draw_text(screen, line, FONT_SM, WHITE, (x, y))

        if self.message_timer > 0:
            msg_rect = pygame.Rect(BOARD_X + 150, BOARD_Y + 18, BOARD_W - 300, 46)
            rounded_panel(screen, msg_rect, (20, 31, 59), 13, CYAN)
            draw_text(screen, self.message, FONT_MD, WHITE, msg_rect.center, "center")

    def draw_menu(self):
        self.draw_background()
        # Dark overlay over board for cinematic menu
        overlay = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        overlay.fill((4, 7, 18, 195))
        screen.blit(overlay, (BOARD_X, BOARD_Y))

        cx = BOARD_X + BOARD_W // 2
        cy = BOARD_Y + BOARD_H // 2 - 40

        draw_text(screen, "NEON", FONT_XL, CYAN, (cx, cy - 105), "center")
        draw_text(screen, "RIFT SNAKE", FONT_XL, WHITE, (cx, cy - 45), "center")
        draw_text(
            screen,
            "Classic Snake + phase dash + portals + shields + combo scoring",
            FONT_SM,
            MUTED,
            (cx, cy + 24),
            "center",
        )

        button = pygame.Rect(cx - 130, cy + 75, 260, 58)
        rounded_panel(screen, button, CYAN_2, 16)
        draw_text(screen, "PRESS ENTER TO PLAY", FONT_MD, WHITE, button.center, "center")

        draw_text(
            screen,
            "Tip: save your phase dash for impossible corners.",
            FONT_SM,
            MUTED,
            (cx, cy + 165),
            "center",
        )

        draw_text(screen, "BEST", FONT_SM, MUTED, (SIDEBAR_X + 20, BOARD_Y + 26))
        draw_text(screen, self.high_score, FONT_XL, YELLOW, (SIDEBAR_X + 20, BOARD_Y + 50))
        draw_text(screen, "FEATURES", FONT_SM, MUTED, (SIDEBAR_X + 20, BOARD_Y + 145))

        features = [
            "• phase dash",
            "• rift portals",
            "• combo multiplier",
            "• shield pickups",
            "• dynamic obstacles",
            "• persistent high score",
        ]
        yy = BOARD_Y + 178
        for item in features:
            draw_text(screen, item, FONT_SM, WHITE, (SIDEBAR_X + 20, yy))
            yy += 32

    def draw_pause(self):
        self.draw_game()
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((2, 4, 12, 170))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "PAUSED", FONT_XL, WHITE, (WINDOW_W // 2, WINDOW_H // 2 - 40), "center")
        draw_text(
            screen,
            "Press P to continue",
            FONT_MD,
            CYAN,
            (WINDOW_W // 2, WINDOW_H // 2 + 25),
            "center",
        )

    def draw_gameover(self):
        self.draw_game()
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((4, 4, 12, 190))
        screen.blit(overlay, (0, 0))

        box = pygame.Rect(WINDOW_W // 2 - 240, WINDOW_H // 2 - 150, 480, 300)
        rounded_panel(screen, box, PANEL, 24, RED)

        draw_text(screen, "SYSTEM CRASH", FONT_LG, RED, (box.centerx, box.y + 42), "center")
        draw_text(screen, f"SCORE  {self.score}", FONT_XL, WHITE, (box.centerx, box.y + 105), "center")
        draw_text(
            screen,
            f"BEST  {self.high_score}",
            FONT_MD,
            YELLOW,
            (box.centerx, box.y + 170),
            "center",
        )
        draw_text(
            screen,
            "ENTER = retry     ESC = menu",
            FONT_MD,
            CYAN,
            (box.centerx, box.y + 225),
            "center",
        )

    def draw_game(self):
        self.draw_background()
        self.draw_board_objects()
        self.draw_sidebar()

        if self.flash_timer > 0:
            flash = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            flash.fill((48, 231, 255, 55))
            screen.blit(flash, (BOARD_X, BOARD_Y))

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        elif self.state == "paused":
            self.draw_pause()
        elif self.state == "gameover":
            self.draw_gameover()


# -------------------------- INPUT --------------------------
game = Game()

KEY_TO_DIR = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}

running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if game.state == "menu":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    game.start()
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif game.state == "playing":
                if event.key in KEY_TO_DIR:
                    game.set_direction(KEY_TO_DIR[event.key])
                elif event.key == pygame.K_SPACE:
                    game.dash()
                elif event.key == pygame.K_p:
                    game.state = "paused"
                elif event.key == pygame.K_r:
                    game.start()
                elif event.key == pygame.K_ESCAPE:
                    game.state = "menu"

            elif game.state == "paused":
                if event.key == pygame.K_p:
                    game.state = "playing"
                elif event.key == pygame.K_r:
                    game.start()
                elif event.key == pygame.K_ESCAPE:
                    game.state = "menu"

            elif game.state == "gameover":
                if event.key == pygame.K_RETURN:
                    game.start()
                elif event.key == pygame.K_ESCAPE:
                    game.state = "menu"

    game.update(dt)
    game.draw()
    pygame.display.flip()

pygame.quit()
sys.exit()
