"""
SDI Service - Wrapper per OpenAPI Sistema di Interscambio.

Documentazione: https://console.openapi.com/it/apis/sdi

Funzionalita:
- Invio fatture a SDI (Sistema di Interscambio dell'Agenzia delle Entrate)
- Verifica stato di una fattura inviata
- Gestione webhook per notifiche da SDI
- Lista fatture inviate con filtri

Il SDI e' il sistema centrale che gestisce la fatturazione elettronica
in Italia. Le fatture vengono trasmesse tramite PEC o web service.
"""
import httpx
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)


class SDIError(Exception):
    """Errore generico SDI."""
    pass


class SDIAuthError(SDIError):
    """Errore di autenticazione SDI."""
    pass


class SDIValidationError(SDIError):
    """Errore di validazione fattura SDI."""
    pass


class SDINotFoundError(SDIError):
    """Fattura non trovata su SDI."""
    pass


class OpenAPISDI:
    """
    Client per il Sistema di Interscambio (SDI).

    Utilizza l'OpenAPI SDI per comunicare con il sistema dell'Agenzia delle Entrate.
    La configurazione API key viene gestita tramite settings.

    Supporta retry automatico (3 tentativi) per errori transienti.
    Ogni chiamata viene loggata con dettagli completi.
    """

    MAX_RETRIES: int = 3

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.sdi.openapi.it/v1",
        timeout: int = 30,
    ):
        """
        Inizializza il client SDI.

        Args:
            api_key: API key per OpenAPI SDI (opzionale, usa settings se non fornita)
            base_url: URL base dell'API SDI
            timeout: Timeout in secondi per le richieste
        """
        self.api_key = api_key or getattr(settings, 'SDI_API_KEY', None)
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Ottiene o crea un client HTTP condiviso."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                headers["X-API-Key"] = self.api_key

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Chiude il client HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Esegue una richiesta HTTP all'API SDI con retry automatico.

        Args:
            method: Metodo HTTP (GET, POST, etc.)
            path: Path dell'endpoint
            data: Body JSON per POST/PUT
            params: Query parameters
            retry_count: Contatore retry interno

        Returns:
            Risposta JSON come dizionario

        Raises:
            SDIError: In caso di errore
        """
        client = await self._get_client()
        timestamp = datetime.utcnow().isoformat()

        logger.info(
            f"[SDI] Chiamata API: {method} {path}",
            extra={
                "sdi_method": method,
                "sdi_path": path,
                "sdi_timestamp": timestamp,
                "sdi_retry": retry_count,
                "sdi_has_data": data is not None,
                "sdi_has_params": params is not None,
            }
        )

        try:
            response = await client.request(
                method=method,
                url=path,
                json=data,
                params=params,
            )

            logger.info(
                f"[SDI] Risposta: {response.status_code}",
                extra={
                    "sdi_method": method,
                    "sdi_path": path,
                    "sdi_status_code": response.status_code,
                    "sdi_timestamp": timestamp,
                    "sdi_retry": retry_count,
                }
            )

            if response.status_code == 401:
                logger.error(f"[SDI] Errore autenticazione 401")
                raise SDIAuthError("Autenticazione SDI fallita. Verificare API key.")

            if response.status_code == 404:
                logger.warning(f"[SDI] Risorsa non trovata: {path}")
                raise SDINotFoundError("Risorsa non trovata su SDI")

            if response.status_code == 422:
                error_data = response.json()
                logger.error(f"[SDI] Validazione fallita: {error_data}")
                raise SDIValidationError(
                    f"Validazione fallita: {error_data.get('detail', 'Errore sconosciuto')}"
                )

            if not response.is_success:
                logger.error(f"[SDI] Errore {response.status_code}: {response.text}")
                raise SDIError(
                    f"Errore SDI {response.status_code}: {response.text}"
                )

            result = response.json()
            logger.info(
                f"[SDI] Successo",
                extra={
                    "sdi_method": method,
                    "sdi_path": path,
                    "sdi_status_code": response.status_code,
                    "sdi_timestamp": timestamp,
                    "sdi_result_keys": list(result.keys()) if isinstance(result, dict) else None,
                }
            )
            return result

        except (SDIAuthError, SDINotFoundError, SDIValidationError):
            # Errori non retryable - rilancio immediatamente
            raise

        except (httpx.TimeoutException, httpx.RequestError) as e:
            if retry_count < self.MAX_RETRIES:
                wait_time = (2 ** retry_count) * 1.0  # exponential backoff
                logger.warning(
                    f"[SDI] Retry {retry_count + 1}/{self.MAX_RETRIES} dopo {wait_time}s: {e}",
                    extra={
                        "sdi_method": method,
                        "sdi_path": path,
                        "sdi_error": str(e),
                        "sdi_retry": retry_count + 1,
                    }
                )
                await asyncio.sleep(wait_time)
                return await self._request(method, path, data, params, retry_count + 1)
            else:
                logger.error(f"[SDI] Errore dopo {self.MAX_RETRIES} tentativi: {e}")
                raise SDIError(f"Errore di rete SDI dopo {self.MAX_RETRIES} tentativi: {str(e)}")

        except SDIError:
            # SDIError generico - retry se non e' gia un retry
            if retry_count < self.MAX_RETRIES:
                wait_time = (2 ** retry_count) * 1.0
                logger.warning(
                    f"[SDI] Retry SDIError {retry_count + 1}/{self.MAX_RETRIES}: {str(e)}"
                )
                await asyncio.sleep(wait_time)
                return await self._request(method, path, data, params, retry_count + 1)
            raise

    async def send_invoice(self, xml_content: str) -> Dict[str, Any]:
        """
        Invia una fattura XML al Sistema di Interscambio.

        Args:
            xml_content: Contenuto XML della fattura FatturaPA

        Returns:
            Dizionario con:
            - sdi_id: Identificativo SDI della fattura
            - status: Stato dell'invio
            - receipt_id: ID ricevuta (se disponibile)

        Raises:
            SDIError: In caso di errore nell'invio
        """
        logger.info(
            f"[SDI] send_invoice chiamata",
            extra={"xml_length": len(xml_content)}
        )

        payload = {
            "invoice": {
                "xml_content": xml_content,
            },
            "options": {
                "synchronous": False,
            }
        }

        result = await self._request("POST", "/invoices/send", data=payload)
        logger.info(f"[SDI] send_invoice result: {result}")
        return result

    async def get_status(self, sdi_id: str) -> Dict[str, Any]:
        """
        Verifica lo stato di una fattura inviata a SDI.

        Args:
            sdi_id: Identificativo SDI della fattura

        Returns:
            Dizionario con:
            - sdi_id: Identificativo SDI
            - status: Stato attuale (draft, sent, delivered, accepted, rejected)
            - timestamps: Date rilevanti
            - error: Messaggio errore (se presente)

        Raises:
            SDIError: In caso di errore
        """
        logger.info(f"[SDI] get_status chiamata per sdi_id={sdi_id}")
        result = await self._request("GET", f"/invoices/{sdi_id}/status")
        logger.info(f"[SDI] get_status result: {result}")
        return result

    async def get_invoices(self) -> List[Dict[str, Any]]:
        """
        Lista tutte le fatture inviate a SDI.

        Returns:
            Lista di dizionari con i dettagli delle fatture

        Raises:
            SDIError: In caso di errore
        """
        logger.info(f"[SDI] get_invoices chiamata")
        result = await self._request("GET", "/invoices")
        items = result.get("items", result) if isinstance(result, dict) else result
        logger.info(f"[SDI] get_invoices result: {len(items) if items else 0} fatture")
        return items


# === Backward compatibility alias ===
SDIService = OpenAPISDI


# === Schemi Pydantic per SDI ===

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SDISendRequest(BaseModel):
    """Request per invio fattura a SDI."""
    invoice_id: int = Field(..., description="ID della fattura nel sistema")
    recipient_sdi: Optional[str] = Field(
        None,
        max_length=7,
        description="Codice SDI del destinatario (6-7 caratteri)"
    )
    recipient_pec: Optional[str] = Field(
        None,
        max_length=255,
        description="PEC del destinatario"
    )
    synchronous: bool = Field(
        False,
        description="Se True, attende risposta sincrona"
    )


class SDISendResponse(BaseModel):
    """Response dopo invio a SDI."""
    success: bool
    sdi_id: Optional[str] = None
    status: str
    message: str
    sdi_record_id: Optional[int] = None


class SDIStatusResponse(BaseModel):
    """Response stato fattura SDI."""
    sdi_id: str
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SDIWebhookPayload(BaseModel):
    """Payload ricevuto dal webhook SDI."""
    sdi_id: str
    invoice_id: str
    status: str
    receipt_id: Optional[str] = None
    receipt_date: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime


class SDIInvoiceResponse(BaseModel):
    """Response per lista fatture SDI."""
    id: int
    invoice_id: int
    invoice_number: Optional[str] = None
    sdi_id: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# === Funzioni helper per operazioni SDI con database ===

async def create_sdi_record(
    db: "AsyncSession",
    invoice_id: int,
    tenant_id: Optional[int],
    xml_content: str,
    sdi_id: Optional[str] = None,
    status: str = "draft",
) -> "SDIInvoice":
    """
    Crea un record SDIInvoice nel database.

    Args:
        db: Sessione database
        invoice_id: ID della fattura
        tenant_id: ID del tenant
        xml_content: Contenuto XML della fattura
        sdi_id: Identificativo SDI (se gia' assegnato)
        status: Stato iniziale

    Returns:
        Record SDIInvoice creato
    """
    from app.models.database import SDIInvoice

    sdi_invoice = SDIInvoice(
        invoice_id=invoice_id,
        tenant_id=tenant_id,
        xml_content=xml_content,
        sdi_id=sdi_id,
        status=status,
    )
    db.add(sdi_invoice)
    await db.commit()
    await db.refresh(sdi_invoice)
    return sdi_invoice


async def update_sdi_status(
    db: "AsyncSession",
    sdi_record_id: int,
    status: str,
    sdi_id: Optional[str] = None,
    error_message: Optional[str] = None,
    **kwargs,
) -> "SDIInvoice":
    """
    Aggiorna lo stato di un record SDIInvoice.

    Args:
        db: Sessione database
        sdi_record_id: ID del record SDIInvoice
        status: Nuovo stato
        sdi_id: Identificativo SDI (opzionale)
        error_message: Messaggio errore (opzionale)
        **kwargs: Altri campi da aggiornare (sent_at, delivered_at, etc.)

    Returns:
        Record SDIInvoice aggiornato
    """
    from app.models.database import SDIInvoice
    from sqlalchemy import select

    result = await db.execute(
        select(SDIInvoice).where(SDIInvoice.id == sdi_record_id)
    )
    sdi_invoice = result.scalar_one_or_none()

    if not sdi_invoice:
        raise ValueError(f"SDIInvoice {sdi_record_id} non trovato")

    sdi_invoice.status = status
    if sdi_id:
        sdi_invoice.sdi_id = sdi_id
    if error_message:
        sdi_invoice.error_message = error_message

    now = datetime.utcnow()
    if status == "sent":
        sdi_invoice.sent_at = now
    elif status == "delivered":
        sdi_invoice.delivered_at = now
    elif status == "accepted":
        sdi_invoice.accepted_at = now
    elif status == "rejected":
        sdi_invoice.rejected_at = now

    for key, value in kwargs.items():
        if hasattr(sdi_invoice, key):
            setattr(sdi_invoice, key, value)

    await db.commit()
    await db.refresh(sdi_invoice)
    return sdi_invoice


# === Singleton per l'applicazione ===
_sdi_service_instance: Optional[OpenAPISDI] = None


def get_sdi_service() -> OpenAPISDI:
    """Restituisce l'istanza singleton del servizio SDI."""
    global _sdi_service_instance
    if _sdi_service_instance is None:
        _sdi_service_instance = OpenAPISDI()
    return _sdi_service_instance
