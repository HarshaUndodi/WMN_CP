#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
mcp_server.py — FastMCP server exposing routing-table resources & tools.

Resources
---------
routing://table/live                → current (latest) routing snapshot (all routers)
routing://table/history/{timestamp} → historical snapshot by timestamp
routing://table/{router_id}         → routing table for a specific router (r1–r4)
routing://topology                  → full network topology as JSON

Tools
-----
get_routing_table()                 → live routing table (all routers, flat list)
get_router_table(router_id)         → routing table for a specific router
detect_route_flap()                 → routes that changed >3× in 60 s
compare_snapshots(ts1, ts2)         → diff two historical snapshots
find_best_path(destination)         → best next-hop for a destination prefix
detect_routing_loops()              → check for routing loops across routers
get_topology()                      → return the network topology graph
get_route_events()                  → return the last route-change events

The server polls every 5 seconds and stores snapshots keyed by timestamps.
"""

import asyncio
import json
import sys
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

# ── make sibling module importable ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from routing_poller import (  # noqa: E402
    poll_routing_table,
    poll_all_routers,
    poll_single_router,
    get_topology as poller_get_topology,
    get_data_source_info,
)

# ═══════════════════════════════════════════════════════════════════════════
# In-memory stores
# ═══════════════════════════════════════════════════════════════════════════

# Snapshot store: { iso_timestamp: { "r1": [...], "r2": [...], ... } }
snapshots: dict[str, dict[str, list[dict]]] = {}

# Flat snapshot store (backward compat): { iso_timestamp: [ {route}, ... ] }
flat_snapshots: dict[str, list[dict]] = {}

# Change log for flap detection: { (router_id, destination): [ts_float, …] }
change_log: dict[tuple[str, str], list[float]] = defaultdict(list)

# Route events: list of dicts recording every route change
route_events: list[dict] = []

POLL_INTERVAL = 5  # seconds
MAX_EVENTS = 200   # max route events to keep


# ═══════════════════════════════════════════════════════════════════════════
# Lifespan — start/stop the background poller
# ═══════════════════════════════════════════════════════════════════════════
@lifespan
async def app_lifespan(server):
    """Start the background poller when the server boots."""
    print("🚀 RoutingTableServer lifespan: starting background poller …", file=sys.stderr)

    # Seed initial snapshot
    initial = poll_all_routers()
    ts_key = datetime.now().isoformat()
    snapshots[ts_key] = initial
    flat_snapshots[ts_key] = poll_routing_table()

    total = sum(len(v) for v in initial.values())
    routers = list(initial.keys())
    src = get_data_source_info()
    print(f"   ✅ Initial snapshot: {len(routers)} routers, {total} routes", file=sys.stderr)
    print(f"   📂 Source: json_exists={src['json_exists']}, fresh={src['json_fresh']}", file=sys.stderr)

    task = asyncio.create_task(_background_poller())
    try:
        yield {}
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        print("🛑 Background poller stopped.", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# Server setup
# ═══════════════════════════════════════════════════════════════════════════
mcp = FastMCP("RoutingTableServer", lifespan=app_lifespan)


# ═══════════════════════════════════════════════════════════════════════════
# Background poller
# ═══════════════════════════════════════════════════════════════════════════
async def _background_poller():
    """Poll routing tables every POLL_INTERVAL seconds."""
    previous: dict[str, list[dict]] = {}
    while True:
        try:
            current = poll_all_routers()
            ts_key = datetime.now().isoformat()
            now_ts = time.time()

            snapshots[ts_key] = current
            flat_snapshots[ts_key] = poll_routing_table()

            # ── Detect changes per router ─────────────────────────
            for router_id, routes in current.items():
                prev_routes = previous.get(router_id, [])
                prev_map = {r["destination"]: r for r in prev_routes}

                for route in routes:
                    dest = route["destination"]
                    key = (router_id, dest)

                    if dest in prev_map:
                        old = prev_map[dest]
                        # Compare gateway/interface/metric (ignore timestamp)
                        changed = (
                            old.get("gateway") != route.get("gateway")
                            or old.get("interface") != route.get("interface")
                            or old.get("metric") != route.get("metric")
                        )
                        if changed:
                            change_log[key].append(now_ts)
                            route_events.append({
                                "type": "route_changed",
                                "timestamp": ts_key,
                                "router_id": router_id,
                                "destination": dest,
                                "before": {
                                    "gateway": old.get("gateway", ""),
                                    "interface": old.get("interface", ""),
                                    "metric": old.get("metric", 0),
                                },
                                "after": {
                                    "gateway": route.get("gateway", ""),
                                    "interface": route.get("interface", ""),
                                    "metric": route.get("metric", 0),
                                },
                            })

                # Detect added routes
                curr_dests = {r["destination"] for r in routes}
                prev_dests = {r["destination"] for r in prev_routes}
                for dest in curr_dests - prev_dests:
                    route_events.append({
                        "type": "route_added",
                        "timestamp": ts_key,
                        "router_id": router_id,
                        "destination": dest,
                    })
                for dest in prev_dests - curr_dests:
                    route_events.append({
                        "type": "route_removed",
                        "timestamp": ts_key,
                        "router_id": router_id,
                        "destination": dest,
                    })

            previous = current

            # Prune old data
            cutoff = now_ts - 120
            for key in list(change_log.keys()):
                change_log[key] = [t for t in change_log[key] if t > cutoff]
                if not change_log[key]:
                    del change_log[key]

            # Cap events list
            if len(route_events) > MAX_EVENTS:
                del route_events[:len(route_events) - MAX_EVENTS]

        except Exception as exc:
            print(f"[poller] error: {exc}", file=sys.stderr)

        await asyncio.sleep(POLL_INTERVAL)


# ═══════════════════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════════════════
@mcp.resource("routing://table/live")
def routing_table_live() -> str:
    """Return the most recent routing-table snapshot (all routers) as JSON."""
    if not snapshots:
        return json.dumps({"status": "no data yet", "routers": {}})
    latest_key = max(snapshots.keys())
    return json.dumps({
        "timestamp": latest_key,
        "source": get_data_source_info(),
        "routers": snapshots[latest_key],
    }, indent=2)


@mcp.resource("routing://table/history/{timestamp}")
def routing_table_history(timestamp: str) -> str:
    """Return a historical routing-table snapshot by timestamp."""
    if timestamp in snapshots:
        return json.dumps({
            "timestamp": timestamp,
            "routers": snapshots[timestamp],
        }, indent=2)
    for key in sorted(snapshots.keys(), reverse=True):
        if key.startswith(timestamp):
            return json.dumps({
                "timestamp": key,
                "routers": snapshots[key],
            }, indent=2)
    return json.dumps({
        "error": "snapshot not found",
        "available_timestamps": sorted(snapshots.keys())[-10:],
    }, indent=2)


@mcp.resource("routing://table/{router_id}")
def routing_table_router(router_id: str) -> str:
    """Return the latest routing table for a specific router (r1, r2, r3, r4)."""
    if not snapshots:
        return json.dumps({"error": "no data yet"})
    latest_key = max(snapshots.keys())
    latest = snapshots[latest_key]
    if router_id in latest:
        return json.dumps({
            "timestamp": latest_key,
            "router_id": router_id,
            "routes": latest[router_id],
        }, indent=2)
    return json.dumps({
        "error": f"router '{router_id}' not found",
        "available_routers": list(latest.keys()),
    }, indent=2)


@mcp.resource("routing://topology")
def routing_topology() -> str:
    """Return the full network topology as JSON."""
    topo = poller_get_topology()
    return json.dumps(topo, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def get_routing_table() -> str:
    """Return the live routing table (all routers) as a JSON list."""
    table = poll_routing_table()
    return json.dumps(table, indent=2)


@mcp.tool()
def get_router_table(router_id: str) -> str:
    """Fetch the routing table for a specific router.

    Parameters
    ----------
    router_id : str
        Router identifier, e.g. 'r1', 'r2', 'r3', or 'r4'.
    """
    routes = poll_single_router(router_id)
    if not routes:
        all_data = poll_all_routers()
        return json.dumps({
            "error": f"router '{router_id}' not found",
            "available_routers": list(all_data.keys()),
        })
    return json.dumps({
        "router_id": router_id,
        "route_count": len(routes),
        "routes": routes,
    }, indent=2)


@mcp.tool()
def detect_route_flap() -> str:
    """Detect routes that changed more than 3 times in the last 60 seconds."""
    cutoff = time.time() - 60
    flaps: list[dict] = []
    for (router_id, dest), timestamps in change_log.items():
        recent = [t for t in timestamps if t > cutoff]
        if len(recent) > 3:
            flaps.append({
                "router_id": router_id,
                "destination": dest,
                "changes_in_last_60s": len(recent),
                "timestamps": [datetime.fromtimestamp(t).isoformat() for t in recent],
            })
    if not flaps:
        return json.dumps({"status": "no route flaps detected"})
    return json.dumps({"flaps": flaps}, indent=2)


@mcp.tool()
def compare_snapshots(ts1: str, ts2: str) -> str:
    """Compare two routing-table snapshots and return the differences.

    Parameters
    ----------
    ts1 : str
        Timestamp (or prefix) of the first snapshot.
    ts2 : str
        Timestamp (or prefix) of the second snapshot.
    """
    def _find(ts: str):
        if ts in flat_snapshots:
            return ts, flat_snapshots[ts]
        for key in sorted(flat_snapshots.keys()):
            if key.startswith(ts):
                return key, flat_snapshots[key]
        return None, []

    key1, snap1 = _find(ts1)
    key2, snap2 = _find(ts2)

    if key1 is None or key2 is None:
        return json.dumps({
            "error": "one or both snapshots not found",
            "available_timestamps": sorted(flat_snapshots.keys())[-10:],
        }, indent=2)

    # Build composite keys (router_id + destination)
    def _make_key(r):
        return (r.get("router_id", ""), r["destination"])

    map1 = {_make_key(r): r for r in snap1}
    map2 = {_make_key(r): r for r in snap2}
    all_keys = sorted(set(map1.keys()) | set(map2.keys()))

    added, removed, changed = [], [], []
    for k in all_keys:
        if k not in map1:
            added.append(map2[k])
        elif k not in map2:
            removed.append(map1[k])
        elif map1[k] != map2[k]:
            changed.append({"key": f"{k[0]}:{k[1]}", "before": map1[k], "after": map2[k]})

    return json.dumps({
        "snapshot_1": key1,
        "snapshot_2": key2,
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": len(all_keys) - len(added) - len(removed) - len(changed),
    }, indent=2)


@mcp.tool()
def find_best_path(destination: str) -> str:
    """Find the best (lowest metric) next-hop for a given destination prefix.

    Parameters
    ----------
    destination : str
        The destination network prefix, e.g. '10.0.1.0/24'.
    """
    table = poll_routing_table()
    matches = [r for r in table if r["destination"] == destination]
    if not matches:
        matches = [r for r in table if destination in r["destination"]]
    if not matches:
        return json.dumps({
            "error": f"no route found for '{destination}'",
            "available_destinations": sorted(set(r["destination"] for r in table)),
        })

    best = min(matches, key=lambda r: r["metric"])
    return json.dumps({
        "destination": destination,
        "best_route": best,
        "all_matches": matches,
    }, indent=2)


@mcp.tool()
def detect_routing_loops() -> str:
    """Check if any route creates a cycle in the next-hop chain across routers.

    Traces the forwarding path for each destination across routers.
    If a router is visited twice, a loop is detected.
    """
    all_data = poll_all_routers()
    topo = poller_get_topology()

    # Build IP → router mapping from topology links
    ip_to_router: dict[str, str] = {}
    for link in topo["links"]:
        ip_to_router[link["from_ip"]] = link["from"]
        ip_to_router[link["to_ip"]] = link["to"]

    # Collect all unique destinations across all routers
    all_dests = set()
    for routes in all_data.values():
        for r in routes:
            all_dests.add(r["destination"])

    loops: list[dict] = []
    loop_free: list[str] = []

    for dest in sorted(all_dests):
        # For each router, trace the forwarding path
        for start_router in sorted(all_data.keys()):
            visited = []
            current_router = start_router
            has_loop = False

            for _ in range(len(all_data) + 1):
                if current_router in visited:
                    has_loop = True
                    break
                visited.append(current_router)

                # Find route for this destination on current router
                router_routes = all_data.get(current_router, [])
                matching = [r for r in router_routes if r["destination"] == dest]
                if not matching:
                    break

                route = matching[0]
                gw = route.get("gateway", "")
                if gw in ("directly connected", ""):
                    break  # Directly connected — no forwarding

                # Find which router the gateway belongs to
                next_router = ip_to_router.get(gw)
                if not next_router:
                    break  # Unknown gateway
                current_router = next_router

            if has_loop:
                loops.append({
                    "destination": dest,
                    "start_router": start_router,
                    "path": visited + [current_router],
                    "loop_at": current_router,
                })

    if not loops:
        return json.dumps({
            "status": "no routing loops detected",
            "routers_checked": sorted(all_data.keys()),
            "destinations_checked": len(all_dests),
        })
    return json.dumps({
        "loops_detected": len(loops),
        "loops": loops,
    }, indent=2)


@mcp.tool()
def get_topology() -> str:
    """Return the network topology graph (routers, links, subnets)."""
    topo = poller_get_topology()
    return json.dumps(topo, indent=2)


@mcp.tool()
def get_route_events() -> str:
    """Return the last route-change events (max 20 most recent)."""
    recent = route_events[-20:]
    return json.dumps({
        "total_events": len(route_events),
        "showing": len(recent),
        "events": recent,
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# Main — run server on stdio
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🚀 RoutingTableServer starting on stdio transport …", file=sys.stderr)
    mcp.run(transport="stdio")
