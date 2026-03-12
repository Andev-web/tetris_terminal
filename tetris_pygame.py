import pygame, random
from dataclasses import dataclass
from typing import List, Optional, Tuple

# -----------------------------
# Look & feel (ASCII CRT)
# -----------------------------
CELL_W = 22   # char cell width
CELL_H = 18   # char cell height
COLS, ROWS = 10, 20
HIDDEN = 2
BOARD_H = ROWS + HIDDEN

PAD_X = 40
PAD_Y = 30

FG = (120, 255, 170)     # phosphor green
DIM = (40, 120, 80)      # dim green
BG  = (5, 8, 10)         # near-black
BORDER = (90, 220, 150)  # brighter border

FPS = 60
BASE_FALL_MS = 700
MIN_FALL_MS = 90
LEVEL_LINES = 10

# ASCII blocks
EMPTY = "."
BLOCK = "[]"

# Tetromino colors (still monochrome-ish but OK)
PIECE_COL = (120, 255, 170)

SHAPES = {
    "I": ["....", "####", "....", "...."],
    "O": [".##.", ".##.", "....", "...."],
    "T": [".#..", "###.", "....", "...."],
    "S": [".##.", "##..", "....", "...."],
    "Z": ["##..", ".##.", "....", "...."],
    "J": ["#...", "###.", "....", "...."],
    "L": ["..#.", "###.", "....", "...."],
}

KICKS = [(0,0), (-1,0), (1,0), (-2,0), (2,0), (0,-1)]

def rotate(mat: List[str]) -> List[str]:
    return ["".join(mat[3-r][c] for r in range(4)) for c in range(4)]

def rotations(base: List[str]) -> List[List[str]]:
    rots = [base]
    for _ in range(3):
        rots.append(rotate(rots[-1]))
    uniq = []
    for r in rots:
        if r not in uniq:
            uniq.append(r)
    return uniq

ROT = {k: rotations(v) for k, v in SHAPES.items()}

@dataclass
class Piece:
    kind: str
    x: int
    y: int
    r: int = 0

    def cells(self):
        mat = ROT[self.kind][self.r]
        out = []
        for rr in range(4):
            for cc in range(4):
                if mat[rr][cc] == "#":
                    out.append((self.x + cc, self.y + rr))
        return out

    def rotated(self):
        n = len(ROT[self.kind])
        return Piece(self.kind, self.x, self.y, (self.r + 1) % n)

class Bag7:
    def __init__(self):
        self.bag = []
    def next(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return self.bag.pop()

class Game:
    def __init__(self):
        self.board: List[List[bool]] = [[False]*COLS for _ in range(BOARD_H)]
        self.bag = Bag7()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.paused = False
        self.over = False
        self.active = self.spawn(self.bag.next())

    def fall_ms(self):
        return max(MIN_FALL_MS, int(BASE_FALL_MS * (0.85 ** (self.level - 1))))

    def spawn(self, k):
        p = Piece(k, COLS//2 - 2, 0, 0)
        if self.collides(p):
            self.over = True
        return p

    def inb(self, x, y):
        return 0 <= x < COLS and 0 <= y < BOARD_H

    def collides(self, p: Piece):
        for x,y in p.cells():
            if not self.inb(x,y): return True
            if self.board[y][x]: return True
        return False

    def move(self, dx, dy):
        p = Piece(self.active.kind, self.active.x+dx, self.active.y+dy, self.active.r)
        if not self.collides(p):
            self.active = p
            return True
        return False

    def rotate(self):
        target = self.active.rotated()
        for kx,ky in KICKS:
            test = Piece(target.kind, target.x+kx, target.y+ky, target.r)
            if not self.collides(test):
                self.active = test
                return

    def lock(self):
        for x,y in self.active.cells():
            self.board[y][x] = True
        self.clear_lines()
        self.active = self.spawn(self.bag.next())

    def clear_lines(self):
        cleared = 0
        newb = []
        for row in self.board:
            if all(row):
                cleared += 1
            else:
                newb.append(row)
        while len(newb) < BOARD_H:
            newb.insert(0, [False]*COLS)
        self.board = newb
        if cleared:
            self.lines += cleared
            self.level = self.lines // LEVEL_LINES + 1
            add = {1:100, 2:300, 3:500, 4:800}.get(cleared, 0)
            self.score += add * self.level

    def soft_drop(self):
        if self.move(0,1):
            self.score += 1
        else:
            self.lock()

    def hard_drop(self):
        dist = 0
        while self.move(0,1):
            dist += 1
        self.score += dist * 2
        self.lock()

# -----------------------------
# Draw (ASCII)
# -----------------------------
def cell_to_px(x, y):
    # y is visible (0..ROWS-1)
    return PAD_X + x*CELL_W, PAD_Y + y*CELL_H

def main():
    pygame.init()
    pygame.display.set_caption("Tetris ASCII CRT (Pygame)")
    # Window sized around board + some HUD top
    W = PAD_X*2 + COLS*CELL_W + 120
    H = PAD_Y*2 + ROWS*CELL_H + 40
    screen = pygame.display.set_mode((W,H))
    clock = pygame.time.Clock()

    # Use a monospace-like font
    font = pygame.font.SysFont("Courier New", 18, bold=True)
    font_small = pygame.font.SysFont("Courier New", 14, bold=True)

    g = Game()
    fall_acc = 0
    last = pygame.time.get_ticks()

    left_held = right_held = False
    move_acc = 0

    def draw_text(txt, x, y, col=FG, small=False):
        f = font_small if small else font
        screen.blit(f.render(txt, True, col), (x,y))

    while True:
        now = pygame.time.get_ticks()
        dt = now - last
        last = now

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); return
                if e.key == pygame.K_p and not g.over:
                    g.paused = not g.paused
                if e.key == pygame.K_r:
                    g = Game()
                    fall_acc = 0
                    left_held = right_held = False
                    move_acc = 0
                if g.paused or g.over:
                    continue

                if e.key == pygame.K_LEFT:
                    left_held = True
                    g.move(-1,0)
                    move_acc = 0
                if e.key == pygame.K_RIGHT:
                    right_held = True
                    g.move(1,0)
                    move_acc = 0
                if e.key == pygame.K_DOWN:
                    g.soft_drop()
                if e.key == pygame.K_UP:
                    g.rotate()
                if e.key == pygame.K_SPACE:
                    g.hard_drop()

            if e.type == pygame.KEYUP:
                if e.key == pygame.K_LEFT: left_held = False
                if e.key == pygame.K_RIGHT: right_held = False

        # Update
        if not (g.paused or g.over):
            move_acc += dt
            if move_acc > 120:
                if left_held: g.move(-1,0)
                if right_held: g.move(1,0)

            fall_acc += dt
            if fall_acc >= g.fall_ms():
                fall_acc = 0
                if not g.move(0,1):
                    g.lock()

        # Draw background
        screen.fill(BG)

        # Top "scoreline" like retro: just a simple numeric row
        draw_text(f"{g.score:04d}  {g.lines:04d}  {g.level:04d}", PAD_X, 6, FG)

        # Board border like terminal brackets
        board_left = PAD_X - 26
        board_top  = PAD_Y - 6
        board_w = COLS*CELL_W + 16
        board_h = ROWS*CELL_H + 10

        # Draw side "walls" using characters to mimic <| .... |>
        # Left wall
        for y in range(ROWS):
            draw_text("<|", board_left, PAD_Y + y*CELL_H, BORDER)
            draw_text("|>", PAD_X + COLS*CELL_W + 4, PAD_Y + y*CELL_H, BORDER)

        # Draw floor
        draw_text("<=" + "="*(COLS*3) + "=>", board_left, PAD_Y + ROWS*CELL_H, BORDER, small=True)
        

        # Draw grid dots + locked blocks
        for y in range(HIDDEN, BOARD_H):
            vy = y - HIDDEN
            for x in range(COLS):
                px, py = cell_to_px(x, vy)
                if g.board[y][x]:
                    draw_text(BLOCK, px, py, PIECE_COL)
                else:
                    draw_text(EMPTY, px+6, py, DIM)  # dot a bit centered

        # Active piece
        if not g.over:
            for x,y in g.active.cells():
                if y >= HIDDEN:
                    vy = y - HIDDEN
                    px, py = cell_to_px(x, vy)
                    draw_text(BLOCK, px, py, PIECE_COL)

        # Minimal HUD
        draw_text("TETRIS", PAD_X + COLS*CELL_W + 40, PAD_Y + 20, FG)
        draw_text("P pause", PAD_X + COLS*CELL_W + 40, PAD_Y + 54, DIM, small=True)
        draw_text("R reset", PAD_X + COLS*CELL_W + 40, PAD_Y + 74, DIM, small=True)
        draw_text("ESC quit", PAD_X + COLS*CELL_W + 40, PAD_Y + 94, DIM, small=True)

        if g.paused:
            draw_text("PAUSA", PAD_X + 10, PAD_Y + 10, FG)
        if g.over:
            draw_text("GAME OVER", PAD_X + 10, PAD_Y + 10, FG)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
