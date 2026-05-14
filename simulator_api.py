#!/usr/bin/env python3
"""
Minimal HTTP API for running the warehouse simulator from the UI.

Endpoints:
  GET  /health
  POST /simulate
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

from src.simulator import WarehouseSimulator


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def _run_simulation(
    config: Dict[str, Any], traffic_control: bool, random_seed: Optional[int] = None
) -> Tuple[Dict[str, Any], str, Optional[Dict[str, Any]]]:
    sim = WarehouseSimulator(config)
    results = sim.run(
        traffic_control_enabled=traffic_control, random_seed=random_seed
    )
    report = sim.full_report(results)
    result_dict = results.to_dict()
    traffic = None
    if results.traffic_model:
        aisles = []
        for aisle in results.traffic_model.aisles.values():
            aisles.append(
                {
                    "name": aisle.name,
                    "width_mm": aisle.width_mm,
                    "capacity": aisle.capacity,
                    "utilization": aisle.utilization,
                    "avg_wait_time_s": aisle.avg_wait_time_s,
                    "arrival_rate_per_hour": aisle.arrival_rate_per_hour,
                }
            )
        bottleneck = results.traffic_model.bottleneck_aisle()
        traffic = {
            "enabled": traffic_control,
            "aisles": aisles,
            "inbound_wait_overhead_s": results.traffic_model.total_wait_time_inbound_s(),
            "outbound_wait_overhead_s": results.traffic_model.total_wait_time_outbound_s(),
            "bottleneck": {
                "name": bottleneck.name if bottleneck else None,
                "utilization": bottleneck.utilization if bottleneck else None,
            },
        }
    return result_dict, report, traffic


class SimulatorHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        _json_response(self, 200, {"ok": True})

    def do_GET(self) -> None:
        if self.path == "/health":
            _json_response(self, 200, {"ok": True, "service": "age-warehouse-simulator"})
            return
        _json_response(self, 404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/simulate":
            _json_response(self, 404, {"ok": False, "error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            config = payload.get("config")
            traffic_control = bool(payload.get("traffic_control", False))
            workload_buckets = payload.get("workload_buckets")
            random_seed = payload.get("random_seed")
            if not isinstance(config, dict):
                _json_response(self, 400, {"ok": False, "error": "Body must include object field 'config'."})
                return
            if random_seed is not None:
                try:
                    random_seed = int(random_seed)
                except (TypeError, ValueError):
                    _json_response(self, 400, {"ok": False, "error": "'random_seed' must be an integer when provided."})
                    return
            if workload_buckets is not None:
                if not isinstance(workload_buckets, dict):
                    _json_response(self, 400, {"ok": False, "error": "'workload_buckets' must be an object when provided."})
                    return
                tc = config.setdefault("Throughput_Configuration", {})
                tc["Workload_Buckets"] = workload_buckets

            result_dict, report, traffic = _run_simulation(config, traffic_control, random_seed=random_seed)
            _json_response(
                self,
                200,
                {
                    "ok": True,
                    "result": result_dict,
                    "required_xpl_fleet": result_dict.get("fleet_sizes", {}).get("required_xpl_fleet"),
                    "report": report,
                    "traffic": traffic,
                },
            )
        except Exception as exc:
            _json_response(self, 500, {"ok": False, "error": str(exc)})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), SimulatorHandler)
    print("Simulator API listening on http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
