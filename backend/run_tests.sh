#!/bin/bash

# Test suite con isolamento transazionale (SAVEPOINT rollback, no TRUNCATE).
# Singola invocazione pytest → nessun overhead di startup ripetuto.
#
# Opzioni:
#   --parallel | -p   Esegue i test in parallelo con pytest-xdist (-n auto)
#   --seq | -s        Esegue i test in sequenza (default)
#
# Esempi:
#   ./run_tests.sh              # sequenziale
#   ./run_tests.sh -p           # parallelo
#   ./run_tests.sh -- -k auth   # passa flag extra a pytest

PARALLEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --seq|-s)
            PARALLEL=false
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

echo "--- STARTING TEST SUITE ---"

if [ "$PARALLEL" = true ]; then
    echo "Mode: parallel (pytest-xdist -n auto)"
    poetry run pytest tests/api/ -v -n auto "$@"
else
    echo "Mode: sequential"
    poetry run pytest tests/api/ -v "$@"
fi

echo "--- ALL TESTS COMPLETED ---"
