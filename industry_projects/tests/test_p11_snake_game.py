"""Tests for Project 11: Classic Snake Game."""

import random
from pathlib import Path

import pytest

from projects.p11_snake_game.core import SnakeGame
from projects.p11_snake_game.models import Direction, Point
from projects.p11_snake_game.storage import load_high_score, save_high_score
from projects.p11_snake_game.ui import run_game_loop


@pytest.fixture
def test_game(tmp_path: Path) -> SnakeGame:
    storage = tmp_path / "highscore.json"
    rng = random.Random(42)
    return SnakeGame(grid_width=10, grid_height=10, rng=rng, storage_path=storage)


def test_snake_initialization(test_game: SnakeGame) -> None:
    state = test_game.state
    assert len(state.snake) == 3
    # Head should be at (5, 5) heading RIGHT
    assert state.snake[0] == Point(5, 5)
    assert state.snake[1] == Point(4, 5)
    assert state.snake[2] == Point(3, 5)
    assert state.direction == Direction.RIGHT
    assert state.score == 0
    assert not state.is_game_over
    assert not state.is_paused


def test_snake_safe_movement_step(test_game: SnakeGame) -> None:
    # Ensure food is not immediately in front
    test_game.state.food = Point(0, 0)
    moved = test_game.step()

    assert moved is True
    # Head moved one cell RIGHT from (5,5) to (6,5)
    assert test_game.state.snake[0] == Point(6, 5)
    assert len(test_game.state.snake) == 3  # Tail followed
    assert test_game.state.snake[-1] == Point(4, 5)


def test_180_degree_turn_rejection(test_game: SnakeGame) -> None:
    assert test_game.state.direction == Direction.RIGHT

    # Attempting to reverse directly to LEFT must be rejected
    rejected = test_game.change_direction(Direction.LEFT)
    assert rejected is False
    assert test_game.state.direction == Direction.RIGHT

    # Turning perpendicular (UP or DOWN) must succeed
    accepted = test_game.change_direction(Direction.UP)
    assert accepted is True
    assert test_game.state.direction == Direction.UP


def test_food_consumption_and_growth(test_game: SnakeGame) -> None:
    # Place food directly in front of snake head at (6, 5)
    test_game.state.food = Point(6, 5)
    test_game.step()

    assert test_game.state.score == 10
    assert len(test_game.state.snake) == 4  # Snake grew by 1 segment
    assert test_game.state.snake[0] == Point(6, 5)
    # New food should have spawned at a different cell
    assert test_game.state.food != Point(6, 5)


def test_wall_collision_triggers_game_over(test_game: SnakeGame) -> None:
    # Teleport snake head near right edge at (9, 5)
    test_game.state.snake = [Point(9, 5), Point(8, 5), Point(7, 5)]
    test_game.state.direction = Direction.RIGHT
    test_game.state.food = Point(0, 0)

    # Moving right should hit the wall (grid width is 10)
    moved = test_game.step()
    assert moved is False
    assert test_game.state.is_game_over is True


def test_self_collision_triggers_game_over(test_game: SnakeGame) -> None:
    # Construct a snake shaped such that turning UP will hit an internal body segment at (5, 4)
    # (5,5) -> (5,6) -> (4,6) -> (4,5) -> (4,4) -> (5,4) -> (6,4)
    test_game.state.snake = [
        Point(5, 5),
        Point(5, 6),
        Point(4, 6),
        Point(4, 5),
        Point(4, 4),
        Point(5, 4),
        Point(6, 4),
    ]
    test_game.state.direction = Direction.UP  # Heading towards (5, 4), which is in snake[:-1]
    test_game.state.food = Point(0, 0)

    moved = test_game.step()
    assert moved is False
    assert test_game.state.is_game_over is True


def test_pause_and_resume(test_game: SnakeGame) -> None:
    # Toggle pause on
    is_paused = test_game.toggle_pause()
    assert is_paused is True
    assert test_game.state.is_paused is True

    # Step should do nothing while paused
    head_before = test_game.state.snake[0]
    moved = test_game.step()
    assert moved is False
    assert test_game.state.snake[0] == head_before

    # Unpause
    test_game.toggle_pause()
    assert test_game.state.is_paused is False
    assert test_game.step() is True


def test_atomic_high_score_storage(tmp_path: Path) -> None:
    score_file = tmp_path / "highscores" / "score.json"
    assert load_high_score(score_file) == 0

    save_high_score(score_file, 150)
    assert load_high_score(score_file) == 150

    # Overwrite with higher score
    save_high_score(score_file, 300)
    assert load_high_score(score_file) == 300


def test_headless_pygame_ui_loop(test_game: SnakeGame) -> None:
    # Test headless UI loop run using dummy driver
    run_game_loop(game=test_game, headless=True)
