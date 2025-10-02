"""Tests for image_converter.harmonica_layout module."""

import os
import tempfile
import pytest

from image_converter.harmonica_layout import (
    HarmonicaLayout,
    HarmonicaLayoutError,
    HoleCoordinates,
    LayoutConfig,
)


class TestHoleCoordinates:
    """Test HoleCoordinates dataclass."""

    def test_hole_coordinates_creation(self):
        """Test creating HoleCoordinates."""
        coords = HoleCoordinates(
            x=10, y=20, width=30, height=40, center_x=25, center_y=40
        )

        assert coords.x == 10
        assert coords.y == 20
        assert coords.width == 30
        assert coords.height == 40
        assert coords.center_x == 25
        assert coords.center_y == 40

    def test_hole_coordinates_equality(self):
        """Test HoleCoordinates equality."""
        coords1 = HoleCoordinates(
            x=10, y=20, width=30, height=40, center_x=25, center_y=40
        )
        coords2 = HoleCoordinates(
            x=10, y=20, width=30, height=40, center_x=25, center_y=40
        )
        coords3 = HoleCoordinates(
            x=15, y=20, width=30, height=40, center_x=30, center_y=40
        )

        assert coords1 == coords2
        assert coords1 != coords3


class TestLayoutConfig:
    """Test LayoutConfig dataclass."""

    def test_layout_config_defaults(self):
        """Test LayoutConfig default values."""
        config = LayoutConfig()

        assert config.min_coordinate == 0
        assert config.max_coordinate == 2000
        assert config.validate_coordinates is True

    def test_layout_config_custom_values(self):
        """Test LayoutConfig with custom values."""
        config = LayoutConfig(
            min_coordinate=50, max_coordinate=1500, validate_coordinates=False
        )

        assert config.min_coordinate == 50
        assert config.max_coordinate == 1500
        assert config.validate_coordinates is False


class TestHarmonicaLayoutInitialization:
    """Test HarmonicaLayout initialization."""

    def test_init_successful(self, temp_image_file, sample_hole_mapping, layout_config):
        """Test successful initialization."""
        layout = HarmonicaLayout(temp_image_file, sample_hole_mapping, layout_config)

        assert layout._image_path == temp_image_file
        assert layout._hole_raw_data == sample_hole_mapping
        assert layout._config == layout_config

    def test_init_missing_image_file(self, sample_hole_mapping, layout_config):
        """Test initialization with missing image file."""
        # HarmonicaLayout doesn't validate file existence during init
        layout = HarmonicaLayout(
            "/nonexistent/image.png", sample_hole_mapping, layout_config
        )
        assert layout.image_path == "/nonexistent/image.png"

    def test_init_image_path_is_directory(self, sample_hole_mapping, layout_config):
        """Test initialization with directory path instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # HarmonicaLayout doesn't validate file existence during init
            layout = HarmonicaLayout(temp_dir, sample_hole_mapping, layout_config)
            assert layout.image_path == temp_dir

    def test_init_empty_hole_map(self, temp_image_file, layout_config):
        """Test initialization with empty hole map."""
        with pytest.raises(HarmonicaLayoutError, match="Hole map cannot be empty"):
            HarmonicaLayout(temp_image_file, {}, layout_config)

    def test_init_default_config(self, temp_image_file, sample_hole_mapping):
        """Test initialization with default config."""
        layout = HarmonicaLayout(temp_image_file, sample_hole_mapping)

        assert isinstance(layout._config, LayoutConfig)
        assert layout._config.min_coordinate == 0
        assert layout._config.max_coordinate == 2000
        assert layout._config.validate_coordinates is True

    def test_init_coordinate_validation(self, temp_image_file, layout_config):
        """Test coordinate validation during initialization."""
        invalid_hole_map = {
            1: {
                "top_left": {"x": -10, "y": 10},
                "bottom_right": {"x": 50, "y": 50},
            },  # Invalid x
        }

        with pytest.raises(HarmonicaLayoutError, match="Coordinate out of range"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)

    def test_init_coordinate_validation_disabled(self, temp_image_file):
        """Test initialization with coordinate validation disabled."""
        config = LayoutConfig(validate_coordinates=False)
        invalid_hole_map = {
            1: {"top_left": {"x": -10, "y": 10}, "bottom_right": {"x": 50, "y": 50}},
        }

        # Should not raise exception when validation is disabled
        layout = HarmonicaLayout(temp_image_file, invalid_hole_map, config)
        assert layout is not None


class TestHarmonicaLayoutCoordinateOperations:
    """Test coordinate calculation and retrieval methods."""

    def test_get_position(self, harmonica_layout):
        """Test getting hole position."""
        position = harmonica_layout.get_position(1)

        assert isinstance(position, tuple)
        assert len(position) == 2
        assert position[0] == 30  # center_x: (10 + 50) / 2
        assert position[1] == 30  # center_y: (10 + 50) / 2

    def test_get_position_nonexistent(self, harmonica_layout):
        """Test getting position for nonexistent hole."""
        position = harmonica_layout.get_position(99)
        assert position == (0, 0)  # Default fallback

    def test_get_rectangle(self, harmonica_layout):
        """Test getting hole rectangle."""
        rectangle = harmonica_layout.get_rectangle(1)

        assert isinstance(rectangle, tuple)
        assert len(rectangle) == 4
        assert rectangle[0] == 10  # x
        assert rectangle[1] == 10  # y
        assert rectangle[2] == 40  # width: 50 - 10
        assert rectangle[3] == 40  # height: 50 - 10

    def test_get_rectangle_nonexistent(self, harmonica_layout):
        """Test getting rectangle for nonexistent hole."""
        rectangle = harmonica_layout.get_rectangle(99)
        assert rectangle == (0, 0, 0, 0)  # Default fallback

    def test_get_all_holes(self, harmonica_layout):
        """Test getting all hole numbers."""
        hole_numbers = harmonica_layout.get_all_holes()

        assert isinstance(hole_numbers, list)
        assert set(hole_numbers) == {1, 2, 3}
        assert hole_numbers == sorted(hole_numbers)  # Should be sorted

    def test_get_layout_info(self, harmonica_layout):
        """Test getting layout information."""
        info = harmonica_layout.get_layout_info()

        assert isinstance(info, dict)
        assert info["total_holes"] == 3
        assert info["image_path"] == harmonica_layout._image_path
        assert "config" in info
        assert isinstance(info["config"], dict)

    def test_hole_positions_property(self, harmonica_layout):
        """Test hole_positions property access."""
        positions = harmonica_layout.hole_positions

        assert isinstance(positions, dict)
        assert 1 in positions
        assert positions[1] == (30, 30)  # center coordinates

    def test_image_path_property(self, harmonica_layout):
        """Test image_path property access."""
        image_path = harmonica_layout.image_path

        assert isinstance(image_path, str)
        assert image_path == harmonica_layout._image_path


class TestHarmonicaLayoutValidation:
    """Test validation methods."""

    def test_validate_coordinates_valid(self, temp_image_file, layout_config):
        """Test validation with valid coordinates."""
        valid_hole_map = {
            1: {"top_left": {"x": 100, "y": 100}, "bottom_right": {"x": 200, "y": 200}},
            2: {"top_left": {"x": 250, "y": 100}, "bottom_right": {"x": 350, "y": 200}},
        }

        # Should not raise exception
        layout = HarmonicaLayout(temp_image_file, valid_hole_map, layout_config)
        assert layout is not None

    def test_validate_coordinates_out_of_bounds_low(
        self, temp_image_file, layout_config
    ):
        """Test validation with coordinates below minimum."""
        invalid_hole_map = {
            1: {"top_left": {"x": -5, "y": 100}, "bottom_right": {"x": 200, "y": 200}},
        }

        with pytest.raises(HarmonicaLayoutError, match="Coordinate out of range"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)

    def test_validate_coordinates_out_of_bounds_high(
        self, temp_image_file, layout_config
    ):
        """Test validation with coordinates above maximum."""
        invalid_hole_map = {
            1: {
                "top_left": {"x": 100, "y": 100},
                "bottom_right": {"x": 2500, "y": 200},
            },
        }

        with pytest.raises(HarmonicaLayoutError, match="Coordinate out of range"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)

    def test_validate_coordinates_invalid_rectangle(
        self, temp_image_file, layout_config
    ):
        """Test validation with invalid rectangle (bottom_right not below/right of top_left)."""
        invalid_hole_map = {
            1: {"top_left": {"x": 200, "y": 200}, "bottom_right": {"x": 100, "y": 100}},
        }

        with pytest.raises(HarmonicaLayoutError, match="Invalid rectangle for hole"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)

    def test_validate_hole_map_structure_missing_top_left(
        self, temp_image_file, layout_config
    ):
        """Test validation with missing top_left in hole map."""
        invalid_hole_map = {
            1: {"bottom_right": {"x": 200, "y": 200}},
        }

        with pytest.raises(HarmonicaLayoutError, match="Missing coordinate data"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)

    def test_validate_hole_map_structure_missing_coordinates(
        self, temp_image_file, layout_config
    ):
        """Test validation with missing x/y coordinates."""
        invalid_hole_map = {
            1: {
                "top_left": {"x": 100},
                "bottom_right": {"x": 200, "y": 200},
            },  # Missing y
        }

        with pytest.raises(HarmonicaLayoutError, match="Missing x/y in"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)

    def test_validate_hole_map_structure_non_integer_coordinates(
        self, temp_image_file, layout_config
    ):
        """Test validation with non-integer coordinates."""
        invalid_hole_map = {
            1: {
                "top_left": {"x": "100", "y": 100},
                "bottom_right": {"x": 200, "y": 200},
            },
        }

        with pytest.raises(HarmonicaLayoutError, match="Invalid coordinate data"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)


class TestHarmonicaLayoutErrorHandling:
    """Test error handling and edge cases."""

    def test_image_file_permissions(self, sample_hole_mapping, layout_config):
        """Test with image file that can't be accessed."""
        # This test might be platform-specific
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"dummy content")
            temp_path = temp_file.name

        try:
            # Try to make file unreadable (might not work on all systems)
            os.chmod(temp_path, 0o000)

            # Create the layout object (this should work as we only check existence)
            layout = HarmonicaLayout(temp_path, sample_hole_mapping, layout_config)

            # The error should occur when trying to read image dimensions
            # But since we're testing permission issues, we'll skip detailed testing
            # as it's platform-dependent
            assert layout is not None

        finally:
            # Restore permissions and cleanup
            os.chmod(temp_path, 0o644)
            os.unlink(temp_path)

    def test_invalid_hole_number(self, temp_image_file, layout_config):
        """Test with invalid hole number."""
        invalid_hole_map = {
            0: {
                "top_left": {"x": 100, "y": 100},
                "bottom_right": {"x": 200, "y": 200},
            },  # Invalid hole 0
        }

        with pytest.raises(HarmonicaLayoutError, match="Invalid hole number"):
            HarmonicaLayout(temp_image_file, invalid_hole_map, layout_config)

    def test_extremely_large_coordinates(self, temp_image_file):
        """Test with extremely large coordinate values."""
        config = LayoutConfig(min_coordinate=0, max_coordinate=1000000)
        large_hole_map = {
            1: {
                "top_left": {"x": 999990, "y": 999990},
                "bottom_right": {"x": 999999, "y": 999999},
            },
        }

        # Should work with appropriate config
        layout = HarmonicaLayout(temp_image_file, large_hole_map, config)
        rectangle = layout.get_rectangle(1)
        assert rectangle[0] == 999990  # x coordinate


class TestHarmonicaLayoutIntegration:
    """Test integration scenarios and real-world usage."""

    def test_realistic_harmonica_layout(self, temp_image_file):
        """Test with realistic harmonica hole coordinates."""
        realistic_mapping = {
            1: {"top_left": {"x": 100, "y": 200}, "bottom_right": {"x": 150, "y": 250}},
            2: {"top_left": {"x": 170, "y": 200}, "bottom_right": {"x": 220, "y": 250}},
            3: {"top_left": {"x": 240, "y": 200}, "bottom_right": {"x": 290, "y": 250}},
            4: {"top_left": {"x": 310, "y": 200}, "bottom_right": {"x": 360, "y": 250}},
            5: {"top_left": {"x": 380, "y": 200}, "bottom_right": {"x": 430, "y": 250}},
        }

        layout = HarmonicaLayout(temp_image_file, realistic_mapping)

        # Test all holes
        for hole_num in range(1, 6):
            rectangle = layout.get_rectangle(hole_num)
            assert rectangle[2] == 50  # width
            assert rectangle[3] == 50  # height

        # Test info
        info = layout.get_layout_info()
        assert info["total_holes"] == 5

    def test_all_coordinate_operations(self, harmonica_layout):
        """Test all coordinate operations in sequence."""
        hole_num = 1

        # Get position
        position = harmonica_layout.get_position(hole_num)
        assert isinstance(position, tuple)

        # Get rectangle
        rectangle = harmonica_layout.get_rectangle(hole_num)
        assert isinstance(rectangle, tuple)
        assert len(rectangle) == 4

        # Get all holes
        all_holes = harmonica_layout.get_all_holes()
        assert hole_num in all_holes

        # Get layout info
        info = harmonica_layout.get_layout_info()
        assert info["total_holes"] > 0

    def test_performance_with_many_holes(self, temp_image_file):
        """Test performance with many holes."""
        # Create mapping with 100 holes
        many_holes_mapping = {}
        for i in range(1, 101):
            x_start = i * 20
            many_holes_mapping[i] = {
                "top_left": {"x": x_start, "y": 100},
                "bottom_right": {"x": x_start + 15, "y": 150},
            }

        config = LayoutConfig(max_coordinate=2500)
        layout = HarmonicaLayout(temp_image_file, many_holes_mapping, config)

        # Test operations are reasonably fast
        all_holes = layout.get_all_holes()
        assert len(all_holes) == 100

        # Test random access
        position_50 = layout.get_position(50)
        assert position_50[0] == 50 * 20 + 7  # center_x (integer division)
