"""
Publication-Quality Visualizer (PR-2 Pipeline)
================================================
300 DPI output, Wong (2011) color-blind-friendly palette.
"""
import os
from typing import Dict, List, Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from .fleet_sizer import FleetSizingResult

# Wong (2011) color-blind-friendly 8-color palette
WONG_PALETTE = {
    "black":   "#000000",
    "orange":  "#E69F00",
    "sky":     "#56B4E9",
    "green":   "#009E73",
    "yellow":  "#F0E442",
    "blue":    "#0072B2",
    "red":     "#D55E00",
    "pink":    "#CC79A7",
}

PUBLICATION_DPI = 300

AGV_COLORS = {
    "XPL_201": WONG_PALETTE["blue"],
    "XQE_122": WONG_PALETTE["orange"],
    "XNA_121": WONG_PALETTE["green"],
    "XNA_151": WONG_PALETTE["sky"],
}


class WarehouseVisualizer:
    """
    Publication-quality visualizations for warehouse simulation results.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def plot_fleet_summary(
        self,
        result: FleetSizingResult,
        save_path: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[str]:
        """
        Bar chart showing required AGVs per aisle.
        300 DPI, color-blind friendly.
        """
        if not HAS_MATPLOTLIB:
            return None

        if not result.aisle_results:
            return None

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle(
            title or f"Fleet Sizing: {result.warehouse_name}",
            fontsize=14, fontweight='bold'
        )

        ax1 = axes[0]
        aisle_names = [r.aisle_name for r in result.aisle_results]
        agv_counts = [r.required_agvs for r in result.aisle_results]
        colors = [AGV_COLORS.get(r.agv_type, WONG_PALETTE["black"]) for r in result.aisle_results]

        ax1.bar(aisle_names, agv_counts, color=colors, edgecolor='white', linewidth=0.5)
        ax1.set_xlabel("Aisle", fontsize=11)
        ax1.set_ylabel("AGVs Required", fontsize=11)
        ax1.set_title("Fleet Size per Aisle", fontsize=12)
        ax1.set_ylim(0, max(agv_counts) + 1)

        for i, r in enumerate(result.aisle_results):
            if r.is_bottleneck:
                ax1.bar(r.aisle_name, r.required_agvs,
                        color=AGV_COLORS.get(r.agv_type, WONG_PALETTE["black"]),
                        edgecolor=WONG_PALETTE["red"], linewidth=2)

        legend_elements = [
            mpatches.Patch(color=AGV_COLORS["XPL_201"], label="XPL_201"),
            mpatches.Patch(color=AGV_COLORS["XQE_122"], label="XQE_122"),
        ]
        ax1.legend(handles=legend_elements, loc='upper right', fontsize=9)

        ax2 = axes[1]
        cycle_times = [r.cycle_time_s for r in result.aisle_results]
        util_pcts = [r.utilization * 100 for r in result.aisle_results]

        ax2_twin = ax2.twinx()
        ax2.bar(aisle_names, cycle_times,
                color=[AGV_COLORS.get(r.agv_type, WONG_PALETTE["black"]) for r in result.aisle_results],
                alpha=0.7, label='Cycle time (s)')
        ax2_twin.plot(aisle_names, util_pcts, 'o-',
                      color=WONG_PALETTE["red"], linewidth=2, markersize=6, label='Utilization %')
        ax2_twin.axhline(y=result.utilization_target * 100,
                         color=WONG_PALETTE["red"], linestyle='--', alpha=0.5,
                         label=f'Target {result.utilization_target*100:.0f}%')

        ax2.set_xlabel("Aisle", fontsize=11)
        ax2.set_ylabel("Cycle Time (s)", fontsize=11)
        ax2_twin.set_ylabel("Utilization (%)", fontsize=11)
        ax2.set_title("Cycle Times & Utilization", fontsize=12)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, "fleet_summary.png")

        fig.savefig(save_path, dpi=PUBLICATION_DPI, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def plot_cycle_time_breakdown(
        self,
        result: FleetSizingResult,
        save_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Stacked bar showing cycle time breakdown per aisle.
        """
        if not HAS_MATPLOTLIB:
            return None

        if not result.aisle_results:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        aisle_names = [r.aisle_name for r in result.aisle_results]

        components = {}
        for r in result.aisle_results:
            comps = r.details.get("components", {})
            for key, val in comps.items():
                if isinstance(val, (int, float)) and key.endswith("_s"):
                    components.setdefault(key, []).append(float(val))

        if not components:
            plt.close(fig)
            return None

        comp_colors = list(WONG_PALETTE.values())
        bottom = [0.0] * len(aisle_names)

        for idx, (comp_name, values) in enumerate(components.items()):
            if len(values) == len(aisle_names):
                label = comp_name.replace("_s", "").replace("_", " ").title()
                ax.bar(aisle_names, values, bottom=bottom,
                       color=comp_colors[idx % len(comp_colors)],
                       label=label, alpha=0.85)
                bottom = [b + v for b, v in zip(bottom, values)]

        ax.set_xlabel("Aisle", fontsize=11)
        ax.set_ylabel("Time (seconds)", fontsize=11)
        ax.set_title("Cycle Time Breakdown per Aisle", fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9, bbox_to_anchor=(1.15, 1))

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, "cycle_breakdown.png")

        fig.savefig(save_path, dpi=PUBLICATION_DPI, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def generate_report(
        self,
        result: FleetSizingResult,
        output_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate all publication-quality charts and return file paths.
        """
        out = output_dir or self.output_dir
        os.makedirs(out, exist_ok=True)
        paths = {}

        p = self.plot_fleet_summary(result, os.path.join(out, "fleet_summary.png"))
        if p:
            paths["fleet_summary"] = p

        p = self.plot_cycle_time_breakdown(result, os.path.join(out, "cycle_breakdown.png"))
        if p:
            paths["cycle_breakdown"] = p

        return paths
