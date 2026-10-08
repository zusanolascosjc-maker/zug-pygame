import os
import pygame

pygame.init()

# ---------- Window ----------
WIDTH, HEIGHT = 1024, 384          # wider view (was 640 x 384). Try 1152 or 1280 if you like.
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("My 2D Platformer")
clock = pygame.time.Clock()

BASE = os.path.dirname(os.path.abspath(__file__))


def find_file(*names):
    """Search the Zug folder (and every folder inside it) for the first name that exists.
    Capital letters are ignored."""
    wanted = [n.lower() for n in names]
    for want in wanted:
        for root, dirs, files in os.walk(BASE):
            dirs[:] = [d for d in dirs if "goblin" not in d.lower()]   # (ignore any old goblin folder)
            for f in files:
                if f.lower() == want:
                    return os.path.join(root, f)
    raise FileNotFoundError(f"Could not find any of {names} under {BASE}")


# ---------- Background layers ----------
def load_bg(name):
    img = pygame.image.load(find_file(name)).convert_alpha()
    scale = HEIGHT / img.get_height()                 # fit to window height
    return pygame.transform.scale(img, (int(img.get_width() * scale), HEIGHT))


clouds_back = load_bg("CloudsBack.png")     # sky + big clouds (farthest)
clouds_front = load_bg("CloudsFront.png")   # lighter clouds
bg_back = load_bg("BGBack.png")             # far purple mountains
bg_front = load_bg("BGFront.png")           # mountains + green ground (nearest)


def draw_layer(img, factor):
    w = img.get_width()
    x = -(int(camera_x * factor) % w)
    while x < WIDTH:
        screen.blit(img, (x, 0))
        x += w


# ---------- Tileset ----------
TILE = 16                  # tile size inside Tileset.png
SCALE = 2                  # draw everything 2x bigger (16 -> 32 px)
T = TILE * SCALE

tileset = pygame.image.load(find_file("Tileset.png")).convert_alpha()


def get_tile(col, row):
    surf = tileset.subsurface((col * TILE, row * TILE, TILE, TILE))
    return pygame.transform.scale(surf, (T, T))


def get_part(x, y, w, h):
    """Cut any rectangle (in pixels) out of the tileset and scale it."""
    surf = tileset.subsurface((x, y, w, h))
    return pygame.transform.scale(surf, (w * SCALE, h * SCALE))


# The big rock block in the top-left of Tileset.png is a 3x3 set of pieces:
#   top-left  top  top-right
#   left      fill right
#   bot-left  bot  bot-right
ROCK = {
    "TL": get_tile(0, 0), "T": get_tile(1, 0), "TR": get_tile(2, 0),
    "L": get_tile(0, 1), "R": get_tile(2, 1),
    "BL": get_tile(0, 2), "B": get_tile(1, 2), "BR": get_tile(2, 2),
}
FILL = [get_tile(1, 1), get_tile(1, 1), get_tile(1, 1), get_tile(4, 0)]

# Grass strip (laid on top of the rock): left end, middle, right end
GRASS_L = get_part(103, 29, 16, 13)
GRASS_M = get_part(119, 29, 16, 13)
GRASS_R = get_part(136, 29, 16, 13)
GRASS_RAISE = 6            # how many pixels the grass sticks up above the rock

# ---------- Level map (one long level, 160 x 12 tiles, nothing repeats) ----------
#  S = solid rock/ground     . = empty
ROWS = 12
COLS = 160                # was 64. More columns = a longer map (1 column = 32 px)
LEVEL_W = COLS * T

_grid = [["."] * COLS for _ in range(ROWS)]


def block(c0, c1, r0, r1):
    """Fill a rectangle of tiles with rock: columns c0..c1, rows r0..r1."""
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            _grid[r][c] = "S"


# --- start: the high cliff and the low ground ---
block(0, 4, 3, 11)        # tall cliff
block(5, 5, 5, 6)         # little bulge on the cliff
block(0, 6, 9, 11)        # first step
block(0, 8, 10, 11)       # low ground
# (hole: columns 9-11)
# --- middle: long ground with a hill ---
block(12, 27, 10, 11)
block(17, 20, 8, 9)       # hill
# (hole: columns 28-31)
block(32, 45, 10, 11)
block(36, 38, 6, 9)       # tall pillar
block(41, 42, 9, 9)       # small step
# (hole: columns 46-49)
# --- new: second part of the map ---
block(50, 70, 10, 11)
block(53, 54, 9, 9)       # little steps up to a plateau
block(55, 58, 8, 9)       # plateau
# (hole: columns 71-74)
block(75, 95, 10, 11)
block(80, 83, 8, 9)       # hill
block(88, 90, 6, 9)       # tall pillar
# (hole: columns 96-100)
block(101, 120, 10, 11)
block(105, 107, 9, 9)     # small step
block(110, 113, 7, 9)     # raised block
block(116, 118, 5, 9)     # tower
# (hole: columns 121-125)
# --- end: ground and stairs up to the final wall ---
block(126, 159, 10, 11)
block(144, 145, 9, 9)
block(146, 147, 7, 9)
block(148, 159, 5, 11)    # end wall

LEVEL = ["".join(r) for r in _grid]


def solid(row, col):
    """True if the tile is solid. Past the left/right end, the last column is repeated
    so the map edges look like they continue."""
    if row < 0:
        return False
    if row >= ROWS:
        return True
    col = max(0, min(COLS - 1, col))
    return LEVEL[row][col] == "S"


def pick_rock(row, col):
    up = not solid(row - 1, col)
    down = not solid(row + 1, col)
    left = not solid(row, col - 1)
    right = not solid(row, col + 1)
    if up and left:
        return ROCK["TL"]
    if up and right:
        return ROCK["TR"]
    if up:
        return ROCK["T"]
    if down and left:
        return ROCK["BL"]
    if down and right:
        return ROCK["BR"]
    if down:
        return ROCK["B"]
    if left:
        return ROCK["L"]
    if right:
        return ROCK["R"]
    return FILL[(col * 7 + row * 3) % len(FILL)]


def pick_grass(row, col):
    """Grass piece for a tile that has open air above it, else None."""
    if not solid(row, col) or solid(row - 1, col):
        return None
    left_is_top = solid(row, col - 1) and not solid(row - 1, col - 1)
    right_is_top = solid(row, col + 1) and not solid(row - 1, col + 1)
    if not left_is_top:
        return GRASS_L
    if not right_is_top:
        return GRASS_R
    return GRASS_M


def draw_level():
    cx = int(camera_x)
    first_col = cx // T
    offset = -(cx % T)
    for i in range(WIDTH // T + 2):
        col = first_col + i
        if col < 0 or col >= COLS:
            continue
        x = offset + i * T
        for row in range(ROWS):
            if solid(row, col):
                screen.blit(pick_rock(row, col), (x, row * T))
        for row in range(ROWS):
            g = pick_grass(row, col)
            if g:
                screen.blit(g, (x, row * T - GRASS_RAISE))


# ---------- Moving rocks (over the holes) ----------
def build_island(tiles_w):
    """Make a floating-rock picture, `tiles_w` tiles wide and 2 tiles tall, with grass on top."""
    surf = pygame.Surface((tiles_w * T, 2 * T + GRASS_RAISE), pygame.SRCALPHA)
    for c in range(tiles_w):
        first, last = c == 0, c == tiles_w - 1
        top = ROCK["TL"] if first else ROCK["TR"] if last else ROCK["T"]
        bottom = ROCK["BL"] if first else ROCK["BR"] if last else ROCK["B"]
        grass = GRASS_L if first else GRASS_R if last else GRASS_M
        surf.blit(top, (c * T, GRASS_RAISE))
        surf.blit(bottom, (c * T, GRASS_RAISE + T))
        surf.blit(grass, (c * T, 0))
    return surf


class MovingRock:
    """A floating rock that moves up and down. You can jump up through it and stand on top."""

    def __init__(self, x, y_high, y_low, tiles_w=3, speed=0.7):
        self.high = y_high                  # highest position (top of the rock)
        self.low = y_low                    # lowest position
        self.y = float(y_low)
        self.dir = -1                       # starts by moving up
        self.speed = speed
        self.rect = pygame.Rect(x, y_low, tiles_w * T, 2 * T)
        self.image = build_island(tiles_w)
        self.dx = 0
        self.dy = 0

    def update(self):
        self.y += self.dir * self.speed
        if self.y <= self.high:
            self.y = self.high
            self.dir = 1
        elif self.y >= self.low:
            self.y = self.low
            self.dir = -1
        new_y = int(round(self.y))
        self.dy = new_y - self.rect.y
        self.rect.y = new_y

    def draw(self):
        sx = self.rect.x - int(camera_x)
        if -self.rect.w < sx < WIDTH:
            screen.blit(self.image, (sx, self.rect.y - GRASS_RAISE))


# MovingRock(x, highest y, lowest y, width in tiles, speed)
# Each rock floats up and down over its hole.
platforms = [
    MovingRock(320, 176, 240, 3, 0.7),      # hole at columns 9-11
    MovingRock(928, 176, 240, 2, 0.8),      # hole at columns 28-31
    MovingRock(1504, 176, 240, 2, 0.9),     # hole at columns 46-49
    MovingRock(2304, 176, 240, 2, 0.8),     # hole at columns 71-74
    MovingRock(3104, 176, 240, 3, 0.9),     # hole at columns 96-100
    MovingRock(3904, 176, 240, 3, 1.0),     # hole at columns 121-125
]


# ---------- Trees ----------
# The code finds the two trees inside the tree picture by itself.
TREES = []
try:
    tree_sheet = pygame.image.load(
        find_file("Trees.png", "TilesExamples (2).png", "TilesExamples__2_.png")
    ).convert_alpha()
    found = [r for r in pygame.mask.from_surface(tree_sheet).get_bounding_rects()
             if r.w * r.h >= 200]
    found.sort(key=lambda r: r.x)                    # left to right
    print("Trees found (x, y, w, h):", [tuple(r) for r in found])

    def cut_tree(r):
        img = tree_sheet.subsurface(r)
        return pygame.transform.scale(img, (r.w * SCALE, r.h * SCALE))

    tree_round = cut_tree(found[0])
    tree_tall = cut_tree(found[1])

    # (x of the trunk in the level, y of the ground it stands on, picture)
    round_flip = pygame.transform.flip(tree_round, True, False)
    tall_flip = pygame.transform.flip(tree_tall, True, False)
    TREES = [
        (125, 3 * T, tree_round),         # on the high cliff
        (235, 10 * T, tree_tall),         # on the low ground
        (470, 10 * T, round_flip),
        (800, 10 * T, tree_tall),
        (1030, 10 * T, tall_flip),
        (1270, 10 * T, tree_round),
        (1650, 10 * T, round_flip),
        (1790, 10 * T, tree_tall),
    ]
    # more trees for the longer map
    _mix = [tree_tall, round_flip, tree_round, tall_flip]
    for _i, _x in enumerate([2000, 2150, 2480, 2800, 3000, 3300, 3500, 3700, 4150, 4300, 4500]):
        TREES.append((_x, 10 * T, _mix[_i % 4]))
except Exception as e:
    print("Trees not loaded:", e)


def draw_trees():
    for x, ground_y, img in TREES:
        w, h = img.get_size()
        sx = x - int(camera_x)
        if -w < sx < WIDTH + w:
            screen.blit(img, (sx - w // 2, ground_y + 4 - h))


# ---------- Character ----------
CHAR_SCALE = SCALE          # character drawn 2x bigger, same as the level. Change to resize.
FRAME_W = 96                # width of ONE picture inside the sprite strips
FACES_RIGHT = True          # set to False if your sprites are drawn facing left
FEET_SINK = 4               # pixels the feet sink into the grass

WALK_SPEED = 3
RUN_SPEED = 4
GRAVITY = 0.6
JUMP_SPEED = -9.5          # jump strength: -12.5 was the old (higher) jump, -10 is lower still
MAX_FALL = 14
MAX_JUMPS = 2               # 2 = double jump
MAX_HP = 100
HEAL_NECRO = 25             # HP you get back for killing a necromancer


def load_frames(filename):
    """Load a sprite strip and cut it into frames of FRAME_W pixels wide."""
    img = pygame.image.load(find_file(filename)).convert_alpha()
    fh = img.get_height()
    n = max(1, img.get_width() // FRAME_W)
    print(f"{filename}: {n} frames of {FRAME_W}x{fh}")
    return [img.subsurface((i * FRAME_W, 0, FRAME_W, fh)).copy() for i in range(n)]


raw = {}
for key, fname in {
    "idle": "IDLE.png", "walk": "WALK.png", "run": "RUN.png", "jump": "JUMP.png",
    "attack1": "ATTACK 1.png", "attack2": "ATTACK 2.png", "attack3": "ATTACK 3.png",
    "defend": "DEFEND.png", "death": "DEATH.png", "hurt": "HURT.png",
}.items():
    try:
        raw[key] = load_frames(fname)
    except Exception as e:
        print("Could not load", fname, "-", e)

# Work out the body size from the idle pictures (used for the hitbox and feet position).
idle_box = raw["idle"][0].get_bounding_rect()
for f in raw["idle"]:
    idle_box = idle_box.union(f.get_bounding_rect())
print("character body (in the picture):", tuple(idle_box), " scale:", CHAR_SCALE)

ANIM_FPS = {"idle": 8, "walk": 10, "run": 14, "jump": 10,
            "attack1": 14, "attack2": 14, "attack3": 14, "defend": 12, "death": 10, "hurt": 12}
anims = {}
for key, frames in raw.items():
    fh = frames[0].get_height()
    scaled = [pygame.transform.scale(f, (int(f.get_width() * CHAR_SCALE), int(fh * CHAR_SCALE)))
              for f in frames]
    if fh == raw["idle"][0].get_height():          # same canvas as idle: reuse its feet position
        ax, ay = idle_box.centerx, idle_box.bottom
    else:                                          # different canvas: bottom centre
        ax, ay = frames[0].get_width() / 2, fh
    anims[key] = {"right": scaled,
                  "left": [pygame.transform.flip(f, True, False) for f in scaled],
                  "ax": ax * CHAR_SCALE, "ay": ay * CHAR_SCALE,
                  "w": scaled[0].get_width(), "fps": ANIM_FPS[key]}
    if not FACES_RIGHT:
        anims[key]["right"], anims[key]["left"] = anims[key]["left"], anims[key]["right"]
        anims[key]["ax"] = anims[key]["w"] - anims[key]["ax"]


def solid_phys(row, col):
    """Solid tiles for collision. Above the map is open air, below it is a bottomless gap."""
    if col < 0 or col >= COLS:
        return True                       # invisible wall at the ends of the level
    if row < 0 or row >= ROWS:
        return False
    return LEVEL[row][col] == "S"


def collides(rect):
    for row in range(rect.top // T, (rect.bottom - 1) // T + 1):
        for col in range(rect.left // T, (rect.right - 1) // T + 1):
            if solid_phys(row, col):
                return True
    return False


class Player:
    def __init__(self):
        w = int(idle_box.w * CHAR_SCALE * 0.7)
        h = int(idle_box.h * CHAR_SCALE)
        self.rect = pygame.Rect(0, 0, w, h)
        self.attack_id = 0
        self.spawn()

    def spawn(self):
        self.rect.midbottom = (80, 3 * T)         # top of the high cliff
        self.vx = 0
        self.vy = 0.0
        self.ry = 0.0
        self.on_ground = False
        self.jumps_used = 0
        self.facing = "right"
        self.state = "idle"
        self.frame_time = 0.0
        self.attack_n = 0
        self.attacking = False
        self.dead = False
        self.standing_on = None
        self.hp = MAX_HP
        self.hurting = False
        self.invincible = 0
        self.heal_flash = 0
        self.game_over = False                    # True = show the GAME OVER screen

    def take_damage(self, amount):
        """Lose HP. Holding the shield (K) halves the damage."""
        if self.dead or self.invincible > 0:
            return
        if self.state == "defend":
            amount = max(1, amount // 2)
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self.die()
            return
        self.invincible = 60                      # about 1 second of protection
        self.attacking = False
        if "hurt" in anims:
            self.hurting = True
            self.state = "hurt"
            self.frame_time = 0.0

    def heal(self, amount):
        """Get HP back (never above MAX_HP). Shows a green +HP number and a green glow."""
        if self.dead:
            return
        gained = min(amount, MAX_HP - self.hp)
        if gained <= 0:
            return
        self.hp += gained
        self.heal_flash = 40
        effects.append(FloatText(self.rect.centerx, self.rect.top - 12, f"+{gained} HP", (110, 255, 130)))

    def die(self):
        self.hp = 0
        self.hurting = False
        self.dead = True
        self.attacking = False
        self.vx = 0
        self.vy = 0.0
        self.ry = 0.0
        self.standing_on = None
        self.rect.bottom = ROWS * T - 2          # lies at the bottom of the hole
        self.state = "death" if "death" in anims else "idle"
        self.frame_time = 0.0

    def hits_platform_top(self):
        for p in platforms:
            if (self.rect.right > p.rect.left and self.rect.left < p.rect.right
                    and self.rect.bottom - 1 == p.rect.top):
                return True
        return False

    def platform_below(self):
        """The rock under our feet (if any). If a rising rock pushed up into our feet a little,
        we get lifted onto its top."""
        for p in platforms:
            if self.rect.right > p.rect.left and self.rect.left < p.rect.right:
                sunk = self.rect.bottom - p.rect.top
                if sunk == 0 or (0 < sunk <= 3 and self.vy >= 0):
                    self.rect.bottom = p.rect.top
                    return p
        return None

    def carry(self, dx, dy=0):
        """Move with the rock we are standing on."""
        if dx:
            step = 1 if dx > 0 else -1
            for _ in range(abs(dx)):
                self.rect.x += step
                if collides(self.rect):
                    self.rect.x -= step
                    break
        if dy:
            step = 1 if dy > 0 else -1
            for _ in range(abs(dy)):
                self.rect.y += step
                if collides(self.rect):
                    self.rect.y -= step
                    break

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.frame_time = 0.0

    def start_attack(self):
        if self.dead or self.hurting or self.attacking or "attack1" not in anims:
            return
        self.attack_n = self.attack_n % 3 + 1
        name = f"attack{self.attack_n}"
        if name not in anims:
            self.attack_n = 1
            name = "attack1"
        self.attacking = True
        self.attack_id += 1
        self.state = name
        self.frame_time = 0.0

    def attack_rect(self):
        """The area the sword hits, only during the middle of an attack. None otherwise."""
        if not self.attacking or self.dead or self.state not in anims:
            return None
        a = anims[self.state]
        n = len(a["right"])
        i = int(self.frame_time * a["fps"])
        if not (n * 0.3 <= i <= n * 0.85):
            return None
        reach = 74
        if self.facing == "right":
            return pygame.Rect(self.rect.centerx, self.rect.top - 8, reach, self.rect.h + 16)
        return pygame.Rect(self.rect.centerx - reach, self.rect.top - 8, reach, self.rect.h + 16)

    def try_jump(self):
        """Called once each time the jump key is pressed (so holding it does not double jump)."""
        defending = self.state == "defend"
        if self.dead or (self.attacking and self.on_ground) or defending:
            return
        if self.on_ground:
            self.jumps_used = 0
        elif self.jumps_used == 0:
            self.jumps_used = 1                  # walked off a ledge: counts as the first jump
        if self.jumps_used < MAX_JUMPS:
            self.vy = JUMP_SPEED
            self.on_ground = False
            self.jumps_used += 1

    def update(self, keys):
        if self.dead:                                   # play the death animation, then GAME OVER
            n = len(anims["death"]["right"]) if "death" in anims else 1
            if self.frame_time > n / ANIM_FPS.get("death", 10) + 0.8:
                self.game_over = True                   # now wait for the Restart button
            return

        if self.heal_flash > 0:
            self.heal_flash -= 1

        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        run = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        defend = keys[pygame.K_k] and self.on_ground and "defend" in anims

        # --- horizontal input ---
        self.vx = 0
        if self.invincible > 0:
            self.invincible -= 1
        if (not self.attacking or not self.on_ground) and not defend and not self.hurting:
            speed = RUN_SPEED if run else WALK_SPEED
            if left and not right:
                self.vx = -speed
                self.facing = "left"
            elif right and not left:
                self.vx = speed
                self.facing = "right"

        # --- move X (1 pixel at a time so we never go through walls) ---
        step = 1 if self.vx > 0 else -1
        for _ in range(abs(self.vx)):
            self.rect.x += step
            if collides(self.rect):
                self.rect.x -= step
                break

        # --- gravity + move Y ---
        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        self.ry += self.vy
        dy = int(self.ry)
        self.ry -= dy
        step = 1 if dy > 0 else -1
        for _ in range(abs(dy)):
            self.rect.y += step
            if collides(self.rect) or (step > 0 and self.hits_platform_top()):
                self.rect.y -= step
                self.vy = 0
                self.ry = 0
                break
        self.rect.y += 1
        tile_ground = collides(self.rect)
        self.rect.y -= 1
        rock = self.platform_below()
        self.standing_on = rock if self.vy >= 0 else None
        self.on_ground = (tile_ground or rock is not None) and self.vy >= 0
        if self.on_ground:
            self.jumps_used = 0

        # fell into a hole -> die
        if self.rect.bottom >= ROWS * T - 4:
            self.die()
            return

        # --- choose animation ---
        if self.attacking or self.hurting:
            pass                                        # keeps playing until it ends
        elif not self.on_ground:
            self.set_state("jump")
        elif defend:
            self.set_state("defend")
        elif self.vx != 0:
            self.set_state("run" if run and "run" in anims else "walk")
        else:
            self.set_state("idle")

        if self.state not in anims:
            self.state = "idle"

    def frame_index(self):
        a = anims[self.state]
        n = len(a["right"])
        if self.state == "jump":                        # early frames going up, late ones falling
            p = (self.vy - JUMP_SPEED) / (MAX_FALL - JUMP_SPEED)
            return max(0, min(n - 1, int(p * n)))
        i = int(self.frame_time * a["fps"])
        if self.state.startswith("attack"):
            if i >= n:
                self.attacking = False
                self.set_state("idle")
                return 0
            return i
        if self.state == "hurt":
            if i >= n:
                self.hurting = False
                self.set_state("idle")
                return 0
            return i
        if self.state in ("defend", "death"):
            return min(i, n - 1)                        # hold the last frame
        return i % n

    def draw(self):
        self.frame_time += 1 / 60
        a = anims[self.state]
        i = self.frame_index()
        a = anims[self.state]
        img = a[self.facing][min(i, len(a[self.facing]) - 1)]
        ax = a["ax"] if self.facing == "right" else a["w"] - a["ax"]
        x = self.rect.centerx - int(camera_x) - ax
        y = self.rect.bottom - a["ay"] + FEET_SINK
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0 and not self.dead:
            return                                      # blink while protected
        if self.heal_flash > 0 and (self.heal_flash // 3) % 2 == 0:
            img = img.copy()                            # green glow while healing
            img.fill((0, 80, 25, 0), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(img, (x, y))


player = Player()


# ---------- Enemies ----------
enemies = []
effects = []
killed = set()      # enemies you defeated: they never come back, even after you die


def _scaled(f):
    return pygame.transform.scale(f, (f.get_width() * SCALE, f.get_height() * SCALE))


def _flash(f):
    g = f.copy()
    g.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGB_ADD)
    return g


class FloatText:
    """A number that floats up and fades away (like +10 HP)."""

    def __init__(self, x, y, text, colour):
        self.x, self.y = x, float(y)
        self.text = text
        self.colour = colour
        self.t = 0
        self.done = False

    def update(self, p):
        self.t += 1
        self.y -= 0.7
        if self.t > 55:
            self.done = True

    def draw(self):
        alpha = max(0, 255 - int(255 * max(0, self.t - 25) / 30))
        for colour, off in (((20, 10, 20), 1), (self.colour, 0)):
            img = hud_font.render(self.text, True, colour)
            img.set_alpha(alpha)
            screen.blit(img, (int(self.x) - int(camera_x) - img.get_width() // 2 + off,
                              int(self.y) + off))


# ---------- Enemy: the Necromancer ----------
# He keeps his distance and casts spells:
#   - a red fireball that flies at you
#   - a "curse": a red circle appears under your feet, then a beam of dark fire erupts there
necro_ok = False
NECRO_FW, NECRO_FH = 160, 128                          # size of ONE picture in the sheet
NECRO_ROWS = {                                          # row number in the sheet, number of pictures
    "idle": (0, 8), "walk": (1, 8), "blast": (2, 13),
    "orb": (4, 17), "hurt": (5, 5), "death": (6, 9),
}
NECRO_FACES_LEFT = True                                 # the pictures face left; set False if wrong

NECRO_HP = 6
NECRO_SPEED = 1.2
NECRO_RANGE_X = 600                 # he notices you from this far away
NECRO_RANGE_Y = 280
NECRO_TOO_CLOSE = 140               # closer than this: he backs away
NECRO_ORB_DAMAGE = 18
NECRO_BLAST_DAMAGE = 25
NECRO_ORB_COOLDOWN = 140            # frames (60 frames = 1 second)
NECRO_BLAST_COOLDOWN = 240


def find_necromancer_sheet():
    for root, dirs, files in os.walk(BASE):
        for f in files:
            if "necromancer" in f.lower() and f.lower().endswith(".png"):
                return os.path.join(root, f)
    return None


necro = {}
try:
    _path = find_necromancer_sheet()
    if not _path:
        raise FileNotFoundError("Necromancer_creativekind-Sheet.png (put it in the assets folder)")
    _sheet = pygame.image.load(_path).convert_alpha()
    for _name, (_row, _n) in NECRO_ROWS.items():
        _raw = [_sheet.subsurface((c * NECRO_FW, _row * NECRO_FH, NECRO_FW, NECRO_FH)).copy()
                for c in range(_n)]
        _base = [_scaled(f) for f in _raw]
        _flip = [pygame.transform.flip(f, True, False) for f in _base]
        _left, _right = (_base, _flip) if NECRO_FACES_LEFT else (_flip, _base)
        necro[_name] = {"raw": _raw, "left": _left, "right": _right,
                        "flash_left": [_flash(f) for f in _left],
                        "flash_right": [_flash(f) for f in _right]}
    necro_box = necro["idle"]["raw"][0].get_bounding_rect()
    for f in necro["idle"]["raw"]:
        necro_box = necro_box.union(f.get_bounding_rect())
    NECRO_AX = necro_box.centerx * SCALE
    NECRO_AY = necro_box.bottom * SCALE
    NECRO_PW = necro["idle"]["right"][0].get_width()
    necro_ok = True
    print("Necromancer loaded from", os.path.basename(_path))
except Exception as e:
    print("Necromancer not loaded:", e)


class Fireball:
    """The red fireball the necromancer throws."""

    def __init__(self, x, y, vx, vy):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.age = 0
        self.trail = []
        self.done = False
        self.rect = pygame.Rect(0, 0, 22, 22)

    def update(self, p):
        self.age += 1
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if collides(self.rect) or self.age > 160:
            self.done = True
        elif not p.dead and self.rect.colliderect(p.rect):
            p.take_damage(NECRO_ORB_DAMAGE)
            self.done = True

    def draw(self):
        cam = int(camera_x)
        for i, (tx, ty) in enumerate(self.trail):                 # fading tail
            r = 3 + i
            pygame.draw.circle(screen, (110, 10, 25), (int(tx) - cam, int(ty)), r)
        flick = 2 if (self.age // 3) % 2 else 0
        cx, cy = int(self.x) - cam, int(self.y)
        pygame.draw.circle(screen, (120, 10, 25), (cx, cy), 14 + flick)
        pygame.draw.circle(screen, (220, 40, 45), (cx, cy), 10)
        pygame.draw.circle(screen, (255, 150, 100), (cx, cy), 5)


class CurseBlast:
    """A red circle on the ground (a warning!), then a beam of dark fire. Move or jump away."""

    def __init__(self, x, ground_y, delay=36):
        self.x, self.ground_y = x, ground_y
        self.delay = delay
        self.t = 0
        self.done = False
        self.hurt_done = False

    def update(self, p):
        self.t += 1
        if self.t == self.delay and not self.hurt_done:
            self.hurt_done = True
            in_column = abs(p.rect.centerx - self.x) < 46
            low_enough = p.rect.bottom >= self.ground_y - 100       # a high jump goes over it
            if not p.dead and in_column and low_enough:
                p.take_damage(NECRO_BLAST_DAMAGE)
        if self.t > self.delay + 16:
            self.done = True

    def draw(self):
        sx = int(self.x) - int(camera_x)
        gy = self.ground_y
        layer = pygame.Surface((160, 260), pygame.SRCALPHA)
        ox, oy = 80, 250                                         # where the ground point is on the layer
        if self.t < self.delay:                                  # warning circle grows and blinks
            k = self.t / self.delay
            w = int(30 + 62 * k)
            alpha = 90 + (70 if (self.t // 4) % 2 else 0)
            pygame.draw.ellipse(layer, (230, 30, 45, alpha), (ox - w // 2, oy - 8, w, 16))
            pygame.draw.ellipse(layer, (255, 120, 120, 200), (ox - w // 2, oy - 8, w, 16), 2)
        else:                                                    # the beam
            k = (self.t - self.delay) / 16
            w = int(70 * (1 - k)) + 8
            alpha = int(230 * (1 - k)) + 20
            pygame.draw.rect(layer, (150, 10, 30, alpha), (ox - w // 2, oy - 240, w, 240))
            pygame.draw.rect(layer, (255, 90, 90, alpha), (ox - w // 4, oy - 240, w // 2, 240))
            pygame.draw.ellipse(layer, (255, 60, 70, alpha), (ox - 46, oy - 10, 92, 20))
        screen.blit(layer, (sx - ox, gy - oy))


class Necromancer:
    def __init__(self, x, spot_id=None):
        self.spot_id = spot_id
        w = int(28 * SCALE)
        h = int((necro_box.bottom - 63) * SCALE)               # body only (not the staff)
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.midbottom = (x, 40)                          # starts in the air and drops down
        self.vy = 0.0
        self.ry = 0.0
        self.rx = 0.0
        self.hp = NECRO_HP
        self.facing = "right"
        self.state = "idle"        # idle, walk, orb, blast, hurt, dying
        self.t = 0
        self.cool_orb = 80
        self.cool_blast = 150
        self.acted = False
        self.flash = 0
        self.kv = 0.0
        self.hit_id = -1
        self.dead = False

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.t = 0
            self.acted = False

    def hurt(self, from_x, attack_id):
        if self.state == "dying":
            return
        self.hit_id = attack_id
        self.hp -= 1
        self.flash = 14
        self.kv = 3.0 if self.rect.centerx > from_x else -3.0
        if self.hp <= 0:
            killed.add(self.spot_id)                  # stays dead for good
            player.heal(HEAL_NECRO)                   # killing gives HP back
            self.set_state("dying")
        else:
            self.set_state("hurt")
            self.cool_orb = max(self.cool_orb, 40)
            self.cool_blast = max(self.cool_blast, 60)

    def ground_ahead(self, d):
        x = self.rect.centerx + d * (self.rect.w // 2 + 10)
        y = self.rect.bottom + 6
        return solid_phys(y // T, x // T)

    def move_x(self, pixels):
        step = 1 if pixels > 0 else -1
        for _ in range(abs(pixels)):
            self.rect.x += step
            if collides(self.rect):
                self.rect.x -= step
                return False
        return True

    def ground_under(self, x, from_y):
        """Y of the top of the ground below a point (None if there is a hole)."""
        for row in range(max(0, from_y // T), ROWS):
            if solid_phys(row, x // T):
                return row * T
        return None

    def update(self, p):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1

        if abs(self.kv) >= 1:                                   # knock-back
            self.move_x(int(self.kv))
            self.kv *= 0.8
        else:
            self.kv = 0

        self.vy = min(self.vy + GRAVITY, MAX_FALL)              # gravity
        self.ry += self.vy
        dy = int(self.ry)
        self.ry -= dy
        step = 1 if dy > 0 else -1
        for _ in range(abs(dy)):
            self.rect.y += step
            if collides(self.rect):
                self.rect.y -= step
                self.vy = 0
                self.ry = 0
                break
        if self.rect.top > ROWS * T + 200:
            self.dead = True
            return

        if self.state == "dying":                               # death animation, then gone
            if self.t > len(necro["death"]["right"]) * 7 + 40:
                self.dead = True
            return
        if self.state == "hurt":
            if self.t // 4 >= len(necro["hurt"]["right"]):
                self.set_state("idle")
            return

        dx = p.rect.centerx - self.rect.centerx
        dyp = p.rect.centery - self.rect.centery
        adx = abs(dx)
        self.cool_orb -= 1
        self.cool_blast -= 1
        aggro = (not p.dead) and adx < NECRO_RANGE_X and abs(dyp) < NECRO_RANGE_Y
        toward = 1 if dx > 0 else -1

        if self.state in ("idle", "walk"):
            if not aggro:
                self.set_state("idle")
                return
            self.facing = "right" if dx > 0 else "left"
            if adx < NECRO_TOO_CLOSE:                           # too close: back away (or fight if cornered)
                away = -toward
                if self.ground_ahead(away):
                    self.set_state("walk")
                    self.rx += away * NECRO_SPEED
                    whole = int(self.rx)
                    self.rx -= whole
                    if not self.move_x(whole) and self.cool_blast <= 0:
                        self.set_state("blast")
                elif self.cool_blast <= 0:
                    self.set_state("blast")
                else:
                    self.set_state("idle")
            elif self.cool_blast <= 0 and adx < 460:
                self.set_state("blast")
            elif self.cool_orb <= 0:
                self.set_state("orb")
            elif adx > 380 and self.ground_ahead(toward):       # too far: come closer
                self.set_state("walk")
                self.rx += toward * NECRO_SPEED
                whole = int(self.rx)
                self.rx -= whole
                self.move_x(whole)
            else:
                self.set_state("idle")

        elif self.state == "orb":                               # fireball
            idx = self.t // 5
            if idx >= 11 and not self.acted:
                self.acted = True
                d = 1 if self.facing == "right" else -1
                x0 = self.rect.centerx + d * 34
                y0 = self.rect.top + 24
                speed = 5.0
                flight = max(1.0, abs(p.rect.centerx - x0) / speed)
                vy = max(-2.5, min(2.5, (p.rect.centery - y0) / flight))
                effects.append(Fireball(x0, y0, d * speed, vy))
            if idx >= len(necro["orb"]["right"]):
                self.cool_orb = NECRO_ORB_COOLDOWN
                self.set_state("idle")

        elif self.state == "blast":                             # curse under the player's feet
            idx = self.t // 6
            if idx >= 2 and not self.acted:
                self.acted = True
                gy = self.ground_under(p.rect.centerx, (p.rect.bottom - 8))
                if gy is not None:
                    effects.append(CurseBlast(p.rect.centerx, gy))
            if idx >= len(necro["blast"]["right"]):
                self.cool_blast = NECRO_BLAST_COOLDOWN
                self.set_state("idle")

    def current_picture(self):
        if self.state == "walk":
            a, i = necro["walk"], self.t // 6
        elif self.state == "orb":
            a, i = necro["orb"], self.t // 5
        elif self.state == "blast":
            a, i = necro["blast"], self.t // 6
        elif self.state == "hurt":
            a, i = necro["hurt"], self.t // 4
        elif self.state == "dying":
            a, i = necro["death"], self.t // 7
        else:
            a, i = necro["idle"], self.t // 8
        n = len(a["right"])
        i = min(i, n - 1) if self.state in ("orb", "blast", "hurt", "dying") else i % n
        flashing = self.flash > 0 and (self.flash // 2) % 2 == 0
        return a["flash_" + self.facing if flashing else self.facing][i]

    def draw(self):
        img = self.current_picture()
        ax = NECRO_AX if self.facing == "right" else NECRO_PW - NECRO_AX
        if NECRO_FACES_LEFT:                                    # (a mirrored picture mirrors the anchor)
            ax = NECRO_PW - NECRO_AX if self.facing == "right" else NECRO_AX
        sx = self.rect.centerx - int(camera_x)
        if -300 < sx < WIDTH + 300:
            screen.blit(img, (sx - ax, self.rect.bottom - NECRO_AY + FEET_SINK))
            if self.state != "dying":                           # HP bar above the head
                bw = 56
                bx, by = sx - bw // 2, self.rect.top - 26
                pygame.draw.rect(screen, (30, 20, 30), (bx - 2, by - 2, bw + 4, 9))
                pygame.draw.rect(screen, (95, 25, 35), (bx, by, bw, 5))
                pygame.draw.rect(screen, (170, 60, 220),
                                 (bx, by, int(bw * max(0, self.hp) / NECRO_HP), 5))


# x position of each necromancer (they drop onto the ground)
NECRO_SPOTS = [840, 1280, 1950, 2450, 2740, 3300, 4300]     # 7 necromancers (add or remove numbers)


def reset_enemies():
    enemies.clear()
    effects.clear()
    if necro_ok:
        for i, x in enumerate(NECRO_SPOTS):
            if ("necro", i) not in killed:            # defeated necromancers do not come back
                enemies.append(Necromancer(x, ("necro", i)))


reset_enemies()


# ---------- HP bar ----------
hud_font = pygame.font.SysFont(None, 22)


def draw_hud():
    x, y, w, h = 14, 14, 170, 16
    ratio = max(0, player.hp) / MAX_HP
    pygame.draw.rect(screen, (30, 20, 30), (x - 4, y - 4, w + 8, h + 8), border_radius=5)
    pygame.draw.rect(screen, (95, 25, 35), (x, y, w, h), border_radius=3)
    if ratio > 0:
        colour = (90, 200, 90) if ratio > 0.6 else (230, 190, 60) if ratio > 0.3 else (220, 55, 60)
        pygame.draw.rect(screen, colour, (x, y, int(w * ratio), h), border_radius=3)
    pygame.draw.rect(screen, (240, 230, 220), (x - 4, y - 4, w + 8, h + 8), 2, border_radius=5)
    label = hud_font.render(f"HP {player.hp}/{MAX_HP}", True, (255, 255, 255))
    shadow = hud_font.render(f"HP {player.hp}/{MAX_HP}", True, (20, 10, 20))
    pos = (x + w // 2 - label.get_width() // 2, y + h // 2 - label.get_height() // 2)
    screen.blit(shadow, (pos[0] + 1, pos[1] + 1))
    screen.blit(label, pos)

    if necro_ok:                                        # how many enemies are left
        total = len(NECRO_SPOTS)
        left = sum(1 for e in enemies if e.state != "dying")
        text = "All enemies defeated!" if left == 0 else f"Enemies left: {left}/{total}"
        shadow = hud_font.render(text, True, (20, 10, 20))
        label = hud_font.render(text, True, (255, 240, 200))
        screen.blit(shadow, (x + 1, y + 31))
        screen.blit(label, (x, y + 30))


# ---------- Game over screen ----------
FULL_RESET_ON_RESTART = False   # False: enemies you killed stay dead. True: they all come back.
big_font = pygame.font.SysFont(None, 84)
btn_font = pygame.font.SysFont(None, 38)
RESTART_BTN = pygame.Rect(0, 0, 210, 54)
RESTART_BTN.center = (WIDTH // 2, HEIGHT // 2 + 55)
dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
dim.fill((10, 0, 10, 170))


def draw_game_over():
    screen.blit(dim, (0, 0))
    title = big_font.render("GAME OVER", True, (230, 60, 70))
    shadow = big_font.render("GAME OVER", True, (20, 5, 15))
    tx, ty = WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 85
    screen.blit(shadow, (tx + 3, ty + 3))
    screen.blit(title, (tx, ty))

    hover = RESTART_BTN.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(screen, (200, 70, 70) if hover else (150, 40, 50), RESTART_BTN, border_radius=10)
    pygame.draw.rect(screen, (245, 235, 225), RESTART_BTN, 3, border_radius=10)
    label = btn_font.render("Restart", True, (255, 255, 255))
    screen.blit(label, (RESTART_BTN.centerx - label.get_width() // 2,
                        RESTART_BTN.centery - label.get_height() // 2))
    hint = hud_font.render("or press R / Enter", True, (230, 220, 210))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, RESTART_BTN.bottom + 10))


def restart_game():
    global camera_x, was_dead
    if FULL_RESET_ON_RESTART:
        killed.clear()
    player.spawn()
    reset_enemies()
    was_dead = False
    camera_x = max(0, min(LEVEL_W - WIDTH, player.rect.centerx - WIDTH // 2))


# ---------- Game state ----------
camera_x = 0.0
was_dead = False

running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if player.game_over:
                if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                    restart_game()
            elif event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                player.try_jump()
            elif event.key == pygame.K_j:
                player.start_attack()
            elif event.key == pygame.K_h:
                player.take_damage(10)               # test key: lose 10 HP (delete this later)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if player.game_over:
                if RESTART_BTN.collidepoint(event.pos):
                    restart_game()
            else:
                player.start_attack()                # left mouse click

    for rock in platforms:
        rock.update()
        if player.standing_on is rock and not player.dead:
            player.carry(rock.dx, rock.dy)                    # ride along with the rock

    player.update(pygame.key.get_pressed())

    # enemies and their spells
    for e in enemies:
        e.update(player)
    swing = player.attack_rect()
    if swing:
        for e in enemies:
            if (e.state != "dying" and e.hit_id != player.attack_id
                    and swing.colliderect(e.rect)):
                e.hurt(player.rect.centerx, player.attack_id)
    for fx in effects:
        fx.update(player)
    enemies[:] = [e for e in enemies if not e.dead]
    effects[:] = [fx for fx in effects if not fx.done]

    if player.dead:
        was_dead = True

    # camera follows the player smoothly
    camera_x += (player.rect.centerx - WIDTH // 2 - camera_x) * 0.12
    camera_x = max(0, min(LEVEL_W - WIDTH, camera_x))

    screen.fill((0, 0, 0))

    # draw back to front
    draw_layer(clouds_back, 0.05)
    draw_layer(clouds_front, 0.15)
    draw_layer(bg_back, 0.3)
    draw_layer(bg_front, 0.5)
    draw_trees()          # behind the ground so the trunk base is hidden by grass
    draw_level()
    for rock in platforms:
        rock.draw()
    for e in enemies:
        e.draw()
    player.draw()
    for fx in effects:
        fx.draw()
    draw_hud()
    if player.game_over:
        draw_game_over()

    pygame.display.flip()

pygame.quit()