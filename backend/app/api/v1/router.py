"""
API v1 Router.
"""
from fastapi import APIRouter
from app.api.v1 import auth, invoices, events, clients, config, onboarding, import_data, feedback, persuasion, sdi, billing, health, reminders, notifications, payments, collection, escalation, integratori

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(invoices.router)
api_router.include_router(events.router)
api_router.include_router(clients.router)
api_router.include_router(config.router)
api_router.include_router(onboarding.router)
api_router.include_router(import_data.router)
api_router.include_router(feedback.router)
api_router.include_router(persuasion.router)  # Payment recovery engine
api_router.include_router(sdi.router)           # SDI - Sistema di Interscambio
api_router.include_router(billing.router)       # Stripe Billing
api_router.include_router(health.router)        # Health check e status workers
api_router.include_router(reminders.router)     # Reminders / Sollecito
api_router.include_router(notifications.router) # Notifications / WhatsApp
api_router.include_router(payments.router)      # Stripe Checkout per fatture
api_router.include_router(collection.router)    # Admin collection management
api_router.include_router(escalation.router)     # Escalation tracker
api_router.include_router(integratori.router)      # Integratori product lookup
