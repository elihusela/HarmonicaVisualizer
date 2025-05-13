import pytest
from tab_converter.tab_mapper import TabMapper


@pytest.fixture
def simple_mapping() -> dict[int, int]:
    return {60: 1, 62: -1, 64: 2}  # C  # D  # E


@pytest.fixture
def tab_mapper(simple_mapping, tmp_path) -> TabMapper:
    output_path = tmp_path.as_posix() + "/"
    return TabMapper(harmonica_mapping=simple_mapping, json_outputs_path=output_path)
