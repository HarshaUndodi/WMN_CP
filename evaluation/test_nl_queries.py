#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
test_nl_queries.py — Test script for natural language routing analysis queries.
Optimized for CPU-only Ollama inference with pre-fetched context.
"""

import asyncio
import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "client"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from nl_client import (
    PYTHON_CMD, SERVER_SCRIPT, OLLAMA_MODEL,
    query_ollama, build_context,
)

RESULTS_FILE = os.path.join(PROJECT_ROOT, "evaluation", "nl_query_results.json")

QUERIES = [
    "How many routes are there in total?",
    "Which router has the most routes?",
    "What is the best path to reach the default gateway?",
    "Are there any routing loops in the network?",
    "What happened to the routes in the last 5 minutes?",
    "Which interface does r1 use to reach r3?",
    "Is the network topology a ring or a star?",
    "What would happen if the link between r1 and r2 failed?"
]


async def run_tests():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   MCP Routing — Natural Language Interface Tests       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Model: {OLLAMA_MODEL} (CPU-optimized)\n")

    server_params = StdioServerParameters(command=PYTHON_CMD, args=[SERVER_SCRIPT])
    results = []

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Pre-build full context
                print("  📊 Pre-fetching network data...")
                full_context = await build_context(session)
                print("  ✅ MCP Server connected. Running queries...\n")

                for idx, q in enumerate(QUERIES, 1):
                    print(f"[{idx}/8] Q: {q}")

                    start_time = time.perf_counter()
                    try:
                        answer = await query_ollama(q, full_context)
                    except Exception as e:
                        answer = f"Error: {e}"
                    elapsed_ms = (time.perf_counter() - start_time) * 1000

                    display = answer[:300] + "..." if len(answer) > 300 else answer
                    print(f"   A: {display}")
                    print(f"   ⏱ {elapsed_ms:.0f} ms")
                    print("-" * 60)

                    results.append({
                        "query": q,
                        "answer": answer,
                        "latency_ms": round(elapsed_ms, 2)
                    })

        with open(RESULTS_FILE, "w") as f:
            json.dump({"model": OLLAMA_MODEL, "queries": results}, f, indent=2)

        print(f"\n💾 Results saved to: {RESULTS_FILE}")
        print("✅ All NL queries complete.")

    except Exception as e:
        print(f"Fatal test error: {e}")


if __name__ == "__main__":
    asyncio.run(run_tests())
