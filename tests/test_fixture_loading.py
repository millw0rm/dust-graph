from pathlib import Path

from typer.testing import CliRunner

from dust_graph.adapters import InMemoryGraphAdapter
from dust_graph.cli import app
from dust_graph.fixtures import import_fixture, load_fixture

SAMPLE_FIXTURE = Path("fixtures/sample_graph.yaml")


def test_load_sample_fixture() -> None:
    fixture = load_fixture(SAMPLE_FIXTURE)

    assert fixture.name == "sample-service-graph"
    assert len(fixture.nodes) == 4
    assert len(fixture.edges) == 3


def test_import_sample_fixture_into_memory_adapter() -> None:
    adapter = InMemoryGraphAdapter()
    fixture = import_fixture(SAMPLE_FIXTURE, adapter)

    assert len(adapter.nodes) == len(fixture.nodes)
    assert len(adapter.edges) == len(fixture.edges)
    assert adapter.query("nodes", {"type": "Service"})[0]["node"].id == "service:dust-api"


def test_validate_fixture_cli_command() -> None:
    result = CliRunner().invoke(app, ["validate-fixture", str(SAMPLE_FIXTURE)])

    assert result.exit_code == 0
    assert "valid fixture" in result.output


def test_import_fixture_cli_command() -> None:
    result = CliRunner().invoke(app, ["import-fixture", str(SAMPLE_FIXTURE)])

    assert result.exit_code == 0
    assert "imported fixture" in result.output
