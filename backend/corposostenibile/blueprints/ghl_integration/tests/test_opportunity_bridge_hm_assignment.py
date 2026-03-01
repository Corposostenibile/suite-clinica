from __future__ import annotations

import ast
from pathlib import Path


BRIDGE_FILE = Path(__file__).resolve().parents[1] / "opportunity_bridge.py"


def _get_function_node(tree: ast.AST, fn_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return node
    raise AssertionError(f"Funzione non trovata: {fn_name}")


def test_bridge_has_health_manager_resolver() -> None:
    tree = ast.parse(BRIDGE_FILE.read_text(encoding="utf-8"))
    _get_function_node(tree, "_resolve_health_manager_id_by_email")


def test_bridge_assigns_health_manager_id_on_cliente() -> None:
    tree = ast.parse(BRIDGE_FILE.read_text(encoding="utf-8"))
    process_fn = _get_function_node(tree, "process_opportunity_data_bridge")

    has_health_manager_assignment = False
    for node in ast.walk(process_fn):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "health_manager_id":
                has_health_manager_assignment = True
                break
        if has_health_manager_assignment:
            break

    assert has_health_manager_assignment, (
        "process_opportunity_data_bridge deve valorizzare cliente.health_manager_id "
        "al momento della creazione/aggiornamento lead."
    )
