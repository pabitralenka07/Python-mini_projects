"""11. Snake Game - Tkinter canvas. Arrows/WASD to move, P pause, R restart."""
import os
import random
import tkinter as tk

from common import DATA_DIR, launch

CELL, COLS, ROWS = 25, 24, 20
DIRS = {"Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0),
        "w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
HS_FILE = os.path.join(DATA_DIR, "snake_highscore.txt")


class SnakeModel:
    """Pure game logic (no GUI) so it can be tested."""

    def __init__(self, cols=COLS, rows=ROWS, rng=None):
        self.cols, self.rows, self.rng = cols, rows, rng or random.Random()
        self.reset()

    def reset(self):
        cx, cy = self.cols // 2, self.rows // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = self.pending = (1, 0)
        self.score, self.alive = 0, True
        self.food = self._place_food()

    def _place_food(self):
        taken = set(self.snake)
        free = [(x, y) for x in range(self.cols) for y in range(self.rows) if (x, y) not in taken]
        return self.rng.choice(free) if free else None

    def turn(self, d):
        if (d[0] + self.direction[0], d[1] + self.direction[1]) != (0, 0):
            self.pending = d

    def step(self):
        if not self.alive:
            return
        self.direction = self.pending
        nx, ny = self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1]
        eating = (nx, ny) == self.food
        body = self.snake if eating else self.snake[:-1]
        if not (0 <= nx < self.cols and 0 <= ny < self.rows) or (nx, ny) in body:
            self.alive = False
            return
        self.snake.insert(0, (nx, ny))
        if eating:
            self.score += 10
            self.food = self._place_food()
            if self.food is None:
                self.alive = False
        else:
            self.snake.pop()


class App:
    def __init__(self, root):
        self.root = root
        self.model = SnakeModel()
        self.paused = False
        self.best = self._load_best()
        self.label = tk.Label(root, font=("Consolas", 13))
        self.label.pack()
        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL, bg="#111")
        self.canvas.pack()
        root.bind("<Key>", self.on_key)
        root.focus_set()
        self.loop()

    def _load_best(self):
        try:
            with open(HS_FILE) as fh:
                return int(fh.read().strip())
        except (OSError, ValueError):
            return 0

    def _save_best(self):
        try:
            with open(HS_FILE, "w") as fh:
                fh.write(str(self.best))
        except OSError:
            pass

    def on_key(self, e):
        k = e.keysym if e.keysym in DIRS else e.keysym.lower()
        if k in DIRS:
            self.model.turn(DIRS[k])
        elif k == "p":
            self.paused = not self.paused
        elif k == "r":
            self.model.reset()
            self.paused = False

    def loop(self):
        if not self.paused:
            self.model.step()
        if self.model.score > self.best:
            self.best = self.model.score
            self._save_best()
        self.draw()
        self.root.after(max(60, 140 - self.model.score // 5), self.loop)

    def draw(self):
        c, m = self.canvas, self.model
        c.delete("all")
        if m.food:
            x, y = m.food
            c.create_oval(x * CELL + 3, y * CELL + 3, (x + 1) * CELL - 3, (y + 1) * CELL - 3, fill="#e53935", outline="")
        for i, (x, y) in enumerate(m.snake):
            c.create_rectangle(x * CELL + 1, y * CELL + 1, (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                               fill="#66bb6a" if i else "#c6ff00", outline="")
        self.label.config(text=f"Score {m.score}   Best {self.best}" + ("   [PAUSED]" if self.paused else ""))
        if not m.alive:
            c.create_text(COLS * CELL // 2, ROWS * CELL // 2, fill="white", font=("Consolas", 22, "bold"),
                          text="GAME OVER\nPress R to restart")


if __name__ == "__main__":
    launch(App, "Snake", f"{COLS * CELL + 20}x{ROWS * CELL + 50}")
