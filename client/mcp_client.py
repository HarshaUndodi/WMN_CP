#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
mcp_client.py — Interactive MCP client for the RoutingTableServer.

Connects over stdio transport, lists resources and tools, and provides
an interactive CLI to query routing data from Mininet routers.

CLI Commands
------------
  get routes                  — fetch the live routing table (all routers)
  get router <r1|r2|r3|r4>   — fetch table for a specific router
  detect flaps                — check for route-flap events
  detect loops                — check for routing loops across routers
  compare <ts1> <ts2>         — diff two historical snapshots
  find path <dest>            — best next-hop for a destination prefix
  show topology               — display network topology
  show events                 — show last 10 route-change events
  list resources              — list available MCP resources
  list tools                  — list available MCP tools
  read live                   — read routing://table/live resource
  read topology               — read routing://topology resource
  read router <r1|r2|r3|r4>  — read routing://table/{router_id} resource
  help                        — show available commands
  quit / exit                 — disconnect and exit
"""

import asyncio
import json
import sys
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Path to the MCP server script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_SCRIPT = os.path.join(PROJECT_ROOT, "server", "mcp_server.py")

# Use the venv Python if available, otherwise fall back to system python3
VENV_PYTHON = os.path.join(PROJECT_ROOT, "venv", "bin", "python3")
PYTHON_CMD = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable


def _pretty(data: str) -> str:
    """Try to pretty-print JSON; return as-is on failure."""
    try:
        obj = json.loads(data)
        return json.dumps(obj, indent=2)
    except (json.JSONDecodeError, TypeError):
        return str(data)


async def main():
    """Connect to the MCP server and run the interactive CLI."""
    server_params = StdioServerParameters(
        command=PYTHON_CMD,
        args=[SERVER_SCRIPT],
    )

    print("=" * 60)
    print("  MCP Routing Table Client  (Mininet Integration)")
    print("=" * 60)
    print(f"  Server : {SERVER_SCRIPT}")
    print(f"  Python : {PYTHON_CMD}")
    print()

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session
            await session.initialize()
            print("✅ Connected to RoutingTableServer!\n")

            # List resources
            print("📦 Available Resources:")
            print("-" * 50)
            resources = await session.list_resources()
            for res in resources.resources:
                print(f"  • {res.uri}  —  {res.name}")

            # List resource templates
            res_templates = await session.list_resource_templates()
            for tpl in res_templates.resourceTemplates:
                print(f"  • {tpl.uriTemplate}  —  {tpl.name}")
            print()

            # List tools
            print("🔧 Available Tools:")
            print("-" * 50)
            tools = await session.list_tools()
            for tool in tools.tools:
                desc = (tool.description or "")[:80]
                print(f"  • {tool.name}  —  {desc}")
            print()

            # Interactive loop
            print("Type 'help' for commands, 'quit' to exit.\n")
            while True:
                try:
                    cmd = input("mcp> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    break

                cmd_lower = cmd.lower()
                if not cmd_lower:
                    continue

                # ── help ──────────────────────────────────────────
                if cmd_lower == "help":
                    print("""
┌──────────────────────────────────────────────────────────┐
│               MCP Routing Client — Commands              │
├──────────────────────────────────────────────────────────┤
│  get routes                 — all routers, flat list     │
│  get router <r1|r2|r3|r4>  — specific router table      │
│  detect flaps               — route-flap detection       │
│  detect loops               — routing-loop detection     │
│  compare <ts1> <ts2>        — diff two snapshots         │
│  find path <destination>    — best next-hop lookup       │
│  show topology              — network topology graph     │
│  show events                — recent route-change events │
│  list resources             — list MCP resources         │
│  list tools                 — list MCP tools             │
│  read live                  — read live resource         │
│  read topology              — read topology resource     │
│  read router <r1|r2|r3|r4> — read router resource       │
│  help                       — show this help             │
│  quit / exit                — disconnect and exit        │
└──────────────────────────────────────────────────────────┘
""")

                # ── quit ──────────────────────────────────────────
                elif cmd_lower in ("quit", "exit"):
                    print("Goodbye!")
                    break

                # ── get routes ────────────────────────────────────
                elif cmd_lower == "get routes":
                    print("\n📡 Fetching live routing table (all routers) …")
                    result = await session.call_tool("get_routing_table", {})
                    for content in result.content:
                        print(_pretty(content.text))
                    print()

                # ── get router <id> ───────────────────────────────
                elif cmd_lower.startswith("get router"):
                    parts = cmd.split()
                    if len(parts) < 3:
                        print("Usage: get router <r1|r2|r3|r4>")
                        continue
                    router_id = parts[2]
                    print(f"\n📡 Fetching routing table for {router_id} …")
                    result = await session.call_tool(
                        "get_router_table",
                        {"router_id": router_id},
                    )
                    for content in result.content:
                        print(_pretty(content.text))
                    print()

                # ── detect flaps ──────────────────────────────────
                elif cmd_lower == "detect flaps":
                    print("\n🔍 Detecting route flaps …")
                    result = await session.call_tool("detect_route_flap", {})
                    for content in result.content:
                        print(_pretty(content.text))
                    print()

                # ── detect loops ──────────────────────────────────
                elif cmd_lower == "detect loops":
                    print("\n🔄 Detecting routing loops …")
                    result = await session.call_tool("detect_routing_loops", {})
                    for content in result.content:
                        print(_pretty(content.text))
                    print()

                # ── compare <ts1> <ts2> ───────────────────────────
                elif cmd_lower.startswith("compare"):
                    parts = cmd.split()
                    if len(parts) < 3:
                        print("Usage: compare <timestamp1> <timestamp2>")
                        continue
                    ts1, ts2 = parts[1], parts[2]
                    print(f"\n📊 Comparing snapshots {ts1} ↔ {ts2} …")
                    result = await session.call_tool(
                        "compare_snapshots",
                        {"ts1": ts1, "ts2": ts2},
                    )
                    for content in result.content:
                        print(_pretty(content.text))
                    print()

                # ── find path <dest> ──────────────────────────────
                elif cmd_lower.startswith("find path"):
                    parts = cmd.split()
                    if len(parts) < 3:
                        print("Usage: find path <destination>")
                        continue
                    dest = parts[2]
                    print(f"\n🗺️  Finding best path to {dest} …")
                    result = await session.call_tool(
                        "find_best_path",
                        {"destination": dest},
                    )
                    for content in result.content:
                        print(_pretty(content.text))
                    print()

                # ── show topology ─────────────────────────────────
                elif cmd_lower == "show topology":
                    print("\n🌐 Network Topology:")
                    result = await session.call_tool("get_topology", {})
                    for content in result.content:
                        data = json.loads(content.text)
                        print(f"\n  Type: {data.get('type', 'unknown')}")
                        print(f"  Routers: {', '.join(data.get('routers', []))}")
                        print(f"\n  Links:")
                        for link in data.get("links", []):
                            print(f"    {link['from']} ({link['from_ip']}) ←→ {link['to']} ({link['to_ip']})  subnet: {link['subnet']}")
                    print()

                # ── show events ───────────────────────────────────
                elif cmd_lower == "show events":
                    print("\n📋 Recent Route Events:")
                    result = await session.call_tool("get_route_events", {})
                    for content in result.content:
                        data = json.loads(content.text)
                        print(f"  Total events: {data.get('total_events', 0)}")
                        events = data.get("events", [])
                        if not events:
                            print("  (no events recorded yet)")
                        for evt in events[-10:]:
                            ts = evt.get("timestamp", "?")[:19]
                            etype = evt.get("type", "?")
                            rid = evt.get("router_id", "?")
                            dest = evt.get("destination", "?")
                            if etype == "route_changed":
                                bef = evt.get("before", {}).get("gateway", "?")
                                aft = evt.get("after", {}).get("gateway", "?")
                                print(f"    [{ts}] ⚡ {etype} on {rid}: {dest}  gw {bef} → {aft}")
                            else:
                                print(f"    [{ts}] {'➕' if 'add' in etype else '➖'} {etype} on {rid}: {dest}")
                    print()

                # ── list resources ────────────────────────────────
                elif cmd_lower == "list resources":
                    resources = await session.list_resources()
                    res_templates = await session.list_resource_templates()
                    print("\n📦 Resources:")
                    for res in resources.resources:
                        print(f"  • {res.uri}  —  {res.name}")
                    for tpl in res_templates.resourceTemplates:
                        print(f"  • {tpl.uriTemplate}  —  {tpl.name}")
                    print()

                # ── list tools ────────────────────────────────────
                elif cmd_lower == "list tools":
                    tools = await session.list_tools()
                    print("\n🔧 Tools:")
                    for tool in tools.tools:
                        desc = (tool.description or "")[:80]
                        print(f"  • {tool.name}  —  {desc}")
                    print()

                # ── read live ─────────────────────────────────────
                elif cmd_lower == "read live":
                    print("\n📖 Reading routing://table/live …")
                    result = await session.read_resource("routing://table/live")
                    for content in result.contents:
                        print(_pretty(content.text))
                    print()

                # ── read topology ─────────────────────────────────
                elif cmd_lower == "read topology":
                    print("\n📖 Reading routing://topology …")
                    result = await session.read_resource("routing://topology")
                    for content in result.contents:
                        print(_pretty(content.text))
                    print()

                # ── read router <id> ──────────────────────────────
                elif cmd_lower.startswith("read router"):
                    parts = cmd.split()
                    if len(parts) < 3:
                        print("Usage: read router <r1|r2|r3|r4>")
                        continue
                    router_id = parts[2]
                    print(f"\n📖 Reading routing://table/{router_id} …")
                    result = await session.read_resource(f"routing://table/{router_id}")
                    for content in result.contents:
                        print(_pretty(content.text))
                    print()

                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for options.")


if __name__ == "__main__":
    asyncio.run(main())
