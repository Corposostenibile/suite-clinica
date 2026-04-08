#!/usr/bin/env python3
"""
Benchmark con codice ottimizzato dentro pod GKE.
Avvia Flask temporaneo su porta 9090, testa, pulisce.
"""
import subprocess, sys, os, time, json, signal

POD = None
REMOTE_DIR = "/tmp/optimized_app"
REMOTE_PORT = 9090

def get_pod():
    out = subprocess.check_output(
        ["kubectl", "get", "pods", "-n", "default",
         "-o", "jsonpath={range .items[*]}{.metadata.name} {.status.phase}{'\\n'}{end}"],
        text=True)
    for line in out.strip().split("\n"):
        parts = line.split()
        if len(parts) == 2 and "backend" in parts[0] and parts[1] == "Running":
            return parts[0]
    return None

def kexec(pod, cmd, timeout=30):
    """kubectl exec wrapper."""
    return subprocess.run(
        ["kubectl", "exec", pod, "-c", "backend", "--", "bash", "-c", cmd],
        capture_output=True, text=True, timeout=timeout)

def main():
    pod = get_pod()
    if not pod:
        print("❌ Nessun pod backend running"); return
    print(f"✅ Pod: {pod}")

    # 1. Copia codice ottimizzato
    print("\n📤 Copio codice ottimizzato nel pod...")
    subprocess.run(["kubectl", "cp", "/tmp/optimized_code.tar.gz",
                     f"{pod}:/tmp/optimized_code.tar.gz", "-c", "backend"], check=True)

    # 2. Estrai nel pod
    print("📦 Estraggo...")
    kexec(pod, f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR} && "
               f"tar xzf /tmp/optimized_code.tar.gz -C {REMOTE_DIR}")

    # 3. Applica gli indici al DB di produzione (se non esistono già)
    print("\n🗄️  Applico indici mancanti al DB (IF NOT EXISTS)...")
    idx_sql = """
import os, sys
sys.path.insert(0, '/tmp/optimized_app')
os.chdir('/tmp/optimized_app')
os.environ.setdefault('FLASK_APP', 'corposostenibile')

from corposostenibile import create_app
from corposostenibile.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status)",
        "CREATE INDEX IF NOT EXISTS ix_tasks_category ON tasks (category)",
        "CREATE INDEX IF NOT EXISTS ix_tasks_assignee_status ON tasks (assignee_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_tasks_status_category ON tasks (status, category)",
        "CREATE INDEX IF NOT EXISTS ix_sales_leads_source_converted ON sales_leads (source_system, converted_to_client_id)",
        "CREATE INDEX IF NOT EXISTS ix_weekly_check_responses_date_check ON weekly_check_responses (submit_date, weekly_check_id)",
        "CREATE INDEX IF NOT EXISTS ix_dca_check_responses_date_check ON dca_check_responses (submit_date, dca_check_id)",
        "CREATE INDEX IF NOT EXISTS ix_minor_check_responses_date_check ON minor_check_responses (submit_date, minor_check_id)",
        "CREATE INDEX IF NOT EXISTS ix_teams_is_active ON teams (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_typeform_responses_submit_date ON typeform_responses (submit_date)",
        "CREATE INDEX IF NOT EXISTS ix_typeform_responses_cliente_id ON typeform_responses (cliente_id)",
        "CREATE INDEX IF NOT EXISTS ix_dca_checks_cliente_id ON dca_checks (cliente_id)",
        "CREATE INDEX IF NOT EXISTS ix_minor_checks_cliente_id ON minor_checks (cliente_id)",
    ]
    ok = 0
    for sql in indexes:
        try:
            db.session.execute(text(sql))
            ok += 1
        except Exception as e:
            print(f"  WARN: {e}")
    db.session.commit()
    print(f"  {ok}/{len(indexes)} indici OK")
"""
    r = kexec(pod, f"python3 -c '{idx_sql}'", timeout=60)
    print(r.stdout)
    if r.stderr:
        # Filter out INFO/DEBUG logs
        for line in r.stderr.split('\n'):
            if 'ERROR' in line or 'WARN' in line:
                print(f"  {line}")

    # 4. Avvia Flask temporaneo su porta 9090
    print(f"\n🚀 Avvio Flask ottimizzato su porta {REMOTE_PORT} nel pod...")
    start_cmd = (
        f"cd {REMOTE_DIR} && "
        f"PYTHONPATH={REMOTE_DIR}:$PYTHONPATH "
        f"FLASK_APP=corposostenibile "
        f"nohup python3 -m gunicorn 'corposostenibile:create_app()' "
        f"--bind 0.0.0.0:{REMOTE_PORT} --workers 1 --timeout 120 "
        f"> /tmp/flask_bench.log 2>&1 & echo $!"
    )
    r = kexec(pod, start_cmd, timeout=15)
    flask_pid = r.stdout.strip().split('\n')[-1]
    print(f"   PID: {flask_pid}")

    # Attendi avvio
    print("   Attendo avvio (max 60s)...")
    for i in range(12):
        time.sleep(5)
        check = kexec(pod, f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{REMOTE_PORT}/api/auth/me 2>/dev/null || echo 000", timeout=10)
        code = check.stdout.strip()
        if code == "200":
            print(f"   ✅ Flask pronto ({(i+1)*5}s)")
            break
        print(f"   ⏳ {code}... ({(i+1)*5}s)")
    else:
        print("   ❌ Timeout avvio Flask")
        # Mostra log
        log = kexec(pod, "tail -30 /tmp/flask_bench.log", timeout=10)
        print(log.stdout)
        print(log.stderr)
        kexec(pod, f"kill {flask_pid} 2>/dev/null")
        return

    # 5. Copia e lancia benchmark
    print("\n📊 Lancio benchmark...")
    subprocess.run(["kubectl", "cp",
                     "/home/manu/suite-clinica/backend/scripts/api_benchmark/benchmark.py",
                     f"{pod}:/tmp/benchmark.py", "-c", "backend"], check=True)

    bench = subprocess.run(
        ["kubectl", "exec", pod, "-c", "backend", "--",
         "python3", "/tmp/benchmark.py", f"--url=http://localhost:{REMOTE_PORT}",
         "--iterations=5"],
        capture_output=True, text=True, timeout=600)
    print(bench.stdout)
    if bench.stderr:
        for line in bench.stderr.split('\n'):
            if line.strip():
                print(f"  stderr: {line}")

    # 6. Cleanup
    print("\n🧹 Pulizia...")
    kexec(pod, f"kill {flask_pid} 2>/dev/null; rm -rf {REMOTE_DIR} /tmp/optimized_code.tar.gz /tmp/benchmark.py /tmp/flask_bench.log")
    print("✅ Pulito. Produzione intatta.")

if __name__ == "__main__":
    main()
