#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  FatturaMVP - Backup Database                              ║
# ║  Esegue dump del database PostgreSQL con compressione       ║
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
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configurazione
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${POSTGRES_DB:-fattura}"
DB_USER="${POSTGRES_USER:-fattura}"
BACKUP_NAME="fattura_backup_${TIMESTAMP}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Banner
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          FATTURAMVP - BACKUP DATABASE                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Crea directory backup se non esiste
mkdir -p "$BACKUP_DIR"

# Verifica che il container db sia in esecuzione
if ! docker compose ps db | grep -q "Up"; then
    log_error "Il container PostgreSQL non è in esecuzione!"
    exit 1
fi

# Calcola dimensione DB prima del backup
log_info "Dimensione database attuale..."
DB_SIZE=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null | xargs || echo "Sconosciuta")
log_info "Dimensione DB: $DB_SIZE"

# Esegue backup
log_info "Eseguo dump del database..."

BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"

# Dump con compressione
if docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_PATH"; then
    log_success "Backup completato!"
else
    log_error "Backup FALLITO!"
    exit 1
fi

# Verifica dimensione backup
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
log_success "Backup salvato: $BACKUP_PATH ($BACKUP_SIZE)"

# Verifica integrità backup
log_info "Verifico integrità backup..."
if zcat "$BACKUP_PATH" > /dev/null 2>&1; then
    log_success "Integrità backup verificata!"
else
    log_error "Backup corrotto! Verificare manualmente."
    exit 1
fi

# Backup dei file upload (se esistono)
log_info "Backup file uploads..."
if [ -d "./backend/data/uploads" ] && [ -n "$(ls -A ./backend/data/uploads 2>/dev/null)" ]; then
    UPLOADS_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}_uploads.tar.gz"
    tar -czf "$UPLOADS_BACKUP" -C ./backend/data uploads 2>/dev/null || true
    if [ -f "$UPLOADS_BACKUP" ]; then
        UPLOADS_SIZE=$(du -h "$UPLOADS_BACKUP" | cut -f1)
        log_success "Uploads backup: $UPLOADS_SIZE"
    fi
else
    log_info "Nessun file upload da backuppare"
fi

# Backup config (senza secrets)
log_info "Backup configurazione (senza secrets)..."
CONFIG_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz"
tar -czf "$CONFIG_BACKUP" \
    docker-compose.yml \
    .env.example \
    backend/requirements.txt \
    frontend/package.json \
    nginx/nginx.conf \
    2>/dev/null || true

if [ -f "$CONFIG_BACKUP" ]; then
    log_success "Config backup completato"
fi

# Pulizia vecchi backup
log_info "Pulizia backup più vecchi di $RETENTION_DAYS giorni..."
find "$BACKUP_DIR" -name "fattura_backup_*" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
CLEANED=$(find "$BACKUP_DIR" -name "fattura_backup_*" -type f -mtime +$RETENTION_DAYS 2>/dev/null | wc -l)
if [ "$CLEANED" -gt 0 ]; then
    log_info "Backup vecchi rimossi: $CLEANED"
fi

# Lista backup recenti
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  BACKUP RECENTI                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
ls -lh "$BACKUP_DIR" | tail -10

echo ""
log_success "Operazione completata!"

# Istruzioni restore
echo ""
echo "Per ripristinare un backup:"
echo "  gunzip < $BACKUP_PATH | docker compose exec -T db psql -U $DB_USER -d $DB_NAME"
echo ""
