# FatturaMVP — README per lo Sviluppatore

## Panoramica
Software di fatturazione elettronica italiana con AI per solleciti di pagamento. Target: professionisti e PMI italiane. Canale: commercialisti come buyer.

## Stack Tecnologico
- **Frontend**: React 18 + TypeScript + TailwindCSS
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL 16
- **Task Queue**: Celery + Redis
- **AI**: MiniMax M2.7 (per solleciti)
- **Email**: Brevo SMTP (gratis <300/giorno)
- **SDI**: OpenAPI SDI (€0.022/fattura)
- **Hosting**: Hetzner (€4-6/mese)

## Quick Start

```bash
# Setup ambiente
cp .env.example .env
# Compila .env con le tue API keys

# Docker (consigliato)
docker-compose up -d postgres redis

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (altro terminale)
cd frontend
npm install
npm run dev
```

## Struttura Progetto

```
fattura-mvp-modern/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoint REST
│   │   │   ├── sdi.py       # Invio SDI
│   │   │   ├── billing.py   # Stripe
│   │   │   └── persuasion.py # Solleciti AI
│   │   ├── models/          # SQLAlchemy models
│   │   ├── services/        # Logica di business
│   │   │   ├── ai_message_service.py  # Generazione solleciti AI
│   │   │   ├── persuasion_engine.py # Motore escalation
│   │   │   ├── sdi_service.py       # Wrapper OpenAPI SDI
│   │   │   ├── email_service.py     # Brevo SMTP
│   │   │   ├── telegram_service.py  # Notifiche Telegram
│   │   │   └── pdf_service.py       # Generazione PDF
│   │   └── tasks/         # Celery tasks
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/        # Pagine (dashboard, scadenziario, etc.)
│   │   ├── components/    # Componenti riutilizzabili
│   │   └── lib/          # API client, utilities
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## API Endpoints Principali

### Fatture
- `GET /api/v1/invoices` — lista fatture
- `POST /api/v1/invoices` — crea fattura
- `GET /api/v1/invoices/{id}` — dettaglio fattura
- `GET /api/v1/invoices/{id}/pdf` — genera PDF

### Clienti
- `GET /api/v1/clients` — lista clienti
- `POST /api/v1/clients` — crea cliente

### SDI
- `POST /api/v1/sdi/send` — invia fattura a SDI
- `GET /api/v1/sdi/status/{id}` — stato notifica

### Solleciti
- `GET /api/v1/recovery/{invoice_id}` — genera sollecito AI
- `POST /api/v1/recovery/{invoice_id}/send` — invia sollecito

### Billing
- `POST /api/v1/billing/checkout` — avvia Stripe checkout
- `GET /api/v1/billing/status` — stato subscription

## Feature Principali Implementate

1. **Wizard fattura 4 step** — cliente → dettagli → pagamento → conferma
2. **Scadenziario** — cards color-coded (rosso/giallo/verde)
3. **Sollecito AI** — 7 stadi escalation, 5 frame psicologici
4. **Trust Score** — scoring predittivo per cliente
5. **Landing page** — con ROI calculator e pricing
6. **PDF generation** — con ReportLab

## API Keys Necessarie

Nel file `.env`:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/fatturamvp
REDIS_URL=redis://localhost:6379
SECRET_KEY=change_me_in_production
OPENAPI_SDI_KEY=your_openapi_key
BREVO_API_KEY=your_brevo_key
TELEGRAM_BOT_TOKEN=your_telegram_token
STRIPE_API_KEY=your_stripe_key
MINIMAX_API_KEY=already_configured
```

## Deployment

```bash
# Build produzione
docker-compose build

# Deploy
./scripts/deploy.sh

# Health check
./scripts/healthcheck.sh

# Backup giornaliero
./scripts/backup.sh
```

## Contatti e Note

Per domande sul progetto: refer to `memory/FATTURA-MVP-SYNTHESIS-FINAL.md`

Piano di sviluppo: `memory/FATTURA-MVP-CLAUDIO-TASKS.md`

Stato implementazione: `memory/implementation-state.json`
