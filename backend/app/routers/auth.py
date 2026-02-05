from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.repos.documents import DocumentRepository
from app.db.repos.users import UserRepository
from app.db.session import get_session
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.current_user import get_current_user
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService

router = APIRouter()

def get_auth_service() -> AuthService:
    return AuthService(UserRepository())


def get_document_service() -> DocumentService:
    return DocumentService(DocumentRepository())


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
    service: AuthService = Depends(get_auth_service),
    document_service: DocumentService = Depends(get_document_service),
) -> UserResponse:
    existing = service.repo.get_by_email(session, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = service.register_user(session, payload.email, payload.password)
    document_service.import_sample_documents(session, user.id)
    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_session),
    service: AuthService = Depends(get_auth_service),
    document_service: DocumentService = Depends(get_document_service),
) -> TokenResponse:
    user = service.authenticate_user(session, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    document_service.import_sample_documents(session, user.id)
    token = service.create_access_token(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(
    current_user=Depends(get_current_user),
) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email)
