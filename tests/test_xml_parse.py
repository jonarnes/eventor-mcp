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
