#!/usr/bin/env python3
"""
Warehouse AGV Simulator – CLI entry point.

Usage:
  python main.py run --config config/config_template.json
  python main.py run --config config/config_medium.json --output results.json
  python main.py run --config config/config_medium.json --visualize --charts-dir ./charts
  python main.py run --config config/config_medium.json --visualize --pdf report.pdf
  python main.py demo --example medium
  python main.py demo --example medium --throughput 50
"""
import argparse
import json
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.simulator import WarehouseSimulator, load_config
from src.visualization import WarehouseVisualizer

EXAMPLE_CONFIGS = {
    "small": "config/config_small.json",
    "medium": "config/config_medium.json",
    "large": "config/config_large.json",
    "template": "config/config_template.json",
}


def cmd_run(args):
    config = load_config(args.config)
    sim = WarehouseSimulator(config)
    results = sim.run()
    report = sim.full_report(results)
    print(report)

    if args.output:
        ext = os.path.splitext(args.output)[1].lower()
        with open(args.output, "w") as f:
            if ext == ".csv":
                f.write(results.to_csv())
            else:
                f.write(results.to_json())
        print(f"\nResults exported to: {args.output}")

    if args.visualize:
        charts_dir = args.charts_dir
        os.makedirs(charts_dir, exist_ok=True)

        viz = WarehouseVisualizer()

        fleet_results = [
            r for r in [results.xpl_fleet, results.xqe_rack_fleet, results.xqe_stack_fleet]
            if r is not None
        ]
        cycle_results = {}
        if results.xpl_cycle is not None:
            cycle_results["XPL_201\nHandover"] = results.xpl_cycle
        if results.xqe_rack_cycle is not None:
            cycle_results["XQE_122\nRack Storage"] = results.xqe_rack_cycle
        if results.xqe_stack_cycle is not None:
            cycle_results["XQE_122\nGnd Stacking"] = results.xqe_stack_cycle

        fleet_chart_path = os.path.join(charts_dir, "fleet_utilization.png")
        viz.plot_fleet_and_utilization(fleet_results, save_path=fleet_chart_path)
        print(f"Fleet chart saved to: {fleet_chart_path}")

        cycle_chart_path = os.path.join(charts_dir, "cycle_time_breakdown.png")
        viz.plot_cycle_time_phases(cycle_results, save_path=cycle_chart_path)
        print(f"Cycle time chart saved to: {cycle_chart_path}")

        if args.pdf:
            warehouse_name = os.path.splitext(os.path.basename(args.config))[0]
            viz.generate_simulation_pdf(
                fleet_results,
                cycle_results,
                output_path=args.pdf,
                warehouse_name=warehouse_name,
            )
            print(f"PDF report saved to: {args.pdf}")


def cmd_demo(args):
    example = args.example.lower()
    if example not in EXAMPLE_CONFIGS:
        print(f"Unknown example '{example}'. Available: {list(EXAMPLE_CONFIGS.keys())}")
        sys.exit(1)

    config_path = EXAMPLE_CONFIGS[example]
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)

    # Allow overriding throughput from the command line
    if args.throughput is not None:
        config.setdefault("Throughput_Configuration", {})["Total_Daily_Pallets"] = args.throughput

    sim = WarehouseSimulator(config)
    results = sim.run()
    print(sim.full_report(results))
    print(f"\nJSON summary:\n{results.to_json()}")


def main():
    parser = argparse.ArgumentParser(
        description="Warehouse AGV Simulator (XQE_122 & XPL_201)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run simulation from a config file")
    run_parser.add_argument("--config", required=True, help="Path to JSON config file")
    run_parser.add_argument("--output", default=None,
                            help="Export results to file (.json or .csv)")
    run_parser.add_argument("--visualize", action="store_true",
                            help="Generate matplotlib charts after the simulation")
    run_parser.add_argument("--charts-dir", default="./charts",
                            help="Directory for saving chart PNG files (default: ./charts)")
    run_parser.add_argument("--pdf", default=None,
                            help="Save a multi-page PDF report to this path")
    run_parser.set_defaults(func=cmd_run)

    # demo command
    demo_parser = subparsers.add_parser("demo", help="Run a built-in example")
    demo_parser.add_argument("--example", default="medium",
                             choices=list(EXAMPLE_CONFIGS.keys()),
                             help="Example scenario name")
    demo_parser.add_argument("--throughput", type=int, default=None,
                             help="Override total daily pallets")
    demo_parser.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()