"""
Feedback Router
API endpoints for submitting and checking user feedback.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import logging

from app.services.feedback_service import get_feedback_service, FeedbackService
from app.auth.dependencies import get_current_user_id_optional
from app.rate_limit import limiter

# Configure logger
logger = logging.getLogger("feedback_router")

# Create router
router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackSubmission(BaseModel):
    """Request body for feedback submission."""
    adventure_id: str
    rating: str  # 'positive' or 'negative'
    feedback_text: Optional[str] = None
    contact_info: Optional[str] = None
    client_uuid: Optional[str] = None  # For guest users
    chapter_number: int = 5


class FeedbackCheckRequest(BaseModel):
    """Query params for checking feedback status."""
    client_uuid: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response for feedback operations."""
    success: bool
    message: str
    feedback_id: Optional[str] = None


class FeedbackCheckResponse(BaseModel):
    """Response for feedback check endpoint."""
    has_given_feedback: bool


def get_feedback_service_dep() -> FeedbackService:
    """Dependency injection for FeedbackService."""
    return get_feedback_service()


@router.post("", response_model=FeedbackResponse)
@limiter.limit("10/minute")
async def submit_feedback(
    request: Request,
    feedback: FeedbackSubmission,
    user_id: Optional[UUID] = Depends(get_current_user_id_optional),
    feedback_service: FeedbackService = Depends(get_feedback_service_dep),
):
    """
    Submit user feedback.

    Accepts feedback from both authenticated users (via JWT) and guest users (via client_uuid).
    """
    logger.info(
        f"Feedback submission received: rating={feedback.rating}, "
        f"user_id={user_id}, client_uuid={feedback.client_uuid}"
    )

    # Validate rating
    if feedback.rating not in ('positive', 'negative'):
        raise HTTPException(
            status_code=400,
            detail="Rating must be 'positive' or 'negative'"
        )

    # Validate adventure_id format
    try:
        adventure_uuid = UUID(feedback.adventure_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid adventure_id format"
        )

    # Store the feedback
    result = await feedback_service.store_feedback(
        adventure_id=adventure_uuid,
        rating=feedback.rating,
        user_id=user_id,
        client_uuid=feedback.client_uuid,
        feedback_text=feedback.feedback_text,
        contact_info=feedback.contact_info,
        chapter_number=feedback.chapter_number,
    )

    if result:
        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!",
            feedback_id=result.get("id")
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to store feedback. Please try again."
        )


@router.get("/check", response_model=FeedbackCheckResponse)
async def check_feedback_status(
    client_uuid: Optional[str] = None,
    user_id: Optional[UUID] = Depends(get_current_user_id_optional),
    feedback_service: FeedbackService = Depends(get_feedback_service_dep),
):
    """
    Check if the current user has ever given feedback.

    Used to implement "once per user" logic for the feedback prompt.
    Returns True if user has given feedback before, False otherwise.
    """
    logger.debug(f"Checking feedback status: user_id={user_id}, client_uuid={client_uuid}")

    has_feedback = await feedback_service.has_user_given_feedback(
        user_id=user_id,
        client_uuid=client_uuid,
    )

    return FeedbackCheckResponse(has_given_feedback=has_feedback)
