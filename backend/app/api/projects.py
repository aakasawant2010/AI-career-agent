from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post("", response_model=ProjectResponse)
def create_project(
    current_user: CurrentUser,
    data: ProjectCreate,
    db: Session = Depends(get_db),
):
    project = Project(
        user_id=current_user.id,
        **data.model_dump(),
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get("", response_model=list[ProjectResponse])
def get_projects(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(Project).where(
            Project.user_id == current_user.id
        )
    )

    return result.scalars().all()


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    current_user: CurrentUser,
    data: ProjectCreate,
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    for field, value in data.model_dump().items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    db.delete(project)
    db.commit()

    return {
        "message": "Project deleted successfully"
    }