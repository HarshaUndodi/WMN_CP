#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
nl_client.py — Natural Language Interface using Ollama and MCP.

Optimized for CPU-only inference: uses the 1B model with compact context,
pre-fetches all MCP tool results so the LLM never needs to make tool calls
(single-shot answer = fastest possible response).
"""

import asyncio
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ── Configuration ─────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_SCRIPT = os.path.join(PROJECT_ROOT, "server", "mcp_server.py")
VENV_PYTHON = os.path.join(PROJECT_ROOT, "venv", "bin", "python3")
PYTHON_CMD = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

OLLAMA_MODEL = "llama3.2:1b"   # 1B params — fast on CPU
OLLAMA_OPTIONS = {
    "num_predict": 256,        # limit response length
    "num_ctx": 2048,           # smaller context window
    "temperature": 0.3,        # deterministic answers
}

# Thread pool for running sync ollama calls from async context
_executor = ThreadPoolExecutor(max_workers=1)


def summarize_routes(raw_json: str) -> str:
    """Convert verbose route JSON into a compact text summary for the LLM."""
    try:
        routes = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return raw_json[:500]

    by_router = {}
    for r in routes:
        rid = r.get("router_id", "?")
        by_router.setdefault(rid, []).append(r)

    lines = [f"Network: 4 routers (r1-r4) in ring topology, {len(routes)} total routes."]
    lines.append("Topology: r1↔r2↔r3↔r4↔r1 (ring)")
    lines.append("")
    for rid in sorted(by_router):
        entries = by_router[rid]
        lines.append(f"  {rid} ({len(entries)} routes):")
        for e in entries:
            gw = e.get("gateway", "?")
            dst = e.get("destination", "?")
            iface = e.get("interface", "?")
            lines.append(f"    {dst} → {gw} via {iface}")
    return "\n".join(lines)


def _ollama_chat(system_prompt: str, user_question: str) -> str:
    """Synchronous Ollama chat call (runs in thread pool)."""
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
            ],
            options=OLLAMA_OPTIONS,
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error communicating with Ollama: {e}"


async def query_ollama(user_question: str, full_context: str) -> str:
    """Send user question + pre-built context to Ollama in a background thread."""
    system_prompt = (
        "You are a concise network analysis assistant for a Mininet network "
        "with 4 routers (r1, r2, r3, r4) in a ring topology.\n"
        "Answer the user's question using ONLY the data below.\n"
        "Be brief: 1-4 sentences max.\n\n"
        f"{full_context}"
    )

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _ollama_chat, system_prompt, user_question
    )


async def build_context(session) -> str:
    """Pre-fetch all MCP tool results and build a single compact context string."""
    sections = []

    # 1. Routing table (summarized)
    try:
        res = await session.call_tool("get_routing_table", {})
        raw = "\n".join(c.text for c in res.content)
        sections.append("ROUTING TABLE:\n" + summarize_routes(raw))
    except Exception:
        sections.append("ROUTING TABLE: unavailable")

    # 2. Loop detection
    try:
        res = await session.call_tool("detect_routing_loops", {})
        text = "\n".join(c.text for c in res.content)
        # Parse and compact
        try:
            data = json.loads(text)
            sections.append(f"LOOP CHECK: {data.get('status', text)}")
        except json.JSONDecodeError:
            sections.append(f"LOOP CHECK: {text[:200]}")
    except Exception:
        sections.append("LOOP CHECK: unavailable")

    # 3. Flap detection
    try:
        res = await session.call_tool("detect_route_flap", {})
        text = "\n".join(c.text for c in res.content)
        try:
            data = json.loads(text)
            sections.append(f"FLAP CHECK: {data.get('status', text)}")
        except json.JSONDecodeError:
            sections.append(f"FLAP CHECK: {text[:200]}")
    except Exception:
        sections.append("FLAP CHECK: unavailable")

    # 4. Topology
    try:
        res = await session.call_tool("get_topology", {})
        text = "\n".join(c.text for c in res.content)
        try:
            data = json.loads(text)
            topo_type = data.get("type", "ring")
            routers = data.get("routers", [])
            links_info = []
            for link in data.get("links", []):
                links_info.append(f"{link.get('from','')}↔{link.get('to','')} ({link.get('subnet','')})")
            sections.append(f"TOPOLOGY: {topo_type}, routers={routers}, links: {', '.join(links_info)}")
        except json.JSONDecodeError:
            sections.append(f"TOPOLOGY: {text[:200]}")
    except Exception:
        sections.append("TOPOLOGY: unavailable")

    # 5. Recent events
    try:
        res = await session.call_tool("get_route_events", {})
        text = "\n".join(c.text for c in res.content)
        try:
            events = json.loads(text)
            if isinstance(events, list):
                recent = events[:5]
                evt_lines = [f"  {e.get('type','?')} {e.get('router_id','?')}: {e.get('destination','?')}" for e in recent]
                sections.append(f"RECENT EVENTS ({len(events)} total):\n" + "\n".join(evt_lines))
            else:
                sections.append(f"RECENT EVENTS: {text[:200]}")
        except json.JSONDecodeError:
            sections.append(f"RECENT EVENTS: {text[:200]}")
    except Exception:
        sections.append("RECENT EVENTS: unavailable")

    return "\n\n".join(sections)


async def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🌐 WMN Routing Assistant (Powered by Ollama + MCP)    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print(f"  Model: {OLLAMA_MODEL} (optimized for CPU)")
    print("  Initializing MCP server connection...")

    try:
        async with stdio_client(StdioServerParameters(command=PYTHON_CMD, args=[SERVER_SCRIPT])) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Fetch tools list for display
                tools = await session.list_tools()
                tools_list = "\n".join(f"  • {t.name}: {t.description}" for t in tools.tools)

                # Pre-build full context from all MCP tools
                print("  📊 Pre-fetching network data...")
                full_context = await build_context(session)

                print("  ✅ Ready!")
                print()
                print("  Commands: 'quit' | 'tools' | 'context' | 'refresh'")
                print("─" * 60)

                while True:
                    try:
                        user_question = input("\n🔹 Ask > ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nGoodbye!")
                        break

                    if not user_question:
                        continue

                    if user_question.lower() in ('quit', 'exit'):
                        print("Goodbye!")
                        break

                    if user_question.lower() == 'tools':
                        print(f"\n🔧 Available MCP Tools:\n{tools_list}")
                        continue

                    if user_question.lower() == 'context':
                        print(f"\n📊 Current Context:\n{full_context}")
                        continue

                    if user_question.lower() == 'refresh':
                        print("🔄 Refreshing network data...")
                        full_context = await build_context(session)
                        print("  ✅ Context refreshed!")
                        continue

                    print("🤔 Thinking...", end=" ", flush=True)
                    start = time.perf_counter()
                    answer = await query_ollama(user_question, full_context)
                    elapsed = time.perf_counter() - start
                    print(f"({elapsed:.1f}s)")
                    print(f"\n🤖 {answer}")

    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
