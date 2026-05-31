"""
Servicio de eliminación de fondo con rembg (opcional)
"""
from PIL import Image
import io


def _remove_bg(input_img):
    """Intenta eliminar fondo con rembg. Si no está disponible, retorna None."""
    try:
        from rembg import remove
        return remove(input_img)
    except Exception as exc:
        print(f"rembg no disponible: {exc}")
        return None


def remove_background(image_bytes: bytes, as_webp: bool = True) -> bytes:
    input_img = Image.open(io.BytesIO(image_bytes))

    output = _remove_bg(input_img)
    if output is None:
        output = input_img

    buf = io.BytesIO()
    if as_webp:
        output.save(buf, format="WEBP", quality=85, method=6)
    else:
        output.save(buf, format="PNG")
    return buf.getvalue()


def generate_thumbnail(image_bytes: bytes, size: int = 300) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=75, method=6)
    return buf.getvalue()
