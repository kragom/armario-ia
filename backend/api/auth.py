"""
API de autenticación: login, registro y verificación
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from storage.auth import (
    get_user,
    verify_login,
    set_user_password,
    create_session,
    get_session_user,
    delete_session,
    change_password as storage_change_password,
)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class SetPasswordRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    username: str
    display_name: str
    has_set_password: bool
    is_new_user: bool = False


@router.post("/auth/login")
async def login(req: LoginRequest):
    user = await verify_login(req.username.strip().lower(), req.password)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.get("error"):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    is_new = not user["has_set_password"]
    if is_new:
        await set_user_password(user["username"], req.password)
        user["has_set_password"] = 1

    token = await create_session(user["id"])
    return AuthResponse(
        token=token,
        user_id=user["id"],
        username=user["username"],
        display_name=user["display_name"],
        has_set_password=bool(user["has_set_password"]),
        is_new_user=is_new,
    )


@router.post("/auth/register")
async def register(req: SetPasswordRequest):
    user = await get_user(req.username.strip().lower())
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Contacta al administrador.")
    if user["has_set_password"]:
        raise HTTPException(status_code=400, detail="Este usuario ya tiene contraseña. Usa el login.")

    await set_user_password(user["username"], req.password)
    token = await create_session(user["id"])
    return AuthResponse(
        token=token,
        user_id=user["id"],
        username=user["username"],
        display_name=user["display_name"],
        has_set_password=True,
        is_new_user=True,
    )


@router.get("/auth/check")
async def check_auth(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No autorizado")
    token = authorization.replace("Bearer ", "")
    user_id = await get_session_user(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    from storage.auth import get_user_by_id
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return {
        "user_id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
    }


@router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "")
        await delete_session(token)
    return {"message": "Sesión cerrada"}


@router.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No autorizado")
    token = authorization.replace("Bearer ", "")
    user_id = await get_session_user(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sesión inválida")

    if len(req.new_password) < 1:
        raise HTTPException(status_code=400, detail="La contraseña no puede estar vacía")

    ok = await storage_change_password(user_id, req.current_password, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    return {"message": "Contraseña cambiada correctamente"}