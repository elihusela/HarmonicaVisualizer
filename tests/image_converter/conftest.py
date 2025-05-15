from unittest.mock import MagicMock

import pytest

from image_converter.animator import Animator
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.models import Tabs, TabEntry


@pytest.fixture
def dummy_tabs() -> Tabs:
    return Tabs(
        [
            TabEntry(tab=1, time=0.0, duration=1.0),  # blow
            TabEntry(tab=-2, time=0.5, duration=1.0),  # draw
            TabEntry(tab=3, time=2.0, duration=0.3),  # future
        ]
    )


@pytest.fixture()
def dummy_harmonica_layout() -> HarmonicaLayout:
    mock = MagicMock(spec=HarmonicaLayout)
    mock.hole_positions = MagicMock()
    return mock


@pytest.fixture()
def dummy_figure_factory() -> FigureFactory:
    return MagicMock(spec=FigureFactory)


@pytest.fixture
def dummy_animator(dummy_harmonica_layout, dummy_figure_factory, tmp_path) -> Animator:
    image_path = tmp_path / "dummy.png"
    image_path.write_bytes(b"FAKE_IMAGE")  # so Image.open doesn't fail
    return Animator(dummy_harmonica_layout, dummy_figure_factory)
