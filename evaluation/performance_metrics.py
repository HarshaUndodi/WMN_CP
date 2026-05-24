#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
performance_metrics.py — Benchmark MCP tool response latencies and resource usage.

Runs each tool 10 times, measures avg/min/max latency, CPU%, and memory usage.
Results saved to evaluation/performance_results.json
"""

import json
import os
import sys
import time
import copy
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ── Setup paths ───────────────────────────────────────────────
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EVAL_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "server"))

from routing_poller import (
    poll_all_routers,
    poll_routing_table,
    poll_single_router,
    get_topology,
    ROUTING_TABLES_JSON,
)

RESULTS_FILE = os.path.join(EVAL_DIR, "performance_results.json")
ITERATIONS = 10


# ══════════════════════════════════════════════════════════════
# Tool implementations (direct calls mirroring MCP server)
# ══════════════════════════════════════════════════════════════

def tool_get_routing_table():
    return json.dumps(poll_routing_table(), indent=2)


def tool_detect_route_flap():
    # No real change log in standalone mode → returns no flaps
    return json.dumps({"status": "no route flaps detected"})


def tool_detect_routing_loops():
    all_data = poll_all_routers()
    topo = get_topology()
    ip_to_router = {}
    for link in topo["links"]:
        ip_to_router[link["from_ip"]] = link["from"]
        ip_to_router[link["to_ip"]] = link["to"]
    all_dests = set()
    for routes in all_data.values():
        for r in routes:
            all_dests.add(r["destination"])
    loops = []
    for dest in sorted(all_dests):
        for start in sorted(all_data.keys()):
            visited, current = [], start
            for _ in range(len(all_data) + 1):
                if current in visited:
                    loops.append({"dest": dest, "start": start})
                    break
                visited.append(current)
                matches = [r for r in all_data.get(current, []) if r["destination"] == dest]
                if not matches:
                    break
                gw = matches[0].get("gateway", "")
                if gw in ("directly connected", ""):
                    break
                nxt = ip_to_router.get(gw)
                if not nxt:
                    break
                current = nxt
    return json.dumps({"loops": loops, "count": len(loops)})


def tool_find_best_path():
    table = poll_routing_table()
    dest = "10.0.3.0/24"
    matches = [r for r in table if r["destination"] == dest]
    if matches:
        best = min(matches, key=lambda r: r["metric"])
        return json.dumps({"best": best})
    return json.dumps({"error": "not found"})


def tool_compare_snapshots():
    # Compare two snapshots of the same data (will show no differences)
    snap1 = poll_routing_table()
    time.sleep(0.001)
    snap2 = poll_routing_table()
    map1 = {r["destination"] + r.get("router_id", ""): r for r in snap1}
    map2 = {r["destination"] + r.get("router_id", ""): r for r in snap2}
    changed = sum(1 for k in map1 if k in map2 and map1[k] != map2[k])
    return json.dumps({"changed": changed, "total": len(map1)})


def tool_get_topology():
    return json.dumps(get_topology(), indent=2)


# ══════════════════════════════════════════════════════════════
# Benchmarking
# ══════════════════════════════════════════════════════════════

TOOLS = [
    ("get_routing_table", tool_get_routing_table),
    ("detect_route_flap", tool_detect_route_flap),
    ("detect_routing_loops", tool_detect_routing_loops),
    ("find_best_path", tool_find_best_path),
    ("compare_snapshots", tool_compare_snapshots),
    ("get_topology", tool_get_topology),
]


def benchmark_tool(name: str, func, iterations: int = ITERATIONS) -> dict:
    """Run a tool multiple times and collect metrics."""
    latencies = []
    cpu_samples = []
    mem_samples = []

    proc = psutil.Process(os.getpid()) if HAS_PSUTIL else None

    for i in range(iterations):
        if proc:
            cpu_before = proc.cpu_percent(interval=None)
            mem_before = proc.memory_info().rss / (1024 * 1024)

        start = time.perf_counter()
        _ = func()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        latencies.append(round(elapsed, 3))

        if proc:
            cpu_after = proc.cpu_percent(interval=None)
            mem_after = proc.memory_info().rss / (1024 * 1024)
            cpu_samples.append(round(cpu_after, 1))
            mem_samples.append(round(mem_after, 2))

    result = {
        "tool": name,
        "iterations": iterations,
        "avg_ms": round(sum(latencies) / len(latencies), 3),
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "all_latencies_ms": latencies,
    }

    if cpu_samples:
        result["avg_cpu_pct"] = round(sum(cpu_samples) / len(cpu_samples), 1)
        result["avg_memory_mb"] = round(sum(mem_samples) / len(mem_samples), 2)
    else:
        result["avg_cpu_pct"] = 0.0
        result["avg_memory_mb"] = 0.0

    return result


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   MCP Routing — Performance Benchmarks                  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    if not HAS_PSUTIL:
        print("\n⚠️  psutil not installed — CPU/memory metrics will be 0")
        print("   Install with: pip install psutil\n")

    # Warm up
    print("🔥 Warming up …")
    for _, func in TOOLS:
        func()

    if HAS_PSUTIL:
        proc = psutil.Process(os.getpid())
        proc.cpu_percent(interval=None)  # prime the counter

    # Benchmark each tool
    print(f"\n📊 Running {ITERATIONS} iterations per tool …\n")
    results = []
    for name, func in TOOLS:
        r = benchmark_tool(name, func)
        results.append(r)
        print(f"  ✅ {name:<25} avg={r['avg_ms']:>8.3f} ms  "
              f"min={r['min_ms']:>8.3f}  max={r['max_ms']:>8.3f}  "
              f"CPU={r['avg_cpu_pct']:>5.1f}%  Mem={r['avg_memory_mb']:>6.1f} MB")

    # ── Formatted table ──────────────────────────────────────
    print("\n" + "═" * 78)
    print(f"  {'Tool':<25} {'Avg(ms)':>9} {'Min(ms)':>9} {'Max(ms)':>9} {'CPU%':>7} {'Mem(MB)':>9}")
    print("  " + "─" * 73)
    for r in results:
        print(f"  {r['tool']:<25} {r['avg_ms']:>9.3f} {r['min_ms']:>9.3f} "
              f"{r['max_ms']:>9.3f} {r['avg_cpu_pct']:>6.1f}% {r['avg_memory_mb']:>8.1f}")
    print("  " + "─" * 73)

    # Save
    output = {
        "timestamp": datetime.now().isoformat(),
        "iterations": ITERATIONS,
        "psutil_available": HAS_PSUTIL,
        "tools": results,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Results saved to: {RESULTS_FILE}")
    print("✅ Benchmarks complete.")
