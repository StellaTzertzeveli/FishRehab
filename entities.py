
import random
from dataclasses import dataclass, field
import config


@dataclass
class Entity:
    name: str
    x: float
    y: float
    size: int
    vx: float = 0.0
    vy: float = 0.0
    alive: bool = True

    @property
    def radius(self) -> int:
        return self.size // 2

    def step(self, frame_w: int, frame_h: int) -> None:
        """Advance position and bounce softly off frame edges."""
        self.x += self.vx
        self.y += self.vy
        margin = self.radius
        if self.x < margin or self.x > frame_w - margin:
            self.vx *= -1
            self.x = max(margin, min(frame_w - margin, self.x))
        if self.y < margin or self.y > frame_h - margin:
            self.vy *= -1
            self.y = max(margin, min(frame_h - margin, self.y))

    def contains(self, px: float, py: float) -> bool:
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= self.radius ** 2


def spawn_debris(frame_w: int, frame_h: int) -> Entity:
    name = random.choice(["banana_trash", "soda_trash", "apple_trash", "bones_trash"])
    return Entity(
        name=name,
        x=random.uniform(config.TRASH_SIZE, frame_w - config.TRASH_SIZE),
        y=random.uniform(config.TRASH_SIZE, frame_h - config.TRASH_SIZE),
        size=config.TRASH_SIZE,
        vx=random.choice([-1, 1]) * random.uniform(0.3, 0.8),
        vy=random.choice([-1, 1]) * random.uniform(0.1, 0.4),
    )


def spawn_predator(frame_w: int, frame_h: int) -> Entity:
    side = random.choice(["left", "right"])
    x = -config.PREDATOR_SIZE if side == "left" else frame_w + config.PREDATOR_SIZE
    vx = random.uniform(1.5, 2.5) * (1 if side == "left" else -1)
    return Entity(
        name="shark_predator",
        x=x,
        y=random.uniform(config.PREDATOR_SIZE, frame_h - config.PREDATOR_SIZE),
        size=config.PREDATOR_SIZE,
        vx=vx,
        vy=random.uniform(-0.3, 0.3),
    )


def spawn_feed_fish(frame_w: int, frame_h: int, name: str) -> Entity:
    return Entity(
        name=name,
        x=random.uniform(config.FISH_SIZE, frame_w - config.FISH_SIZE),
        y=random.uniform(config.FISH_SIZE, frame_h - config.FISH_SIZE),
        size=config.FISH_SIZE,
        vx=random.choice([-1, 1]) * random.uniform(0.4, 0.9),
        vy=random.choice([-1, 1]) * random.uniform(0.2, 0.5),
    )


def spawn_decor_fish(frame_w: int, frame_h: int, name: str) -> Entity:
    return Entity(
        name=name,
        x=random.uniform(config.DECOR_FISH_SIZE, frame_w - config.DECOR_FISH_SIZE),
        y=random.uniform(config.DECOR_FISH_SIZE, frame_h - config.DECOR_FISH_SIZE),
        size=config.DECOR_FISH_SIZE,
        vx=random.choice([-1, 1]) * random.uniform(0.5, 1.0),
        vy=random.choice([-1, 1]) * random.uniform(0.2, 0.5),
    )
