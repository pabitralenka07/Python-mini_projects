"""Pure Python core game logic for Snake Game (Zero Pygame dependencies)."""

import random
from pathlib import Path

from projects.p11_snake_game.models import Direction, GameState, Point
from projects.p11_snake_game.storage import load_high_score, save_high_score


class SnakeGame:
    """Decoupled game engine managing snake kinematics, grid collisions, and score."""

    def __init__(
        self,
        grid_width: int = 20,
        grid_height: int = 20,
        rng: random.Random | None = None,
        storage_path: Path | None = None,
    ) -> None:
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.rng = rng if rng is not None else random.Random()
        self.storage_path = (
            storage_path
            if storage_path is not None
            else Path(__file__).resolve().parent / "data" / "highscore.json"
        )
        self.state: GameState = self._initialize_state()

    def _initialize_state(self) -> GameState:
        mid_x = self.grid_width // 2
        mid_y = self.grid_height // 2

        # Initial snake of 3 segments heading RIGHT
        snake = [
            Point(mid_x, mid_y),
            Point(mid_x - 1, mid_y),
            Point(mid_x - 2, mid_y),
        ]
        direction = Direction.RIGHT
        high_score = load_high_score(self.storage_path)

        # Place initial food
        empty_points = [
            Point(x, y)
            for x in range(self.grid_width)
            for y in range(self.grid_height)
            if Point(x, y) not in snake
        ]
        food = self.rng.choice(empty_points) if empty_points else Point(0, 0)

        return GameState(
            snake=snake,
            direction=direction,
            food=food,
            score=0,
            high_score=high_score,
            is_game_over=False,
            is_paused=False,
            grid_width=self.grid_width,
            grid_height=self.grid_height,
        )

    def reset(self) -> None:
        """Resets the game session while preserving or updating high score."""
        current_high = self.state.high_score
        self.state = self._initialize_state()
        self.state.high_score = max(current_high, self.state.high_score)

    def spawn_food(self) -> Point:
        """Picks a random grid point not currently occupied by the snake."""
        snake_points = set(self.state.snake)
        empty_points = [
            Point(x, y)
            for x in range(self.grid_width)
            for y in range(self.grid_height)
            if Point(x, y) not in snake_points
        ]
        if not empty_points:
            # Snake filled the entire grid (victory condition)
            return Point(-1, -1)
        return self.rng.choice(empty_points)

    def change_direction(self, new_direction: Direction) -> bool:
        """Changes heading direction, rejecting 180-degree self-reversals."""
        if self.state.is_game_over or self.state.is_paused:
            return False

        # Reject immediate 180-degree reversal
        if new_direction == self.state.direction.opposite:
            return False

        self.state.direction = new_direction
        return True

    def toggle_pause(self) -> bool:
        """Toggles pause status."""
        if self.state.is_game_over:
            return False
        self.state.is_paused = not self.state.is_paused
        return self.state.is_paused

    def step(self) -> bool:
        """Advances game world by one tick.

        Returns True if snake moved safely, False if game is paused or over.
        """
        if self.state.is_game_over or self.state.is_paused:
            return False

        head = self.state.snake[0]
        dx, dy = self.state.direction.value
        new_head = Point(head.x + dx, head.y + dy)

        # 1. Wall collision check
        if (
            new_head.x < 0
            or new_head.x >= self.grid_width
            or new_head.y < 0
            or new_head.y >= self.grid_height
        ):
            self._handle_game_over()
            return False

        # 2. Self collision check (excluding current tail since it will move, unless eating)
        # In standard Snake, hitting any current body segment except the tail that vacates is fatal
        body_to_check = self.state.snake[:-1]
        if new_head in body_to_check:
            self._handle_game_over()
            return False

        # 3. Safe movement: add new head
        self.state.snake.insert(0, new_head)

        # 4. Food consumption check
        if new_head == self.state.food:
            self.state.score += 10
            if self.state.score > self.state.high_score:
                self.state.high_score = self.state.score
            self.state.food = self.spawn_food()
        else:
            # Did not eat food: remove tail segment
            self.state.snake.pop()

        return True

    def _handle_game_over(self) -> None:
        self.state.is_game_over = True
        if self.state.score >= self.state.high_score and self.state.score > 0:
            save_high_score(self.storage_path, self.state.score)
