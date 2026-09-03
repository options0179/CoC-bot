import re
from html.parser import HTMLParser

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_BRACKET_RE = re.compile(r"「[^」]*」")


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
        self.scenes: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "p"):
            self._tag = tag
            self._buf = []
        elif tag == "br" and self._tag:
            self._buf.append("\n")

    def handle_data(self, data):
        if self._tag:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag not in ("h1", "h2", "h3", "p"):
            return
        text = "".join(self._buf).strip()
        self._buf = []
        self._tag = None
        if tag == "h1":
            self._part = text
            self._in_narration = False
        elif tag == "h2":
            self.scenes.append({"part": self._part, "scene": text, "lines": []})
            self._in_narration = False
        elif tag == "h3":
            self._in_narration = text.startswith("Keeper")
        elif tag == "p" and self._in_narration and text and self.scenes:
            self.scenes[-1]["lines"].extend(split_sentences(text))


def parse_scenario_html(html: str) -> list[dict]:
    parser = _OutlineParser()
    parser.feed(html)
    return [scene for scene in parser.scenes if scene["lines"]]
