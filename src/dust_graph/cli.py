"""Command-line interface for Dust Graph."""

from __future__ import annotations

from pathlib import Path

import typer

from dust_graph.adapters import InMemoryGraphAdapter
from dust_graph.fixtures import import_fixture, load_fixture

app = typer.Typer(help="Dust Graph CLI.")


@app.command()
def validate_fixture(path: Path) -> None:
    """Validate a YAML or JSON graph fixture."""

    fixture = load_fixture(path)
    typer.echo(
        f"valid fixture '{fixture.name}' with {len(fixture.nodes)} nodes and {len(fixture.edges)} edges"
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

