"""
The Game class owns all mutable state: current phase, entities on
screen, score, and per-entity cooldown timers. `Game.update()` is
called once per frame with the current BGR frame and the derived
HandState, and draws everything back onto that frame.
"""

import random
import cv2
import config, entities, svg_loader

PHASE_DEBRIS = "debris"
PHASE_PREDATOR = "predator"
PHASE_FEEDING = "feeding"
PHASE_DONE = "done"

PHASE_ORDER = [PHASE_DEBRIS, PHASE_PREDATOR, PHASE_FEEDING, PHASE_DONE]

PHASE_TITLES = {
    PHASE_DEBRIS: "Phase 1: Clear the debris - pinch and grab each item",
    PHASE_PREDATOR: "Phase 2: Push the predator away - open palm, push forward",
    PHASE_FEEDING: "Phase 3: Feed the assets with the matching finger",
    PHASE_DONE: "Great job! Game complete.",
}


class Entity:
    """(kept here only as a type reference; real class lives in entities.py)"""


class Game:
    def __init__(self, frame_w: int, frame_h: int):
        self.frame_w = frame_w
        self.frame_h = frame_h

        self.phase = PHASE_DEBRIS
        self.score = 0
        self.phase_progress = 0  # correct actions within the current phase

        self.active = []          # entities currently on screen for the active phase
        self.decor = []           # purely decorative assets, present throughout
        self._cooldowns = {}      # id(entity) -> frames remaining before it can score again
        self._grab_hold = {}      # id(entity) -> consecutive pinch+overlap frame count
        self._finger_cooldown = {f: 0 for f in config.FINGER_FISH_MAP}

        self._spawn_decor()
        self._refill_active()

    # ------------------------------------------------------------------
    # Spawning helpers
    # ------------------------------------------------------------------
    def _spawn_decor(self):
        for name in config.DECORATIVE_FISH:
            for _ in range(2):
                self.decor.append(entities.spawn_decor_fish(self.frame_w, self.frame_h, name))

    def _refill_active(self):
        if self.phase == PHASE_DEBRIS:
            while len(self.active) < min(config.MAX_DEBRIS_ON_SCREEN,
                                          config.DEBRIS_TARGET - self.phase_progress):
                self.active.append(entities.spawn_debris(self.frame_w, self.frame_h))
        elif self.phase == PHASE_PREDATOR:
            while len(self.active) < min(config.MAX_PREDATORS_ON_SCREEN,
                                          config.PREDATOR_TARGET - self.phase_progress):
                self.active.append(entities.spawn_predator(self.frame_w, self.frame_h))
        elif self.phase == PHASE_FEEDING:
            colors = list(config.FINGER_FISH_MAP.values())
            while len(self.active) < min(config.MAX_FEED_FISH_ON_SCREEN,
                                          config.FEEDING_TARGET - self.phase_progress):
                name = random.choice(colors)
                self.active.append(entities.spawn_feed_fish(self.frame_w, self.frame_h, name))

    def _advance_phase(self):
        idx = PHASE_ORDER.index(self.phase)
        self.phase = PHASE_ORDER[min(idx + 1, len(PHASE_ORDER) - 1)]
        self.phase_progress = 0
        self.active = []
        self._grab_hold.clear()
        self._cooldowns.clear()
        if self.phase != PHASE_DONE:
            self._refill_active()

    def _score_point(self):
        self.score += 1
        self.phase_progress += 1
        target = {
            PHASE_DEBRIS: config.DEBRIS_TARGET,
            PHASE_PREDATOR: config.PREDATOR_TARGET,
            PHASE_FEEDING: config.FEEDING_TARGET,
        }.get(self.phase)
        if target is not None and self.phase_progress >= target:
            self._advance_phase()

    # ------------------------------------------------------------------
    # Per-phase update logic
    # ------------------------------------------------------------------
    def _update_debris(self, hand_state):
        for ent in list(self.active):
            eid = id(ent)
            self._grab_hold.setdefault(eid, 0)
            overlapping = hand_state.present and hand_state.is_pinching and \
                ent.contains(*hand_state.pinch_point)
            if overlapping:
                self._grab_hold[eid] += 1
            else:
                self._grab_hold[eid] = 0

            if self._grab_hold[eid] >= config.GRAB_HOLD_FRAMES:
                self.active.remove(ent)
                self._grab_hold.pop(eid, None)
                self._score_point()
                self._refill_active()

    def _update_predator(self, hand_state):
        for ent in list(self.active):
            eid = id(ent)
            self._cooldowns[eid] = max(0, self._cooldowns.get(eid, 0) - 1)

            can_score = self._cooldowns[eid] == 0
            pushing = (
                hand_state.present
                and hand_state.is_palm_open
                and hand_state.palm_speed > config.PALM_PUSH_SPEED_PX
                and ent.contains(*hand_state.palm_center)
            )
            if pushing and can_score:
                self.active.remove(ent)
                self._cooldowns.pop(eid, None)
                self._score_point()
                self._refill_active()

    def _update_feeding(self, hand_state):
        for finger in self._finger_cooldown:
            self._finger_cooldown[finger] = max(0, self._finger_cooldown[finger] - 1)

        if not hand_state.present:
            return

        for finger, target_name in config.FINGER_FISH_MAP.items():
            if self._finger_cooldown[finger] > 0:
                continue
            tip = hand_state.finger_tips.get(finger)
            if tip is None:
                continue
            for ent in list(self.active):
                if ent.name != target_name:
                    continue
                if ent.contains(*tip):
                    self.active.remove(ent)
                    self._finger_cooldown[finger] = config.TAP_COOLDOWN_FRAMES
                    self._score_point()
                    self._refill_active()
                    break

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, hand_state):
        for ent in self.active:
            ent.step(self.frame_w, self.frame_h)
        for ent in self.decor:
            ent.step(self.frame_w, self.frame_h)

        if self.phase == PHASE_DEBRIS:
            self._update_debris(hand_state)
        elif self.phase == PHASE_PREDATOR:
            self._update_predator(hand_state)
        elif self.phase == PHASE_FEEDING:
            self._update_feeding(hand_state)

    def draw(self, frame):
        for ent in self.decor:
            sprite = svg_loader.load_asset(ent.name, ent.size)
            svg_loader.overlay_bgra(frame, sprite, int(ent.x), int(ent.y))
        for ent in self.active:
            sprite = svg_loader.load_asset(ent.name, ent.size)
            svg_loader.overlay_bgra(frame, sprite, int(ent.x), int(ent.y))
        self._draw_hud(frame)

    def _draw_hud(self, frame):
        cv2.rectangle(frame, (0, 0), (self.frame_w, 70), (20, 20, 20), -1)
        cv2.putText(
            frame, PHASE_TITLES[self.phase], (16, 30),
            cv2.FONT_HERSHEY_SIMPLEX, config.HUD_FONT_SCALE * 0.7,
            (255, 255, 255), 2, cv2.LINE_AA,
        )
        cv2.putText(
            frame, f"Score: {self.score} / {config.SCORE_TARGET}", (16, 58),
            cv2.FONT_HERSHEY_SIMPLEX, config.HUD_FONT_SCALE * 0.6,
            (0, 220, 255), 2, cv2.LINE_AA,
        )
        if self.phase == PHASE_DONE:
            text = "GAME COMPLETE - press Q to quit"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
            x = (self.frame_w - tw) // 2
            y = (self.frame_h + th) // 2
            cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                        (0, 255, 120), 3, cv2.LINE_AA)

    @property
    def is_done(self) -> bool:
        return self.phase == PHASE_DONE
