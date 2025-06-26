# tab_text_parser.py


class TabTextParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.pages = self._load_and_parse()

    def _load_and_parse(self):
        pages = {}
        current_page = None
        with open(self.file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.lower().startswith("page"):
                    current_page = line.rstrip(":").strip()
                    pages[current_page] = []
                elif current_page and line:
                    pages[current_page].append(self._parse_tab_line(line))
        return pages

    def _parse_tab_line(self, line: str):
        chords = []
        current = []
        i = 0
        while i < len(line):
            if line[i] == "-":
                j = i + 1
                while j < len(line) and line[j].isdigit():
                    j += 1
                note = -int(line[i + 1 : j])
                current.append(note)
                i = j
            elif line[i].isdigit():
                j = i
                while j < len(line) and line[j].isdigit():
                    j += 1
                note = int(line[i:j])
                current.append(note)
                i = j
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

    def get_pages(self):
        return self.pages
