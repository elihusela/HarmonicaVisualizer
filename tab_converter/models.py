from dataclasses import dataclass
from typing import NamedTuple, List


@dataclass
class TabEntry:
    tab: int
    time: float
    duration: float
    confidence: float
    is_bend: bool = False


@dataclass
class Tabs:
    tabs: List[TabEntry]


class NoteEvent(NamedTuple):
    start_time: float
    end_time: float
    pitch: int
    confidence: float
    activation: List[float]
