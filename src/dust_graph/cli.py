"""Command-line interface for Dust Graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from dust_graph.adapters import InMemoryGraphAdapter
from dust_graph.fixtures import import_fixture, load_fixture
from dust_graph.queries import execute_saved_query
from dust_graph.schema import GraphSchemaError, validate_graph_fixture_schema

app = typer.Typer(help="Dust Graph CLI.")


@app.command()
def validate_fixture(path: Path) -> None:
    """Validate a YAML or JSON graph fixture."""

    fixture = load_fixture(path)
    typer.echo(
        f"valid fixture '{fixture.name}' with "
        f"{len(fixture.nodes)} nodes and {len(fixture.edges)} edges"
    )


@app.command(name="validate-schema")
def validate_schema(path: Path) -> None:
    """Validate a graph fixture against the canonical schema."""

    fixture = load_fixture(path)
    try:
        validate_graph_fixture_schema(fixture)
    except GraphSchemaError as exc:
        for error in exc.errors:
            typer.echo(error, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"valid schema for fixture '{fixture.name}' with "
        f"{len(fixture.nodes)} nodes and {len(fixture.edges)} edges"
    )


@app.command(name="import-fixture")
def import_fixture_command(
    path: Path = typer.Argument(..., help="Path to a YAML or JSON graph fixture."),
) -> None:
    """Import a fixture into the in-memory adapter."""

    adapter = InMemoryGraphAdapter()
    fixture = import_fixture(path, adapter)
    typer.echo(
        f"imported fixture '{fixture.name}' into memory: "
        f"{len(adapter.nodes)} nodes, {len(adapter.edges)} edges"
    )


@app.command(name="query")
def query_command(
    path: Path = typer.Argument(..., help="Path to a YAML or JSON graph fixture."),
    query_name: str = typer.Argument(..., help="Saved query name to execute."),
    params: Annotated[
        list[str] | None,
        typer.Option(
            "--param",
            help="Saved query parameter as key=value. May be provided multiple times.",
        ),
    ] = None,
) -> None:
    """Run a saved query against a graph fixture with the in-memory adapter."""

    adapter = InMemoryGraphAdapter()
    import_fixture(path, adapter)
    try:
        results = execute_saved_query(adapter, query_name, _parse_params(params or []))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(results, sort_keys=True, indent=2))


def _parse_params(params: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for param in params:
        if "=" not in param:
            raise ValueError(f"invalid --param value {param!r}; expected key=value")
        key, value = param.split("=", 1)
        if not key:
            raise ValueError("invalid --param value; key must not be empty")
        parsed[key] = _parse_param_value(value)
    return parsed


def _parse_param_value(value: str) -> object:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
