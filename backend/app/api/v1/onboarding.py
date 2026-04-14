"""
Onboarding API endpoints.

Manages the guided setup process for new users to configure their
business preferences for the intelligent sollecito system.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from app.db.session import get_db
from app.models.user import User
from app.models.client import BusinessConfig
from app.schemas.client import (
    OnboardingStatusResponse,
    OnboardingQuestionResponse,
    OnboardingAnswerRequest,
    OnboardingConfigProposal,
    OnboardingApproveRequest,
)
from app.core.security import get_current_active_user
from app.services.trust_score import update_config

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# Onboarding questions definition
ONBOARDING_QUESTIONS = [
    {
        "step": 1,
        "question": "Quando un cliente è in ritardo, di solito cosa fai?",
        "input_type": "single_choice",
        "options": [
            {"value": "call", "label": "Lo chiamo direttamente"},
            {"value": "whatsapp", "label": "Invio un messaggio WhatsApp"},
            {"value": "wait", "label": "Aspetto che si faccia vivo"},
            {"value": "other", "label": "Altro"},
        ],
    },
    {
        "step": 2,
        "question": "Qual è il ritardo che ti fa preoccupare?",
        "input_type": "single_choice",
        "options": [
            {"value": "7", "label": "7 giorni"},
            {"value": "15", "label": "15 giorni"},
            {"value": "30", "label": "30 giorni"},
            {"value": "other", "label": "Altro"},
        ],
    },
    {
        "step": 3,
        "question": "Sotto quale importo non ti conviene perdere tempo?",
        "input_type": "slider",
        "slider_min": 0,
        "slider_max": 10000,
        "slider_default": 2000,
    },
    {
        "step": 4,
        "question": "Hai già uno storico clienti da importare?",
        "input_type": "single_choice",
        "options": [
            {"value": "yes_csv", "label": "Sì, ho un CSV da importare"},
            {"value": "no_start_fresh", "label": "No, inizio da zero"},
        ],
    },
]


def _deduce_style(answers: dict) -> str:
    """Deduce business style from onboarding answers."""
    action = answers.get("1", {}).get("answer", "")
    
    if action == "wait":
        return "gentile"
    elif action == "call":
        return "equilibrato"
    elif action == "other":
        return "fermo"
    else:
        return "gentile"  # Default


def _deduce_thresholds(answers: dict) -> dict:
    """Deduce threshold values from onboarding answers."""
    worry_delay = answers.get("2", {}).get("answer", "15")
    min_amount = answers.get("3", {}).get("answer", 2000)
    
    # Parse delay value
    if worry_delay == "7":
        warning = 7
        escalation = 14
    elif worry_delay == "30":
        warning = 30
        escalation = 60
    elif worry_delay == "other":
        warning = 15
        escalation = 30
    else:
        warning = int(worry_delay)
        escalation = warning * 2
    
    # Calculate legal threshold (average of min_amount * 0.5)
    legal_threshold = float(min_amount) * 0.5
    
    return {
        "warning_threshold_days": warning,
        "escalation_days": escalation,
        "legal_threshold": legal_threshold,
        "first_reminder_days": max(1, warning // 2),
    }


def _build_proposal(answers: dict) -> OnboardingConfigProposal:
    """Build config proposal from answers."""
    style = _deduce_style(answers)
    thresholds = _deduce_thresholds(answers)
    
    # Build reasoning
    action = answers.get("1", {}).get("answer", "")
    action_labels = {
        "call": "preferisci chiamare direttamente i clienti",
        "whatsapp": "preferisci un approccio informale via messaggio",
        "wait": "preferisci aspettare che il cliente si faccia vivo",
        "other": "preferisci un approccio deciso",
    }
    action_text = action_labels.get(action, "preferisci un approccio equilibrato")
    
    reasoning = (
        f"Hai indicato che {action_text}. "
        f"Ti preoccupa un ritardo di {answers.get('2', {}).get('answer', '15')} giorni "
        f"e non vuoi perdere tempo con importi sotto €{thresholds['legal_threshold']:.0f}. "
        f"Ho configurato il sistema con uno stile '{style}'."
    )
    
    return OnboardingConfigProposal(
        style=style,
        legal_threshold=thresholds["legal_threshold"],
        new_client_score=60,
        first_reminder_days=thresholds["first_reminder_days"],
        warning_threshold_days=thresholds["warning_threshold_days"],
        escalation_days=thresholds["escalation_days"],
        reasoning=reasoning,
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current onboarding status."""
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config or not config.onboarding_answers:
        return OnboardingStatusResponse(status="not_started")
    
    answers = json.loads(config.onboarding_answers)
    
    # Check if completed
    if config.onboarding_completed:
        return OnboardingStatusResponse(
            status="completed",
            current_step=4,
            total_steps=4,
            answers=answers,
        )
    
    # Find current step (first unanswered)
    current_step = 1
    for i in range(1, 5):
        if str(i) not in answers:
            current_step = i
            break
    else:
        current_step = 4
    
    return OnboardingStatusResponse(
        status="in_progress",
        current_step=current_step,
        total_steps=4,
        answers=answers,
    )


@router.post("/start", response_model=OnboardingQuestionResponse)
async def start_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Start or resume onboarding, returns first unanswered question."""
    # Get or create config
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = BusinessConfig(id=1, onboarding_answers="{}")
        db.add(config)
        await db.commit()
    
    # Check if already completed
    if config.onboarding_completed:
        raise HTTPException(status_code=400, detail="Onboarding already completed")
    
    # Parse existing answers
    answers = {}
    if config.onboarding_answers:
        answers = json.loads(config.onboarding_answers)
    
    # Find first unanswered question
    for q in ONBOARDING_QUESTIONS:
        if str(q["step"]) not in answers:
            return OnboardingQuestionResponse(
                step=q["step"],
                question=q["question"],
                options=q.get("options"),
                input_type=q["input_type"],
                slider_min=q.get("slider_min"),
                slider_max=q.get("slider_max"),
                slider_default=q.get("slider_default"),
            )
    
    # All answered, return first question (shouldn't happen if status is correct)
    return OnboardingQuestionResponse(**ONBOARDING_QUESTIONS[0])


@router.post("/answer", response_model=OnboardingQuestionResponse | OnboardingConfigProposal)
async def answer_question(
    answer_data: OnboardingAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submit an answer to the current question."""
    # Get config
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = BusinessConfig(id=1, onboarding_answers="{}")
        db.add(config)
    
    # Parse existing answers
    answers = {}
    if config.onboarding_answers:
        answers = json.loads(config.onboarding_answers)
    
    # Validate step
    expected_step = len(answers) + 1
    if answer_data.step != expected_step:
        raise HTTPException(
            status_code=400,
            detail=f"Expected step {expected_step}, got {answer_data.step}"
        )
    
    # Save answer
    answers[str(answer_data.step)] = {
        "answer": answer_data.answer,
    }
    config.onboarding_answers = json.dumps(answers)
    await db.commit()
    
    # Check if more questions or done
    if answer_data.step < 4:
        # Return next question
        next_q = ONBOARDING_QUESTIONS[answer_data.step]
        return OnboardingQuestionResponse(
            step=next_q["step"],
            question=next_q["question"],
            options=next_q.get("options"),
            input_type=next_q["input_type"],
            slider_min=next_q.get("slider_min"),
            slider_max=next_q.get("slider_max"),
            slider_default=next_q.get("slider_default"),
        )
    else:
        # All questions answered, return proposal
        return _build_proposal(answers)


@router.post("/approve", response_model=dict)
async def approve_config(
    approve_data: OnboardingApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Approve the proposed configuration and activate the system."""
    if not approve_data.approved:
        raise HTTPException(status_code=400, detail="Config not approved")
    
    # Get config
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=400, detail="Please complete onboarding first")
    
    if config.onboarding_completed:
        raise HTTPException(status_code=400, detail="Onboarding already completed")
    
    # Parse answers and build proposal
    answers = {}
    if config.onboarding_answers:
        answers = json.loads(config.onboarding_answers)
    
    proposal = _build_proposal(answers)
    
    # Apply the configuration
    await update_config(
        db,
        style=proposal.style,
        legal_threshold=proposal.legal_threshold,
        new_client_score=proposal.new_client_score,
        first_reminder_days=proposal.first_reminder_days,
        warning_threshold_days=proposal.warning_threshold_days,
        escalation_days=proposal.escalation_days,
    )
    
    # Mark onboarding as completed
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()
    config.onboarding_completed = True
    await db.commit()
    
    return {
        "success": True,
        "message": "Configurazione completata. Il sistema è attivo.",
        "config": proposal,
    }
