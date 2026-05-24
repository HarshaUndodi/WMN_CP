# 🌐 Real-Time Routing Table Analysis using MCP Resources

**Course:** Wireless Mobile Networks (WMN)  
**Technology:** Model Context Protocol (MCP) + FastMCP + Mininet

---

## 📖 Description

This project demonstrates real-time routing table monitoring and analysis
using the **Model Context Protocol (MCP)**. MCP is an open protocol that
provides a standardized way for applications to expose **Resources** (data
endpoints) and **Tools** (executable functions) to clients.

### What are MCP Resources?

MCP Resources are **read-only data endpoints** identified by URIs (like
`routing://table/live`). They allow clients to fetch structured data from
a server without needing to know the underlying implementation. In this
project, resources expose:

- **Live routing table** — the current state of network routes
- **Historical snapshots** — past routing tables indexed by timestamp

### What are MCP Tools?

MCP Tools are **executable functions** that clients can invoke with
parameters. This project provides tools for:

- Fetching the live routing table
- Detecting route flaps (rapid route changes)
- Comparing historical routing snapshots
- Finding the best path to a destination

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SYSTEM ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     stdio      ┌──────────────────────┐   │
│  │   MCP Client     │◄──────────────►│   MCP Server         │   │
│  │  (mcp_client.py) │                │  (mcp_server.py)     │   │
│  │                  │                │                      │   │
│  │  • CLI Interface │                │  Resources:          │   │
│  │  • get routes    │                │  • routing://live    │   │
│  │  • detect flaps  │                │  • routing://history │   │
│  │  • compare       │                │                      │   │
│  │  • find path     │                │  Tools:              │   │
│  └──────────────────┘                │  • get_routing_table │   │
│                                      │  • detect_route_flap │   │
│                                      │  • compare_snapshots │   │
│                                      │  • find_best_path    │   │
│                                      │                      │   │
│                                      │  Background Poller   │   │
│                                      │  (every 10s)         │   │
│                                      └──────────┬───────────┘   │
│                                                 │               │
│                                      ┌──────────▼───────────┐   │
│                                      │  Routing Poller      │   │
│                                      │  (routing_poller.py) │   │
│                                      │                      │   │
│                                      │  • ip route show     │   │
│                                      │  • Parse output      │   │
│                                      │  • Mock fallback     │   │
│                                      └──────────┬───────────┘   │
│                                                 │               │
│                                      ┌──────────▼───────────┐   │
│                                      │  Linux Kernel /      │   │
│                                      │  Mininet Network     │   │
│                                      │  (mininet_topology)  │   │
│                                      │                      │   │
│                                      │   r1 ──── r2         │   │
│                                      │   |        |         │   │
│                                      │   r4 ──── r3         │   │
│                                      └──────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
routing-mcp-project/
├── server/
│   ├── mcp_server.py              # FastMCP server (4 resources, 8 tools)
│   └── routing_poller.py          # Multi-source routing data poller
├── client/
│   ├── mcp_client.py              # Interactive MCP client with CLI
│   └── nl_client.py               # Natural Language interface (Ollama + MCP)
├── network/
│   ├── mininet_topology.py        # Mininet ring topology (4 routers)
│   ├── route_visualizer.py        # Topology graph visualizer
│   ├── routing_tables.json        # Real Mininet routing data
│   └── topology_graph.png         # Generated topology graph
├── evaluation/
│   ├── scenario_runner.py         # 3-scenario evaluation runner
│   ├── performance_metrics.py     # Tool latency benchmarks
│   ├── generate_charts.py         # Chart generation (3 charts)
│   ├── generate_report.py         # Report generator (MD + HTML)
│   ├── test_nl_queries.py         # NL query test suite (8 queries)
│   ├── charts/                    # Generated performance charts
│   ├── report.md                  # Final report (Markdown)
│   └── report.html                # Final report (styled HTML)
├── demo_script.sh                 # Automated demo launcher
├── run_project.sh                 # One-command project launcher
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## 🔧 Prerequisites

| Requirement       | Version  | Notes                              |
|--------------------|----------|------------------------------------|
| Python             | 3.10+    | Required for type hints & asyncio  |
| pip                | latest   | Python package manager             |
| Mininet (optional) | 2.3+     | For real network simulation        |
| Linux              | any      | Required for `ip route show`       |

---

## 🚀 How to Run

### Step 1 — Install Dependencies

```bash
cd routing-mcp-project
pip install -r requirements.txt
```

### Step 2 — Test the Routing Poller

```bash
python3 server/routing_poller.py
```

This will poll the routing table 3 times (5-second intervals) and print
the results. If `ip route show` fails, it uses mock data.

### Step 3 — (Optional) Run Mininet Topology

```bash
sudo python3 network/mininet_topology.py
```

This creates a ring topology with 4 routers and dumps their routing
tables to `routing_tables.json`. Requires Mininet and root privileges.

If Mininet is not installed, mock routing data will be generated instead.

### Step 4 — Start the MCP Server

```bash
python3 server/mcp_server.py
```

The server starts on **stdio transport** and begins polling every 10
seconds. It will print status messages to stderr.

### Step 5 — Connect the MCP Client

Open a **new terminal** and run:

```bash
python3 client/mcp_client.py
```

The client automatically spawns the server as a subprocess and connects
via stdio. You'll see available resources and tools listed.

---

## 🧪 Testing MCP Tools

Once the client is running, use these commands:

### Get Live Routing Table
```
mcp> get routes
```
Returns the current routing table as a JSON list with destination,
gateway, interface, and metric for each route.

### Detect Route Flaps
```
mcp> detect flaps
```
Checks if any route has changed more than 3 times in the last 60
seconds. Returns flapping routes with change counts and timestamps.

### Compare Historical Snapshots
```
mcp> compare 2025-01-01T12:00 2025-01-01T12:01
```
Diffs two routing snapshots showing added, removed, and changed routes.
Use partial timestamps for matching.

### Find Best Path
```
mcp> find path 10.0.1.0/24
```
Finds the best (lowest metric) next-hop for a given destination prefix.

### Read Live Resource
```
mcp> read live
```
Reads the `routing://table/live` MCP resource directly.

### List Resources & Tools
```
mcp> list resources
mcp> list tools
```

### Exit
```
mcp> quit
```

---

## 🤖 Natural Language Interface (Ollama + MCP)

Ask questions about your network in plain English! An Ollama model (`llama3.2:1b`)
pre-fetches all MCP tool results at startup, then answers queries in a single shot.

### Requirements
- Ollama installed (`curl -fsSL https://ollama.com/install.sh | sh`)
- `llama3.2:1b` model downloaded (`ollama pull llama3.2:1b`)
- Ollama service running (`ollama serve`)

### How to Run
```bash
venv/bin/python3 client/nl_client.py
```

### Example Session
```
🔹 Ask > How many routers are in the network?
🤔 Thinking... (5.8s)
🤖 There are 4 routers (r1, r2, r3, r4) in the Mininet network.

🔹 Ask > Are there any route flaps?
🤔 Thinking... (6.2s)
🤖 No, there are no route flaps detected in the network topology.

🔹 Ask > Show me the routing table for r1
🤔 Thinking... (25.3s)
🤖 r1 (4 routes):
    10.0.1.0/24 → directly connected via r1-eth0
    10.0.2.0/24 → 10.0.1.2 via r1-eth0
    10.0.3.0/24 → 10.0.4.1 via r1-eth1
    10.0.4.0/24 → directly connected via r1-eth1
```

### Special Commands
| Command   | Description                            |
|-----------|----------------------------------------|
| `tools`   | List all available MCP tools           |
| `context` | Show the pre-fetched network data      |
| `refresh` | Re-fetch latest data from MCP server   |
| `quit`    | Exit the assistant                     |

### How It Works
1. On startup, `nl_client.py` calls **all 5 MCP tools** (routes, loops, flaps, topology, events)
2. Results are compressed into a compact text summary (~500 bytes)
3. When the user asks a question, Ollama receives the full context + question in one prompt
4. The model generates a single-shot answer — no round-trips, no tool-call parsing
5. Type `refresh` to re-fetch the latest network state

---

## 📊 MCP Resources Reference

| Resource URI                          | Description                         |
|---------------------------------------|-------------------------------------|
| `routing://table/live`                | Latest routing table snapshot       |
| `routing://table/history/{timestamp}` | Historical snapshot by timestamp    |

## 🔨 MCP Tools Reference

| Tool                          | Parameters         | Description                          |
|-------------------------------|--------------------|--------------------------------------|
| `get_routing_table()`         | none               | Returns live routing table as list   |
| `detect_route_flap()`         | none               | Detects routes changing >3×/60s      |
| `compare_snapshots(ts1, ts2)` | two timestamps     | Diffs two historical snapshots       |
| `find_best_path(destination)` | destination prefix | Finds lowest-metric next-hop         |

---

## 📝 How It Works

1. **Polling:** The server runs a background task that calls `ip route show`
   every 10 seconds (or uses mock data if unavailable).

2. **Snapshots:** Each poll result is stored in memory with an ISO timestamp
   key, building a history of routing table states.

3. **Flap Detection:** When a route's destination changes between polls, the
   change is logged. If a destination changes >3 times in 60 seconds, it's
   flagged as a route flap.

4. **MCP Protocol:** The server exposes this data through standardized MCP
   Resources (for reading data) and Tools (for analysis functions).

5. **Client:** Connects via stdio transport, discovers available resources
   and tools, and provides an interactive CLI for querying.

---

## 👨‍🎓 Course Context

This project is developed for the **Wireless Mobile Networks** course to
demonstrate:

- Real-time network monitoring concepts
- Routing table analysis and route instability detection
- Software-defined networking with Mininet
- Modern protocol design with MCP (Model Context Protocol)
- Asynchronous Python programming with asyncio

---

## 📜 License

Academic project — for educational purposes only.
