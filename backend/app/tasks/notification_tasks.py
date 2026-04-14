"""
Task Celery per la gestione delle notifiche.
Include: riepilogo giornaliero, notifiche istantanee, solleciti via email/Telegram.
"""
from app.tasks.celery_app import celery_app
from celery import Task
import logging
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func

logger = logging.getLogger(__name__)


class NotificationTask(Task):
    """Task base con retry automatico per notifiche."""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


@celery_app.task(bind=True, base=NotificationTask, name="app.tasks.notification_tasks.send_daily_reminder")
def send_daily_reminder(self, user_id: int = None) -> dict:
    """
    Invia riepilogo giornaliero delle fatture all'utente.
    Scheduled: ogni giorno alle 8:30.
    
    Args:
        user_id: ID utente opzionale (se None, invia a tutti gli utenti attivi)
        
    Returns:
        dict con riepilogo invii
    """
    logger.info(f"Notifiche: Avvio riepilogo giornaliero (user_id={user_id})")
    
    async def _send():
        from app.db.session import async_session_maker
        from app.models.user import User
        from app.models.invoice import Invoice, InvoiceStatus
        
        async with async_session_maker() as db:
            # Costruisce query per utenti
            if user_id:
                query = select(User).where(
                    and_(User.id == user_id, User.is_active == True)
                )
            else:
                query = select(User).where(User.is_active == True)
            
            result = await db.execute(query)
            users = result.scalars().all()
            
            sent_count = 0
            failed_count = 0
            results = []
            
            today = date.today()
            
            for user in users:
                try:
                    # Carica fatture pendenti per l'utente
                    invoices_result = await db.execute(
                        select(Invoice).where(
                            and_(
                                Invoice.created_by == user.id,
                                Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE])
                            )
                        )
                    )
                    user_invoices = invoices_result.scalars().all()
                    
                    # Separa per scadenza
                    overdue = [inv for inv in user_invoices if inv.due_date < today]
                    due_soon = [inv for inv in user_invoices 
                               if inv.due_date >= today and inv.due_date <= today + timedelta(days=7)]
                    
                    # Costruisce messaggio riepilogo
                    if not user_invoices:
                        continue  # Skip utenti senza fatture
                    
                    message = _build_daily_reminder_message(user, overdue, due_soon, today)
                    
                    # Invia tramite canali configurati
                    if user.telegram_chat_id:
                        await _send_telegram(user.telegram_chat_id, message)
                        sent_count += 1
                    elif user.email:
                        await _send_email(user.email, "Riepilogo Fatture - FatturaMVP", message)
                        sent_count += 1
                    else:
                        failed_count += 1
                    
                    results.append({
                        "user_id": user.id,
                        "email": user.email,
                        "invoices_count": len(user_invoices),
                        "overdue": len(overdue),
                        "due_soon": len(due_soon)
                    })
                    
                except Exception as e:
                    logger.error(f"Notifiche: Errore per utente {user.id}: {e}")
                    failed_count += 1
            
            logger.info(f"Notifiche: Riepilogo completato. Inviati: {sent_count}, Falliti: {failed_count}")
            
            return {
                "success": True,
                "sent": sent_count,
                "failed": failed_count,
                "details": results
            }
    
    import asyncio
    return asyncio.run(_send())


@celery_app.task(bind=True, base=NotificationTask, name="app.tasks.notification_tasks.send_instant_notification")
def send_instant_notification(self, invoice_id: int, notification_type: str) -> dict:
    """
    Invia notifica immediata per una fattura.
    
    Args:
        invoice_id: ID della fattura
        notification_type: tipo di notifica (payment_received, invoice_overdue, invoice_paid, etc.)
        
    Returns:
        dict con esito invio
    """
    logger.info(f"Notifiche: Notifica immediata per fattura {invoice_id}, tipo {notification_type}")
    
    async def _send():
        from app.db.session import async_session_maker
        from app.models.invoice import Invoice
        from app.models.user import User
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            # Recupera fattura
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                return {"success": False, "error": "Fattura non trovata"}
            
            # Recupera utente proprietario
            if not invoice.created_by:
                return {"success": False, "error": "Fattura senza utente proprietario"}
            
            user_result = await db.execute(
                select(User).where(User.id == invoice.created_by)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"success": False, "error": "Utente non trovato"}
            
            # Costruisce messaggio in base al tipo
            message = _build_instant_notification_message(invoice, notification_type)
            
            # Invia al canale preferito dell'utente
            sent = False
            
            if user.telegram_chat_id:
                await _send_telegram(user.telegram_chat_id, message)
                sent = True
            
            if user.email and not sent:
                await _send_email(user.email, f"FatturaMVP - Notifica", message)
                sent = True
            
            if not sent:
                logger.warning(f"Notifiche: Nessun canale disponibile per utente {user.id}")
                return {"success": False, "error": "Nessun canale di notifica configurato"}
            
            return {
                "success": True,
                "invoice_id": invoice_id,
                "notification_type": notification_type,
                "user_id": user.id
            }
    
    import asyncio
    return asyncio.run(_send())


@celery_app.task(bind=True, base=NotificationTask, name="app.tasks.notification_tasks.send_sollecito")
def send_sollecito(self, invoice_id: int, channel: str = "auto") -> dict:
    """
    Invia sollecito pagamento via email o Telegram.
    
    Args:
        invoice_id: ID della fattura
        channel: canale ('email', 'telegram', 'auto')
        
    Returns:
        dict con esito invio
    """
    logger.info(f"Notifiche: Invio sollecito per fattura {invoice_id}, canale {channel}")
    
    async def _send():
        from app.db.session import async_session_maker
        from app.models.invoice import Invoice, Reminder
        from app.models.user import User
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            # Recupera fattura
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                return {"success": False, "error": "Fattura non trovata"}
            
            # Recupera utente
            if not invoice.created_by:
                return {"success": False, "error": "Fattura senza utente proprietario"}
            
            user_result = await db.execute(
                select(User).where(User.id == invoice.created_by)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"success": False, "error": "Utente non trovato"}
            
            # Costruisce messaggio sollecito
            message = _build_sollecito_message(invoice)
            
            # Determina canale
            actual_channel = channel
            if channel == "auto":
                if user.telegram_chat_id:
                    actual_channel = "telegram"
                elif user.email:
                    actual_channel = "email"
                else:
                    return {"success": False, "error": "Nessun canale disponibile"}
            
            # Invia
            sent = False
            
            if actual_channel == "telegram":
                if user.telegram_chat_id:
                    await _send_telegram(user.telegram_chat_id, message)
                    sent = True
                else:
                    return {"success": False, "error": "Telegram non configurato"}
            
            elif actual_channel == "email":
                if user.email:
                    await _send_email(user.email, f"Sollecito pagamento - {invoice.invoice_number}", message)
                    sent = True
                else:
                    return {"success": False, "error": "Email non configurata"}
            
            # Crea record reminder in DB
            if sent:
                reminder = Reminder(
                    invoice_id=invoice_id,
                    reminder_date=datetime.utcnow(),
                    reminder_type="sollecito",
                    sent_via=actual_channel,
                    status="sent",
                    message=message[:1000] if message else None,
                    sent_by=user.id
                )
                db.add(reminder)
                await db.commit()
            
            return {
                "success": sent,
                "invoice_id": invoice_id,
                "channel": actual_channel,
                "user_id": user.id
            }
    
    import asyncio
    return asyncio.run(_send())


# =============================================================================
# HELPERS - Costruzione messaggi
# =============================================================================

def _build_daily_reminder_message(user, overdue: list, due_soon: list, today: date) -> str:
    """Costruisce il messaggio di riepilogo giornaliero."""
    
    message = f"📊 *Riepilogo FatturaMVP - {today.strftime('%d/%m/%Y')}*\n\n"
    
    if user.full_name:
        message += f"Ciao {user.full_name},\n\n"
    
    if overdue:
        message += f"⚠️ *FATTURE SCADUTE ({len(overdue)})*\n"
        for inv in overdue[:5]:  # Max 5 in elenco
            days_overdue = (today - inv.due_date).days
            message += f"• {inv.invoice_number}: €{inv.total_amount:,.2f} (scaduta {days_overdue}gg fa)\n"
        if len(overdue) > 5:
            message += f"• ... e altre {len(overdue) - 5} fatture\n"
        message += "\n"
    
    if due_soon:
        message += f"📅 *IN SCADENZA PRESTO ({len(due_soon)})*\n"
        for inv in due_soon[:5]:
            days_until = (inv.due_date - today).days
            message += f"• {inv.invoice_number}: €{inv.total_amount:,.2f} (tra {days_until}gg)\n"
        if len(due_soon) > 5:
            message += f"• ... e altre {len(due_soon) - 5} fatture\n"
        message += "\n"
    
    if not overdue and not due_soon:
        message += "✅ Nessuna fattura da sollecitare oggi.\n\n"
    
    message += "—\n_Generato automaticamente da FatturaMVP_"
    
    return message


def _build_instant_notification_message(invoice, notification_type: str) -> str:
    """Costruisce messaggio di notifica istantanea."""
    
    emoji = {
        "payment_received": "✅",
        "invoice_overdue": "⚠️",
        "invoice_paid": "💰",
        "invoice_created": "📄",
        "reminder_sent": "🔔",
    }.get(notification_type, "📢")
    
    titles = {
        "payment_received": "Pagamento Ricevuto",
        "invoice_overdue": "Fattura Scaduta",
        "invoice_paid": "Fattura Saldata",
        "invoice_created": "Nuova Fattura",
        "reminder_sent": "Sollecito Inviato",
    }.get(notification_type, "Notifica")
    
    message = f"{emoji} *{titles}*\n\n"
    message += f"📄 Fattura: {invoice.invoice_number}\n"
    message += f"💶 Importo: €{invoice.total_amount:,.2f}\n"
    message += f"📅 Scadenza: {invoice.due_date.strftime('%d/%m/%Y')}\n"
    message += f"🏢 Cliente: {invoice.customer_name}\n"
    
    if notification_type == "payment_received":
        message += "\n_Il pagamento è stato registrato nel sistema._\n"
    elif notification_type == "invoice_overdue":
        days = (date.today() - invoice.due_date).days
        message += f"\n⚠️ La fattura è scaduta da {days} giorni.\n"
    
    message += "\n—\n_Notifica automatica FatturaMVP_"
    
    return message


def _build_sollecito_message(invoice) -> str:
    """Costruisce messaggio di sollecito."""
    
    days_overdue = (date.today() - invoice.due_date).days if invoice.due_date < date.today() else 0
    
    message = f"🔔 *SOLLECITO DI PAGAMENTO*\n\n"
    message += f" Gentile Cliente,\n\n"
    message += f"con la presente Vi sollecitiamo gentilmente al pagamento della fattura in oggetto.\n\n"
    message += f"📄 *Dati Fattura*\n"
    message += f"• Numero: {invoice.invoice_number}\n"
    message += f"• Data: {invoice.invoice_date.strftime('%d/%m/%Y')}\n"
    message += f"• Scadenza: {invoice.due_date.strftime('%d/%m/%Y')}\n"
    message += f"• Importo: €{invoice.total_amount:,.2f}\n\n"
    message += f"🏢 *Vs. Dati*\n"
    message += f"• Ragione Sociale: {invoice.customer_name}\n"
    
    if invoice.customer_vat:
        message += f"• P.IVA: {invoice.customer_vat}\n"
    
    message += f"\n💳 *Dati Pagamento*\n"
    if invoice.supplier_iban:
        message += f"• IBAN: {invoice.supplier_iban}\n"
    
    if days_overdue > 0:
        message += f"\n⚠️ *La fattura risulta scaduta da {days_overdue} giorni.*\n"
    
    message += f"\n_Vi invitiamo a provvedere al pagamento entro 7 giorni dalla data odierna._\n"
    message += f"\n_Cordiali saluti_\n"
    message += f"_FatturaMVP_\n"
    
    return message


# =============================================================================
# HELPERS - Invio canali
# =============================================================================

async def _send_telegram(chat_id: str, message: str) -> bool:
    """Invia messaggio via Telegram."""
    import httpx
    from app.core.config import settings
    
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram: Bot token non configurato")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=settings.NOTIFICATION_CONFIG.get("telegram_timeout", 10) if hasattr(settings, 'NOTIFICATION_CONFIG') else 10
            )
            
            if response.status_code == 200:
                logger.info(f"Telegram: Messaggio inviato a {chat_id}")
                return True
            else:
                logger.error(f"Telegram: Errore invio {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Telegram: Eccezione invio: {e}")
        return False


async def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Invia email (placeholder - da implementare con SMTP reale)."""
    # In produzione: implementare con aiosmtplib
    logger.info(f"Email: Da implementare - a {to_email}: {subject}")
    return True
