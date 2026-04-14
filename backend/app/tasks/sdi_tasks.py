"""
Task Celery per la gestione delle operazioni SDI (Sistema Di Interscambio).
Include invio fatture, verifica stato e retry per invii falliti.
"""
from app.tasks.celery_app import celery_app
from celery import Task
import logging
from datetime import datetime, date
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class SDITask(Task):
    """Task base con retry automatico per operazioni SDI."""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(bind=True, base=SDITask, name="app.tasks.sdi_tasks.send_invoice_to_sdi")
def send_invoice_to_sdi(self, invoice_id: int) -> dict:
    """
    Invia una fattura al Sistema Di Interscambio (SDI) in background.
    
    Args:
        invoice_id: ID della fattura da inviare
        
    Returns:
        dict con stato operazione e dettagli
    """
    logger.info(f"SDI: Avvio invio fattura {invoice_id}")
    
    # Importazione ritardata per evitare circular imports
    from app.db.session import async_session_maker
    from app.models.invoice import Invoice, InvoiceStatus
    
    async def _send():
        async with async_session_maker() as db:
            # Recupera fattura
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                logger.error(f"SDI: Fattura {invoice_id} non trovata")
                return {"success": False, "error": "Fattura non trovata", "invoice_id": invoice_id}
            
            # Verifica che la fattura abbia i dati SDI necessari
            if not invoice.customer_sdi and not invoice.customer_pec:
                logger.warning(f"SDI: Fattura {invoice_id} senza SDI/pec cliente")
                return {
                    "success": False,
                    "error": "Cliente senza SDI o PEC",
                    "invoice_id": invoice_id
                }
            
            # Simula invio SDI (in produzione chiamare API SDI reale)
            try:
                sdi_destination = invoice.customer_sdi or invoice.customer_pec
                
                logger.info(f"SDI: Invio a destinatario {sdi_destination}")
                
                # Genera lotto XML per SDI
                # In produzione: costruire XML FatturaPA conforme
                sdi_id = f"SDI_{invoice.invoice_number}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                
                # Aggiorna stato fattura
                invoice.status = InvoiceStatus.PENDING
                invoice.updated_at = datetime.utcnow()
                
                # Crea record di notifica SDI (se esiste tabella)
                # await create_sdi_notification(db, invoice, sdi_id)
                
                await db.commit()
                
                logger.info(f"SDI: Fattura {invoice_id} inviata con ID {sdi_id}")
                
                return {
                    "success": True,
                    "invoice_id": invoice_id,
                    "sdi_id": sdi_id,
                    "destination": sdi_destination,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"SDI: Errore invio fattura {invoice_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    # Esegue la coroutine asincrona
    import asyncio
    return asyncio.run(_send())


@celery_app.task(bind=True, base=SDITask, name="app.tasks.sdi_tasks.check_sdi_status")
def check_sdi_status(self, sdi_id: str) -> dict:
    """
    Verifica lo stato di una notifica SDI.
    
    Args:
        sdi_id: ID notifica SDI da verificare
        
    Returns:
        dict con stato attuale e storico
    """
    logger.info(f"SDI: Verifica stato notifica {sdi_id}")
    
    async def _check():
        from app.db.session import async_session_maker
        
        async with async_session_maker() as db:
            # In produzione: query tabella sdi_notifications
            # Per ora simula la verifica
            
            try:
                # Simula chiamata API SDI per stato
                # In produzione: chiamare endpoint SDI reale
                
                status_result = {
                    "sdi_id": sdi_id,
                    "status": "delivered",  # delivered, accepted, rejected, error
                    "checked_at": datetime.utcnow().isoformat(),
                    "history": [
                        {"timestamp": datetime.utcnow().isoformat(), "status": "delivered"},
                    ]
                }
                
                logger.info(f"SDI: Stato notifica {sdi_id}: {status_result['status']}")
                return status_result
                
            except Exception as e:
                logger.error(f"SDI: Errore verifica stato {sdi_id}: {e}")
                raise self.retry(exc=e)
    
    import asyncio
    return asyncio.run(_check())


@celery_app.task(bind=True, base=SDITask, name="app.tasks.sdi_tasks.retry_failed_sdi")
def retry_failed_sdi(self) -> dict:
    """
    Ritenta l'invio SDI per tutte le fatture fallite.
    Task eseguito automaticamente ogni ora.
    
    Returns:
        dict con riepilogo operazioni effettuate
    """
    logger.info("SDI: Avvio retry invii falliti")
    
    async def _retry():
        from app.db.session import async_session_maker
        from app.models.invoice import Invoice, InvoiceStatus
        
        async with async_session_maker() as db:
            # Trova fatture con stato FALLITO_SDI o fatture mai inviate oltre 24h
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Fatture con invio SDI fallito
            result = await db.execute(
                select(Invoice).where(
                    and_(
                        Invoice.status == InvoiceStatus.OVERDUE,
                        Invoice.updated_at < cutoff_time
                    )
                )
            )
            failed_invoices = result.scalars().all()
            
            retried = []
            failed = []
            
            for invoice in failed_invoices:
                try:
                    # Ritenta invio
                    logger.info(f"SDI: Retry fattura {invoice.id}")
                    
                    # Chiama send_invoice_to_sdi per questa fattura
                    # In pratica invochiamo il task in modo sincrono qui
                    result_sync = await _send_single_invoice(db, invoice)
                    
                    if result_sync:
                        retried.append(invoice.id)
                    else:
                        failed.append(invoice.id)
                        
                except Exception as e:
                    logger.error(f"SDI: Retry fallito per fattura {invoice.id}: {e}")
                    failed.append(invoice.id)
            
            await db.commit()
            
            logger.info(f"SDI: Retry completato. Ritentati: {len(retried)}, Falliti: {len(failed)}")
            
            return {
                "success": True,
                "retried": retried,
                "failed": failed,
                "total": len(failed_invoices)
            }
    
    import asyncio
    return asyncio.run(_retry())


async def _send_single_invoice(db, invoice) -> bool:
    """
    Helper asincrono per inviare una singola fattura.
    
    Args:
        db: Sessione database
        invoice: Istanza Invoice
        
    Returns:
        True se invio riuscito, False altrimenti
    """
    from app.models.invoice import InvoiceStatus
    
    try:
        if not invoice.customer_sdi and not invoice.customer_pec:
            return False
        
        sdi_destination = invoice.customer_sdi or invoice.customer_pec
        sdi_id = f"SDI_RETRY_{invoice.invoice_number}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        invoice.status = InvoiceStatus.PENDING
        invoice.updated_at = datetime.utcnow()
        
        return True
        
    except Exception:
        return False
