from dataclasses import dataclass
from typing import List


@dataclass
class TabEntry:
    tab: int
    time: float
    duration: float

@dataclass
class Tabs:
    tabs: List[TabEntry]