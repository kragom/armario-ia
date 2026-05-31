from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from services.weather import get_weather, normalize_location_request, DEFAULT_LOCATION_QUERY
from api.deps import get_current_user_id
from services.packing import generate_packing_list
from pydantic import BaseModel

router = APIRouter()


class DayOutfit(BaseModel):
    day: int
    date: str
    weather_forecast: str
    top: Optional[dict]
    bottom: Optional[dict]
    shoes: Optional[dict]
    accessories: list[dict]


class PackingResponse(BaseModel):
    days: list[DayOutfit]
    trip_summary: str
    items_not_to_forget: list[str]
    total_items: int


@router.get("/maleta", response_model=PackingResponse)
async def get_packing_list(
    days: int = Query(default=3, ge=1, le=14, description="Número de días del viaje"),
    location: str = Query(default=DEFAULT_LOCATION_QUERY, description="Destino del viaje"),
    user_id: int = Depends(get_current_user_id),
):
    normalized_location, validation_error = normalize_location_request(location=location)
    if validation_error:
        raise HTTPException(status_code=422, detail=validation_error)

    weather = await get_weather(normalized_location)
    if not weather:
        raise HTTPException(status_code=500, detail="No se pudo obtener el clima")

    result = await generate_packing_list(
        days=days,
        weather=weather,
        user_id=user_id,
        location=normalized_location,
    )

    return result
