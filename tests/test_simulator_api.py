import copy
import os

from src.simulator import load_config
from simulator_api import _run_simulation


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "config_medium.json"
)


def test_run_simulation_includes_required_xpl_fleet_and_seed():
    config = load_config(CONFIG_PATH)
    result, _report, _traffic = _run_simulation(
        copy.deepcopy(config), traffic_control=False, random_seed=42
    )

    assert result["random_seed"] == 42
    assert result["fleet_sizes"]["required_xpl_fleet"] == result["fleet_sizes"]["xpl201"]
    assert result["fleet_sizes"]["required_xpl_fleet"] > 0


def test_seeded_simulation_is_reproducible_for_same_seed():
    config = load_config(CONFIG_PATH)
    result_1, _report_1, _traffic_1 = _run_simulation(
        copy.deepcopy(config), traffic_control=False, random_seed=1234
    )
    result_2, _report_2, _traffic_2 = _run_simulation(
        copy.deepcopy(config), traffic_control=False, random_seed=1234
    )

    assert result_1 == result_2


def test_seed_value_changes_result_payload():
    config = load_config(CONFIG_PATH)
    result_1, _report_1, _traffic_1 = _run_simulation(
        copy.deepcopy(config), traffic_control=False, random_seed=111
    )
    result_2, _report_2, _traffic_2 = _run_simulation(
        copy.deepcopy(config), traffic_control=False, random_seed=222
    )

    assert result_1 != result_2
