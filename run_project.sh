#!/bin/bash
# ================================================================
#  run_project.sh — Launch the full MCP Routing Table Analysis
#
#  Steps:
#    1. Activate the virtual environment
#    2. Start Mininet topology in background (requires sudo)
#    3. Wait for routing_tables.json
#    4. Start MCP client (auto-launches server)
#    5. Cleanup on exit
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
ROUTING_JSON="$SCRIPT_DIR/network/routing_tables.json"
MININET_PID=""

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "================================================================"
echo "  Real-Time Routing Table Analysis using MCP Resources"
echo "================================================================"
echo -e "${NC}"

# ── Step 1: Check venv ───────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Virtual environment not found at: $VENV_PYTHON${NC}"
    echo "   Run: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi
echo -e "${GREEN}✅ Step 1: Virtual environment found${NC}"

# ── Step 2: Start Mininet topology ───────────────────────────
echo -e "\n${YELLOW}🔑 Step 2: Starting Mininet topology (requires sudo password)${NC}"
echo "   This will create 4 routers in a ring topology."
echo ""

# Run mininet in background, pipe exit to it after dumping tables
sudo "$VENV_PYTHON" network/mininet_topology.py <<< "exit" &
MININET_PID=$!

# ── Step 3: Wait for routing_tables.json ─────────────────────
echo -e "\n${CYAN}⏳ Step 3: Waiting for routing_tables.json to be generated …${NC}"
for i in $(seq 1 10); do
    if [ -f "$ROUTING_JSON" ]; then
        AGE=$(( $(date +%s) - $(stat -c %Y "$ROUTING_JSON") ))
        if [ $AGE -lt 30 ]; then
            echo -e "${GREEN}   ✅ routing_tables.json found (${AGE}s old)${NC}"
            break
        fi
    fi
    echo "   Waiting … ($i/10)"
    sleep 1
done

# Wait for mininet to finish
wait $MININET_PID 2>/dev/null || true
MININET_PID=""

if [ ! -f "$ROUTING_JSON" ]; then
    echo -e "${YELLOW}   ⚠️  routing_tables.json not found, will use mock data${NC}"
fi

# ── Step 4: Generate topology graph ──────────────────────────
echo -e "\n${CYAN}📊 Step 4: Generating topology graph …${NC}"
"$VENV_PYTHON" network/route_visualizer.py --dest "10.0.3.0/24" --from-router r1 2>&1 || true

# ── Step 5: Start MCP Client ────────────────────────────────
echo -e "\n${GREEN}🚀 Step 5: Starting MCP Client (server auto-starts via stdio)${NC}"
echo ""
"$VENV_PYTHON" client/mcp_client.py

# ── Cleanup ──────────────────────────────────────────────────
echo -e "\n${YELLOW}🧹 Cleaning up Mininet …${NC}"
sudo mn -c 2>/dev/null || true
echo -e "${GREEN}✅ Done!${NC}"
