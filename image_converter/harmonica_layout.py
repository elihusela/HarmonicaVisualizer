from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional


@dataclass
class HoleCoordinates:
    """Represents coordinates for a single harmonica hole."""

    x: int
    y: int
    width: int
    height: int
    center_x: int
    center_y: int


@dataclass
class LayoutConfig:
    """Configuration for harmonica layout processing."""

    min_coordinate: int = 0
    max_coordinate: int = 2000
    validate_coordinates: bool = True


class HarmonicaLayoutError(Exception):
    """Custom exception for harmonica layout errors."""

    pass


class HarmonicaLayout:
    """
    Manages harmonica hole positions and coordinates for animation.

    Handles validation, coordinate calculation, and provides a clean API
    for accessing hole positions and rectangles used in video animation.
    """

    def __init__(
        self,
        image_path: str,
        hole_map: Dict[int, Dict[str, Dict[str, int]]],
        config: Optional[LayoutConfig] = None,
    ):
        """
        Initialize harmonica layout.

        Args:
            image_path: Path to harmonica background image
            hole_map: Dictionary mapping hole numbers to coordinate data
            config: Optional configuration for layout processing

        Raises:
            HarmonicaLayoutError: If hole mapping data is invalid
        """
        self._image_path = image_path
        self._config = config or LayoutConfig()

        # Validate and process hole mapping data
        self._validate_hole_map(hole_map)
        self._hole_raw_data = hole_map

        # Calculate derived data
        self._hole_coordinates = self._calculate_hole_coordinates()
        self._hole_positions = self._extract_positions()

    def get_position(self, hole: int) -> Tuple[int, int]:
        """
        Get center position for a hole.

        Args:
            hole: Hole number (1-10)

        Returns:
            Tuple of (center_x, center_y) coordinates
        """
        return self._hole_positions.get(hole, (0, 0))

    def get_rectangle(self, hole: int) -> Tuple[int, int, int, int]:
        """
        Get rectangle coordinates for a hole.

        Args:
            hole: Hole number (1-10)

        Returns:
            Tuple of (x, y, width, height) for rectangle drawing
        """
        coords = self._hole_coordinates.get(hole)
        if not coords:
            return 0, 0, 0, 0
        return coords.x, coords.y, coords.width, coords.height

    def get_all_holes(self) -> List[int]:
        """
        Get list of all available hole numbers.

        Returns:
            Sorted list of hole numbers
        """
        return sorted(self._hole_coordinates.keys())

    def get_layout_info(self) -> dict:
        """
        Get comprehensive layout information for debugging.

        Returns:
            Dict with layout properties and statistics
        """
        holes = self.get_all_holes()

        return {
            "image_path": self._image_path,
            "total_holes": len(holes),
            "hole_numbers": holes,
            "coordinate_range": self._get_coordinate_range(),
            "layout_bounds": self._get_layout_bounds(),
            "config": {
                "min_coordinate": self._config.min_coordinate,
                "max_coordinate": self._config.max_coordinate,
                "validate_coordinates": self._config.validate_coordinates,
            },
        }

    def _validate_hole_map(
        self, hole_map: Dict[int, Dict[str, Dict[str, int]]]
    ) -> None:
        """
        Validate hole mapping data structure and values.

        Args:
            hole_map: Raw hole mapping data

        Raises:
            HarmonicaLayoutError: If validation fails
        """
        if not hole_map:
            raise HarmonicaLayoutError("Hole map cannot be empty")

        if not self._config.validate_coordinates:
            return

        for hole, coords in hole_map.items():
            try:
                # Validate hole number
                if not isinstance(hole, int) or hole < 1:
                    raise HarmonicaLayoutError(f"Invalid hole number: {hole}")

                # Validate structure
                if "top_left" not in coords or "bottom_right" not in coords:
                    raise HarmonicaLayoutError(
                        f"Missing coordinate data for hole {hole}"
                    )

                top_left = coords["top_left"]
                bottom_right = coords["bottom_right"]

                # Validate coordinate structure
                for corner, corner_coords in [
                    ("top_left", top_left),
                    ("bottom_right", bottom_right),
                ]:
                    if "x" not in corner_coords or "y" not in corner_coords:
                        raise HarmonicaLayoutError(
                            f"Missing x/y in {corner} for hole {hole}"
                        )

                # Validate coordinate values
                tl_x, tl_y = top_left["x"], top_left["y"]
                br_x, br_y = bottom_right["x"], bottom_right["y"]

                # Check coordinate ranges
                for coord, name in [
                    (tl_x, f"hole {hole} top_left.x"),
                    (tl_y, f"hole {hole} top_left.y"),
                    (br_x, f"hole {hole} bottom_right.x"),
                    (br_y, f"hole {hole} bottom_right.y"),
                ]:
                    if not (
                        self._config.min_coordinate
                        <= coord
                        <= self._config.max_coordinate
                    ):
                        raise HarmonicaLayoutError(
                            f"Coordinate out of range for {name}: {coord}"
                        )

                # Validate rectangle geometry
                if br_x <= tl_x or br_y <= tl_y:
                    raise HarmonicaLayoutError(
                        f"Invalid rectangle for hole {hole}: bottom_right must be > top_left"
                    )

            except (KeyError, TypeError, ValueError) as e:
                raise HarmonicaLayoutError(
                    f"Invalid coordinate data for hole {hole}: {e}"
                )

    def _calculate_hole_coordinates(self) -> Dict[int, HoleCoordinates]:
        """
        Calculate processed coordinate data for all holes.

        Returns:
            Dictionary mapping hole numbers to HoleCoordinates
        """
        coordinates = {}

        for hole, coords in self._hole_raw_data.items():
            try:
                top_left = coords["top_left"]
                bottom_right = coords["bottom_right"]

                # Extract base coordinates
                x, y = top_left["x"], top_left["y"]
                width = bottom_right["x"] - top_left["x"]
                height = bottom_right["y"] - top_left["y"]

                # Calculate center
                center_x = (top_left["x"] + bottom_right["x"]) // 2
                center_y = (top_left["y"] + bottom_right["y"]) // 2

                coordinates[hole] = HoleCoordinates(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    center_x=center_x,
                    center_y=center_y,
                )

            except Exception as e:
                raise HarmonicaLayoutError(
                    f"Failed to calculate coordinates for hole {hole}: {e}"
                )

        return coordinates

    def _extract_positions(self) -> Dict[int, Tuple[int, int]]:
        """
        Extract center positions from calculated coordinates.

        Returns:
            Dictionary mapping hole numbers to (center_x, center_y) tuples
        """
        return {
            hole: (coords.center_x, coords.center_y)
            for hole, coords in self._hole_coordinates.items()
        }

    def _get_coordinate_range(self) -> dict:
        """
        Calculate coordinate range statistics.

        Returns:
            Dict with min/max coordinate values
        """
        if not self._hole_coordinates:
            return {"x_min": 0, "x_max": 0, "y_min": 0, "y_max": 0}

        all_coords = list(self._hole_coordinates.values())

        return {
            "x_min": min(coord.x for coord in all_coords),
            "x_max": max(coord.x + coord.width for coord in all_coords),
            "y_min": min(coord.y for coord in all_coords),
            "y_max": max(coord.y + coord.height for coord in all_coords),
        }

    def _get_layout_bounds(self) -> dict:
        """
        Calculate overall layout boundaries.

        Returns:
            Dict with layout width, height, and area
        """
        coord_range = self._get_coordinate_range()

        width = coord_range["x_max"] - coord_range["x_min"]
        height = coord_range["y_max"] - coord_range["y_min"]

        return {
            "width": width,
            "height": height,
            "area": width * height,
            "aspect_ratio": width / height if height > 0 else 0,
        }

    # Backwards compatibility properties
    @property
    def hole_positions(self) -> Dict[int, Tuple[int, int]]:
        """Legacy property for backwards compatibility."""
        return self._hole_positions

    @property
    def image_path(self) -> str:
        """Image path property for backwards compatibility."""
        return self._image_path

    @property
    def hole_raw_data(self) -> Dict[int, Dict[str, Dict[str, int]]]:
        """Raw hole data property for backwards compatibility."""
        return self._hole_raw_data
