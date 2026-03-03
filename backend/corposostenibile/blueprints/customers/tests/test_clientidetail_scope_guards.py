from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


ROUTES_FILE = Path(__file__).resolve().parents[1] / "routes.py"


@dataclass
class RouteFn:
    blueprint: str
    path: str
    methods: tuple[str, ...]
    fn_name: str
    fn_node: ast.FunctionDef


def _extract_routes() -> list[RouteFn]:
    tree = ast.parse(ROUTES_FILE.read_text(encoding="utf-8"))
    out: list[RouteFn] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue

        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            if not isinstance(dec.func, ast.Attribute) or dec.func.attr != "route":
                continue
            if not isinstance(dec.func.value, ast.Name):
                continue
            if not dec.args or not isinstance(dec.args[0], ast.Constant) or not isinstance(dec.args[0].value, str):
                continue

            blueprint = dec.func.value.id
            path = dec.args[0].value
            methods = ("GET",)
            for kw in dec.keywords:
                if kw.arg != "methods" or not isinstance(kw.value, ast.List):
                    continue
                vals: list[str] = []
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        vals.append(elt.value.upper())
                if vals:
                    methods = tuple(vals)

            out.append(
                RouteFn(
                    blueprint=blueprint,
                    path=path,
                    methods=methods,
                    fn_name=node.name,
                    fn_node=node,
                )
            )

    return out


def _has_call(fn: ast.FunctionDef, call_name: str) -> bool:
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == call_name:
            return True
    return False


def _get_fn(routes: list[RouteFn], blueprint: str, path: str, method: str) -> RouteFn:
    matches = [
        r
        for r in routes
        if r.blueprint == blueprint and r.path == path and method.upper() in r.methods
    ]
    assert matches, f"Route non trovata: {blueprint}.route({path!r}, methods={[method]})"
    assert len(matches) == 1, (
        f"Route ambigua ({len(matches)} match): {blueprint}.route({path!r}, methods={[method]}), "
        f"funzioni={[m.fn_name for m in matches]}"
    )
    return matches[0]


def _assert_guard(
    routes: list[RouteFn],
    *,
    blueprint: str,
    path: str,
    method: str,
    any_of_calls: tuple[str, ...],
) -> None:
    route = _get_fn(routes, blueprint, path, method)
    if any(_has_call(route.fn_node, c) for c in any_of_calls):
        return
    calls_fmt = " or ".join(any_of_calls)
    assert False, (
        f"Guardia mancante in {route.fn_name} (linea {route.fn_node.lineno}) "
        f"per {blueprint}:{method} {path}. Attesa chiamata a: {calls_fmt}"
    )


def test_clientidetail_routes_have_explicit_scope_or_role_guards() -> None:
    routes = _extract_routes()

    # /api/v1/customers/... (clientiService API_BASE)
    api_cliente_scope_routes = [
        ("/<int:cliente_id>", "GET"),
        ("/<int:cliente_id>", "PATCH"),
        ("/<int:cliente_id>", "DELETE"),
        ("/<int:cliente_id>/initial-checks", "GET"),
        ("/<int:cliente_id>/professionisti/history", "GET"),
        ("/<int:cliente_id>/professionisti/assign", "POST"),
        ("/<int:cliente_id>/professionisti/<int:history_id>/interrupt", "POST"),
        ("/<int:cliente_id>/professionisti/legacy/interrupt", "POST"),
    ]
    for path, method in api_cliente_scope_routes:
        _assert_guard(
            routes,
            blueprint="api_bp",
            path=path,
            method=method,
            any_of_calls=("_require_cliente_scope_or_403",),
        )

    # Call bonus su cliente: deve almeno verificare assegnazione/scope esplicito.
    for path, method in [
        ("/<int:cliente_id>/call-bonus-history", "GET"),
        ("/<int:cliente_id>/call-bonus-request", "POST"),
    ]:
        _assert_guard(
            routes,
            blueprint="api_bp",
            path=path,
            method=method,
            any_of_calls=("_require_cliente_scope_or_403", "_is_assigned_to_cliente"),
        )

    # Route service-specific (anamnesi/diary) su API v1.
    for path, method in [
        ("/<int:cliente_id>/anamnesi/<service_type>", "GET"),
        ("/<int:cliente_id>/anamnesi/<service_type>", "POST"),
        ("/<int:cliente_id>/diary/<service_type>", "GET"),
        ("/<int:cliente_id>/diary/<service_type>", "POST"),
        ("/<int:cliente_id>/diary/<service_type>/<int:entry_id>", "PUT"),
        ("/<int:cliente_id>/diary/<service_type>/<int:entry_id>", "DELETE"),
        ("/<int:cliente_id>/diary/<service_type>/<int:entry_id>/history", "GET"),
    ]:
        _assert_guard(
            routes,
            blueprint="api_bp",
            path=path,
            method=method,
            any_of_calls=("_require_service_scope_or_403",),
        )

    # Route legacy /customers/... ancora usate da ClientiDetail via axios diretto.
    for path, method in [
        ("/<int:cliente_id>/stati/<servizio>/storico", "GET"),
        ("/<int:cliente_id>/nutrition/change", "POST"),
        ("/<int:cliente_id>/nutrition/history", "GET"),
        ("/<int:cliente_id>/nutrition/<int:plan_id>/versions", "GET"),
        ("/<int:cliente_id>/training/add", "POST"),
        ("/<int:cliente_id>/training/change", "POST"),
        ("/<int:cliente_id>/training/history", "GET"),
        ("/<int:cliente_id>/training/<int:plan_id>/versions", "GET"),
        ("/<int:cliente_id>/location/add", "POST"),
        ("/<int:cliente_id>/location/change/<int:loc_id>", "POST"),
        ("/<int:cliente_id>/location/history", "GET"),
    ]:
        _assert_guard(
            routes,
            blueprint="customers_bp",
            path=path,
            method=method,
            any_of_calls=("_require_service_scope_or_403",),
        )
