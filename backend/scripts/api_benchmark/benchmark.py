#!/usr/bin/env python3
"""
Benchmark endpoint critici della Suite Clinica.
Progettato per essere eseguito in 2 modi:

  1) DENTRO il pod GKE (via kubectl cp + kubectl exec) → testa direttamente localhost:8080
  2) LOCALE con port-forward → testa via kubectl port-forward

Uso consigliato (produzione):
  # Dal VPS, one-liner:
  kubectl cp scripts/api_benchmark/benchmark.py <POD>:/tmp/benchmark.py -c backend
  kubectl exec <POD> -c backend -- python3 /tmp/benchmark.py

  # Oppure usa lo script wrapper:
  bash scripts/api_benchmark/run_prod.sh

Uso locale:
  poetry run python scripts/api_benchmark/benchmark.py --url http://localhost:5001
"""

import argparse
import json
import time
import statistics
import os
from datetime import datetime
from typing import Optional
import requests


# Credenziali di test
EMAIL = "dev@corposostenibile.it"
PASSWORD = "Dev123?"

# Tutti gli endpoint critici (GET only, solo interni)
ALL_ENDPOINTS = [
    ("/api/tasks/",                                      "Tasks",                         4730, 791),
    ("/api/client-checks/professionisti/nutrizione",     "Checks Nutrizione Prof",        3735, 4001),
    ("/api/client-checks/azienda/stats",                 "Checks Azienda Stats",          3672, 3733),
    ("/api/team/{TT}/health_manager",                    "Team Health Manager",           2387, 3717),
    ("/api/team/{TT}/coach",                             "Team Coach",                    2045, 3319),
    ("/api/team/teams",                                  "Team Lista",                    3031, 1495),
    ("/api/team/{TT}/nutrizione",                        "Team Nutrizione",               2423, 2993),
    ("/api/team/professionals/criteria",                 "Team Criteri Prof",             None, 2885),
    ("/api/team/{TT}/psicologia",                        "Team Psicologia",               2018, 2552),
    ("/old-suite/api/leads",                             "Old Suite Leads",               2431, 2382),
    ("/api/client-checks/professionisti/coach",          "Checks Coach Prof",             2439, 1553),
]


def run_benchmark(base_url: str, iterations: int, target: int):
    """Esegue benchmark completo."""
    s = requests.Session()

    # Login (remember_me=True per persistere sessione tra richieste)
    r = s.post(f"{base_url}/api/auth/login",
               json={"email": EMAIL, "password": PASSWORD, "remember_me": True},
               timeout=30)
    d = r.json()
    if not d.get("success"):
        print(f"LOGIN FALLITO: {d.get('error')}")
        return None
    print(f"Login OK: {d['user'].get('full_name')} (role: {d['user'].get('role')})")

    # Verifica sessione
    me = s.get(f"{base_url}/api/auth/me", timeout=10).json()
    if not me.get("authenticated"):
        print("SESSIONE NON VALIDA")
        return None

    # Team token
    tt = None
    try:
        tr = s.get(f"{base_url}/api/team/teams", timeout=60)
        if tr.status_code == 200:
            data = tr.json()
            teams = data if isinstance(data, list) else data.get("teams", data.get("data", []))
            if teams:
                tt = str(teams[0].get("token") or teams[0].get("id") or "")
                if tt:
                    print(f"Team token: {tt}")
    except Exception as e:
        print(f"Team token error: {e}")

    print(f"\nTest: {len(ALL_ENDPOINTS)} endpoint, {iterations} iterazioni, target <{target}ms\n")

    results = []
    for path, desc, t15, t8 in ALL_ENDPOINTS:
        if "{TT}" in path:
            if not tt:
                results.append({"endpoint": path, "desc": desc, "skipped": True})
                print(f"SKIP  {desc:<35} (no team token)")
                continue
            path = path.replace("{TT}", tt)

        times = []
        codes = []
        for i in range(iterations):
            try:
                t0 = time.perf_counter()
                resp = s.get(f"{base_url}{path}", timeout=60)
                ms = (time.perf_counter() - t0) * 1000
                times.append(ms)
                codes.append(resp.status_code)
            except Exception as e:
                codes.append(-1)

        if not times:
            results.append({"endpoint": path, "desc": desc, "error": True})
            print(f"ERR   {desc:<35}")
            continue

        avg = statistics.mean(times)
        ok = avg < target
        var = round(((avg - t8) / t8) * 100, 1) if t8 else None
        icon = "PASS" if ok else "FAIL"
        var_str = f"{var:+.1f}%" if var is not None else "N/A"

        results.append({
            "endpoint": path,
            "desc": desc,
            "t15d": t15,
            "t8d": t8,
            "avg": round(avg),
            "min": round(min(times)),
            "max": round(max(times)),
            "median": round(statistics.median(times)),
            "passed": ok,
            "codes": list(set(codes)),
            "var": var,
        })

        print(f"{icon:4s}  {desc:<35} avg={round(avg):>5}ms  min={round(min(times)):>5}ms  "
              f"max={round(max(times)):>5}ms  8gg={t8 if t8 else 'N/A':>5}  var={var_str:>8}")

    # Summary table
    print()
    print("=" * 120)
    print(f"{'Endpoint':<50} {'15 giorni':>10} {'8 giorni':>10} {'PRODUZIONE':>11} "
          f"{'Target':>8} {'Stato':>6} {'Variaz':>8}")
    print("-" * 120)
    ok_count = fail_count = err_count = skip_count = 0
    for r in results:
        if r.get("skipped"):
            print(f"{r['endpoint']:<50} {'':>10} {'':>10} {'SKIP':>11}")
            skip_count += 1; continue
        if r.get("error"):
            print(f"{r['endpoint']:<50} {'':>10} {'':>10} {'ERRORE':>11}")
            err_count += 1; continue
        t15 = f"{r['t15d']}ms" if r['t15d'] else "N/A"
        t8 = f"{r['t8d']}ms" if r['t8d'] else "N/A"
        var = f"{r['var']:+.1f}%" if r["var"] is not None else "N/A"
        icon = "OK" if r["passed"] else "LENTO"
        print(f"{r['endpoint']:<50} {t15:>10} {t8:>10} {r['avg']:>7}ms    "
              f"{target:>6}ms {icon:>6} {var:>8}")
        if r["passed"]: ok_count += 1
        else: fail_count += 1

    print("=" * 120)
    total = len(results)
    print(f"\nRISULTATI: {ok_count}/{total} OK | {fail_count}/{total} LENTI | "
          f"{err_count}/{total} ERRORI | {skip_count}/{total} SKIP")

    if fail_count > 0:
        print("\nENDPOINT DA OTTIMIZZARE:")
        for r in results:
            if not r.get("passed") and not r.get("skipped") and not r.get("error"):
                print(f"  {r['endpoint']}: media {r['avg']}ms, max {r['max']}ms")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "env": "production-gke" if base_url == "http://localhost:8080" else base_url,
        "target_ms": target,
        "iterations": iterations,
        "summary": {"ok": ok_count, "fail": fail_count, "err": err_count, "skip": skip_count},
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark API Suite Clinica")
    parser.add_argument("--url", default="http://localhost:8080",
                        help="URL base (default: http://localhost:8080 per esecuzione dentro pod)")
    parser.add_argument("--iterations", type=int, default=5, help="Iterazioni per endpoint (default: 5)")
    parser.add_argument("--target", type=int, default=2000, help="Target ms (default: 2000)")
    args = parser.parse_args()

    print(f"Benchmark Suite Clinica - {args.url}")
    data = run_benchmark(args.url, args.iterations, args.target)

    if data:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/benchmark_{ts}.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nJSON salvato: {filename}")


if __name__ == "__main__":
    main()
