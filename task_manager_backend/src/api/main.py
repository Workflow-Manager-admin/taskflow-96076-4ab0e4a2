from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any

from .models import init_db, SessionLocal, User, UserCreate, UserRead
from .auth import get_password_hash, create_access_token, authenticate_user

app = FastAPI(
    title="Task Manager Backend",
    description="Backend RESTful APIs for task and user management, including authentication.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utility dependency to get a new DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", tags=["health"])
def health_check():
    return {"message": "Healthy"}


# --- AUTH ROUTES ---


class Token(BaseModel):
    """Response schema for JWT tokens."""
    access_token: str = Field(..., description="JWT access token for authentication")
    token_type: str = Field(..., description="Type of token (always 'bearer')")


@app.post(
    "/register",
    summary="Register new user",
    tags=["auth"],
    response_model=UserRead,
    status_code=201,
)
def register(user_create: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Registers a new user with unique username and a securely hashed password.
    - **username**: Unique username for the new account.
    - **password**: Desired password (minimum 6 chars recommended).
    """
    existing = db.query(User).filter(User.username == user_create.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    user = User(
        username=user_create.username,
        password_hash=get_password_hash(user_create.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
    )


@app.post(
    "/login",
    summary="Authenticate and get JWT access token",
    tags=["auth"],
    response_model=Token,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Any:
    """
    Authenticates a user and returns a JWT access token.
    - **username**: Username
    - **password**: Password
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")
