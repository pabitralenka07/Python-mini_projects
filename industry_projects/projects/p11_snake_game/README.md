# Project 11: Classic Snake Game

A modular, arcade-quality Snake Game demonstrating clean game architecture: complete separation of pure game engine logic (`core.py`) from graphical rendering (`ui.py`), allowing 100% automated headless unit testing without requiring an active display or window manager.

---

## 1. Architecture & Design

The project separates game state simulation from presentation:

- **`models.py`**: Immutable `Direction` enum and `Point` coordinate representation, plus the mutable `GameState` model.
- **`storage.py`**: Atomic JSON persistence for persistent high-score tracking using atomic file replacement (`os.replace`).
- **`core.py` (Zero Pygame Dependencies)**:
  - Manages grid bounds, snake segment lists, directional movement, and collision detection.
  - Can be driven deterministically tick-by-tick in unit tests without initializing Pygame or SDL.
  - **180-Degree Reversal Guard**: Rejects illegal opposite heading changes (e.g. attempting to press `LEFT` while moving `RIGHT`).
  - **Collision Physics**: Detects wall boundaries and self-body intersections.
  - **Food Consumption**: Grows snake length and spawns food on unoccupied cells.
- **`ui.py`**: Lazy-loaded Pygame presentation layer rendering grid lines, snake segments, food pellets, live HUD banners, and pause/game-over overlays.

---

## 2. Coordinate System & Kinematics

The game operates on a discrete 2D grid of size `W x H` (default `20 x 20`):

```text
(0, 0) -------------------------> +X (Width)
  |      [ . ]  [ . ]  [ . ]  [ . ]
  |      [ . ]  [ * ]  [ # ]  [ H ]  -> Snake moving RIGHT (H = Head)
  |      [ . ]  [ . ]  [ . ]  [ . ]
  v      [ . ]  [ F ]  [ . ]  [ . ]  -> Food item (F)
 +Y (Height)
```

- Each step tick moves the head to `(head.x + dx, head.y + dy)`.
- If food is eaten: the head advances, the tail is NOT removed, and the snake grows by 1 segment.
- If no food is eaten: the head advances and the tail segment is popped (`snake.pop()`).

---

## 3. Atomic High-Score Persistence

To prevent JSON file corruption in the event of an abrupt program exit:
1. The updated high score is written to a temporary sibling file (`highscore.tmp`).
2. Data is flushed to disk via `f.flush()` and `os.fsync()`.
3. The temporary file replaces the live high score file via `os.replace()`, an atomic operation supported by all POSIX and Windows filesystems.

---

## 4. Controls & Keybindings

| Key | Action |
| :--- | :--- |
| **Up Arrow / W** | Turn Up |
| **Down Arrow / S** | Turn Down |
| **Left Arrow / A** | Turn Left |
| **Right Arrow / D** | Turn Right |
| **Space / P** | Pause / Resume Game |
| **R** | Restart Game Session |
| **Esc** | Quit Application |

---

## 5. Running the Game & Headless Testing

### Interactive Graphical Gameplay:
```bash
.venv/bin/python -m projects.p11_snake_game
```

### Headless Automated Testing:
Unit tests test `SnakeGame` directly in pure Python without initializing graphical displays, and test Pygame loops using `headless=True` (`SDL_VIDEODRIVER=dummy`):
```bash
.venv/bin/pytest tests/test_p11_snake_game.py
```

---

## 6. Unsolved Practice Exercises

1. **Exercise 1: Progressive Difficulty (Speed Acceleration)**
   - Modify `SnakeGame` to track levels.
   - For every 50 points earned, increase game tick speed (e.g. starting at 8 FPS, ramping up to 20 FPS).
2. **Exercise 2: Obstacle Mazes / Poison Apples**
   - Add static obstacle blocks in the grid center.
   - Spawn occasional "golden apples" that offer bonus points but expire after 5 seconds.
