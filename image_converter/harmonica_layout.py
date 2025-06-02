from typing import Tuple, Dict


class HarmonicaLayout:
    def __init__(self, image_path: str, hole_map: Dict[int, Dict[str, Dict[str, int]]]):
        self.image_path = image_path
        self.hole_raw_data: Dict[int, Dict[str, Dict[str, int]]] = hole_map
        self.hole_positions: Dict[int, Tuple[int, int]] = self._calc_centers()

    def get_position(self, hole: int) -> Tuple[int, int]:
        return self.hole_positions.get(hole, (0, 0))

    def get_rectangle(self, hole: int) -> Tuple[int, int, int, int]:
        coords = self.hole_raw_data.get(hole)
        if not coords:
            return 0, 0, 0, 0
        top_left = coords["top_left"]
        bottom_right = coords["bottom_right"]
        x, y = top_left["x"], top_left["y"]
        width = bottom_right["x"] - top_left["x"]
        height = bottom_right["y"] - top_left["y"]
        return x, y, width, height

    def _calc_centers(self) -> Dict[int, Tuple[int, int]]:
        return {
            hole: (
                (coords["top_left"]["x"] + coords["bottom_right"]["x"]) // 2,
                (coords["top_left"]["y"] + coords["bottom_right"]["y"]) // 2,
            )
            for hole, coords in self.hole_raw_data.items()
        }
