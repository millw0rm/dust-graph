"""Resolvers that infer relationships across collected graph fixtures."""

from dust_graph.resolvers.cross_repository import resolve_cross_repository_context

__all__ = ["resolve_cross_repository_context"]
