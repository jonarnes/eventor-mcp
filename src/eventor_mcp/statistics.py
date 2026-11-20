from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _text(value: Any) -> Any:
    return value.get("#text") if isinstance(value, dict) else value


def _parse_int(value: Any) -> int | None:
    try:
        return int(_text(value))
    except (TypeError, ValueError):
        return None


def summarize_person_results(parsed_xml: Any, *, max_events: int) -> dict[str, Any]:
    """Summarize overall person results, without counting individual races twice.

    Eventor ResultList/ClassResult supply the event and class context. RaceResult
    is intentionally excluded: a multi-day event contributes its overall result.
    Results with no position (DNS, DNF, disqualified, unranked) still count.
    """
    rows: list[dict[str, Any]] = []
    root = parsed_xml.get("ResultListList", {}) if isinstance(parsed_xml, dict) else {}
    lists = root.get("ResultList") if isinstance(root, dict) else None
    if lists is None and isinstance(parsed_xml, dict):
        lists = parsed_xml.get("ResultList")
    for result_list in _items(lists):
        event = result_list.get("Event")
        event = event if isinstance(event, dict) else {}
        for class_result in _items(result_list.get("ClassResult")):
            event_class = class_result.get("EventClass")
            event_class = event_class if isinstance(event_class, dict) else {}
            for person_result in _items(class_result.get("PersonResult")):
                result = person_result.get("Result")
                if not isinstance(result, dict):
                    continue
                status = result.get("CompetitorStatus")
                status = status.get("@value") if isinstance(status, dict) else status
                pos = _parse_int(result.get("ResultPosition"))
                # Only ranked, valid finishes contribute to placement statistics.
                if pos is not None and (pos <= 0 or status not in (None, "", "OK", "Finished")):
                    pos = None
                rows.append({
                    "position": pos,
                    "event_id": result_list.get("EventId") or event.get("EventId"),
                    "event_name": event.get("Name"),
                    "event_class_id": class_result.get("EventClassId") or event_class.get("EventClassId"),
                    "event_class_name": event_class.get("Name"),
                    "status": status,
                })
    events = rows[:max_events]
    positions = [row["position"] for row in events if row["position"] is not None]
    return {
        "events_included": len(events),
        "events_available": len(rows),
        "truncated": len(rows) > max_events,
        "best_position": min(positions) if positions else None,
        "worst_position": max(positions) if positions else None,
        "positions_sample": positions[:50],
        "events": events,
    }


def _parse_date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {value!r} (use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")


def assert_date_range_allowed(from_date: str, to_date: str, *, max_days: int) -> None:
    a, b = _parse_date(from_date), _parse_date(to_date)
    if b < a:
        raise ValueError("to_date must be >= from_date")
    if b - a > timedelta(days=max_days):
        raise ValueError(f"Date range exceeds configured maximum ({max_days} days). Narrow from_date/to_date.")


def resolve_date_range(
    from_date: str | None, to_date: str | None, *, max_days: int, default_days: int = 30,
) -> tuple[str, str]:
    """Default to a bounded window ending today, or starting at an explicit from date."""
    span = timedelta(days=min(default_days, max_days))
    if to_date is not None:
        end = _parse_date(to_date)
        start = _parse_date(from_date) if from_date is not None else end - span
    elif from_date is not None:
        start = _parse_date(from_date)
        end = start + span
    else:
        end = datetime.now().replace(microsecond=0)
        start = end - span
    a, b = start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")
    assert_date_range_allowed(a, b, max_days=max_days)
    return a, b
