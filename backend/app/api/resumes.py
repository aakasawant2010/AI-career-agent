import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.database import get_db
from app.core.resume_parser import parse_resume
from app.models.resume import Resume
from app.schemas.resume import (
    ResumeCreate,
    ResumeResponse,
    ResumeUpdate,
)


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)


@router.post("/upload", response_model=ResumeResponse)
def upload_resume(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported",
        )

    file_type = extension.replace(".", "")

    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    file_bytes = file.file.read(max_bytes + 1)

    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {get_settings().max_upload_mb} MB)",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    try:
        parsed_text = parse_resume(
            file_bytes,
            file_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse resume. Check that the file is a valid PDF or DOCX.",
        )

    upload_dir = Path(get_settings().upload_dir)

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Never trust the client's file name: strip any directory part and odd characters.
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file.filename).name)[:120] or "resume"
    file_name = f"{current_user.id}_{uuid.uuid4().hex[:8]}_{safe_name}"

    file_path = upload_dir / file_name

    file_path.write_bytes(file_bytes)

    # Uploaded resumes become the active resume automatically.
    db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True,
    ).update(
        {"is_active": False},
        synchronize_session=False,
    )

    resume = Resume(
        user_id=current_user.id,
        name=Path(file.filename).stem,
        file_path=str(file_path),
        file_type=file_type,
        parsed_text=parsed_text,
        is_active=True,
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return resume


@router.post("", response_model=ResumeResponse)
def create_resume(
    current_user: CurrentUser,
    data: ResumeCreate,
    db: Session = Depends(get_db),
):
    # Deactivate existing active resumes
    # if the new resume is marked as active.
    if data.is_active:
        db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_active == True,
        ).update(
            {"is_active": False},
            synchronize_session=False,
        )

    # Uploaded resumes become the active resume automatically.
    db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True,
    ).update(
        {"is_active": False},
        synchronize_session=False,
    )

    resume = Resume(
        user_id=current_user.id,
        **data.model_dump(),
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return resume


@router.get("/active", response_model=ResumeResponse)
def get_active_resume(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    resume = (
        db.query(Resume)
        .filter(
            Resume.user_id == current_user.id,
            Resume.is_active == True,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Active resume not found",
        )

    return resume


@router.get("", response_model=list[ResumeResponse])
def get_resumes(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    resumes = (
        db.query(Resume)
        .filter(
            Resume.user_id == current_user.id,
        )
        .all()
    )

    return resumes


@router.put("/{resume_id}", response_model=ResumeResponse)
def update_resume(
    resume_id: UUID,
    current_user: CurrentUser,
    data: ResumeUpdate,
    db: Session = Depends(get_db),
):
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    update_data = data.model_dump(
        exclude_unset=True,
    )

    # If this resume is being activated,
    # deactivate all other resumes first.
    if update_data.get("is_active") is True:
        db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.id != resume_id,
            Resume.is_active == True,
        ).update(
            {"is_active": False},
            synchronize_session=False,
        )

    for field, value in update_data.items():
        setattr(resume, field, value)

    db.commit()
    db.refresh(resume)

    return resume


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    db.delete(resume)
    db.commit()

    return {
        "message": "Resume deleted successfully",
    }