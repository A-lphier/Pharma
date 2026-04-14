"""
Tests for invoice endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import date, timedelta

from app.models.invoice import Invoice


@pytest.mark.asyncio
async def test_list_invoices_empty(client: AsyncClient, auth_headers):
    """Test listing invoices when empty."""
    response = await client.get("/api/v1/invoices", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_invoices_requires_auth(client: AsyncClient):
    """Test that listing invoices requires authentication."""
    response = await client.get("/api/v1/invoices")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_invoice_stats(client: AsyncClient, auth_headers):
    """Test getting invoice statistics."""
    response = await client.get("/api/v1/invoices/stats", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "paid" in data
    assert "pending" in data
    assert "overdue" in data


@pytest.mark.asyncio
async def test_create_invoice_from_xml(client: AsyncClient, auth_headers, test_db):
    """Test creating an invoice from XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FatturaElettronica versione="FPR12" xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>12345678901</IdCodice></IdFiscaleIVA>
        <Denominazione>Test Supplier S.r.l.</Denominazione>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>98765432109</IdCodice></IdFiscaleIVA>
        <Denominazione>Test Customer S.p.A.</Denominazione>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <Numero>FT/2026/001</Numero>
        <Data>2026-01-15</Data>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DatiRiepilogo>
        <ImponibileImporto>1000.00</ImponibileImporto>
        <Imposta>220.00</Imposta>
        <AliquotaIVA>22</AliquotaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</FatturaElettronica>
"""
    
    import io
    files = {"file": ("test_invoice.xml", io.BytesIO(xml_content.encode()), "application/xml")}
    
    response = await client.post(
        "/api/v1/invoices",
        files=files,
        headers=auth_headers,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["invoice_number"] == "FT/2026/001"
    assert data["customer_name"] == "Test Customer S.p.A."
    assert data["supplier_name"] == "Test Supplier S.r.l."
    assert data["total_amount"] == 1220.00


@pytest.mark.asyncio
async def test_get_invoice_not_found(client: AsyncClient, auth_headers):
    """Test getting a nonexistent invoice."""
    response = await client.get("/api/v1/invoices/99999", headers=auth_headers)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_invoice_paid(client: AsyncClient, auth_headers, test_db, test_user):
    """Test marking an invoice as paid."""
    # Create invoice
    invoice = Invoice(
        invoice_number="TEST/001",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        customer_name="Test Customer",
        amount=1000,
        vat_amount=220,
        total_amount=1220,
        created_by=test_user.id,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)
    
    # Mark as paid
    response = await client.post(
        f"/api/v1/invoices/{invoice.id}/paid",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_delete_invoice(client: AsyncClient, auth_headers, test_db, test_user):
    """Test deleting an invoice."""
    # Create invoice
    invoice = Invoice(
        invoice_number="TEST/002",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        customer_name="Test Customer",
        amount=500,
        vat_amount=110,
        total_amount=610,
        created_by=test_user.id,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)
    
    # Delete
    response = await client.delete(
        f"/api/v1/invoices/{invoice.id}",
        headers=auth_headers,
    )
    
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_bulk_mark_paid(client: AsyncClient, auth_headers, test_db, test_user):
    """Test bulk marking invoices as paid."""
    # Create invoices
    invoices = []
    for i in range(3):
        invoice = Invoice(
            invoice_number=f"TEST/{i+1:03d}",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            customer_name=f"Customer {i+1}",
            amount=500,
            vat_amount=110,
            total_amount=610,
            created_by=test_user.id,
        )
        test_db.add(invoice)
        invoices.append(invoice)
    
    await test_db.commit()
    
    ids = [inv.id for inv in invoices]
    
    # Bulk mark paid
    response = await client.post(
        "/api/v1/invoices/bulk/pay",
        json={"invoice_ids": ids},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    assert response.json()["updated"] == 3


@pytest.mark.asyncio
async def test_send_reminder(client: AsyncClient, auth_headers, test_db, test_user):
    """Test sending a reminder for an invoice."""
    # Create invoice
    invoice = Invoice(
        invoice_number="TEST/003",
        invoice_date=date.today(),
        due_date=date.today() - timedelta(days=5),  # Overdue
        customer_name="Test Customer",
        amount=1000,
        vat_amount=220,
        total_amount=1220,
        created_by=test_user.id,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)
    
    # Send reminder
    response = await client.post(
        f"/api/v1/invoices/{invoice.id}/remind",
        json={"message": "Test reminder"},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    assert response.json()["reminder_type"] == "manual"
