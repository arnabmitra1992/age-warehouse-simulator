"""
Fleet sizing calculations for XPL_201 and XQE_122 vehicle types.
"""
import math
from dataclasses import dataclass


@dataclass
class ThroughputConfig:
    total_daily_pallets: int = 1000
    operating_hours: float = 16
    xpl201_percentage: float = 30        # % of pallets handled by XPL_201
    xqe_rack_percentage: float = 50      # % of pallets handled by XQE rack
    xqe_stacking_percentage: float = 20  # % of pallets handled by XQE stacking
    utilization_target: float = 0.75
    buffer_capacity_pallets: int = 50
    # Separate inbound/outbound daily pallets (new outbound workflow)
    total_daily_inbound_pallets: int = 0   # 0 = use total_daily_pallets
    total_daily_outbound_pallets: int = 0  # 0 = use total_daily_pallets

    @property
    def effective_inbound_pallets(self) -> int:
        """Inbound pallets to process per day."""
        return self.total_daily_inbound_pallets or self.total_daily_pallets

    @property
    def effective_outbound_pallets(self) -> int:
        """Outbound pallets to process per day."""
        return self.total_daily_outbound_pallets or self.total_daily_pallets

    @property
    def xpl201_daily_pallets(self) -> float:
        return self.total_daily_pallets * self.xpl201_percentage / 100.0

    @property
    def xqe_rack_daily_pallets(self) -> float:
        return self.total_daily_pallets * self.xqe_rack_percentage / 100.0

    @property
    def xqe_stacking_daily_pallets(self) -> float:
        return self.total_daily_pallets * self.xqe_stacking_percentage / 100.0

    def validate(self) -> None:
        total = self.xpl201_percentage + self.xqe_rack_percentage + self.xqe_stacking_percentage
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Workflow percentages must sum to 100, got {total:.1f}"
            )


@dataclass
class FleetSizeResult:
    vehicle_type: str
    workflow: str
    daily_pallets: float
    avg_cycle_time_s: float
    operating_hours: float
    utilization_target: float
    fleet_size: int
    throughput_per_hour: float
    utilization_percent: float

    def summary(self) -> str:
        return (
            f"{self.vehicle_type} ({self.workflow}): "
            f"{self.fleet_size} vehicles | "
            f"Cycle {self.avg_cycle_time_s:.0f}s | "
            f"Throughput {self.throughput_per_hour:.1f} pallets/h | "
            f"Utilisation {self.utilization_percent:.1f}%"
        )


def calculate_fleet_size(
    daily_pallets: float,
    avg_cycle_time_s: float,
    operating_hours: float,
    utilization_target: float,
    vehicle_type: str = "",
    workflow: str = "",
) -> FleetSizeResult:
    """
    Minimum fleet size for a given workflow.

    fleet_size = ceil(
        (daily_pallets × avg_cycle_time_s)
        / (operating_hours × 3600 × utilization_target)
    )
    """
    if avg_cycle_time_s <= 0 or daily_pallets <= 0:
        return FleetSizeResult(
            vehicle_type=vehicle_type,
            workflow=workflow,
            daily_pallets=daily_pallets,
            avg_cycle_time_s=avg_cycle_time_s,
            operating_hours=operating_hours,
            utilization_target=utilization_target,
            fleet_size=0,
            throughput_per_hour=0.0,
            utilization_percent=0.0,
        )

    available_seconds = operating_hours * 3600.0 * utilization_target
    fleet_size = math.ceil((daily_pallets * avg_cycle_time_s) / available_seconds)

    # Utilisation with this fleet
    actual_pallets_per_hour = 3600.0 / avg_cycle_time_s * fleet_size
    required_pallets_per_hour = daily_pallets / operating_hours
    utilization_percent = (required_pallets_per_hour / actual_pallets_per_hour) * 100.0

    return FleetSizeResult(
        vehicle_type=vehicle_type,
        workflow=workflow,
        daily_pallets=daily_pallets,
        avg_cycle_time_s=avg_cycle_time_s,
        operating_hours=operating_hours,
        utilization_target=utilization_target,
        fleet_size=fleet_size,
        throughput_per_hour=actual_pallets_per_hour,
        utilization_percent=utilization_percent,
    )


def throughput_config_from_dict(d: dict) -> ThroughputConfig:
    return ThroughputConfig(
        total_daily_pallets=d.get("Total_Daily_Pallets", 1000),
        operating_hours=d.get("Operating_Hours", 16),
        xpl201_percentage=d.get("XPL_201_Percentage", 30),
        xqe_rack_percentage=d.get("XQE_Rack_Percentage", 50),
        xqe_stacking_percentage=d.get("XQE_Stacking_Percentage", 20),
        utilization_target=d.get("Utilization_Target", 0.75),
        buffer_capacity_pallets=d.get("Buffer_Capacity_Pallets", 50),
        total_daily_inbound_pallets=d.get("Total_Daily_Inbound_Pallets", 0),
        total_daily_outbound_pallets=d.get("Total_Daily_Outbound_Pallets", 0),
    )
