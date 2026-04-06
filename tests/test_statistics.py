import pytest

from eventor_mcp.statistics import assert_date_range_allowed, summarize_person_results


def test_summarize_person_results_extracts_positions() -> None:
    parsed = {
        "ResultListList": {
            "ResultList": {
                "Result": [
                    {
                        "Position": "3",
                        "EventId": "100",
                        "EventName": "Race A",
                        "EventClassName": "H21",
                    },
                    {
                        "Position": "1",
                        "EventId": "101",
                        "EventName": "Race B",
                        "EventClassName": "H21",
                    },
                ]
            }
        }
    }
    s = summarize_person_results(parsed, max_events=50)
    assert s["best_position"] == 1
    assert s["worst_position"] == 3
    assert s["events_included"] == 2


def test_assert_date_range_allowed_rejects_too_wide() -> None:
    with pytest.raises(ValueError):
        assert_date_range_allowed(
            "2020-01-01 00:00:00",
            "2025-01-01 00:00:00",
            max_days=30,
        )


def test_assert_date_range_allowed_accepts_narrow() -> None:
    assert_date_range_allowed(
        "2025-01-01 00:00:00",
        "2025-01-15 00:00:00",
        max_days=30,
    )
