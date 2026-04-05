"""
AI Layout Parser Module (Ollama Integration)
=============================================
Extracts structured warehouse configuration JSON from text descriptions or
image paths using a locally-running Ollama LLM with Few-Shot prompting.

Few-Shot strategy:
  - Three reference layouts are embedded in the system prompt.
  - The model learns the exact JSON schema from examples and applies it to new input.
  - Output is validated against AGV constraints before being returned.

Fallback:
  - If Ollama is unavailable, the parser raises OllamaUnavailableError with
    instructions on how to install/start Ollama.
  - A manual configuration builder is provided as an alternative.
"""

import json
import logging
import re
from typing import Optional, Union

from .reference_layouts import get_few_shot_prompt_block

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are a warehouse layout analyzer expert.
Your job is to read warehouse layout descriptions or analyse provided images and
extract the structural configuration as a precise JSON object.

OUTPUT FORMAT RULES:
1. Output ONLY valid JSON. No prose, no markdown fences.
2. Follow EXACTLY the schema shown in the examples below.
3. All distances must be in metres (float).
4. If a value is unknown, use null.
5. storage_type must be one of: "rack", "ground_storage", "ground_stacking"
6. entry_type must be one of: "dead-end", "through"

EXAMPLES (learn the pattern from these):

{few_shot_examples}

Now extract the JSON layout from the new warehouse description provided by the user.
Remember: output ONLY valid JSON, nothing else.
"""

# ---------------------------------------------------------------------------
# JSON schema validator
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL_KEYS = {
    "warehouse",
    "inbound_docks",
    "outbound_docks",
    "head_aisles",
    "storage_aisles",
    "ground_storage_zones",
    "ground_stacking_zones",
}


def _validate_layout_schema(layout: dict) -> list:
    """
    Validate basic schema of extracted layout JSON.
    Returns a list of warning/error strings (empty = all good).
    """
    errors = []
    missing = REQUIRED_TOP_LEVEL_KEYS - set(layout.keys())
    if missing:
        errors.append(f"Missing top-level keys: {missing}")

    for aisle in layout.get("storage_aisles", []):
        if "width" not in aisle:
            errors.append(f"Storage aisle {aisle.get('name', '?')} missing 'width'")
        if "storage_type" not in aisle:
            errors.append(f"Storage aisle {aisle.get('name', '?')} missing 'storage_type'")
        if aisle.get("storage_type") not in ("rack", "ground_storage", "ground_stacking", None):
            errors.append(
                f"Unknown storage_type '{aisle.get('storage_type')}' "
                f"in aisle {aisle.get('name', '?')}"
            )
    return errors


def _validate_agv_constraints(layout: dict) -> list:
    """
    Check extracted layout against AGV minimum aisle width requirements.
    Returns list of constraint warning strings.
    """
    from .agv_specs import AGV_SPECS

    warnings = []
    for aisle in layout.get("storage_aisles", []):
        aisle_width = aisle.get("width", 0)
        storage_type = aisle.get("storage_type", "")
        aisle_name = aisle.get("name", "?")
        compatible = []
        for agv_name, spec in AGV_SPECS.items():
            if storage_type not in spec["storage_types"]:
                continue
            if aisle_width >= spec["aisle_width"]:
                compatible.append(agv_name)
        if not compatible:
            warnings.append(
                f"Aisle {aisle_name} (width={aisle_width}m, type={storage_type}): "
                f"NO compatible AGV found! Minimum widths are "
                f"XNA=1.77m, XPL=2.6m, XQE=2.84m."
            )
        else:
            logger.debug("Aisle %s: compatible AGVs = %s", aisle_name, compatible)
    return warnings


def _extract_json_from_text(text: str) -> Optional[dict]:
    """
    Attempt to extract a JSON object from raw LLM output text.
    Handles cases where the model wraps the JSON in markdown code fences.
    """
    # Remove markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # Try parsing the whole string first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object within the text
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

class OllamaUnavailableError(RuntimeError):
    """Raised when Ollama is not running or not installed."""


class LayoutParser:
    """
    AI-powered warehouse layout parser using Ollama with Few-Shot prompting.

    Parameters
    ----------
    model : str
        Ollama model name to use. Defaults to 'llama3.2' (compact, fast).
        Other good options: 'neural-chat', 'mistral', 'llama2', 'phi3'.
    ollama_url : str
        Base URL of the Ollama API. Defaults to http://localhost:11434.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        ollama_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self._system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            few_shot_examples=get_few_shot_prompt_block()
        )

    def _check_ollama(self) -> None:
        """Verify Ollama is running. Raises OllamaUnavailableError if not."""
        try:
            import urllib.request

            req = urllib.request.urlopen(f"{self.ollama_url}/api/tags", timeout=3)
            req.read()
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Ollama is not running at {self.ollama_url}.\n\n"
                "To install and start Ollama:\n"
                "  1. Download from https://ollama.ai\n"
                "  2. Run: ollama serve\n"
                f"  3. Pull a model: ollama pull {self.model}\n"
                "  4. Re-run the simulator.\n\n"
                "Alternatively, use --manual mode to configure the warehouse manually."
            ) from exc

    def _call_ollama(self, user_message: str) -> str:
        """
        Send a chat completion request to Ollama and return the response text.
        """
        import json as _json
        import urllib.request

        payload = _json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = _json.loads(resp.read().decode())
            return body["message"]["content"]

    def parse_text(self, description: str) -> dict:
        """
        Parse a text description of a warehouse layout.

        Parameters
        ----------
        description : str
            Natural-language or structured text description of the warehouse.

        Returns
        -------
        dict
            Validated warehouse layout JSON.

        Raises
        ------
        OllamaUnavailableError
            If Ollama is not running.
        ValueError
            If the extracted JSON is invalid or cannot be parsed.
        """
        self._check_ollama()
        logger.info("Sending layout description to Ollama (%s)…", self.model)
        raw_response = self._call_ollama(description)
        logger.debug("Raw Ollama response:\n%s", raw_response)

        layout = _extract_json_from_text(raw_response)
        if layout is None:
            raise ValueError(
                "Ollama did not return valid JSON. Raw response:\n" + raw_response
            )

        return self._post_process(layout)

    def parse_image(self, image_path: str) -> dict:
        """
        Parse a warehouse layout image (requires a vision-capable Ollama model).

        Parameters
        ----------
        image_path : str
            Path to the warehouse image file (PNG, JPG, etc.).

        Returns
        -------
        dict
            Validated warehouse layout JSON.
        """
        import base64
        import json as _json
        import urllib.request

        self._check_ollama()

        with open(image_path, "rb") as fh:
            img_b64 = base64.b64encode(fh.read()).decode()

        payload = _json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Analyse this warehouse layout image and extract "
                            "the structured JSON configuration."
                        ),
                        "images": [img_b64],
                    },
                ],
                "stream": False,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = _json.loads(resp.read().decode())
            raw_response = body["message"]["content"]

        layout = _extract_json_from_text(raw_response)
        if layout is None:
            raise ValueError(
                "Ollama did not return valid JSON for the image. "
                "Try a vision-capable model such as 'llava' or 'bakllava'.\n"
                "Raw response:\n" + raw_response
            )

        return self._post_process(layout)

    def _post_process(self, layout: dict) -> dict:
        """Validate schema and AGV constraints; attach warnings."""
        schema_errors = _validate_layout_schema(layout)
        agv_warnings = _validate_agv_constraints(layout)

        if schema_errors:
            logger.warning("Schema validation issues: %s", schema_errors)
        if agv_warnings:
            logger.warning("AGV constraint warnings: %s", agv_warnings)

        layout["_validation"] = {
            "schema_errors": schema_errors,
            "agv_warnings": agv_warnings,
        }
        return layout


# ---------------------------------------------------------------------------
# Manual configuration builder (fallback when Ollama unavailable)
# ---------------------------------------------------------------------------

class ManualLayoutBuilder:
    """
    Interactive CLI-based warehouse configuration builder.
    Use when Ollama is not available or for precise manual entry.
    """

    def __init__(self) -> None:
        self._layout: dict = {
            "warehouse": {},
            "inbound_docks": [],
            "outbound_docks": [],
            "head_aisles": [],
            "storage_aisles": [],
            "ground_storage_zones": [],
            "ground_stacking_zones": [],
            "_validation": {"schema_errors": [], "agv_warnings": []},
        }

    def interactive_build(self) -> dict:
        """Walk the user through building a layout interactively."""
        print("\n" + "=" * 60)
        print("  MANUAL WAREHOUSE CONFIGURATION BUILDER")
        print("=" * 60)

        # Warehouse dimensions
        name = input("Warehouse name [My Warehouse]: ").strip() or "My Warehouse"
        width = float(input("Warehouse width (m): "))
        length = float(input("Warehouse length (m): "))
        self._layout["warehouse"] = {"name": name, "width": width, "length": length}

        # Docks
        n_ib = int(input("Number of inbound dock positions: "))
        ib_x = float(input("Inbound dock X position (m): "))
        ib_y = float(input("Inbound dock Y position (m): "))
        self._layout["inbound_docks"].append(
            {"name": "IB1", "position": {"x": ib_x, "y": ib_y}, "count": n_ib}
        )

        n_ob = int(input("Number of outbound dock positions: "))
        ob_x = float(input("Outbound dock X position (m): "))
        ob_y = float(input("Outbound dock Y position (m): "))
        self._layout["outbound_docks"].append(
            {"name": "OB1", "position": {"x": ob_x, "y": ob_y}, "count": n_ob}
        )

        # Head aisles
        n_ha = int(input("Number of head aisles: "))
        for i in range(n_ha):
            print(f"\n  Head Aisle {i + 1}:")
            ha_name = input("  Name [HA1]: ").strip() or f"HA{i + 1}"
            ha_sx = float(input("  Start X (m): "))
            ha_sy = float(input("  Start Y (m): "))
            ha_ex = float(input("  End X (m): "))
            ha_ey = float(input("  End Y (m): "))
            ha_w = float(input("  Width (m): "))
            self._layout["head_aisles"].append(
                {
                    "name": ha_name,
                    "start": {"x": ha_sx, "y": ha_sy},
                    "end": {"x": ha_ex, "y": ha_ey},
                    "width": ha_w,
                    "connections": [],
                }
            )

        # Storage aisles
        n_sa = int(input("\nNumber of storage aisles: "))
        for i in range(n_sa):
            print(f"\n  Storage Aisle {i + 1}:")
            sa_name = input("  Name [SA1]: ").strip() or f"SA{i + 1}"
            sa_sx = float(input("  Entry X (m): "))
            sa_sy = float(input("  Entry Y (m): "))
            sa_depth = float(input("  Depth (m): "))
            sa_dir = input("  Direction N/S/E/W [N]: ").strip().upper() or "N"
            sa_w = float(input("  Width (m): "))
            sa_type = (
                input("  Storage type (rack/ground_storage/ground_stacking) [rack]: ")
                .strip()
                .lower()
                or "rack"
            )
            sa_entry = (
                input("  Entry type (dead-end/through) [dead-end]: ").strip().lower()
                or "dead-end"
            )

            # Compute end point
            dir_map = {
                "N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)
            }
            dx, dy = dir_map.get(sa_dir, (0, 1))
            sa_ex = sa_sx + dx * sa_depth
            sa_ey = sa_sy + dy * sa_depth

            aisle: dict = {
                "name": sa_name,
                "start": {"x": sa_sx, "y": sa_sy},
                "end": {"x": sa_ex, "y": sa_ey},
                "width": sa_w,
                "depth": sa_depth,
                "entry_type": sa_entry,
                "storage_type": sa_type,
                "head_aisle": (
                    self._layout["head_aisles"][0]["name"]
                    if self._layout["head_aisles"]
                    else "HA1"
                ),
                "racks": [],
            }

            if sa_type == "rack":
                rack_h = float(input("  Rack height (m) [4.5]: ") or 4.5)
                rack_l = int(input("  Rack levels [3]: ") or 3)
                rack_pos = int(input("  Positions per side [10]: ") or 10)
                aisle["racks"] = [
                    {"side": "left", "positions": rack_pos, "height": rack_h, "levels": rack_l},
                    {"side": "right", "positions": rack_pos, "height": rack_h, "levels": rack_l},
                ]

            self._layout["storage_aisles"].append(aisle)

        return self._layout

    def load_from_file(self, path: str) -> dict:
        """Load a warehouse layout from a JSON file."""
        with open(path, "r") as fh:
            layout = json.load(fh)
        errors = _validate_layout_schema(layout)
        warnings = _validate_agv_constraints(layout)
        layout["_validation"] = {
            "schema_errors": errors,
            "agv_warnings": warnings,
        }
        return layout

    def save_to_file(self, layout: dict, path: str) -> None:
        """Save a warehouse layout to a JSON file."""
        export = {k: v for k, v in layout.items() if not k.startswith("_")}
        with open(path, "w") as fh:
            json.dump(export, fh, indent=2)
        logger.info("Layout saved to %s", path)
