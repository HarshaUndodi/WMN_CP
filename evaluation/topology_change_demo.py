#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
topology_change_demo.py — Demonstrate dynamic topology changes.

Shows how the MCP system detects:
  1. Adding a new router (r5) to the topology
  2. Removing a router (r4) from the topology
  3. System automatically detects changes via polling

Usage:
  python evaluation/topology_change_demo.py
"""

import json
import os
import sys
import time
import copy
from datetime import datetime

# ── Setup paths ───────────────────────────────────────────────
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EVAL_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "server"))

from routing_poller import (
    poll_all_routers,
    poll_routing_table,
    ROUTING_TABLES_JSON,
)

RESULTS_FILE = os.path.join(EVAL_DIR, "topology_change_results.json")


def _load_json():
    """Load current routing_tables.json."""
    with open(ROUTING_TABLES_JSON, "r") as f:
        return json.load(f)


def _save_json(data):
    """Write data back to routing_tables.json."""
    with open(ROUTING_TABLES_JSON, "w") as f:
        json.dump(data, f, indent=2)


def _time_call(func, *args, **kwargs):
    """Call func and return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000  # ms
    return result, round(elapsed, 2)


# ══════════════════════════════════════════════════════════════
# DEMO 1: Adding a Router (r5)
# ══════════════════════════════════════════════════════════════
def demo_add_router(original_data):
    print("\n" + "═" * 65)
    print("  DEMO 1 — Adding Router r5 to the Topology")
    print("═" * 65)

    # Show current state
    _save_json(original_data)
    time.sleep(0.1)
    before = poll_all_routers()
    before_routers = sorted(before.keys())
    before_routes = sum(len(v) for v in before.values())
    print(f"\n  📊 BEFORE: {len(before_routers)} routers ({', '.join(before_routers)})")
    print(f"            {before_routes} total routes")

    # Add router r5 between r3 and r4
    # New topology: r1 — r2 — r3 — r5 — r4 — r1
    # New subnet: r3-r5 = 10.0.5.0/24, r5-r4 = 10.0.6.0/24
    # Remove old r3-r4 link (10.0.3.0/24 stays but routes change)
    data = copy.deepcopy(original_data)

    # Add r5 with its routes
    data["r5"] = [
        {"destination": "10.0.5.0/24", "gateway": "",          "interface": "r5-eth0", "metric": 0},
        {"destination": "10.0.6.0/24", "gateway": "",          "interface": "r5-eth1", "metric": 0},
        {"destination": "10.0.1.0/24", "gateway": "10.0.6.1",  "interface": "r5-eth1", "metric": 0},
        {"destination": "10.0.2.0/24", "gateway": "10.0.5.1",  "interface": "r5-eth0", "metric": 0},
        {"destination": "10.0.3.0/24", "gateway": "10.0.5.1",  "interface": "r5-eth0", "metric": 0},
        {"destination": "10.0.4.0/24", "gateway": "10.0.6.1",  "interface": "r5-eth1", "metric": 0},
    ]

    # Update r3: add route to r5's subnet
    data["r3"].append(
        {"destination": "10.0.5.0/24", "gateway": "", "interface": "r3-eth2", "metric": 0}
    )
    data["r3"].append(
        {"destination": "10.0.6.0/24", "gateway": "10.0.5.2", "interface": "r3-eth2", "metric": 0}
    )

    # Update r4: add route to r5's subnet
    data["r4"].append(
        {"destination": "10.0.6.0/24", "gateway": "", "interface": "r4-eth2", "metric": 0}
    )
    data["r4"].append(
        {"destination": "10.0.5.0/24", "gateway": "10.0.6.2", "interface": "r4-eth2", "metric": 0}
    )

    print(f"\n  💉 Adding router r5 between r3 and r4")
    print(f"     New subnets: 10.0.5.0/24 (r3↔r5), 10.0.6.0/24 (r5↔r4)")

    inject_time = time.perf_counter()
    _save_json(data)

    # Detect the change
    detected = False
    detection_latency = 0
    for attempt in range(20):
        time.sleep(0.25)
        current = poll_all_routers()
        if "r5" in current:
            detection_latency = (time.perf_counter() - inject_time) * 1000
            detected = True
            break

    after = poll_all_routers()
    after_routers = sorted(after.keys())
    after_routes = sum(len(v) for v in after.values())

    print(f"\n  📊 AFTER:  {len(after_routers)} routers ({', '.join(after_routers)})")
    print(f"            {after_routes} total routes")
    print(f"  🔍 Router r5 detected: {'✅ YES' if detected else '❌ NO'}")
    print(f"  ⏱️  Detection latency: {detection_latency:.0f} ms")

    # Show r5's routes
    if "r5" in after:
        print(f"\n  📡 Router r5 routes:")
        for r in after["r5"]:
            gw = f" via {r['gateway']}" if r['gateway'] not in ('directly connected', '') else ""
            print(f"     {r['destination']}{gw} dev {r['interface']}")

    result = {
        "demo": "Add Router r5",
        "routers_before": len(before_routers),
        "routers_after": len(after_routers),
        "routes_before": before_routes,
        "routes_after": after_routes,
        "router_detected": detected,
        "detection_latency_ms": round(detection_latency, 2),
        "status": "PASS" if detected else "FAIL",
    }
    return result


# ══════════════════════════════════════════════════════════════
# DEMO 2: Removing a Router (r4)
# ══════════════════════════════════════════════════════════════
def demo_remove_router(original_data):
    print("\n" + "═" * 65)
    print("  DEMO 2 — Removing Router r4 from the Topology")
    print("═" * 65)

    # Show current state
    _save_json(original_data)
    time.sleep(0.1)
    before = poll_all_routers()
    before_routers = sorted(before.keys())
    before_routes = sum(len(v) for v in before.values())
    print(f"\n  📊 BEFORE: {len(before_routers)} routers ({', '.join(before_routers)})")
    print(f"            {before_routes} total routes")

    # Remove r4 entirely
    data = copy.deepcopy(original_data)
    del data["r4"]

    # Update r1: remove routes via r4 (gateway 10.0.4.1)
    data["r1"] = [r for r in data["r1"] if r.get("gateway") != "10.0.4.1"]
    # Remove r1's direct connection to 10.0.4.0/24
    data["r1"] = [r for r in data["r1"] if r["destination"] != "10.0.4.0/24"]
    # r1 now needs to reach 10.0.3.0/24 via r2 instead
    data["r1"].append(
        {"destination": "10.0.3.0/24", "gateway": "10.0.1.2", "interface": "r1-eth0", "metric": 0}
    )

    # Update r3: remove routes via r4 (gateway 10.0.3.2)
    data["r3"] = [r for r in data["r3"] if r.get("gateway") != "10.0.3.2"]
    # Remove r3's direct connection to 10.0.3.0/24 as a fallback
    # r3 now reaches 10.0.1.0/24 only via r2
    # Add route for 10.0.4.0/24 — no longer reachable (or reroute via r2→r1)
    # For simplicity, 10.0.4.0/24 is no longer in the topology

    print(f"\n  💥 Removing router r4 from topology")
    print(f"     Subnet 10.0.4.0/24 (r4↔r1 link) no longer exists")
    print(f"     Topology becomes: r1 — r2 — r3 (linear)")

    remove_time = time.perf_counter()
    _save_json(data)

    # Detect the removal
    detected = False
    detection_latency = 0
    for attempt in range(20):
        time.sleep(0.25)
        current = poll_all_routers()
        if "r4" not in current:
            detection_latency = (time.perf_counter() - remove_time) * 1000
            detected = True
            break

    after = poll_all_routers()
    after_routers = sorted(after.keys())
    after_routes = sum(len(v) for v in after.values())

    print(f"\n  📊 AFTER:  {len(after_routers)} routers ({', '.join(after_routers)})")
    print(f"            {after_routes} total routes")
    print(f"  🔍 Router r4 removed: {'✅ YES' if detected else '❌ NO'}")
    print(f"  ⏱️  Detection latency: {detection_latency:.0f} ms")

    # Show remaining topology
    print(f"\n  📡 Remaining routers:")
    for rid in sorted(after.keys()):
        routes = after[rid]
        print(f"     {rid}: {len(routes)} routes")
        for r in routes:
            gw = f" via {r['gateway']}" if r['gateway'] not in ('directly connected', '') else ""
            print(f"       {r['destination']}{gw} dev {r['interface']}")

    result = {
        "demo": "Remove Router r4",
        "routers_before": len(before_routers),
        "routers_after": len(after_routers),
        "routes_before": before_routes,
        "routes_after": after_routes,
        "router_removed": detected,
        "detection_latency_ms": round(detection_latency, 2),
        "status": "PASS" if detected else "FAIL",
    }
    return result


# ══════════════════════════════════════════════════════════════
# Connection Architecture Explanation
# ══════════════════════════════════════════════════════════════
def show_connection_architecture():
    print("\n" + "═" * 65)
    print("  MCP CLIENT ↔ SERVER CONNECTION ARCHITECTURE")
    print("═" * 65)
    print("""
  The MCP Client and Server communicate via stdio (standard I/O):

  ┌─────────────────┐   stdin (JSON-RPC)    ┌──────────────────┐
  │   MCP Client     │ ──────────────────►  │   MCP Server      │
  │  (mcp_client.py) │                      │  (mcp_server.py)  │
  │                  │ ◄──────────────────  │                   │
  │  User Interface  │   stdout (JSON-RPC)   │  FastMCP Framework│
  └─────────────────┘                       └────────┬─────────┘
                                                     │
  How it works:                                      │ polls every 5s
  1. Client spawns Server as a subprocess            │
  2. Client sends requests via stdin pipe    ┌───────▼──────────┐
  3. Server processes and responds via       │ Routing Poller    │
     stdout pipe                             │ (routing_poller)  │
  4. Uses JSON-RPC 2.0 message format        │                   │
  5. No network sockets needed — all local   │ Reads:            │
                                             │ routing_tables.json│
  Transport: stdio                           └──────────────────┘
  Protocol:  MCP (Model Context Protocol)
  Format:    JSON-RPC 2.0
  """)


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   MCP Routing — Topology Change Demo                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Show connection architecture first
    show_connection_architecture()

    # Load original data
    original_data = _load_json()
    print(f"📂 Loaded {ROUTING_TABLES_JSON}")
    print(f"   Routers: {', '.join(sorted(original_data.keys()))}")
    total = sum(len(v) for v in original_data.values())
    print(f"   Total routes: {total}")

    results = []

    # Demo 1: Add router
    r1 = demo_add_router(original_data)
    results.append(r1)

    # Restore before demo 2
    _save_json(original_data)
    time.sleep(0.2)

    # Demo 2: Remove router
    r2 = demo_remove_router(original_data)
    results.append(r2)

    # Restore original
    _save_json(original_data)
    print("\n📂 Original routing_tables.json restored.")

    # ── Summary ───────────────────────────────────────────────
    print("\n" + "═" * 65)
    print("  TOPOLOGY CHANGE DEMO — SUMMARY")
    print("═" * 65)
    print(f"  {'Demo':<30} {'Before':>8} {'After':>8} {'Latency':>10} {'Status':>8}")
    print("  " + "─" * 60)
    for r in results:
        name = r["demo"][:29]
        before = f"{r['routers_before']}R"
        after = f"{r['routers_after']}R"
        lat = f"{r['detection_latency_ms']:.0f} ms"
        status = r["status"]
        print(f"  {name:<30} {before:>8} {after:>8} {lat:>10} {status:>8}")
    print("  " + "─" * 60)

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "demos": results,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Results saved to: {RESULTS_FILE}")
    print("✅ Topology change demo complete.")
