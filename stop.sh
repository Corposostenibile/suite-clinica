#!/bin/bash

#############################################
#   CORPOSOSTENIBILE SUITE - STOP SCRIPT    #
#############################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BASE_DIR/.running_pids"

echo -e "${YELLOW}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   🛑  ARRESTO CORPOSOSTENIBILE SUITE                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Ferma processi dal PID file
if [ -f "$PID_FILE" ]; then
    echo -e "${CYAN}Arresto processi salvati...${NC}"
    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null
            echo -e "   ${GREEN}✓ Processo $pid terminato${NC}"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

# Ferma eventuali processi rimasti
echo -e "${CYAN}Pulizia processi residui...${NC}"

# Flask
pkill -f "flask run --port 5001" 2>/dev/null && echo -e "   ${GREEN}✓ Flask terminato${NC}"

# Celery
pkill -f "celery.*corposostenibile" 2>/dev/null && echo -e "   ${GREEN}✓ Celery terminato${NC}"

# Vite (frontend)
pkill -f "vite.*corposostenibile-clinica" 2>/dev/null && echo -e "   ${GREEN}✓ Frontend Clinica terminato${NC}"
pkill -f "vite.*corposostenibile-amministrativa" 2>/dev/null && echo -e "   ${GREEN}✓ Frontend Admin terminato${NC}"

# Node processes sulle porte specifiche
lsof -ti:3000 | xargs kill -9 2>/dev/null
lsof -ti:3001 | xargs kill -9 2>/dev/null
lsof -ti:5001 | xargs kill -9 2>/dev/null

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅  Tutti i servizi sono stati arrestati                ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
