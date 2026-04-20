from __future__ import annotations

import ast
from pathlib import Path


ROUTES_FILE = Path(__file__).resolve().parents[1] / "routes.py"


def _load_tree() -> ast.AST:
    return ast.parse(ROUTES_FILE.read_text(encoding="utf-8"))


def _get_function_node(tree: ast.AST, fn_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return node
    raise AssertionError(f"Funzione non trovata: {fn_name}")


def test_old_suite_confirm_assignment_populates_ai_analysis_snapshot() -> None:
    tree = _load_tree()
    fn = _get_function_node(tree, "api_confirm_assignment")
    source = ast.get_source_segment(ROUTES_FILE.read_text(encoding="utf-8"), fn) or ""
    assert "ai_analysis_snapshot" in source
    assert "deepcopy" in source
