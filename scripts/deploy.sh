#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  FatturaMVP - Script di Deploy                              ║
# ║  Build e start di tutti i servizi con Docker Compose        ║
# ╚══════════════════════════════════════════════════════════════╝

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utility
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Banner
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          FATTURAMVP - DEPLOY in produzione                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Verifica Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker non è installato. Installa Docker prima di procedere."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose non è installato."
    exit 1
fi

# Verifica file .env
if [ ! -f .env ]; then
    log_warn "File .env non trovato. Creo da .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log_warn "Compila il file .env con i tuoi valori prima di continuare!"
        exit 1
    else
        log_error ".env.example non trovato. Impossibile procedere."
        exit 1
    fi
fi

# Verifica connettività Docker daemon
if ! docker info &> /dev/null; then
    log_error "Docker daemon non è in esecuzione. Avvialo e riprova."
    exit 1
fi

# Pull immagini base
log_info "Aggiorno immagini Docker..."

# Build immagini custom
log_info "Build immagini backend e frontend..."
docker compose build --parallel

log_success "Build completato!"

# Pulizia immagini dangling
log_info "Pulizia immagini non utilizzate..."
docker image prune -f

# Start servizi
log_info "Avvio servizi..."
docker compose up -d --removeorphans

# Attesa per health check
log_info "Attendo che i servizi siano pronti..."

# Verifica backend
BACKEND_MAX_RETRIES=30
BACKEND_RETRY_COUNT=0
until curl -sf http://localhost:${BACKEND_PORT:-8000}/health > /dev/null 2>&1 || [ $BACKEND_RETRY_COUNT -eq $BACKEND_MAX_RETRIES ]; do
    echo -n "."
    sleep 2
    BACKEND_RETRY_COUNT=$((BACKEND_RETRY_COUNT + 1))
done
echo ""

if [ $BACKEND_RETRY_COUNT -eq $BACKEND_MAX_RETRIES ]; then
    log_error "Backend non raggiungibile dopo 60 secondi. Controlla i log:"
    docker compose logs backend
    exit 1
fi

log_success "Backend online!"

# Verifica frontend
FRONTEND_MAX_RETRIES=15
FRONTEND_RETRY_COUNT=0
until curl -sf http://localhost:${FRONTEND_PORT:-3000}/ > /dev/null 2>&1 || [ $FRONTEND_RETRY_COUNT -eq $FRONTEND_MAX_RETRIES ]; do
    echo -n "."
    sleep 2
    FRONTEND_RETRY_COUNT=$((FRONTEND_RETRY_COUNT + 1))
done
echo ""

if [ $FRONTEND_RETRY_COUNT -eq $FRONTEND_MAX_RETRIES ]; then
    log_warn "Frontend potrebbe non essere pronto. Controlla i log."
else
    log_success "Frontend online!"
fi

# Status finale
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  DEPLOY COMPLETATO!                                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Servizi attivi:"
docker compose ps
echo ""
log_success "Backend:      http://localhost:${BACKEND_PORT:-8000}"
log_success "Frontend:     http://localhost:${FRONTEND_PORT:-3000}"
log_success "API Docs:     http://localhost:${BACKEND_PORT:-8000}/docs"
log_success "Redoc:        http://localhost:${BACKEND_PORT:-8000}/redoc"
echo ""
echo "Per vedere i log:    docker compose logs -f"
echo "Per fermare:         docker compose down"
echo "Per riavviare:      docker compose restart"
echo ""
