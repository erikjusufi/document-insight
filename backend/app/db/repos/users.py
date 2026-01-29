from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    def get_by_email(self, session: Session, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, session: Session, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return session.execute(stmt).scalar_one_or_none()

    def create(self, session: Session, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def update_password(self, session: Session, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
