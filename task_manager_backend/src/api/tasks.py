from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc
from typing import List, Optional
from datetime import datetime
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
    summary="List/search/filter/sort tasks for the authenticated user",
    description=(
        "Retrieves the authenticated user's tasks, supporting flexible search (by query),\n"
        "status filtering, deadline filtering, and sorting options.\n"
        "Examples for query params:\n"
        "- `query=abc` (search title/description for 'abc')\n"
        "- `status=pending` (filter by status)\n"
        "- `deadline_before=2024-07-01T00:00:00` (tasks before date)\n"
        "- `deadline_after=2024-07-01T00:00:00` (tasks after date)\n"
        "- `sort_by=deadline&sort_order=asc`\n"
    ),
)
def list_and_search_tasks(
    query: Optional[str] = Query(
        None,
        description="Text to search in title or description"
    ),
    status: Optional[str] = Query(
        None,
        description="Status to filter by (e.g. 'pending', 'completed')"
    ),
    deadline_before: Optional[datetime] = Query(
        None,
        description="Only tasks with deadline before this datetime"
    ),
    deadline_after: Optional[datetime] = Query(
        None,
        description="Only tasks with deadline after this datetime"
    ),
    sort_by: Optional[str] = Query(
        "created_at",
        description="Field to sort by (created_at, updated_at, deadline, title, status)"
    ),
    sort_order: Optional[str] = Query(
        "desc",
        regex="^(asc|desc)$",
        description="'asc' for ascending or 'desc' for descending sort"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List/search/filter/sort tasks for the authenticated user.

    - Optionally search by text in `title` or `description`
    - Optionally filter by status
    - Optionally filter by deadline (before/after)
    - Optionally sort by specified field and order
    """
    q = db.query(Task).filter(Task.owner_id == current_user.id)

    # Flexible search by text in title or description
    if query:
        search = f"%{query.lower()}%"
        q = q.filter(
            or_(
                Task.title.ilike(search),
                Task.description.ilike(search)
            )
        )

    # Filter by status (exact match)
    if status:
        q = q.filter(Task.status == status)

    # Filter by deadline before/after
    if deadline_before is not None:
        q = q.filter(Task.deadline.isnot(None), Task.deadline <= deadline_before)
    if deadline_after is not None:
        q = q.filter(Task.deadline.isnot(None), Task.deadline >= deadline_after)

    # Sorting
    sort_by_allowed = {"created_at", "updated_at", "deadline", "title", "status"}
    if sort_by in sort_by_allowed:
        sort_field = getattr(Task, sort_by)
    else:
        sort_field = Task.created_at
    if sort_order == "asc":
        q = q.order_by(asc(sort_field))
    else:
        q = q.order_by(desc(sort_field))

    return q.all()


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
@router.patch(
    "/{task_id}/status",
    response_model=TaskRead,
    summary="Partially update task status (mark as completed, pending, etc.)",
    description=(
        "Partially update ONLY the status of the specified task for the authenticated user. "
        "Can be used to mark completed, revert to pending, etc. "
        "Task must belong to current user."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Task status updated"},
        404: {"description": "Task not found"},
        400: {"description": "Invalid status value"},
    },
)
def update_task_status(
    task_id: int,
    status_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Partially update ONLY the status field of the specified task for the authenticated user.

    - **task_id**: ID of the task whose status is to be updated
    - **status_update**: JSON body containing {"status": "new_status"}

    Returns the updated Task object.
    """
    if "status" not in status_update:
        raise HTTPException(status_code=400, detail="Missing status in payload")
    new_status = status_update["status"]
    if not isinstance(new_status, str) or not new_status:
        raise HTTPException(status_code=400, detail="Invalid status value")
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.owner_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = new_status
    db.commit()
    db.refresh(task)
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
