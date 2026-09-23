import random
import time

import cv2
import numpy as np

import config
import svg_loader

from entities import (
Entity,
spawn_debris,
spawn_predator,
spawn_feed_fish,
spawn_decor_fish,
)

class Game:

    # Speech name -> actual debris asset/entity name
    DEBRIS_NAMES = {
        "apple": "apple_trash",
        "banana": "banana_trash",
        "soda": "soda_trash",
        "bones": "bones_trash",
    }

    def __init__(self, frame_w, frame_h):

        self.frame_w = frame_w
        self.frame_h = frame_h

        self.phase = "debris"

        self.debris_score = 0
        self.predator_score = 0
        self.feeding_score = 0

        self.active = []
        self.decor = []

        self.predator = None

        # This is the debris currently activated by speech.
        self.spoken_target_name = None

        # Warning message for predator movement.
        self.movement_warning_until = 0
        self.last_warning_time = 0

        self.assets = {}

        self._load_assets()

        self._spawn_decorative_fish()
        self._fill_debris()

    # =========================================================
    # ASSETS
    # =========================================================

    def _load_assets(self):

        names = [
            "banana_trash",
            "soda_trash",
            "apple_trash",
            "bones_trash",
            "shark_predator",
            "blue_fish",
            "green_fish",
            "pink_fish",
            "yellow_fish",
        ]

        for name in names:

            try:

                if name == "shark_predator":
                    size = config.PREDATOR_SIZE

                elif name in config.DECORATIVE_FISH:
                    size = config.DECOR_FISH_SIZE

                elif name in config.FINGER_FISH_MAP.values():
                    size = config.FISH_SIZE

                else:
                    size = config.TRASH_SIZE

                self.assets[name] = svg_loader.load_asset(
                    name,
                    size
                )

            except FileNotFoundError:

                print(
                    "Missing asset:",
                    name
                )

    # =========================================================
    # SPAWNING
    # =========================================================

    def _spawn_decorative_fish(self):

        for name in config.DECORATIVE_FISH:

            try:

                self.decor.append(
                    spawn_decor_fish(
                        self.frame_w,
                        self.frame_h,
                        name
                    )
                )

            except Exception as e:

                print(
                    "Could not spawn decorative fish:",
                    e
                )

    def _fill_debris(self):

        while (
            len(self.active)
            < config.MAX_DEBRIS_ON_SCREEN
        ):

            self.active.append(
                spawn_debris(
                    self.frame_w,
                    self.frame_h
                )
            )

    def _spawn_predator(self):

        self.predator = spawn_predator(
            self.frame_w,
            self.frame_h
        )

    def _spawn_feeding_fish(self):

        self.active.clear()

        fish_names = []

        for name in config.FINGER_FISH_MAP.values():

            if name in self.assets and name not in fish_names:
                fish_names.append(name)

        for name in fish_names:

            if (
                len(self.active)
                >= config.MAX_FEED_FISH_ON_SCREEN
            ):
                break

            self.active.append(
                spawn_feed_fish(
                    self.frame_w,
                    self.frame_h,
                    name
                )
            )

        self.decor.clear()

        for name in config.DECORATIVE_FISH:

            try:

                self.decor.append(
                    spawn_decor_fish(
                        self.frame_w,
                        self.frame_h,
                        name
                    )
                )

            except Exception as e:

                print(
                    "Could not spawn decorative fish:",
                    e
                )

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        hand_state,
        speech_state
    ):

        # Move decorative fish.
        for fish in self.decor:

            fish.step(
                self.frame_w,
                self.frame_h
            )

        if self.phase == "debris":

            self._update_debris(
                hand_state,
                speech_state
            )

        elif self.phase == "predator":

            self._update_predator(
                hand_state
            )

        elif self.phase == "feeding":

            self._update_feeding(
                hand_state
            )

    # =========================================================
    # DEBRIS PHASE
    # =========================================================

    def _update_debris(
        self,
        hand_state,
        speech_state
    ):

        # Move debris.
        for ent in self.active:

            ent.step(
                self.frame_w,
                self.frame_h
            )

        recognized = speech_state.get(
            "recognized_object"
        )

        # -----------------------------------------------------
        # A new correct word was spoken.
        # -----------------------------------------------------

        if recognized in self.DEBRIS_NAMES:

            target_name = self.DEBRIS_NAMES[
                recognized
            ]

            # Check whether that type actually exists.
            target_exists = any(
                ent.name == target_name
                for ent in self.active
            )

            if target_exists:

                self.spoken_target_name = target_name

        # -----------------------------------------------------
        # If we don't have an activated target,
        # the player cannot pick anything up.
        # -----------------------------------------------------

        if self.spoken_target_name is None:
            return

        target = None

        for ent in self.active:

            if (
                ent.name
                == self.spoken_target_name
            ):

                target = ent
                break

        # The target disappeared somehow.
        if target is None:

            self.spoken_target_name = None

            return

        # -----------------------------------------------------
        # Either hand can pinch the activated debris.
        # -----------------------------------------------------

        for hand in hand_state.hands:

            if not hand.present:
                continue

            if not hand.is_pinching:
                continue

            if hand.pinch_point is None:
                continue

            px, py = hand.pinch_point

            if target.contains(px, py):

                self.active.remove(target)

                target.alive = False

                self.debris_score += 1

                # IMPORTANT:
                # Remove the halo too.
                self.spoken_target_name = None

                # Refill the screen.
                self._fill_debris()

                # Move to predator phase.
                if (
                    self.debris_score
                    >= config.DEBRIS_TARGET
                ):

                    self.phase = "predator"

                    self.active.clear()

                    self._spawn_predator()

                break

    # =========================================================
    # PREDATOR PHASE
    # =========================================================

    def _update_predator(
        self,
        hand_state
    ):

        if self.predator is None:

            self._spawn_predator()

            return

        predator = self.predator

        # -----------------------------------------------------
        # Move predator.
        #
        # We intentionally DO NOT use Entity.step()
        # because Entity.step() keeps objects inside the frame.
        # The predator needs to leave the frame.
        # -----------------------------------------------------

        predator.x += predator.vx
        predator.y += predator.vy

        # Keep vertical movement inside the screen.
        if (
            predator.y < predator.radius
            or predator.y
            > self.frame_h - predator.radius
        ):

            predator.vy *= -1

        # -----------------------------------------------------
        # Detect a correct palm push.
        # -----------------------------------------------------

        pushed = False

        for hand in hand_state.hands:

            if not hand.present:
                continue

            if hand.palm_center is None:
                continue

            # A push should use an open palm.
            if not hand.is_palm_open:
                continue

            # The palm needs to move quickly enough.
            if (
                hand.palm_speed
                < config.PALM_PUSH_SPEED_PX
            ):
                continue

            hx, hy = hand.palm_center

            distance = (
                (hx - predator.x) ** 2
                + (hy - predator.y) ** 2
            ) ** 0.5

            if (
                distance
                <= predator.radius + 100
            ):

                pushed = True

                # Direction from hand -> shark.
                dx = predator.x - hx
                dy = predator.y - hy

                length = max(
                    (dx * dx + dy * dy) ** 0.5,
                    1
                )

                # Strong push.
                push_strength = 45

                predator.x += (
                    dx / length
                ) * push_strength

                predator.y += (
                    dy / length
                ) * push_strength

                self.predator_score += 1

                # Don't show wrong-movement message.
                self.movement_warning_until = 0

                break

        # -----------------------------------------------------
        # WRONG MOVEMENT MESSAGE
        # -----------------------------------------------------

        if not pushed:

            now = time.time()

            # Don't flash it constantly.
            if (
                now - self.last_warning_time
                > 1.0
            ):

                # Only show it when there is a hand present.
                if any(
                    hand.present
                    for hand in hand_state.hands
                ):

                    self.movement_warning_until = (
                        now + 1.0
                    )

                    self.last_warning_time = now

        # -----------------------------------------------------
        # Has shark completely left the screen?
        # -----------------------------------------------------

        completely_left = (
            predator.x
            < -predator.size
            or
            predator.x
            > self.frame_w + predator.size
            or
            predator.y
            < -predator.size
            or
            predator.y
            > self.frame_h + predator.size
        )

        if completely_left:

            self.predator = None

            # Continue predator phase until target reached.
            if (
                self.predator_score
                >= config.PREDATOR_TARGET
            ):

                self.phase = "feeding"

                self._spawn_feeding_fish()

            else:

                self._spawn_predator()

    # =========================================================
    # FEEDING
    # =========================================================

    def _update_feeding(
        self,
        hand_state
    ):

        for fish in self.active:

            fish.step(
                self.frame_w,
                self.frame_h
            )

        for hand in hand_state.hands:

            if not hand.present:
                continue

            for finger_name, point in hand.finger_tips.items():

                if point is None:
                    continue

                fish_name = (
                    config.FINGER_FISH_MAP.get(
                        finger_name
                    )
                )

                if fish_name is None:
                    continue

                for fish in self.active:

                    if fish.name != fish_name:
                        continue

                    if fish.contains(
                        point[0],
                        point[1]
                    ):

                        fish.alive = False

                        self.active.remove(
                            fish
                        )

                        self.feeding_score += 1

                        break

        # Keep fish present.
        available = [
            name
            for name in config.FINGER_FISH_MAP.values()
            if name in self.assets
        ]

        while (
            available
            and
            len(self.active)
            < min(
                config.MAX_FEED_FISH_ON_SCREEN,
                len(available)
            )
        ):

            name = random.choice(
                available
            )

            self.active.append(
                spawn_feed_fish(
                    self.frame_w,
                    self.frame_h,
                    name
                )
            )

        if (
            self.feeding_score
            >= config.FEEDING_TARGET
        ):

            self.phase = "complete"

    # =========================================================
    # DRAW
    # =========================================================

    def draw(self, frame):

        # -----------------------------------------------------
        # Decorative fish
        # -----------------------------------------------------

        for fish in self.decor:

            self._draw_entity(
                frame,
                fish
            )

        # -----------------------------------------------------
        # Debris
        # -----------------------------------------------------

        for ent in self.active:

            # Draw halo FIRST.
            #
            # This makes it appear behind the debris.
            if (
                self.phase == "debris"
                and
                ent.name
                == self.spoken_target_name
            ):

                self._draw_halo(
                    frame,
                    ent
                )

            # Then draw debris on top.
            self._draw_entity(
                frame,
                ent
            )

        # -----------------------------------------------------
        # Predator
        # -----------------------------------------------------

        if (
            self.phase == "predator"
            and
            self.predator is not None
        ):

            self._draw_entity(
                frame,
                self.predator
            )

        # -----------------------------------------------------
        # HUD
        # -----------------------------------------------------

        self._draw_hud(frame)

        # -----------------------------------------------------
        # Movement warning
        # -----------------------------------------------------

        if (
            time.time()
            < self.movement_warning_until
        ):

            text = (
                "You're not doing the right movement!"
            )

            font = cv2.FONT_HERSHEY_SIMPLEX

            scale = 0.45
            thickness = 1

            (text_w, text_h), _ = (
                cv2.getTextSize(
                    text,
                    font,
                    scale,
                    thickness
                )
            )

            margin = 20

            x = (
                self.frame_w
                - text_w
                - margin
            )

            y = (
                self.frame_h
                - margin
            )

            cv2.putText(
                frame,
                text,
                (x, y),
                font,
                scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA
            )

    # =========================================================
    # HALO
    # =========================================================

    def _draw_halo(
        self,
        frame,
        ent
    ):

        # Create a soft-looking halo using several circles.
        center = (
            int(ent.x),
            int(ent.y)
        )

        radius = int(
            ent.size * 0.62
        )

        # Outer glow.
        cv2.circle(
            frame,
            center,
            radius + 12,
            (0, 255, 255),
            8,
            cv2.LINE_AA
        )

        # Inner glow.
        cv2.circle(
            frame,
            center,
            radius,
            (0, 255, 255),
            4,
            cv2.LINE_AA
        )

    # =========================================================
    # ENTITY DRAWING
    # =========================================================

    def _draw_entity(
        self,
        frame,
        ent
    ):

        if not ent.alive:
            return

        image = self.assets.get(
            ent.name
        )

        if image is None:
            return

        # Entity x/y are CENTER coordinates.
        x = int(
            ent.x - ent.size / 2
        )

        y = int(
            ent.y - ent.size / 2
        )

        svg_loader.overlay_bgra(
            frame,
            image,
            x,
            y
        )

    # =========================================================
    # HUD
    # =========================================================

    def _draw_hud(self, frame):

        if self.phase == "debris":

            text = (
                f"Clean the water: "
                f"{self.debris_score}/"
                f"{config.DEBRIS_TARGET}"
            )

        elif self.phase == "predator":

            text = (
                f"Push the predator away: "
                f"{self.predator_score}/"
                f"{config.PREDATOR_TARGET}"
            )

        elif self.phase == "feeding":

            text = (
                f"Feed the fish: "
                f"{self.feeding_score}/"
                f"{config.FEEDING_TARGET}"
            )

        else:

            text = (
                "Rehabilitation complete!"
            )

        cv2.putText(
            frame,
            text,
            (20, self.frame_h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

