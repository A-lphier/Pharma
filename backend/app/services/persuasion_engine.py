"""
FatturaMVP — Persuasion & Payment Recovery Engine
================================================

Motore intelligente di recupero crediti che scala la comunicazione
dal promemoria gentile fino al pre-avvocato.

La filosofia: il 90% dei ritardi non è cattiveria — è psicologia.
Il sistema sollecita AL POSTO TUO, con il tono giusto, al momento giusto.

API KEYS NECESSARIE (da configurare in .env):
- OPENAPI_SDI_KEY: per invio SDI (gia nel piano)
- BREVO_API_KEY: per email (placeholder, Brevo free tier)
- TELEGRAM_BOT_TOKEN: per notifiche (gia configurato)

STRUTTURA ESCALATION:
Step 0: Promemoria pre-scadenza (3gg prima)
Step 1: Promemoria giorno scadenza
Step 2: Primo sollecito (7gg ritardo)
Step 3: Sollecito formale (14-21gg)
Step 4: Sollecito deciso (30gg)
Step 5: Pre-avvocato (45-60gg)
Step 6: Avvocato (60-90gg) — passaggio a manuale
"""

import logging
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EscalationStage(Enum):
    """Stadi di escalation del sollecito."""
    NONE = "none"
    REMINDER_BEFORE = "reminder_before"       # 3gg prima scadenza
    REMINDER_DUE = "reminder_due"             # Giorno scadenza
    SOLLECITO_GENTLE = "sollecito_gentile"    # 7gg ritardo
    SOLLECITO_FORMALE = "sollecito_formale"   # 14-21gg ritardo
    SOLLECITO_DECISO = "sollecito_deciso"     # 30gg ritardo
    PRE_AVVOCATO = "pre_avvocato"             # 45-60gg ritardo
    AVVOCATO = "avvocato"                     # 60-90gg → manuale


class CommunicationChannel(Enum):
    """Canali di comunicazione disponibili."""
    EMAIL = "email"
    PEC = "pec"
    TELEGRAM = "telegram"
    SMS = "sms"
    RACCOMANDATA = "raccomandata"


class PsychologicalFrame(Enum):
    """Frame psicologici per i messaggi."""
    RECIPROCITY = "reciprocity"       # "Abbiamo sempre rispettato i nostri impegni..."
    PEER_PRESSURE = "peer_pressure"  # "Aziende come la tua di solito..."
    EMPATHY = "empathy"             # "Capiamo che possiate avere difficolta..."
    CONSEQUENCE = "consequence"       # "Dovremo attivare procedure di recupero..."
    URGENCY = "urgency"             # "Hai ancora 5 giorni per..."
    FRIENDLY = "friendly"           # Promemoria amichevole, no accusa


# ─────────────────────────────────────────────────────────────────────────────
# Configurazione per cliente (dal suo profilo)
# ─────────────────────────────────────────────────────────────────────────────

CLIENT_PROFILES = {
    "high_value_long_term": {
        "description": "Cliente strategico, valore alto, rapporto lungo",
        "escalation_slower": True,       # Più step intermedi
        "rateizzazione_offered": True,   # Offri sempre rateizzazione
        "direct_contact_owner": True,     # Coinvolgi titolare prima
        "psychology_primary": PsychologicalFrame.RECIPROCITY,
    },
    "new_client": {
        "description": "Nuovo cliente, ancora non fidato",
        "escalation_slower": False,
        "rateizzazione_offered": True,
        "direct_contact_owner": False,
        "psychology_primary": PsychologicalFrame.FRIENDLY,
    },
    "repeat_delinquent": {
        "description": "Cliente che ritarda spesso",
        "escalation_faster": True,       # Salta gli step gentili
        "rateizzazione_offered": False,  # Non offrire subito
        "direct_contact_owner": True,
        "psychology_primary": PsychologicalFrame.CONSEQUENCE,
    },
    "financial_difficulties": {
        "description": "Cliente in difficolta finanziaria",
        "escalation_slower": True,
        "rateizzazione_offered": True,
        "direct_contact_owner": False,
        "psychology_primary": PsychologicalFrame.EMPATHY,
    },
    "disputed": {
        "description": "Cliente che contesta la fattura",
        "escalation_paused": True,       # SOSPENDI escalation
        "rateizzazione_offered": False,
        "direct_contact_owner": False,
        "psychology_primary": PsychologicalFrame.FRIENDLY,
        "action_required": "human_review",  # Passa a operatore
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder per ogni stage
# ─────────────────────────────────────────────────────────────────────────────

STAGE_PROMPTS = {
    EscalationStage.REMINDER_BEFORE: {
        "tone": "gentile",
        "subject": "Promemoria: fattura {invoice_number} in scadenza tra 3 giorni",
        "psychology_frames": [PsychologicalFrame.FRIENDLY],
        "days_target": -3,  # 3 giorni PRIMA della scadenza
        "channel_preference": [CommunicationChannel.EMAIL],
    },
    EscalationStage.REMINDER_DUE: {
        "tone": "gentile",
        "subject": "Fattura {invoice_number} in scadenza oggi",
        "psychology_frames": [PsychologicalFrame.FRIENDLY, PsychologicalFrame.RECIPROCITY],
        "days_target": 0,
        "channel_preference": [CommunicationChannel.EMAIL, CommunicationChannel.TELEGRAM],
    },
    EscalationStage.SOLLECITO_GENTLE: {
        "tone": "gentile",
        "subject": "Gentile promemoria: fattura {invoice_number} scaduta",
        "psychology_frames": [PsychologicalFrame.RECIPROCITY, PsychologicalFrame.FRIENDLY],
        "days_target": 7,
        "channel_preference": [CommunicationChannel.EMAIL, CommunicationChannel.TELEGRAM],
        "offer_rateizzazione": True,
    },
    EscalationStage.SOLLECITO_FORMALE: {
        "tone": "equilibrato",
        "subject": "Sollecito formale: fattura {invoice_number} scaduta da {days_late} giorni",
        "psychology_frames": [PsychologicalFrame.RECIPROCITY, PsychologicalFrame.CONSEQUENCE],
        "days_target": 14,
        "channel_preference": [CommunicationChannel.PEC, CommunicationChannel.EMAIL],
        "offer_rateizzazione": True,
        "create_legal_record": True,  # Predispongo documentazione per eventuale azione legale
    },
    EscalationStage.SOLLECITO_DECISO: {
        "tone": "fermo",
        "subject": "URGENTE: sollecito pagamento fattura {invoice_number}",
        "psychology_frames": [PsychologicalFrame.CONSEQUENCE, PsychologicalFrame.URGENCY],
        "days_target": 30,
        "channel_preference": [CommunicationChannel.PEC, CommunicationChannel.EMAIL],
        "offer_rateizzazione": False,  # Ormai è tardi
        "create_legal_record": True,
        "mention_interest": True,  # Diritto a interessi di mora
    },
    EscalationStage.PRE_AVVOCATO: {
        "tone": "fermo",
        "subject": "FINALE: {days_left} giorni per evitare azione legale - fattura {invoice_number}",
        "psychology_frames": [PsychologicalFrame.CONSEQUENCE, PsychologicalFrame.URGENCY, PsychologicalFrame.PEER_PRESSURE],
        "days_target": 45,
        "channel_preference": [CommunicationChannel.PEC, CommunicationChannel.RACCOMANDATA],
        "offer_rateizzazione": False,
        "create_legal_record": True,
        "mention_legal_costs": True,  # Costi legali a carico del debitore
        "days_before_lawyer": 5,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Motore principale
# ─────────────────────────────────────────────────────────────────────────────

class PaymentRecoveryEngine:
    """
    Motore di recupero crediti intelligente.

    Uso:
        engine = PaymentRecoveryEngine(
            trust_score=65,
            client_profile="high_value_long_term",
            is_new_client=False,
        )

        stage = engine.get_current_stage(days_late=12)
        channel = engine.get_optimal_channel(client_has_pec=True, client_has_telegram=True)
        frame = engine.get_psychological_frame()

        result = await engine.generate_sollecito(
            client_name="Mario Rossi",
            invoice_number="FT-2026-001",
            invoice_amount=1500.00,
            due_date=date(2026, 3, 10),
            days_late=12,
        )
    """

    def __init__(
        self,
        trust_score: int = 60,
        client_profile: str = "new_client",
        is_new_client: bool = False,
        has_telegram: bool = False,
        has_pec: bool = False,
        has_whatsapp: bool = False,
    ):
        self.trust_score = trust_score
        self.client_profile = client_profile
        self.is_new_client = is_new_client
        self.has_telegram = has_telegram
        self.has_pec = has_pec
        self.has_whatsapp = has_whatsapp

        # Carica profilo cliente
        profile_config = CLIENT_PROFILES.get(client_profile, CLIENT_PROFILES["new_client"])
        self.escalation_slower = profile_config.get("escalation_slower", False)
        self.escalation_faster = profile_config.get("escalation_faster", False)
        self.rateizzazione_offered = profile_config.get("rateizzazione_offered", True)
        self.psychology_primary = profile_config.get("psychology_primary", PsychologicalFrame.FRIENDLY)

    def get_current_stage(self, days_late: int, stage_history: list = None) -> EscalationStage:
        """
        Determina lo stage di escalation basato sui giorni di ritardo.

        Args:
            days_late: giorni di ritardo dalla scadenza
            stage_history: lista degli stage gia attraversati

        Returns:
            EscalationStage appropriato
        """
        if self.escalation_faster:
            # Clienti recidivi: escalation piu rapida
            if days_late >= 45:
                return EscalationStage.PRE_AVVOCATO
            elif days_late >= 21:
                return EscalationStage.SOLLECITO_DECISO
            elif days_late >= 7:
                return EscalationStage.SOLLECITO_FORMALE
            elif days_late >= 3:
                return EscalationStage.SOLLECITO_GENTLE
            elif days_late >= 0:
                return EscalationStage.REMINDER_DUE
            else:
                return EscalationStage.REMINDER_BEFORE

        elif self.escalation_slower:
            # Clienti di valore: escalation piu lenta
            if days_late >= 60:
                return EscalationStage.PRE_AVVOCATO
            elif days_late >= 45:
                return EscalationStage.SOLLECITO_DECISO
            elif days_late >= 30:
                return EscalationStage.SOLLECITO_FORMALE
            elif days_late >= 14:
                return EscalationStage.SOLLECITO_GENTLE
            elif days_late >= 3:
                return EscalationStage.REMINDER_DUE
            else:
                return EscalationStage.REMINDER_BEFORE

        else:
            # Comportamento standard
            if days_late >= 60:
                return EscalationStage.AVVOCATO
            elif days_late >= 45:
                return EscalationStage.PRE_AVVOCATO
            elif days_late >= 30:
                return EscalationStage.SOLLECITO_DECISO
            elif days_late >= 14:
                return EscalationStage.SOLLECITO_FORMALE
            elif days_late >= 7:
                return EscalationStage.SOLLECITO_GENTLE
            elif days_late >= 0:
                return EscalationStage.REMINDER_DUE
            else:
                return EscalationStage.REMINDER_BEFORE

    def get_optimal_channel(self, days_late: int) -> CommunicationChannel:
        """
        Sceglie il canale ottimale per questo cliente a questo stadio.

        La logica:
        - PEC ha valore legale documentabile (fondamentale dopo 14gg)
        - Telegram ha apertura 80-98% ma nessun valore legale
        - Email è il fallback standard
        - SMS è per emergenze (costo)
        - Raccomandata A/R è per comunicazioni legali (costo +3gg)
        """
        if days_late >= 45 and self.has_pec:
            return CommunicationChannel.PEC
        elif days_late >= 30 and self.has_pec:
            return CommunicationChannel.PEC
        elif days_late >= 14 and self.has_pec:
            return CommunicationChannel.PEC
        elif days_late >= 7 and self.has_telegram:
            return CommunicationChannel.TELEGRAM
        elif self.has_whatsapp:
            return CommunicationChannel.TELEGRAM  # WhatsApp via Telegram bridge
        elif self.has_pec:
            return CommunicationChannel.PEC
        else:
            return CommunicationChannel.EMAIL

    def get_psychological_frame(self, stage: EscalationStage) -> PsychologicalFrame:
        """Restituisce il frame psicologico appropriato per questo stadio."""
        stage_config = STAGE_PROMPTS.get(stage, STAGE_PROMPTS[EscalationStage.SOLLECITO_GENTLE])
        return stage_config["psychology_frames"][0]

    def get_stage_config(self, stage: EscalationStage) -> dict:
        """Restituisce la configurazione completa per questo stadio."""
        return STAGE_PROMPTS.get(stage, STAGE_PROMPTS[EscalationStage.SOLLECITO_GENTLE])

    def should_offer_rateizzazione(self, stage: EscalationStage) -> bool:
        """Decide se offrire rateizzazione a questo stadio."""
        if stage.value in ["pre_avvocato", "avvocato"]:
            return False
        return self.rateizzazione_offered

    def should_create_legal_record(self, stage: EscalationStage) -> bool:
        """Se True, stiamo costruendo il presupposto per azione legale."""
        stage_config = self.get_stage_config(stage)
        return stage_config.get("create_legal_record", False)

    def get_days_before_lawyer(self, stage: EscalationStage) -> Optional[int]:
        """Giorni rimanenti prima di passare all'avvocato."""
        if stage == EscalationStage.PRE_AVVOCATO:
            return STAGE_PROMPTS[stage].get("days_before_lawyer", 5)
        return None

    def get_subject(
        self,
        stage: EscalationStage,
        invoice_number: str,
        days_late: int = 0,
    ) -> str:
        """Genera l'oggetto email/messaggio appropriato."""
        template = self.get_stage_config(stage)["subject"]
        return template.format(
            invoice_number=invoice_number,
            days_late=days_late,
            days_left=self.get_days_before_lawyer(stage) or 5,
        )

    def needs_human_review(self) -> bool:
        """True se questa situazione richiede intervento umano."""
        return self.client_profile == "disputed"


# ─────────────────────────────────────────────────────────────────────────────
# Service per integrazione AI
# ─────────────────────────────────────────────────────────────────────────────

class PaymentRecoveryService:
    """
    Service principale che combina il motore di escalation con l'AI
    per generare solleciti personalizzati.

    Usage:
        service = PaymentRecoveryService()
        result = await service.get_sollecito_data(
            client=client_obj,
            invoice=invoice_obj,
        )
        # result contiene: stage, canale, messaggio AI, subject
    """

    def __init__(self):
        # TODO: Inietta AI service quando disponibile
        # from app.services.ai_message_service import AIMessageService
        # self.ai_service = AIMessageService()
        pass

    async def get_sollecito_data(
        self,
        client_name: str,
        client_vat: str,
        client_profile: str,
        trust_score: int,
        invoice_number: str,
        invoice_amount: float,
        due_date: date,
        paid_date: Optional[date],
        days_late: int,
        stage_history: list,
        has_telegram: bool,
        has_pec: bool,
        has_whatsapp: bool,
        business_name: str = "la nostra azienda",
    ) -> dict:
        """
        Restituisce tutti i dati necessari per inviare un sollecito.

        Returns:
            {
                "stage": EscalationStage,
                "channel": CommunicationChannel,
                "subject": str,
                "message_ai": str,  # Messaggio generato da AI
                "should_send": bool,
                "should_offer_rateizzazione": bool,
                "needs_human_review": bool,
                "legal_record": bool,
                "days_before_lawyer": int | None,
            }
        """
        # Calcola stage attuale
        engine = PaymentRecoveryEngine(
            trust_score=trust_score,
            client_profile=client_profile,
            has_telegram=has_telegram,
            has_pec=has_pec,
            has_whatsapp=has_whatsapp,
        )

        stage = engine.get_current_stage(days_late, stage_history)
        channel = engine.get_optimal_channel(days_late)
        stage_config = engine.get_stage_config(stage)
        psychology_frame = engine.get_psychological_frame(stage)

        # Costruisci prompt per AI
        prompt_data = self._build_ai_prompt(
            engine=engine,
            stage=stage,
            channel=channel,
            psychology_frame=psychology_frame,
            client_name=client_name,
            invoice_number=invoice_number,
            invoice_amount=invoice_amount,
            due_date=due_date,
            days_late=days_late,
            business_name=business_name,
        )

        # TODO: Chiama AI per generare messaggio
        # message_ai = await self.ai_service.generate_sollecito(**prompt_data)
        message_ai = self._generate_fallback_message(stage, prompt_data)

        return {
            "stage": stage,
            "channel": channel,
            "subject": engine.get_subject(stage, invoice_number, days_late),
            "message_ai": message_ai,
            "should_send": not engine.needs_human_review(),
            "should_offer_rateizzazione": engine.should_offer_rateizzazione(stage),
            "needs_human_review": engine.needs_human_review(),
            "legal_record": engine.should_create_legal_record(stage),
            "days_before_lawyer": engine.get_days_before_lawyer(stage),
            "psychology_frame": psychology_frame.value,
            "stage_name": stage.value,
        }

    def _build_ai_prompt(
        self,
        engine: PaymentRecoveryEngine,
        stage: EscalationStage,
        channel: CommunicationChannel,
        psychology_frame: PsychologicalFrame,
        client_name: str,
        invoice_number: str,
        invoice_amount: float,
        due_date: date,
        days_late: int,
        business_name: str,
    ) -> dict:
        """Costruisce i dati per il prompt AI."""

        formatted_amount = f"€{invoice_amount:,.2f}".replace(",", ".")
        formatted_date = due_date.strftime("%d/%m/%Y")
        stage_tone = STAGE_PROMPTS[stage]["tone"]

        return {
            "client_name": client_name,
            "invoice_number": invoice_number,
            "invoice_amount": formatted_amount,
            "due_date": formatted_date,
            "days_late": days_late,
            "business_name": business_name,
            "stage_tone": stage_tone,
            "channel": channel.value,
            "psychology_frame": psychology_frame.value,
            "offer_rateizzazione": engine.should_offer_rateizzazione(stage),
            "mention_interest": STAGE_PROMPTS[stage].get("mention_interest", False),
            "mention_legal_costs": STAGE_PROMPTS[stage].get("mention_legal_costs", False),
            "days_before_lawyer": engine.get_days_before_lawyer(stage),
        }

    def _generate_fallback_message(self, stage: EscalationStage, data: dict) -> str:
        """
        Genera un messaggio di fallback se l'AI non è disponibile.
        Usa i template statici esistenti.
        """
        # TODO: Usa reminder_templates.py esistente come fallback
        return f"Gentile {data['client_name']}, in riferimento alla fattura {data['invoice_number']} di {data['invoice_amount']} scaduta il {data['due_date']}, vi invitiamo a provvedere al pagamento."


# ─────────────────────────────────────────────────────────────────────────────
# Funzione helper per uso rapido
# ─────────────────────────────────────────────────────────────────────────────

async def get_payment_recovery_data(
    client_name: str,
    invoice_number: str,
    invoice_amount: float,
    due_date: date,
    days_late: int,
    trust_score: int = 60,
    client_profile: str = "new_client",
    has_telegram: bool = False,
    has_pec: bool = False,
    business_name: str = "la nostra azienda",
) -> dict:
    """
    Funzione helper per ottenere i dati di sollecito.

    Usage:
        data = await get_payment_recovery_data(
            client_name="Mario Rossi",
            invoice_number="FT-2026-001",
            invoice_amount=1500.00,
            due_date=date(2026, 3, 10),
            days_late=12,
            trust_score=65,
            client_profile="high_value_long_term",
        )
    """
    service = PaymentRecoveryService()
    return await service.get_sollecito_data(
        client_name=client_name,
        client_vat="",
        client_profile=client_profile,
        trust_score=trust_score,
        invoice_number=invoice_number,
        invoice_amount=invoice_amount,
        due_date=due_date,
        paid_date=None,
        days_late=days_late,
        stage_history=[],
        has_telegram=has_telegram,
        has_pec=has_pec,
        has_whatsapp=False,
        business_name=business_name,
    )
