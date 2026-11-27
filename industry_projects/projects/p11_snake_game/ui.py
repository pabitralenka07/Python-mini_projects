"""Pygame graphical user interface for Snake Game (Lazy loaded)."""

from pathlib import Path

from projects.p11_snake_game.core import SnakeGame
from projects.p11_snake_game.models import Direction


def run_game_loop(
    game: SnakeGame | None = None,
    cell_size: int = 25,
    fps: int = 10,
    headless: bool = False,
) -> None:
    """Launches the Pygame rendering loop."""
    import pygame

    if headless:
        import os

        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()

    font = None
    big_font = None
    try:
        pygame.font.init()
        font = pygame.font.SysFont("Helvetica", 18, bold=True)
        big_font = pygame.font.SysFont("Helvetica", 32, bold=True)
    except (NotImplementedError, AttributeError, ImportError, RuntimeError):
        pass

    if game is None:
        data_path = Path(__file__).resolve().parent / "data" / "highscore.json"
        game = SnakeGame(grid_width=20, grid_height=20, storage_path=data_path)

    banner_height = 60
    screen_width = game.grid_width * cell_size
    screen_height = game.grid_height * cell_size + banner_height

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Antigravity Classic Snake")
    clock = pygame.time.Clock()

    color_bg = (15, 23, 42)
    color_banner = (30, 41, 59)
    color_grid = (51, 65, 85)
    color_snake_head = (52, 211, 153)
    color_snake_body = (16, 185, 129)
    color_food = (239, 68, 68)
    color_text = (248, 250, 252)
    color_gold = (251, 191, 36)

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_SPACE, pygame.K_p):
                    game.toggle_pause()
                elif event.key == pygame.K_r:
                    game.reset()
                elif event.key in (pygame.K_UP, pygame.K_w):
                    game.change_direction(Direction.UP)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    game.change_direction(Direction.DOWN)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    game.change_direction(Direction.LEFT)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    game.change_direction(Direction.RIGHT)

        game.step()

        screen.fill(color_bg)

        pygame.draw.rect(screen, color_banner, (0, 0, screen_width, banner_height))
        if font is not None:
            score_surf = font.render(f"Score: {game.state.score}", True, color_text)
            high_surf = font.render(f"High Score: {game.state.high_score}", True, color_gold)
            screen.blit(score_surf, (16, 20))
            screen.blit(high_surf, (screen_width - high_surf.get_width() - 16, 20))

        for gx in range(game.grid_width):
            for gy in range(game.grid_height):
                rect = (
                    gx * cell_size,
                    gy * cell_size + banner_height,
                    cell_size,
                    cell_size,
                )
                pygame.draw.rect(screen, color_grid, rect, 1)

        if game.state.food.x >= 0 and game.state.food.y >= 0:
            food_rect = (
                game.state.food.x * cell_size + 2,
                game.state.food.y * cell_size + banner_height + 2,
                cell_size - 4,
                cell_size - 4,
            )
            pygame.draw.rect(screen, color_food, food_rect, border_radius=6)

        for idx, pt in enumerate(game.state.snake):
            color = color_snake_head if idx == 0 else color_snake_body
            seg_rect = (
                pt.x * cell_size + 1,
                pt.y * cell_size + banner_height + 1,
                cell_size - 2,
                cell_size - 2,
            )
            radius = 8 if idx == 0 else 4
            pygame.draw.rect(screen, color, seg_rect, border_radius=radius)

        if game.state.is_paused:
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            if big_font is not None:
                pause_text = big_font.render("GAME PAUSED", True, color_gold)
                screen.blit(
                    pause_text,
                    (
                        (screen_width - pause_text.get_width()) // 2,
                        (screen_height - pause_text.get_height()) // 2,
                    ),
                )

        if game.state.is_game_over:
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            if big_font is not None and font is not None:
                go_text = big_font.render("GAME OVER", True, color_food)
                restart_text = font.render(
                    "Press 'R' to Restart or 'Esc' to Quit", True, color_text
                )
                screen.blit(
                    go_text,
                    (
                        (screen_width - go_text.get_width()) // 2,
                        (screen_height - go_text.get_height()) // 2 - 20,
                    ),
                )
                screen.blit(
                    restart_text,
                    (
                        (screen_width - restart_text.get_width()) // 2,
                        (screen_height - restart_text.get_height()) // 2 + 25,
                    ),
                )

        pygame.display.flip()
        clock.tick(fps)

        if headless:
            break

    pygame.quit()


if __name__ == "__main__":
    run_game_loop()
