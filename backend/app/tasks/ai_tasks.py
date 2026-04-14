"""
Task Celery per operazioni AI.
Include: generazione solleciti AI, calcolo trust scores, caching.
"""
from app.tasks.celery_app import celery_app
from celery import Task
import logging
import json
import hashlib
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class AITask(Task):
    """Task base con retry automatico per operazioni AI."""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(bind=True, base=AITask, name="app.tasks.ai_tasks.generate_and_cache_sollecito")
def generate_and_cache_sollecito(self, invoice_id: int = None) -> dict:
    """
    Genera sollecito AI e lo mette in cache per 24h.
    Se invoice_id è None, processa tutte le fatture scadute non sollecitate.
    
    Args:
        invoice_id: ID fattura opzionale (None = processa tutte le scadute)
        
    Returns:
        dict con sollecito generato e cache info
    """
    logger.info(f"AI: Generazione sollecito per fattura {invoice_id}")
    
    async def _generate():
        from app.db.session import async_session_maker
        from app.models.invoice import Invoice, InvoiceStatus
        from app.core.config import settings
        import redis
        import httpx
        
        # Connessione Redis per cache
        redis_client = redis.from_url(settings.REDIS_URL)
        
        async with async_session_maker() as db:
            # Costruisce query
            if invoice_id:
                query = select(Invoice).where(Invoice.id == invoice_id)
            else:
                # Tutte le fatture scadute da oltre 7 giorni senza sollecito recente
                cutoff = date.today() - timedelta(days=7)
                query = select(Invoice).where(
                    and_(
                        Invoice.due_date < cutoff,
                        Invoice.status == InvoiceStatus.OVERDUE
                    )
                )
            
            result = await db.execute(query)
            invoices = result.scalars().all()
            
            generated = []
            cached = []
            errors = []
            
            for invoice in invoices:
                try:
                    # Check se gia' in cache
                    cache_key = f"sollecito:invoice:{invoice.id}"
                    cached_data = redis_client.get(cache_key)
                    
                    if cached_data:
                        logger.info(f"AI: Sollecito gia' in cache per fattura {invoice.id}")
                        cached.append(invoice.id)
                        continue
                    
                    # Genera sollecito AI
                    sollecito_text = await _generate_sollecito_ai(invoice, db)
                    
                    # Salva in cache per 24h
                    cache_data = {
                        "invoice_id": invoice.id,
                        "sollecito": sollecito_text,
                        "generated_at": datetime.utcnow().isoformat(),
                        "invoice_number": invoice.invoice_number,
                        "customer_name": invoice.customer_name,
                        "total_amount": invoice.total_amount,
                    }
                    
                    redis_client.setex(
                        cache_key,
                        timedelta(hours=24),
                        json.dumps(cache_data)
                    )
                    
                    generated.append({
                        "invoice_id": invoice.id,
                        "invoice_number": invoice.invoice_number,
                        "sollecito_preview": sollecito_text[:100] + "..."
                    })
                    
                    logger.info(f"AI: Sollecito generato e cache per fattura {invoice.id}")
                    
                except Exception as e:
                    logger.error(f"AI: Errore generazione sollecito {invoice.id}: {e}")
                    errors.append({"invoice_id": invoice.id, "error": str(e)})
            
            redis_client.close()
            
            logger.info(f"AI: Sollecito completato. Generati: {len(generated)}, Cached: {len(cached)}, Errori: {len(errors)}")
            
            return {
                "success": True,
                "generated": len(generated),
                "cached": len(cached),
                "errors": len(errors),
                "details": {
                    "generated_invoices": generated,
                    "cached_invoices": cached,
                    "error_details": errors
                }
            }
    
    import asyncio
    return asyncio.run(_generate())


@celery_app.task(bind=True, base=AITask, name="app.tasks.ai_tasks.update_trust_scores")
def update_trust_scores(self) -> dict:
    """
    Aggiorna trust score di tutti i clienti basato su storico pagamenti.
    Calcola nuovo score basato su:
    - Puntualita' pagamenti recenti
    - Numero di ritardi
    - Importo medio fatture
    - Pattern di pagamento
    
    Returns:
        dict con riepilogo aggiornamenti
    """
    logger.info("AI: Avvio aggiornamento trust scores")
    
    async def _update():
        from app.db.session import async_session_maker
        from app.models.client import Client, PaymentHistory
        from sqlalchemy import select, func
        
        async with async_session_maker() as db:
            # Recupera tutti i clienti
            result = await db.execute(select(Client))
            clients = result.scalars().all()
            
            updated = []
            errors = []
            
            for client in clients:
                try:
                    # Calcola statistiche pagamento per questo cliente
                    stats = await _calculate_payment_stats(db, client.id)
                    
                    if stats is None:
                        continue
                    
                    # Calcola nuovo trust score
                    new_score = _calculate_trust_score(stats, client.is_new)
                    
                    # Aggiorna cliente
                    client.trust_score = new_score
                    client.payment_pattern = stats.get("pattern", "unknown")
                    client.updated_at = datetime.utcnow()
                    
                    # Se nuovo cliente e ha pagato in tempo, marca come non nuovo
                    if client.is_new and stats.get("on_time_ratio", 1.0) >= 0.8:
                        client.is_new = False
                    
                    updated.append({
                        "client_id": client.id,
                        "name": client.name,
                        "old_score": client.trust_score,
                        "new_score": new_score,
                        "pattern": stats.get("pattern", "unknown")
                    })
                    
                except Exception as e:
                    logger.error(f"AI: Errore aggiornamento trust score cliente {client.id}: {e}")
                    errors.append({"client_id": client.id, "error": str(e)})
            
            await db.commit()
            
            logger.info(f"AI: Trust scores aggiornati. Aggiornati: {len(updated)}, Errori: {len(errors)}")
            
            return {
                "success": True,
                "updated": len(updated),
                "errors": len(errors),
                "details": updated[:50]  # Limita output
            }
    
    import asyncio
    return asyncio.run(_update())


# =============================================================================
# HELPERS - Generazione AI
# =============================================================================

async def _generate_sollecito_ai(invoice, db) -> str:
    """
    Genera testo sollecito usando AI.
    Usa fallback pattern -> OpenAI -> Anthropic -> MiniMax.
    """
    from app.core.config import settings
    import httpx
    
    # Recupera dati business config per stile
    from app.models.client import BusinessConfig
    from sqlalchemy import select
    
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()
    
    style = config.style if config else "gentile"
    
    # Costruisce prompt
    prompt = _build_sollecito_prompt(invoice, style)
    
    # Tenta generazione con vari provider AI
    providers = [
        ("openai", _call_openai),
        ("anthropic", _call_anthropic),
        ("minimax", _call_minimax),
    ]
    
    for provider_name, provider_func in providers:
        try:
            result_text = await provider_func(prompt, settings)
            if result_text:
                return result_text
        except Exception as e:
            logger.warning(f"AI: Provider {provider_name} fallito: {e}")
            continue
    
    # Fallback: genera template locale
    return _generate_template_sollecito(invoice, style)


def _build_sollecito_prompt(invoice, style: str) -> str:
    """Costruisce prompt per generazione sollecito AI."""
    
    style_instructions = {
        "gentile": "Tonо gentile e cortese, focale sul rapporto commerciale. Accogliente ma fermo.",
        "equilibrato": "Tonо professionale e neutrale. Chiaro ma rispettoso.",
        "fermo": "Tonо deciso e professionale. Richiesta esplicita di pagamento."
    }.get(style, "")
    
    prompt = f"""Genera un sollecito di pagamento professionale in italiano.

DATI FATTURA:
- Numero: {invoice.invoice_number}
- Importo: €{invoice.total_amount:,.2f}
- Data fattura: {invoice.invoice_date.strftime('%d/%m/%Y')}
- Data scadenza: {invoice.due_date.strftime('%d/%m/%Y')}
- Cliente: {invoice.customer_name}
- P.IVA cliente: {invoice.customer_vat or 'N/D'}

ISTRUZIONI DI STILE:
{style_instructions}

Il sollecito deve:
1. Iniziare con un saluto cortese
2. Identificare chiaramente la fattura
3. Richiedere il pagamento
4. Includere IBAN per bonifico: {invoice.supplier_iban or 'N/D'}
5. Terminare con formula di cortesia

Rispondi SOLO con il testo del sollecito, senza spiegazioni aggiuntive.
"""
    
    return prompt


async def _call_openai(prompt: str, settings) -> str:
    """Chiama OpenAI per generazione."""
    import httpx
    
    if not settings.OPENAI_API_KEY:
        raise Exception("OpenAI API key non configurata")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI error: {response.status_code}")
        
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


async def _call_anthropic(prompt: str, settings) -> str:
    """Chiama Anthropic per generazione."""
    import httpx
    
    if not settings.ANTHROPIC_API_KEY:
        raise Exception("Anthropic API key non configurata")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic error: {response.status_code}")
        
        data = response.json()
        return data["content"][0]["text"].strip()


async def _call_minimax(prompt: str, settings) -> str:
    """Chiama MiniMax per generazione (fallback)."""
    import httpx
    
    if not settings.MINIMAX_API_KEY:
        raise Exception("MiniMax API key non configurata")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.MINIMAX_BASE_URL}/text/chatcompletion_pro",
            headers={
                "Authorization": f"Bearer {settings.MINIMAX_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "abab5.5-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise Exception(f"MiniMax error: {response.status_code}")
        
        data = response.json()
        return data["choices"][0]["text"].strip()


def _generate_template_sollecito(invoice, style: str) -> str:
    """Genera sollecito template locale (fallback senza AI)."""
    
    if style == "gentile":
        saluto = "Gentile Cliente,"
        chiusura = "Confidiamo nel Vs. sollecito pagamento e porgiamo cordiali saluti."
    elif style == "fermo":
        saluto = "Spett.le Cliente,"
        chiusura = "In caso di mancato pagamento entro il termine indicato, saremo costretti a intraprendere le dovute azioni."
    else:
        saluto = "Egregio Cliente,"
        chiusura = "Restiamo in attesa di un Vs. cortese riscontro entro 7 giorni."
    
    iban_line = f"\n\nCoordinate bancarie per il pagamento:\nIBAN: {invoice.supplier_iban or 'N/D'}" if invoice.supplier_iban else ""
    
    text = f"""{saluto}

con la presente Vi informiamo che la fattura sotto indicata risulta ad oggi non saldata:

• Numero fattura: {invoice.invoice_number}
• Data fattura: {invoice.invoice_date.strftime('%d/%m/%Y')}
• Data scadenza: {invoice.due_date.strftime('%d/%m/%Y')}
• Importo: €{invoice.total_amount:,.2f}
• Vs. Ragione sociale: {invoice.customer_name}
• Vs. P.IVA: {invoice.customer_vat or 'N/D'}

{iban_line}

{chiusura}

Distinti saluti
"""
    
    return text


# =============================================================================
# HELPERS - Trust Score
# =============================================================================

async def _calculate_payment_stats(db, client_id: int) -> dict:
    """Calcola statistiche pagamento per un cliente."""
    from app.models.payment_history import PaymentHistory
    from sqlalchemy import select, func
    
    result = await db.execute(
        select(PaymentHistory).where(PaymentHistory.client_id == client_id)
    )
    histories = result.scalars().all()
    
    if not histories:
        return None
    
    total = len(histories)
    on_time = sum(1 for h in histories if h.was_on_time)
    late_count = sum(1 for h in histories if not h.was_on_time)
    total_days_late = sum(h.days_late for h in histories)
    avg_amount = sum(h.invoice_amount for h in histories) / total if total > 0 else 0
    
    # Determina pattern
    if on_time / total >= 0.9:
        pattern = "ottimo"  # >90% puntuale
    elif on_time / total >= 0.7:
        pattern = "buono"  # >70% puntuale
    elif on_time / total >= 0.5:
        pattern = "mediocre"  # >50% puntuale
    else:
        pattern = "scarso"  # <50% puntuale
    
    return {
        "total_invoices": total,
        "on_time": on_time,
        "late": late_count,
        "on_time_ratio": on_time / total if total > 0 else 1.0,
        "avg_days_late": total_days_late / late_count if late_count > 0 else 0,
        "avg_amount": avg_amount,
        "pattern": pattern
    }


def _calculate_trust_score(stats: dict, is_new: bool) -> int:
    """
    Calcola trust score basato su statistiche.
    Score finale: 0-100
    """
    from app.core.config import settings
    
    base_score = settings.NEW_CLIENT_SCORE if is_new else 50
    
    # Modificatori
    modifiers = []
    
    # Bonus per puntualita'
    on_time_ratio = stats.get("on_time_ratio", 1.0)
    if on_time_ratio >= 0.95:
        modifiers.append(20)
    elif on_time_ratio >= 0.85:
        modifiers.append(15)
    elif on_time_ratio >= 0.70:
        modifiers.append(5)
    elif on_time_ratio < 0.50:
        modifiers.append(-20)
    
    # Penalty per ritardi frequenti
    late_ratio = 1 - on_time_ratio
    if late_ratio > 0.3:
        modifiers.append(-15)
    if late_ratio > 0.5:
        modifiers.append(-10)
    
    # Bonus per avg amount elevato (clienti importanti)
    avg_amount = stats.get("avg_amount", 0)
    if avg_amount > 5000:
        modifiers.append(10)
    elif avg_amount > 2000:
        modifiers.append(5)
    
    # Calcola score finale
    final_score = base_score + sum(modifiers)
    
    # Limita range 0-100
    return max(0, min(100, final_score))
