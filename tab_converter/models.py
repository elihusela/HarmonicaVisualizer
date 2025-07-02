from dataclasses import dataclass
from typing import NamedTuple, List


@dataclass
class TabEntry:
    tab: int
    time: float
    duration: float
    confidence: float


@dataclass
class Tabs:
    tabs: List[TabEntry]


class NoteEvent(NamedTuple):
    pitch: int
    start_time: float
    end_time: float
    confidence: float
    activation: List[float]
