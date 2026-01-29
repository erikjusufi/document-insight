from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import User
from app.db.repos.users import UserRepository

pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")


class AuthService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    def register_user(self, session: Session, email: str, password: str) -> User:
        hashed_password = pwd_context.hash(password)
        return self.repo.create(session, email=email, hashed_password=hashed_password)

    def authenticate_user(self, session: Session, email: str, password: str) -> User | None:
        user = self.repo.get_by_email(session, email)
        if not user:
            return None
        if not pwd_context.verify(password, user.hashed_password):
            return None
        if pwd_context.needs_update(user.hashed_password):
            new_hash = pwd_context.hash(password)
            self.repo.update_password(session, user, new_hash)
        return user

    def create_access_token(self, user: User) -> str:
        settings = get_settings()
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
        payload = {"sub": str(user.id), "email": user.email, "exp": expire}
        return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> dict:
        settings = get_settings()
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])

    def get_user_from_token(self, session: Session, token: str) -> User | None:
        try:
            payload = self.decode_token(token)
        except JWTError:
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            return None
        return self.repo.get_by_id(session, user_id_int)
