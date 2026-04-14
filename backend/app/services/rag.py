"""
RAG (Retrieval-Augmented Generation) service for Italian fiscal data extraction.
"""
import os
import re
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Italian fiscal knowledge base for RAG
ITALIAN_FISCAL_RULES = """
# Regole Fiscali Italiane - FatturaPA

## Dati Obbligatori Fattura Elettronica

### Cedente/Prestatore (Fornitore)
- Denominazione o Nome+Cognome
- Partita IVA (11 cifre: IT + 11 numeri)
- Sede legale (Indirizzo, CAP, Comune, Provincia)
- Codice Fiscale (16 caratteri per persone fisiche)
- Contatti: Telefono, Email, PEC
- IBAN per bonifici
- Codice SDI (7 caratteri alfanumerici) per fatturazione elettronica

### Cessionario/Committente (Cliente)
- Denominazione o Nome+Cognome
- Partita IVA (11 cifre) oppure Codice Fiscale
- Sede (Indirizzo, CAP, Comune, Provincia)
- PEC o Codice SDI se B2B
- Email (opzionale)

### Dati Generali Fattura
- Numero Fattura (formato libero ma univoco)
- Data Fattura (formato YYYY-MM-DD o DD/MM/YYYY)
- Dati Ritenzione (se applicabile)
- Causale (descrizione servizi/prodotti)

### Dati Pagamento
- Modalità pagamento (es: BB01 = bonifico, MP05 = bollettino)
- Termini pagamento (gg: es: 30GG = 30 giorni)
- Data scadenza pagamento
- IBAN beneficiario

### Dati Riepilogo
- Imponibile (base imponibile IVA)
- Aliquota IVA (es: 22%, 10%, 4%, 0%)
- Importo IVA
- Totale documento

## Codici SDI Standard
- 0000000: non require codice
- 1-6 caratteri: codice pec o codice specifico
- 7 caratteri: codice SDI standard

## Formato Partita IVA
- 11 cifre
- Prime 7 cifre: numero identificativo
- Cifre 8-10: codice oficina
- Cifra 11: check digit (modulo 10)

## Formato Codice Fiscale
- 6 caratteri: cognome (3) + nome (3)
- 2 cifre: anno nascita
- Lettera: mese nascita (A=gen, B=feb, C=mar, D=apr, E=mag, H=giu, L=lug, M=ago, P=set, R=ott, S=nov, T=dic)
- 2 cifre: giorno nascita + comune/stato estero
- 4 caratteri: codice catastale
- Lettera: check digit
"""


class RAGExtractor:
    """
    RAG-based extractor for Italian fiscal data.
    Uses knowledge base + pattern matching + AI (optional).
    """

    def __init__(self):
        self.knowledge_base = ITALIAN_FISCAL_RULES
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for extraction."""
        self.patterns = {
            "piva": [
                r'IT\s*(\d{11})',
                r'Partita\s*(?:IVA|I\.V\.A\.?)[:\s]*(\d{11})',
                r'P\.?I\.?[:\s]*(\d{11})',
            ],
            "cf": [
                r'\b([A-Z]{6}[0-9LMNPQRSTUVlmnpqrstuv]{2}[A-Z][0-9LMNPQRSTUVlmnpqrstuv]{2}[A-Z][0-9LMNPQRSTUVlmnpqrstuv]{3}[A-Z])\b',
            ],
            "phone": [
                r'\+39[\s\.]?(\d{2,4})[\s\.]?(\d{3,4})[\s\.]?(\d{3,4})',
                r'00\d{2}[\s\.]?\d{3,4}[\s\.]?\d{3,4}',
                r'(?:tel|fono|cell|cellular)[:\s]*(\+?39?\s*\d{2,4}[\s\.]?\d{3,4}[\s\.]?\d{3,4})',
            ],
            "pec": [
                r'([a-zA-Z0-9._%+-]+@pec\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            ],
            "email": [
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?!.*pec))',
            ],
            "sdi": [
                r'(?i)Codice(?:e)?\s*Destinatario[:\s]*([A-Z0-9]{7})',
                r'(?i)SDI[:\s]*([A-Z0-9]{6,7})',
                r'(?i)Cod\.?\s*SDI[:\s]*([A-Z0-9]{6,7})',
            ],
            "iban": [
                r'(?i)IBAN[:\s]*([A-Z]{2}\d{2}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{2,3})',
                r'(IT\d{2}[\s]?[A-Z0-9]{30,34})',
            ],
            "invoice_number": [
                r'(?:Nr?|Numero|Fattura)[:\s]*([A-Z0-9/\-\.]+)',
            ],
            "amount": [
                r'[€$]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
                r'Totale[:\s]*[€$]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            ],
            "vat": [
                r'IVA[:\s]*(\d+(?:[.,]\d+)?)\s*%',
                r'Aliquota[:\s]*(\d+(?:[.,]\d+)?)\s*%',
            ],
        }

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract structured data from plain text using patterns + rules."""
        result = {}

        # PIVA
        for pattern in self.patterns["piva"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["piva"] = match.group(1).replace(" ", "").replace(".", "")
                break

        # CF
        for pattern in self.patterns["cf"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cf = match.group(1).upper()
                if len(cf) == 16:
                    result["cf"] = cf
                    break

        # Phone
        for pattern in self.patterns["phone"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phone = match.group(0)
                result["phone"] = re.sub(r'[^\d\+]', '', phone)
                break

        # PEC
        for pattern in self.patterns["pec"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["pec"] = match.group(1).lower()
                break

        # Email
        for pattern in self.patterns["email"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                email = match.group(1).lower()
                if "pec" not in email and email not in result.get("pec", ""):
                    result["email"] = email
                    break

        # SDI
        for pattern in self.patterns["sdi"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sdi = re.sub(r'[^A-Z0-9]', '', match.group(1).upper())
                if 6 <= len(sdi) <= 7:
                    result["sdi"] = sdi
                    break

        # IBAN
        for pattern in self.patterns["iban"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                iban = match.group(1).upper().replace(" ", "").replace(".", "")
                if iban.startswith("IT"):
                    result["iban"] = iban
                    break

        return result

    def enrich_invoice_data(self, invoice_data: Dict[str, Any], xml_content: str = "") -> Dict[str, Any]:
        """
        Enrich invoice data using RAG extraction.
        Combines parsed XML data with pattern-based extraction from raw text.
        """
        import xml.etree.ElementTree as ET

        enriched = invoice_data.copy()

        # If we have raw XML, extract text and enrich
        if xml_content:
            try:
                root = ET.fromstring(xml_content)
                text = ET.tostring(root, encoding='unicode', method='text')
                extracted = self.extract_from_text(text)

                # Merge extracted data (only if not already present)
                for key, value in extracted.items():
                    # Map to customer/supplier fields
                    if key == "piva":
                        if not enriched.get("customer_vat") and value:
                            enriched["customer_vat"] = value
                        if not enriched.get("supplier_vat") and value:
                            enriched["supplier_vat"] = value
                    elif key in ["cf", "phone", "pec", "email", "sdi", "iban"]:
                        # Try to determine if customer or supplier
                        # (In production, would use position in XML)
                        if "customer" not in enriched or not enriched.get(f"customer_{key}"):
                            enriched[f"customer_{key}"] = value
                        if "supplier" not in enriched or not enriched.get(f"supplier_{key}"):
                            enriched[f"supplier_{key}"] = value

            except ET.ParseError as e:
                logger.warning(f"Failed to parse XML for enrichment: {e}")

        return enriched


async def extract_with_rag(
    invoice_data: Dict[str, Any],
    xml_content: str = "",
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Main RAG extraction function.
    Uses pattern-based extraction first, then AI if available.
    """
    rag = RAGExtractor()

    # Extract with patterns
    enriched = rag.enrich_invoice_data(invoice_data, xml_content)

    # Optionally enhance with AI
    if use_ai:
        ai_data = await _extract_with_ai_api(xml_content)
        if ai_data:
            # Merge AI data (prefer non-empty values)
            for key, value in ai_data.items():
                if value and key not in enriched:
                    enriched[key] = value

    return enriched


async def _extract_with_ai_api(xml_content: str) -> Optional[Dict[str, Any]]:
    """Extract using AI API (OpenAI/Anthropic/MiniMax)."""
    from app.core.config import settings
    import httpx

    if not xml_content:
        return None

    # Try MiniMax first (as per Vi preference)
    if settings.MINIMAX_API_KEY:
        try:
            return await _extract_with_minimax(xml_content)
        except Exception as e:
            logger.warning(f"MiniMax extraction failed: {e}")

    # Fallback to OpenAI
    if settings.OPENAI_API_KEY:
        try:
            return await _extract_with_openai(xml_content)
        except Exception as e:
            logger.warning(f"OpenAI extraction failed: {e}")

    return None


async def _extract_with_openai(xml_content: str) -> Dict[str, Any]:
    """Extract using OpenAI API."""
    from app.core.config import settings
    import httpx

    prompt = f"""Sei un assistente specializzato nell'estrazione di dati da fatture XML italiane (FatturaPA).

Basandoti sul seguente testo della fattura, estrai i dati mancanti.
Rispondi SOLO con un JSON valido con questi campi possibili:
- customer_phone, customer_pec, customer_sdi, customer_cf
- supplier_phone, supplier_pec, supplier_iban, supplier_sdi, supplier_cf

Testo fattura:
{xml_content[:6000]}

Risposta JSON (solo campi trovati):"""

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 300,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())

    return {}


async def _extract_with_minimax(xml_content: str) -> Dict[str, Any]:
    """Extract using MiniMax API."""
    from app.core.config import settings
    import httpx

    prompt = f"""Estrai i seguenti dati da questa fattura XML italiana.
Rispondi SOLO con JSON valido:

Campi: customer_phone, customer_pec, customer_sdi, customer_cf, supplier_phone, supplier_pec, supplier_iban, supplier_sdi, supplier_cf

Testo fattura:
{xml_content[:6000]}

Risposta JSON:"""

    headers = {
        "Authorization": f"Bearer {settings.MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "MiniMax-Text-01",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 300,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.MINIMAX_BASE_URL}/text/chatcompletion_v2",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())

    return {}
