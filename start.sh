#!/bin/bash

#############################################
#  CORPOSOSTENIBILE SUITE - STARTUP SCRIPT  #
#############################################

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directory base
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# File per salvare i PID
PID_FILE="$BASE_DIR/.running_pids"

# Funzione per stampare header
print_header() {
    echo -e "${PURPLE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     🏥  CORPOSOSTENIBILE SUITE  🏥                        ║"
    echo "║                                                           ║"
    echo "║     Backend + Clinica + Amministrativa                    ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Funzione per verificare se un comando esiste
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 non trovato. Installalo prima di continuare.${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $1 trovato${NC}"
    return 0
}

# Funzione per verificare se una porta è in uso
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Porta in uso
    fi
    return 1  # Porta libera
}

# Funzione per fermare i processi
stop_all() {
    echo -e "\n${YELLOW}🛑 Arresto di tutti i servizi...${NC}"

    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if ps -p $pid > /dev/null 2>&1; then
                kill $pid 2>/dev/null
                echo -e "${CYAN}   Processo $pid terminato${NC}"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    # Termina anche eventuali processi npm/node/flask rimasti
    pkill -f "flask run --port 5001" 2>/dev/null
    pkill -f "vite.*3000" 2>/dev/null
    pkill -f "vite.*3001" 2>/dev/null
    pkill -f "celery.*corposostenibile" 2>/dev/null

    # Ferma Qdrant container (non lo rimuove)
    docker stop qdrant 2>/dev/null && echo -e "${CYAN}   Qdrant fermato${NC}"

    echo -e "${GREEN}✅ Tutti i servizi sono stati arrestati${NC}"
    exit 0
}

# Trap per CTRL+C
trap stop_all SIGINT SIGTERM

# Funzione per attendere che un servizio sia pronto
wait_for_service() {
    local port=$1
    local name=$2
    local max_attempts=30
    local attempt=0

    echo -ne "${CYAN}   Attendo $name (porta $port)...${NC}"

    while ! check_port $port; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo -e " ${RED}TIMEOUT${NC}"
            return 1
        fi
        sleep 1
        echo -n "."
    done

    echo -e " ${GREEN}OK${NC}"
    return 0
}

# ==================== MAIN ====================

print_header

# Verifica prerequisiti
echo -e "${BLUE}📋 Verifica prerequisiti...${NC}"
echo ""

MISSING=0

check_command "python3" || MISSING=1
check_command "node" || MISSING=1
check_command "npm" || MISSING=1
check_command "poetry" || MISSING=1

# Verifica Redis
if check_command "redis-cli"; then
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis è in esecuzione${NC}"
    else
        echo -e "${YELLOW}⚠ Redis non è in esecuzione. Provo ad avviarlo...${NC}"
        if command -v brew &> /dev/null; then
            brew services start redis 2>/dev/null || redis-server --daemonize yes
        else
            redis-server --daemonize yes
        fi
        sleep 2
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Redis avviato${NC}"
        else
            echo -e "${YELLOW}⚠ Redis non disponibile. Celery non funzionerà.${NC}"
        fi
    fi
fi

echo ""

if [ $MISSING -eq 1 ]; then
    echo -e "${RED}❌ Prerequisiti mancanti. Installa i componenti necessari.${NC}"
    exit 1
fi

# Pulisci vecchi PID
rm -f "$PID_FILE"

# ==================== QDRANT ====================

echo -e "${BLUE}🧠 [0/4] Avvio Qdrant Vector DB (porta 6333)...${NC}"

if check_port 6333; then
    echo -e "${YELLOW}   ⚠ Porta 6333 già in uso. Qdrant potrebbe essere già avviato.${NC}"
else
    if command -v docker &> /dev/null; then
        # Controlla se il container esiste già (fermo)
        if docker ps -a --format '{{.Names}}' | grep -q '^qdrant$'; then
            docker start qdrant > /dev/null 2>&1
            echo -e "${CYAN}   Container 'qdrant' riavviato${NC}"
        else
            docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
                -v "$HOME/qdrant_storage:/qdrant/storage" \
                qdrant/qdrant > /dev/null 2>&1
            echo -e "${CYAN}   Container 'qdrant' creato e avviato${NC}"
        fi
        wait_for_service 6333 "Qdrant"
    else
        echo -e "${YELLOW}   ⚠ Docker non disponibile, Qdrant saltato. Il SOP Chatbot non funzionerà.${NC}"
    fi
fi

# ==================== BACKEND ====================

echo -e "${BLUE}🔧 [1/4] Avvio Backend Flask (porta 5001)...${NC}"

if check_port 5001; then
    echo -e "${YELLOW}   ⚠ Porta 5001 già in uso. Backend potrebbe essere già avviato.${NC}"
else
    cd "$BASE_DIR/backend"

    # Verifica se poetry env esiste, altrimenti installa
    if ! poetry env info > /dev/null 2>&1; then
        echo -e "${CYAN}   Installazione dipendenze Python...${NC}"
        poetry install --no-interaction
    fi

    # Avvia Flask
    poetry run flask run --port 5001 > "$BASE_DIR/logs/backend.log" 2>&1 &
    FLASK_PID=$!
    echo $FLASK_PID >> "$PID_FILE"

    wait_for_service 5001 "Backend Flask"
fi

# ==================== CELERY ====================

echo -e "${BLUE}⚡ [2/4] Avvio Celery Worker...${NC}"

if redis-cli ping > /dev/null 2>&1; then
    cd "$BASE_DIR/backend"
    poetry run celery -A corposostenibile.celery_app worker --loglevel=warning > "$BASE_DIR/logs/celery.log" 2>&1 &
    CELERY_PID=$!
    echo $CELERY_PID >> "$PID_FILE"
    echo -e "${GREEN}   ✓ Celery Worker avviato (PID: $CELERY_PID)${NC}"

    poetry run celery -A corposostenibile.celery_app beat --loglevel=warning > "$BASE_DIR/logs/celery-beat.log" 2>&1 &
    CELERY_BEAT_PID=$!
    echo $CELERY_BEAT_PID >> "$PID_FILE"
    echo -e "${GREEN}   ✓ Celery Beat avviato (PID: $CELERY_BEAT_PID)${NC}"
else
    echo -e "${YELLOW}   ⚠ Redis non disponibile, Celery saltato${NC}"
fi

# ==================== FRONTEND CLINICA ====================

echo -e "${BLUE}🏥 [3/4] Avvio Frontend Clinica (porta 3000)...${NC}"

if check_port 3000; then
    echo -e "${YELLOW}   ⚠ Porta 3000 già in uso. Clinica potrebbe essere già avviata.${NC}"
else
    cd "$BASE_DIR/corposostenibile-clinica"

    # Verifica node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${CYAN}   Installazione dipendenze npm...${NC}"
        npm install --silent
    fi

    npm run dev > "$BASE_DIR/logs/clinica.log" 2>&1 &
    CLINICA_PID=$!
    echo $CLINICA_PID >> "$PID_FILE"

    wait_for_service 3000 "Frontend Clinica"
fi

# ==================== FRONTEND AMMINISTRATIVA ====================

echo -e "${BLUE}🏢 [4/4] Avvio Frontend Amministrativa (porta 3001)...${NC}"

if check_port 3001; then
    echo -e "${YELLOW}   ⚠ Porta 3001 già in uso. Admin potrebbe essere già avviata.${NC}"
else
    cd "$BASE_DIR/corposostenibile-amministrativa"

    # Verifica node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${CYAN}   Installazione dipendenze npm...${NC}"
        npm install --silent
    fi

    npm run dev > "$BASE_DIR/logs/admin.log" 2>&1 &
    ADMIN_PID=$!
    echo $ADMIN_PID >> "$PID_FILE"

    wait_for_service 3001 "Frontend Admin"
fi

# ==================== RIEPILOGO ====================

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   ✅  TUTTI I SERVIZI SONO STATI AVVIATI!                 ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   🧠 Qdrant DB:        ${CYAN}http://localhost:6333${GREEN}              ║${NC}"
echo -e "${GREEN}║   🔧 Backend API:      ${CYAN}http://127.0.0.1:5001${GREEN}             ║${NC}"
echo -e "${GREEN}║   🏥 Suite Clinica:    ${CYAN}http://localhost:3000${GREEN}             ║${NC}"
echo -e "${GREEN}║   🏢 Suite Admin:      ${CYAN}http://localhost:3001${GREEN}             ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   📁 Logs: ${YELLOW}$BASE_DIR/logs/${GREEN}                  ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   ${YELLOW}Premi CTRL+C per fermare tutti i servizi${GREEN}              ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Apri automaticamente i browser (opzionale, commenta se non vuoi)
if command -v open &> /dev/null; then
    echo -e "${CYAN}🌐 Apro i browser...${NC}"
    sleep 2
    open "http://localhost:3000" 2>/dev/null
    open "http://localhost:3001" 2>/dev/null
fi

# Mantieni lo script attivo per permettere CTRL+C
echo -e "${PURPLE}Script in esecuzione. I log vengono scritti in $BASE_DIR/logs/${NC}"
echo ""

# Mostra i log in tempo reale (tail combinato)
tail -f "$BASE_DIR/logs/backend.log" "$BASE_DIR/logs/clinica.log" "$BASE_DIR/logs/admin.log" 2>/dev/null
