"""
Adaptive Reminder Templates Service.

Generates personalized reminder messages based on:
- Client trust score and status
- Business config style (gentile, equilibrato, fermo)
- Invoice details (amount, due date, days late)
"""
from datetime import date, datetime, timedelta
from typing import Optional

from app.services.trust_score import get_trust_score_label


def generate_reminder_message(
    client_name: str,
    invoice_number: str,
    invoice_amount: float,
    due_date: date,
    trust_score: int,
    style: str = "gentile",
    days_late: int = 0,
    is_overdue: bool = False,
) -> str:
    """
    Generate an adaptive reminder message.
    
    Args:
        client_name: Name of the client
        invoice_number: Invoice number
        invoice_amount: Invoice amount
        due_date: Due date of the invoice
        trust_score: Client trust score (0-100)
        style: Business style ('gentile', 'equilibrato', 'fermo')
        days_late: Number of days overdue (if applicable)
        is_overdue: Whether the invoice is overdue
    
    Returns:
        Formatted reminder message string.
    """
    label, emoji = get_trust_score_label(trust_score)
    formatted_amount = f"€{invoice_amount:,.2f}".replace(",", ".")
    formatted_date = due_date.strftime("%d/%m/%Y")
    
    if is_overdue and days_late > 0:
        message = _get_overdue_message(
            client_name, invoice_number, formatted_amount, days_late, trust_score, style
        )
    else:
        message = _get_upcoming_message(
            client_name, invoice_number, formatted_amount, formatted_date, trust_score, style
        )
    
    return message


def _get_upcoming_message(
    client_name: str,
    invoice_number: str,
    formatted_amount: str,
    formatted_date: str,
    trust_score: int,
    style: str,
) -> str:
    """Generate message for upcoming (not yet due) invoices."""
    templates = {
        "gentile": {
            "excellent": "Ciao {name}, ti ricordo la fattura {number} di {amount} in scadenza il {date}. Grazie!",
            "reliable": "Gentile {name}, ti ricordo che la fattura {number} di {amount} scade il {date}. Grazie per l'attenzione.",
            "verify": "Gentile {name}, la fattura {number} di {amount} scade il {date}. Potrebbe essere sfuggita? Grazie.",
            "problems": "Egregio {name}, la fattura {number} di {amount} scade il {date}. Le chiediamo di verificarla. Grazie.",
            "unreliable": "Egregio {name}, la fattura {number} di {amount} scade il {date}. La preghiamo di regolare il pagamento entro la scadenza.",
        },
        "equilibrato": {
            "excellent": "Gentile {name}, desideriamo ricordare che la fattura {number} di {amount} è in scadenza il {date}. La ringraziamo per l'attenzione.",
            "reliable": "Gentile {name}, la fattura {number} di {amount} è in scadenza il {date}. La preghiamo di verificare la sua posizione. Grazie.",
            "verify": "Gentile {name}, la fattura {number} di {amount} è in scadenza il {date}. Le chiediamo di cortesemente verificare. Grazie.",
            "problems": "Egregio {name}, la fattura {number} di {amount} è in scadenza il {date}. Le chiediamo di procedere al pagamento entro la data di scadenza.",
            "unreliable": "Egregio {name}, la fattura {number} di {amount} è in scadenza il {date}. Senza pagamento entro la scadenza, saremo costretti a valutare azioni.",
        },
        "fermo": {
            "excellent": "La informiamo che la fattura {number} di {amount} è in scadenza il {date}. La preghiamo di provvedere.",
            "reliable": "La fattura {number} di {amount} è in scadenza il {date}. Le chiediamo di verificare e regolare.",
            "verify": "La fattura {number} di {amount} è in scadenza il {date}. Le chiediamo di procedere al pagamento entro la scadenza.",
            "problems": "La fattura {number} di {amount} è in scadenza il {date}. Senza pagamento entro la data indicata, saranno avviate le procedure di recupero.",
            "unreliable": "La fattura {number} di {amount} è in scadenza il {date}. In assenza di pagamento, saremo costretti a procedere legalmente.",
        },
    }
    
    tone = _get_tone_key(trust_score)
    template = templates.get(style, templates["gentile"])[tone]
    
    return template.format(name=client_name, number=invoice_number, amount=formatted_amount, date=formatted_date)


def _get_overdue_message(
    client_name: str,
    invoice_number: str,
    formatted_amount: str,
    days_late: int,
    trust_score: int,
    style: str,
) -> str:
    """Generate message for overdue invoices."""
    templates = {
        "gentile": {
            "excellent": "Ciao {name}, ti ricordo che la fattura {number} di {amount} è scaduta il {date}. Potrebbe essere sfuggita? Grazie per l'attenzione.",
            "reliable": "Gentile {name}, la fattura {number} di {amount} è scaduta il {date}. Potrebbe essere sfuggita? Grazie per l'attenzione.",
            "verify": "Gentile {name}, la fattura {number} di {amount} è scaduta il {date}. Potrebbe essere sfuggita? Grazie.",
            "problems": "Egregio {name}, la fattura {number} di {amount} risulta scaduta da {days} giorni. Le chiediamo di verificare e regolare entro 7 giorni.",
            "unreliable": "Egregio {name}, la fattura {number} di {amount} è scaduta da {days} giorni. Senza pagamento entro 5 giorni, saremo costretti a valutare azioni.",
        },
        "equilibrato": {
            "excellent": "Gentile {name}, la fattura {number} di {amount} risulta scaduta. Le chiediamo di verificare la sua posizione. Grazie per l'attenzione.",
            "reliable": "Gentile {name}, la fattura {number} di {amount} risulta scaduta. La preghiamo di verificare e regolare. Grazie.",
            "verify": "Gentile {name}, la fattura {number} di {amount} risulta scaduta da {days} giorni. Le chiediamo di procedere al pagamento. Grazie.",
            "problems": "Egregio {name}, la fattura {number} di {amount} risulta scaduta da {days} giorni. Le chiediamo di regolare entro 7 giorni. In caso contrario, saremo costretti a procedere.",
            "unreliable": "Egregio {name}, la fattura {number} di {amount} è scaduta da {days} giorni. Le chiediamo di regolare entro 5 giorni. In assenza, saremo costretti a valutare azioni legali.",
        },
        "fermo": {
            "excellent": "La informiamo che la fattura {number} di {amount} risulta scaduta. Le chiediamo di provvedere al pagamento con urgenza.",
            "reliable": "La fattura {number} di {amount} risulta scaduta. Le chiediamo di procedere al pagamento entro 7 giorni.",
            "verify": "La fattura {number} di {amount} è scaduta da {days} giorni. Le chiediamo di regolare entro 7 giorni.",
            "problems": "La fattura {number} di {amount} è scaduta da {days} giorni. Senza pagamento entro 7 giorni, saranno avviate le procedure di recupero crediti.",
            "unreliable": "La fattura {number} di {amount} è scaduta da {days} giorni. Senza pagamento entro 5 giorni, saremo costretti a procedere legalmente.",
        },
    }
    
    tone = _get_tone_key(trust_score)
    template = templates.get(style, templates["gentile"])[tone]
    
    # Calculate original due date
    due_date = date.today() - timedelta(days=days_late)
    formatted_date = date.today().strftime("%d/%m/%Y")
    
    return template.format(
        name=client_name,
        number=invoice_number,
        amount=formatted_amount,
        days=days_late,
        date=formatted_date,
    )


def _get_tone_key(trust_score: int) -> str:
    """Get tone key based on trust score."""
    if trust_score >= 80:
        return "excellent"
    elif trust_score >= 60:
        return "reliable"
    elif trust_score >= 40:
        return "verify"
    elif trust_score >= 20:
        return "problems"
    else:
        return "unreliable"


def format_amount(amount: float) -> str:
    """Format amount as Italian currency."""
    return f"€{amount:,.2f}".replace(",", ".")


def get_urgency_level(trust_score: int, days_late: int = 0) -> str:
    """Determine urgency level for UI display."""
    if trust_score >= 60 and days_late <= 7:
        return "low"
    elif trust_score >= 40 and days_late <= 15:
        return "medium"
    elif trust_score >= 20 and days_late <= 30:
        return "high"
    else:
        return "critical"
