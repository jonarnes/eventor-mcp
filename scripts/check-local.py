"""Check the local stdio launcher and optionally the configured Eventor API key."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import re
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check(live: bool) -> int:
    root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(command=str(root / "scripts" / "run-local.sh"), cwd=tempfile.gettempdir())
    with tempfile.TemporaryFile(mode="w+") as errors:
        try:
            async with stdio_client(params, errlog=errors) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = (await session.list_tools()).tools
                    print(f"Local MCP connected: {len(tools)} tools")
                    if live:
                        result = await session.call_tool("eventor_ping", {})
                        if result.isError:
                            message = result.content[0].text
                            status = re.search(r"HTTP (\d{3})", message)
                            reason = status.group(0) if status else "connection or configuration failed"
                            print(f"Eventor API check failed: {reason}")
                            return 1
                        print("Eventor API check passed (response data withheld)")
        except Exception:
            # Child-process stderr may contain secret-bearing configuration errors.
            print("Local MCP startup failed. Check the venv and .env configuration.")
            return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Also perform one read-only Eventor API request")
    raise SystemExit(asyncio.run(check(parser.parse_args().live)))
