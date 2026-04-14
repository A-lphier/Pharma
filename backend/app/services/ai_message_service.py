"""
AI-Powered Message Generation Service.

Genera messaggi personalizzati per solleciti di pagamento usando AI.
Design plug-and-play: puoi sostituire il provider AI senza cambiare il codice chiamante.

Provider supportati:
- MiniMax (provider predefinito)
- OpenAI (fallback)
- Anthropic (future)
"""
import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any, List

import httpx

from app.core.config import settings
from app.services.trust_score import get_trust_score_label

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    MINIMAX = "minimax"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class AIProviderInterface(ABC):
    """Interfaccia astratta per i provider AI."""

    @abstractmethod
    async def generate_message(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Genera un messaggio usando il provider AI."""
        pass


class MiniMaxProvider(AIProviderInterface):
    """Provider MiniMax — quello usato da te e Cloud."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.MINIMAX_API_KEY
        self.base_url = base_url or settings.MINIMAX_BASE_URL or "https://api.minimax.chat/v1"

    async def generate_message(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        if not self.api_key:
            raise ValueError("MiniMax API key non configurata")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # MiniMax usa API Anthropic-compatible (come configurato in OpenClaw)
        payload = {
            "model": "MiniMax-M2.7",
            "messages": [
                {"role": "user", "content": f"<system>{system_prompt}</system>\n\n{prompt}"},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            # MiniMax returns content as array with objects of type "text" or "thinking"
            for item in data.get("content", []):
                if item.get("type") == "text":
                    return item["text"]
            # Fallback: return first item's text if available
            return data["content"][0].get("text", "")


class OpenAIProvider(AIProviderInterface):
    """Provider OpenAI (fallback)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    async def generate_message(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key non configurata")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AIProviderFactory:
    """Factory per ottenere il provider AI corretto."""

    _providers: Dict[AIProvider, AIProviderInterface] = {}

    @classmethod
    def get_provider(cls, provider: AIProvider = AIProvider.MINIMAX) -> AIProviderInterface:
        if provider == AIProvider.MINIMAX:
            if AIProvider.MINIMAX not in cls._providers:
                cls._providers[AIProvider.MINIMAX] = MiniMaxProvider()
            return cls._providers[AIProvider.MINIMAX]
        elif provider == AIProvider.OPENAI:
            if AIProvider.OPENAI not in cls._providers:
                cls._providers[AIProvider.OPENAI] = OpenAIProvider()
            return cls._providers[AIProvider.OPENAI]
        else:
            raise ValueError(f"Provider {provider} non supportato")

    @classmethod
    def set_provider(cls, provider: AIProvider, instance: AIProviderInterface):
        """Inietta un provider custom (utile per testing o provider alternativi)."""
        cls._providers[provider] = instance


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Builder — costruisce i prompt per i solleciti
# ─────────────────────────────────────────────────────────────────────────────

STYLE_DESCRIPTIONS = {
    "gentile": "Tono gentile, cortese, empatico. Tratti il cliente come un ospite gradito.",
    "equilibrato": "Tono professionale e neutro. Né troppo morbido né troppo fermo.",
    "fermo": "Tono deciso e professionale. Chiaro sulle conseguenze del mancato pagamento.",
}

TRUST_SCORE_HINTS = {
    "excellent": "Cliente eccellente, pagamenti sempre puntuali. Probabilmente un dimenticanza.",
    "reliable": "Cliente affidabile. Richiamo amichevole dovrebbe bastare.",
    "verify": "Cliente con qualche ritardo. Usa discrezione ma sollecita con fermezza.",
    "problems": "Cliente con precedenti ritardi. Fai emergere l'urgenza.",
    "unreliable": "Cliente problematico. Evita minacce esplicite ma sii fermo e professionale.",
}


def build_sollecito_prompt(
    client_name: str,
    invoice_number: str,
    invoice_amount: float,
    due_date: date,
    trust_score: int,
    style: str,
    days_late: int = 0,
    is_overdue: bool = False,
    payment_history: Optional[List[Dict[str, Any]]] = None,
    business_name: str = "la nostra azienda",
    business_sector: str = "",
) -> tuple[str, str]:
    """
    Costruisce il system prompt e il user prompt per la generazione del sollecito.

    Returns:
        (system_prompt, user_prompt) — entrambi da passare al provider AI
    """
    label, emoji = get_trust_score_label(trust_score)
    formatted_amount = f"€{invoice_amount:,.2f}".replace(",", ".")
    formatted_date = due_date.strftime("%d/%m/%Y")

    if is_overdue:
        scadenza_text = f"scaduta da {days_late} giorni (scadeva il {formatted_date})"
    else:
        scadenza_text = f"in scadenza il {formatted_date}"

    history_text = ""
    if payment_history:
        history_lines = []
        for h in payment_history[-3:]:
            h_date = h.get("date", "N/D")
            h_amount = h.get("amount", 0)
            h_late = h.get("days_late", 0)
            if h_late > 0:
                history_lines.append(f"- Fattura del {h_date}: {h_late} giorni di ritardo")
            else:
                history_lines.append(f"- Fattura del {h_date}: pagata in tempo")
        if history_lines:
            history_text = "\nStorico pagamenti:\n" + "\n".join(history_lines)

    system_prompt = f"""Sei un assistente AI specializzato nella redazione di messaggi di sollecito pagamento per aziende italiane.

REGOLE FONDAMENTALI:
1. Scrivi SOLO il messaggio, senza prefissi, spiegazioni o note
2. Il messaggio deve essere in ITALIANO, professionale ma umano
3. Lunghezza: 50-200 parole
4. Includi sempre: nome cliente, numero fattura, importo, data scadenza
5. Non inventare date, importi o dati — usa solo quelli forniti
6. Non usare placeholder come [NOME], [DATA] — riempi con i dati reali
7. Adatta il tono al profilo del cliente (vedi sotto)
8. Non minacciare mai direttamente azioni legali
9. Firma con il nome dell'azienda fornito, non con "L'azienda" o simili
10. Non usare frasi generiche — il messaggio deve sembrare scritto da un umano per quello specifico cliente

STILE DI COMUNICAZIONE: {style.upper()}
{STYLE_DESCRIPTIONS.get(style, STYLE_DESCRIPTIONS["equilibrato"])}

PROFILO CLIENTE: {label} (trust score {trust_score}/100)
{TRUST_SCORE_HINTS.get(label.lower().replace(" ", "_"), "Cliente con profilo standard")}"""

    user_prompt = f"""Genera un messaggio di sollecito per questo cliente:

DATI FATTURA:
- Cliente: {client_name}
- Numero fattura: {invoice_number}
- Importo: {formatted_amount}
- Status: {scadenza_text}
- Giorni di ritardo: {days_late}{history_text}

NOME AZIENDA CREDITRICE: {business_name}
{"SETTORE: " + business_sector if business_sector else ""}

Stile richiesto: {style}

Scrivi SOLO il messaggio di sollecito, nient'altro."""

    return system_prompt, user_prompt


# ─────────────────────────────────────────────────────────────────────────────
# Service principale
# ─────────────────────────────────────────────────────────────────────────────

class AIMessageService:
    """
    Servizio per generare messaggi AI personalizzati.

    Usage:
        service = AIMessageService()
        message = await service.generate_sollecito(
            client_name="Mario Rossi",
            invoice_number="FT-2026-001",
            invoice_amount=1500.00,
            due_date=date(2026, 3, 15),
            trust_score=65,
            style="gentile",
            days_late=5,
            is_overdue=True,
        )
    """

    def __init__(self, provider: AIProvider = AIProvider.MINIMAX):
        self.provider = AIProviderFactory.get_provider(provider)

    async def generate_sollecito(
        self,
        client_name: str,
        invoice_number: str,
        invoice_amount: float,
        due_date: date,
        trust_score: int,
        style: str = "equilibrato",
        days_late: int = 0,
        is_overdue: bool = False,
        payment_history: Optional[List[Dict[str, Any]]] = None,
        business_name: str = "la nostra azienda",
        business_sector: str = "",
        temperature: float = 0.7,
    ) -> str:
        """
        Genera un messaggio di sollecito personalizzato via AI.

        Args:
            client_name: Nome del cliente
            invoice_number: Numero fattura
            invoice_amount: Importo fattura
            due_date: Data scadenza
            trust_score: Trust score del cliente (0-100)
            style: Stile comunicazione ('gentile', 'equilibrato', 'fermo')
            days_late: Giorni di ritardo (se scaduta)
            is_overdue: True se fattura scaduta
            payment_history: Lista ultimi pagamenti [{date, amount, days_late}]
            business_name: Nome azienda creditrice
            business_sector: Settore azienda
            temperature: Creatività del modello (0.1-1.0)

        Returns:
            Messaggio di sollecito generato
        """
        system_prompt, user_prompt = build_sollecito_prompt(
            client_name=client_name,
            invoice_number=invoice_number,
            invoice_amount=invoice_amount,
            due_date=due_date,
            trust_score=trust_score,
            style=style,
            days_late=days_late,
            is_overdue=is_overdue,
            payment_history=payment_history,
            business_name=business_name,
            business_sector=business_sector,
        )

        try:
            message = await self.provider.generate_message(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=2000,  # MiniMax needs enough tokens for thinking + text
            )
            # Pulisci il messaggio da possibili markdown o prefissi
            return self._clean_message(message)
        except Exception as e:
            logger.error(f"AI message generation failed: {e}")
            # Fallback: usa i template statici
            from app.services.reminder_templates import generate_reminder_message
            return generate_reminder_message(
                client_name=client_name,
                invoice_number=invoice_number,
                invoice_amount=invoice_amount,
                due_date=due_date,
                trust_score=trust_score,
                style=style,
                days_late=days_late,
                is_overdue=is_overdue,
            )

    def _clean_message(self, message: str) -> str:
        """Pulisce il messaggio da markdown e prefissi indesiderati."""
        # Rimuovi blocchi markdown code
        message = re.sub(r'```[\s\S]*?```', '', message)
        # Rimuovi bold/italic markdown
        message = re.sub(r'\*\*([^*]+)\*\*', r'\1', message)
        message = re.sub(r'\*([^*]+)\*', r'\1', message)
        # Rimuovi prefissi come "Messaggio:" ecc.
        message = re.sub(r'^(Messaggio|Sollecto|Sollecto pagamento)[\s:]+', '', message, flags=re.IGNORECASE)
        # Rimuovi spazi multipli
        message = re.sub(r'\n{3,}', '\n\n', message)
        return message.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Funzione helper per uso rapido (backward compatible)
# ─────────────────────────────────────────────────────────────────────────────

_async_generate_sollecito = None


def get_ai_message_service() -> AIMessageService:
    """Factory function — torna sempre un'istanza fresca (così non tiene stato)."""
    return AIMessageService()


async def generate_personalized_sollecito(
    client_name: str,
    invoice_number: str,
    invoice_amount: float,
    due_date: date,
    trust_score: int,
    style: str = "equilibrato",
    days_late: int = 0,
    is_overdue: bool = False,
    payment_history: Optional[List[Dict[str, Any]]] = None,
    business_name: str = "la nostra azienda",
) -> str:
    """
    Genera un sollecito personalizzato via AI (API unificata).

    Uso:
        message = await generate_personalized_sollecito(
            client_name="Mario Rossi",
            invoice_number="FT-2026-001",
            invoice_amount=1500.00,
            due_date=date(2026, 3, 15),
            trust_score=65,
            style="gentile",
            days_late=5,
            is_overdue=True,
        )
    """
    service = AIMessageService()
    return await service.generate_sollecito(
        client_name=client_name,
        invoice_number=invoice_number,
        invoice_amount=invoice_amount,
        due_date=due_date,
        trust_score=trust_score,
        style=style,
        days_late=days_late,
        is_overdue=is_overdue,
        payment_history=payment_history,
        business_name=business_name,
    )
