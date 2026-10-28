from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.candidate_intelligence import CandidateIntelligence
from app.services.candidate_intelligence import build_candidate_intelligence


router = APIRouter(
    prefix="/candidate-intelligence",
    tags=["Candidate Intelligence"],
)


@router.post("/generate")
def generate_candidate_intelligence(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    try:
        return build_candidate_intelligence(
            current_user.id,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get("")
def get_candidate_intelligence(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    candidate = (
        db.query(CandidateIntelligence)
        .filter(
            CandidateIntelligence.user_id == current_user.id
        )
        .first()
    )

    if not candidate:
        raise HTTPException(
            status_code=404,
            detail="Candidate intelligence not found",
        )

    return candidate