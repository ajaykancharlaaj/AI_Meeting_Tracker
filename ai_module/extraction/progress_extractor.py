"""
Progress extraction module.
Extracts explicit numerical percentages and normalized qualitative progress labels
from natural language meeting utterances without inventing exact percentages.
"""

from __future__ import annotations
import re
from typing import Optional
from ai_module.schemas.models import ProgressInfo


PERCENT_PATTERN = re.compile(
    r"\b(?P<val>\d{1,3})\s*(?:%|percent)\b",
    re.IGNORECASE,
)

QUALITATIVE_PATTERNS = [
    # completed
    (re.compile(r"\b(completed|finished|done|fully implemented)\b", re.IGNORECASE), "completed", 100, 0.95),
    # almost complete
    (re.compile(r"\b(almost finished|almost completed|almost done|mostly done|nearly done|nearly finished|almost complete)\b", re.IGNORECASE), "almost_complete", None, 0.90),
    # half complete
    (re.compile(r"\b(half completed|halfway done|half done|half finished)\b", re.IGNORECASE), "half_complete", 50, 0.88),
    # in progress / working
    (re.compile(r"\b(still working|currently working|in progress|ongoing|making progress)\b", re.IGNORECASE), "in_progress", None, 0.85),
    # started
    (re.compile(r"\b(just started|started|commenced|kicked off|begun)\b", re.IGNORECASE), "started", None, 0.85),
]


def extract_progress(text: str) -> Optional[ProgressInfo]:
    """
    Extract progress information from an utterance.

    Examples:
        "Authentication functionality is around 50 percent done."
        -> ProgressInfo(progress_value=50, progress_label='50%', progress_type='explicit_percentage', confidence=0.98)

        "The login module is almost finished."
        -> ProgressInfo(progress_value=None, progress_label='almost_complete', progress_type='qualitative', confidence=0.90)
    """
    if not text:
        return None

    # 1. Check for explicit percentage
    match = PERCENT_PATTERN.search(text)
    if match:
        val = int(match.group("val"))
        if 0 <= val <= 100:
            return ProgressInfo(
                progress_value=val,
                progress_label=f"{val}%",
                progress_type="explicit_percentage",
                confidence=0.98,
            )

    # 2. Check qualitative patterns
    for pattern, label, val, conf in QUALITATIVE_PATTERNS:
        if pattern.search(text):
            return ProgressInfo(
                progress_value=val,
                progress_label=label,
                progress_type="qualitative",
                confidence=conf,
            )

    return None
