import re
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def parse_due_date(text: str, received_at: str) -> Optional[str]:
    """
    Extracts a due date from email text. Returns YYYY-MM-DD or None.
    received_at is the email's received timestamp (ISO 8601).
    Returns None if no specific date found — never guesses.
    """
    if not text or not received_at:
        return None

    try:
        base = datetime.fromisoformat(received_at.replace("Z", "+00:00")).astimezone(IST)
    except Exception:
        base = datetime.now(IST)

    text_lower = text.lower()

    # "tomorrow EOD" / "tomorrow"
    if "tomorrow" in text_lower:
        return (base + timedelta(days=1)).strftime("%Y-%m-%d")

    # "today EOD" / "by today"
    if "today" in text_lower and ("eod" in text_lower or "end of day" in text_lower):
        return base.strftime("%Y-%m-%d")

    # "by Friday" / "this Friday"
    weekdays = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    for i, day in enumerate(weekdays):
        if day in text_lower:
            current_dow = base.weekday()  # 0=Mon
            days_ahead = (i - current_dow) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (base + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # DD-MM-YYYY or DD/MM/YYYY
    match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
    if match:
        try:
            d = datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # "12th August 2026" / "12 Aug 2026" / "11th August"
    months = {
        "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
        "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
    }
    match = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(months.keys()) + r")[a-z]*(?:\s+(\d{4}))?\b",
        text_lower,
    )
    if match:
        try:
            year = int(match.group(3)) if match.group(3) else base.year
            d = datetime(year, months[match.group(2)[:3]], int(match.group(1)))
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        try:
            d = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # "20th" / "the 20th" without month — assume same month as received
    match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\b", text_lower)
    if match:
        day = int(match.group(1))
        if 1 <= day <= 31:
            try:
                d = base.replace(day=day)
                if d < base:
                    # already passed this month — next month
                    if base.month == 12:
                        d = d.replace(year=base.year+1, month=1)
                    else:
                        d = d.replace(month=base.month+1)
                return d.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None


def hours_until_deadline(due_date_str: str, received_at: str) -> Optional[float]:
    """Returns hours between received_at and due_date. Used for 72-hour priority rule."""
    if not due_date_str or not received_at:
        return None
    try:
        base = datetime.fromisoformat(received_at.replace("Z", "+00:00")).astimezone(IST)
        due = datetime.strptime(due_date_str, "%Y-%m-%d").replace(
            hour=23, minute=59, tzinfo=IST
        )
        delta = (due - base).total_seconds() / 3600
        return delta
    except Exception:
        return None
