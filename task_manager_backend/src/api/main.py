from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any

from .models import init_db, SessionLocal, User, UserCreate, UserRead
from .auth import get_password_hash, create_access_token, authenticate_user
from .tasks import router as tasks_router

app = FastAPI(
    title="Task Manager Backend",
    description="Backend RESTful APIs for task and user management, including authentication.",
    version="1.0.0",
    contact={
        "name": "Task Manager Backend Team",
        "email": "support@example.com",
    },
    summary="API for managing users and tasks with authentication and robust error responses."
)

# CORS configuration for cross-origin frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom error handling for common errors and improved OpenAPI docs


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Return HTTP errors in a consistent JSON structure with detail and code."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": exc.status_code,
            "type": "HTTPException",
            "path": str(request.url)
        },
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette-based HTTPExceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": exc.status_code,
            "type": "HTTPException",
            "path": str(request.url)
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle pydantic validation errors for request bodies and query parameters."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "code": 422,
            "type": "ValidationError",
            "path": str(request.url),
            "details": exc.errors()
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Generic error catch-all for uncaught/unknown exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "code": 500,
            "type": type(exc).__name__,
            "path": str(request.url)
        },
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
    """Initializes the database schema."""
    init_db()


@app.get(
    "/",
    tags=["health"],
    summary="Health check endpoint",
    description="Check health status to confirm backend is running.",
    response_description="Service health response."
)
def health_check():
    """Returns basic health check message."""
    return {"message": "Healthy"}


# --- AUTH ROUTES ---


app.include_router(tasks_router)


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
    response_description="The registered user's information.",
    responses={
        201: {"description": "User successfully registered", "model": UserRead},
        400: {"description": "Username already registered"},
        422: {"description": "Validation error"},
    },
)
def register(user_create: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Registers a new user with unique username and a securely hashed password.
    - **username**: Unique username for the new account.
    - **password**: Desired password (minimum 6 chars recommended).
    Returns the created user.
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
    response_description="JWT token for authenticated access",
    responses={
        200: {"description": "Successful login and JWT retrieval", "model": Token},
        401: {"description": "Incorrect username or password"},
        422: {"description": "Validation error"},
    },
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
