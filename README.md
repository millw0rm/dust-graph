# Dust Graph

Dust Graph starts with a small Python foundation for modeling infrastructure, access, and runtime relationship graphs before committing to a production graph backend.

## Initial stack

- **Runtime:** Python 3.11 or newer.
- **CLI:** Typer, exposed as `dust-graph`.
- **Models:** Pydantic v2 for explicit validation boundaries.
- **Storage:** A backend-neutral adapter protocol with an in-memory adapter first. Kuzu is intentionally deferred as the next adapter once the in-memory contract is stable.
- **Fixtures:** YAML or JSON graph fixtures for reviewable local examples.

## Quick start

```bash
python -m pip install -e '.[dev]'
dust-graph validate-fixture fixtures/sample_graph.yaml
dust-graph import-fixture fixtures/sample_graph.yaml
pytest
```
