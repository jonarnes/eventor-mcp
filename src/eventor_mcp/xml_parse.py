from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def _strip_tag(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def element_to_structure(elem: ET.Element) -> Any:
    """Convert an XML element to dict/list/str structures."""

    children = list(elem)
    if not children:
        return (elem.text or "").strip()

    out: dict[str, Any] = {}
    for child in children:
        name = _strip_tag(child.tag)
        val = element_to_structure(child)
        if name in out:
            existing = out[name]
            if isinstance(existing, list):
                existing.append(val)
            else:
                out[name] = [existing, val]
        else:
            out[name] = val
    return out


def parse_eventor_xml(xml_text: str) -> Any:
    """Parse Eventor XML response body."""

    text = xml_text.strip()
    if not text:
        return {}
    root = ET.fromstring(text)
    return {_strip_tag(root.tag): element_to_structure(root)}
