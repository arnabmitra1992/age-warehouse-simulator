"""
Visualization Module
====================
Charts, graphs, and report generation for the warehouse AGV simulator.

Provides:
  - Warehouse layout graph plot (NetworkX + Matplotlib)
  - AGV utilization vs throughput chart
  - Fleet size comparison across AGV types
  - Aisle usage heatmap
  - Cycle time breakdown bar chart
  - Multi-page PDF report generation
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend – safe for servers and thesis export
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import networkx as nx
import numpy as np

from .agv_specs import AGV_SPECS
from .fleet_sizing import FleetSizingResult, AisleAnalysis

logger = logging.getLogger(__name__)

# Color scheme
COLORS = {
    "dock": "#E74C3C",
    "head_aisle_pt": "#3498DB",
    "aisle_entry": "#2ECC71",
    "aisle_exit": "#27AE60",
    "storage_position": "#BDC3C7",
    "edge_forward": "#2980B9",
    "edge_reverse": "#E67E22",
    "background": "#F8F9FA",
    "XQE_122": "#3498DB",
    "XPL_201": "#E74C3C",
    "XNA_121": "#2ECC71",
    "XNA_151": "#9B59B6",
}

NODE_SIZES = {
    "dock": 600,
    "head_aisle_pt": 200,
    "aisle_entry": 400,
    "aisle_exit": 300,
    "storage_position": 60,
}


class WarehouseVisualizer:
    """
    Generates matplotlib figures for warehouse layout, simulation results,
    and PDF reports.

    Parameters
    ----------
    layout : dict, optional
        Warehouse layout JSON (for dimension annotations).
    """

    def __init__(self, layout: Optional[dict] = None) -> None:
        self.layout = layout or {}

    # ------------------------------------------------------------------
    # Graph plot
    # ------------------------------------------------------------------

    def plot_warehouse_graph(
        self,
        graph,
        positions: Dict[str, Tuple[float, float]],
        title: str = "Warehouse Layout Graph",
        highlight_agv: Optional[str] = None,
        save_path: Optional[str] = None,
        show: bool = False,
    ) -> plt.Figure:
        """
        Plot the warehouse graph with colour-coded node types.

        Parameters
        ----------
        graph : nx.DiGraph
            The warehouse graph.
        positions : dict
            {node_id: (x, y)} mapping.
        title : str
            Plot title.
        highlight_agv : str, optional
            If set, highlight edges accessible to this AGV type.
        save_path : str, optional
            File path to save the figure (.png or .pdf).
        show : bool
            If True, display interactively.
        """
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_facecolor(COLORS["background"])
        fig.patch.set_facecolor(COLORS["background"])

        # Separate nodes by type
        node_groups: dict = {}
        for node, data in graph.nodes(data=True):
            nt = data.get("node_type", "unknown")
            if nt not in node_groups:
                node_groups[nt] = []
            node_groups[nt].append(node)

        # Draw nodes by type
        for nt, nodes in node_groups.items():
            color = COLORS.get(nt, "#95A5A6")
            size = NODE_SIZES.get(nt, 100)
            pos_subset = {n: positions[n] for n in nodes if n in positions}
            if pos_subset:
                nx.draw_networkx_nodes(
                    graph, pos_subset, nodelist=list(pos_subset.keys()),
                    node_color=color, node_size=size, alpha=0.85, ax=ax
                )

        # Draw edges
        fwd_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("forward", True)]
        rev_edges = [(u, v) for u, v, d in graph.edges(data=True) if not d.get("forward", True)]

        nx.draw_networkx_edges(
            graph, positions, edgelist=fwd_edges,
            edge_color=COLORS["edge_forward"], alpha=0.5,
            arrows=True, arrowsize=10, width=1.2, ax=ax
        )
        nx.draw_networkx_edges(
            graph, positions, edgelist=rev_edges,
            edge_color=COLORS["edge_reverse"], alpha=0.5,
            arrows=True, arrowsize=10, width=1.2, style="dashed", ax=ax
        )

        # Label only key nodes
        label_nodes = {
            n: n.replace("dock_", "").replace("aisle_entry_", "").replace("ha_start_", "")
            for n in graph.nodes
            if any(
                n.startswith(pfx)
                for pfx in ("dock_", "aisle_entry_", "aisle_exit_")
            )
        }
        pos_label = {n: positions[n] for n in label_nodes if n in positions}
        nx.draw_networkx_labels(graph, pos_label, labels=label_nodes,
                                font_size=7, font_color="#2C3E50", ax=ax)

        # Legend
        legend_handles = [
            mpatches.Patch(color=COLORS["dock"], label="Dock"),
            mpatches.Patch(color=COLORS["head_aisle_pt"], label="Head Aisle Point"),
            mpatches.Patch(color=COLORS["aisle_entry"], label="Aisle Entry"),
            mpatches.Patch(color=COLORS["storage_position"], label="Storage Position"),
            mpatches.Patch(color=COLORS["edge_forward"], label="Forward Travel"),
            mpatches.Patch(color=COLORS["edge_reverse"], label="Reverse Travel (Fork)"),
        ]
        ax.legend(handles=legend_handles, loc="upper right", fontsize=8,
                  fancybox=True, framealpha=0.9)

        ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel("X position (m)", fontsize=10)
        ax.set_ylabel("Y position (m)", fontsize=10)
        ax.grid(True, alpha=0.3, linestyle="--")

        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info("Graph saved to %s", save_path)
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # Fleet size comparison
    # ------------------------------------------------------------------

    def plot_fleet_comparison(
        self,
        fleet_result: FleetSizingResult,
        save_path: Optional[str] = None,
        show: bool = False,
    ) -> plt.Figure:
        """
        Bar chart comparing fleet sizes and utilizations across AGV types.
        """
        agv_types = sorted(fleet_result.fleet_size_per_agv.keys())
        fleet_sizes = [fleet_result.fleet_size_per_agv[a] for a in agv_types]
        utils = [fleet_result.utilization_per_agv.get(a, 0) * 100 for a in agv_types]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        fig.patch.set_facecolor(COLORS["background"])

        colors = [COLORS.get(a, "#95A5A6") for a in agv_types]
        bars1 = ax1.bar(agv_types, fleet_sizes, color=colors, alpha=0.85, edgecolor="white")
        ax1.set_title(
            f"Fleet Size Needed\n({fleet_result.tasks_per_hour:.0f} tasks/hr target)",
            fontweight="bold"
        )
        ax1.set_ylabel("Number of AGVs")
        ax1.set_ylim(0, max(fleet_sizes) * 1.3 if fleet_sizes else 5)
        for bar, val in zip(bars1, fleet_sizes):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     str(val), ha="center", va="bottom", fontweight="bold")

        bars2 = ax2.bar(agv_types, utils, color=colors, alpha=0.85, edgecolor="white")
        ax2.axhline(
            y=fleet_result.utilization_target * 100,
            color="#E74C3C", linestyle="--", linewidth=1.5,
            label=f"Target ({fleet_result.utilization_target * 100:.0f}%)"
        )
        ax2.set_title("Fleet Utilization", fontweight="bold")
        ax2.set_ylabel("Utilization (%)")
        ax2.set_ylim(0, 110)
        ax2.legend(fontsize=9)
        for bar, val in zip(bars2, utils):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     f"{val:.1f}%", ha="center", va="bottom", fontweight="bold")

        # Mark recommended AGV
        if fleet_result.recommended_agv and fleet_result.recommended_agv in agv_types:
            idx = agv_types.index(fleet_result.recommended_agv)
            bars1[idx].set_edgecolor("#F39C12")
            bars1[idx].set_linewidth(3)
            bars2[idx].set_edgecolor("#F39C12")
            bars2[idx].set_linewidth(3)

        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # Throughput vs fleet size
    # ------------------------------------------------------------------

    def plot_throughput_vs_fleet(
        self,
        sensitivity_data: Dict[str, List[Tuple[float, int, float]]],
        save_path: Optional[str] = None,
        show: bool = False,
    ) -> plt.Figure:
        """
        Plot fleet size vs throughput for multiple AGV types.

        Parameters
        ----------
        sensitivity_data : dict
            {agv_type: [(tasks_per_hour, fleet_size, utilization), ...]}
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        fig.patch.set_facecolor(COLORS["background"])

        for agv_type, data in sensitivity_data.items():
            if not data:
                continue
            tph_vals = [d[0] for d in data]
            fleet_vals = [d[1] for d in data]
            util_vals = [d[2] * 100 for d in data]
            color = COLORS.get(agv_type, "#95A5A6")
            ax1.plot(tph_vals, fleet_vals, marker="o", label=agv_type,
                     color=color, linewidth=2, markersize=5)
            ax2.plot(tph_vals, util_vals, marker="s", label=agv_type,
                     color=color, linewidth=2, markersize=5)

        ax1.set_title("Fleet Size vs Throughput", fontweight="bold")
        ax1.set_xlabel("Tasks per Hour")
        ax1.set_ylabel("Fleet Size (AGVs)")
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)

        ax2.axhline(y=80, color="#E74C3C", linestyle="--", linewidth=1.5,
                    label="Target 80%")
        ax2.set_title("Utilization vs Throughput", fontweight="bold")
        ax2.set_xlabel("Tasks per Hour")
        ax2.set_ylabel("Utilization (%)")
        ax2.set_ylim(0, 105)
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # Cycle time breakdown
    # ------------------------------------------------------------------

    def plot_cycle_time_breakdown(
        self,
        cycle_breakdowns: Dict[str, dict],
        save_path: Optional[str] = None,
        show: bool = False,
    ) -> plt.Figure:
        """
        Stacked bar chart showing cycle time component breakdown per AGV type.

        Parameters
        ----------
        cycle_breakdowns : dict
            {agv_type: cycle_result.to_dict()["components"]}
        """
        components = [
            ("forward_travel_s", "Forward Travel", "#3498DB"),
            ("reverse_travel_s", "Reverse Travel (Loaded)", "#E67E22"),
            ("lift_up_s", "Lift Up", "#9B59B6"),
            ("lift_down_s", "Lift Down", "#8E44AD"),
            ("pickup_s", "Pickup", "#2ECC71"),
            ("dropoff_s", "Dropoff", "#27AE60"),
            ("turns_s", "Turn Time", "#F39C12"),
            ("dock_positioning_s", "Dock Positioning", "#BDC3C7"),
        ]

        agv_types = list(cycle_breakdowns.keys())
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor(COLORS["background"])

        x = np.arange(len(agv_types))
        bottoms = np.zeros(len(agv_types))

        for key, label, color in components:
            values = [
                cycle_breakdowns[at].get("components", {}).get(key, 0)
                for at in agv_types
            ]
            if any(v > 0 for v in values):
                bars = ax.bar(x, values, bottom=bottoms, label=label,
                              color=color, alpha=0.85, edgecolor="white")
                bottoms += np.array(values)

        ax.set_xticks(x)
        ax.set_xticklabels(agv_types, fontsize=10)
        ax.set_title("Cycle Time Component Breakdown by AGV Type", fontweight="bold")
        ax.set_ylabel("Time (seconds)")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
        ax.grid(axis="y", alpha=0.3)

        # Add total labels
        for i, total in enumerate(bottoms):
            ax.text(i, total + 1, f"{total:.0f}s", ha="center",
                    va="bottom", fontsize=9, fontweight="bold")

        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # Heatmap
    # ------------------------------------------------------------------

    def plot_aisle_heatmap(
        self,
        aisle_usage: Dict[str, int],
        save_path: Optional[str] = None,
        show: bool = False,
    ) -> plt.Figure:
        """
        Horizontal bar chart showing relative aisle usage (traffic heatmap).
        """
        if not aisle_usage:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, "No aisle usage data available",
                    ha="center", va="center", transform=ax.transAxes)
            return fig

        sorted_aisles = sorted(aisle_usage.items(), key=lambda x: -x[1])
        aisles = [a[0] for a in sorted_aisles]
        counts = [a[1] for a in sorted_aisles]
        max_count = max(counts) if counts else 1

        fig, ax = plt.subplots(figsize=(10, max(4, len(aisles) * 0.4 + 1)))
        fig.patch.set_facecolor(COLORS["background"])

        # Color by intensity
        cmap = plt.cm.YlOrRd
        bar_colors = [cmap(c / max_count) for c in counts]
        bars = ax.barh(aisles, counts, color=bar_colors, edgecolor="white")

        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    str(count), va="center", fontsize=9)

        ax.set_xlabel("Number of Tasks")
        ax.set_title("Aisle Usage Heatmap (Task Count)", fontweight="bold")
        ax.grid(axis="x", alpha=0.3)

        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # PDF report
    # ------------------------------------------------------------------

    def generate_pdf_report(
        self,
        fleet_result: FleetSizingResult,
        graph,
        positions: Dict[str, Tuple[float, float]],
        sensitivity_data: Optional[Dict] = None,
        aisle_usage: Optional[Dict[str, int]] = None,
        output_path: str = "fleet_sizing_report.pdf",
        warehouse_name: str = "Warehouse",
    ) -> str:
        """
        Generate a multi-page PDF report suitable for a master thesis.

        Pages:
          1. Title page with summary
          2. Warehouse layout graph
          3. Fleet size comparison
          4. Cycle time breakdown
          5. Throughput vs fleet size (if sensitivity_data provided)
          6. Aisle heatmap (if aisle_usage provided)

        Returns
        -------
        str
            Path to the generated PDF.
        """
        with PdfPages(output_path) as pdf:
            # Page 1: Title / summary
            fig_title = self._make_title_page(fleet_result, warehouse_name)
            pdf.savefig(fig_title, bbox_inches="tight")
            plt.close(fig_title)

            # Page 2: Warehouse graph
            if graph and positions:
                fig_graph = self.plot_warehouse_graph(
                    graph, positions,
                    title=f"{warehouse_name} – Layout Graph"
                )
                pdf.savefig(fig_graph, bbox_inches="tight")
                plt.close(fig_graph)

            # Page 3: Fleet comparison
            fig_fleet = self.plot_fleet_comparison(fleet_result)
            pdf.savefig(fig_fleet, bbox_inches="tight")
            plt.close(fig_fleet)

            # Page 4: Cycle time breakdown
            breakdowns = {}
            for at, sim_res in fleet_result.simulation_results.items():
                if sim_res.cycle_time_breakdown:
                    breakdowns[at] = sim_res.cycle_time_breakdown
            if not breakdowns:
                # Use aisle analysis data
                for a in fleet_result.aisle_analyses:
                    for at, ct in a.cycle_times.items():
                        if at not in breakdowns:
                            breakdowns[at] = {"components": {"reverse_travel_s": ct}}
            if breakdowns:
                fig_cycles = self.plot_cycle_time_breakdown(breakdowns)
                pdf.savefig(fig_cycles, bbox_inches="tight")
                plt.close(fig_cycles)

            # Page 5: Sensitivity
            if sensitivity_data:
                fig_sens = self.plot_throughput_vs_fleet(sensitivity_data)
                pdf.savefig(fig_sens, bbox_inches="tight")
                plt.close(fig_sens)

            # Page 6: Heatmap
            if aisle_usage:
                fig_heat = self.plot_aisle_heatmap(aisle_usage)
                pdf.savefig(fig_heat, bbox_inches="tight")
                plt.close(fig_heat)

            # PDF metadata
            d = pdf.infodict()
            d["Title"] = f"AGV Fleet Sizing Report – {warehouse_name}"
            d["Author"] = "Warehouse AGV Simulator"
            d["Subject"] = "Fleet Sizing Analysis"
            d["Keywords"] = "AGV, warehouse, fleet sizing, simulation"

        logger.info("PDF report saved to %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _make_title_page(
        self, fleet_result: FleetSizingResult, warehouse_name: str
    ) -> plt.Figure:
        fig = plt.figure(figsize=(11, 8.5))
        fig.patch.set_facecolor("#2C3E50")
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.set_facecolor("#2C3E50")

        ax.text(0.5, 0.92, "AGV Fleet Sizing Report",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=24, fontweight="bold", color="white")
        ax.text(0.5, 0.84, warehouse_name,
                ha="center", va="center", transform=ax.transAxes,
                fontsize=18, color="#BDC3C7")
        ax.text(0.5, 0.76,
                f"Target Throughput: {fleet_result.tasks_per_hour:.0f} tasks/hour  |  "
                f"Target Utilization: {fleet_result.utilization_target * 100:.0f}%",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=13, color="#ECF0F1")

        # Summary table
        rows = []
        for at in sorted(fleet_result.fleet_size_per_agv):
            fl = fleet_result.fleet_size_per_agv[at]
            ct = fleet_result.cycle_time_per_agv.get(at, 0)
            util = fleet_result.utilization_per_agv.get(at, 0) * 100
            marker = " ★" if at == fleet_result.recommended_agv else ""
            rows.append(f"{at}{marker:<4}  Fleet: {fl}  Cycle: {ct:.0f}s  Util: {util:.1f}%")

        y_pos = 0.62
        for row in rows:
            ax.text(0.5, y_pos, row,
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=12, color="#ECF0F1", family="monospace")
            y_pos -= 0.07

        if fleet_result.recommended_agv:
            ax.text(0.5, y_pos - 0.04,
                    f"★ Recommended AGV: {fleet_result.recommended_agv}",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=14, color="#F39C12", fontweight="bold")

        ax.text(0.5, 0.06,
                "Generated by Warehouse AGV Fleet Sizing Simulator  |  "
                "EP Equipment AGV Models",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=9, color="#7F8C8D")
        return fig
