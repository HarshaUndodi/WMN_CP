#!/usr/bin/env python3
"""Generate visual charts for all 7 evaluation parameters + topology changes."""

import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(EVAL_DIR, "charts")
PERF_FILE = os.path.join(EVAL_DIR, "performance_results.json")
SCENARIO_FILE = os.path.join(EVAL_DIR, "scenario_results.json")
TOPO_FILE = os.path.join(EVAL_DIR, "topology_change_results.json")
os.makedirs(CHARTS_DIR, exist_ok=True)

# Style
BG = "#1a1a2e"; FG = "#e0e0e0"; ACC = "#00d4aa"; ACC2 = "#5f7cec"
ACC3 = "#ff6b6b"; ACC4 = "#ffa502"; GRID = "#2a2a4a"
COLORS = ["#00d4aa", "#5f7cec", "#ff6b6b", "#ffa502", "#a55eea", "#2ed573"]

def _style(ax, title=""):
    ax.set_facecolor(BG)
    ax.set_title(title, color=FG, fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors=FG, labelsize=9)
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    for s in ["bottom","left"]: ax.spines[s].set_color(GRID)
    ax.yaxis.label.set_color(FG); ax.xaxis.label.set_color(FG)

def load(path):
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    return None

# ── Chart 1: Tool Response Latency (Parameter 1) ─────────────
def chart1_latency():
    perf = load(PERF_FILE)
    tools = [t["tool"].replace("_","\n") for t in perf["tools"]]
    avgs = [t["avg_ms"] for t in perf["tools"]]
    mins = [t["min_ms"] for t in perf["tools"]]
    maxs = [t["max_ms"] for t in perf["tools"]]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.patch.set_facecolor(BG)
    _style(ax, "Parameter 1: MCP Tool Response Latency")

    x = np.arange(len(tools))
    bars = ax.bar(x, avgs, 0.55, color=COLORS[:len(tools)], alpha=0.88,
                  edgecolor="white", linewidth=0.5)
    errs = [[a-mn for a,mn in zip(avgs,mins)],[mx-a for a,mx in zip(avgs,maxs)]]
    ax.errorbar(x, avgs, yerr=errs, fmt="none", ecolor=ACC3, capsize=5, capthick=1.5)
    for b, v in zip(bars, avgs):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.02,
                f"{v:.3f}", ha="center", va="bottom", color=FG, fontsize=9, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(tools, fontsize=8)
    ax.set_ylabel("Latency (ms)"); ax.set_xlabel("MCP Tool")
    ax.axhline(y=1.0, color=ACC3, linestyle="--", alpha=0.4, linewidth=1)
    ax.text(len(tools)-0.5, 1.05, "1 ms threshold", color=ACC3, fontsize=8, alpha=0.7)
    ax.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)
    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "param1_tool_latency.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Chart 2: Detection Latency (Parameter 2) ─────────────────
def chart2_detection():
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(BG); _style(ax, "Parameter 2: Route Change Detection Latency")
    scenarios = ["Route\nInjection", "Link\nFailure"]
    latencies = [251.66, 252.29]
    bars = ax.bar(scenarios, latencies, 0.45, color=[ACC2, ACC3], alpha=0.88,
                  edgecolor="white", linewidth=0.5)
    for b, v in zip(bars, latencies):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+3,
                f"{v:.1f} ms", ha="center", va="bottom", color=FG, fontsize=11, fontweight="bold")
    ax.axhline(y=250, color=ACC4, linestyle="--", alpha=0.5)
    ax.text(1.3, 253, "~250 ms polling", color=ACC4, fontsize=9, alpha=0.8)
    ax.set_ylabel("Detection Latency (ms)"); ax.set_ylim(0, 320)
    ax.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)
    # Add PASS labels
    for b in bars:
        ax.text(b.get_x()+b.get_width()/2, 15, "PASS ✓", ha="center",
                color="#00ff88", fontsize=10, fontweight="bold")
    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "param2_detection_latency.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Chart 3: Memory Consumption (Parameter 3) ────────────────
def chart3_memory():
    perf = load(PERF_FILE)
    tools = [t["tool"].replace("_","\n") for t in perf["tools"]]
    mems = [t["avg_memory_mb"] for t in perf["tools"]]

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor(BG); _style(ax, "Parameter 3: Memory Consumption per Tool")
    x = np.arange(len(tools))
    bars = ax.bar(x, mems, 0.55, color=ACC2, alpha=0.85, edgecolor="white", linewidth=0.5)
    for b, v in zip(bars, mems):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.05,
                f"{v:.2f}", ha="center", va="bottom", color=FG, fontsize=9, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(tools, fontsize=8)
    ax.set_ylabel("Memory (MB)"); ax.set_ylim(14.0, 15.2)
    ax.axhline(y=14.77, color=ACC, linestyle="--", alpha=0.4)
    ax.text(len(tools)-0.5, 14.78, "Avg: 14.77 MB", color=ACC, fontsize=9, alpha=0.8)
    ax.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)
    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "param3_memory.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Chart 4: CPU Utilization (Parameter 4) ────────────────────
def chart4_cpu():
    perf = load(PERF_FILE)
    tools = [t["tool"].replace("_","\n") for t in perf["tools"]]
    cpus = [t["avg_cpu_pct"] for t in perf["tools"]]

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor(BG); _style(ax, "Parameter 4: CPU Utilization per Tool")
    x = np.arange(len(tools))
    bars = ax.bar(x, [max(c, 0.02) for c in cpus], 0.55, color=ACC4, alpha=0.85,
                  edgecolor="white", linewidth=0.5)
    for b, v in zip(bars, cpus):
        ax.text(b.get_x()+b.get_width()/2, 0.5, f"{v:.1f}%", ha="center",
                va="bottom", color=FG, fontsize=10, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(tools, fontsize=8)
    ax.set_ylabel("CPU Usage (%)"); ax.set_ylim(0, 5)
    ax.axhline(y=1.0, color=ACC3, linestyle="--", alpha=0.3)
    ax.text(len(tools)-0.5, 1.1, "1% reference", color=ACC3, fontsize=9, alpha=0.6)
    # Big "0.0%" overlay
    ax.text(len(tools)/2-0.5, 3.0, "Near-Zero CPU Overhead", ha="center",
            color=ACC, fontsize=16, fontweight="bold", alpha=0.4)
    ax.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)
    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "param4_cpu.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Chart 5: Accuracy (Parameters 5 & 6) ─────────────────────
def chart5_accuracy():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor(BG)
    fig.suptitle("Parameters 5 & 6: Detection Accuracy", color=FG,
                 fontsize=14, fontweight="bold", y=0.98)

    # Flap Detection (Param 5)
    ax1.set_facecolor(BG)
    labels = ["True\nPositive", "True\nNegative"]
    values = [1, 1]; colors_pie = [ACC, ACC2]
    wedges, texts, autotexts = ax1.pie(values, labels=labels, colors=colors_pie,
        autopct="✓", startangle=90, textprops={"color": FG, "fontsize": 10},
        wedgeprops={"edgecolor": BG, "linewidth": 2})
    for at in autotexts: at.set_color("white"); at.set_fontsize(14); at.set_fontweight("bold")
    ax1.set_title("Route Flap Detection\n(100% Accuracy)", color=FG, fontsize=11, pad=10)

    # Loop Detection (Param 6)
    ax2.set_facecolor(BG)
    categories = ["Destinations\nChecked", "Routers\nChecked", "Path\nTraces", "Loops\nFound"]
    vals = [4, 4, 16, 0]
    x = np.arange(len(categories))
    bar_colors = [ACC2, ACC, ACC4, ACC3]
    bars = ax2.bar(x, vals, 0.5, color=bar_colors, alpha=0.85, edgecolor="white", linewidth=0.5)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x()+b.get_width()/2, b.get_height()+0.3,
                str(v), ha="center", va="bottom", color=FG, fontsize=11, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels(categories, fontsize=9, color=FG)
    ax2.set_title("Routing Loop Detection\n(0 Loops = Correct)", color=FG, fontsize=11, pad=10)
    ax2.tick_params(colors=FG)
    for s in ["top","right"]: ax2.spines[s].set_visible(False)
    for s in ["bottom","left"]: ax2.spines[s].set_color(GRID)
    ax2.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)

    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "param5_6_accuracy.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Chart 6: Scalability (Parameter 7) ───────────────────────
def chart6_scalability():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor(BG)
    fig.suptitle("Parameter 7: Scalability — Route Count vs Performance",
                 color=FG, fontsize=14, fontweight="bold", y=0.98)

    # Left: Route counts per scenario
    _style(ax1, "Route Count by Scenario")
    scenarios = ["Baseline", "Injection", "Failure"]
    counts = [16, 17, 15]
    bars = ax1.bar(scenarios, counts, 0.45, color=[ACC, ACC2, ACC3], alpha=0.88,
                   edgecolor="white", linewidth=0.5)
    for b, v in zip(bars, counts):
        ax1.text(b.get_x()+b.get_width()/2, b.get_height()+0.2,
                str(v), ha="center", va="bottom", color=FG, fontsize=12, fontweight="bold")
    ax1.set_ylabel("Route Count"); ax1.set_ylim(0, 20)
    ax1.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)

    # Right: Response time vs route count
    _style(ax2, "Response Time vs Route Count")
    route_counts = [15, 16, 17]
    resp_times = [0.64, 0.41, 0.70]
    ax2.plot(route_counts, resp_times, color=ACC, linewidth=2.5, marker="o",
             markersize=10, markerfacecolor=ACC2, markeredgecolor="white", markeredgewidth=2, zorder=5)
    ax2.fill_between(route_counts, resp_times, alpha=0.15, color=ACC)
    for rc, rt in zip(route_counts, resp_times):
        ax2.annotate(f"{rt:.2f} ms", (rc, rt), textcoords="offset points",
                    xytext=(0, 12), ha="center", color=FG, fontsize=10, fontweight="bold")
    ax2.set_xlabel("Route Count"); ax2.set_ylabel("Response Time (ms)")
    ax2.set_ylim(0, 1.2); ax2.set_xticks(route_counts)
    ax2.axhline(y=1.0, color=ACC3, linestyle="--", alpha=0.4)
    ax2.text(16.5, 1.03, "1 ms threshold", color=ACC3, fontsize=9, alpha=0.7)
    ax2.grid(color=GRID, linestyle="--", alpha=0.4)

    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "param7_scalability.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Chart 7: Topology Changes ────────────────────────────────
def chart7_topology():
    fig = plt.figure(figsize=(13, 5.5))
    fig.patch.set_facecolor(BG)
    gs = GridSpec(1, 3, width_ratios=[1, 1, 1.2], wspace=0.35)

    # Left: Router count before/after
    ax1 = fig.add_subplot(gs[0]); _style(ax1, "Add Router r5")
    x = [0, 1]; vals = [4, 5]; labels = ["Before", "After"]
    bars = ax1.bar(x, vals, 0.45, color=[ACC2, ACC], alpha=0.88, edgecolor="white")
    for b, v in zip(bars, vals):
        ax1.text(b.get_x()+b.get_width()/2, b.get_height()+0.1,
                f"{v}R", ha="center", va="bottom", color=FG, fontsize=12, fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels(labels, color=FG)
    ax1.set_ylabel("Routers"); ax1.set_ylim(0, 7)
    ax1.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)

    # Middle: Router count for removal
    ax2 = fig.add_subplot(gs[1]); _style(ax2, "Remove Router r4")
    vals2 = [4, 3]
    bars2 = ax2.bar(x, vals2, 0.45, color=[ACC2, ACC3], alpha=0.88, edgecolor="white")
    for b, v in zip(bars2, vals2):
        ax2.text(b.get_x()+b.get_width()/2, b.get_height()+0.1,
                f"{v}R", ha="center", va="bottom", color=FG, fontsize=12, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels(labels, color=FG)
    ax2.set_ylabel("Routers"); ax2.set_ylim(0, 7)
    ax2.grid(axis="y", color=GRID, linestyle="--", alpha=0.4)

    # Right: Detection latency comparison
    ax3 = fig.add_subplot(gs[2]); _style(ax3, "Detection Latency")
    ops = ["Add r5", "Remove r4"]
    lats = [253, 252]
    bars3 = ax3.barh(ops, lats, 0.4, color=[ACC, ACC3], alpha=0.88, edgecolor="white")
    for b, v in zip(bars3, lats):
        ax3.text(v+3, b.get_y()+b.get_height()/2, f"{v} ms",
                va="center", color=FG, fontsize=11, fontweight="bold")
    ax3.set_xlabel("Latency (ms)"); ax3.set_xlim(0, 320)
    ax3.tick_params(colors=FG)
    ax3.grid(axis="x", color=GRID, linestyle="--", alpha=0.4)

    fig.suptitle("Topology Change Detection Results", color=FG,
                 fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "topology_changes.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Chart 8: All Parameters Summary Radar ─────────────────────
def chart8_summary():
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG); ax.axis("off")
    ax.set_title("All 7 Evaluation Parameters — Summary", color=FG,
                 fontsize=15, fontweight="bold", pad=20)
    cols = ["#", "Parameter", "Metric", "Value", "Verdict"]
    rows = [
        ["1", "Tool Response Latency", "Avg across 6 tools", "0.004–1.286 ms", "✓ Sub-ms"],
        ["2", "Detection Latency", "Injection & failure", "~252 ms", "✓ Pass"],
        ["3", "Memory Consumption", "RSS during execution", "~14.8 MB", "✓ Light"],
        ["4", "CPU Utilization", "CPU % during execution", "0.0%", "✓ Zero"],
        ["5", "Flap Detection", "TP + TN accuracy", "100%", "✓ Correct"],
        ["6", "Loop Detection", "Loop presence/absence", "100%", "✓ Correct"],
        ["7", "Scalability", "15–17 routes", "< 1 ms", "✓ Stable"],
    ]
    table = ax.table(cellText=rows, colLabels=cols, cellLoc="center", loc="center")
    table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1, 2.2)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(GRID)
        if row == 0:
            cell.set_facecolor("#2a2a5a")
            cell.set_text_props(color="white", fontweight="bold", fontsize=10)
        else:
            cell.set_facecolor("#16213e")
            cell.set_text_props(color=FG, fontsize=10)
            if col == 4:
                cell.set_facecolor("#1a4a2e")
                cell.set_text_props(color="#00ff88", fontweight="bold")
    plt.tight_layout()
    p = os.path.join(CHARTS_DIR, "param_summary.png")
    plt.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight"); plt.close()
    print(f"  ✅ {p}"); return p

# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   Results Charts Generator (7 Parameters)              ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    chart1_latency()
    chart2_detection()
    chart3_memory()
    chart4_cpu()
    chart5_accuracy()
    chart6_scalability()
    chart7_topology()
    chart8_summary()
    print(f"\n✅ All 8 charts generated in {CHARTS_DIR}/")
