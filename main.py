#!/usr/bin/env python3
"""
Warehouse AGV Simulator – CLI entry point.

Usage:
  python main.py run --config config/config_template.json
  python main.py run --config config/config_medium.json --output results.json
  python main.py run --config config/config_medium.json --visualize --charts-dir ./charts
  python main.py run --config config/config_your_warehouse.json --traffic-control --visualize --charts-dir ./output
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
    results = sim.run(traffic_control_enabled=args.traffic_control)
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

    # Generate visualizations if requested
    if args.visualize:
        charts_dir = args.charts_dir or "./charts"
        os.makedirs(charts_dir, exist_ok=True)
        
        print(f"\n📊 Generating visualizations in {charts_dir}/...")
        visualizer = WarehouseVisualizer(config)
        
        try:
            # Cycle time breakdown chart
            cycle_breakdowns = {}
            if results.xpl_cycle:
                cycle_breakdowns["XPL_201"] = {
                    "total_time_s": results.xpl_cycle.total_time_s,
                    "components": {
                        "forward_travel_s": getattr(results.xpl_cycle, 'forward_travel_s', 0),
                        "reverse_travel_s": getattr(results.xpl_cycle, 'reverse_travel_s', 0),
                        "pickup_s": 30,
                        "dropoff_s": 30,
                        "turns_s": getattr(results.xpl_cycle, 'turns_s', 0),
                    }
                }
            if results.xqe_rack_cycle:
                cycle_breakdowns["XQE_122_Rack"] = {
                    "total_time_s": results.xqe_rack_cycle.total_time_s,
                    "components": {
                        "forward_travel_s": getattr(results.xqe_rack_cycle, 'forward_travel_s', 0),
                        "reverse_travel_s": getattr(results.xqe_rack_cycle, 'reverse_travel_s', 0),
                        "lift_up_s": getattr(results.xqe_rack_cycle, 'lift_up_s', 0),
                        "pickup_s": 30,
                        "dropoff_s": 30,
                        "turns_s": getattr(results.xqe_rack_cycle, 'turns_s', 0),
                    }
                }
            if results.xqe_stack_cycle:
                cycle_breakdowns["XQE_122_Stack"] = {
                    "total_time_s": results.xqe_stack_cycle.total_time_s,
                    "components": {
                        "forward_travel_s": getattr(results.xqe_stack_cycle, 'forward_travel_s', 0),
                        "reverse_travel_s": getattr(results.xqe_stack_cycle, 'reverse_travel_s', 0),
                        "lift_up_s": getattr(results.xqe_stack_cycle, 'lift_up_s', 0),
                        "pickup_s": 30,
                        "dropoff_s": 30,
                        "turns_s": getattr(results.xqe_stack_cycle, 'turns_s', 0),
                    }
                }
            
            if cycle_breakdowns:
                cycle_chart_path = os.path.join(charts_dir, "cycle_time_breakdown.png")
                visualizer.plot_cycle_time_breakdown(cycle_breakdowns, save_path=cycle_chart_path)
                print(f"  ✅ Cycle time breakdown → {cycle_chart_path}")
        except Exception as e:
            print(f"  ⚠️ Could not generate cycle breakdown chart: {e}")
        
        try:
            fleet_sizes = {}
            if results.xpl_fleet:
                fleet_sizes["XPL_201"] = results.xpl_fleet.fleet_size
            if results.xqe_rack_fleet:
                fleet_sizes["XQE_Rack"] = results.xqe_rack_fleet.fleet_size
            if results.xqe_stack_fleet:
                fleet_sizes["XQE_Stack"] = results.xqe_stack_fleet.fleet_size
            
            if fleet_sizes:
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.bar(fleet_sizes.keys(), fleet_sizes.values(), color=["#E74C3C", "#3498DB", "#2ECC71"], alpha=0.85)
                ax.set_title("Fleet Size by Vehicle Type", fontweight="bold", fontsize=14)
                ax.set_ylabel("Number of Vehicles", fontsize=12)
                ax.set_xlabel("AGV Type", fontsize=12)
                ax.grid(axis="y", alpha=0.3)
                
                for i, (k, v) in enumerate(fleet_sizes.items()):
                    ax.text(i, v + 0.1, str(v), ha="center", va="bottom", fontweight="bold")
                
                plt.tight_layout()
                fleet_chart_path = os.path.join(charts_dir, "fleet_composition.png")
                fig.savefig(fleet_chart_path, dpi=150, bbox_inches="tight")
                plt.close(fig)
                print(f"  ✅ Fleet composition → {fleet_chart_path}")
        except Exception as e:
            print(f"  ⚠️ Could not generate fleet chart: {e}")
        
        print(f"\n✨ All charts saved to {charts_dir}/")


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
                            help="Generate visualization charts")
    run_parser.add_argument("--traffic-control", action="store_true",
                            help="Enable traffic control simulation – models aisle queue wait "
                                 "times using XQE aisle-width rules "
                                 "(≥3.5 m → 2 XQEs simultaneous; 2.84–3.49 m → 1 XQE)")
    run_parser.add_argument("--charts-dir", default="./charts",
                            help="Directory to save chart images (default: ./charts)")
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
