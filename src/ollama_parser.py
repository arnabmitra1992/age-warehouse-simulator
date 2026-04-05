"""
Ollama Parser Adapter
======================
Provides the OllamaParser class and related functions for AI-powered
warehouse layout parsing. This module re-exports the relevant parts
of layout_parser for the PR-2/PR-3/PR-4 combined pipeline.
"""
from .layout_parser import (
    LayoutParser as OllamaParser,
    ManualLayoutBuilder,
    OllamaUnavailableError,
    _validate_layout_schema,
    _validate_agv_constraints,
    _extract_json_from_text,
)

__all__ = [
    "OllamaParser",
    "ManualLayoutBuilder",
    "OllamaUnavailableError",
    "_validate_layout_schema",
    "_validate_agv_constraints",
    "_extract_json_from_text",
]
