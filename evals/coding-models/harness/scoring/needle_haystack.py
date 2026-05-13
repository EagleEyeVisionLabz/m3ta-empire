"""Needle-in-haystack recall scoring."""

from __future__ import annotations

import re


def score_needle_recall(response: str, expected: str) -> float:
    """Return [0, 1] indicating how well `response` recovers `expected`.

    1.0 means the response is exactly the expected string (modulo whitespace).
    Anything else gets a partial credit based on substring match: 0.5 if the
    expected value is present somewhere in the response, 0.0 otherwise.
    """
    if not expected:
        return 0.0

    normalized = _strip(response)
    target = _strip(expected)
    if normalized == target:
        return 1.0
    if target in normalized:
        return 0.5
    return 0.0


_WHITESPACE = re.compile(r"\s+")


def _strip(text: str) -> str:
    return _WHITESPACE.sub(" ", text.strip().strip('"').strip("'")).strip()
