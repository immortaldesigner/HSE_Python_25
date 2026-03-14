from sqlalchemy import Column, Integer, String, DateTime

from app.core.database import Base


class ExpiredLink(Base):
    __tablename__ = "expired_links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=True)
    last_accessed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=False)
    user_id = Column(Integer, nullable=True)