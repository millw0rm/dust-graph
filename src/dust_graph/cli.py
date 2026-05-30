"""Command-line interface for Dust Graph."""

from __future__ import annotations

from pathlib import Path

import typer

from dust_graph.adapters import InMemoryGraphAdapter
from dust_graph.fixtures import import_fixture, load_fixture
from dust_graph.schema import GraphSchemaError, validate_graph_fixture_schema

app = typer.Typer(help="Dust Graph CLI.")


@app.command()
def validate_fixture(path: Path) -> None:
    """Validate a YAML or JSON graph fixture."""

    fixture = load_fixture(path)
    typer.echo(
        f"valid fixture '{fixture.name}' with {len(fixture.nodes)} nodes and {len(fixture.edges)} edges"
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

