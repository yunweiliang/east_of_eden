"""Load the user's copy of the book and split it into chapters.

The book text never leaves this module except as the prompt sent to the model. It is not written
to any committed file.
"""

from __future__ import annotations

import hashlib
import html
import posixpath
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

CHAPTER_HEADING = re.compile(r"^\s*chapter\s+(\d+|[ivxlc]+)\s*\.?\s*$", re.IGNORECASE | re.MULTILINE)
ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


@dataclass(frozen=True)
class Chapter:
    number: int
    text: str


@dataclass(frozen=True)
class Book:
    chapters: list[Chapter]
    sha256: str

    def chapter(self, number: int) -> Chapter | None:
        return next((c for c in self.chapters if c.number == number), None)


def roman_to_int(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s.lower()):
        value = ROMAN[ch]
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total


def split_chapters(text: str) -> list[Chapter]:
    """Split on 'Chapter N' headings. Front matter before the first heading is dropped."""
    matches = list(CHAPTER_HEADING.finditer(text))
    chapters = []
    for i, m in enumerate(matches):
        raw = m.group(1)
        number = int(raw) if raw.isdigit() else roman_to_int(raw)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if body:
            chapters.append(Chapter(number, body))
    # A table of contents also matches the heading pattern; keep the last (real) copy of each number.
    by_number = {c.number: c for c in chapters}
    return [by_number[n] for n in sorted(by_number)]


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "section", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    return html.unescape("".join(parser.parts))


def epub_to_text(path: Path) -> str:
    """Concatenate the epub's spine documents in reading order."""
    with zipfile.ZipFile(path) as z:
        container = ElementTree.fromstring(z.read("META-INF/container.xml"))
        ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
        opf_path = container.find(".//c:rootfile", ns).get("full-path")
        opf = ElementTree.fromstring(z.read(opf_path))
        opf_ns = {"o": "http://www.idpf.org/2007/opf"}
        manifest = {item.get("id"): item.get("href") for item in opf.findall(".//o:manifest/o:item", opf_ns)}
        base = posixpath.dirname(opf_path)
        docs = []
        for ref in opf.findall(".//o:spine/o:itemref", opf_ns):
            href = manifest[ref.get("idref")]
            docs.append(html_to_text(z.read(posixpath.join(base, href)).decode("utf-8", errors="replace")))
    return "\n".join(docs)


def load_book(path: Path) -> Book:
    if path.suffix.lower() == ".epub":
        text = epub_to_text(path)
    else:
        text = path.read_text(encoding="utf-8")
    text = unicodedata.normalize("NFC", text)
    chapters = split_chapters(text)
    if not chapters:
        raise ValueError(f"No 'Chapter N' headings found in {path}")
    return Book(chapters, hashlib.sha256(text.encode()).hexdigest())


def normalize_for_match(s: str) -> str:
    """Make quote matching robust to curly quotes, dashes, case and line wrapping."""
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "—": "-", "–": "-"}))
    s = s.replace('"', "").replace("'", "")
    return re.sub(r"\s+", " ", s).strip().lower()
