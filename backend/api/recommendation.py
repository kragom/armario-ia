"""
AI穿搭推荐 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from services.weather import get_weather, normalize_location_request, DEFAULT_LOCATION_QUERY
from services.recommendation import get_ai_recommendation
from api.deps import get_current_user_id
from pydantic import BaseModel, Field

router = APIRouter()


class RecommendationResponse(BaseModel):
    """推荐响应"""
    weather: dict
    horoscope: Optional[dict] = None
    temperature_rule: Optional[dict] = None
    recommendation_text: str
    outfit_summary: Optional[str] = None
    selection_reasons: Optional[dict] = None
    suggested_top: Optional[dict] = None
    suggested_bottom: Optional[dict] = None
    suggested_shoes: Optional[dict] = None
    suggested_accessories: list[dict] = Field(default_factory=list)
    purchase_suggestions: list[dict] = Field(default_factory=list)
    goal_raw: Optional[str] = None
    goal_normalized: Optional[str] = None


@router.get("/recommendation", response_model=RecommendationResponse)
async def get_outfit_recommendation(
    location: Optional[str] = Query(
        default=None,
        description="城市名 或 经纬度坐标(如 '31.23,121.47' 或 '121.47,31.23')"
    ),
    city: Optional[str] = Query(default=None, description="城市（结构化查询参数）"),
    state: Optional[str] = Query(default=None, description="省/州（结构化查询参数）"),
    country: Optional[str] = Query(default=None, description="国家（结构化查询参数）"),
    goal: Optional[str] = Query(default=None, description="可选，用户本次穿搭目标/场景"),
    user_id: int = Depends(get_current_user_id),
):
    from storage.auth import get_user_by_id
    user = await get_user_by_id(user_id)

    # Usar ubicación del perfil del usuario si no se especificó
    effective_location = location or (user.get("weather_location", "") if user else "") or DEFAULT_LOCATION_QUERY
    effective_zodiac = (user.get("zodiac_sign", "") if user else "") or ""

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

    recommendation = await get_ai_recommendation(weather, zodiac_sign=effective_zodiac, goal=goal, user_id=user_id)
    return recommendation
