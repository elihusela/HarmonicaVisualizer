"""Tests for image_converter.consts module."""

import pytest
from image_converter.consts import (
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    C_BASIC_MODEL_WIDTH,
    C_BASIC_MODEL_HEIGHT,
    OUT_COLOR,
    IN_COLOR,
    C_BASIC_MODEL_HOLE_MAPPING,
    C_NEW_MODEL_HOLE_MAPPING,
)


class TestImageConstants:
    """Test image dimension constants."""

    def test_image_dimensions(self):
        """Test image dimension constants are defined."""
        assert IMAGE_WIDTH == 1536
        assert IMAGE_HEIGHT == 512
        assert isinstance(IMAGE_WIDTH, int)
        assert isinstance(IMAGE_HEIGHT, int)

    def test_basic_model_dimensions(self):
        """Test basic model hole dimensions."""
        assert C_BASIC_MODEL_WIDTH == 40
        assert C_BASIC_MODEL_HEIGHT == 84
        assert isinstance(C_BASIC_MODEL_WIDTH, int)
        assert isinstance(C_BASIC_MODEL_HEIGHT, int)


class TestColorConstants:
    """Test color scheme constants."""

    def test_color_values(self):
        """Test color constants are valid hex colors."""
        assert OUT_COLOR == "#41dd65"  # Green for blow notes
        assert IN_COLOR == "#fd4444"  # Red for draw notes

        # Verify they're valid hex color format
        assert OUT_COLOR.startswith("#")
        assert IN_COLOR.startswith("#")
        assert len(OUT_COLOR) == 7  # #RRGGBB
        assert len(IN_COLOR) == 7  # #RRGGBB

    def test_color_difference(self):
        """Test colors are different."""
        assert OUT_COLOR != IN_COLOR


class TestHoleMappingStructure:
    """Test hole mapping data structure consistency."""

    @pytest.mark.parametrize(
        "mapping", [C_BASIC_MODEL_HOLE_MAPPING, C_NEW_MODEL_HOLE_MAPPING]
    )
    def test_hole_mapping_structure(self, mapping):
        """Test hole mapping has correct structure."""
        # Should have holes 1-10
        expected_holes = set(range(1, 11))
        actual_holes = set(mapping.keys())
        assert actual_holes == expected_holes

        for hole_num, coordinates in mapping.items():
            # Each hole should have top_left and bottom_right
            assert "top_left" in coordinates
            assert "bottom_right" in coordinates

            # Each coordinate should have x and y
            for corner in ["top_left", "bottom_right"]:
                assert "x" in coordinates[corner]
                assert "y" in coordinates[corner]
                assert isinstance(coordinates[corner]["x"], int)
                assert isinstance(coordinates[corner]["y"], int)

    @pytest.mark.parametrize(
        "mapping", [C_BASIC_MODEL_HOLE_MAPPING, C_NEW_MODEL_HOLE_MAPPING]
    )
    def test_hole_coordinate_validity(self, mapping):
        """Test hole coordinates are reasonable."""
        for hole_num, coordinates in mapping.items():
            top_left = coordinates["top_left"]
            bottom_right = coordinates["bottom_right"]

            # Bottom right should be below and to the right of top left
            assert (
                bottom_right["x"] > top_left["x"]
            ), f"Hole {hole_num}: invalid x coordinates"
            assert (
                bottom_right["y"] > top_left["y"]
            ), f"Hole {hole_num}: invalid y coordinates"

            # Coordinates should be within reasonable image bounds
            for point in [top_left, bottom_right]:
                assert (
                    0 <= point["x"] <= IMAGE_WIDTH
                ), f"Hole {hole_num}: x coordinate out of bounds"
                assert (
                    0 <= point["y"] <= IMAGE_HEIGHT
                ), f"Hole {hole_num}: y coordinate out of bounds"

    def test_hole_ordering(self):
        """Test holes are ordered left to right."""
        for mapping in [C_BASIC_MODEL_HOLE_MAPPING, C_NEW_MODEL_HOLE_MAPPING]:
            x_positions = []
            for hole_num in range(1, 11):
                x_center = (
                    mapping[hole_num]["top_left"]["x"]
                    + mapping[hole_num]["bottom_right"]["x"]
                ) / 2
                x_positions.append(x_center)

            # X positions should be increasing (left to right)
            assert x_positions == sorted(
                x_positions
            ), "Holes should be ordered left to right"

    def test_basic_vs_new_model_differences(self):
        """Test that basic and new models have different coordinates."""
        # They should have different coordinate values
        assert C_BASIC_MODEL_HOLE_MAPPING != C_NEW_MODEL_HOLE_MAPPING

        # But same structure
        assert set(C_BASIC_MODEL_HOLE_MAPPING.keys()) == set(
            C_NEW_MODEL_HOLE_MAPPING.keys()
        )

    def test_hole_size_consistency(self):
        """Test holes have consistent sizes within each model."""
        for mapping_name, mapping in [
            ("basic", C_BASIC_MODEL_HOLE_MAPPING),
            ("new", C_NEW_MODEL_HOLE_MAPPING),
        ]:
            widths = []
            heights = []

            for hole_num, coordinates in mapping.items():
                width = coordinates["bottom_right"]["x"] - coordinates["top_left"]["x"]
                height = coordinates["bottom_right"]["y"] - coordinates["top_left"]["y"]
                widths.append(width)
                heights.append(height)

            # Sizes should be reasonably consistent (allow some variation)
            width_range = max(widths) - min(widths)
            height_range = max(heights) - min(heights)

            # Allow up to 20% variation in size
            assert (
                width_range <= max(widths) * 0.2
            ), f"{mapping_name} model: width variation too large"
            assert (
                height_range <= max(heights) * 0.2
            ), f"{mapping_name} model: height variation too large"


class TestHoleMappingCalculations:
    """Test coordinate calculations and utilities."""

    def test_hole_center_calculation(self):
        """Test calculating hole centers."""
        mapping = C_NEW_MODEL_HOLE_MAPPING
        hole_1 = mapping[1]

        expected_center_x = (hole_1["top_left"]["x"] + hole_1["bottom_right"]["x"]) / 2
        expected_center_y = (hole_1["top_left"]["y"] + hole_1["bottom_right"]["y"]) / 2

        assert expected_center_x == (290 + 341) / 2
        assert expected_center_y == (333 + 400) / 2

    def test_hole_dimensions_calculation(self):
        """Test calculating hole dimensions."""
        mapping = C_NEW_MODEL_HOLE_MAPPING
        hole_1 = mapping[1]

        width = hole_1["bottom_right"]["x"] - hole_1["top_left"]["x"]
        height = hole_1["bottom_right"]["y"] - hole_1["top_left"]["y"]

        assert width == 341 - 290
        assert height == 400 - 333
        assert width > 0
        assert height > 0

    def test_no_hole_overlap(self):
        """Test that holes don't overlap."""
        for mapping in [C_BASIC_MODEL_HOLE_MAPPING, C_NEW_MODEL_HOLE_MAPPING]:
            holes = list(mapping.items())

            for i, (hole1_num, hole1_coords) in enumerate(holes):
                for hole2_num, hole2_coords in holes[i + 1 :]:
                    # Check if rectangles overlap
                    h1_left = hole1_coords["top_left"]["x"]
                    h1_right = hole1_coords["bottom_right"]["x"]
                    h1_top = hole1_coords["top_left"]["y"]
                    h1_bottom = hole1_coords["bottom_right"]["y"]

                    h2_left = hole2_coords["top_left"]["x"]
                    h2_right = hole2_coords["bottom_right"]["x"]
                    h2_top = hole2_coords["top_left"]["y"]
                    h2_bottom = hole2_coords["bottom_right"]["y"]

                    # No overlap condition
                    no_overlap = (
                        h1_right <= h2_left  # hole1 completely to the left
                        or h2_right <= h1_left  # hole2 completely to the left
                        or h1_bottom <= h2_top  # hole1 completely above
                        or h2_bottom <= h1_top  # hole2 completely above
                    )

                    assert no_overlap, f"Holes {hole1_num} and {hole2_num} overlap"
