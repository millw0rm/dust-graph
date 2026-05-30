"""Fixture loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from dust_graph.adapter import GraphAdapter
from dust_graph.models import GraphFixture
from dust_graph.schema import validate_graph_fixture_schema


def load_fixture(path: Path, *, validate_schema: bool = False) -> GraphFixture:
    """Load and validate a graph fixture from YAML or JSON."""

    raw = _load_mapping(path)
    fixture = GraphFixture.model_validate(raw)
    if validate_schema:
        validate_graph_fixture_schema(fixture)
    return fixture


def import_fixture(
    path: Path, adapter: GraphAdapter, *, validate_schema: bool = False
) -> GraphFixture:
    """Load a fixture and import it through a graph adapter."""

    fixture = load_fixture(path, validate_schema=validate_schema)
    adapter.bulk_import(fixture)
    return fixture


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
    elif path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text())
    else:
        raise ValueError("fixture must be a .json, .yaml, or .yml file")
    if not isinstance(data, dict):
        raise ValueError("fixture root must be a mapping")
    return data
