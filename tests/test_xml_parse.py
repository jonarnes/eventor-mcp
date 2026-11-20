from eventor_mcp.xml_parse import parse_eventor_xml


def test_parse_simple_list() -> None:
    xml = """
    <EventList>
      <Event>
        <EventId>10</EventId>
        <Name>Test</Name>
      </Event>
    </EventList>
    """
    data = parse_eventor_xml(xml)
    assert "EventList" in data
    inner = data["EventList"]
    assert inner["Event"]["EventId"] == "10"


def test_parse_repeated_sibling_becomes_list() -> None:
    xml = """
    <Root>
      <Item>1</Item>
      <Item>2</Item>
    </Root>
    """
    data = parse_eventor_xml(xml)
    assert data["Root"]["Item"] == ["1", "2"]


def test_preserves_attributes_and_text_without_collisions():
    data = parse_eventor_xml('<Root value="outer"><value>child</value><Status value="OK"/><Amount currency="NOK">100</Amount></Root>')
    assert data == {"Root": {"@value": "outer", "value": "child", "Status": {"@value": "OK"},
                             "Amount": {"@currency": "NOK", "#text": "100"}}}


def test_competitor_count_is_not_lost():
    data = parse_eventor_xml('<CompetitorCountList><CompetitorCount eventId="100" numberOfEntries="42" numberOfStarts="40"/></CompetitorCountList>')
    assert data["CompetitorCountList"]["CompetitorCount"]["@numberOfEntries"] == "42"
    assert data["CompetitorCountList"]["CompetitorCount"]["@numberOfStarts"] == "40"
