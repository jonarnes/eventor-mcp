from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_int(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _collect_result_nodes(data: Any) -> list[dict[str, Any]]:
    """Heuristically collect dict nodes that look like a single result row."""

    candidates: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            keys = {str(k) for k in node.keys()}
            if "Position" in keys or "ClassPosition" in keys:
                candidates.append(node)
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(data)
    return candidates


def summarize_person_results(
    parsed_xml: Any,
    *,
    max_events: int,
) -> dict[str, Any]:
    """
    Build a compact summary from /api/results/person parsed XML.
    Field names vary; we extract common keys when present.
    """

    rows = _collect_result_nodes(parsed_xml)
    events: list[dict[str, Any]] = []
    positions: list[int] = []

    for row in rows[:max_events]:
        pos = _parse_int(row.get("Position")) or _parse_int(row.get("ClassPosition"))
        if pos is not None:
            positions.append(pos)
        events.append(
            {
                "position": pos,
                "event_id": row.get("EventId") or row.get("EventID"),
                "event_name": row.get("EventName") or row.get("Name"),
                "event_class_name": row.get("EventClassName") or row.get("ClassName"),
                "status": row.get("CompetitorStatus") or row.get("Status"),
            }
        )

    best = min(positions) if positions else None
    worst = max(positions) if positions else None

    return {
        "events_included": len(events),
        "best_position": best,
        "worst_position": worst,
        "positions_sample": positions[:50],
        "events": events,
    }


def assert_date_range_allowed(
    from_date: str,
    to_date: str,
    *,
    max_days: int,
) -> None:
    """Raise ValueError if span exceeds policy (reduces API load)."""

    def _parse(dt: str) -> datetime:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(dt.strip(), fmt)
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: {dt!r} (use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")

    a = _parse(from_date)
    b = _parse(to_date)
    if b < a:
        raise ValueError("to_date must be >= from_date")
    if (b - a).days > max_days:
        raise ValueError(
            f"Date range exceeds STATS_MAX_DATE_RANGE_DAYS ({max_days} days). "
            "Narrow from_date/to_date or raise the limit in configuration."
        )
