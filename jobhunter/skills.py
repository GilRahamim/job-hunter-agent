"""Skills vocabulary matcher, shared by the CV heuristic profile and the job pre-score."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

VOCAB_PATH = Path(__file__).with_name("skills_vocab.txt")

# Ambiguous short names: only count them inside a list ("Python, C, SQL"), after
# "and"/"or", or next to the word "language" / "programming".
_AMBIGUOUS = {"C", "R", "Go"}
_HEBREW = re.compile(r"[֐-׿]")
_HEBREW_PREFIX = "[בהולמשכ]?"        # one-letter prefixes attach to Hebrew words (בפייתון)
_LEFT = r"(?<![\w+#.])"
_RIGHT = r"(?![\w+#])"
_LIST_LEFT = r"(?:(?<=[,/|;])|(?<=[,/|;] )|(?<=\band )|(?<=\bor )|(?<=: ))"
_LIST_RIGHT = r"(?=\s*[,/|;)]|\s+(?:language|programming|developer|lang)\b|\s+and\b|\s*$)"


def _alias_pattern(canonical: str, alias: str) -> str:
    escaped = re.escape(alias)
    if canonical in _AMBIGUOUS and alias == canonical:
        return rf"(?:{_LIST_LEFT}{escaped}{_RIGHT}|{_LEFT}{escaped}(?=\s+(?:language|programming)\b))" \
               rf"(?:{_LIST_RIGHT}|)"
    if _HEBREW.search(alias):
        return rf"(?<!\w){_HEBREW_PREFIX}{escaped}(?![\w])"
    return rf"(?i:{_LEFT}{escaped}{_RIGHT})"


@lru_cache(maxsize=1)
def load_vocab(path: Path = VOCAB_PATH) -> list[tuple[str, re.Pattern[str]]]:
    vocab = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        canonical, *aliases = (p.strip() for p in line.split("|"))
        names = [canonical, *[a for a in aliases if a]]
        pattern = "|".join(_alias_pattern(canonical, n) for n in names)
        vocab.append((canonical, re.compile(pattern)))
    return vocab


def extract_skills(text: str) -> list[str]:
    """Canonical skill names found in `text`, in vocabulary order."""
    return [name for name, pattern in load_vocab() if pattern.search(text)]
