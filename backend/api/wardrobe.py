"""
API de armario - gestión de prendas por usuario
"""
from fastapi import APIRouter, HTTPException, Depends

from domain.clothes import ClothesItem, WardrobeResponse, ClothesCreate
from domain.clothes import normalize_category_value
from storage.db import (
    get_all_clothes,
    get_clothes_by_category,
    get_clothes_by_id,
    delete_clothes,
    update_clothes
)
from api.deps import get_current_user_id
from pydantic import BaseModel

router = APIRouter()

WARDROBE_OPTIONS_CATEGORIES = ["top", "bottom", "shoes", "accessory"]
WARDROBE_OPTIONS_STYLES = ["casual", "formal", "sporty", "elegant", "bohemian", "minimal", "vintage", "romantic", "edgy", "preppy", "business", "artistic"]
WARDROBE_OPTIONS_SEASONS = ["primavera", "verano", "otoño", "invierno", "todas"]
WARDROBE_OPTIONS_USAGES = ["daily", "commute", "sport", "party", "work", "travel", "home", "beach", "date", "night"]
WARDROBE_OPTIONS_COLORS = ["negro", "blanco", "gris", "rojo", "azul", "verde", "amarillo", "rosa", "naranja", "marrón", "morado", "beige", "dorado", "plateado", "estampado"]


class WardrobeOptionsResponse(BaseModel):
    categories: list[str]
    styles: list[str]
    seasons: list[str]
    usages: list[str]
    colors: list[str]


@router.get("/wardrobe/options", response_model=WardrobeOptionsResponse)
async def get_wardrobe_options():
    return WardrobeOptionsResponse(
        categories=WARDROBE_OPTIONS_CATEGORIES,
        styles=WARDROBE_OPTIONS_STYLES,
        seasons=WARDROBE_OPTIONS_SEASONS,
        usages=WARDROBE_OPTIONS_USAGES,
        colors=WARDROBE_OPTIONS_COLORS,
    )


@router.get("/wardrobe", response_model=WardrobeResponse)
async def get_wardrobe(user_id: int = Depends(get_current_user_id)):
    all_clothes = await get_all_clothes(user_id)

    tops: list[ClothesItem] = []
    bottoms: list[ClothesItem] = []
    shoes: list[ClothesItem] = []
    accessories: list[ClothesItem] = []

    for clothes in all_clothes:
        category = normalize_category_value(clothes.category)
        if category == "top":
            tops.append(clothes)
        elif category == "bottom":
            bottoms.append(clothes)
        elif category == "shoes":
            shoes.append(clothes)
        elif category == "accessory":
            accessories.append(clothes)

    return WardrobeResponse(
        tops=tops, bottoms=bottoms, shoes=shoes, accessories=accessories
    )


@router.get("/wardrobe/{category}", response_model=list[ClothesItem])
async def get_wardrobe_category(category: str, user_id: int = Depends(get_current_user_id)):
    category = normalize_category_value(category)
    if category not in ["top", "bottom", "shoes", "accessory"]:
        raise HTTPException(status_code=400, detail="Categoría debe ser top, bottom, shoes o accessory")
    return await get_clothes_by_category(category, user_id)


@router.get("/clothes/{clothes_id}", response_model=ClothesItem)
async def get_clothes(clothes_id: int, user_id: int = Depends(get_current_user_id)):
    clothes = await get_clothes_by_id(clothes_id, user_id)
    if not clothes:
        raise HTTPException(status_code=404, detail="Prenda no encontrada")
    return clothes


@router.put("/clothes/{clothes_id}")
async def update_clothes_item(clothes_id: int, clothes: ClothesCreate, user_id: int = Depends(get_current_user_id)):
    success = await update_clothes(clothes_id, clothes, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prenda no encontrada")
    return {"message": "Actualizada", "id": clothes_id}


@router.delete("/clothes/{clothes_id}")
async def remove_clothes(clothes_id: int, user_id: int = Depends(get_current_user_id)):
    success = await delete_clothes(clothes_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prenda no encontrada")
    return {"message": "Eliminada", "id": clothes_id}
