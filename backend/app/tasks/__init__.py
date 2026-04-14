"""
Tasks package per FatturaMVP.
Gestisce operazioni asincrone con Celery.
"""
from app.tasks.celery_app import celery_app

# Esporta l'app Celery per uso nei worker
__all__ = ["celery_app"]
