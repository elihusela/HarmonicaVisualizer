"""
Harmonica Key Registry - Centralized configuration for different harmonica keys.

Maps harmonica keys (C, G, D, etc.) to their corresponding MIDI mappings,
hole coordinate mappings, and model images.
"""

from dataclasses import dataclass
from typing import Dict

from image_converter.consts import (
    A_MODEL_HOLE_MAPPING,
    AB_MODEL_HOLE_MAPPING,
    B_MODEL_HOLE_MAPPING,
    BB_MODEL_HOLE_MAPPING,
    C_NEW_MODEL_HOLE_MAPPING,
    CS_MODEL_HOLE_MAPPING,
    D_MODEL_HOLE_MAPPING,
    E_MODEL_HOLE_MAPPING,
    EB_MODEL_HOLE_MAPPING,
    F_MODEL_HOLE_MAPPING,
    FS_MODEL_HOLE_MAPPING,
    G_MODEL_HOLE_MAPPING,
)
from tab_converter.consts import (
    A_HARMONICA_MAPPING,
    AB_HARMONICA_MAPPING,
    B_HARMONICA_MAPPING,
    BB_HARMONICA_MAPPING,
    C_HARMONICA_MAPPING,
    CS_HARMONICA_MAPPING,
    D_HARMONICA_MAPPING,
    E_HARMONICA_MAPPING,
    EB_HARMONICA_MAPPING,
    F_HARMONICA_MAPPING,
    FS_HARMONICA_MAPPING,
    G_HARMONICA_MAPPING,
)


@dataclass
class HarmonicaKeyConfig:
    """Configuration for a specific harmonica key."""

    key: str  # "C", "G", "D", etc.
    model_image: str  # Filename in harmonica-models/ directory
    midi_mapping: Dict[int, int]  # MIDI note -> harmonica hole
    hole_mapping: Dict[int, Dict]  # Hole -> coordinates


# Registry of supported harmonica keys
HARMONICA_KEY_REGISTRY: Dict[str, HarmonicaKeyConfig] = {
    "A": HarmonicaKeyConfig(
        key="A",
        model_image="A.png",
        midi_mapping=A_HARMONICA_MAPPING,
        hole_mapping=A_MODEL_HOLE_MAPPING,
    ),
    "AB": HarmonicaKeyConfig(
        key="AB",
        model_image="Ab.png",
        midi_mapping=AB_HARMONICA_MAPPING,
        hole_mapping=AB_MODEL_HOLE_MAPPING,
    ),
    "B": HarmonicaKeyConfig(
        key="B",
        model_image="b.png",
        midi_mapping=B_HARMONICA_MAPPING,
        hole_mapping=B_MODEL_HOLE_MAPPING,
    ),
    "BB": HarmonicaKeyConfig(
        key="BB",
        model_image="Bb.png",
        midi_mapping=BB_HARMONICA_MAPPING,
        hole_mapping=BB_MODEL_HOLE_MAPPING,
    ),
    "C": HarmonicaKeyConfig(
        key="C",
        model_image="c.png",
        midi_mapping=C_HARMONICA_MAPPING,
        hole_mapping=C_NEW_MODEL_HOLE_MAPPING,
    ),
    "CS": HarmonicaKeyConfig(
        key="CS",
        model_image="c#.png",
        midi_mapping=CS_HARMONICA_MAPPING,
        hole_mapping=CS_MODEL_HOLE_MAPPING,
    ),
    "D": HarmonicaKeyConfig(
        key="D",
        model_image="D.png",
        midi_mapping=D_HARMONICA_MAPPING,
        hole_mapping=D_MODEL_HOLE_MAPPING,
    ),
    "E": HarmonicaKeyConfig(
        key="E",
        model_image="E.png",
        midi_mapping=E_HARMONICA_MAPPING,
        hole_mapping=E_MODEL_HOLE_MAPPING,
    ),
    "EB": HarmonicaKeyConfig(
        key="EB",
        model_image="Eb.png",
        midi_mapping=EB_HARMONICA_MAPPING,
        hole_mapping=EB_MODEL_HOLE_MAPPING,
    ),
    "F": HarmonicaKeyConfig(
        key="F",
        model_image="F.png",
        midi_mapping=F_HARMONICA_MAPPING,
        hole_mapping=F_MODEL_HOLE_MAPPING,
    ),
    "FS": HarmonicaKeyConfig(
        key="FS",
        model_image="F#.png",
        midi_mapping=FS_HARMONICA_MAPPING,
        hole_mapping=FS_MODEL_HOLE_MAPPING,
    ),
    "G": HarmonicaKeyConfig(
        key="G",
        model_image="G.png",
        midi_mapping=G_HARMONICA_MAPPING,
        hole_mapping=G_MODEL_HOLE_MAPPING,
    ),
}


def get_harmonica_config(key: str) -> HarmonicaKeyConfig:
    """
    Get configuration for a harmonica key.

    Args:
        key: Harmonica key (case-insensitive, supports common aliases)
            Examples: "C", "g", "D", "F#", "Bb", "Ab", "C#", "Eb"

    Returns:
        HarmonicaKeyConfig for the requested key

    Raises:
        ValueError: If the key is not supported

    Example:
        >>> config = get_harmonica_config("C")
        >>> config.model_image
        'c.png'
        >>> config = get_harmonica_config("F#")  # Alias for FS
        >>> config.key
        'FS'
    """
    key = key.upper()

    # Support common key name aliases
    KEY_ALIASES = {
        "F#": "FS",
        "C#": "CS",
        "AB": "AB",  # Already correct but listed for clarity
        "EB": "EB",  # Already correct but listed for clarity
        "BB": "BB",  # Already correct but listed for clarity
    }

    # Apply alias if it exists
    key = KEY_ALIASES.get(key, key)

    if key not in HARMONICA_KEY_REGISTRY:
        supported_keys = ", ".join(sorted(HARMONICA_KEY_REGISTRY.keys()))
        raise ValueError(
            f"Unsupported harmonica key: {key}. Supported keys: {supported_keys}"
        )

    return HARMONICA_KEY_REGISTRY[key]


def get_supported_keys() -> list[str]:
    """
    Get list of all supported harmonica keys.

    Returns:
        Sorted list of supported key names

    Example:
        >>> get_supported_keys()
        ['C', 'G']
    """
    return sorted(HARMONICA_KEY_REGISTRY.keys())
