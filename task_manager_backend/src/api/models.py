from typing import Optional
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pydantic import BaseModel, Field


Base = declarative_base()

DATABASE_URL = "sqlite:///./task_manager.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    """
    ORM model for a user in the task manager.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")


class Task(Base):
    """
    ORM model for a task in the task manager.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    status = Column(String(32), default="pending", nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tasks")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# PUBLIC_INTERFACE
class UserBase(BaseModel):
    """Base Pydantic schema for User."""
    username: str = Field(..., description="Unique username of the user.")


# PUBLIC_INTERFACE
class UserCreate(UserBase):
    """Pydantic schema for creating a new user."""
    password: str = Field(..., description="Password for the new user.")


# PUBLIC_INTERFACE
class UserRead(UserBase):
    """Pydantic schema for reading user information."""
    id: int
    is_active: bool

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
class TaskBase(BaseModel):
    """Base Pydantic schema for Task."""
    title: str = Field(..., description="Title of the task.")
    description: Optional[str] = Field(None, description="Description of the task.")
    deadline: Optional[datetime] = Field(None, description="Deadline for the task.")
    status: str = Field(default="pending", description="Task status (pending, completed, etc.).")


# PUBLIC_INTERFACE
class TaskCreate(TaskBase):
    """Pydantic schema for creating a new task."""
    pass


# PUBLIC_INTERFACE
class TaskUpdate(BaseModel):
    """Pydantic schema for updating a task."""
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None


# PUBLIC_INTERFACE
class TaskRead(TaskBase):
    """Pydantic schema for reading task information."""
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
def init_db():
    """
    Initializes the database. Creates all tables.
    Call this at app startup to ensure schema exists.
    """
    Base.metadata.create_all(bind=engine)
