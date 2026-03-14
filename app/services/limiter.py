from fastapi import Request, HTTPException
from app.core.redis_client import redis_client

async def rate_limit_user(request: Request):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    current_usage = await redis_client.incr(key)
    if current_usage == 1:
        await redis_client.expire(key, 60)
        
    if current_usage > 10:
        raise HTTPException(status_code=429, detail="Too many requests. Calm down!")