"""
rembg 背景移除服务
"""
from rembg import remove
from PIL import Image
import io


def remove_background(image_bytes: bytes, as_webp: bool = True) -> bytes:
    """
    使用 rembg 移除图片背景，保存为 WebP 格式（更小更快）
    
    Args:
        image_bytes: 原始图片的字节数据
        as_webp: 是否保存为 WebP (True) 或 PNG (False)
        
    Returns:
        去除背景后的图片字节数据 (WebP por defecto)
    """
    input_img = Image.open(io.BytesIO(image_bytes))
    output = remove(input_img)
    
    buf = io.BytesIO()
    if as_webp:
        output.save(buf, format="WEBP", quality=85, method=6)
    else:
        output.save(buf, format="PNG")
    return buf.getvalue()


def generate_thumbnail(image_bytes: bytes, size: int = 300) -> bytes:
    """
    Genera una miniatura WebP a partir de una imagen procesada.
    
    Args:
        image_bytes: imagen procesada (WebP o PNG)
        size: ancho máximo en píxeles
        
    Returns:
        miniatura en WebP
    """
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=75, method=6)
    return buf.getvalue()
