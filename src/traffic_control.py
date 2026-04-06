"""
Traffic control simulation for the warehouse.

Implements aisle capacity rules for XQE_122:
  - aisle_width < 2840 mm   : cannot operate
  - 2840 mm ≤ width < 3500 mm : single XQE at a time (queue if busy)
  - width ≥ 3500 mm          : two XQEs can pass simultaneously (bidirectional)

Queue wait times are estimated analytically using an M/D/c queuing model
(Poisson arrivals, deterministic service, c servers).  For c=1 the Pollaczek–
Khinchine formula applies; for c=2 the Erlang-C approximation is used.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .warehouse_layout import (
    AisleWidths,
    XQE_MIN_AISLE_WIDTH_MM,
    XQE_BIDIRECTIONAL_WIDTH_MM,
)


@dataclass
class TrafficControlConfig:
    """Configuration for the traffic control simulation."""
    enabled: bool = True
    xqe_min_aisle_width_mm: float = XQE_MIN_AISLE_WIDTH_MM
    xqe_bidirectional_width_mm: float = XQE_BIDIRECTIONAL_WIDTH_MM


@dataclass
class AisleMetrics:
    """Traffic metrics for a single aisle."""
    name: str
    width_mm: float
    capacity: int               # max simultaneous XQEs
    arrival_rate_per_hour: float = 0.0   # AGV passes per hour
    traverse_time_s: float = 0.0         # typical time to traverse aisle (s)

    @property
    def utilization(self) -> float:
        """Traffic intensity ρ = λ / (μ × c)."""
        if self.capacity <= 0 or self.traverse_time_s <= 0:
            return 0.0
        mu = 3600.0 / self.traverse_time_s   # service rate per server (passes/h)
        return self.arrival_rate_per_hour / (mu * self.capacity)

    @property
    def avg_wait_time_s(self) -> float:
        """
        Estimated average queue wait time (seconds) using the Pollaczek–Khinchine
        mean value formula (M/D/1) for single-server aisles, or Erlang-C
        approximation for two-server aisles.
        """
        if self.capacity <= 0 or self.traverse_time_s <= 0:
            return 0.0
        rho = self.utilization
        if rho <= 0:
            return 0.0
        if rho >= 1.0:
            # Overloaded – queue grows without bound; cap at a high value
            return self.traverse_time_s * 10.0
        if self.capacity == 1:
            # M/D/1: Wq = rho * D / (2 * (1 - rho))  where D = service time
            return (rho * self.traverse_time_s) / (2.0 * (1.0 - rho))
        # c = 2: Erlang-C approximation
        # C(c, rho_total) = P(wait) for M/M/c; use as upper bound for M/D/c
        rho_total = rho  # already ρ = λ/(cμ)
        # Erlang-C probability of waiting
        c = self.capacity
        a = self.arrival_rate_per_hour / (3600.0 / self.traverse_time_s)  # total offered load
        erlang_c = _erlang_c(c, a)
        mu = 3600.0 / self.traverse_time_s
        wq = erlang_c / (c * mu - self.arrival_rate_per_hour / 3600.0)
        # Convert wq from hours to seconds
        return wq * 3600.0

    def summary(self) -> str:
        cap_str = f"{self.capacity}" if self.capacity > 0 else "BLOCKED"
        return (
            f"  {self.name:<22} width={self.width_mm:.0f}mm  "
            f"cap={cap_str}  "
            f"ρ={self.utilization:.2f}  "
            f"avg_wait={self.avg_wait_time_s:.1f}s"
        )


def _erlang_c(c: int, a: float) -> float:
    """
    Erlang-C formula: probability an arriving customer has to wait in
    an M/M/c queue with offered load ``a`` and ``c`` servers.

    ``a`` must be < ``c`` for stability.
    """
    if a <= 0:
        return 0.0
    if a >= c:
        return 1.0   # overloaded
    # Numerator: a^c / (c! * (1 - a/c))
    numerator = (a ** c) / (math.factorial(c) * (1.0 - a / c))
    # Denominator: sum_{k=0}^{c-1} a^k / k!  + numerator
    summation = sum((a ** k) / math.factorial(k) for k in range(c))
    denominator = summation + numerator
    return numerator / denominator if denominator > 0 else 0.0


class TrafficControlModel:
    """
    Warehouse-level traffic model combining all aisles.

    Parameters
    ----------
    aisle_widths : AisleWidths
        Physical aisle widths.
    config : TrafficControlConfig
        Traffic control parameters.
    total_agv_count : int
        Total number of AGVs in the fleet (used for arrival rate estimation).
    inbound_cycle_s : float
        Average inbound cycle time (seconds).
    outbound_cycle_s : float
        Average outbound cycle time (seconds).
    operating_hours : float
        Daily operating hours.
    """

    INBOUND_AISLE_NAME = "Inbound Access"
    HEAD_AISLE_NAME = "Head Aisle"
    OUTBOUND_AISLE_NAME = "Outbound Access"

    def __init__(
        self,
        aisle_widths: AisleWidths,
        config: TrafficControlConfig,
        total_agv_count: int = 1,
        inbound_cycle_s: float = 120.0,
        outbound_cycle_s: float = 180.0,
        operating_hours: float = 16.0,
    ):
        self.aisle_widths = aisle_widths
        self.config = config
        self.total_agv_count = total_agv_count
        self.inbound_cycle_s = inbound_cycle_s
        self.outbound_cycle_s = outbound_cycle_s
        self.operating_hours = operating_hours
        self._aisles: Dict[str, AisleMetrics] = {}
        self._build_aisle_models()

    def _build_aisle_models(self) -> None:
        """Construct AisleMetrics for each aisle."""
        total_daily_moves = (
            self.total_agv_count
            * (3600.0 * self.operating_hours)
            / max(1.0, (self.inbound_cycle_s + self.outbound_cycle_s) / 2.0)
        )
        passes_per_hour = total_daily_moves / self.operating_hours
        # Each inbound cycle uses the inbound aisle once (loaded) + once empty.
        # Each outbound cycle uses inbound aisle (empty retrieval) + head aisle
        # (twice) + outbound aisle (loaded + empty).
        inbound_aisle_passes = passes_per_hour * 2  # in + out per cycle
        head_aisle_passes = passes_per_hour * 2      # crosses per outbound cycle
        outbound_aisle_passes = passes_per_hour * 2  # in + out per outbound cycle

        inbound_traverse_s = max(1.0, self.inbound_cycle_s * 0.05)
        head_traverse_s = max(1.0, self.inbound_cycle_s * 0.03)
        outbound_traverse_s = max(1.0, self.outbound_cycle_s * 0.05)

        self._aisles[self.INBOUND_AISLE_NAME] = AisleMetrics(
            name=self.INBOUND_AISLE_NAME,
            width_mm=self.aisle_widths.inbound_access_width_mm,
            capacity=self.aisle_widths.inbound_capacity,
            arrival_rate_per_hour=inbound_aisle_passes,
            traverse_time_s=inbound_traverse_s,
        )
        self._aisles[self.HEAD_AISLE_NAME] = AisleMetrics(
            name=self.HEAD_AISLE_NAME,
            width_mm=self.aisle_widths.head_aisle_width_mm,
            capacity=self.aisle_widths.head_aisle_capacity,
            arrival_rate_per_hour=head_aisle_passes,
            traverse_time_s=head_traverse_s,
        )
        self._aisles[self.OUTBOUND_AISLE_NAME] = AisleMetrics(
            name=self.OUTBOUND_AISLE_NAME,
            width_mm=self.aisle_widths.outbound_access_width_mm,
            capacity=self.aisle_widths.outbound_capacity,
            arrival_rate_per_hour=outbound_aisle_passes,
            traverse_time_s=outbound_traverse_s,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def aisles(self) -> Dict[str, AisleMetrics]:
        return self._aisles

    def total_wait_time_inbound_s(self) -> float:
        """Total estimated wait time per inbound cycle (s)."""
        if not self.config.enabled:
            return 0.0
        return self._aisles[self.INBOUND_AISLE_NAME].avg_wait_time_s

    def total_wait_time_outbound_s(self) -> float:
        """Total estimated wait time per outbound cycle (s)."""
        if not self.config.enabled:
            return 0.0
        return (
            self._aisles[self.INBOUND_AISLE_NAME].avg_wait_time_s
            + self._aisles[self.HEAD_AISLE_NAME].avg_wait_time_s * 2
            + self._aisles[self.OUTBOUND_AISLE_NAME].avg_wait_time_s
        )

    def bottleneck_aisle(self) -> Optional[AisleMetrics]:
        """Return the aisle with the highest utilization."""
        if not self._aisles:
            return None
        return max(self._aisles.values(), key=lambda a: a.utilization)

    def report(self) -> str:
        lines = ["TRAFFIC CONTROL ANALYSIS", "=" * 60]
        for m in self._aisles.values():
            lines.append(m.summary())
        bn = self.bottleneck_aisle()
        if bn:
            lines.append(f"\n  Bottleneck: {bn.name} (ρ={bn.utilization:.2f})")
        lines.append(
            f"  Inbound wait overhead  : {self.total_wait_time_inbound_s():.1f}s/cycle"
        )
        lines.append(
            f"  Outbound wait overhead : {self.total_wait_time_outbound_s():.1f}s/cycle"
        )
        return "\n".join(lines)


def traffic_control_config_from_dict(d: dict) -> TrafficControlConfig:
    """Create TrafficControlConfig from a configuration dictionary."""
    return TrafficControlConfig(
        enabled=d.get("Enabled", True),
        xqe_min_aisle_width_mm=d.get("XQE_Min_Aisle_Width_mm", XQE_MIN_AISLE_WIDTH_MM),
        xqe_bidirectional_width_mm=d.get(
            "XQE_Bidirectional_Width_mm", XQE_BIDIRECTIONAL_WIDTH_MM
        ),
    )
