"""
API de subida de imágenes con autenticación
"""
import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from services.segment import remove_background, generate_thumbnail
from services.removebg import remove_background_api
from storage.config_store import load_config
from domain.clothes import ClothesCreate, ClothesItem, normalize_category_value
from storage.db import add_clothes, get_clothes_by_id, update_clothes_analysis, update_clothes
from api.deps import get_current_user_id

router = APIRouter()

from paths import UPLOAD_DIR as _PATHS_UPLOAD_DIR
UPLOAD_DIR = _PATHS_UPLOAD_DIR

ALLOWED_CATEGORIES = {"top", "bottom", "shoes", "accessory", "outerwear"}


@router.post("/upload", response_model=ClothesItem)
async def upload_image(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se admiten imágenes")

    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Archivo vacío")

        # Validar que sea una imagen procesable
        import io
        from PIL import Image
        try:
            with Image.open(io.BytesIO(raw_bytes)) as test_img:
                test_img.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="El archivo no es una imagen válida")

        config = load_config()
        loop = asyncio.get_event_loop()

        # Procesar imagen (eliminar fondo si está habilitado)
        if getattr(config, 'bg_removal_enabled', True):
            if config.bg_removal_method == "removebg" and config.removebg_api_key:
                try:
                    processed_bytes = await remove_background_api(raw_bytes, config.removebg_api_key)
                except Exception as e:
                    print(f"remove.bg API falló, usando local: {e}")
                    processed_bytes = await loop.run_in_executor(None, remove_background, raw_bytes)
            else:
                processed_bytes = await loop.run_in_executor(None, remove_background, raw_bytes)

            # Fallback automático: si rembg deja la imagen casi vacía (>90% transparente), usar la original
            from PIL import Image as PILImage
            import io as _io
            try:
                test_img = PILImage.open(_io.BytesIO(processed_bytes))
                if test_img.mode == "RGBA":
                    pixels = test_img.getdata()
                    total = len(pixels)
                    transparent = sum(1 for p in pixels if p[3] < 10)
                    if transparent / total > 0.9:
                        print("rembg dejó la imagen casi vacía, usando original")
                        processed_bytes = raw_bytes
            except Exception:
                pass
        else:
            processed_bytes = raw_bytes

        filename = f"{uuid.uuid4()}.webp"
        filepath = UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            f.write(processed_bytes)

        thumb_filename = f"{uuid.uuid4()}-thumb.webp"
        thumb_path = UPLOAD_DIR / thumb_filename
        thumb_bytes = await loop.run_in_executor(None, generate_thumbnail, processed_bytes, 300)
        with open(thumb_path, "wb") as f:
            f.write(thumb_bytes)

        # Nombre por defecto: nombre original del archivo (sin extensión)
        original_name = Path(file.filename or "prenda").stem
        item_name = original_name.replace("_", " ").replace("-", " ").strip() or "Prenda"

        clothes_data = ClothesCreate(
            category="top",
            item=item_name,
            style_semantics=[],
            season_semantics=[],
            usage_semantics=[],
            color_semantics="",
            description="",
            notes="",
            image_filename=filename,
            image_filename_thumb=thumb_filename,
            analysis_status="pending",
        )

        clothes_id = await add_clothes(clothes_data, user_id)

        clothes = await get_clothes_by_id(clothes_id, user_id)
        if not clothes:
            raise HTTPException(status_code=500, detail="Error al guardar")
        return clothes

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en upload: {e}")
        raise HTTPException(status_code=500, detail=f"Error del servidor: {str(e)}")


@router.post("/clothes/{clothes_id}/analyze", response_model=ClothesItem)
async def retry_analysis(clothes_id: int, user_id: int = Depends(get_current_user_id)):
    from services.openai_compatible import analyze_clothes_openai
    from domain.clothes import ClothesSemantics

    clothes = await get_clothes_by_id(clothes_id, user_id)
    if not clothes:
        raise HTTPException(status_code=404, detail="Prenda no encontrada")

    filepath = UPLOAD_DIR / clothes.image_url.replace("/uploads/", "")
    if not filepath.exists():
        raise HTTPException(status_code=400, detail="Imagen no encontrada en el servidor")

    with open(filepath, "rb") as f:
        image_bytes = f.read()

    try:
        semantics = await analyze_clothes_openai(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=429, detail=f"Sin crédito de IA: {str(e)}")

    normalized_category = normalize_category_value(semantics.category)
    if normalized_category not in ALLOWED_CATEGORIES:
        normalized_category = "accessory"

    updated = ClothesCreate(
        category=normalized_category,
        item=semantics.item,
        style_semantics=semantics.style_semantics,
        season_semantics=semantics.season_semantics,
        usage_semantics=semantics.usage_semantics,
        color_semantics=semantics.color_semantics,
        description=semantics.description,
        notes=semantics.notes or "",
        image_filename=clothes.image_url.replace("/uploads/", ""),
        image_filename_thumb=clothes.thumbnail_url.replace("/uploads/", ""),
        analysis_status="completed",
    )
    await update_clothes(clothes_id, updated, user_id)

    result = await get_clothes_by_id(clothes_id, user_id)
    if not result:
        raise HTTPException(status_code=500, detail="Error al obtener la prenda")
    return result


@router.put("/clothes/{clothes_id}/metadata", response_model=ClothesItem)
async def update_clothes_metadata_endpoint(
    clothes_id: int,
    category: str = "",
    item: str = "",
    notes: str = "",
    user_id: int = Depends(get_current_user_id),
):
    from storage.db import update_clothes_metadata, get_clothes_by_id

    if not category or not item:
        raise HTTPException(status_code=400, detail="Categoría y nombre son obligatorios")

    cat = normalize_category_value(category)
    if cat not in ALLOWED_CATEGORIES:
        cat = "accessory"

    ok = await update_clothes_metadata(clothes_id, cat, item, notes, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Prenda no encontrada")

    result = await get_clothes_by_id(clothes_id, user_id)
    if not result:
        raise HTTPException(status_code=500, detail="Error al obtener la prenda")
    return result
