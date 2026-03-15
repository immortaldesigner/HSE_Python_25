import pytest
import asyncio
from datetime import datetime, timedelta

from app.services.security import generate_short_code
from app.models.link import Link
from app.models.expired_link import ExpiredLink
from app.main import delete_expired_links

from datetime import datetime, timedelta

def test_short_code_generation():
    code1 = generate_short_code()
    code2 = generate_short_code()
    assert len(code1) == 6
    assert code1 != code2

def test_expired_links_logic(db_session):
    past_date = datetime.utcnow() - timedelta(days=1)
    link = Link(original_url="https://old.com", short_code="old", expires_at=past_date)
    db_session.add(link)
    db_session.commit()
    
    assert db_session.query(Link).filter_by(short_code="old").first() is not None

def test_short_code_length():
    code = generate_short_code()
    assert len(code) == 6

def test_short_code_uniqueness():
    codes = {generate_short_code() for _ in range(100)}
    assert len(codes) == 100

@pytest.mark.asyncio
async def test_cleanup_task_logic(db_session):
    from app.models.link import Link
    from app.models.expired_link import ExpiredLink
    from unittest.mock import patch
    import app.main

    code = "oldie_unique_99"
    past_date = datetime.utcnow() - timedelta(days=10)
    expired_link = Link(
        original_url="https://expired.com", 
        short_code=code,
        expires_at=past_date,
        created_at=past_date
    )
    db_session.add(expired_link)
    db_session.commit()

    with patch("app.main.SessionLocal", return_value=db_session):
        try:
            await asyncio.wait_for(app.main.delete_expired_links(), timeout=0.5)
        except:
            pass

    db_session.expire_all()
    link_in_db = db_session.query(Link).filter_by(short_code=code).first()
    assert link_in_db is None