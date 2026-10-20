"""
PARP System Architecture — landscape, monochrome.

Install:
    pip install matplotlib

Run:
    python generate_parp_architecture.py

IMPORTANT:
    Outputs are saved to ~/PARP_output instead of /mnt/c/... to avoid
    the Windows-mounted-drive OSError seen in some WSL setups.
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BLACK = "#111111"
WHITE = "#FFFFFF"


def build_diagram():
    fig, ax = plt.subplots(figsize=(18, 10))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, title, body):
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.06,rounding_size=0.10",
            linewidth=1.5, edgecolor=BLACK, facecolor=WHITE
        )
        ax.add_patch(patch)
        ax.text(
            x + w / 2, y + h - 0.25, title,
            ha="center", va="top", fontsize=13,
            fontweight="bold", color=BLACK, linespacing=1.15
        )
        ax.text(
            x + w / 2, y + h / 2 - 0.18, body,
            ha="center", va="center", fontsize=11.2,
            color=BLACK, linespacing=1.4
        )

    def arrow(start, end, label, offset=(0, 0.25)):
        ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=16,
            linewidth=1.5, color=BLACK
        ))
        ax.text(
            (start[0] + end[0]) / 2 + offset[0],
            (start[1] + end[1]) / 2 + offset[1],
            label, ha="center", va="center", fontsize=9.5,
            color=BLACK,
            bbox=dict(facecolor=WHITE, edgecolor="none", pad=1.5)
        )

    ax.text(
        9, 9.55,
        "System Architecture of Predictive Adaptive Routing Protocol (PARP)",
        ha="center", va="center", fontsize=19,
        fontweight="bold", color=BLACK
    )

    bw, bh = 4.55, 2.45
    xl, xm, xr = 0.55, 6.72, 12.89
    yt, yb = 6.15, 2.25

    box(xl, yt, bw, bh, "1. Network Environment",
        "Mininet topology\nSource: h1 | Destination: h2\n\n"
        "Path 1: r1-r2-r4 (10 Mbps)\nPath 2: r1-r3-r4 (20 Mbps)")
    box(xm, yt, bw, bh, "2. Telemetry Collection",
        "Generate traffic and collect link data\n\n"
        "Link utilization | RTT | Jitter\nInterface transmit-drop information")
    box(xr, yt, bw, bh, "3. Dataset & Feature Engineering",
        "Store telemetry observations in CSV\nClean and order samples\n"
        "Create utilization lag-1, lag-2,\nand utilization-change features")
    box(xr, yb, bw, bh, "4. ML Prediction",
        "StandardScaler + Linear Regression\nInput: seven features per link\n"
        "Output: predicted utilization for\nthe next observation")
    box(xm, yb, bw, bh, "5. Routing Computation",
        "Calculate link costs from predicted\nutilization and build a weighted graph\n"
        "Run Dijkstra's shortest-path algorithm")
    box(xl, yb, bw, bh, "6. Route Selection",
        "Compare candidate path costs\nSelect the minimum-cost path:\n"
        "Path 1: r1-r2-r4\nor Path 2: r1-r3-r4")

    top_cy = yt + bh / 2
    arrow((xl + bw + 0.08, top_cy), (xm - 0.08, top_cy), "link metrics")
    arrow((xm + bw + 0.08, top_cy), (xr - 0.08, top_cy), "telemetry CSV")
    arrow((xr + bw / 2, yt - 0.08), (xr + bw / 2, yb + bh + 0.08),
          "feature matrix", (0.85, 0))

    bottom_cy = yb + bh / 2
    arrow((xr - 0.08, bottom_cy), (xm + bw + 0.08, bottom_cy),
          "predictions")
    arrow((xm - 0.08, bottom_cy), (xl + bw + 0.08, bottom_cy),
          "path costs")

    ax.text(
        9, 1.30,
        "Prototype scope: route selection uses a collected telemetry snapshot; "
        "continuous automatic rerouting is future work.",
        ha="center", va="center", fontsize=10.5, color=BLACK
    )
    fig.tight_layout()
    return fig


def main():
    # Avoid saving to /mnt/c: write to the Linux home directory instead.
    output_dir = Path.home() / "PARP_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    png_path = output_dir / "PARP_System_Architecture.png"
    pdf_path = output_dir / "PARP_System_Architecture.pdf"

    fig = build_diagram()
    try:
        fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor=WHITE)
        fig.savefig(pdf_path, bbox_inches="tight", facecolor=WHITE)
    finally:
        plt.close(fig)

    print("Architecture diagram generated successfully.")
    print(f"PNG: {png_path}")
    print(f"PDF: {pdf_path}")
    print("To open the output folder from WSL, run:")
    print(f' explorer.exe "$(wslpath -w "{output_dir}")"')


if __name__ == "__main__":
    main()
"""
PARP System Architecture — landscape, monochrome.

Install:
    pip install matplotlib

Run:
    python generate_parp_architecture.py

IMPORTANT:
    Outputs are saved to ~/PARP_output instead of /mnt/c/... to avoid
    the Windows-mounted-drive OSError seen in some WSL setups.
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BLACK = "#111111"
WHITE = "#FFFFFF"


def build_diagram():
    fig, ax = plt.subplots(figsize=(18, 10))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, title, body):
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.06,rounding_size=0.10",
            linewidth=1.5, edgecolor=BLACK, facecolor=WHITE
        )
        ax.add_patch(patch)
        ax.text(
            x + w / 2, y + h - 0.25, title,
            ha="center", va="top", fontsize=13,
            fontweight="bold", color=BLACK, linespacing=1.15
        )
        ax.text(
            x + w / 2, y + h / 2 - 0.18, body,
            ha="center", va="center", fontsize=11.2,
            color=BLACK, linespacing=1.4
        )

    def arrow(start, end, label, offset=(0, 0.25)):
        ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=16,
            linewidth=1.5, color=BLACK
        ))
        ax.text(
            (start[0] + end[0]) / 2 + offset[0],
            (start[1] + end[1]) / 2 + offset[1],
            label, ha="center", va="center", fontsize=9.5,
            color=BLACK,
            bbox=dict(facecolor=WHITE, edgecolor="none", pad=1.5)
        )

    ax.text(
        9, 9.55,
        "System Architecture of Predictive Adaptive Routing Protocol (PARP)",
        ha="center", va="center", fontsize=19,
        fontweight="bold", color=BLACK
    )

    bw, bh = 4.55, 2.45
    xl, xm, xr = 0.55, 6.72, 12.89
    yt, yb = 6.15, 2.25

    box(xl, yt, bw, bh, "1. Network Environment",
        "Mininet topology\nSource: h1 | Destination: h2\n\n"
        "Path 1: r1-r2-r4 (10 Mbps)\nPath 2: r1-r3-r4 (20 Mbps)")
    box(xm, yt, bw, bh, "2. Telemetry Collection",
        "Generate traffic and collect link data\n\n"
        "Link utilization | RTT | Jitter\nInterface transmit-drop information")
    box(xr, yt, bw, bh, "3. Dataset & Feature Engineering",
        "Store telemetry observations in CSV\nClean and order samples\n"
        "Create utilization lag-1, lag-2,\nand utilization-change features")
    box(xr, yb, bw, bh, "4. ML Prediction",
        "StandardScaler + Linear Regression\nInput: seven features per link\n"
        "Output: predicted utilization for\nthe next observation")
    box(xm, yb, bw, bh, "5. Routing Computation",
        "Calculate link costs from predicted\nutilization and build a weighted graph\n"
        "Run Dijkstra's shortest-path algorithm")
    box(xl, yb, bw, bh, "6. Route Selection",
        "Compare candidate path costs\nSelect the minimum-cost path:\n"
        "Path 1: r1-r2-r4\nor Path 2: r1-r3-r4")

    top_cy = yt + bh / 2
    arrow((xl + bw + 0.08, top_cy), (xm - 0.08, top_cy), "link metrics")
    arrow((xm + bw + 0.08, top_cy), (xr - 0.08, top_cy), "telemetry CSV")
    arrow((xr + bw / 2, yt - 0.08), (xr + bw / 2, yb + bh + 0.08),
          "feature matrix", (0.85, 0))

    bottom_cy = yb + bh / 2
    arrow((xr - 0.08, bottom_cy), (xm + bw + 0.08, bottom_cy),
          "predictions")
    arrow((xm - 0.08, bottom_cy), (xl + bw + 0.08, bottom_cy),
          "path costs")

    ax.text(
        9, 1.30,
        "Prototype scope: route selection uses a collected telemetry snapshot; "
        "continuous automatic rerouting is future work.",
        ha="center", va="center", fontsize=10.5, color=BLACK
    )
    fig.tight_layout()
    return fig


def main():
    # Avoid saving to /mnt/c: write to the Linux home directory instead.
    output_dir = Path.home() / "PARP_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    png_path = output_dir / "PARP_System_Architecture.png"
    pdf_path = output_dir / "PARP_System_Architecture.pdf"

    fig = build_diagram()
    try:
        fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor=WHITE)
        fig.savefig(pdf_path, bbox_inches="tight", facecolor=WHITE)
    finally:
        plt.close(fig)

    print("Architecture diagram generated successfully.")
    print(f"PNG: {png_path}")
    print(f"PDF: {pdf_path}")
    print("To open the output folder from WSL, run:")
    print(f' explorer.exe "$(wslpath -w "{output_dir}")"')


if __name__ == "__main__":
    main()
