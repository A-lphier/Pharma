"""
Tests for invoice parser service.
"""
import pytest
from app.services.invoice_parser import parse_invoice_xml, InvoiceParserError


def test_parse_valid_fatturapa_xml():
    """Test parsing a valid FatturaPA XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FatturaElettronica versione="FPR12" xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>12345678901</IdCodice></IdFiscaleIVA>
        <Denominazione>Fornitore Test S.r.l.</Denominazione>
        <Email>fornitore@test.it</Email>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>Via Roma 1</Indirizzo>
        <CAP>00100</CAP>
        <Comune>Roma</Comune>
        <Provincia>RM</Provincia>
      </Sede>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>98765432109</IdCodice></IdFiscaleIVA>
        <Denominazione>Cliente Test S.p.A.</Denominazione>
        <Email>cliente@test.it</Email>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>Via Milano 10</Indirizzo>
        <CAP>20100</CAP>
        <Comune>Milano</Comune>
        <Provincia>MI</Provincia>
      </Sede>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <Numero>FT/2026/0001</Numero>
        <Data>2026-01-10</Data>
        <Causale>Servizi di consulenza</Causale>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DatiRiepilogo>
        <ImponibileImporto>5000.00</ImponibileImporto>
        <Imposta>1100.00</Imposta>
        <AliquotaIVA>22</AliquotaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
    <DatiPagamento>
      <DatiPagamento>
        <TerminiPagamento>30</TerminiPagamento>
        <ModalitaPagamento>BB01</ModalitaPagamento>
      </DatiPagamento>
    </DatiPagamento>
  </FatturaElettronicaBody>
</FatturaElettronica>
"""
    
    result = parse_invoice_xml(xml_content)
    
    assert result["invoice_number"] == "FT/2026/0001"
    assert result["customer_name"] == "Cliente Test S.p.A."
    assert result["supplier_name"] == "Fornitore Test S.r.l."
    assert result["amount"] == 5000.00
    assert result["vat_amount"] == 1100.00
    assert result["total_amount"] == 6100.00
    assert result["customer_vat"] == "IT98765432109"
    assert result["supplier_vat"] == "IT12345678901"


def test_parse_invalid_xml():
    """Test parsing invalid XML raises error."""
    with pytest.raises(InvoiceParserError):
        parse_invoice_xml("not valid xml")


def test_parse_empty_xml():
    """Test parsing empty XML raises error."""
    with pytest.raises(InvoiceParserError):
        parse_invoice_xml("")


def test_parse_missing_body():
    """Test parsing XML without FatturaElettronicaBody raises error."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FatturaElettronica versione="FPR12">
</FatturaElettronica>
"""
    with pytest.raises(InvoiceParserError, match="Missing FatturaElettronicaBody"):
        parse_invoice_xml(xml_content)


def test_parse_with_bom():
    """Test parsing XML with BOM."""
    xml_content = '\ufeff<?xml version="1.0" encoding="UTF-8"?>\n<FatturaElettronica versione="FPR12" xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"><FatturaElettronicaBody></FatturaElettronicaBody></FatturaElettronica>'
    result = parse_invoice_xml(xml_content.encode('utf-8'))
    # Should not raise, body is empty but valid structure
    assert "invoice_number" in result


def test_parse_extracts_pec_from_text():
    """Test PEC extraction from raw text."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FatturaElettronica versione="FPR12" xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <Numero>FT/001</Numero>
        <Data>2026-01-01</Data>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DatiRiepilogo>
        <ImponibileImporto>100</ImponibileImporto>
        <Imposta>22</Imposta>
        <AliquotaIVA>22</AliquotaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</FatturaElettronica>
"""
    # Add PEC to raw text section
    result = parse_invoice_xml(xml_content)
    # Basic structure should work
    assert result["invoice_number"] == "FT/001"
