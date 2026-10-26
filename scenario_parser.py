import re
from html.parser import HTMLParser

from sheet_parser import SKILL_NAMES

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_BRACKET_RE = re.compile(r"「[^」]*」")
_CHECK_COLUMNS = ("id", "skill", "action", "success", "failure")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    placeholders = {}

    def _mask(match: re.Match) -> str:
        key = f"\x00{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key

    masked = _BRACKET_RE.sub(_mask, text)
    sentences = []
    for part in _SENTENCE_SPLIT_RE.split(masked):
        part = part.strip()
        if not part:
            continue
        for key, original in placeholders.items():
            part = part.replace(key, original)
        sentences.append(part)
    return sentences


class _OutlineParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._tag = None
        self._buf: list[str] = []
        self._part = None
        self._in_narration = False
        self._in_checks = False
        self._in_table = False
        self._table_headers = False
        self._row: list[str] = []
        self._cell: list[str] | None = None
        self.scenes: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._in_table = True
            self._table_headers = False
        elif self._in_table:
            if tag == "tr":
                self._row = []
            elif tag in ("th", "td") and self._in_checks:
                self._cell = []
            elif tag == "br" and self._cell is not None:
                self._cell.append("\n")
            return
        if tag in ("h1", "h2", "h3", "p"):
            self._tag = tag
            self._buf = []
        elif tag == "br" and self._tag:
            self._buf.append("\n")

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        elif self._tag and not self._in_table:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if self._in_table:
            if tag in ("th", "td") and self._cell is not None:
                self._row.append("".join(self._cell).strip())
                self._cell = None
            elif tag == "tr" and self._in_checks and self.scenes:
                if tuple(self._row) == _CHECK_COLUMNS:
                    self._table_headers = True
                elif self._table_headers and len(self._row) == len(_CHECK_COLUMNS):
                    check = dict(zip(_CHECK_COLUMNS, self._row))
                    checks = self.scenes[-1]["checks"]
                    if (all(check.values()) and check["skill"] in SKILL_NAMES
                            and not any(item["id"] == check["id"] for item in checks)):
                        checks.append(check)
            elif tag == "table":
                self._in_table = False
                self._in_checks = False
            return
        if tag not in ("h1", "h2", "h3", "p"):
            return
        text = "".join(self._buf).strip()
        self._buf = []
        self._tag = None
        if tag == "h1":
            self._part = text
            self._in_narration = False
            self._in_checks = False
        elif tag == "h2":
            self.scenes.append({"part": self._part, "scene": text, "lines": [], "checks": []})
            self._in_narration = False
            self._in_checks = False
        elif tag == "h3":
            self._in_narration = text.startswith("Keeper")
            self._in_checks = text == "Checks"
        elif tag == "p" and self._in_narration and text and self.scenes:
            self.scenes[-1]["lines"].extend(split_sentences(text))


def parse_scenario_html(html: str) -> list[dict]:
    parser = _OutlineParser()
    parser.feed(html)
    return [scene for scene in parser.scenes if scene["lines"]]
