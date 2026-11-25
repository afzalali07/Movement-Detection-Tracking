"""
Graph generator — produces matplotlib charts from tracking analytics.
"""

import matplotlib
matplotlib.use("Agg")          # non-interactive backend

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os


def save_all_graphs(analysis: dict, output_dir: str) -> dict[str, str]:
    """
    Generate and save all analysis graphs.
    Returns a dict of {graph_name: filename}.
    """
    os.makedirs(output_dir, exist_ok=True)
    tid = analysis["track_id"]
    saved = {}

    # 1. Trajectory path
    saved["trajectory"] = _trajectory_graph(analysis, output_dir, tid)
    # 2. Speed over frames
    saved["speed"] = _speed_graph(analysis, output_dir, tid)
    # 3. X/Y displacement over frames
    saved["displacement"] = _displacement_graph(analysis, output_dir, tid)
    # 4. Direction histogram
    saved["direction"] = _direction_hist(analysis, output_dir, tid)
    # 5. Summary dashboard
    saved["dashboard"] = _dashboard(analysis, output_dir, tid)

    return saved


# ─────────────────────────── individual charts ───────────────────────────────

def _trajectory_graph(analysis: dict, out: str, tid: int) -> str:
    pts = analysis["trajectory"]
    if not pts:
        return ""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    fig, ax = plt.subplots(figsize=(8, 5), facecolor="#0d1117")
    ax.set_facecolor("#161b22")

    # gradient colour along path
    n = len(xs)
    for i in range(1, n):
        alpha = i / n
        ax.plot(
            [xs[i - 1], xs[i]], [ys[i - 1], ys[i]],
            color=(alpha, 1 - alpha, 0.6),
            linewidth=2,
        )

    ax.plot(xs[0], ys[0], "go", ms=10, label="Start", zorder=5)
    ax.plot(xs[-1], ys[-1], "rs", ms=10, label="End", zorder=5)

    ax.set_title(f"Trajectory — Track ID {tid}", color="white", fontsize=14)
    ax.set_xlabel("X (pixels)", color="#8b949e")
    ax.set_ylabel("Y (pixels)", color="#8b949e")
    ax.tick_params(colors="#8b949e")
    ax.invert_yaxis()
    ax.legend(facecolor="#21262d", labelcolor="white")
    ax.spines[:].set_color("#30363d")
    fig.tight_layout()

    fname = f"trajectory_{tid}.png"
    fig.savefig(os.path.join(out, fname), dpi=100)
    plt.close(fig)
    return fname


def _speed_graph(analysis: dict, out: str, tid: int) -> str:
    speeds = analysis["speeds"]
    if not speeds:
        return ""

    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#0d1117")
    ax.set_facecolor("#161b22")

    frames = list(range(len(speeds)))
    ax.fill_between(frames, speeds, alpha=0.3, color="#58a6ff")
    ax.plot(frames, speeds, color="#58a6ff", linewidth=1.5)
    ax.axhline(y=analysis["avg_speed_px_s"], color="#f78166", linewidth=1.5,
               linestyle="--", label=f"Avg {analysis['avg_speed_px_s']:.1f} px/s")

    ax.set_title(f"Speed Over Frames — Track ID {tid}", color="white", fontsize=13)
    ax.set_xlabel("Frame index", color="#8b949e")
    ax.set_ylabel("Speed (px / s)", color="#8b949e")
    ax.tick_params(colors="#8b949e")
    ax.legend(facecolor="#21262d", labelcolor="white")
    ax.spines[:].set_color("#30363d")
    fig.tight_layout()

    fname = f"speed_{tid}.png"
    fig.savefig(os.path.join(out, fname), dpi=100)
    plt.close(fig)
    return fname


def _displacement_graph(analysis: dict, out: str, tid: int) -> str:
    dx = analysis["displacements_x"]
    dy = analysis["displacements_y"]
    if not dx:
        return ""

    frames = list(range(len(dx)))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5), facecolor="#0d1117",
                                    sharex=True)
    for ax in (ax1, ax2):
        ax.set_facecolor("#161b22")
        ax.spines[:].set_color("#30363d")
        ax.tick_params(colors="#8b949e")

    ax1.bar(frames, dx, color="#3fb950", alpha=0.8, label="ΔX")
    ax1.axhline(0, color="#30363d", linewidth=0.8)
    ax1.set_ylabel("ΔX (px)", color="#8b949e")
    ax1.set_title(f"Frame-by-Frame Displacement — Track ID {tid}",
                  color="white", fontsize=13)
    ax1.legend(facecolor="#21262d", labelcolor="white")

    ax2.bar(frames, dy, color="#ff7b72", alpha=0.8, label="ΔY")
    ax2.axhline(0, color="#30363d", linewidth=0.8)
    ax2.set_ylabel("ΔY (px)", color="#8b949e")
    ax2.set_xlabel("Frame index", color="#8b949e")
    ax2.legend(facecolor="#21262d", labelcolor="white")

    fig.patch.set_facecolor("#0d1117")
    fig.tight_layout()

    fname = f"displacement_{tid}.png"
    fig.savefig(os.path.join(out, fname), dpi=100)
    plt.close(fig)
    return fname


def _direction_hist(analysis: dict, out: str, tid: int) -> str:
    dirs = analysis["directions"]
    if not dirs:
        return ""

    all_dirs = ["North", "NE", "East", "SE", "South", "SW", "West", "NW", "Stationary"]
    counts = {d: dirs.count(d) for d in all_dirs}
    labels = [d for d in all_dirs if counts[d] > 0]
    values = [counts[d] for d in labels]

    colors = plt.cm.plasma(np.linspace(0.2, 0.9, len(labels)))

    fig, ax = plt.subplots(figsize=(6, 5), facecolor="#0d1117")
    ax.set_facecolor("#161b22")

    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, padding=3, color="#8b949e")
    ax.set_title(f"Movement Direction Distribution — Track ID {tid}",
                 color="white", fontsize=12)
    ax.set_ylabel("Frame count", color="#8b949e")
    ax.tick_params(colors="#8b949e", axis="both")
    ax.spines[:].set_color("#30363d")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()

    fname = f"direction_{tid}.png"
    fig.savefig(os.path.join(out, fname), dpi=100)
    plt.close(fig)
    return fname


def _dashboard(analysis: dict, out: str, tid: int) -> str:
    """4-panel summary dashboard."""
    fig = plt.figure(figsize=(14, 8), facecolor="#0d1117")
    fig.suptitle(
        f"Movement Analysis Dashboard — ID {tid} ({analysis['class']})",
        color="white", fontsize=15, fontweight="bold", y=0.98,
    )

    axes = [
        fig.add_subplot(2, 2, 1),
        fig.add_subplot(2, 2, 2),
        fig.add_subplot(2, 2, 3),
        fig.add_subplot(2, 2, 4),
    ]
    for ax in axes:
        ax.set_facecolor("#161b22")
        ax.spines[:].set_color("#30363d")
        ax.tick_params(colors="#8b949e")

    # Panel 1 — trajectory
    pts = analysis["trajectory"]
    if pts:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        n = len(xs)
        for i in range(1, n):
            a = i / n
            axes[0].plot([xs[i-1], xs[i]], [ys[i-1], ys[i]],
                         color=(a, 1 - a, 0.6), lw=1.5)
        axes[0].plot(xs[0], ys[0], "go", ms=7)
        axes[0].plot(xs[-1], ys[-1], "rs", ms=7)
        axes[0].invert_yaxis()
    axes[0].set_title("Trajectory", color="white", fontsize=11)
    axes[0].set_xlabel("X (px)", color="#8b949e", fontsize=9)
    axes[0].set_ylabel("Y (px)", color="#8b949e", fontsize=9)

    # Panel 2 — speed
    speeds = analysis["speeds"]
    if speeds:
        frames = list(range(len(speeds)))
        axes[1].fill_between(frames, speeds, alpha=0.3, color="#58a6ff")
        axes[1].plot(frames, speeds, color="#58a6ff", lw=1.5)
        axes[1].axhline(analysis["avg_speed_px_s"], color="#f78166", lw=1.5,
                        linestyle="--")
    axes[1].set_title("Speed (px/s)", color="white", fontsize=11)
    axes[1].set_xlabel("Frame", color="#8b949e", fontsize=9)
    axes[1].set_ylabel("px/s", color="#8b949e", fontsize=9)

    # Panel 3 — displacement bars
    dx = analysis["displacements_x"]
    dy = analysis["displacements_y"]
    if dx:
        f = list(range(len(dx)))
        axes[2].bar(f, dx, color="#3fb950", alpha=0.7, label="ΔX")
        axes[2].bar(f, dy, color="#ff7b72", alpha=0.7, label="ΔY")
        axes[2].legend(facecolor="#21262d", labelcolor="white", fontsize=8)
    axes[2].set_title("Displacement per Frame", color="white", fontsize=11)
    axes[2].set_xlabel("Frame", color="#8b949e", fontsize=9)
    axes[2].set_ylabel("Pixels", color="#8b949e", fontsize=9)

    # Panel 4 — stats text
    dirs = analysis["directions"]
    all_d = ["North", "NE", "East", "SE", "South", "SW", "West", "NW", "Stationary"]
    cnts = [dirs.count(d) for d in all_d]
    colors_p = plt.cm.plasma(np.linspace(0.2, 0.9, len(all_d)))
    non_zero = [(l, v, c) for l, v, c in zip(all_d, cnts, colors_p) if v > 0]
    if non_zero:
        ls, vs, cs = zip(*non_zero)
        axes[3].bar(ls, vs, color=cs)
        plt.setp(axes[3].xaxis.get_majorticklabels(), rotation=30, ha="right",
                 fontsize=8)
    axes[3].set_title("Direction Histogram", color="white", fontsize=11)
    axes[3].set_ylabel("Frames", color="#8b949e", fontsize=9)

    fig.tight_layout(rect=[0, 0, 1, 0.96])

    fname = f"dashboard_{tid}.png"
    fig.savefig(os.path.join(out, fname), dpi=100)
    plt.close(fig)
    return fname
