#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
route_visualizer.py — Visualize the Mininet ring topology using networkx + matplotlib.

Reads network/routing_tables.json, draws the network graph with:
  - Routers as nodes (r1, r2, r3, r4)
  - Links as edges with subnet labels
  - Optionally highlights the best path for a destination in red

Usage:
  python3 network/route_visualizer.py
  python3 network/route_visualizer.py --dest 10.0.3.0/24 --from r1

Output:
  network/topology_graph.png
"""

import json
import os
import sys
import argparse

import networkx as nx
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTING_TABLES_JSON = os.path.join(_THIS_DIR, "routing_tables.json")
OUTPUT_PNG = os.path.join(_THIS_DIR, "topology_graph.png")

# Topology definition (matches mininet_topology.py)
TOPOLOGY_LINKS = [
    {"from": "r1", "to": "r2", "subnet": "10.0.1.0/24", "from_ip": "10.0.1.1", "to_ip": "10.0.1.2"},
    {"from": "r2", "to": "r3", "subnet": "10.0.2.0/24", "from_ip": "10.0.2.1", "to_ip": "10.0.2.2"},
    {"from": "r3", "to": "r4", "subnet": "10.0.3.0/24", "from_ip": "10.0.3.1", "to_ip": "10.0.3.2"},
    {"from": "r4", "to": "r1", "subnet": "10.0.4.0/24", "from_ip": "10.0.4.1", "to_ip": "10.0.4.2"},
]

# IP → router mapping (for path tracing)
IP_TO_ROUTER = {}
for link in TOPOLOGY_LINKS:
    IP_TO_ROUTER[link["from_ip"]] = link["from"]
    IP_TO_ROUTER[link["to_ip"]] = link["to"]


def load_routing_tables() -> dict:
    """Load routing tables from JSON file."""
    if not os.path.exists(ROUTING_TABLES_JSON):
        print(f"⚠️  {ROUTING_TABLES_JSON} not found. Using default topology.")
        return {}

    with open(ROUTING_TABLES_JSON, "r") as f:
        return json.load(f)


def trace_path(routing_tables: dict, src_router: str, destination: str) -> list[str]:
    """Trace the forwarding path from src_router to the destination subnet.

    Returns list of router IDs visited.
    """
    path = [src_router]
    current = src_router
    visited = set()

    for _ in range(10):  # safety limit
        if current in visited:
            break  # loop detected
        visited.add(current)

        routes = routing_tables.get(current, [])
        match = [r for r in routes if r["destination"] == destination]
        if not match:
            break

        gw = match[0].get("gateway", "")
        if not gw:
            break  # directly connected — we've arrived

        next_router = IP_TO_ROUTER.get(gw)
        if not next_router or next_router in visited:
            break
        path.append(next_router)
        current = next_router

    return path


def draw_topology(routing_tables: dict, highlight_dest: str = "", highlight_from: str = ""):
    """Draw the network topology graph and save to PNG."""
    G = nx.Graph()

    # Add nodes (routers)
    routers = ["r1", "r2", "r3", "r4"]
    for r in routers:
        route_count = len(routing_tables.get(r, []))
        G.add_node(r, label=r, routes=route_count)

    # Add edges (links)
    edge_labels = {}
    for link in TOPOLOGY_LINKS:
        G.add_edge(link["from"], link["to"], subnet=link["subnet"])
        edge_labels[(link["from"], link["to"])] = link["subnet"]

    # Layout — square positions for ring topology
    pos = {
        "r1": (-1, 1),
        "r2": (1, 1),
        "r3": (1, -1),
        "r4": (-1, -1),
    }

    # ── Figure setup ──────────────────────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    # ── Draw edges ────────────────────────────────────────────
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#4a4a6a",
        width=3,
        alpha=0.8,
    )

    # ── Highlight path if requested ───────────────────────────
    path_edges = []
    if highlight_dest and highlight_from and routing_tables:
        path = trace_path(routing_tables, highlight_from, highlight_dest)
        if len(path) > 1:
            for i in range(len(path) - 1):
                edge = (path[i], path[i + 1])
                rev = (path[i + 1], path[i])
                if G.has_edge(*edge):
                    path_edges.append(edge)
                elif G.has_edge(*rev):
                    path_edges.append(rev)

            nx.draw_networkx_edges(
                G, pos, edgelist=path_edges, ax=ax,
                edge_color="#ff4757",
                width=5,
                alpha=1.0,
                style="solid",
            )

    # ── Draw nodes ────────────────────────────────────────────
    node_colors = []
    for r in routers:
        if highlight_from and r == highlight_from:
            node_colors.append("#ff6b6b")  # source = red
        elif path_edges and r in [n for e in path_edges for n in e]:
            node_colors.append("#ffa502")  # path = orange
        else:
            node_colors.append("#5f7cec")  # default = blue

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        nodelist=routers,
        node_color=node_colors,
        node_size=2500,
        edgecolors="#ffffff",
        linewidths=2.5,
    )

    # ── Node labels ───────────────────────────────────────────
    node_labels = {}
    for r in routers:
        rc = len(routing_tables.get(r, []))
        node_labels[r] = f"{r.upper()}\n({rc} routes)"

    nx.draw_networkx_labels(
        G, pos, labels=node_labels, ax=ax,
        font_size=11,
        font_color="white",
        font_weight="bold",
    )

    # ── Edge labels (subnets) ─────────────────────────────────
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, ax=ax,
        font_size=9,
        font_color="#00d2d3",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#16213e", edgecolor="#00d2d3", alpha=0.9),
    )

    # ── Title and legend ──────────────────────────────────────
    title = "Mininet Ring Topology — Routing Table Analysis"
    if highlight_dest:
        title += f"\nPath: {highlight_from} → {highlight_dest}"
    ax.set_title(title, color="white", fontsize=14, fontweight="bold", pad=20)

    # Legend
    legend_items = [
        mpatches.Patch(color="#5f7cec", label="Router (default)"),
        mpatches.Patch(color="#4a4a6a", label="Link"),
    ]
    if highlight_dest:
        legend_items.append(mpatches.Patch(color="#ff6b6b", label="Source router"))
        legend_items.append(mpatches.Patch(color="#ff4757", label="Forwarding path"))

    ax.legend(
        handles=legend_items,
        loc="lower right",
        facecolor="#16213e",
        edgecolor="#4a4a6a",
        labelcolor="white",
        fontsize=9,
    )

    # ── Router details table ──────────────────────────────────
    if routing_tables:
        detail_lines = []
        for r in routers:
            routes = routing_tables.get(r, [])
            for route in routes:
                gw = route.get("gateway", "")
                if gw:
                    detail_lines.append(f"  {r}: {route['destination']} via {gw}")
                else:
                    detail_lines.append(f"  {r}: {route['destination']} (direct)")

        # Add a text box with route details
        info_text = "Routing Tables:\n" + "\n".join(detail_lines[:16])
        if len(detail_lines) > 16:
            info_text += f"\n  ... and {len(detail_lines) - 16} more"

        ax.text(
            0.02, 0.02, info_text,
            transform=ax.transAxes,
            fontsize=7,
            fontfamily="monospace",
            color="#a0a0c0",
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#16213e", edgecolor="#4a4a6a", alpha=0.9),
        )

    ax.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Topology graph saved to: {OUTPUT_PNG}")
    return OUTPUT_PNG


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize Mininet ring topology")
    parser.add_argument("--dest", default="", help="Destination to highlight path for (e.g. 10.0.3.0/24)")
    parser.add_argument("--from-router", dest="from_router", default="r1", help="Source router (default: r1)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Route Visualizer — Mininet Ring Topology")
    print("=" * 60)

    tables = load_routing_tables()
    if tables:
        print(f"\n📂 Loaded routing tables for: {', '.join(sorted(tables.keys()))}")
        for r, routes in sorted(tables.items()):
            print(f"   {r}: {len(routes)} routes")
    else:
        print("\n⚠️  No routing data loaded — drawing topology only")

    print()
    output = draw_topology(
        tables,
        highlight_dest=args.dest,
        highlight_from=args.from_router,
    )

    if args.dest:
        path = trace_path(tables, args.from_router, args.dest)
        print(f"\n🗺️  Path from {args.from_router} to {args.dest}: {' → '.join(path)}")
