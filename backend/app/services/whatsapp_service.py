"""
WhatsApp Service - Invio messaggi via Twilio WhatsApp API.

Supporta:
- Invio via Twilio WhatsApp (se TWILIO_ACCOUNT_SID configurato)
- Mock mode con logging (se non configurato)
- Salvataggio notification in DB

Twilio WhatsApp setup:
- Account SID: https://console.twilio.com
- FROM: il numero WhatsApp Business approvato (whatsapp:+39xxxxxxxxx)
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppError(Exception):
    """Errore generico WhatsApp."""
    pass


class WhatsAppService:
    """
    Servizio per invio messaggi WhatsApp.

    Usa Twilio WhatsApp API se TWILIO_ACCOUNT_SID è configurato,
    altrimenti opera in mock mode (logga il messaggio).
    """

    API_BASE: str = "https://api.twilio.com/2010-04-01"

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        """
        Inizializza il servizio WhatsApp.

        Args:
            account_sid: Twilio Account SID (opzionale, usa settings se non fornito)
            auth_token: Twilio Auth Token (opzionale)
            from_number: Numero WhatsApp mittente (formato: whatsapp:+39xxxxxxxxx)
        """
        self.account_sid = account_sid or getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = auth_token or getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = from_number or getattr(settings, 'TWILIO_WHATSAPP_FROM', None)
        self._client: Optional[httpx.AsyncClient] = None

        self._is_mock = not bool(self.account_sid and self.auth_token)

    @property
    def is_mock(self) -> bool:
        """True se in modalità mock (Twilio non configurato)."""
        return self._is_mock

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

    async def _send_via_twilio(
        self,
        to_number: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Invia messaggio via Twilio WhatsApp API.

        Args:
            to_number: Numero destinatario (formato: whatsapp:+39xxxxxxxxx)
            body: Body del messaggio

        Returns:
            Risultato con message_sid

        Raises:
            WhatsAppError: In caso di errore
        """
        if not self.account_sid or not self.auth_token:
            raise WhatsAppError("Twilio credentials non configurate")

        url = f"{self.API_BASE}/Accounts/{self.account_sid}/Messages.json"

        data = {
            "To": to_number,
            "From": self.from_number,
            "Body": body,
        }

        client = await self._get_client()

        try:
            response = await client.post(
                url,
                data=data,
                auth=(self.account_sid, self.auth_token),
            )
            result = response.json()

            if response.status_code >= 400:
                error_message = result.get("message", "Errore sconosciuto")
                logger.error(f"[WHATSAPP] Twilio error: {error_message}")
                raise WhatsAppError(f"Twilio error: {error_message}")

            message_sid = result.get("sid", "")
            logger.info(
                f"[WHATSAPP] Messaggio inviato via Twilio: {message_sid}",
                extra={
                    "whatsapp_to": to_number,
                    "whatsapp_sid": message_sid,
                }
            )
            return {
                "success": True,
                "sid": message_sid,
                "status": result.get("status", "sent"),
                "to": to_number,
                "sent_at": datetime.utcnow().isoformat(),
            }

        except httpx.RequestError as e:
            logger.error(f"[WHATSAPP] Errore di rete Twilio: {e}")
            raise WhatsAppError(f"Errore di rete: {str(e)}")

    async def _mock_send(
        self,
        to_number: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Mock mode: logga il messaggio che sarebbe stato inviato.

        Args:
            to_number: Numero destinatario
            body: Body del messaggio

        Returns:
            Risultato mock
        """
        logger.info(
            f"[WHATSAPP] MOCK MODE - Il messaggio sarebbe inviato a {to_number}:",
            extra={
                "whatsapp_to": to_number,
                "whatsapp_body": body,
                "whatsapp_mock": True,
            }
        )
        logger.info(f"[WHATSAPP] MOCK BODY:\n{body}")
        return {
            "success": True,
            "mock": True,
            "sid": f"mock_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "to": to_number,
            "sent_at": datetime.utcnow().isoformat(),
        }

    async def send_message(
        self,
        to_number: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Invia un messaggio WhatsApp.

        Args:
            to_number: Numero destinatario (whatsapp:+39xxxxxxxxx)
            body: Body del messaggio

        Returns:
            Dizionario con esito invio

        Raises:
            WhatsAppError: In caso di errore (non in mock mode)
        """
        # Normalizza il numero: deve avere prefisso whatsapp:
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"

        if self.is_mock:
            return await self._mock_send(to_number, body)
        else:
            return await self._send_via_twilio(to_number, body)

    async def send_sollecito(
        self,
        invoice_id: int,
        to_number: str,
        customer_name: str,
        invoice_number: str,
        invoice_amount: float,
        due_date: str,
        payment_link: Optional[str] = None,
        client_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Invia un sollecito di pagamento via WhatsApp.

        Template:
        "Gentile {{cliente}}, ricordiamo che la fattura {{numero}} di €{{importo}}
         è scaduta il {{scadenza}}. Paga ora: {{payment_link}}"

        Args:
            invoice_id: ID della fattura
            to_number: Numero WhatsApp destinatario
            customer_name: Nome cliente
            invoice_number: Numero fattura
            invoice_amount: Importo fattura
            due_date: Data scadenza formattata
            payment_link: Link di pagamento opzionale
            client_id: ID cliente (opzionale)

        Returns:
            Dizionario con esito invio
        """
        formatted_amount = f"€{invoice_amount:,.2f}".replace(",", ".")

        # Template WhatsApp sollecito
        message = (
            f"Gentile {customer_name}, "
            f"ricordiamo che la fattura {invoice_number} di {formatted_amount} "
            f"è scaduta il {due_date}."
        )

        if payment_link:
            message += f" Paga ora: {payment_link}"

        logger.info(
            f"[WHATSAPP] Invio sollecito per fattura {invoice_number} a {to_number}",
            extra={
                "sollecito_invoice_id": invoice_id,
                "sollecito_client_id": client_id,
                "whatsapp_to": to_number,
                "has_payment_link": bool(payment_link),
            }
        )

        result = await self.send_message(to_number, message)

        # Salva notification in DB
        await self._log_notification(
            invoice_id=invoice_id,
            client_id=client_id,
            channel="whatsapp",
            recipient=to_number,
            content=message,
            status="sent" if result.get("success") else "failed",
            provider_sid=result.get("sid"),
            error_message=result.get("error") if not result.get("success") else None,
        )

        return result

    async def _log_notification(
        self,
        invoice_id: int,
        client_id: Optional[int],
        channel: str,
        recipient: str,
        content: str,
        status: str,
        provider_sid: Optional[str] = None,
        error_message: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> None:
        """
        Salva una notification nel database.

        Args:
            invoice_id: ID fattura correlata
            client_id: ID cliente correlato
            channel: Canale (whatsapp)
            recipient: Destinatario
            content: Contenuto del messaggio
            status: Stato (sent, failed)
            provider_sid: SID Twilio (se usato)
            error_message: Messaggio errore (se fallito)
            tenant_id: ID tenant
        """
        try:
            from app.models.database import Notification
            from app.db.session import async_session_maker

            async with async_session_maker() as db:
                notification = Notification(
                    invoice_id=invoice_id,
                    client_id=client_id,
                    channel=channel,
                    recipient=recipient,
                    content=content,
                    status=status,
                    provider_sid=provider_sid,
                    error_message=error_message,
                    sent_at=datetime.utcnow() if status == "sent" else None,
                )
                db.add(notification)
                await db.commit()

                logger.info(
                    f"[WHATSAPP] Notification salvata per fattura {invoice_id}: {status}",
                    extra={
                        "notification_channel": channel,
                        "notification_status": status,
                        "notification_invoice_id": invoice_id,
                    }
                )

        except Exception as e:
            # Non fallire l'invio se il logging fallisce
            logger.warning(f"[WHATSAPP] Errore logging notification: {e}")


# === Singleton ===
_whatsapp_service_instance: Optional[WhatsAppService] = None


def get_whatsapp_service() -> WhatsAppService:
    """Restituisce l'istanza singleton del servizio WhatsApp."""
    global _whatsapp_service_instance
    if _whatsapp_service_instance is None:
        _whatsapp_service_instance = WhatsAppService()
    return _whatsapp_service_instance
