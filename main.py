#!/usr/bin/env python3
"""
Warehouse AGV Simulator – CLI entry point.

Usage:
  python main.py run --config config/config_template.json
  python main.py run --config config/config_medium.json --output results.json
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
