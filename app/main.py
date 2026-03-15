import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.routes import router
from app.core.database import Base, engine, SessionLocal
from app.models.link import Link
from app.models.expired_link import ExpiredLink
from app.core.config import UNUSED_LINK_DAYS

Base.metadata.create_all(bind=engine)

async def delete_expired_links():
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            expired_links = db.query(Link).filter(Link.expires_at != None, Link.expires_at < now).all()
            unused_links = db.query(Link).filter(
                ((Link.last_accessed_at != None) & (Link.last_accessed_at < now - timedelta(days=UNUSED_LINK_DAYS))) |
                ((Link.last_accessed_at == None) & (Link.created_at < now - timedelta(days=UNUSED_LINK_DAYS)))
            ).all()

            for link in (expired_links + unused_links):
                expired = ExpiredLink(
                    original_url=link.original_url, short_code=link.short_code,
                    created_at=link.created_at, last_accessed_at=link.last_accessed_at,
                    expires_at=link.expires_at, deleted_at=now, user_id=link.user_id
                )
                db.add(expired)
                db.delete(link)
            db.commit()
        finally:
            db.close()
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(delete_expired_links())
    yield
    cleanup_task.cancel()

app = FastAPI(lifespan=lifespan)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "URL Shortener API"}