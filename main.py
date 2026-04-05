#!/usr/bin/env python3
"""
Warehouse AGV Fleet Sizing Simulator
======================================
Main entry point for the warehouse AGV fleet sizing simulator.

Supports three modes:
  1. demo       - Run with a built-in example warehouse (no setup needed)
  2. parse      - Parse a warehouse layout using Ollama AI or manual entry
  3. simulate   - Run fleet sizing simulation on a saved layout JSON
  4. interactive - Full interactive menu-driven session

Usage:
  python main.py demo
  python main.py demo --agv XQE_122 --throughput 30
  python main.py parse --text "my warehouse description..."
  python main.py parse --image /path/to/layout.png
  python main.py parse --manual
  python main.py simulate --layout examples/medium_warehouse.json --throughput 40
  python main.py interactive
"""

import argparse
import json
import logging
import os
import sys

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from src.agv_specs import AGV_SPECS, TASK_PARAMETERS, print_agv_summary
from src.reference_layouts import (
    SIMPLE_WAREHOUSE_JSON,
    MEDIUM_WAREHOUSE_JSON,
    COMPLEX_WAREHOUSE_JSON,
)
from src.layout_parser import LayoutParser, ManualLayoutBuilder, OllamaUnavailableError
from src.graph_generator import WarehouseGraph
from src.physics import AGVPhysics
from src.simulation_engine import SimulationEngine
from src.fleet_sizing import FleetSizingCalculator
from src.visualization import WarehouseVisualizer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_layout(path: str) -> dict:
    builder = ManualLayoutBuilder()
    return builder.load_from_file(path)


def _build_graph(layout: dict) -> WarehouseGraph:
    wg = WarehouseGraph()
    wg.build_from_layout(layout)
    return wg


def _run_sizing(
    layout: dict,
    agv_type: str,
    throughput: float,
    run_simulation: bool = True,
    simulation_hours: float = 4.0,
    output_dir: str = "output",
) -> None:
    """Core fleet sizing + visualization pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    wh_name = layout.get("warehouse", {}).get("name", "Warehouse")
    print(f"\n{'─' * 60}")
    print(f"  Warehouse: {wh_name}")
    print(f"  Target throughput: {throughput:.0f} tasks/hour")
    print(f"  AGV filter: {agv_type if agv_type != 'ALL' else 'all compatible types'}")
    print(f"{'─' * 60}")

    # Build graph
    wg = _build_graph(layout)
    print(f"\n{wg.summary()}\n")

    # Fleet sizing
    calc = FleetSizingCalculator(wg, layout)
    analyses = calc.analyse_aisles()
    calc.print_aisle_analysis(analyses)

    agv_filter = None if agv_type == "ALL" else agv_type
    result = calc.calculate_fleet_size(
        tasks_per_hour=throughput,
        agv_type=agv_filter,
        run_simulation=run_simulation,
        simulation_hours=simulation_hours,
    )
    result.print_report()

    # Print simulation results if available
    for at, sim_res in result.simulation_results.items():
        sim_res.print_summary()

    # Single task cycle breakdown (example)
    print("\n  === EXAMPLE TASK CYCLE BREAKDOWN ===")
    for at, ct in sorted(result.cycle_time_per_agv.items(), key=lambda x: x[1]):
        try:
            cycle = _example_cycle_breakdown(at, layout, wg)
            cycle.print_breakdown()
        except (ValueError, Exception) as exc:
            logger.debug("Could not compute cycle for %s: %s", at, exc)

    # Visualizations
    vis = WarehouseVisualizer(layout)
    positions = wg.get_node_positions()

    # Graph plot
    graph_path = os.path.join(output_dir, "warehouse_graph.png")
    vis.plot_warehouse_graph(wg.graph, positions,
                             title=f"{wh_name} – Warehouse Graph",
                             save_path=graph_path)
    print(f"\n  Layout graph saved → {graph_path}")

    # Fleet comparison
    fleet_path = os.path.join(output_dir, "fleet_comparison.png")
    vis.plot_fleet_comparison(result, save_path=fleet_path)
    print(f"  Fleet comparison saved → {fleet_path}")

    # Throughput sensitivity
    sens_data = {}
    tph_range = list(range(5, int(throughput * 2) + 1, max(1, int(throughput / 10))))
    for at in (result.fleet_size_per_agv.keys() if agv_filter is None else [agv_filter]):
        sens = calc.throughput_sensitivity(at, [float(t) for t in tph_range])
        if sens:
            sens_data[at] = sens

    if sens_data:
        sens_path = os.path.join(output_dir, "throughput_sensitivity.png")
        vis.plot_throughput_vs_fleet(sens_data, save_path=sens_path)
        print(f"  Throughput sensitivity saved → {sens_path}")

    # Aisle usage heatmap (from simulation if available)
    aisle_usage = {}
    for sim_res in result.simulation_results.values():
        for aisle, cnt in sim_res.aisle_usage_counts.items():
            aisle_usage[aisle] = aisle_usage.get(aisle, 0) + cnt
    if aisle_usage:
        heat_path = os.path.join(output_dir, "aisle_heatmap.png")
        vis.plot_aisle_heatmap(aisle_usage, save_path=heat_path)
        print(f"  Aisle heatmap saved → {heat_path}")

    # PDF report
    pdf_path = os.path.join(output_dir, "fleet_sizing_report.pdf")
    vis.generate_pdf_report(
        fleet_result=result,
        graph=wg.graph,
        positions=positions,
        sensitivity_data=sens_data if sens_data else None,
        aisle_usage=aisle_usage if aisle_usage else None,
        output_path=pdf_path,
        warehouse_name=wh_name,
    )
    print(f"  PDF report saved → {pdf_path}")

    # JSON results export
    json_path = os.path.join(output_dir, "fleet_sizing_results.json")
    with open(json_path, "w") as fh:
        json.dump(result.to_dict(), fh, indent=2)
    print(f"  JSON results saved → {json_path}\n")


def _example_cycle_breakdown(
    agv_type: str, layout: dict, wg: WarehouseGraph
) -> "TaskCycleResult":
    """Return a representative cycle result for an AGV type."""
    engine = SimulationEngine(wg, layout)
    for aisle in layout.get("storage_aisles", []):
        st = aisle.get("storage_type", "rack")
        name = aisle["name"]
        w = aisle.get("width", 2.84)
        spec = AGV_SPECS[agv_type]
        if st not in spec["storage_types"]:
            continue
        if w < spec["aisle_width"]:
            continue
        racks = aisle.get("racks", [])
        lift_h = max((r.get("height", 0.0) for r in racks), default=0.0) / 2.0
        return engine.calculate_single_task_cycle(agv_type, st, name, lift_h)
    raise ValueError(f"No compatible aisle found for {agv_type}")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_demo(args) -> None:
    """Run with a built-in example warehouse."""
    demo_layouts = {
        "simple": (SIMPLE_WAREHOUSE_JSON, "Simple 2-aisle warehouse"),
        "medium": (MEDIUM_WAREHOUSE_JSON, "Medium 4-aisle warehouse"),
        "complex": (COMPLEX_WAREHOUSE_JSON, "Complex 6-aisle warehouse"),
    }

    layout_key = getattr(args, "example", "medium")
    if layout_key not in demo_layouts:
        layout_key = "medium"

    layout, desc = demo_layouts[layout_key]
    print(f"\n  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║  WAREHOUSE AGV FLEET SIZING SIMULATOR – DEMO MODE   ║")
    print(f"  ╚══════════════════════════════════════════════════════╝")
    print(f"\n  Using: {desc}")

    print_agv_summary()

    agv_type = getattr(args, "agv", "ALL") or "ALL"
    throughput = getattr(args, "throughput", 30) or 30
    run_sim = not getattr(args, "no_sim", False)

    _run_sizing(
        layout=layout,
        agv_type=agv_type,
        throughput=float(throughput),
        run_simulation=run_sim,
        output_dir=getattr(args, "output", "output"),
    )


def cmd_parse(args) -> None:
    """Parse a warehouse layout using Ollama or manual entry."""
    builder = ManualLayoutBuilder()

    if getattr(args, "manual", False):
        layout = builder.interactive_build()
        out = getattr(args, "output_layout", "warehouse_layout.json")
        builder.save_to_file(layout, out)
        print(f"\n  Layout saved to {out}")
    elif getattr(args, "text", None):
        parser = LayoutParser(model=getattr(args, "model", "llama3.2"))
        try:
            layout = parser.parse_text(args.text)
            out = getattr(args, "output_layout", "warehouse_layout.json")
            builder.save_to_file(layout, out)
            print(f"\n  Layout extracted and saved to {out}")
            _print_validation(layout)
        except OllamaUnavailableError as e:
            print(f"\n  ⚠ {e}")
            sys.exit(1)
    elif getattr(args, "image", None):
        parser = LayoutParser(model=getattr(args, "model", "llava"))
        try:
            layout = parser.parse_image(args.image)
            out = getattr(args, "output_layout", "warehouse_layout.json")
            builder.save_to_file(layout, out)
            print(f"\n  Layout extracted from image and saved to {out}")
            _print_validation(layout)
        except OllamaUnavailableError as e:
            print(f"\n  ⚠ {e}")
            sys.exit(1)
    else:
        print("  Please specify --manual, --text, or --image")
        sys.exit(1)


def cmd_simulate(args) -> None:
    """Run fleet sizing simulation on a layout file."""
    layout_path = getattr(args, "layout", None)
    if not layout_path:
        print("  Please specify --layout <path>")
        sys.exit(1)
    layout = _load_layout(layout_path)
    agv_type = getattr(args, "agv", "ALL") or "ALL"
    throughput = getattr(args, "throughput", 30) or 30
    run_sim = not getattr(args, "no_sim", False)
    _run_sizing(
        layout=layout,
        agv_type=agv_type,
        throughput=float(throughput),
        run_simulation=run_sim,
        output_dir=getattr(args, "output", "output"),
    )


def cmd_interactive(args) -> None:
    """Full interactive menu-driven session."""
    print(f"\n  ╔══════════════════════════════════════════════════════════╗")
    print(f"  ║   WAREHOUSE AGV FLEET SIZING SIMULATOR – INTERACTIVE    ║")
    print(f"  ╚══════════════════════════════════════════════════════════╝\n")
    print_agv_summary()

    while True:
        print("\n  Main Menu:")
        print("    1. Run demo (built-in example warehouse)")
        print("    2. Parse warehouse layout (Ollama AI)")
        print("    3. Load existing warehouse layout JSON")
        print("    4. Manual warehouse configuration")
        print("    5. Show AGV specifications")
        print("    6. Exit")
        choice = input("\n  Select [1-6]: ").strip()

        if choice == "1":
            print("\n  Example layouts:")
            print("    a. Simple  (2 rack aisles, 2 docks)")
            print("    b. Medium  (4 mixed aisles, 4 docks)")
            print("    c. Complex (6 aisles, 2 head aisles, 6 docks)")
            sub = input("  Select [a/b/c, default=b]: ").strip().lower() or "b"
            layout_map = {"a": SIMPLE_WAREHOUSE_JSON, "b": MEDIUM_WAREHOUSE_JSON, "c": COMPLEX_WAREHOUSE_JSON}
            layout = layout_map.get(sub, MEDIUM_WAREHOUSE_JSON)
            throughput = float(input("  Target tasks/hour [30]: ") or 30)
            agv = input("  Restrict to AGV type (leave blank for all): ").strip() or "ALL"
            _run_sizing(layout, agv, throughput, run_simulation=True)

        elif choice == "2":
            desc = input("  Enter warehouse description (or press Enter for example): ").strip()
            if not desc:
                desc = "Simple warehouse, 40m wide, 50m long, 2 rack aisles each 40m deep and 2.84m wide, one head aisle 4m wide, inbound dock at west end, outbound dock at east end"
            model = input("  Ollama model [llama3.2]: ").strip() or "llama3.2"
            parser = LayoutParser(model=model)
            try:
                layout = parser.parse_text(desc)
                _print_validation(layout)
                save = input("  Save layout to file? [y/N]: ").strip().lower()
                if save == "y":
                    path = input("  File path [warehouse_layout.json]: ").strip() or "warehouse_layout.json"
                    ManualLayoutBuilder().save_to_file(layout, path)
                throughput = float(input("  Target tasks/hour [30]: ") or 30)
                agv = input("  Restrict to AGV type (blank for all): ").strip() or "ALL"
                _run_sizing(layout, agv, throughput, run_simulation=True)
            except OllamaUnavailableError as e:
                print(f"\n  ⚠ {e}")

        elif choice == "3":
            path = input("  Layout JSON path: ").strip()
            if not os.path.exists(path):
                print(f"  File not found: {path}")
                continue
            layout = _load_layout(path)
            throughput = float(input("  Target tasks/hour [30]: ") or 30)
            agv = input("  Restrict to AGV type (blank for all): ").strip() or "ALL"
            _run_sizing(layout, agv, throughput, run_simulation=True)

        elif choice == "4":
            builder = ManualLayoutBuilder()
            layout = builder.interactive_build()
            path = input("  Save to file [warehouse_layout.json]: ").strip() or "warehouse_layout.json"
            builder.save_to_file(layout, path)
            throughput = float(input("  Target tasks/hour [30]: ") or 30)
            agv = input("  Restrict to AGV type (blank for all): ").strip() or "ALL"
            _run_sizing(layout, agv, throughput, run_simulation=True)

        elif choice == "5":
            print_agv_summary()

        elif choice == "6":
            print("\n  Goodbye! 👋\n")
            break
        else:
            print("  Invalid choice. Please enter 1–6.")


def _print_validation(layout: dict) -> None:
    val = layout.get("_validation", {})
    errors = val.get("schema_errors", [])
    warnings = val.get("agv_warnings", [])
    if errors:
        print("\n  ⚠ Schema issues:")
        for e in errors:
            print(f"    • {e}")
    if warnings:
        print("\n  ⚠ AGV constraint warnings:")
        for w in warnings:
            print(f"    • {w}")
    if not errors and not warnings:
        print("\n  ✓ Layout validated successfully.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Warehouse AGV Fleet Sizing Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py demo
  python main.py demo --example complex --agv XNA_121 --throughput 50
  python main.py parse --text "warehouse 40x60m, 3 rack aisles..."
  python main.py parse --image layout.png --model llava
  python main.py parse --manual --output-layout my_warehouse.json
  python main.py simulate --layout my_warehouse.json --throughput 40 --agv XQE_122
  python main.py interactive
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # -- demo --
    p_demo = subparsers.add_parser("demo", help="Run with a built-in example warehouse")
    p_demo.add_argument("--example", choices=["simple", "medium", "complex"],
                        default="medium", help="Built-in example to use (default: medium)")
    p_demo.add_argument("--agv", metavar="AGV_TYPE",
                        help="Restrict to a specific AGV type (e.g. XQE_122)")
    p_demo.add_argument("--throughput", type=float, default=30,
                        help="Target tasks per hour (default: 30)")
    p_demo.add_argument("--no-sim", action="store_true",
                        help="Skip full simulation (faster, analytical only)")
    p_demo.add_argument("--output", default="output",
                        help="Output directory for charts and reports (default: output/)")

    # -- parse --
    p_parse = subparsers.add_parser("parse", help="Parse a warehouse layout")
    p_parse_grp = p_parse.add_mutually_exclusive_group(required=True)
    p_parse_grp.add_argument("--text", help="Warehouse text description")
    p_parse_grp.add_argument("--image", help="Path to warehouse image file")
    p_parse_grp.add_argument("--manual", action="store_true",
                             help="Build layout interactively")
    p_parse.add_argument("--model", default="llama3.2",
                         help="Ollama model name (default: llama3.2)")
    p_parse.add_argument("--output-layout", default="warehouse_layout.json",
                         help="Path to save extracted layout JSON")

    # -- simulate --
    p_sim = subparsers.add_parser("simulate", help="Run fleet sizing on a layout JSON")
    p_sim.add_argument("--layout", required=True, help="Path to warehouse layout JSON")
    p_sim.add_argument("--agv", metavar="AGV_TYPE",
                       help="Restrict to a specific AGV type")
    p_sim.add_argument("--throughput", type=float, default=30,
                       help="Target tasks per hour (default: 30)")
    p_sim.add_argument("--no-sim", action="store_true",
                       help="Skip full simulation (analytical only)")
    p_sim.add_argument("--output", default="output",
                       help="Output directory")

    # -- run (PR-2 pipeline: mm-based JSON config, separate inbound/outbound) --
    p_run = subparsers.add_parser(
        "run",
        help="Run fleet sizing with separate inbound/outbound throughput (mm-based JSON config)",
    )
    p_run.add_argument("--config", required=True,
                       help="Path to warehouse config JSON (mm-based distances)")
    p_run.add_argument("--inbound-throughput", dest="inbound_throughput",
                       type=int, default=None,
                       help="Inbound daily tasks (overrides config value)")
    p_run.add_argument("--outbound-throughput", dest="outbound_throughput",
                       type=int, default=None,
                       help="Outbound daily tasks (overrides config value)")
    p_run.add_argument("--inbound-hours", dest="inbound_hours",
                       type=float, default=None,
                       help="Inbound operating hours per day (overrides config)")
    p_run.add_argument("--outbound-hours", dest="outbound_hours",
                       type=float, default=None,
                       help="Outbound operating hours per day (overrides config)")
    p_run.add_argument("--inbound-util", dest="inbound_util",
                       type=float, default=None,
                       help="Inbound utilization target 0–1 (overrides config)")
    p_run.add_argument("--outbound-util", dest="outbound_util",
                       type=float, default=None,
                       help="Outbound utilization target 0–1 (overrides config)")
    p_run.add_argument("--output", default="output",
                       help="Output directory for charts and JSON report (default: output/)")
    p_run.add_argument("--no-vis", action="store_true",
                       help="Skip visualization (analytical report only)")

    # -- interactive --
    subparsers.add_parser("interactive", help="Full interactive menu session")

    return parser


def cmd_run(args) -> None:
    """Run the PR-2 pipeline (mm-based JSON config, separate inbound/outbound throughput)."""
    from src.simulator import WarehouseSimulator

    config_path = getattr(args, "config", None)
    if not config_path:
        print("  Please specify --config <path>")
        import sys as _sys
        _sys.exit(1)

    print(f"\n  ╔══════════════════════════════════════════════════════════╗")
    print(f"  ║   WAREHOUSE AGV FLEET SIZING SIMULATOR – RUN MODE       ║")
    print(f"  ╚══════════════════════════════════════════════════════════╝\n")

    sim = WarehouseSimulator(config_path=config_path)
    sim.print_capacity_summary()

    report = sim.run(
        inbound_tasks=getattr(args, "inbound_throughput", None),
        outbound_tasks=getattr(args, "outbound_throughput", None),
        inbound_hours=getattr(args, "inbound_hours", None),
        outbound_hours=getattr(args, "outbound_hours", None),
        inbound_utilization=getattr(args, "inbound_util", None),
        outbound_utilization=getattr(args, "outbound_util", None),
    )
    report.print_report()

    output_dir = getattr(args, "output", "output")
    json_path = sim.save_report(report, output_dir=output_dir)
    print(f"  JSON report saved → {json_path}")

    if not getattr(args, "no_vis", False):
        sim.visualize(report, output_dir=output_dir)
        print(f"  Charts saved → {output_dir}/")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None or args.command == "interactive":
        cmd_interactive(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "parse":
        cmd_parse(args)
    elif args.command == "simulate":
        cmd_simulate(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
