import pytest

from eventor_mcp.statistics import assert_date_range_allowed, resolve_date_range, summarize_person_results
from eventor_mcp.xml_parse import parse_eventor_xml


RESULTS_XML = '''<ResultListList><ResultList><Event><EventId>100</EventId><Name>Race A</Name></Event>
<ClassResult><EventClass><EventClassId>10</EventClassId><Name>H21</Name></EventClass>
<PersonResult><PersonId>1</PersonId><Result><ResultPosition>3</ResultPosition><CompetitorStatus value="OK"/></Result>
<RaceResult><EventRaceId>200</EventRaceId><Result><ResultPosition>1</ResultPosition><CompetitorStatus value="OK"/></Result></RaceResult>
</PersonResult></ClassResult></ResultList>
<ResultList><EventId>101</EventId><ClassResult><EventClassId>11</EventClassId>
<PersonResult><PersonId>1</PersonId><Result><CompetitorStatus value="DidNotFinish"/></Result></PersonResult>
</ClassResult></ResultList></ResultListList>'''


def test_schema_shaped_results_preserve_context_and_do_not_double_count_races():
    s = summarize_person_results(parse_eventor_xml(RESULTS_XML), max_events=50)
    assert s["best_position"] == s["worst_position"] == 3
    assert s["events_included"] == 2
    assert s["events"][0] == {"position": 3, "event_id": "100", "event_name": "Race A",
                              "event_class_id": "10", "event_class_name": "H21", "status": "OK"}
    assert s["events"][1]["status"] == "DidNotFinish"
    assert s["events"][1]["position"] is None
    assert s["truncated"] is False


def test_summary_reports_truncation():
    s = summarize_person_results(parse_eventor_xml(RESULTS_XML), max_events=1)
    assert s["events_available"] == 2
    assert s["events_included"] == 1
    assert s["truncated"] is True


@pytest.mark.parametrize("status,position", [("OK", "0"), ("Disqualified", "1"), ("OK", "")])
def test_invalid_finishes_do_not_affect_placement_statistics(status, position):
    xml = RESULTS_XML.replace('<ResultPosition>3</ResultPosition><CompetitorStatus value="OK"/>',
                              f'<ResultPosition>{position}</ResultPosition><CompetitorStatus value="{status}"/>')
    s = summarize_person_results(parse_eventor_xml(xml), max_events=50)
    assert s["events_included"] == 2
    assert s["best_position"] is None


@pytest.mark.parametrize("a,b", [
    ("2020-01-01", "2025-01-01"), ("2025-02-01", "2025-01-01"),
    ("0000-01-01", "2025-01-01"), ("2025-01-01", "2025-01-31 00:00:01"),
])
def test_invalid_or_excessive_ranges(a, b):
    with pytest.raises(ValueError):
        assert_date_range_allowed(a, b, max_days=30)


def test_summary_defaults_work_even_with_small_policy_limit():
    a, b = resolve_date_range(None, None, max_days=7, default_days=365)
    assert_date_range_allowed(a, b, max_days=7)


def test_single_date_bounds():
    assert resolve_date_range("2025-01-01", None, max_days=30) == ("2025-01-01 00:00:00", "2025-01-31 00:00:00")
    assert resolve_date_range(None, "2025-01-31", max_days=30) == ("2025-01-01 00:00:00", "2025-01-31 00:00:00")
