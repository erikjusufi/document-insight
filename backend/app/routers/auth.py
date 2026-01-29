from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.repos.users import UserRepository
from app.db.session import get_session
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.current_user import get_current_user
from app.services.auth_service import AuthService

router = APIRouter()

def get_auth_service() -> AuthService:
    return AuthService(UserRepository())


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    existing = service.repo.get_by_email(session, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = service.register_user(session, payload.email, payload.password)
    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_session),
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    user = service.authenticate_user(session, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = service.create_access_token(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(
    current_user=Depends(get_current_user),
) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email)
