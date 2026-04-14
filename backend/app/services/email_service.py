"""
Email Service - Invio email via SMTP Brevo (ex Sendinblue).

Supporta:
- Invio email generiche via SMTP
- Invio solleciti di pagamento personalizzati
- Logging di tutte le email inviate nel database
- Retry automatico su errori transienti
"""
import smtplib
import logging
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Errore generico invio email."""
    pass


class EmailAuthError(EmailError):
    """Errore di autenticazione SMTP."""
    pass


class BrevoSMTPService:
    """
    Servizio per invio email tramite SMTP Brevo (Sendinblue).

    Brevo SMTP configuration:
    - Host: smtp-relay.brevo.com
    - Port: 587 (STARTTLS) o 465 (SSL)
    - Login: chiave SMTP (smtp.brevo.com > Configurazione > Chiavi SMTP)
    - Password: non usata (autenticazione con chiave SMTP)

    La chiave SMTP si trova su: https://app.brevo.com/settings/keys/smtp
    """

    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT_TLS: int = 587
    SMTP_PORT_SSL: int = 465

    def __init__(
        self,
        smtp_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        """
        Inizializza il servizio email Brevo.

        Args:
            smtp_key: Chiave SMTP Brevo (opzionale, usa settings se non fornita)
            from_email: Email mittente predefinita
            from_name: Nome mittente predefinito
        """
        self.smtp_key = smtp_key or getattr(settings, 'BREVO_SMTP_KEY', None)
        self.from_email = from_email or getattr(settings, 'BREVO_FROM_EMAIL', 'noreply@fatturamvp.it')
        self.from_name = from_name or getattr(settings, 'BREVO_FROM_NAME', 'FatturaMVP')

    def _build_message(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        body: str,
        body_html: Optional[str] = None,
    ) -> MIMEMultipart:
        """Costruisce il messaggio email MIME."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email

        # Plain text
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # HTML (se fornito)
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        return msg

    async def _send_via_smtp(self, msg: MIMEMultipart, to_email: str) -> Dict[str, Any]:
        """
        Invia email tramite connessione SMTP.

        Args:
            msg: Messaggio MIME costruito
            to_email: Email destinatario

        Returns:
            Dizionario con esito invio

        Raises:
            EmailError: In caso di errore
        """
        if not self.smtp_key:
            raise EmailAuthError("Brevo SMTP key non configurata")

        logger.info(
            f"[EMAIL] Invio a {to_email}: {msg['Subject']}",
            extra={
                "email_to": to_email,
                "email_subject": msg["Subject"],
                "email_from": msg["From"],
            }
        )

        try:
            # Connessione TLS sulla porta 587
            server = smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT_TLS, timeout=30)
            server.set_debuglevel(0)

            try:
                server.starttls()
                # Autenticazione con chiave SMTP come username, la key come password
                server.login(self.smtp_key, "")  # Brevo usa la chiave come password vuoto
                server.sendmail(self.from_email, [to_email], msg.as_string())
            finally:
                server.quit()

            logger.info(f"[EMAIL] Invio riuscito a {to_email}")
            return {
                "success": True,
                "to": to_email,
                "subject": msg["Subject"],
                "sent_at": datetime.utcnow().isoformat(),
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[EMAIL] Errore autenticazione SMTP: {e}")
            raise EmailAuthError(f"Autenticazione SMTP fallita: {str(e)}")

        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"[EMAIL] Destinatario rifiutato: {e}")
            raise EmailError(f"Destinatario rifiutato: {to_email}")

        except smtplib.SMTPException as e:
            logger.error(f"[EMAIL] Errore SMTP: {e}")
            raise EmailError(f"Errore SMTP: {str(e)}")

        except Exception as e:
            logger.error(f"[EMAIL] Errore generico invio email: {e}")
            raise EmailError(f"Errore invio email: {str(e)}")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        to_name: Optional[str] = None,
        body_html: Optional[str] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Invia un'email tramite SMTP Brevo.

        Args:
            to_email: Email destinatario
            subject: Oggetto dell'email
            body: Body plain text dell'email
            to_name: Nome del destinatario (opzionale)
            body_html: Body HTML opzionale
            retry_count: Contatore retry interno

        Returns:
            Dizionario con esito invio

        Raises:
            EmailError: In caso di errore dopo tutti i retry
        """
        MAX_RETRIES = 3

        msg = self._build_message(to_email, to_name, subject, body, body_html)

        try:
            result = await self._send_via_smtp(msg, to_email)

            # Logga nel database se disponibile
            await self._log_email(
                email_type="other",
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body_preview=body[:500],
                status="sent",
            )

            return result

        except (EmailAuthError, EmailError) as e:
            if retry_count < MAX_RETRIES:
                wait_time = (2 ** retry_count) * 2.0
                logger.warning(
                    f"[EMAIL] Retry {retry_count + 1}/{MAX_RETRIES} dopo {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
                return await self.send_email(
                    to_email, subject, body, to_name, body_html, retry_count + 1
                )
            raise

    async def send_sollecito_email(
        self,
        invoice_id: int,
        to_email: str,
        to_name: Optional[str],
        invoice_number: str,
        invoice_amount: float,
        due_date: str,
        message: str,
        client_id: Optional[int] = None,
        sollecito_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Invia un sollecito di pagamento via email.

        Args:
            invoice_id: ID della fattura
            to_email: Email destinatario
            to_name: Nome del destinatario
            invoice_number: Numero fattura
            invoice_amount: Importo fattura
            due_date: Data scadenza formattata
            message: Body del sollecito
            client_id: ID cliente (opzionale)
            sollecito_id: ID sollecito (opzionale)

        Returns:
            Dizionario con esito invio

        Raises:
            EmailError: In caso di errore
        """
        subject = f"Sollecito pagamento fattura {invoice_number} - Scaduta il {due_date}"
        formatted_amount = f"€{invoice_amount:,.2f}".replace(",", ".")

        # Costruisci body completo
        full_body = f"""
Gentile {to_name or "Cliente"},

{message}

Dettagli fattura:
- Numero fattura: {invoice_number}
- Importo: {formatted_amount}
- Data scadenza: {due_date}

Se hai gia' provveduto al pagamento, ti ringraziamo e ti chiediamo di ignorare questa comunicazione.

Per qualsiasi domanda o problema, non esitare a contattarci.

Cordiali saluti,
{self.from_name}
""".strip()

        # HTML versione
        body_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
<p>Gentile <strong>{to_name or "Cliente"}</strong>,</p>
<p>{message.replace(chr(10), '<br>')}</p>
<hr>
<p><strong>Dettagli fattura:</strong></p>
<ul>
<li>Numero fattura: <strong>{invoice_number}</strong></li>
<li>Importo: <strong>{formatted_amount}</strong></li>
<li>Data scadenza: <strong>{due_date}</strong></li>
</ul>
<p>Se hai gia' provveduto al pagamento, ti ringraziamo e ti chiediamo di ignorare questa comunicazione.</p>
<p>Per qualsiasi domanda o problema, non esitare a contattarci.</p>
<hr>
<p>Cordiali saluti,<br><strong>{self.from_name}</strong></p>
</body>
</html>
"""

        logger.info(
            f"[EMAIL] Invio sollecito per fattura {invoice_number} a {to_email}",
            extra={
                "sollecito_invoice_id": invoice_id,
                "sollecito_client_id": client_id,
                "sollecito_id": sollecito_id,
                "email_to": to_email,
            }
        )

        try:
            result = await self.send_email(
                to_email=to_email,
                subject=subject,
                body=full_body,
                to_name=to_name,
                body_html=body_html,
            )

            # Logga nel database
            await self._log_email(
                email_type="sollecito",
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body_preview=message[:500],
                invoice_id=invoice_id,
                client_id=client_id,
                sollecito_id=sollecito_id,
                status="sent",
            )

            return result

        except Exception as e:
            # Logga fallimento
            await self._log_email(
                email_type="sollecito",
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body_preview=message[:500],
                invoice_id=invoice_id,
                client_id=client_id,
                sollecito_id=sollecito_id,
                status="failed",
                error_message=str(e),
            )
            raise

    async def _log_email(
        self,
        email_type: str,
        recipient_email: str,
        recipient_name: Optional[str],
        subject: str,
        body_preview: str,
        invoice_id: Optional[int] = None,
        client_id: Optional[int] = None,
        reminder_id: Optional[int] = None,
        sollecito_id: Optional[int] = None,
        template_id: Optional[str] = None,
        status: str = "pending",
        error_message: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> None:
        """
        Logga un'email inviata nel database.

        Args:
            email_type: Tipo email (invoice, reminder, sollecito, etc.)
            recipient_email: Email destinatario
            recipient_name: Nome destinatario
            subject: Oggetto
            body_preview: Anteprima body (primi 500 chars)
            invoice_id: ID fattura correlata
            client_id: ID cliente correlato
            reminder_id: ID reminder correlato
            sollecito_id: ID sollecito correlato
            template_id: ID template Brevo usato
            status: Stato invio (pending, sent, delivered, failed, bounced)
            error_message: Messaggio errore se fallito
            tenant_id: ID tenant
        """
        try:
            from app.models.database import EmailLog, EmailType
            from app.db.session import async_session_maker
            from sqlalchemy import select

            async with async_session_maker() as db:
                log_entry = EmailLog(
                    tenant_id=tenant_id,
                    email_type=EmailType.SOLLECITO if email_type == "sollecito" else EmailType.OTHER,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name or "",
                    subject=subject,
                    body_preview=body_preview,
                    template_id=template_id,
                    invoice_id=invoice_id,
                    client_id=client_id,
                    reminder_id=reminder_id,
                    sollecito_id=sollecito_id,
                    status=status,
                    error_message=error_message,
                    attempts=1,
                    sent_at=datetime.utcnow() if status == "sent" else None,
                )
                db.add(log_entry)
                await db.commit()

                logger.info(
                    f"[EMAIL] Log salvato per {recipient_email}: {status}",
                    extra={
                        "email_type": email_type,
                        "email_status": status,
                        "email_invoice_id": invoice_id,
                    }
                )

        except Exception as e:
            # Non fallire l'invio se il logging fallisce
            logger.warning(f"[EMAIL] Errore logging email: {e}")


# === Singleton ===
_email_service_instance: Optional[BrevoSMTPService] = None


def get_email_service() -> BrevoSMTPService:
    """Restituisce l'istanza singleton del servizio email."""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = BrevoSMTPService()
    return _email_service_instance
