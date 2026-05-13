"""HTML similarity scoring.

For now this is a structural / token-overlap heuristic — pixel-perfect rendering
requires a headless browser (Playwright/Chromium) which we don't assume is
available in CI. When that gets wired up, replace `score_html_against_reference`
with the rendered-image diff and keep the same signature.
"""

from __future__ import annotations

import re
from collections import Counter

TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)\b")
ATTR = re.compile(r'\b([a-zA-Z-]+)\s*=\s*"[^"]*"')


def _tag_attr_bag(html: str) -> Counter:
    bag: Counter = Counter()
    bag.update(("tag", t.lower()) for t in TAG.findall(html))
    bag.update(("attr", a.lower()) for a in ATTR.findall(html))
    return bag


def _cosine(a: Counter, b: Counter) -> float:
    """Cosine similarity over multiset (Counter) vectors."""
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def score_html_against_reference(generated: str, reference: str) -> float:
    """Score generated HTML against a reference, in [0, 1].

    Currently uses tag/attribute multiset cosine. Replace with rendered
    pixel-diff once a headless renderer is wired in.
    """
    if not reference.strip():
        # No reference available — give a small partial credit if the model
        # at least returned something HTML-shaped.
        return 0.3 if "<" in generated and ">" in generated else 0.0
    return _cosine(_tag_attr_bag(generated), _tag_attr_bag(reference))
