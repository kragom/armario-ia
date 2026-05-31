"""
Dependencias compartidas para autenticación
"""
from fastapi import Header, HTTPException
from typing import Optional

from storage.auth import get_session_user, get_user_by_id


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="No autorizado")
    token = authorization.replace("Bearer ", "")
    user_id = await get_session_user(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    return user_id


async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No autorizado")
    token = authorization.replace("Bearer ", "")
    user_id = await get_session_user(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user