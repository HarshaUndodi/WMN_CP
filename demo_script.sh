#!/bin/bash
# ================================================================
#  demo_script.sh — Automated demo of the MCP Routing Table
#  Analysis project for WMN Course presentation.
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

# ── Colors ────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Real-Time Routing Table Analysis using MCP Resources   ║"
echo "║  WMN Course Project — Demo                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: Activate venv ─────────────────────────────────────
echo -e "${GREEN}▶ Step 1: Activating virtual environment${NC}"
source "$SCRIPT_DIR/venv/bin/activate"
echo "  ✅ venv activated: $(which python3)"
echo ""

# ── Step 2: Open report in browser ───────────────────────────
echo -e "${GREEN}▶ Step 2: Opening project report in browser${NC}"
if [ -f "evaluation/report.html" ]; then
    xdg-open "evaluation/report.html" 2>/dev/null &
    echo "  ✅ report.html opened in default browser"
else
    echo "  ⚠️  report.html not found — skipping"
fi
sleep 2
echo ""

# ── Step 3: Show topology graph ──────────────────────────────
echo -e "${GREEN}▶ Step 3: Displaying topology graph${NC}"
if [ -f "network/topology_graph.png" ]; then
    if command -v eog &>/dev/null; then
        eog "network/topology_graph.png" 2>/dev/null &
        echo "  ✅ topology_graph.png opened with eog"
    elif command -v feh &>/dev/null; then
        feh "network/topology_graph.png" 2>/dev/null &
        echo "  ✅ topology_graph.png opened with feh"
    else
        xdg-open "network/topology_graph.png" 2>/dev/null &
        echo "  ✅ topology_graph.png opened with xdg-open"
    fi
else
    echo "  ⚠️  topology_graph.png not found — skipping"
fi
sleep 2
echo ""

# ── Step 4: Run MCP client with automated commands ───────────
echo -e "${GREEN}▶ Step 4: Starting MCP Client — automated demo${NC}"
echo -e "${YELLOW}  Commands: get routes → detect loops → show topology → get router r1 → detect flaps → show events → quit${NC}"
echo ""

# Build the command sequence with delays
{
    sleep 3; echo "get routes"
    sleep 3; echo "detect loops"
    sleep 3; echo "show topology"
    sleep 3; echo "get router r1"
    sleep 3; echo "detect flaps"
    sleep 3; echo "show events"
    sleep 3; echo "quit"
} | "$VENV_PYTHON" client/mcp_client.py 2>&1

echo ""

# ── Step 5: Done ─────────────────────────────────────────────
echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   DEMO COMPLETE                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
