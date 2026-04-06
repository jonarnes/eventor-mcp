from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from eventor_mcp.config import Settings
from eventor_mcp.http_discovery import register_mcp_discovery_routes
from eventor_mcp.mcp_bearer_auth import http_mcp_auth_from_settings
from eventor_mcp.runtime import get_runtime
from eventor_mcp.statistics import (
    assert_date_range_allowed,
    summarize_person_results,
)

_INSTRUCTIONS = (
    "Read-only tools for Norwegian Eventor (orienteering): organisations, events, entries, "
    "starts, results, and derived summaries. Only HTTP GET is used; nothing is written back to "
    "Eventor. Responses are parsed from Eventor XML into JSON. Access depends on your API key."
)


def _parsed(data: Any) -> dict[str, Any]:
    return {"data": data}


def register_eventor_tools(mcp: FastMCP) -> None:
    """Attach all Eventor tools to a FastMCP instance."""

    @mcp.tool()
    async def eventor_ping() -> dict[str, Any]:
        """Verify the API key and return the organisation linked to it (GET /api/organisation/apiKey)."""

        client = get_runtime().client
        data = await client.get_xml("/api/organisation/apiKey")
        return _parsed(data)

    @mcp.tool()
    async def eventor_list_organisations(include_properties: bool = False) -> dict[str, Any]:
        """List organisations (clubs, regions, federation) (GET /api/organisations)."""

        client = get_runtime().client
        data = await client.get_xml(
            "/api/organisations",
            {"includeProperties": include_properties},
        )
        return _parsed(data)

    @mcp.tool()
    async def eventor_get_organisation(organisation_id: int) -> dict[str, Any]:
        """Get one organisation by id (GET /api/organisation/{id})."""

        client = get_runtime().client
        data = await client.get_xml(f"/api/organisation/{organisation_id}")
        return _parsed(data)

    @mcp.tool()
    async def eventor_list_events(
        from_date: str = "0000-01-01 00:00:00",
        to_date: str = "9999-12-31 23:59:59",
        organisation_ids: str | None = None,
        event_ids: str | None = None,
        classification_ids: str | None = None,
        include_entry_breaks: bool = False,
        include_attributes: bool = False,
    ) -> dict[str, Any]:
        """Search events in a date window (GET /api/events). organisation_ids/event_ids are comma-separated."""

        params: dict[str, Any] = {
            "fromDate": from_date,
            "toDate": to_date,
            "includeEntryBreaks": include_entry_breaks,
            "includeAttributes": include_attributes,
        }
        if organisation_ids:
            params["organisationIds"] = organisation_ids
        if event_ids:
            params["eventIds"] = event_ids
        if classification_ids:
            params["classificationIds"] = classification_ids

        client = get_runtime().client
        data = await client.get_xml("/api/events", params)
        return _parsed(data)

    @mcp.tool()
    async def eventor_get_event(event_id: int) -> dict[str, Any]:
        """Get a single event (GET /api/event/{eventId})."""

        client = get_runtime().client
        data = await client.get_xml(f"/api/event/{event_id}")
        return _parsed(data)

    @mcp.tool()
    async def eventor_list_event_classes(event_id: int, include_entry_fees: bool = False) -> dict[str, Any]:
        """List classes for an event (GET /api/eventclasses)."""

        client = get_runtime().client
        data = await client.get_xml(
            "/api/eventclasses",
            {"eventId": event_id, "includeEntryFees": include_entry_fees},
        )
        return _parsed(data)

    @mcp.tool()
    async def eventor_list_entries(
        organisation_ids: str | None = None,
        event_ids: str | None = None,
        event_class_ids: str | None = None,
        from_event_date: str = "0000-01-01 00:00:00",
        to_event_date: str = "9999-12-31 23:59:59",
        include_entry_fees: bool = False,
        include_person_element: bool = False,
        include_organisation_element: bool = False,
        include_event_element: bool = False,
    ) -> dict[str, Any]:
        """List entries (GET /api/entries). IDs are comma-separated lists."""

        params: dict[str, Any] = {
            "fromEventDate": from_event_date,
            "toEventDate": to_event_date,
            "includeEntryFees": include_entry_fees,
            "includePersonElement": include_person_element,
            "includeOrganisationElement": include_organisation_element,
            "includeEventElement": include_event_element,
        }
        if organisation_ids:
            params["organisationIds"] = organisation_ids
        if event_ids:
            params["eventIds"] = event_ids
        if event_class_ids:
            params["eventClassIds"] = event_class_ids

        client = get_runtime().client
        data = await client.get_xml("/api/entries", params)
        return _parsed(data)

    @mcp.tool()
    async def eventor_competitor_count(
        organisation_ids: str,
        event_ids: str | None = None,
        person_ids: str | None = None,
    ) -> dict[str, Any]:
        """Count entries (GET /api/competitorcount). organisation_ids is required (comma-separated)."""

        params: dict[str, Any] = {"organisationIds": organisation_ids}
        if event_ids:
            params["eventIds"] = event_ids
        if person_ids:
            params["personIds"] = person_ids

        client = get_runtime().client
        data = await client.get_xml("/api/competitorcount", params)
        return _parsed(data)

    @mcp.tool()
    async def eventor_results_event(
        event_id: int,
        include_split_times: bool = False,
        top: int | None = None,
    ) -> dict[str, Any]:
        """Results for an event (GET /api/results/event)."""

        params: dict[str, Any] = {"eventId": event_id, "includeSplitTimes": include_split_times}
        if top is not None:
            params["top"] = top

        client = get_runtime().client
        data = await client.get_xml("/api/results/event", params)
        return _parsed(data)

    @mcp.tool()
    async def eventor_results_person(
        person_id: int,
        from_date: str = "0000-01-01 00:00:00",
        to_date: str = "9999-12-31 23:59:59",
        event_ids: str | None = None,
        include_split_times: bool = False,
        top: int | None = None,
    ) -> dict[str, Any]:
        """Historical results for a person (GET /api/results/person)."""

        params: dict[str, Any] = {
            "personId": person_id,
            "fromDate": from_date,
            "toDate": to_date,
            "includeSplitTimes": include_split_times,
        }
        if event_ids:
            params["eventIds"] = event_ids
        if top is not None:
            params["top"] = top

        client = get_runtime().client
        data = await client.get_xml("/api/results/person", params)
        return _parsed(data)

    @mcp.tool()
    async def eventor_results_organisation(
        organisation_ids: str,
        event_id: int,
        include_split_times: bool = False,
        top: int | None = None,
    ) -> dict[str, Any]:
        """Results for organisations in an event (GET /api/results/organisation)."""

        params: dict[str, Any] = {
            "organisationIds": organisation_ids,
            "eventId": event_id,
            "includeSplitTimes": include_split_times,
        }
        if top is not None:
            params["top"] = top

        client = get_runtime().client
        data = await client.get_xml("/api/results/organisation", params)
        return _parsed(data)

    @mcp.tool()
    async def eventor_starts_event(event_id: int) -> dict[str, Any]:
        """Start list for an event (GET /api/starts/event)."""

        client = get_runtime().client
        data = await client.get_xml("/api/starts/event", {"eventId": event_id})
        return _parsed(data)

    @mcp.tool()
    async def eventor_starts_person(
        person_id: int,
        from_date: str = "0000-01-01 00:00:00",
        to_date: str = "9999-12-31 23:59:59",
        event_ids: str | None = None,
    ) -> dict[str, Any]:
        """Start times for a person (GET /api/starts/person)."""

        params: dict[str, Any] = {
            "personId": person_id,
            "fromDate": from_date,
            "toDate": to_date,
        }
        if event_ids:
            params["eventIds"] = event_ids

        client = get_runtime().client
        data = await client.get_xml("/api/starts/person", params)
        return _parsed(data)

    @mcp.tool()
    async def eventor_starts_organisation(organisation_ids: str, event_id: int) -> dict[str, Any]:
        """Start times for organisations in an event (GET /api/starts/organisation)."""

        client = get_runtime().client
        data = await client.get_xml(
            "/api/starts/organisation",
            {"organisationIds": organisation_ids, "eventId": event_id},
        )
        return _parsed(data)

    @mcp.tool()
    async def eventor_person_results_summary(
        person_id: int,
        from_date: str = "0000-01-01 00:00:00",
        to_date: str = "9999-12-31 23:59:59",
        event_ids: str | None = None,
        include_split_times: bool = False,
        include_raw_data: bool = False,
    ) -> dict[str, Any]:
        """
        Derived summary over historical results for a person (uses GET /api/results/person).
        Enforces a configurable max date range to limit API load. Returns compact stats; optionally includes parsed XML as JSON.
        """

        settings = get_runtime().settings
        assert_date_range_allowed(
            from_date,
            to_date,
            max_days=settings.stats_max_date_range_days,
        )

        params: dict[str, Any] = {
            "personId": person_id,
            "fromDate": from_date,
            "toDate": to_date,
            "includeSplitTimes": include_split_times,
        }
        if event_ids:
            params["eventIds"] = event_ids

        client = get_runtime().client
        parsed = await client.get_xml("/api/results/person", params)
        summary = summarize_person_results(
            parsed,
            max_events=settings.stats_max_events_in_summary,
        )
        out: dict[str, Any] = {"summary": summary}
        if include_raw_data:
            out["data"] = parsed
        return out


def create_mcp(settings: Settings, *, http_auth: bool = False) -> FastMCP:
    """
    Build a FastMCP server instance.

    When ``http_auth`` is True (SSE / streamable-http), optional Bearer auth is enabled if
    ``EVENTOR_MCP_BEARER_TOKEN`` is set. Stdio transport should use ``http_auth=False`` so local
    clients are unaffected by Mistral connector secrets in ``.env``.
    """

    if http_auth:
        auth, verifier = http_mcp_auth_from_settings(settings)
    else:
        auth, verifier = None, None

    mcp = FastMCP(
        "eventor",
        instructions=_INSTRUCTIONS,
        auth=auth,
        token_verifier=verifier,
    )
    register_mcp_discovery_routes(mcp, settings)
    register_eventor_tools(mcp)
    return mcp
