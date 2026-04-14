"""
Configurazione Celery per FatturaMVP.
Broker: Redis
Tasks: SDI, notifiche, AI, sollecito
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Istanza principale Celery
celery_app = Celery(
    "fatturamvp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.sdi_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.escalation_tasks",
    ]
)

# Configurazione generale Celery
celery_app.conf.update(
    # Serializzazione
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="Europe/Rome",
    enable_utc=True,
    
    # Tracking e limiti
    task_track_started=True,
    task_time_limit=300,  # 5 minuti max per task
    task_soft_time_limit=240,  # 4 minuti soft limit
    
    # Prefetch per worker
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Ricicla worker dopo 1000 task
    
    # Retry automatico (default per tutti i task)
    task_default_retry_delay=60,  # 1 minuto tra retry
    task_default_max_retries=3,
    
    # Result expiration
    result_expires=3600,  # Risultati scadono dopo 1 ora
    
    # Serializzazione date
    json_encoder="json.dumps",
    json_decoder="json.loads",
)

# =============================================================================
# CELERY BEAT SCHEDULE - Task periodici
# =============================================================================
celery_app.conf.beat_schedule = {
    # -------------------------------------------------------------------------
    # TASK GIORNALIERI
    # -------------------------------------------------------------------------
    "send-daily-reminder-08-30": {
        "task": "app.tasks.notification_tasks.send_daily_reminder",
        "schedule": crontab(hour=8, minute=30),  # Ogni giorno alle 8:30
    },
    
    "process-escalation-09-00": {
        "task": "app.tasks.escalation_tasks.process_overdue_escalation",
        "schedule": crontab(hour=9, minute=0),  # Ogni giorno alle 9:00
    },
    
    # -------------------------------------------------------------------------
    # TASK ORARI
    # -------------------------------------------------------------------------
    "retry-failed-sdi-hourly": {
        "task": "app.tasks.sdi_tasks.retry_failed_sdi",
        "schedule": crontab(hour="*", minute=0),  # Ogni ora
    },
    
    # -------------------------------------------------------------------------
    # TASK SETTIMANALI / MULTI-ORARI
    # -------------------------------------------------------------------------
    "update-trust-scores-every-6h": {
        "task": "app.tasks.ai_tasks.update_trust_scores",
        "schedule": crontab(hour="*/6", minute=0),  # Ogni 6 ore (0, 6, 12, 18)
    },
    
    # -------------------------------------------------------------------------
    # TASK FREQUENTI (ogni 15 minuti)
    # -------------------------------------------------------------------------
    "generate-cache-solleciti-15min": {
        "task": "app.tasks.ai_tasks.generate_and_cache_sollecito",
        "schedule": crontab(minute="*/15"),  # Ogni 15 minuti
    },
}

# =============================================================================
# CONFIGURAZIONE SDI (Sistema Di Interscambio)
# =============================================================================
celery_app.conf.sdi_config = {
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 120,  # 2 minuti
}

# =============================================================================
# CONFIGURAZIONE NOTIFICHE
# =============================================================================
celery_app.conf.notification_config = {
    "telegram_timeout": 10,
    "email_timeout": 30,
    "max_retries": 3,
}
