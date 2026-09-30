"""
Deadline normalization and intelligence module.
Converts natural language deadlines (explicit, relative, weekdays) into YYYY-MM-DD
and detects changes in deadlines across meetings.
"""

from __future__ import annotations
from datetime import datetime, timedelta
import re
from typing import Optional, Dict, Any


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def normalize_deadline(
    deadline_text: str | None,
    reference_date: str
) -> str | None:
    """
    Convert common natural-language deadlines into YYYY-MM-DD format.

    reference_date (YYYY-MM-DD) is used for relative dates such as
    'today', 'tomorrow', 'Friday', etc.
    """
    if not deadline_text:
        return None

    text = deadline_text.lower().strip()

    try:
        reference = datetime.strptime(reference_date, "%Y-%m-%d")
    except Exception:
        reference = datetime.now()

    # Direct ISO date YYYY-MM-DD check
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if iso_match:
        return iso_match.group(1)

    # Today
    if "today" in text:
        return reference.strftime("%Y-%m-%d")

    # Day after tomorrow
    if "day after tomorrow" in text:
        day_after = reference + timedelta(days=2)
        return day_after.strftime("%Y-%m-%d")

    # Tomorrow
    if "tomorrow" in text:
        tomorrow = reference + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")

    # Explicit date: "September 18", "Friday, September 18"
    month_match = re.search(
        r"(january|february|march|april|may|june|july|"
        r"august|september|october|november|december)"
        r"\s+(\d{1,2})",
        text
    )
    if month_match:
        month = month_match.group(1)
        day = int(month_match.group(2))
        month_number = datetime.strptime(month, "%B").month
        year = reference.year
        result = datetime(year, month_number, day)
        return result.strftime("%Y-%m-%d")

    # Relative weekday: "Friday", "by next Monday", "next Friday"
    is_next_week = "next" in text
    for day_name, day_idx in WEEKDAYS.items():
        if day_name in text:
            curr_idx = reference.weekday()
            days_ahead = day_idx - curr_idx
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            if is_next_week and days_ahead < 7:
                days_ahead += 7
            target_date = reference + timedelta(days=days_ahead)
            return target_date.strftime("%Y-%m-%d")

    # In N days
    in_days_match = re.search(r"in\s+(\d+)\s+days?", text)
    if in_days_match:
        days = int(in_days_match.group(1))
        return (reference + timedelta(days=days)).strftime("%Y-%m-%d")

    return None


def detect_deadline_change(text: str) -> bool:
    """
    Detect whether the speaker is modifying/moving an existing deadline.
    Examples:
        "Deadline moved to Monday"
        "Pushed the deadline to Friday"
        "We extended the deadline"
    """
    pattern = r"\b(moved to|pushed to|extended to|postponed to|rescheduled to|delayed to|changed to)\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def extract_deadline_info(text: str, reference_date: str) -> Dict[str, Any]:
    """
    Extract deadline and determine if it represents a deadline modification.
    """
    normalized = normalize_deadline(text, reference_date)
    is_change = detect_deadline_change(text)
    return {
        "deadline": normalized,
        "is_changed": is_change,
        "change_type": "deadline_changed" if is_change else "initial",
        "confidence": 0.95 if normalized else 0.0,
    }