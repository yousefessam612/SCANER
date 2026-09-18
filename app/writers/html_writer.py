"""كاتب HTML دلالي: dir/lang لكل عنصر بحسب سكربته — عربي RTL افتراضيًا."""
from __future__ import annotations

import html

from ..core.languages import dominant_script

_LANG = {"ar": "ar", "latin": "en", "none": "en"}
_DIR = {"ar": "rtl", "latin": "ltr", "none": "ltr"}


class HtmlWriter:
    def __init__(self, path: str, title: str = ""):
        self.path = path
        self.title = title
        self.blocks: list[dict] = []

    def add_block(self, block: dict):
        self.blocks.append(block)

    def add_blocks(self, blocks):
        for b in blocks:
            self.add_block(b)

    def save(self):
        doc_dir, doc_lang = _DIR["ar"], "ar"
        if self.blocks:
            dom = dominant_script(" ".join(b["text"] for b in self.blocks))
            doc_dir, doc_lang = _DIR[dom], _LANG[dom]
        out = [
            "<!DOCTYPE html>",
            f'<html lang="{doc_lang}" dir="{doc_dir}">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{html.escape(self.title)}</title>",
            "<style>",
            "body{font-family:'Noto Naskh Arabic','Amiri',serif;line-height:1.9;max-width:52rem;margin:2rem auto;padding:0 1rem;}",
            "h1,h2,h3{line-height:1.4}",
            "</style>",
            "</head>",
            "<body>",
        ]
        i = 0
        blocks = self.blocks
        while i < len(blocks):
            b = blocks[i]
            dom = dominant_script(b["text"])
            d, lg = _DIR[dom], _LANG[dom]
            if b["type"] == "list_item":
                out.append(f'<ul dir="{d}" lang="{lg}">')
                while i < len(blocks) and blocks[i]["type"] == "list_item":
                    dd, ll = _DIR[dominant_script(blocks[i]["text"])], _LANG[dominant_script(blocks[i]["text"])]
                    out.append(f'<li dir="{dd}" lang="{ll}">{html.escape(blocks[i]["text"])}</li>')
                    i += 1
                out.append("</ul>")
                continue
            if b["type"] == "heading":
                out.append(f'<h2 dir="{d}" lang="{lg}">{html.escape(b["text"])}</h2>')
            else:
                out.append(f'<p dir="{d}" lang="{lg}">{html.escape(b["text"])}</p>')
            i += 1
        out += ["</body>", "</html>"]
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
