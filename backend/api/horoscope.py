"""
API de horóscopo diario
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from services.horoscope import get_daily_horoscope
from services.weather import get_weather, normalize_location_request, DEFAULT_LOCATION_QUERY
from api.deps import get_current_user_id
from storage.auth import get_user_by_id


router = APIRouter()


@router.get("/horoscope/daily")
async def get_today_horoscope(
    location: Optional[str] = Query(
        default=None,
        description="Ciudad o coordenadas (por defecto usa la del perfil)",
    ),
    city: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    user_id: int = Depends(get_current_user_id),
):
    user = await get_user_by_id(user_id)

    effective_location = location or (user.get("weather_location", "") if user else "") or DEFAULT_LOCATION_QUERY
    zodiac_sign = (user or {}).get("zodiac_sign", "") or ""

    normalized_location, validation_error = normalize_location_request(
        location=effective_location,
        city=city,
        state=state,
        country=country,
    )
    if validation_error:
        raise HTTPException(status_code=422, detail=validation_error)

    weather = await get_weather(normalized_location)
    if not weather:
        raise HTTPException(status_code=500, detail="No se pudo obtener el clima")

    return await get_daily_horoscope(
        weather=weather,
        zodiac_sign=zodiac_sign,
    )
