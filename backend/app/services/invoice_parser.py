"""
FatturaPA XML Parser Service.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from defusedxml import ElementTree as DefusedET


class InvoiceParserError(Exception):
    """Raised when XML parsing fails."""
    pass


def _get_namespace(root: ET.Element) -> str:
    """Extract namespace from root element."""
    tag = root.tag
    if tag.startswith('{'):
        return '{' + tag.split('}')[0].lstrip('{') + '}'
    return ''


def _extract_with_pattern(text: str, patterns: list) -> str:
    """Extract a value using regex patterns."""
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            val = matches[0] if isinstance(matches[0], str) else str(matches[0])
            return val.strip()
    return ''


def parse_invoice_xml(xml_content: str) -> Dict[str, Any]:
    """
    Parse FatturaPA XML and extract invoice data.
    """
    try:
        if isinstance(xml_content, bytes):
            if xml_content.startswith(b'\xef\xbb\xbf'):
                xml_content = xml_content[3:]
            xml_content = xml_content.decode('utf-8')

        xml_content = xml_content.strip()
        if not xml_content:
            raise InvoiceParserError("Empty XML content")

        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise InvoiceParserError(f"XML parsing failed: {e}")

    ns = _get_namespace(root)
    raw_text = ET.tostring(root, encoding='unicode', method='text')

    result = {'raw_xml': xml_content}

    # Find body and header
    body = root.find(f'.//{ns}FatturaElettronicaBody')
    header = root.find(f'.//{ns}FatturaElettronicaHeader')

    if body is None:
        raise InvoiceParserError("Missing FatturaElettronicaBody")

    # Parse supplier
    if header is not None:
        result.update(_parse_supplier(header, ns, raw_text))

    # Parse customer
    if header is not None:
        result.update(_parse_customer(header, ns, raw_text))

    # Parse invoice info
    result.update(_parse_invoice_info(body, ns))

    # Parse payment
    result.update(_parse_payment(body, ns, result.get('invoice_date')))

    # Defaults
    if not result.get('invoice_number'):
        result['invoice_number'] = f"UNKNOWN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    if not result.get('customer_name'):
        result['customer_name'] = 'Cliente sconosciuto'
    if not result.get('due_date'):
        result['due_date'] = date.today() + timedelta(days=30)

    # Normalize dates
    result['invoice_date'] = _normalize_date(result.get('invoice_date', ''))
    result['due_date'] = _normalize_date(result.get('due_date', ''))

    # Ensure numeric
    result['amount'] = float(result.get('amount') or 0)
    result['vat_amount'] = float(result.get('vat_amount') or 0)
    result['total_amount'] = float(result.get('total_amount') or 0)

    result.setdefault('status', 'pending')

    return result


def _parse_supplier(header: ET.Element, ns: str, raw_text: str = '') -> Dict[str, str]:
    """Parse supplier/cedente data."""
    result = {}

    cedente = header.find(f'{ns}CedentePrestatore')
    if cedente is None:
        return result

    dati_ana = cedente.find(f'{ns}DatiAnagrafici')
    if dati_ana is not None:
        id_fisc = dati_ana.find(f'{ns}IdFiscaleIVA')
        if id_fisc is not None:
            paese = id_fisc.findtext(f'{ns}IdPaese', '')
            codice = id_fisc.findtext(f'{ns}IdCodice', '')
            result['supplier_vat'] = f"{paese}{codice}"

        denom = dati_ana.findtext(f'{ns}Denominazione')
        if not denom:
            nome = dati_ana.findtext(f'{ns}Nome', '')
            cognome = dati_ana.findtext(f'{ns}Cognome', '')
            denom = f"{nome} {cognome}".strip()
        result['supplier_name'] = denom or ''

        email = dati_ana.findtext(f'{ns}Email', '')
        if email:
            result['supplier_email'] = email

        contatti = dati_ana.find(f'{ns}Contatti')
        if contatti is not None:
            telefono = contatti.findtext(f'{ns}Telefono', '')
            if telefono:
                result['supplier_phone'] = telefono

    sede = cedente.find(f'{ns}Sede')
    if sede is not None:
        indirizzo = sede.findtext(f'{ns}Indirizzo', '')
        civico = sede.findtext(f'{ns}NumeroCivico', '')
        cap = sede.findtext(f'{ns}CAP', '')
        comune = sede.findtext(f'{ns}Comune', '')
        provincia = sede.findtext(f'{ns}Provincia', '')
        parts = [x for x in [f"{indirizzo} {civico}".strip(), cap, comune, provincia] if x]
        result['supplier_address'] = ', '.join(parts)

    # Pattern-based extraction
    if raw_text:
        phone_patterns = [
            r'(?i)(?:tel|fono|cell)[:\s]*(\+?39?\s*\d{2,4}[\s\.]?\d{3,4}[\s\.]?\d{3,4})',
        ]
        if not result.get('supplier_phone'):
            result['supplier_phone'] = _extract_with_pattern(raw_text, phone_patterns)

        pec_patterns = [r'([a-zA-Z0-9._%+-]+@pec\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})']
        result['supplier_pec'] = _extract_with_pattern(raw_text, pec_patterns)

        iban_patterns = [
            r'(?i)iban[:\s]*([A-Z]{2}\d{2}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{2,3})',
            r'(IT\d{2}[\s]?[A-Z0-9]{30,34})',
        ]
        iban = _extract_with_pattern(raw_text, iban_patterns)
        if iban:
            result['supplier_iban'] = iban.replace(' ', '').replace('.', '').upper()

        sdi_patterns = [r'(?i)codicedestinatario[:\s]*([A-Z0-9]{6,7})']
        sdi = _extract_with_pattern(raw_text, sdi_patterns)
        if sdi:
            result['supplier_sdi'] = re.sub(r'[^A-Z0-9]', '', sdi.upper())[:7]

        cf_patterns = [
            r'\b([A-Z]{6}[0-9LMNPQRSTUVlmnpqrstuv]{2}[A-Z][0-9LMNPQRSTUVlmnpqrstuv]{2}[A-Z][0-9LMNPQRSTUVlmnpqrstuv]{3}[A-Z])\b',
        ]
        cf = _extract_with_pattern(raw_text, cf_patterns)
        if cf:
            result['supplier_cf'] = cf.upper()

    return result


def _parse_customer(header: ET.Element, ns: str, raw_text: str = '') -> Dict[str, str]:
    """Parse customer/committente data."""
    result = {}

    committente = header.find(f'{ns}CessionarioCommittente')
    if committente is None:
        return result

    dati_ana = committente.find(f'{ns}DatiAnagrafici')
    if dati_ana is not None:
        id_fisc = dati_ana.find(f'{ns}IdFiscaleIVA')
        if id_fisc is not None:
            paese = id_fisc.findtext(f'{ns}IdPaese', '')
            codice = id_fisc.findtext(f'{ns}IdCodice', '')
            result['customer_vat'] = f"{paese}{codice}"

        denom = dati_ana.findtext(f'{ns}Denominazione')
        if not denom:
            nome = dati_ana.findtext(f'{ns}Nome', '')
            cognome = dati_ana.findtext(f'{ns}Cognome', '')
            denom = f"{nome} {cognome}".strip()
        result['customer_name'] = denom or ''

        email = dati_ana.findtext(f'{ns}Email')
        if email:
            result['customer_email'] = email

        contatti = dati_ana.find(f'{ns}Contatti')
        if contatti is not None:
            telefono = contatti.findtext(f'{ns}Telefono', '')
            if telefono:
                result['customer_phone'] = telefono

    sede = committente.find(f'{ns}Sede')
    if sede is not None:
        indirizzo = sede.findtext(f'{ns}Indirizzo', '')
        civico = sede.findtext(f'{ns}NumeroCivico', '')
        cap = sede.findtext(f'{ns}CAP', '')
        comune = sede.findtext(f'{ns}Comune', '')
        provincia = sede.findtext(f'{ns}Provincia', '')
        parts = [x for x in [f"{indirizzo} {civico}".strip(), cap, comune, provincia] if x]
        result['customer_address'] = ', '.join(parts)

    if raw_text:
        phone_patterns = [r'(?i)(?:tel|fono|cell)[:\s]*(\+?39?\s*\d{2,4}[\s\.]?\d{3,4}[\s\.]?\d{3,4})']
        if not result.get('customer_phone'):
            result['customer_phone'] = _extract_with_pattern(raw_text, phone_patterns)

        pec_patterns = [r'([a-zA-Z0-9._%+-]+@pec\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})']
        if not result.get('customer_pec'):
            result['customer_pec'] = _extract_with_pattern(raw_text, pec_patterns)

        sdi_patterns = [r'(?i)codicedestinatario[:\s]*([A-Z0-9]{6,7})']
        sdi = _extract_with_pattern(raw_text, sdi_patterns)
        if sdi and not result.get('customer_sdi'):
            result['customer_sdi'] = re.sub(r'[^A-Z0-9]', '', sdi.upper())[:7]

        cf_patterns = [
            r'\b([A-Z]{6}[0-9LMNPQRSTUVlmnpqrstuv]{2}[A-Z][0-9LMNPQRSTUVlmnpqrstuv]{2}[A-Z][0-9LMNPQRSTUVlmnpqrstuv]{3}[A-Z])\b',
        ]
        cf = _extract_with_pattern(raw_text, cf_patterns)
        if cf and not result.get('customer_cf'):
            result['customer_cf'] = cf.upper()

    return result


def _parse_invoice_info(body: ET.Element, ns: str) -> Dict[str, Any]:
    """Parse invoice general info."""
    result = {}

    dati_gen = body.find(f'{ns}DatiGenerali/{ns}DatiGeneraliDocumento')
    if dati_gen is None:
        dati_gen = body.find('.//DatiGeneraliDocumento')

    if dati_gen is not None:
        result['invoice_number'] = dati_gen.findtext(f'{ns}Numero', '')
        data_elem = dati_gen.find(f'{ns}Data') or dati_gen.find('Data')
        if data_elem is not None and data_elem.text:
            result['invoice_date'] = data_elem.text

        causali = dati_gen.findall(f'{ns}Causale') or dati_gen.findall('Causale')
        if causali:
            result['description'] = ' '.join(c.text for c in causali if c.text)

    # Amounts
    beni = body.find(f'{ns}DatiBeniServizi') or body.find('DatiBeniServizi')
    if beni is not None:
        riepilogo_list = beni.findall(f'{ns}DatiRiepilogo') or beni.findall('DatiRiepilogo')

        amount = 0.0
        vat_amount = 0.0

        for r in riepilogo_list:
            imponibile = r.findtext(f'{ns}ImponibileImporto')
            imposta = r.findtext(f'{ns}Imposta')
            try:
                if imponibile and float(imponibile) > 0:
                    amount += float(imponibile)
                elif imposta and float(imposta) > 0:
                    amount += float(imposta) / 0.22  # Assume 22% VAT
                vat_amount += float(imposta) if imposta else 0.0
            except (ValueError, TypeError):
                pass

        result['amount'] = round(amount, 2)
        result['vat_amount'] = round(vat_amount, 2)
        result['total_amount'] = round(amount + vat_amount, 2)

    return result


def _parse_payment(body: ET.Element, ns: str, invoice_date: str = None) -> Dict[str, Any]:
    """Parse payment terms and due date."""
    result = {}

    pagamenti = body.find(f'{ns}DatiPagamento') or body.find('DatiPagamento')
    if pagamenti is not None:
        pag = pagamenti.find(f'{ns}DatiPagamento') or pagamenti

        if pag is not None:
            termini = pag.findtext(f'{ns}TerminiPagamento', pag.findtext('TerminiPagamento', ''))
            if termini:
                try:
                    days = int(termini)
                    result['payment_days'] = days
                    if invoice_date and 'due_date' not in result:
                        dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                        result['due_date'] = (dt + timedelta(days=days)).strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    pass

            data_scad = pag.findtext(f'{ns}DataScadenzaPagamento', pag.findtext('DataScadenzaPagamento'))
            if data_scad and 'due_date' not in result:
                result['due_date'] = data_scad

            modo = pag.findtext(f'{ns}ModalitaPagamento', pag.findtext('ModalitaPagamento'))
            if modo:
                result['payment_method'] = modo

    return result


def _normalize_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD."""
    if not date_str:
        return ''

    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y']:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue

    return date_str
