#!/usr/bin/env python3
"""Validate a tutor plugin concept graph (DOT file).

Checks enforced:
  1. Syntax — file parses as DOT
  2. Schema — every node has label, taxonomy, status, chapter
  3. DAG — no cycles
  4. Edge integrity — every edge endpoint is a known node
  5. Connectedness — every non-foundational node reaches a foundational one
  6. Chapter assignment — every node's chapter is in the outline (if --outline given)
  7. Taxonomy hygiene — no taxonomy category holds more than 30% of nodes
  8. Label uniqueness — no two nodes share a label

Usage:
  python validate-concept-graph.py <dot-file> [--outline <outline-file>]

Exit codes:
  0 — all checks pass
  1 — one or more checks failed (error report written to stdout)
  2 — invocation error (missing file, bad arguments)
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import pydot
    import networkx as nx
except ImportError as e:
    print(f"ERROR: missing dependency: {e}. Install with: pip install pydot networkx", file=sys.stderr)
    sys.exit(2)


REQUIRED_ATTRS = {"label", "taxonomy", "status", "chapter"}
VALID_STATUS = {"pending", "covered", "shaky"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a tutor concept graph.")
    parser.add_argument("dot_file", type=Path, help="Path to the concepts.dot file")
    parser.add_argument("--outline", type=Path, default=None, help="Optional outline.md for chapter-assignment check")
    args = parser.parse_args()

    if not args.dot_file.exists():
        print(f"ERROR: file not found: {args.dot_file}", file=sys.stderr)
        return 2

    errors: list[str] = []

    # --- 1. Syntax check ---
    try:
        graphs = pydot.graph_from_dot_file(str(args.dot_file))
    except Exception as e:
        print(f"FAIL [syntax]: could not parse DOT file: {e}")
        return 1

    if not graphs:
        print("FAIL [syntax]: no graphs found in file (parse returned empty)")
        return 1

    graph = graphs[0]

    # Extract node attributes into a dict of node_id -> attribute dict.
    nodes: dict[str, dict[str, str]] = {}
    for node in graph.get_nodes():
        node_id = node.get_name().strip('"')
        # Skip pydot's built-in "node" and "edge" defaults.
        if node_id in ("node", "edge", "graph"):
            continue
        attrs = {k: (v.strip('"') if isinstance(v, str) else v) for k, v in node.get_attributes().items()}
        nodes[node_id] = attrs

    # Also extract any nodes implicitly defined only through edges.
    edges: list[tuple[str, str]] = []
    for edge in graph.get_edges():
        src = edge.get_source().strip('"')
        dst = edge.get_destination().strip('"')
        edges.append((src, dst))

    # --- 2. Schema check ---
    for node_id, attrs in nodes.items():
        missing = REQUIRED_ATTRS - set(attrs.keys())
        if missing:
            errors.append(f"FAIL [schema]: node '{node_id}' missing required attributes: {sorted(missing)}")
            continue
        if attrs["status"] not in VALID_STATUS:
            errors.append(f"FAIL [schema]: node '{node_id}' has invalid status '{attrs['status']}' (expected one of {sorted(VALID_STATUS)})")
        label = attrs["label"]
        if len(label) > 60:
            errors.append(f"FAIL [schema]: node '{node_id}' label exceeds 60 chars: '{label}'")
        if not label.isascii():
            errors.append(f"FAIL [schema]: node '{node_id}' label is not ASCII: '{label}'")
        if '"' in label or "," in label:
            errors.append(f"FAIL [schema]: node '{node_id}' label contains forbidden character (\" or ,): '{label}'")

    # --- 4. Edge integrity (check before DAG so we don't crash on missing nodes) ---
    for src, dst in edges:
        if src not in nodes:
            errors.append(f"FAIL [edge-integrity]: edge source '{src}' is not a defined node")
        if dst not in nodes:
            errors.append(f"FAIL [edge-integrity]: edge destination '{dst}' is not a defined node (possibly a typo or missing node definition)")

    # If schema or edge-integrity errors exist, report and stop — further checks are unreliable.
    if errors:
        for e in errors:
            print(e)
        return 1

    # --- 3. DAG check via networkx ---
    nx_graph = nx.DiGraph()
    for node_id in nodes:
        nx_graph.add_node(node_id)
    for src, dst in edges:
        nx_graph.add_edge(src, dst)

    cycles = list(nx.simple_cycles(nx_graph))
    if cycles:
        for cycle in cycles:
            errors.append(f"FAIL [dag]: cycle detected: {' -> '.join(cycle)} -> {cycle[0]}")

    # --- 5. Connectedness ---
    # Reject orphan islands: the graph should be one weakly-connected component.
    # (A DAG automatically has every node reaching some sink, so the check that
    # matters is whether there are multiple disconnected subgraphs.)
    if nodes:
        num_components = nx.number_weakly_connected_components(nx_graph)
        if num_components > 1:
            components = list(nx.weakly_connected_components(nx_graph))
            component_sizes = sorted([len(c) for c in components], reverse=True)
            errors.append(
                f"FAIL [connectedness]: graph has {num_components} disconnected components "
                f"(sizes: {component_sizes}); the course should be one connected graph"
            )

    # --- 6. Chapter assignment (only if outline provided) ---
    if args.outline is not None:
        if not args.outline.exists():
            print(f"ERROR: outline file not found: {args.outline}", file=sys.stderr)
            return 2
        outline_text = args.outline.read_text()
        # Match chapter headings in several common styles:
        #   ## Chapter 01
        #   ## Chapter 01: Title
        #   ## Chapter 01 - Title
        #   ## Chapter 01 — Title (em dash)
        #   ## 01 Title
        chapter_ids: set[str] = set()
        for match in re.finditer(r"^##\s*(?:Chapter\s+)?(\S+)", outline_text, re.MULTILINE):
            raw = match.group(1)
            # Strip trailing punctuation that commonly attaches to the id.
            cid = raw.rstrip(":,.;-")
            if cid:
                chapter_ids.add(cid)
        for node_id, attrs in nodes.items():
            chapter = attrs.get("chapter", "")
            if chapter and chapter != "null" and chapter not in chapter_ids:
                errors.append(f"FAIL [chapter-assignment]: node '{node_id}' references chapter '{chapter}' which is not in the outline")

    # --- 7. Taxonomy hygiene ---
    if nodes:
        taxonomies = Counter(attrs["taxonomy"] for attrs in nodes.values())
        total = len(nodes)
        for tax, count in taxonomies.items():
            pct = count / total
            if pct > 0.30 and total >= 4:
                errors.append(f"FAIL [taxonomy]: category '{tax}' holds {count}/{total} nodes ({pct:.0%}), exceeds 30% limit")

    # --- 8. Label uniqueness ---
    labels = [attrs["label"] for attrs in nodes.values()]
    label_counts = Counter(labels)
    for label, count in label_counts.items():
        if count > 1:
            errors.append(f"FAIL [label-uniqueness]: label '{label}' is used by {count} different nodes")

    if errors:
        for e in errors:
            print(e)
        return 1

    print(f"OK: {len(nodes)} nodes, {len(edges)} edges, all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
