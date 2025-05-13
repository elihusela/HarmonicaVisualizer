import pytest

from image_converter.animator import Animator
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


@pytest.fixture
def dummy_animator(tmp_path) -> Animator:
    image_path = tmp_path / "dummy.png"
    image_path.write_bytes(b"FAKE_IMAGE")  # so Image.open doesn't fail
    output_path = tmp_path / "final.mp4"
    return Animator(str(image_path), str(output_path))
