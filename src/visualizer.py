"""
Simulator Visualizer Module
============================
Publication-quality charts for the warehouse AGV simulator.

All charts are saved at 300 DPI using a colour-blind-friendly 8-colour palette
(Wong, 2011) and consistent global rcParams for academic publication quality.
"""

from __future__ import annotations

import os
from typing import Optional, Dict, List

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False

from .warehouse_layout import WarehouseConfig
from .fleet_sizer import FleetSizingReport

# ---------------------------------------------------------------------------
# Publication constants
# ---------------------------------------------------------------------------

PUBLICATION_DPI = 300

#: Wong (2011) colour-blind-friendly 8-colour palette
CB_PALETTE: Dict[str, str] = {
    "black":      "#000000",
    "orange":     "#E69F00",
    "sky_blue":   "#56B4E9",
    "green":      "#009E73",
    "yellow":     "#F0E442",
    "blue":       "#0072B2",
    "vermillion": "#D55E00",
    "pink":       "#CC79A7",
}

_COLORS = list(CB_PALETTE.values())

if _MATPLOTLIB_AVAILABLE:
    plt.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": PUBLICATION_DPI,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.figsize": (8, 5),
        "axes.grid": True,
        "grid.alpha": 0.4,
    })


# ---------------------------------------------------------------------------
# Visualizer class
# ---------------------------------------------------------------------------

class SimulatorVisualizer:
    """
    Generates publication-quality matplotlib figures for AGV fleet sizing.

    Parameters
    ----------
    config : WarehouseConfig
        The warehouse configuration (used for layout annotations).
    """

    def __init__(self, config: WarehouseConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all(
        self,
        report: FleetSizingReport,
        output_dir: str = "output",
    ) -> List[str]:
        """
        Generate all charts and return list of saved file paths.
        """
        if not _MATPLOTLIB_AVAILABLE:
            print("  ⚠ matplotlib not available – skipping visualizations.")
            return []

        os.makedirs(output_dir, exist_ok=True)
        saved = []

        try:
            p = self.plot_fleet_composition(report, output_dir)
            if p:
                saved.append(p)
        except Exception as exc:
            print(f"  ⚠ fleet_composition chart failed: {exc}")

        try:
            p = self.plot_cycle_times(report, output_dir)
            if p:
                saved.append(p)
        except Exception as exc:
            print(f"  ⚠ cycle_times chart failed: {exc}")

        try:
            p = self.plot_workflow_diagram(report, output_dir)
            if p:
                saved.append(p)
        except Exception as exc:
            print(f"  ⚠ workflow_diagram chart failed: {exc}")

        return saved

    def plot_fleet_composition(
        self,
        report: FleetSizingReport,
        output_dir: str = "output",
    ) -> Optional[str]:
        """Bar chart of fleet requirements by AGV type and direction."""
        if not _MATPLOTLIB_AVAILABLE:
            return None

        reqs = report.fleet_requirements
        if not reqs:
            return None

        labels = [f"{r.agv_type}\n{r.direction}/{r.storage_type}" for r in reqs]
        sizes = [r.fleet_size for r in reqs]
        colors = [
            CB_PALETTE["blue"] if r.agv_type == "XQE_122"
            else CB_PALETTE["orange"] if r.agv_type == "XPL_201"
            else CB_PALETTE["vermillion"]
            for r in reqs
        ]

        fig, ax = plt.subplots(figsize=(max(8, len(reqs) * 1.5), 5))
        bars = ax.bar(labels, sizes, color=colors, edgecolor="white", linewidth=0.8)
        ax.set_title(f"Fleet Composition – {self.config.name}", fontweight="bold")
        ax.set_ylabel("Number of AGVs")
        ax.set_xlabel("AGV Type / Workflow")

        for bar, val in zip(bars, sizes):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                str(val),
                ha="center", va="bottom", fontsize=9,
            )

        legend_patches = [
            mpatches.Patch(color=CB_PALETTE["blue"], label="XQE_122 (storage + short haul)"),
            mpatches.Patch(color=CB_PALETTE["orange"], label="XPL_201 (long haul / handover)"),
            mpatches.Patch(color=CB_PALETTE["vermillion"], label="XNA (narrow aisle)"),
        ]
        ax.legend(handles=legend_patches, loc="upper right")

        path = os.path.join(output_dir, "fleet_composition.png")
        fig.tight_layout()
        fig.savefig(path, dpi=PUBLICATION_DPI)
        plt.close(fig)
        return path

    def plot_cycle_times(
        self,
        report: FleetSizingReport,
        output_dir: str = "output",
    ) -> Optional[str]:
        """Horizontal bar chart of average cycle times per workflow."""
        if not _MATPLOTLIB_AVAILABLE:
            return None

        wcts = [
            report.inbound_rack_wct,
            report.inbound_stacking_wct,
            report.outbound_rack_wct,
            report.outbound_stacking_wct,
        ]
        wcts = [w for w in wcts if w is not None]
        if not wcts:
            return None

        labels = [f"{w.direction}/{w.storage_type}" for w in wcts]
        times_min = [w.avg_cycle_time_s / 60.0 for w in wcts]
        colors = [
            CB_PALETTE["sky_blue"] if w.direction == "inbound" else CB_PALETTE["green"]
            for w in wcts
        ]

        fig, ax = plt.subplots(figsize=(8, max(4, len(wcts) * 0.9)))
        bars = ax.barh(labels, times_min, color=colors, edgecolor="white", linewidth=0.8)
        ax.set_title(f"Average Cycle Times – {self.config.name}", fontweight="bold")
        ax.set_xlabel("Cycle Time (minutes)")

        for bar, val in zip(bars, times_min):
            ax.text(
                bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f} min", va="center", fontsize=9,
            )

        legend_patches = [
            mpatches.Patch(color=CB_PALETTE["sky_blue"], label="Inbound"),
            mpatches.Patch(color=CB_PALETTE["green"], label="Outbound"),
        ]
        ax.legend(handles=legend_patches)

        path = os.path.join(output_dir, "cycle_times.png")
        fig.tight_layout()
        fig.savefig(path, dpi=PUBLICATION_DPI)
        plt.close(fig)
        return path

    def plot_workflow_diagram(
        self,
        report: FleetSizingReport,
        output_dir: str = "output",
    ) -> Optional[str]:
        """Simple text-based workflow diagram rendered as a figure."""
        if not _MATPLOTLIB_AVAILABLE:
            return None

        cfg = self.config
        rack_compat = report.rack_compatibility

        lines = []
        lines.append(f"Warehouse: {cfg.name}")
        lines.append("")

        if rack_compat:
            if rack_compat.is_ok:
                if rack_compat.agv_type == "XNA":
                    lines.append("INBOUND RACK (XNA – ALWAYS HANDOVER):")
                    lines.append("  Inbound → [XPL_201] → Handover → [XNA] → Rack ✅")
                    lines.append("OUTBOUND RACK (XNA – ALWAYS HANDOVER):")
                    lines.append("  Rack → [XNA] → Handover → [XPL_201] → Outbound ✅")
                else:
                    d = cfg.inbound_to_rack_handover_m
                    hv = "WITH HANDOVER" if d >= 50 else "NO HANDOVER"
                    lines.append(f"INBOUND RACK (XQE – {hv}):")
                    if d >= 50:
                        lines.append("  Inbound → [XPL_201] → Handover → [XQE_122] → Rack ✅")
                    else:
                        lines.append("  Inbound → [XQE_122] → Rack ✅")
                    d_ob = cfg.rack_handover_to_outbound_m
                    hv_ob = "WITH HANDOVER" if d_ob >= 50 else "NO HANDOVER"
                    lines.append(f"OUTBOUND RACK (XQE – {hv_ob}):")
                    if d_ob >= 50:
                        lines.append("  Rack → [XQE_122] → Handover → [XPL_201] → Outbound ✅")
                    else:
                        lines.append("  Rack → [XQE_122] → Outbound ✅")
            else:
                lines.append(f"RACK: ❌ {rack_compat.note}")

        lines.append("")
        d_stk_ib = cfg.inbound_to_stacking_handover_m
        hv_stk = "WITH HANDOVER" if d_stk_ib >= 50 else "NO HANDOVER"
        lines.append(f"INBOUND STACKING (XQE – {hv_stk}):")
        if d_stk_ib >= 50:
            lines.append("  Inbound → [XPL_201] → Handover → [XQE_122] → Stacking ✅")
        else:
            lines.append("  Inbound → [XQE_122] → Stacking ✅")

        d_stk_ob = cfg.stacking_handover_to_outbound_m
        hv_stk_ob = "WITH HANDOVER" if d_stk_ob >= 50 else "NO HANDOVER"
        lines.append(f"OUTBOUND STACKING (XQE – {hv_stk_ob}):")
        if d_stk_ob >= 50:
            lines.append("  Stacking → [XQE_122] → Handover → [XPL_201] → Outbound ✅")
        else:
            lines.append("  Stacking → [XQE_122] → Outbound ✅")

        fig, ax = plt.subplots(figsize=(10, max(4, len(lines) * 0.45)))
        ax.axis("off")
        ax.text(
            0.02, 0.98,
            "\n".join(lines),
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            fontfamily="monospace",
        )
        ax.set_title("Workflow Decision Diagram", fontweight="bold", pad=12)

        path = os.path.join(output_dir, "workflow_diagram.png")
        fig.tight_layout()
        fig.savefig(path, dpi=PUBLICATION_DPI, bbox_inches="tight")
        plt.close(fig)
        return path
