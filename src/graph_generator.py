"""
Graph Generator Module
=======================
Converts a warehouse layout JSON into a NetworkX directed graph for path
calculation and visualization.

Node types:
  - 'dock'            : inbound or outbound dock position
  - 'head_aisle_pt'   : point on a head aisle (aisle junction or dock entry)
  - 'aisle_entry'     : where AGV enters a storage aisle from the head aisle
  - 'aisle_exit'      : far end of a storage aisle (through aisles only)
  - 'storage_position': individual rack or floor storage location

Edge attributes:
  - 'distance'   : metres
  - 'forward'    : True = forward direction of travel, False = reverse
  - 'turns'      : number of 90° turns required to traverse this edge
  - 'type'       : 'head_aisle', 'storage_aisle', 'dock_connection'

Coordinate system:
  - X = horizontal (west–east)
  - Y = vertical (south–north)
  - (0, 0) = south-west corner of warehouse
"""

import math
import logging
from typing import Dict, List, Optional, Tuple

import networkx as nx

from .agv_specs import AGV_SPECS, get_compatible_agvs_for_aisle

# Maximum number of storage position nodes to create per aisle.
# Capped for graph performance; the aisle depth is still used for physics
# calculations independent of this limit.
MAX_STORAGE_POSITIONS_PER_AISLE = 20

logger = logging.getLogger(__name__)


class WarehouseGraph:
    """
    NetworkX-based directed graph representation of a warehouse layout.

    Usage
    -----
    >>> wg = WarehouseGraph()
    >>> wg.build_from_layout(layout_dict)
    >>> path = wg.shortest_path("dock_IB1", "aisle_entry_SA1")
    >>> wg.get_node_positions()  # returns {node_id: (x, y)}
    """

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self._positions: Dict[str, Tuple[float, float]] = {}
        self._layout: Optional[dict] = None
        self._aisle_compatible_agvs: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Public build API
    # ------------------------------------------------------------------

    def build_from_layout(self, layout: dict) -> nx.DiGraph:
        """
        Build the warehouse graph from a layout JSON dict.

        Parameters
        ----------
        layout : dict
            Warehouse layout as produced by LayoutParser or ManualLayoutBuilder.

        Returns
        -------
        nx.DiGraph
            The populated directed graph.
        """
        self._layout = layout
        self.graph.clear()
        self._positions.clear()
        self._aisle_compatible_agvs.clear()

        self._add_dock_nodes(layout)
        self._add_head_aisle_nodes(layout)
        self._add_storage_aisle_nodes(layout)
        self._connect_docks_to_head_aisles(layout)
        self._connect_head_aisles_to_storage_aisles(layout)

        logger.info(
            "Graph built: %d nodes, %d edges",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
        )
        return self.graph

    def get_node_positions(self) -> Dict[str, Tuple[float, float]]:
        """Return dict of {node_id: (x, y)}."""
        return dict(self._positions)

    def get_compatible_agvs_for_aisle(self, aisle_name: str) -> List[str]:
        """Return list of compatible AGV type names for a given aisle."""
        return self._aisle_compatible_agvs.get(aisle_name, [])

    def shortest_path(
        self, source: str, target: str, weight: str = "distance"
    ) -> Optional[List[str]]:
        """Return shortest path node list or None if no path exists."""
        try:
            return nx.shortest_path(self.graph, source, target, weight=weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def path_distance(self, path: List[str]) -> float:
        """Return total distance in metres for a list of node IDs."""
        total = 0.0
        for i in range(len(path) - 1):
            data = self.graph.get_edge_data(path[i], path[i + 1]) or {}
            total += data.get("distance", 0.0)
        return total

    def get_dock_to_aisle_entry_path(
        self, dock_id: str, aisle_name: str
    ) -> Optional[List[str]]:
        """Return the path from a dock to the entry of a storage aisle."""
        target = f"aisle_entry_{aisle_name}"
        return self.shortest_path(dock_id, target)

    def get_all_storage_positions(self, aisle_name: str) -> List[str]:
        """Return all storage position node IDs in a given aisle."""
        prefix = f"storage_pos_{aisle_name}_"
        return [n for n in self.graph.nodes if n.startswith(prefix)]

    def count_turns_in_path(self, path: List[str]) -> int:
        """Count the number of 90° direction changes in a path."""
        if len(path) < 3:
            return 0
        turns = 0
        for i in range(1, len(path) - 1):
            a = self._positions.get(path[i - 1])
            b = self._positions.get(path[i])
            c = self._positions.get(path[i + 1])
            if a is None or b is None or c is None:
                continue
            ab = (b[0] - a[0], b[1] - a[1])
            bc = (c[0] - b[0], c[1] - b[1])
            if _vec_len(ab) < 1e-6 or _vec_len(bc) < 1e-6:
                continue
            cos_a = _dot(ab, bc) / (_vec_len(ab) * _vec_len(bc))
            cos_a = max(-1.0, min(1.0, cos_a))
            angle = math.degrees(math.acos(cos_a))
            if 60 <= angle <= 120:
                turns += 1
        return turns

    def validate_agv_path(
        self, path: List[str], agv_type: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if a given AGV type can traverse a path.
        Returns (True, []) if valid, or (False, [list of issues]).
        """
        if agv_type not in AGV_SPECS:
            return False, [f"Unknown AGV type '{agv_type}'"]

        issues = []
        spec = AGV_SPECS[agv_type]

        for node in path:
            node_data = self.graph.nodes.get(node, {})
            if node_data.get("type") == "aisle_entry":
                aisle_name = node_data.get("aisle")
                aisle_width = node_data.get("aisle_width", 999)
                storage_type = node_data.get("storage_type", "")

                if aisle_width < spec["aisle_width"]:
                    issues.append(
                        f"Aisle {aisle_name}: width {aisle_width:.2f}m < "
                        f"{agv_type} minimum {spec['aisle_width']}m"
                    )
                if storage_type not in spec["storage_types"]:
                    issues.append(
                        f"Aisle {aisle_name}: storage type '{storage_type}' "
                        f"not supported by {agv_type}"
                    )
        return (len(issues) == 0), issues

    # ------------------------------------------------------------------
    # Private graph building helpers
    # ------------------------------------------------------------------

    def _add_dock_nodes(self, layout: dict) -> None:
        for dock in layout.get("inbound_docks", []):
            node_id = f"dock_{dock['name']}"
            pos = dock["position"]
            self._add_node(
                node_id,
                x=pos["x"],
                y=pos["y"],
                node_type="dock",
                dock_type="inbound",
                dock_name=dock["name"],
                count=dock.get("count", 1),
            )

        for dock in layout.get("outbound_docks", []):
            node_id = f"dock_{dock['name']}"
            pos = dock["position"]
            self._add_node(
                node_id,
                x=pos["x"],
                y=pos["y"],
                node_type="dock",
                dock_type="outbound",
                dock_name=dock["name"],
                count=dock.get("count", 1),
            )

    def _add_head_aisle_nodes(self, layout: dict) -> None:
        for ha in layout.get("head_aisles", []):
            # Add start and end points of each head aisle
            start_id = f"ha_start_{ha['name']}"
            end_id = f"ha_end_{ha['name']}"
            sx, sy = ha["start"]["x"], ha["start"]["y"]
            ex, ey = ha["end"]["x"], ha["end"]["y"]

            self._add_node(start_id, x=sx, y=sy, node_type="head_aisle_pt",
                           head_aisle=ha["name"])
            self._add_node(end_id, x=ex, y=ey, node_type="head_aisle_pt",
                           head_aisle=ha["name"])

            dist = _distance((sx, sy), (ex, ey))
            # Head aisle is bidirectional, forward travel in both directions
            self._add_edge(start_id, end_id, distance=dist, forward=True,
                           turns=0, edge_type="head_aisle")
            self._add_edge(end_id, start_id, distance=dist, forward=True,
                           turns=0, edge_type="head_aisle")

    def _add_storage_aisle_nodes(self, layout: dict) -> None:
        for aisle in layout.get("storage_aisles", []):
            name = aisle["name"]
            sx, sy = aisle["start"]["x"], aisle["start"]["y"]
            ex, ey = aisle["end"]["x"], aisle["end"]["y"]
            depth = aisle.get("depth", _distance((sx, sy), (ex, ey)))
            width = aisle.get("width", 2.84)
            storage_type = aisle.get("storage_type", "rack")
            entry_type = aisle.get("entry_type", "dead-end")

            entry_id = f"aisle_entry_{name}"
            self._add_node(
                entry_id,
                x=sx, y=sy,
                node_type="aisle_entry",
                aisle=name,
                aisle_width=width,
                storage_type=storage_type,
                entry_type=entry_type,
                depth=depth,
            )

            # Through-aisle has an exit node at the far end
            if entry_type == "through":
                exit_id = f"aisle_exit_{name}"
                self._add_node(
                    exit_id,
                    x=ex, y=ey,
                    node_type="aisle_exit",
                    aisle=name,
                    aisle_width=width,
                    storage_type=storage_type,
                )

            # Add representative storage positions along the aisle
            # For visualization and path planning; positions are equidistant
            racks = aisle.get("racks", [])
            n_positions = _count_storage_positions(racks, storage_type, depth)
            if n_positions > 0:
                step = depth / (n_positions + 1)
                # Direction vector along aisle
                dx = (ex - sx) / depth if depth > 0 else 0
                dy = (ey - sy) / depth if depth > 0 else 1
                for j in range(1, min(n_positions + 1, MAX_STORAGE_POSITIONS_PER_AISLE + 1)):
                    pos_id = f"storage_pos_{name}_{j}"
                    px = sx + dx * step * j
                    py = sy + dy * step * j
                    rack_h = racks[0]["height"] if racks else 0.0
                    rack_levels = racks[0]["levels"] if racks else 1
                    self._add_node(
                        pos_id,
                        x=px, y=py,
                        node_type="storage_position",
                        aisle=name,
                        storage_type=storage_type,
                        rack_height=rack_h,
                        rack_levels=rack_levels,
                    )
                    dist_to_entry = step * j
                    # AGV always reverses into storage aisle (fork first)
                    self._add_edge(
                        entry_id, pos_id,
                        distance=dist_to_entry,
                        forward=False,   # reverse – fork first into aisle
                        turns=0,
                        edge_type="storage_aisle",
                    )
                    self._add_edge(
                        pos_id, entry_id,
                        distance=dist_to_entry,
                        forward=False,   # reverse – out of aisle with load
                        turns=0,
                        edge_type="storage_aisle",
                    )

            # Record compatible AGVs for this aisle
            rack_h = racks[0]["height"] if racks else 0.0
            compatible = get_compatible_agvs_for_aisle(
                width, storage_type, required_lift_height=rack_h if storage_type == "rack" else None
            )
            self._aisle_compatible_agvs[name] = compatible

    def _connect_docks_to_head_aisles(self, layout: dict) -> None:
        """
        Connect dock nodes to the nearest head aisle start/end point.
        Assume docks are at the ends of head aisles (inline – no turn needed).
        """
        for ha in layout.get("head_aisles", []):
            start_id = f"ha_start_{ha['name']}"
            end_id = f"ha_end_{ha['name']}"
            ha_sx, ha_sy = ha["start"]["x"], ha["start"]["y"]
            ha_ex, ha_ey = ha["end"]["x"], ha["end"]["y"]

            for dock in layout.get("inbound_docks", []) + layout.get("outbound_docks", []):
                dock_id = f"dock_{dock['name']}"
                dp = dock["position"]
                dx, dy = dp["x"], dp["y"]

                # Find the closest head aisle endpoint
                d_start = _distance((dx, dy), (ha_sx, ha_sy))
                d_end = _distance((dx, dy), (ha_ex, ha_ey))

                if d_start <= d_end:
                    closest_ha_node = start_id
                    dist = d_start
                else:
                    closest_ha_node = end_id
                    dist = d_end

                if dist < 1e-3:
                    # Dock is right at head aisle endpoint – no travel needed
                    dist = 0.1  # minimal non-zero distance

                # Dock connections are bidirectional, forward travel
                self._add_edge(dock_id, closest_ha_node, distance=dist,
                               forward=True, turns=0, edge_type="dock_connection")
                self._add_edge(closest_ha_node, dock_id, distance=dist,
                               forward=True, turns=0, edge_type="dock_connection")

    def _connect_head_aisles_to_storage_aisles(self, layout: dict) -> None:
        """
        Connect storage aisle entry/exit nodes to their parent head aisle.
        Each connection involves 1 turn (90° at the aisle junction).
        """
        ha_by_name = {ha["name"]: ha for ha in layout.get("head_aisles", [])}

        for aisle in layout.get("storage_aisles", []):
            name = aisle["name"]
            sx, sy = aisle["start"]["x"], aisle["start"]["y"]
            ha_name = aisle.get("head_aisle")
            entry_id = f"aisle_entry_{name}"

            if ha_name and ha_name in ha_by_name:
                ha = ha_by_name[ha_name]
                ha_sx, ha_sy = ha["start"]["x"], ha["start"]["y"]
                ha_ex, ha_ey = ha["end"]["x"], ha["end"]["y"]

                # Find the nearest point on the head aisle to this aisle entry
                ha_pt = _project_onto_segment(
                    (sx, sy), (ha_sx, ha_sy), (ha_ex, ha_ey)
                )
                ha_junction_id = f"ha_junction_{name}"
                self._add_node(
                    ha_junction_id,
                    x=ha_pt[0], y=ha_pt[1],
                    node_type="head_aisle_pt",
                    head_aisle=ha_name,
                    junction_for=name,
                )

                # Distance from junction to aisle entry (short perpendicular segment)
                d_perp = _distance(ha_pt, (sx, sy))
                if d_perp < 0.1:
                    d_perp = 0.1  # minimal

                # Head aisle → junction → aisle entry (1 turn at junction)
                # Junction is reachable from both HA endpoints
                d_from_start = _distance(ha_pt, (ha_sx, ha_sy))
                d_from_end = _distance(ha_pt, (ha_ex, ha_ey))
                ha_start_id = f"ha_start_{ha_name}"
                ha_end_id = f"ha_end_{ha_name}"

                # HA start ↔ junction (forward, no turns within head aisle)
                self._add_edge(ha_start_id, ha_junction_id, distance=d_from_start,
                               forward=True, turns=0, edge_type="head_aisle")
                self._add_edge(ha_junction_id, ha_start_id, distance=d_from_start,
                               forward=True, turns=0, edge_type="head_aisle")

                # HA end ↔ junction
                self._add_edge(ha_end_id, ha_junction_id, distance=d_from_end,
                               forward=True, turns=0, edge_type="head_aisle")
                self._add_edge(ha_junction_id, ha_end_id, distance=d_from_end,
                               forward=True, turns=0, edge_type="head_aisle")

                # Junction ↔ aisle entry (1 turn – perpendicular to head aisle)
                self._add_edge(ha_junction_id, entry_id, distance=d_perp,
                               forward=True, turns=1, edge_type="junction")
                self._add_edge(entry_id, ha_junction_id, distance=d_perp,
                               forward=True, turns=1, edge_type="junction")

                # Through-aisle exit similarly connects to HA2
                if aisle.get("entry_type") == "through":
                    exit_id = f"aisle_exit_{name}"
                    ex, ey = aisle["end"]["x"], aisle["end"]["y"]
                    # Find second head aisle if available
                    for other_ha in layout.get("head_aisles", []):
                        if other_ha["name"] == ha_name:
                            continue
                        osx, osy = other_ha["start"]["x"], other_ha["start"]["y"]
                        oex, oey = other_ha["end"]["x"], other_ha["end"]["y"]
                        oha_pt = _project_onto_segment((ex, ey), (osx, osy), (oex, oey))
                        d_exit = _distance(oha_pt, (ex, ey))
                        if d_exit < 1.0:
                            d_exit = 1.0
                        oha_junc_id = f"ha_junction_exit_{name}"
                        self._add_node(
                            oha_junc_id,
                            x=oha_pt[0], y=oha_pt[1],
                            node_type="head_aisle_pt",
                            head_aisle=other_ha["name"],
                        )
                        d_ostart = _distance(oha_pt, (osx, osy))
                        d_oend = _distance(oha_pt, (oex, oey))
                        oha_start_id = f"ha_start_{other_ha['name']}"
                        oha_end_id = f"ha_end_{other_ha['name']}"

                        self._add_edge(oha_start_id, oha_junc_id, distance=d_ostart,
                                       forward=True, turns=0, edge_type="head_aisle")
                        self._add_edge(oha_junc_id, oha_start_id, distance=d_ostart,
                                       forward=True, turns=0, edge_type="head_aisle")
                        self._add_edge(oha_end_id, oha_junc_id, distance=d_oend,
                                       forward=True, turns=0, edge_type="head_aisle")
                        self._add_edge(oha_junc_id, oha_end_id, distance=d_oend,
                                       forward=True, turns=0, edge_type="head_aisle")

                        self._add_edge(oha_junc_id, exit_id, distance=d_exit,
                                       forward=True, turns=1, edge_type="junction")
                        self._add_edge(exit_id, oha_junc_id, distance=d_exit,
                                       forward=True, turns=1, edge_type="junction")
                        break

    # ------------------------------------------------------------------
    # Node / edge helpers
    # ------------------------------------------------------------------

    def _add_node(self, node_id: str, x: float, y: float, **attrs) -> None:
        self.graph.add_node(node_id, **attrs)
        self._positions[node_id] = (x, y)

    def _add_edge(
        self,
        u: str,
        v: str,
        distance: float,
        forward: bool,
        turns: int,
        edge_type: str,
    ) -> None:
        self.graph.add_edge(
            u, v,
            distance=distance,
            forward=forward,
            turns=turns,
            type=edge_type,
            weight=distance,  # for nx.shortest_path
        )

    # ------------------------------------------------------------------
    # Geometry summary helpers
    # ------------------------------------------------------------------

    def get_aisle_geometry(self, aisle_name: str) -> Optional[dict]:
        """Return entry node attributes for a storage aisle."""
        entry_id = f"aisle_entry_{aisle_name}"
        if entry_id in self.graph.nodes:
            return dict(self.graph.nodes[entry_id])
        return None

    def get_dock_to_aisle_distances(
        self, dock_id: str, aisle_name: str
    ) -> Tuple[float, float, int]:
        """
        Compute the key distances for physics calculations.

        Returns
        -------
        (d_head_aisle, d_aisle_depth, num_turns) where:
          - d_head_aisle : distance along head aisle from dock to aisle junction (m)
          - d_aisle_depth: average distance from aisle entry to mid-aisle (m)
          - num_turns    : number of 90° turns in the path
        """
        entry_id = f"aisle_entry_{aisle_name}"
        path = self.shortest_path(dock_id, entry_id)
        if path is None:
            return 0.0, 0.0, 0

        d_head = 0.0
        d_aisle_depth = 0.0
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i + 1]) or {}
            et = edge_data.get("type", "")
            dist = edge_data.get("distance", 0.0)
            if et in ("head_aisle", "dock_connection"):
                d_head += dist
            elif et in ("storage_aisle", "junction"):
                d_aisle_depth += dist

        turns = self.count_turns_in_path(path)

        # If we didn't count junction turns from edges, count from geometry
        if turns == 0:
            turns = sum(
                self.graph.get_edge_data(path[i], path[i + 1], {}).get("turns", 0)
                for i in range(len(path) - 1)
            )

        return d_head, d_aisle_depth, turns

    def summary(self) -> str:
        """Return a text summary of the graph."""
        node_types: dict = {}
        for _, data in self.graph.nodes(data=True):
            nt = data.get("node_type", "unknown")
            node_types[nt] = node_types.get(nt, 0) + 1

        lines = [
            f"Graph nodes : {self.graph.number_of_nodes()}",
            f"Graph edges : {self.graph.number_of_edges()}",
            "Node types  :",
        ]
        for nt, count in sorted(node_types.items()):
            lines.append(f"  {nt:<22}: {count}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Geometry utilities
# ---------------------------------------------------------------------------

def _distance(a: tuple, b: tuple) -> float:
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)


def _dot(a: tuple, b: tuple) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _vec_len(v: tuple) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2)


def _project_onto_segment(
    p: tuple, a: tuple, b: tuple
) -> tuple:
    """Project point p onto line segment AB; return the closest point."""
    ab = (b[0] - a[0], b[1] - a[1])
    ap = (p[0] - a[0], p[1] - a[1])
    len_sq = _dot(ab, ab)
    if len_sq < 1e-10:
        return a
    t = max(0.0, min(1.0, _dot(ap, ab) / len_sq))
    return (a[0] + t * ab[0], a[1] + t * ab[1])


def _count_storage_positions(
    racks: list, storage_type: str, depth: float
) -> int:
    """Estimate the number of representative storage positions in an aisle."""
    if storage_type == "rack" and racks:
        return max(r.get("positions", 0) for r in racks)
    if storage_type in ("ground_storage", "ground_stacking"):
        # Estimate based on depth (1 position per 2m)
        return max(1, int(depth / 2))
    return 0
