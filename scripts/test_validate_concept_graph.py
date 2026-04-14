"""Tests for validate-concept-graph.py.

Run with: pytest tutor/scripts/test_validate_concept_graph.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent / "validate-concept-graph.py"


def run_validator(dot_path, outline_path=None):
    """Run the validator and return (exit_code, stdout, stderr)."""
    args = [sys.executable, str(SCRIPT), str(dot_path)]
    if outline_path is not None:
        args.extend(["--outline", str(outline_path)])
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def write_dot(tmp_path, content):
    dot = tmp_path / "concepts.dot"
    dot.write_text(content)
    return dot


def write_outline(tmp_path, chapters):
    """Write a minimal outline.md with the given chapter IDs."""
    lines = ["# Outline\n"]
    for cid in chapters:
        lines.append(f"## Chapter {cid}\n")
    outline = tmp_path / "outline.md"
    outline.write_text("\n".join(lines))
    return outline


# ============================================================
# 1. Syntax check
# ============================================================

def test_parse_valid_dot_passes(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="fundamentals", status="pending", chapter="01"];
}
''')
    code, out, err = run_validator(dot)
    assert code == 0, f"stdout={out} stderr={err}"


def test_parse_syntax_error_fails(tmp_path):
    dot = write_dot(tmp_path, 'digraph G { a [label="unterminated ]; }')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "syntax" in (out + err).lower() or "parse" in (out + err).lower()


# ============================================================
# 2. Schema check
# ============================================================

def test_schema_missing_label_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [taxonomy="fundamentals", status="pending", chapter="01"];
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "label" in (out + err).lower()


def test_schema_missing_taxonomy_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", status="pending", chapter="01"];
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "taxonomy" in (out + err).lower()


def test_schema_missing_status_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="fundamentals", chapter="01"];
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "status" in (out + err).lower()


def test_schema_chapter_null_is_allowed(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="fundamentals", status="pending", chapter="null"];
}
''')
    code, out, err = run_validator(dot)
    assert code == 0, f"stdout={out} stderr={err}"


def test_schema_invalid_status_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="fundamentals", status="bogus", chapter="01"];
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "status" in (out + err).lower()


# ============================================================
# 3. DAG check
# ============================================================

def test_dag_acyclic_passes(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b [label="Beta", taxonomy="t1", status="pending", chapter="02"];
  c [label="Gamma", taxonomy="t1", status="pending", chapter="03"];
  b -> a;
  c -> b;
}
''')
    code, out, err = run_validator(dot)
    assert code == 0, f"stdout={out} stderr={err}"


def test_dag_cycle_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b [label="Beta", taxonomy="t1", status="pending", chapter="02"];
  a -> b;
  b -> a;
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "cycle" in (out + err).lower()


# ============================================================
# 4. Edge integrity
# ============================================================

def test_edge_to_missing_node_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  a -> ghost;
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "ghost" in (out + err).lower() or "missing" in (out + err).lower() or "integrity" in (out + err).lower()


# ============================================================
# 5. Connectedness — every non-foundational concept reaches a foundational one
# ============================================================

def test_all_reach_foundational_passes(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b [label="Beta", taxonomy="t1", status="pending", chapter="02"];
  b -> a;
}
''')
    code, out, err = run_validator(dot)
    assert code == 0, f"stdout={out} stderr={err}"


def test_orphan_component_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b [label="Beta", taxonomy="t1", status="pending", chapter="02"];
  b -> a;
  c [label="Gamma", taxonomy="t1", status="pending", chapter="03"];
  d [label="Delta", taxonomy="t1", status="pending", chapter="04"];
  d -> c;
  c -> d;
}
''')
    code, out, err = run_validator(dot)
    assert code != 0


# ============================================================
# 6. Chapter assignment check (requires outline)
# ============================================================

def test_chapter_assignment_valid_passes(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b [label="Beta", taxonomy="t1", status="pending", chapter="02"];
  b -> a;
}
''')
    outline = write_outline(tmp_path, ["01", "02"])
    code, out, err = run_validator(dot, outline)
    assert code == 0, f"stdout={out} stderr={err}"


def test_chapter_assignment_missing_chapter_fails(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="99"];
}
''')
    outline = write_outline(tmp_path, ["01", "02"])
    code, out, err = run_validator(dot, outline)
    assert code != 0
    assert "99" in (out + err) or "chapter" in (out + err).lower()


def test_chapter_assignment_null_with_outline_passes(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="null"];
}
''')
    outline = write_outline(tmp_path, ["01"])
    code, out, err = run_validator(dot, outline)
    assert code == 0


def test_chapter_check_skipped_without_outline(tmp_path):
    """If --outline is not provided, the chapter check is skipped."""
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="99"];
}
''')
    code, out, err = run_validator(dot)
    assert code == 0, f"stdout={out} stderr={err}"


# ============================================================
# 7. Taxonomy hygiene — no taxonomy >30% of nodes
# ============================================================

def test_taxonomy_balanced_passes(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="A", taxonomy="t1", status="pending", chapter="01"];
  b [label="B", taxonomy="t2", status="pending", chapter="01"];
  c [label="C", taxonomy="t3", status="pending", chapter="01"];
  d [label="D", taxonomy="t4", status="pending", chapter="01"];
  b -> a;
  c -> a;
  d -> a;
}
''')
    code, out, err = run_validator(dot)
    assert code == 0, f"stdout={out} stderr={err}"


def test_taxonomy_bloated_fails(tmp_path):
    # 3 of 4 nodes are in "t1" (75%) — fails the 30% rule.
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="A", taxonomy="t1", status="pending", chapter="01"];
  b [label="B", taxonomy="t1", status="pending", chapter="01"];
  c [label="C", taxonomy="t1", status="pending", chapter="01"];
  d [label="D", taxonomy="t2", status="pending", chapter="01"];
  b -> a;
  c -> a;
  d -> a;
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "taxonomy" in (out + err).lower()


# ============================================================
# 8. Label uniqueness
# ============================================================

def test_unique_labels_pass(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b [label="Beta", taxonomy="t1", status="pending", chapter="01"];
  b -> a;
}
''')
    code, out, err = run_validator(dot)
    assert code == 0, f"stdout={out} stderr={err}"


def test_duplicate_labels_fail(tmp_path):
    dot = write_dot(tmp_path, '''
digraph G {
  a [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b [label="Alpha", taxonomy="t1", status="pending", chapter="01"];
  b -> a;
}
''')
    code, out, err = run_validator(dot)
    assert code != 0
    assert "label" in (out + err).lower() or "duplicate" in (out + err).lower()
