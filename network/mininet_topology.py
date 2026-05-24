#!/usr/bin/env python3
# Real-Time Routing Table Analysis using MCP Resources | WMN Course Project | May 2026
"""
mininet_topology.py — Ring topology with 4 routers for routing-table analysis.

Topology
--------
    r1 ——— r2
    |       |
    r4 ——— r3

Subnets
-------
  r1–r2 : 10.0.1.0/24
  r2–r3 : 10.0.2.0/24
  r3–r4 : 10.0.3.0/24
  r4–r1 : 10.0.4.0/24

Usage
-----
  sudo python3 mininet_topology.py

Requires Mininet to be installed:
  sudo apt install mininet
"""

import json
import sys
import os

try:
    from mininet.net import Mininet
    from mininet.node import Node
    from mininet.cli import CLI
    from mininet.log import setLogLevel, info
    from mininet.link import TCLink
    MININET_AVAILABLE = True
except ImportError:
    MININET_AVAILABLE = False


class LinuxRouter(Node if MININET_AVAILABLE else object):
    """A Linux node configured to act as a router (IP forwarding enabled)."""

    def config(self, **params):
        super().config(**params)
        self.cmd("sysctl -w net.ipv4.ip_forward=1")

    def terminate(self):
        self.cmd("sysctl -w net.ipv4.ip_forward=0")
        super().terminate()


# ── IP addressing scheme ──────────────────────────────────────────────────
LINKS = {
    # (router_a, router_b): (ip_a, ip_b, subnet)
    ("r1", "r2"): ("10.0.1.1/24", "10.0.1.2/24", "10.0.1.0/24"),
    ("r2", "r3"): ("10.0.2.1/24", "10.0.2.2/24", "10.0.2.0/24"),
    ("r3", "r4"): ("10.0.3.1/24", "10.0.3.2/24", "10.0.3.0/24"),
    ("r4", "r1"): ("10.0.4.1/24", "10.0.4.2/24", "10.0.4.0/24"),
}

# Static routes – each router gets routes to non-directly-connected subnets
STATIC_ROUTES = {
    "r1": [
        ("10.0.2.0/24", "10.0.1.2"),   # via r2
        ("10.0.3.0/24", "10.0.4.1"),   # via r4 (shorter via ring)
    ],
    "r2": [
        ("10.0.3.0/24", "10.0.2.2"),   # via r3
        ("10.0.4.0/24", "10.0.1.1"),   # via r1
    ],
    "r3": [
        ("10.0.4.0/24", "10.0.3.2"),   # via r4
        ("10.0.1.0/24", "10.0.2.1"),   # via r2
    ],
    "r4": [
        ("10.0.1.0/24", "10.0.4.2"),   # via r1
        ("10.0.2.0/24", "10.0.3.1"),   # via r3
    ],
}


def build_topology():
    """Build and return the Mininet network with the ring topology."""
    if not MININET_AVAILABLE:
        print("❌ Mininet is not installed.")
        print("   Install with:  sudo apt install mininet")
        print("   Then run:      sudo python3 mininet_topology.py")
        sys.exit(1)

    setLogLevel("info")

    net = Mininet(link=TCLink)

    info("*** Creating routers\n")
    routers = {}
    for name in ("r1", "r2", "r3", "r4"):
        routers[name] = net.addHost(name, cls=LinuxRouter, ip=None)

    info("*** Creating links\n")
    intf_idx = {}  # track interface index per router
    for (ra, rb), (ip_a, ip_b, _subnet) in LINKS.items():
        ia = intf_idx.get(ra, 0)
        ib = intf_idx.get(rb, 0)
        intf_a = f"{ra}-eth{ia}"
        intf_b = f"{rb}-eth{ib}"
        net.addLink(
            routers[ra], routers[rb],
            intfName1=intf_a, params1={"ip": ip_a},
            intfName2=intf_b, params2={"ip": ip_b},
        )
        intf_idx[ra] = ia + 1
        intf_idx[rb] = ib + 1

    net.start()

    info("*** Configuring static routes\n")
    for rname, routes in STATIC_ROUTES.items():
        for dest, via in routes:
            routers[rname].cmd(f"ip route add {dest} via {via}")

    return net, routers


def dump_routing_tables(routers: dict, outfile: str = "routing_tables.json"):
    """Dump routing tables from all routers to a JSON file."""
    data = {}
    for name, router in sorted(routers.items()):
        output = router.cmd("ip route show")
        routes = []
        for line in output.strip().splitlines():
            parts = line.split()
            if not parts:
                continue
            route = {"destination": parts[0], "gateway": "", "interface": "", "metric": 0}
            i = 1
            while i < len(parts):
                if parts[i] == "via" and i + 1 < len(parts):
                    route["gateway"] = parts[i + 1]; i += 2
                elif parts[i] == "dev" and i + 1 < len(parts):
                    route["interface"] = parts[i + 1]; i += 2
                elif parts[i] == "metric" and i + 1 < len(parts):
                    try: route["metric"] = int(parts[i + 1])
                    except ValueError: pass
                    i += 2
                else:
                    i += 1
            routes.append(route)
        data[name] = routes

    filepath = os.path.join(os.path.dirname(__file__), outfile)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ Routing tables written to {filepath}")
    return data


def print_mock_topology():
    """Print the topology information when Mininet is not available."""
    print("=" * 60)
    print("  Mininet Ring Topology (4 Routers)")
    print("=" * 60)
    print("""
  Topology Diagram:

      r1 ———————— r2
      |   10.0.1   |
      |  .0/24     |  10.0.2
      |            |  .0/24
      |   10.0.4   |
      r4 ———————— r3
         10.0.3
          .0/24

  Subnets:
    r1-r2 : 10.0.1.0/24   (r1=.1, r2=.2)
    r2-r3 : 10.0.2.0/24   (r2=.1, r3=.2)
    r3-r4 : 10.0.3.0/24   (r3=.1, r4=.2)
    r4-r1 : 10.0.4.0/24   (r4=.1, r1=.2)
    """)

    # Generate mock routing_tables.json
    mock_data = {
        "r1": [
            {"destination": "10.0.1.0/24", "gateway": "", "interface": "r1-eth0", "metric": 0},
            {"destination": "10.0.4.0/24", "gateway": "", "interface": "r1-eth1", "metric": 0},
            {"destination": "10.0.2.0/24", "gateway": "10.0.1.2", "interface": "r1-eth0", "metric": 0},
            {"destination": "10.0.3.0/24", "gateway": "10.0.4.1", "interface": "r1-eth1", "metric": 0},
        ],
        "r2": [
            {"destination": "10.0.1.0/24", "gateway": "", "interface": "r2-eth0", "metric": 0},
            {"destination": "10.0.2.0/24", "gateway": "", "interface": "r2-eth1", "metric": 0},
            {"destination": "10.0.3.0/24", "gateway": "10.0.2.2", "interface": "r2-eth1", "metric": 0},
            {"destination": "10.0.4.0/24", "gateway": "10.0.1.1", "interface": "r2-eth0", "metric": 0},
        ],
        "r3": [
            {"destination": "10.0.2.0/24", "gateway": "", "interface": "r3-eth0", "metric": 0},
            {"destination": "10.0.3.0/24", "gateway": "", "interface": "r3-eth1", "metric": 0},
            {"destination": "10.0.4.0/24", "gateway": "10.0.3.2", "interface": "r3-eth1", "metric": 0},
            {"destination": "10.0.1.0/24", "gateway": "10.0.2.1", "interface": "r3-eth0", "metric": 0},
        ],
        "r4": [
            {"destination": "10.0.3.0/24", "gateway": "", "interface": "r4-eth0", "metric": 0},
            {"destination": "10.0.4.0/24", "gateway": "", "interface": "r4-eth1", "metric": 0},
            {"destination": "10.0.1.0/24", "gateway": "10.0.4.2", "interface": "r4-eth1", "metric": 0},
            {"destination": "10.0.2.0/24", "gateway": "10.0.3.1", "interface": "r4-eth0", "metric": 0},
        ],
    }
    filepath = os.path.join(os.path.dirname(__file__), "routing_tables.json")
    with open(filepath, "w") as f:
        json.dump(mock_data, f, indent=2)
    print(f"  ✅ Mock routing tables written to {filepath}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not MININET_AVAILABLE:
        print_mock_topology()
        print("\n  ⚠️  Mininet is not installed. Mock data generated.")
        print("  To run with real Mininet:")
        print("    sudo apt install mininet")
        print("    sudo python3 mininet_topology.py")
        sys.exit(0)

    if os.geteuid() != 0:
        print("❌ This script must be run as root.")
        print("   Usage: sudo python3 mininet_topology.py")
        sys.exit(1)

    net, routers = build_topology()

    print("\n" + "=" * 60)
    print("  Ring Topology Active — 4 Routers")
    print("=" * 60)

    # Dump routing tables
    tables = dump_routing_tables(routers)
    for rname, routes in sorted(tables.items()):
        print(f"\n  {rname}:")
        for r in routes:
            gw = f" via {r['gateway']}" if r['gateway'] else ""
            print(f"    {r['destination']}{gw} dev {r['interface']}")

    print("\n  Entering Mininet CLI. Type 'exit' to stop.\n")
    CLI(net)
    net.stop()
