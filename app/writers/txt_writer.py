"""كاتب TXT نظيف: UTF-8 مع BOM (يعمل مع المفكرة وNVDA فورًا) + فواصل صفحات اختيارية."""
from __future__ import annotations


class TxtWriter:
    def __init__(self, path: str, page_markers: bool = False):
        self.path = path
        self.page_markers = page_markers
        self.parts: list[str] = []
        self._last_page = None

    def add_block(self, block: dict):
        prefix = ""
        page = block.get("page")
        if self.page_markers and page is not None and self._last_page is not None and page > self._last_page:
            prefix = "\n\n―――― صفحة {} ――――\n".format(page + 1)
        self.parts.append(prefix + block["text"])
        if page is not None:
            self._last_page = page

    def add_blocks(self, blocks):
        for b in blocks:
            self.add_block(b)

    def save(self):
        text = "\n\n".join(self.parts) + "\n"
        # BOM يجعل المفكرة وقارئ الشاشة يتعرفان على UTF-8 تلقائيًا
        with open(self.path, "w", encoding="utf-8-sig") as f:
            f.write(text)
