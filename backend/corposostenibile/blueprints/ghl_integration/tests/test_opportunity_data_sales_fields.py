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


def test_opportunity_data_extraction_includes_sales_fields() -> None:
    tree = _load_tree()
    fn = _get_function_node(tree, "_extract_opportunity_contact_fields")

    source = ast.get_source_segment(ROUTES_FILE.read_text(encoding="utf-8"), fn) or ""
    assert "sales_consultant" in source
    assert "sales_person" in source


def test_opportunity_data_save_persists_sales_fields() -> None:
    tree = _load_tree()
    fn = _get_function_node(tree, "_save_opportunity_data_payload")

    assigns = []
    for node in ast.walk(fn):
        if isinstance(node, ast.keyword):
            assigns.append(node.arg)

    assert "sales_consultant" in assigns
    assert "sales_person_id" in assigns


def test_sales_person_resolver_exists() -> None:
    tree = _load_tree()
    _get_function_node(tree, "_resolve_sales_person_by_name")
