"""
Telegram Service - Invio messaggi e notifiche via Bot Telegram.

Funzionalita:
- Invio messaggi di testo
- Invio solleciti di pagamento
- Notifiche promemoria fatture
- Notifiche stato SDI
- Invio documenti (PDF fatture)
- Keyboard inline per azioni rapide

Il bot Telegram deve essere configurato con:
- TELEGRAM_BOT_TOKEN in settings
- Chat ID dell'utente (dalla tabella users.telegram_chat_id)
"""
import httpx
import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    """Errore generico Telegram."""
    pass


class TelegramBotError(TelegramError):
    """Errore API Telegram Bot."""
    pass


class TelegramService:
    """
    Servizio per invio messaggi tramite Bot Telegram.

    Documentazione: https://core.telegram.org/bots/api

    Utilizza la Telegram Bot API per inviare messaggi e notifiche.
    """

    API_BASE: str = "https://api.telegram.org/bot"

    def __init__(self, bot_token: Optional[str] = None):
        """
        Inizializza il servizio Telegram.

        Args:
            bot_token: Token del bot Telegram (opzionale, usa settings se non fornito)
        """
        self.bot_token = bot_token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def api_base(self) -> str:
        """URL base per le API Telegram."""
        if not self.bot_token:
            raise TelegramError("Telegram bot token non configurato")
        return f"{self.API_BASE}{self.bot_token}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Ottiene o crea un client HTTP condiviso."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Chiude il client HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _api_request(
        self,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Esegue una richiesta all'API Telegram con retry.

        Args:
            method: Metodo API Telegram (es. sendMessage)
            data: Parametri della richiesta
            retry_count: Contatore retry interno

        Returns:
            Risposta JSON dell'API

        Raises:
            TelegramBotError: In caso di errore API
        """
        MAX_RETRIES = 3

        client = await self._get_client()
        url = f"{self.api_base}/{method}"

        logger.info(
            f"[TELEGRAM] API call: {method}",
            extra={
                "tg_method": method,
                "tg_retry": retry_count,
                "tg_has_data": data is not None,
            }
        )

        try:
            response = await client.post(url, json=data)
            result = response.json()

            if not result.get("ok"):
                error_code = result.get("error_code", 0)
                error_description = result.get("description", "Errore sconosciuto")

                logger.error(
                    f"[TELEGRAM] API error: {error_code} - {error_description}",
                    extra={
                        "tg_method": method,
                        "tg_error_code": error_code,
                        "tg_error_description": error_description,
                    }
                )

                # Retry su errori 429 (Too Many Requests) e 500-503
                if error_code in (429, 500, 502, 503) and retry_count < MAX_RETRIES:
                    wait_time = (2 ** retry_count) * 2.0
                    logger.warning(f"[TELEGRAM] Retry {retry_count + 1}/{MAX_RETRIES} dopo {wait_time}s")
                    await asyncio.sleep(wait_time)
                    return await self._api_request(method, data, retry_count + 1)

                raise TelegramBotError(f"Telegram API error {error_code}: {error_description}")

            logger.info(
                f"[TELELEGRAM] Success: {method}",
                extra={
                    "tg_method": method,
                    "tg_retry": retry_count,
                }
            )
            return result

        except httpx.TimeoutException:
            if retry_count < MAX_RETRIES:
                await asyncio.sleep((2 ** retry_count) * 2.0)
                return await self._api_request(method, data, retry_count + 1)
            raise TelegramError("Timeout comunicazione con Telegram")

        except httpx.RequestError as e:
            if retry_count < MAX_RETRIES:
                await asyncio.sleep((2 ** retry_count) * 2.0)
                return await self._api_request(method, data, retry_count + 1)
            raise TelegramError(f"Errore di rete Telegram: {str(e)}")

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
        reply_to_message_id: Optional[str] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invia un messaggio di testo.

        Args:
            chat_id: Chat ID del destinatario
            text: Testo del messaggio (supporta HTML)
            parse_mode: Modalita' parsing (HTML o Markdown)
            disable_notification: Disabilita notifica (mute)
            reply_to_message_id: ID messaggio a cui rispondere
            reply_markup: Keyboard inline opzionale

        Returns:
            Risultato API con message_id

        Raises:
            TelegramError: In caso di errore
        """
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }

        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._api_request("sendMessage", data)
        return result.get("result", {})

    async def send_invoice_reminder(
        self,
        chat_id: str,
        invoice_number: str,
        invoice_amount: float,
        due_date: str,
        days_late: int = 0,
    ) -> Dict[str, Any]:
        """
        Invia un promemoria fattura scaduta o in scadenza.

        Args:
            chat_id: Chat ID del destinatario
            invoice_number: Numero fattura
            invoice_amount: Importo fattura
            due_date: Data scadenza
            days_late: Giorni di ritardo (0 se non scaduta)

        Returns:
            Risultato API

        Raises:
            TelegramError: In caso di errore
        """
        formatted_amount = f"€{invoice_amount:,.2f}".replace(",", ".")

        if days_late > 0:
            emoji = "⚠️"
            title = f"Fattura SCADUTA da {days_late} giorni"
        else:
            emoji = "📅"
            title = "Promemoria fattura in scadenza"

        text = f"""
{emoji} <b>{title}</b>

<b>Fattura:</b> {invoice_number}
<b>Importo:</b> {formatted_amount}
<b>Scadenza:</b> {due_date}

Clicca per maggiori dettagli.
""".strip()

        # Keyboard inline per azioni rapide
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "💰 Segna come pagata", "callback_data": f"pay_{invoice_number}"},
                    {"text": "📋 Dettagli", "callback_data": f"inv_{invoice_number}"},
                ],
                [
                    {"text": "📤 Invia sollecito", "callback_data": f"sollecito_{invoice_number}"},
                ],
            ]
        }

        return await self.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )

    async def send_sollecito(
        self,
        chat_id: str,
        invoice_number: str,
        invoice_amount: float,
        due_date: str,
        client_name: str,
        message: str,
        days_late: int,
        style: str = "gentile",
    ) -> Dict[str, Any]:
        """
        Invia un sollecito di pagamento via Telegram.

        Args:
            chat_id: Chat ID del destinatario
            invoice_number: Numero fattura
            invoice_amount: Importo fattura
            due_date: Data scadenza
            client_name: Nome cliente
            message: Body del sollecito
            days_late: Giorni di ritardo
            style: Stile sollecito (gentile, equilibrato, fermo)

        Returns:
            Risultato API

        Raises:
            TelegramError: In caso di errore
        """
        formatted_amount = f"€{invoice_amount:,.2f}".replace(",", ".")

        style_emoji = {
            "gentile": "🤝",
            "equilibrato": "📢",
            "fermo": "🚨",
        }
        emoji = style_emoji.get(style, "📢")

        text = f"""
{emoji} <b>SOLLECITO DI PAGAMENTO</b>

Gentile <b>{client_name}</b>,

{message}

━━━━━━━━━━━━━━━━━━
<b>Dettagli fattura:</b>
• Numero: {invoice_number}
• Importo: <b>{formatted_amount}</b>
• Scadenza: {due_date}
• Ritardo: <b>{days_late} giorni</b>
━━━━━━━━━━━━━━━━━━

Per effettuare il pagamento:
• IBAN: vedi fattura originale

Per qualsiasi problema contattaci.
""".strip()

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Ho pagato", "callback_data": f"paid_{invoice_number}"},
                    {"text": "📋 Contesta fattura", "callback_data": f"contest_{invoice_number}"},
                ],
                [
                    {"text": "📞 Richiedi contatto", "callback_data": f"contact_{invoice_number}"},
                ],
            ]
        }

        return await self.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )

    async def send_sdi_status(
        self,
        chat_id: str,
        invoice_number: str,
        sdi_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invia una notifica sullo stato SDI di una fattura.

        Args:
            chat_id: Chat ID del destinatario
            invoice_number: Numero fattura
            sdi_id: Identificativo SDI
            status: Stato SDI (sent, delivered, accepted, rejected)
            error_message: Messaggio errore (se presente)

        Returns:
            Risultato API

        Raises:
            TelegramError: In caso di errore
        """
        status_emoji = {
            "draft": "📝",
            "sending": "📤",
            "sent": "✅",
            "delivered": "📬",
            "accepted": "👍",
            "rejected": "❌",
            "error": "⚠️",
        }
        emoji = status_emoji.get(status, "📋")

        status_text = {
            "draft": "Bozza",
            "sending": "In invio",
            "sent": "Inviata a SDI",
            "delivered": "Consegnata al destinatario",
            "accepted": "Accettata",
            "rejected": "Rifiutata",
            "error": "Errore",
        }
        status_label = status_text.get(status, status)

        text = f"""
{emoji} <b>Stato SDI aggiornato</b>

<b>Fattura:</b> {invoice_number}
<b>SDI ID:</b> <code>{sdi_id}</code>
<b>Stato:</b> {status_label}
"""

        if error_message:
            text += f"\n<b>Errore:</b> {error_message}"

        return await self.send_message(chat_id=chat_id, text=text)

    async def send_document(
        self,
        chat_id: str,
        document_path: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invia un documento (PDF fattura).

        Args:
            chat_id: Chat ID del destinatario
            document_path: Path al file PDF
            caption: Caption opzionale

        Returns:
            Risultato API

        Raises:
            TelegramError: In caso di errore
        """
        client = await self._get_client()

        with open(document_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"

            url = f"{self.api_base}/sendDocument"
            response = await client.post(url, data=data, files=files)

        result = response.json()
        if not result.get("ok"):
            raise TelegramBotError(
                f"Telegram API error {result.get('error_code')}: {result.get('description')}"
            )

        return result.get("result", {})

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> Dict[str, Any]:
        """
        Risponde a un callback query (click su inline keyboard).

        Args:
            callback_query_id: ID del callback query
            text: Testo opzionale da mostrare
            show_alert: Se True, mostra come alert invece che toast

        Returns:
            Risultato API
        """
        data = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text:
            data["text"] = text

        return await self._api_request("answerCallbackQuery", data)

    async def get_me(self) -> Dict[str, Any]:
        """
        Restituisce informazioni sul bot.

        Returns:
            Info bot (id, username, name)
        """
        return await self._api_request("getMe")


# === Singleton ===
_telegram_service_instance: Optional[TelegramService] = None


def get_telegram_service() -> TelegramService:
    """Restituisce l'istanza singleton del servizio Telegram."""
    global _telegram_service_instance
    if _telegram_service_instance is None:
        _telegram_service_instance = TelegramService()
    return _telegram_service_instance
