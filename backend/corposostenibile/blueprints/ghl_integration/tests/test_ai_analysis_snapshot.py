from __future__ import annotations

import ast
from pathlib import Path


ROUTES_FILE = Path(__file__).resolve().parents[1] / "routes.py"
TEAM_API_FILE = Path(__file__).resolve().parents[2] / "team" / "api.py"
MODELS_FILE = Path(__file__).resolve().parents[3] / "models.py"


def _load_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _get_function_node(tree: ast.AST, fn_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return node
    raise AssertionError(f"Funzione non trovata: {fn_name}")


def test_team_confirm_assignment_populates_ai_analysis_snapshot() -> None:
    tree = _load_tree(TEAM_API_FILE)
    fn = _get_function_node(tree, "api_confirm_assignment")
    source = ast.get_source_segment(TEAM_API_FILE.read_text(encoding="utf-8"), fn) or ""
    assert "ai_analysis_snapshot" in source
    assert "deepcopy" in source


def test_service_cliente_assignment_model_has_snapshot_column() -> None:
    source = MODELS_FILE.read_text(encoding="utf-8")
    assert "ai_analysis_snapshot = db.Column(JSONB)" in source


def test_ghl_assignments_api_exposes_snapshot() -> None:
    tree = _load_tree(ROUTES_FILE)
    fn = _get_function_node(tree, "api_assignments")
    source = ast.get_source_segment(ROUTES_FILE.read_text(encoding="utf-8"), fn) or ""
    assert "ai_analysis_snapshot" in source
