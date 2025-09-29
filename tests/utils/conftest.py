"""Test fixtures for utils module tests."""

import pytest


@pytest.fixture
def sample_audio_paths(temp_test_dir):
    """Sample audio file paths for testing."""
    return {
        "input_wav": str(temp_test_dir / "input.wav"),
        "output_wav": str(temp_test_dir / "output.wav"),
        "input_mp3": str(temp_test_dir / "input.mp3"),
        "output_mp3": str(temp_test_dir / "output.mp3"),
        "input_with_spaces": str(temp_test_dir / "input file with spaces.wav"),
        "output_with_spaces": str(temp_test_dir / "output file with spaces.wav"),
    }


@pytest.fixture
def audio_processor_presets():
    """Common AudioProcessor preset configurations for testing."""
    return {
        "test_default": {
            "low_freq": 200,
            "high_freq": 5000,
            "noise_reduction_db": -25,
            "target_lufs": -16,
        },
        "test_custom": {
            "low_freq": 300,
            "high_freq": 4000,
            "noise_reduction_db": -20,
            "target_lufs": -14,
            "sample_rate": 48000,
        },
        "test_extreme": {
            "low_freq": 100,
            "high_freq": 8000,
            "noise_reduction_db": -40,
            "target_lufs": -10,
            "true_peak_db": -3.0,
            "lra": 20,
            "sample_rate": 96000,
        },
    }
