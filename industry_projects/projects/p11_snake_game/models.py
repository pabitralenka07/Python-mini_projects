"""Data models for Snake Game."""

from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """Movement directions with (dx, dy) coordinate deltas."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def opposite(self) -> "Direction":
        """Returns the 180-degree opposite direction."""
        if self == Direction.UP:
            return Direction.DOWN
        elif self == Direction.DOWN:
            return Direction.UP
        elif self == Direction.LEFT:
            return Direction.RIGHT
        else:
            return Direction.LEFT


@dataclass(frozen=True)
class Point:
    """Discrete 2D coordinate on the game grid."""

    x: int
    y: int


@dataclass
class GameState:
    """Mutable snapshot of the active game session."""

    snake: list[Point]
    direction: Direction
    food: Point
    score: int
    high_score: int
    is_game_over: bool
    is_paused: bool
    grid_width: int
    grid_height: int
