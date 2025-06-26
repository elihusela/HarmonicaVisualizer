# tab_text_parser.py
from typing import Dict, List


class TabTextParser:
    def __init__(self, file_path: str):
        self.file_path: str = file_path
        self.pages: Dict[str, List[List[List[int]]]] = self._load_and_parse()

    def _load_and_parse(self) -> Dict[str, List[List[List[int]]]]:
        pages: Dict[str, List[List[List[int]]]] = {}
        current_page: str | None = None
        with open(self.file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.lower().startswith("page"):
                    current_page = line.rstrip(":").strip()
                    pages[current_page] = []
                elif current_page and line:
                    pages[current_page].append(self._parse_tab_line(line))
        return pages

    @staticmethod
    def _parse_tab_line(line: str) -> List[List[int]]:
        chords: List[List[int]] = []
        current: List[int] = []
        i: int = 0
        while i < len(line):
            if line[i] == "-":
                j_neg: int = i + 1
                while j_neg < len(line) and line[j_neg].isdigit():
                    j_neg += 1
                neg_digits: str = line[i + 1 : j_neg]
                for d in neg_digits:
                    current.append(-int(d))
                i = j_neg
            elif line[i].isdigit():
                j_pos: int = i
                while j_pos < len(line) and line[j_pos].isdigit():
                    j_pos += 1
                pos_digits: str = line[i:j_pos]
                for d in pos_digits:
                    current.append(int(d))
                i = j_pos
            elif line[i].isspace():
                if current:
                    chords.append(current)
                    current = []
                i += 1
            else:
                i += 1

        if current:
            chords.append(current)

        return chords

    def get_pages(self) -> Dict[str, List[List[List[int]]]]:
        return self.pages
