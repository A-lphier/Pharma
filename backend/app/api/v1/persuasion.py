"""
API Endpoints per il motore di Payment Recovery
=============================================

GET  /api/v1/recovery/{invoice_id}
     → Restituisce stage attuale, canale consigliato, messaggio AI

POST /api/v1/recovery/{invoice_id}/send
     → Invia il sollecito (email/PEC/Telegram)

GET  /api/v1/recovery/{invoice_id}/history
     → Storico di tutti i solleciti per questa fattura

GET  /api/v1/recovery/dashboard
     → Dashboard con tutte le fatture da sollecitare

POST /api/v1/recovery/{invoice_id}/stage
     → Aggiorna stage manualmente (human override)
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.persuasion_engine import (
    PaymentRecoveryService,
    EscalationStage,
    CommunicationChannel,
    get_payment_recovery_data,
)

router = APIRouter(prefix="/api/v1/recovery", tags=["recovery"])


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response models
# ─────────────────────────────────────────────────────────────────────────────

class RecoveryStageResponse(BaseModel):
    invoice_id: int
    stage: str
    stage_name: str
    channel: str
    subject: str
    message: str
    psychology_frame: str
    should_send: bool
    should_offer_rateizzazione: bool
    needs_human_review: bool
    legal_record: bool
    days_before_lawyer: Optional[int]
    days_late: int
    trust_score: int
    client_name: str
    client_profile: str


class SendSollecitoRequest(BaseModel):
    message_override: Optional[str] = None  # Se l'utente ha modificato il messaggio
    tone: str = "gentile"  # gentle / equilibrato / fermo


class SendSollecitoResponse(BaseModel):
    success: bool
    channel: str
    sent_at: str
    message_preview: str
    error: Optional[str] = None


class UpdateStageRequest(BaseModel):
    stage: str  # Nome dello stage


class RecoveryDashboardItem(BaseModel):
    invoice_id: int
    invoice_number: str
    client_name: str
    client_profile: str
    amount: float
    due_date: str
    days_late: int
    stage: str
    trust_score: int
    should_escalate: bool


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{invoice_id}", response_model=RecoveryStageResponse)
async def get_recovery_stage(invoice_id: int):
    """
    Restituisce lo stage di escalation, canale consigliato e messaggio
    generato per una fattura.

    Questo è il cuore della UX: quando l'utente clicca su una fattura,
    vede immediatamente:
    - In che stage siamo
    - Quale canale usare
    - Cosa dice il messaggio (generato da AI)
    - Se serve intervento umano
    """
    # TODO: Recupera fattura da DB
    # invoice = await db.get_invoice(invoice_id)
    # client = await db.get_client(invoice.client_id)

    # Per ora mock
    mock_data = await get_payment_recovery_data(
        client_name="Mario Rossi",
        invoice_number="FT-2026-001",
        invoice_amount=1500.00,
        due_date=date(2026, 3, 10),
        days_late=12,
        trust_score=65,
        client_profile="high_value_long_term",
    )

    return RecoveryStageResponse(
        invoice_id=invoice_id,
        stage=mock_data["stage"].value,
        stage_name=mock_data["stage_name"],
        channel=mock_data["channel"].value,
        subject=mock_data["subject"],
        message=mock_data["message_ai"],
        psychology_frame=mock_data["psychology_frame"],
        should_send=mock_data["should_send"],
        should_offer_rateizzazione=mock_data["should_offer_rateizzazione"],
        needs_human_review=mock_data["needs_human_review"],
        legal_record=mock_data["legal_record"],
        days_before_lawyer=mock_data["days_before_lawyer"],
        days_late=12,
        trust_score=65,
        client_name="Mario Rossi",
        client_profile="high_value_long_term",
    )


@router.post("/{invoice_id}/send", response_model=SendSollecitoResponse)
async def send_sollecito(invoice_id: int, request: SendSollecitoRequest):
    """
    Invia il sollecito via il canale appropriato.

    Steps:
    1. Recupera dati fattura e cliente
    2. Genera/Aggiorna messaggio (se modified)
    3. Invia via canale appropriato (email/PEC/Telegram)
    4. Logga in sollecito_history
    5. Aggiorna stage se necessario
    6. Notifica utente del successo/fallimento
    """
    # TODO: Implementa invio reale

    # Mock response
    return SendSollecitoResponse(
        success=True,
        channel="email",
        sent_at="2026-03-27T18:45:00Z",
        message_preview="Gentile Mario Rossi, in riferimento alla fattura FT-2026-001...",
        error=None,
    )


@router.get("/{invoice_id}/history")
async def get_sollecito_history(invoice_id: int):
    """
    Restituisce lo storico di tutti i solleciti inviati per questa fattura.
    Ogni entry contiene: data, canale, messaggio, stage, utente che ha inviato.
    """
    # TODO: Recupera da DB
    return {
        "invoice_id": invoice_id,
        "history": [
            {
                "id": 1,
                "sent_at": "2026-03-20T10:30:00Z",
                "channel": "email",
                "stage": "sollecito_gentle",
                "message": "Gentile Mario Rossi, desideriamo ricordarle che...",
                "sent_by": "system",
            },
            {
                "id": 2,
                "sent_at": "2026-03-27T09:00:00Z",
                "channel": "email",
                "stage": "sollecito_formale",
                "message": "Gentile Mario Rossi, nonostante il nostro precedente sollecito...",
                "sent_by": "user",
            },
        ],
    }


@router.get("/dashboard")
async def get_recovery_dashboard(
    days_filter: Optional[int] = None,  # Solo fatture con >N giorni di ritardo
    stage_filter: Optional[str] = None,  # Solo un specifico stage
):
    """
    Dashboard con tutte le fatture che necessitano di sollecito.

    Raggruppate per stage di escalation, ordinate per urgenza.
    """
    # TODO: Query reale su DB
    mock_items = [
        {
            "invoice_id": 1,
            "invoice_number": "FT-2026-001",
            "client_name": "Mario Rossi",
            "client_profile": "high_value_long_term",
            "amount": 1500.00,
            "due_date": "2026-03-10",
            "days_late": 17,
            "stage": "sollecito_formale",
            "trust_score": 65,
            "should_escalate": True,
        },
        {
            "invoice_id": 2,
            "invoice_number": "FT-2026-002",
            "client_name": "Laura Verdi",
            "client_profile": "new_client",
            "amount": 850.00,
            "due_date": "2026-03-15",
            "days_late": 12,
            "stage": "sollecito_gentle",
            "trust_score": 72,
            "should_escalate": True,
        },
        {
            "invoice_id": 3,
            "invoice_number": "FT-2026-003",
            "client_name": "Giovanni Bianchi",
            "client_profile": "repeat_delinquent",
            "amount": 3200.00,
            "due_date": "2026-02-15",
            "days_late": 40,
            "stage": "sollecito_deciso",
            "trust_score": 15,
            "should_escalate": True,
        },
    ]

    # Filtra se richiesto
    items = mock_items
    if days_filter:
        items = [i for i in items if i["days_late"] >= days_filter]
    if stage_filter:
        items = [i for i in items if i["stage"] == stage_filter]

    return {
        "total": len(items),
        "by_stage": {
            "sollecito_gentle": len([i for i in items if i["stage"] == "sollecito_gentle"]),
            "sollecito_formale": len([i for i in items if i["stage"] == "sollecito_formale"]),
            "sollecito_deciso": len([i for i in items if i["stage"] == "sollecito_deciso"]),
            "pre_avvocato": len([i for i in items if i["stage"] == "pre_avvocato"]),
        },
        "items": items,
    }


@router.post("/{invoice_id}/stage")
async def update_stage(invoice_id: int, request: UpdateStageRequest):
    """
    Override manuale dello stage di escalation.
    L'utente puo forzare uno stage diverso da quello calcolato automaticamente.

    Uso tipico: "So che questo cliente sta per pagare, skipami lo stage"
    oppure "Questo cliente è in dispute, sospendi escalation"
    """
    # TODO: Salva in DB
    return {
        "invoice_id": invoice_id,
        "new_stage": request.stage,
        "updated_at": "2026-03-27T18:45:00Z",
        "updated_by": "user",
    }
