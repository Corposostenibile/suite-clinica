#!/bin/bash
# Lancia benchmark API direttamente nel pod GKE di produzione.
#
# Uso:
#   bash scripts/api_benchmark/run_prod.sh
#   bash scripts/api_benchmark/run_prod.sh --iterations 10

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔍 Cerco pod backend in produzione..."
POD=$(kubectl get pods -n default -o jsonpath='{range .items[*]}{.metadata.name} {.status.phase}{"\n"}{end}' \
  | grep Running | grep "suite-clinica-backend" | head -1 | awk '{print $1}')

if [ -z "$POD" ]; then
  echo "❌ Nessun pod backend running trovato"
  exit 1
fi
echo "✅ Pod: $POD"

echo "📤 Copio script nel pod..."
kubectl cp "$SCRIPT_DIR/benchmark.py" "$POD:/tmp/benchmark.py" -c backend

echo "🚀 Lancio benchmark in produzione..."
echo ""
kubectl exec "$POD" -c backend -- python3 /tmp/benchmark.py "$@"

echo ""
echo "📥 Recupero risultati JSON..."
LATEST=$(kubectl exec "$POD" -c backend -- bash -c 'ls -t /tmp/benchmark_*.json 2>/dev/null | head -1')
if [ -n "$LATEST" ]; then
  LOCAL_FILE="$SCRIPT_DIR/benchmark_prod_$(date +%Y%m%d_%H%M%S).json"
  kubectl cp "$POD:$LATEST" "$LOCAL_FILE" -c backend
  echo "✅ Risultati salvati in: $LOCAL_FILE"
fi
