from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.core.rate_limit import llm_rate_limit
from app.models.interview import InterviewSession
from app.schemas.interview import (
    AnswerRequest,
    InterviewSessionCreate,
    InterviewSessionListItem,
    InterviewSessionResponse,
    QuestionResponse,
)
from app.services import interview_service as svc

router = APIRouter(prefix="/interviews", tags=["Interview Agent"])


def _full(db: Session, session: InterviewSession) -> InterviewSessionResponse:
    data = InterviewSessionResponse.model_validate(session)
    data.questions = [QuestionResponse.model_validate(q) for q in svc.session_questions(db, session.id)]
    return data


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=exc.args[0] if exc.args else "Not found")
    return HTTPException(status_code=409 if "completed" in str(exc) else 400, detail=str(exc))


@router.post("/sessions", response_model=InterviewSessionResponse, status_code=201,
             dependencies=[Depends(llm_rate_limit)])
def start_session(data: InterviewSessionCreate, current_user: CurrentUser, db: Session = Depends(get_db)):
    """Generate a practice interview for a job (or an application's job)."""
    try:
        session = svc.create_session(
            db, current_user.id, job_id=data.job_id, application_id=data.application_id,
            mode=data.mode, difficulty=data.difficulty, num_questions=data.num_questions,
        )
    except (LookupError, svc.InterviewError) as exc:
        raise _http(exc) from exc
    return _full(db, session)


@router.get("/sessions", response_model=list[InterviewSessionListItem])
def list_sessions(
    current_user: CurrentUser,
    application_id: UUID | None = None,
    job_id: UUID | None = None,
    status: str | None = Query(default=None, description="IN_PROGRESS or COMPLETED"),
    db: Session = Depends(get_db),
):
    stmt = (
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    if application_id:
        stmt = stmt.where(InterviewSession.application_id == application_id)
    if job_id:
        stmt = stmt.where(InterviewSession.job_id == job_id)
    if status:
        stmt = stmt.where(InterviewSession.status == status.upper())
    return list(db.scalars(stmt))


@router.get("/sessions/{session_id}", response_model=InterviewSessionResponse)
def get_session(session_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)):
    try:
        return _full(db, svc.get_session(db, current_user.id, session_id))
    except LookupError as exc:
        raise _http(exc) from exc


@router.post("/sessions/{session_id}/questions/{question_id}/answer", response_model=QuestionResponse,
             dependencies=[Depends(llm_rate_limit)])
def answer(session_id: UUID, question_id: UUID, data: AnswerRequest, current_user: CurrentUser,
           db: Session = Depends(get_db)):
    """Submit (or revise) an answer and get scored feedback. Practice only; nothing is sent anywhere."""
    try:
        return svc.answer_question(db, current_user.id, session_id, question_id, data.answer)
    except (LookupError, svc.InterviewError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{session_id}/complete", response_model=InterviewSessionResponse)
def complete(session_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)):
    try:
        return _full(db, svc.complete_session(db, current_user.id, session_id))
    except (LookupError, ValueError) as exc:
        raise _http(exc) from exc


@router.get("/sessions/{session_id}/report")
def report(session_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)):
    try:
        session = svc.get_session(db, current_user.id, session_id)
    except LookupError as exc:
        raise _http(exc) from exc
    if session.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Complete the session to generate its report")
    return {"session_id": session.id, "job_id": session.job_id, "completed_at": session.completed_at, **session.summary}
