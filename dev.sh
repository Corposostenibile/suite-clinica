#!/bin/bash
# Dev Manager Locale per Suite Clinica (senza Docker)
# Gestisce l'ambiente di sviluppo locale con Poetry e servizi nativi
# VERSIONE FINALE con Gunicorn (background) e Flask Dev Server (foreground)

set -e

# Configurazione
DEFAULT_HOST="localhost"

# Configurazione sviluppatori
DEVELOPERS=("manu" "samu" "matte")
PORTS_APP=("5001" "5002" "5003")
PORTS_FRONTEND=("3001" "3002" "3003")
DB_PORT="5432"  # Porta fissa per tutti gli sviluppatori
DB_NAMES=("suite_clinica_dev_manu" "suite_clinica_dev_samu" "suite_clinica_dev_matte")

# Variabili globali
PROJECT_DIR=""
VENV_PATH=""

# Funzione per impostare PROJECT_DIR in base allo sviluppatore
set_project_dir() {
    local dev=$1
    if [[ -n "$dev" ]]; then
        PROJECT_DIR="/home/$dev/suite-clinica"
    else
        PROJECT_DIR="/home/$(whoami)/suite-clinica"
    fi
    VENV_PATH="$PROJECT_DIR/.venv"
    export POETRY_CACHE_DIR="/home/$dev/.cache/pypoetry"
    export POETRY_VIRTUALENVS_PATH="/home/$dev/.cache/pypoetry/virtualenvs"
    export POETRY_VIRTUALENVS_CREATE=true
}

# Colori
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# Funzioni di log
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Funzioni di utilità
validate_developer() {
    [[ " ${DEVELOPERS[@]} " =~ " $1 " ]] || { log_error "Sviluppatore '$1' non valido. Scegli tra: ${DEVELOPERS[*]}"; exit 1; }
}

get_developer_info() {
    local dev=$1
    for i in "${!DEVELOPERS[@]}"; do
        if [[ "${DEVELOPERS[$i]}" == "$dev" ]]; then
            echo "${PORTS_APP[$i]} $DB_PORT ${DB_NAMES[$i]} ${PORTS_FRONTEND[$i]}"; return
        fi
    done
}

# Aggiorna il DATABASE_URL nel file .env in base allo sviluppatore
update_env_database_url() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local db_name="${info[2]}"

    local new_database_url="postgresql://suite_clinica:password@localhost:$DB_PORT/$db_name"
    local env_file="$PROJECT_DIR/backend/.env"

    if [[ -f "$env_file" ]]; then
        # Usa sed per sostituire la linea DATABASE_URL esistente
        if grep -q "^DATABASE_URL=" "$env_file"; then
            sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$new_database_url|" "$env_file"
            log_success "DATABASE_URL aggiornato nel file .env per $dev: $new_database_url"
        else
            # Se non esiste, aggiungilo
            echo "DATABASE_URL=$new_database_url" >> "$env_file"
            log_success "DATABASE_URL aggiunto nel file .env per $dev: $new_database_url"
        fi
    else
        log_error "File .env non trovato in $PROJECT_DIR"
        return 1
    fi
}

show_help() {
    echo "🔧 Dev Manager Locale - Suite Clinica"
    echo ""
    echo "Uso: $0 [COMANDO] [SVILUPPATORE]"
    echo ""
    echo "COMANDI FULLSTACK (Backend + Frontend):"
    echo "  fullstack [dev]                          - Avvia sia Backend Flask (5001/5002/5003) che Frontend React (3001/3002/3003)."
    echo "                                             Modalità raccomandata per lo sviluppo ibrido."
    echo "  frontend [dev]                           - Avvia solo il frontend React (Vite) sulla porta dedicata."
    echo ""
    echo "COMANDI BACKEND (Foreground):"
    echo "  debug [dev]                              - Avvia solo Flask con hot-reload (vecchio stile)."
    echo ""
    echo "COMANDI GESTIONE SERVIZIO:"
    echo "  start [dev]                              - Avvia Gunicorn in foreground."
    echo "  stop [dev]                               - Ferma il server."
    echo "  restart [dev]                            - Riavvia il server."
    echo "  status                                   - Mostra lo stato dei servizi."
    echo "  setup-firewall                           - Configura UFW per aprire le porte necessarie."
    echo ""
    echo "COMANDI GESTIONE AMBIENTE:"
    echo "  setup [dev]                              - Setup completo iniziale (dipendenze + db + admin)."
    echo "  clear [dev]                              - Pulisce completamente l'ambiente."
    echo "  recreate [dev]                           - Ricrea completamente l'ambiente da zero."
    echo "  reset-db [dev]                           - Resetta il database (elimina tutto, setup e crea admin)."
    echo ""
    echo "ESEMPI:"
    echo "  $0 fullstack manu                     # Avvia tutto l'ambiente (Flask:5001 + React:3001)."
    echo "  $0 debug manu                         # Sviluppo solo backend."
    echo "  $0 setup-firewall                     # Apre le porte nel firewall."
}

# --- FUNZIONI DI DOCUMENTAZIONE ---
build_docs() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    log_info "Costruzione documentazione MkDocs..."
    cd "$PROJECT_DIR/backend"
    if poetry run mkdocs build -f corposostenibile/blueprints/documentation/mkdocs.yml; then
        log_success "Documentazione costruita con successo in static/"
    else
        log_error "Errore durante la build della documentazione."
        return 1
    fi
}


# --- FUNZIONI DI GESTIONE SERVER ---

# NUOVA FUNZIONE: Avvia il server di sviluppo Flask in foreground
debug_server() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    update_env_database_url "$dev"

    local info=($(get_developer_info "$dev"))
    local port="${info[0]}"
    local db_name="${info[2]}"

    log_info "Avvio server di sviluppo Flask per $dev su http://$DEFAULT_HOST:$port..."
    log_warning "Il server si riavvierà automaticamente alle modifiche del codice."
    log_warning "Premi Ctrl+C per fermare."
    cd "$PROJECT_DIR/backend"

    # Controlla se Gunicorn è attivo sulla stessa porta e avvisa
    local PID_FILE="$PROJECT_DIR/backend/.pid_${dev}"
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" &>/dev/null; then
        log_error "Un server Gunicorn per '$dev' è già attivo! Fermalo prima con '$0 stop $dev'."
        exit 1
    fi

    export DATABASE_URL="postgresql://suite_clinica:password@localhost:$DB_PORT/$db_name"

    # Build docs prima di avviare
    build_docs "$dev"

    # Esegue il comando ufficiale di Flask per lo sviluppo

    # Esegue il comando ufficiale di Flask per lo sviluppo
    poetry run flask run --host="0.0.0.0" --port="$port" --debug
}


# Avvia il server in foreground
start_server() {
    local dev=$1; validate_developer "$dev"; set_project_dir "$dev"
    update_env_database_url "$dev"
    local info=($(get_developer_info "$dev")); local port="${info[0]}"; local db_name="${info[2]}"

    log_info "Avvio server per $dev su $DEFAULT_HOST:$port in foreground..."
    cd "$PROJECT_DIR/backend"

    # Controlla se il server è già in esecuzione sulla porta
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        local existing_pid=$(lsof -ti:$port 2>/dev/null | head -1)
        log_warning "Server per $dev è già in esecuzione sulla porta $port (PID: $existing_pid)."; return
    fi

    export DATABASE_URL="postgresql://suite_clinica:password@localhost:$DB_PORT/$db_name"

    # Avvia il server in foreground con Gunicorn
    poetry run gunicorn --workers 3 --bind "0.0.0.0:$port" "corposostenibile:create_app()"
}

# Ferma il server Gunicorn
stop_server() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local port="${info[0]}"
    log_info "Fermando server per $dev..."

    # Controlla se c'è qualcosa in esecuzione sulla porta
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        log_info "Servizio rilevato sulla porta $port..."

        # Trova il processo sulla porta e terminalo
        local port_pid=$(lsof -ti:$port 2>/dev/null | head -1)
        if [[ -n "$port_pid" ]]; then
            log_info "Processo trovato sulla porta $port (PID: $port_pid)"
            kill "$port_pid"; sleep 1
            if ! kill -0 "$port_pid" &>/dev/null; then
                log_success "Server per $dev (PID: $port_pid) fermato."
            else
                log_error "Impossibile fermare il server per $dev (PID: $port_pid). Tentativo con kill -9."
                kill -9 "$port_pid"; sleep 1
                if ! kill -0 "$port_pid" &>/dev/null; then
                    log_success "Server per $dev (PID: $port_pid) fermato forzatamente."
                else
                    log_error "Impossibile fermare il server per $dev (PID: $port_pid) anche con kill -9."
                    return 1
                fi
            fi
        else
            log_warning "Nessun processo trovato sulla porta $port."
        fi
    else
        log_warning "Server per $dev non in esecuzione."
    fi
}

restart_server() {
    local dev=$1; validate_developer "$dev"
    log_info "Riavvio del server per $dev..."; stop_server "$dev"; sleep 2; start_server "$dev"
}

show_status() {
    log_info "Stato servizi globali:"
    systemctl is-active --quiet postgresql && log_success "PostgreSQL: ATTIVO" || log_error "PostgreSQL: INATTIVO"
    systemctl is-active --quiet redis-server && log_success "Redis: ATTIVO" || log_error "Redis: INATTIVO"
    echo ""
    log_info "Stato ambienti sviluppatori (servizi in background):"
    echo ""
    for dev in "${DEVELOPERS[@]}"; do
        set_project_dir "$dev"
        local info=($(get_developer_info "$dev"))
        local port="${info[0]}"
        local db_name="${info[2]}"
        echo -e "👤 ${YELLOW}$dev${NC}:"

        # Controlla se il servizio è in esecuzione sulla porta
        if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
            local pid=$(lsof -ti:$port 2>/dev/null | head -1)
            log_success "   Server Gunicorn: ATTIVO (PID: $pid)"
            echo "   🌐 URL: http://$DEFAULT_HOST:$port"
        else
            log_warning "   Server Gunicorn: INATTIVO"
        fi
        echo ""
    done
}



# --- ALTRE FUNZIONI (invariate) ---
check_prerequisites() {
    local dev=$1; log_info "Verifico prerequisiti per ${dev:-sistema}..."; set_project_dir "${dev:-manu}"
    command -v poetry &> /dev/null || { log_error "Poetry non trovato."; exit 1; }
    [[ -f "$PROJECT_DIR/backend/pyproject.toml" ]] || { log_error "File pyproject.toml non trovato in $PROJECT_DIR/backend"; exit 1; }
    systemctl is-active --quiet postgresql || sudo systemctl start postgresql
    systemctl is-active --quiet redis-server || sudo systemctl start redis-server
    
    # Crea l'utente PostgreSQL se non esiste
    if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='suite_clinica'" | grep -q 1; then
        log_info "Creazione utente PostgreSQL suite_clinica..."
        sudo -u postgres psql -c "CREATE USER suite_clinica WITH PASSWORD 'password';" || { log_error "Impossibile creare utente PostgreSQL"; exit 1; }
        sudo -u postgres psql -c "ALTER USER suite_clinica CREATEDB;" || { log_error "Impossibile assegnare permessi CREATEDB"; exit 1; }
        log_success "Utente PostgreSQL suite_clinica creato con successo."
    else
        log_info "Utente PostgreSQL suite_clinica già esistente."
    fi
    
    [[ -f "$PROJECT_DIR/backend/.env" ]] || { log_error "File .env non trovato."; exit 1; }
    log_success "Prerequisiti verificati."
}
install_dependencies() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    log_info "Installazione dipendenze per $dev..."
    cd "$PROJECT_DIR/backend"

    # Configura Poetry per evitare problemi di connessione durante install
    export POETRY_NO_CACHE=1
    export POETRY_INSTALLER_READ_TIMEOUT=300
    export POETRY_REQUESTS_TIMEOUT=300
    export POETRY_HTTP_BASIC_PYPI_USERNAME="pypi"
    export POETRY_HTTP_BASIC_PYPI_PASSWORD="pypi"

    # Riprova l'installazione fino a 3 volte in caso di timeout/errori di rete
    local max_attempts=3
    local attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Tentativo $attempt/$max_attempts di installazione dipendenze..."
        if poetry install --no-root --no-cache; then
            log_success "Dipendenze installate con successo."
            return 0
        else
            if [[ $attempt -lt $max_attempts ]]; then
                log_warning "Tentativo $attempt fallito, riprovando tra 10 secondi..."
                sleep 10
            fi
        fi
        ((attempt++))
    done

    log_error "Impossibile installare le dipendenze dopo $max_attempts tentativi."
    log_info "Prova manualmente: cd $PROJECT_DIR/backend && poetry cache clear pypi --all && poetry install --no-root"
    return 1
}
setup_database() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local db_name="${info[2]}"
    log_info "Setup database per $dev..."
    cd "$PROJECT_DIR/backend"
    export DATABASE_URL="postgresql://suite_clinica:password@localhost:$DB_PORT/$db_name"
    if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
        log_info "Creazione database $db_name..."
        sudo -u postgres psql -p "$DB_PORT" -c "CREATE DATABASE $db_name"
        sudo -u postgres psql -p "$DB_PORT" -c "GRANT ALL PRIVILEGES ON DATABASE $db_name TO suite_clinica"
        # Concedi permessi sullo schema public
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "GRANT ALL ON SCHEMA public TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO suite_clinica"
    else
        log_info "Database $db_name esiste già."
        # Assicurati che i permessi siano corretti anche per database esistenti
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "GRANT ALL ON SCHEMA public TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO suite_clinica"
        sudo -u postgres psql -p "$DB_PORT" -d "$db_name" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO suite_clinica"
    fi
    poetry run flask create-db
    log_success "Database $db_name inizializzato."
}
create_admin_user() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local db_name="${info[2]}"
    log_info "Creazione utente admin per $dev..."
    cd "$PROJECT_DIR/backend"
    export DATABASE_URL="postgresql://suite_clinica:password@localhost:$DB_PORT/$db_name"

    # Crea admin direttamente con Python
    poetry run python -c "
from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import User, UserRoleEnum, UserSpecialtyEnum

app = create_app()
with app.app_context():
    # Verifica se l'utente esiste già
    existing_user = User.query.filter_by(email='admin1@suiteclinica.com').first()
    if existing_user:
        print('⚠️  Utente admin già esistente.')
    else:
        # Crea l'utente admin
        admin = User(
            email='admin1@suiteclinica.com',
            first_name='Admin',
            last_name='Sistema',
            role=UserRoleEnum.admin,
            specialty=UserSpecialtyEnum.amministrazione,
            is_admin=True,
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('✅ Utente admin creato con successo!')
"

    log_success "Comando creazione admin eseguito."
    log_info "Credenziali admin: admin@suiteclinica.com / admin123"
}
db_migrate() {
    local dev=$1
    local message="$2"
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local db_name="${info[2]}"
    cd "$PROJECT_DIR/backend"
    if [[ -z "$message" ]]; then
        message="Auto migration $(date '+%Y%m%d_%H%M%S')"
    fi
    export DATABASE_URL="postgresql://suite_clinica:password@localhost:$DB_PORT/$db_name"

    # Pulisci cache Poetry prima della migrazione
    log_info "Pulizia cache Poetry..."
    poetry cache clear pypi --all 2>/dev/null || true

    # Reset del database di migrazioni (alembic_version)
    log_info "Reset della cache migrazioni del database..."
    poetry run flask db stamp head 2>/dev/null || true

    log_info "Creazione migrazione per $dev..."
    poetry run flask db migrate -m "$message"
}
db_upgrade() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local db_name="${info[2]}"
    cd "$PROJECT_DIR/backend"
    export DATABASE_URL="postgresql://suite_clinica:password@localhost:$DB_PORT/$db_name"
    log_info "Applicazione migrazioni per $dev..."
    poetry run flask db upgrade
}
setup_environment() {
    local dev=$1
    validate_developer "$dev"
    log_info "Setup completo per $dev..."
    check_prerequisites "$dev"
    update_env_database_url "$dev"
    install_dependencies "$dev"
    setup_database "$dev"
    create_admin_user "$dev"
    log_success "Setup completato! Usa '$0 debug $dev' per sviluppare o '$0 start $dev' per avviare il servizio."
}




# Pulisce completamente l'ambiente di sviluppo
clear_environment() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local port="${info[0]}"
    local db_port="${info[1]}"
    local db_name="${info[2]}"

    log_warning "⚠️  ATTENZIONE: Questa operazione cancellerà COMPLETAMENTE l'ambiente di $dev!"
    log_warning "   - Database: $db_name"
    log_warning "   - Virtual environment Poetry"
    log_warning "   - Cache Poetry"
    log_warning "   - Log files"
    echo ""
    read -p "Sei sicuro di voler procedere? Digita 'CONFERMA' per continuare: " confirm

    if [[ "$confirm" != "CONFERMA" ]]; then
        log_info "Operazione annullata."
        return 0
    fi

    log_info "Pulizia ambiente per $dev..."

    # 1. Ferma il server se in esecuzione
    log_info "Fermando eventuali server in esecuzione..."
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        stop_server "$dev"
    fi

    # 2. Rimuovi il database
    log_info "Rimozione database $db_name..."
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
        sudo -u postgres psql -p "$db_port" -c "DROP DATABASE IF EXISTS $db_name;"
        log_success "Database $db_name rimosso."
    else
        log_info "Database $db_name non esistente."
    fi

    # 3. Rimuovi virtual environment Poetry
    log_info "Rimozione virtual environment Poetry..."
    cd "$PROJECT_DIR/backend"
    if poetry env list | grep -q "Activated"; then
        poetry env remove --all 2>/dev/null || true
        log_success "Virtual environment rimosso."
    else
        log_info "Nessun virtual environment attivo trovato."
    fi

    # 4. Pulisci cache Poetry
    log_info "Pulizia cache Poetry..."
    rm -rf "/home/$dev/.cache/pypoetry" 2>/dev/null || true
    log_success "Cache Poetry pulita."

    # 5. Rimuovi log files
    log_info "Rimozione log files..."
    rm -rf "$PROJECT_DIR/backend/logs" 2>/dev/null || true
    log_success "Log files rimossi."

    log_success "✨ Ambiente per $dev completamente pulito!"
}

# Ricrea completamente l'ambiente di sviluppo da zero
recreate_environment() {
    local dev=$1
    validate_developer "$dev"

    log_info "🔄 Ricreazione completa ambiente per $dev..."
    echo ""

    # Prima pulisce tutto
    clear_environment "$dev"

    echo ""
    log_info "🚀 Avvio setup completo da zero..."

    # Poi ricrea tutto da capo
    setup_environment "$dev"

    log_success "🎉 Ambiente per $dev ricreato completamente da zero!"
    log_info "Puoi ora utilizzare:"
    log_info "  - '$0 debug $dev' per sviluppo attivo"
    log_info "  - '$0 start $dev' per avviare il servizio in background"
}

# Reset del database: elimina tutto, setup e crea admin
reset_database() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    local info=($(get_developer_info "$dev"))
    local db_name="${info[2]}"
    local db_port="${info[1]}"

    log_warning "⚠️  ATTENZIONE: Questa operazione resetterà COMPLETAMENTE il database di $dev!"
    log_warning "   - Database: $db_name"
    echo ""
    read -p "Sei sicuro di voler procedere? Digita 'RESET' per continuare: " confirm

    if [[ "$confirm" != "RESET" ]]; then
        log_info "Operazione annullata."
        return 0
    fi

    log_info "Reset database per $dev..."

    # 1. Ferma il server se in esecuzione
    local port="${info[0]}"
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        stop_server "$dev"
    fi

    # 2. Rimuovi il database
    log_info "Rimozione database $db_name..."
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
        sudo -u postgres psql -p "$db_port" -c "DROP DATABASE IF EXISTS $db_name;"
        log_success "Database $db_name rimosso."
    else
        log_info "Database $db_name non esistente."
    fi

    # 3. Ricrea il database
    setup_database "$dev"

    # 4. Applica migrazioni
    db_upgrade "$dev"

    # 5. Crea admin
    create_admin_user "$dev"

    log_success "✨ Database per $dev resettato con successo!"
    log_info "Credenziali admin: admin@suiteclinica.com / admin123"
}

# --- GESTIONE FRONTEND (React) ---

check_node() {
    if ! command -v npm &> /dev/null; then
        log_error "Node.js e npm non trovati. Installa Node.js per usare il frontend React."
        exit 1
    fi
}

setup_frontend() {
    log_info "Verifica dipendenze frontend..."
    check_node
    cd "$PROJECT_DIR/corposostenibile-clinica"
    if [ ! -d "node_modules" ]; then
        log_info "Installazione dipendenze React (npm install)..."
        npm install
    fi
}

start_frontend() {
    local dev=$1
    if [[ -z "$dev" ]]; then dev="manu"; fi 
    
    validate_developer "$dev"
    set_project_dir "$dev"
    
    local info=($(get_developer_info "$dev"))
    local fe_port="${info[3]}"
    local be_port="${info[0]}"
    export BACKEND_URL="http://127.0.0.1:$be_port"
    log_info "Configurato backend su $BACKEND_URL"

    log_info "Avvio Frontend React (Vite) per $dev sulla porta $fe_port..."
    setup_frontend
    cd "$PROJECT_DIR/corposostenibile-clinica"
    npm run dev -- --port "$fe_port" --host
}

start_fullstack() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    
    local info=($(get_developer_info "$dev"))
    local be_port="${info[0]}"
    local fe_port="${info[3]}"
    
    log_info "🚀 Avvio modalità FULLSTACK per $dev"
    log_info "   - Backend Flask: http://localhost:$be_port"
    log_info "   - Frontend React: http://localhost:$fe_port"
    
    # Avvia Backend in background e salva PID
    cd "$PROJECT_DIR/backend"
    export FLASK_APP="corposostenibile:create_app()"
    export FLASK_DEBUG=1
    update_env_database_url "$dev"
    
    log_info "Avvio Backend..."
    poetry run flask run --host=0.0.0.0 --port="$be_port" --debug &
    BACKEND_PID=$!
    
    # Trap per chiudere il backend quando si chiude lo script
    cleanup() {
        log_info "🛑 Arresto servizi Fullstack..."
        kill $BACKEND_PID 2>/dev/null || true
        exit 0
    }
    trap cleanup SIGINT SIGTERM EXIT
    
    # Attendi un attimo che il backend parta
    sleep 2
    
    # Avvia Frontend
    start_frontend "$dev"
}

setup_firewall() {
    log_info "🔒 Configurazione Firewall (UFW)..."
    
    # Porte Backend
    for port in "${PORTS_APP[@]}"; do
        log_info "Apertura porta Backend TCP/$port..."
        sudo ufw allow "$port"/tcp
    done

    # Porte Frontend
    for port in "${PORTS_FRONTEND[@]}"; do
        log_info "Apertura porta Frontend TCP/$port..."
        sudo ufw allow "$port"/tcp
    done

    # Database
    log_info "Apertura porta Database TCP/$DB_PORT..."
    sudo ufw allow "$DB_PORT"/tcp

    sudo ufw reload
    log_success "Regole Firewall applicate! (Verifica con 'sudo ufw status')"
}

# --- GESTIONE PM2 (Background Persistente) ---

check_pm2() {
    if ! command -v npx &> /dev/null; then
        log_error "npx non trovato. Installa Node.js."
        exit 1
    fi
}

start_pm2() {
    local dev=$1
    validate_developer "$dev"
    set_project_dir "$dev"
    check_pm2

    local info=($(get_developer_info "$dev"))
    local be_port="${info[0]}"
    local fe_port="${info[3]}"
    local db_name="${info[2]}"

    log_info "🚀 Avvio servizi PM2 per $dev (Backend:$be_port, Frontend:$fe_port)..."

    # Aggiorna .env backend
    cd "$PROJECT_DIR/backend"
    update_env_database_url "$dev"

    # Avvia Backend
    log_info "Avvio Backend Flask..."
    npx pm2 start "poetry run flask run --host=0.0.0.0 --port=$be_port --debug" --name "backend-$dev" --namespace "$dev" --force

    # Avvia Frontend
    log_info "Avvio Frontend React..."
    cd "$PROJECT_DIR/corposostenibile-clinica"
    if [ ! -d "node_modules" ]; then npm install; fi
    npx pm2 start "npm run dev -- --port $fe_port --host" --name "frontend-$dev" --namespace "$dev" --force

    log_success "Servizi avviati in background!"
    log_info "Usa '$0 logs-pm2 $dev' per vedere i log o '$0 stop-pm2 $dev' per fermarli."
}

stop_pm2() {
    local dev=$1
    validate_developer "$dev"
    check_pm2
    
    log_info "Fermando servizi PM2 per $dev..."
    npx pm2 delete "backend-$dev" 2>/dev/null || true
    npx pm2 delete "frontend-$dev" 2>/dev/null || true
    log_success "Servizi fermati."
}

restart_pm2() {
    local dev=$1
    validate_developer "$dev"
    stop_pm2 "$dev"
    start_pm2 "$dev"
}

logs_pm2() {
    local dev=$1
    validate_developer "$dev"
    check_pm2
    log_info "Mostrando log per namespace $dev... (Ctrl+C per uscire)"
    npx pm2 logs --namespace "$dev"
}

status_pm2() {
    check_pm2
    npx pm2 list
}


# --- SCRIPT PRINCIPALE ---
if [[ $# -eq 0 ]]; then show_help; exit 0; fi

COMMAND=$1; shift
case "$COMMAND" in
    debug|start|stop|restart|create-admin|setup|install-deps|db-init|db-upgrade|db-migrate|clear|recreate|reset-db|fullstack|build-docs|start-pm2|stop-pm2|restart-pm2|logs-pm2)
        if [[ -z "$1" ]]; then log_error "Specificare lo sviluppatore per il comando '$COMMAND'."; exit 1; fi
        check_prerequisites "$1"
        case "$COMMAND" in
            debug) debug_server "$1";;
            fullstack) start_fullstack "$1";;
            build-docs) build_docs "$1";;
            start) start_server "$1";;
            stop) stop_server "$1";;
            restart) restart_server "$1";;
            create-admin) create_admin_user "$1";;
            setup) setup_environment "$1";;
            install-deps) install_dependencies "$1";;
            db-init) setup_database "$1";;
            db-upgrade) db_upgrade "$1";;
            db-migrate) db_migrate "$1" "$2";;
            clear) clear_environment "$1";;
            recreate) recreate_environment "$1";;
            reset-db) reset_database "$1";;
            build-docs) build_docs "$1";;
            start-pm2) start_pm2 "$1";;
            stop-pm2) stop_pm2 "$1";;
            restart-pm2) restart_pm2 "$1";;
            logs-pm2) logs_pm2 "$1";;
        esac
        ;;
    status-pm2)
        status_pm2
        ;;
    setup-firewall)
        setup_firewall
        ;;
    frontend)
        # Frontend non richiede argomento dev obbligatorio, ma settiamo project dir se presente
        if [[ -n "$1" ]]; then start_frontend "$1"; else start_frontend "$(whoami)"; fi
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Comando sconosciuto: $COMMAND"; show_help; exit 1
        ;;
esac