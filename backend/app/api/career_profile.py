from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.career_profile import CareerProfile
from app.schemas.career_profile import (
    CareerProfileCreate,
    CareerProfileResponse,
)


router = APIRouter(
    prefix="/career-profile",
    tags=["Career Profile"],
)


@router.post("", response_model=CareerProfileResponse)
def create_career_profile(
    current_user: CurrentUser,
    data: CareerProfileCreate,
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(CareerProfile).where(
            CareerProfile.user_id == current_user.id
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Career profile already exists",
        )

    profile = CareerProfile(
        user_id=current_user.id,
        **data.model_dump(),
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile


@router.get("", response_model=CareerProfileResponse)
def get_career_profile(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(CareerProfile).where(
            CareerProfile.user_id == current_user.id
        )
    )

    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Career profile not found",
        )

    return profile


@router.put("", response_model=CareerProfileResponse)
def update_career_profile(
    current_user: CurrentUser,
    data: CareerProfileCreate,
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(CareerProfile).where(
            CareerProfile.user_id == current_user.id
        )
    )

    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Career profile not found",
        )

    for field, value in data.model_dump().items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile