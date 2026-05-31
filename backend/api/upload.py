"""
API de subida de imágenes con autenticación
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid

from services.segment import remove_background, generate_thumbnail
from services.removebg import remove_background_api
from services.openai_compatible import analyze_clothes_openai
from storage.config_store import load_config
from domain.clothes import ClothesSemantics, ClothesCreate, ClothesItem, normalize_category_value
from storage.db import add_clothes, get_clothes_by_id
from api.deps import get_current_user_id

router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_CATEGORIES = {"top", "bottom", "shoes", "accessory"}


@router.post("/upload", response_model=ClothesItem)
async def upload_image(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id)):
    """
    上传衣物图片
    
    流程：
    1. 接收图片
    2. 根据配置使用 rembg 或 remove.bg API 去除背景
    3. 使用 LLM Vision 进行语义分析
    4. 保存到数据库
    5. 返回衣物信息
    """
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")
    
    try:
        # 读取原始图片
        raw_bytes = await file.read()
        
        # 加载配置
        config = load_config()
        
        # 根据配置选择背景移除方式
        if config.bg_removal_method == "removebg" and config.removebg_api_key:
            # 使用 remove.bg API
            try:
                processed_bytes = await remove_background_api(
                    raw_bytes, 
                    config.removebg_api_key
                )
            except ValueError as e:
                # 如果 remove.bg 失败，回退到本地处理
                print(f"⚠️ remove.bg API 失败，回退到本地处理: {e}")
                processed_bytes = remove_background(raw_bytes)
        else:
            # 使用本地 rembg
            processed_bytes = remove_background(raw_bytes)
        
        # 使用 OpenAI 兼容 API 进行语义分析
        semantics: ClothesSemantics = await analyze_clothes_openai(processed_bytes)
        
        # Guardar imagen completa en WebP
        filename = f"{uuid.uuid4()}.webp"
        filepath = UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            f.write(processed_bytes)
        
        # Generar y guardar miniatura (thumbnail)
        thumb_filename = f"{uuid.uuid4()}-thumb.webp"
        thumb_path = UPLOAD_DIR / thumb_filename
        thumb_bytes = generate_thumbnail(processed_bytes, size=300)
        with open(thumb_path, "wb") as f:
            f.write(thumb_bytes)
        
        normalized_category = normalize_category_value(semantics.category)
        if normalized_category not in ALLOWED_CATEGORIES:
            normalized_category = "accessory"

        # 保存到数据库
        clothes_data = ClothesCreate(
            category=normalized_category,
            item=semantics.item,
            style_semantics=semantics.style_semantics,
            season_semantics=semantics.season_semantics,
            usage_semantics=semantics.usage_semantics,
            color_semantics=semantics.color_semantics,
            description=semantics.description,
            notes=semantics.notes or "",
            image_filename=filename,
            image_filename_thumb=thumb_filename
        )
        
        clothes_id = await add_clothes(clothes_data, user_id)
        
        # 返回完整的衣物信息
        clothes = await get_clothes_by_id(clothes_id)
        if not clothes:
            raise HTTPException(status_code=500, detail="保存失败")
        
        return clothes
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"图片分析失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")
