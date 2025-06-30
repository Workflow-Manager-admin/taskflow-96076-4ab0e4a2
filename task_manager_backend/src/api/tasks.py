from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .models import (
    SessionLocal,
    Task,
    TaskCreate,
    TaskRead,
    TaskUpdate,
    User,
)
from .auth import get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=TaskRead,
    summary="Create a new task",
    status_code=status.HTTP_201_CREATED,
    description="Creates a new task for the authenticated user.",
)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task for the authenticated user."""
    task = Task(
        title=task_in.title,
        description=task_in.description,
        deadline=task_in.deadline,
        status=task_in.status,
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[TaskRead],
    summary="List all tasks for the authenticated user",
    description=(
        "Retrieves all tasks owned by the authenticated user, "
        "ordered by creation date descending."
    ),
)
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all tasks for the authenticated user."""
    tasks = (
        db.query(Task)
        .filter(Task.owner_id == current_user.id)
        .order_by(Task.created_at.desc())
        .all()
    )
    return tasks


# PUBLIC_INTERFACE
@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Retrieve a task by ID",
    description="Fetch a task by its ID if it belongs to the authenticated user.",
    responses={404: {"description": "Task not found"}},
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a task by ID for the current user."""
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.owner_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# PUBLIC_INTERFACE
@router.put(
    "/{task_id}",
    response_model=TaskRead,
    summary="Update a task by ID",
    description="Update fields of a task belonging to the authenticated user.",
    responses={404: {"description": "Task not found"}},
)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task by ID for the current user."""
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.owner_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update fields if provided
    for field, value in task_update.dict(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


# PUBLIC_INTERFACE
@router.delete(
    "/{task_id}",
    response_model=dict,
    summary="Delete a task by ID",
    description="Delete a specified task if it belongs to the authenticated user.",
    responses={404: {"description": "Task not found"}},
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task by ID for the current user."""
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.owner_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"detail": "Task deleted"}
