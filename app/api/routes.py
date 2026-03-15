import qrcode
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis_client import redis_client
from app.models.link import Link, LinkClick
from app.schemas.link import LinkCreate, LinkUpdate
from app.services.security import get_current_user, get_current_user_optional, generate_short_code
from app.services.limiter import rate_limit_user
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.security import hash_password

router = APIRouter()

async def log_click_task(link_id: int, ip: str, ua: str, db_session_factory):
    db = db_session_factory()
    try:
        new_click = LinkClick(link_id=link_id, ip_address=ip, user_agent=ua)
        db.add(new_click)
        db.query(Link).filter(Link.id == link_id).update({
            "click_count": Link.click_count + 1,
            "last_accessed_at": datetime.utcnow()
        })
        db.commit()
    finally:
        db.close()

@router.post("/register", status_code=201)
async def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(
        username=data.username,
        password=hash_password(data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created", "username": new_user.username}



@router.post("/links/shorten", dependencies=[Depends(rate_limit_user)])
async def create_link(
    data: LinkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional)
):
    short_code = data.custom_alias or generate_short_code()
    
    if db.query(Link).filter(Link.short_code == short_code).first():
        raise HTTPException(status_code=400, detail="Short code already exists")

    new_link = Link(
        original_url=data.original_url,
        short_code=short_code,
        expires_at=data.expires_at,
        user_id=current_user.id if current_user else None
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    return new_link

@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    cached_url = await redis_client.get(f"link:{short_code}")
    
    if cached_url:
        original_url = cached_url.decode("utf-8")
        link = db.query(Link).filter(Link.short_code == short_code).first()
    else:
        link = db.query(Link).filter(Link.short_code == short_code).first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        original_url = link.original_url
        await redis_client.setex(f"link:{short_code}", 3600, original_url)


    from app.core.database import SessionLocal
    background_tasks.add_task(
        log_click_task, link.id, request.client.host, request.headers.get("user-agent"), SessionLocal
    )

    return RedirectResponse(url=original_url)

@router.get("/links/search")
async def search_link(original_url: str = Query(...), db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.original_url == original_url).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link

@router.get("/links/{short_code}/stats")
async def get_link_stats(short_code: str, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    last_clicks = db.query(LinkClick).filter(LinkClick.link_id == link.id).order_by(LinkClick.timestamp.desc()).limit(5).all()
    
    return {
        "original_url": link.original_url,
        "click_count": link.click_count,
        "created_at": link.created_at,
        "last_accessed_at": link.last_accessed_at,
        "recent_activity": last_clicks
    }

@router.get("/links/{short_code}/qr")
async def get_qr_code(short_code: str, request: Request, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
        
    full_url = f"{request.base_url}{short_code}"
    img = qrcode.make(full_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@router.put("/links/{short_code}")
async def update_link(
    short_code: str,
    data: LinkUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this link")

    link.original_url = data.original_url
    db.commit()
    
    await redis_client.delete(f"link:{short_code}")
    
    return link

@router.delete("/links/{short_code}")
async def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")

    db.delete(link)
    db.commit()

    await redis_client.delete(f"link:{short_code}")
    
    return {"message": "Link deleted successfully"}