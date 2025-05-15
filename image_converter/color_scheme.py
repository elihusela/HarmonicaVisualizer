from tab_converter.models import TabEntry
from image_converter.consts import IN_COLOR, OUT_COLOR


class ColorScheme:
    def get_color(self, tab_entry: TabEntry) -> str:
        return OUT_COLOR if tab_entry.tab > 0 else IN_COLOR
