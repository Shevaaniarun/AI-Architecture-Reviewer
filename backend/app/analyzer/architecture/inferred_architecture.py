"""Simple directory-grouped architecture inferred from import dependencies."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.analyzer.graph.dependency_graph import DependencyGraph


@dataclass(frozen=True)
class ArchitectureComponent:
    """A top-level directory grouping of analyzed source files."""

    name: str
    files: tuple[str, ...]


@dataclass(frozen=True)
class ArchitectureRelationship:
    """An aggregated directed dependency between directory components."""

    source: str
    target: str
    file_dependency_count: int


@dataclass(frozen=True)
class InferredArchitecture:
    """A candidate architecture view derived from directories and imports."""

    status: str
    components: tuple[ArchitectureComponent, ...]
    relationships: tuple[ArchitectureRelationship, ...]
    mermaid: str


def infer_architecture(dependencies: DependencyGraph) -> InferredArchitecture:
    """Group files by their first directory and aggregate actual import edges."""
    component_by_file = {
        filename: _component_name(filename)
        for filename in dependencies.graph.nodes
    }
    files_by_component: dict[str, list[str]] = {}
    for filename, component in component_by_file.items():
        files_by_component.setdefault(component, []).append(filename)

    components = tuple(
        ArchitectureComponent(name=name, files=tuple(sorted(files, key=str.casefold)))
        for name, files in sorted(files_by_component.items(), key=lambda item: item[0].casefold())
    )
    dependency_counts: dict[tuple[str, str], int] = {}
    for source, target in dependencies.graph.edges:
        source_component = component_by_file[source]
        target_component = component_by_file[target]
        if source_component != target_component:
            pair = (source_component, target_component)
            dependency_counts[pair] = dependency_counts.get(pair, 0) + 1

    relationships = tuple(
        ArchitectureRelationship(source, target, count)
        for (source, target), count in sorted(
            dependency_counts.items(),
            key=lambda item: (item[0][0].casefold(), item[0][1].casefold()),
        )
    )
    return InferredArchitecture(
        status="INFERRED",
        components=components,
        relationships=relationships,
        mermaid=generate_mermaid(components, relationships),
    )


def generate_mermaid(
    components: tuple[ArchitectureComponent, ...],
    relationships: tuple[ArchitectureRelationship, ...],
) -> str:
    """Render a Mermaid flowchart using only inferred component relationships."""
    identifiers = {component.name: f"component_{index}" for index, component in enumerate(components)}
    lines = ["flowchart TD"]
    for component in components:
        label = _safe_mermaid_label(component.name)
        lines.append(f'    {identifiers[component.name]}["{label}"]')
    for relationship in relationships:
        source_id = identifiers[relationship.source]
        target_id = identifiers[relationship.target]
        lines.append(f"    {source_id} --> {target_id}")
    return "\n".join(lines)


def _component_name(filename: str) -> str:
    parts = PurePosixPath(filename).parts
    if len(parts) == 1:
        return "Root"
    return parts[0]


def _safe_mermaid_label(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9 _.-]", " ", value)
    return " ".join(normalized.split()) or "Component"
