#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  FatturaMVP - Health Check                                 ║
# ║  Verifica lo stato di salute di tutti i servizi            ║
# ╚══════════════════════════════════════════════════════════════╝

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funzioni
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

# Banner
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          FATTURAMVP - HEALTH CHECK                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Conteggio errori
ERRORS=0

# ──────────────────────────────────────────────
# Verifica Docker Compose
# ──────────────────────────────────────────────
log_info "Verifica Docker Compose..."

if ! docker compose ps &> /dev/null; then
    log_error "Docker Compose non è in esecuzione o non è disponibile."
    exit 1
fi

# ──────────────────────────────────────────────
# Verifica PostgreSQL
# ──────────────────────────────────────────────
log_info "Verifica PostgreSQL 16..."

if docker compose exec -T db pg_isready -U ${POSTGRES_USER:-fattura} -d ${POSTGRES_DB:-fattura} &> /dev/null; then
    log_success "PostgreSQL - Connessione OK"
else
    log_error "PostgreSQL - Connessione FALLITA"
    ERRORS=$((ERRORS + 1))
fi

# ──────────────────────────────────────────────
# Verifica Redis
# ──────────────────────────────────────────────
log_info "Verifica Redis 7..."

if docker compose exec -T redis redis-cli ping &> /dev/null; then
    log_success "Redis - Connessione OK"
else
    log_error "Redis - Connessione FALLITA"
    ERRORS=$((ERRORS + 1))
fi

# ──────────────────────────────────────────────
# Verifica Backend
# ──────────────────────────────────────────────
log_info "Verifica Backend (FastAPI)..."

BACKEND_URL="http://localhost:${BACKEND_PORT:-8000}/health"
if curl -sf "$BACKEND_URL" &> /dev/null; then
    log_success "Backend - Health check OK"
else
    log_error "Backend - Health check FALLITO"
    ERRORS=$((ERRORS + 1))
fi

# ──────────────────────────────────────────────
# Verifica Celery Worker
# ──────────────────────────────────────────────
log_info "Verifica Celery Worker..."

CELERY_STATUS=$(docker compose exec -T celery_worker celery -A app.celery_app inspect ping 2>&1 || echo "FAIL")
if echo "$CELERY_STATUS" | grep -q "pong"; then
    log_success "Celery Worker - Attivo"
else
    log_warn "Celery Worker - Potrebbe non essere attivo (verifica manualmente)"
fi

# ──────────────────────────────────────────────
# Verifica Celery Beat
# ──────────────────────────────────────────────
log_info "Verifica Celery Beat..."

BEAT_RUNNING=$(docker compose ps --filter "name=fattura_celery_beat" --format "{{.State}}" 2>/dev/null || echo "unknown")
if [ "$BEAT_RUNNING" = "running" ]; then
    log_success "Celery Beat - Attivo"
else
    log_warn "Celery Beat - Non in esecuzione"
fi

# ──────────────────────────────────────────────
# Verifica Frontend
# ──────────────────────────────────────────────
log_info "Verifica Frontend (React/Nginx)..."

FRONTEND_URL="http://localhost:${FRONTEND_PORT:-3000}/"
if curl -sf "$FRONTEND_URL" &> /dev/null; then
    log_success "Frontend - Risponde OK"
else
    log_error "Frontend - Risposta FALLITA"
    ERRORS=$((ERRORS + 1))
fi

# ──────────────────────────────────────────────
# Verifica spazio disco
# ──────────────────────────────────────────────
log_info "Verifica spazio disco..."

DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    log_success "Disco - Utilizzo $DISK_USAGE% (OK)"
elif [ "$DISK_USAGE" -lt 90 ]; then
    log_warn "Disco - Utilizzo $DISK_USAGE% (Attenzione)"
else
    log_error "Disco - Utilizzo $DISK_USAGE% (Critico!)"
    ERRORS=$((ERRORS + 1))
fi

# ──────────────────────────────────────────────
# Verifica volumi
# ──────────────────────────────────────────────
log_info "Verifica volumi persistenti..."

POSTGRES_VOLUME=$(docker volume ls -q | grep -E "fatturamvp_postgres_data|postgres_data" | head -1)
REDIS_VOLUME=$(docker volume ls -q | grep -E "fatturamvp_redis_data|redis_data" | head -1)

if [ -n "$POSTGRES_VOLUME" ]; then
    log_success "Volume PostgreSQL - Presente"
else
    log_warn "Volume PostgreSQL - Non trovato (dati non persistenti)"
fi

if [ -n "$REDIS_VOLUME" ]; then
    log_success "Volume Redis - Presente"
else
    log_warn "Volume Redis - Non trovato (dati non persistenti)"
fi

# ──────────────────────────────────────────────
# Riepilogo
# ──────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  RIEPILOGO STATUS                                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
docker compose ps
echo ""

if [ $ERRORS -eq 0 ]; then
    log_success "Tutti i servizi sono operativi!"
    exit 0
else
    log_error "Trovati $ERRORS errore/i. Controlla i log:"
    echo ""
    echo "  docker compose logs backend"
    echo "  docker compose logs celery_worker"
    echo ""
    exit 1
fi
