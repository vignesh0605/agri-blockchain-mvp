"""Review Queue routes"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db, ReviewStatus
from models import (
    ReviewQueueCreate, ReviewQueueUpdate, ReviewQueueResponse,
    ReviewActionRequest
)
from crud import (
    create_review_queue, get_review, get_review_by_event,
    get_pending_reviews, update_review
)
from anomaly import analyze_event, train_detector

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewQueueResponse, status_code=status.HTTP_201_CREATED)
def create_review_endpoint(review: ReviewQueueCreate, db: Session = Depends(get_db)):
    """Create a review queue entry (typically called internally after anomaly detection)"""
    return create_review_queue(db, review)


@router.get("/", response_model=List[ReviewQueueResponse])
def list_reviews(
    status: Optional[ReviewStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List review queue entries"""
    if status:
        from crud import get_review
        # Filter by status would need a new crud function
        reviews = db.query(ReviewQueue).filter(ReviewQueue.status == status).offset(skip).limit(limit).all()
        return reviews
    return get_pending_reviews(db, skip=skip, limit=limit)


@router.get("/{review_id}", response_model=ReviewQueueResponse)
def get_review_endpoint(review_id: int, db: Session = Depends(get_db)):
    """Get a review by ID"""
    review = get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found"
        )
    return review


@router.get("/event/{event_id}", response_model=ReviewQueueResponse)
def get_review_by_event_endpoint(event_id: int, db: Session = Depends(get_db)):
    """Get review for a specific event"""
    review = get_review_by_event(db, event_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review for event {event_id} not found"
        )
    return review


@router.patch("/{review_id}", response_model=ReviewQueueResponse)
def update_review_endpoint(review_id: int, review_update: ReviewQueueUpdate, db: Session = Depends(get_db)):
    """Update a review"""
    review = update_review(db, review_id, review_update)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found"
        )
    return review


@router.post("/{review_id}/action", response_model=ReviewQueueResponse)
def take_review_action(
    review_id: int,
    action_request: ReviewActionRequest,
    db: Session = Depends(get_db)
):
    """Take action on a review: accept, reject, or needs_more_info"""
    review = get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found"
        )

    from database import EventStatus, AnomalyStatus, ReviewStatus

    action = action_request.action
    admin_id = action_request.admin_id
    notes = action_request.notes

    if action == "accept":
        # Accept: event -> committed, anomaly -> accepted, review -> accepted
        update_review(db, review_id, ReviewQueueUpdate(
            status=ReviewStatus.ACCEPTED,
            action="accepted",
            notes=notes,
            assigned_to=admin_id
        ))
        # Update event status
        from crud import update_event
        update_event(db, review.event_id, type('obj', (object,), {'status': EventStatus.COMMITTED})())
        # Update anomaly flag
        from crud import update_anomaly_flag_status
        update_anomaly_flag_status(db, review.event_id, AnomalyStatus.ACCEPTED, notes, admin_id)

    elif action == "reject":
        # Reject: event -> rejected, anomaly -> rejected, review -> rejected
        update_review(db, review_id, ReviewQueueUpdate(
            status=ReviewStatus.REJECTED,
            action="rejected",
            notes=notes,
            assigned_to=admin_id
        ))
        from crud import update_event, update_anomaly_flag_status
        update_event(db, review.event_id, type('obj', (object,), {'status': EventStatus.REJECTED})())
        update_anomaly_flag_status(db, review.event_id, AnomalyStatus.REJECTED, notes, admin_id)

    elif action == "needs_more_info":
        # Request more info: review -> needs_more_info
        update_review(db, review_id, ReviewQueueUpdate(
            status=ReviewStatus.NEEDS_MORE_INFO,
            action="needs_more_info",
            notes=notes,
            assigned_to=admin_id
        ))
        # Event stays flagged, anomaly stays in admin_review

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action}"
        )

    # Return updated review
    return get_review(db, review_id)