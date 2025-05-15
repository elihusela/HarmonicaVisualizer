from typing import Tuple

from image_converter.consts import FIRST_X, DISTANCE, Y


class HarmonicaLayout:
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.hole_positions = self._load_layout()

    def get_position(self, hole: int) -> Tuple[int, int]:
        return self.hole_positions.get(hole, (0, 0))

    @staticmethod
    def _load_layout() -> dict[int, Tuple[int, int]]:
        return {i: (FIRST_X + (i - 1) * DISTANCE, Y) for i in range(1, 11)}
