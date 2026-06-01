from fastapi import Depends, HTTPException, Header
from app.config import settings

async def verify_admin(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
