"""
AI 智能衣柜 - FastAPI 后端入口
"""
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from contextlib import asynccontextmanager

from api.upload import router as upload_router
from api.wardrobe import router as wardrobe_router
from api.config import router as config_router
from api.weather import router as weather_router
from api.recommendation import router as recommendation_router
from api.horoscope import router as horoscope_router
from api.auth import router as auth_router
from api.packing import router as packing_router
from storage.db import init_db
from storage.auth import init_auth_db

from paths import UPLOAD_DIR as _PATHS_UPLOAD_DIR
UPLOAD_DIR = _PATHS_UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ANALYZE_INTERVAL = 120  # segundos entre ciclos de análisis


async def auto_analyze_pending():
    """Analiza automáticamente prendas pendientes cuando hay quota de IA."""
    while True:
        try:
            await asyncio.sleep(ANALYZE_INTERVAL)

            from storage.db import get_all_clothes, update_clothes
            from domain.clothes import ClothesCreate, normalize_category_value
            from services.openai_compatible import analyze_clothes_openai
            from api.upload import UPLOAD_DIR, ALLOWED_CATEGORIES

            from services.key_rotator import get_current_key
            key = await get_current_key()
            if not key:
                continue  # Sin API key, saltar

            # Obtener todas las prendas de todos los usuarios
            # (necesitamos user_id para update_clothes)
            import aiosqlite
            from storage.db import DB_PATH

            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM clothes WHERE analysis_status = 'pending' ORDER BY created_at ASC LIMIT 5"
                )
                pending = await cursor.fetchall()

            for row in pending:
                clothes_id = row["id"]
                user_id = row["user_id"]
                image_filename = row["image_filename"]

                filepath = UPLOAD_DIR / image_filename
                if not filepath.exists():
                    continue

                with open(filepath, "rb") as f:
                    image_bytes = f.read()

                try:
                    semantics = await analyze_clothes_openai(image_bytes)
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
                        image_filename=image_filename,
                        image_filename_thumb=row["image_filename_thumb"] or "",
                        analysis_status="completed",
                    )
                    await update_clothes(clothes_id, updated, user_id)
                    print(f"✅ Auto-análisis completado: prenda {clothes_id}")
                except Exception as e:
                    print(f"⏳ Auto-análisis pendiente (sin quota): {e}")
                    break

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error en auto-análisis: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_auth_db()
    print("✅ Base de datos inicializada")

    task = asyncio.create_task(auto_analyze_pending())
    print("🔍 Auto-análisis de prendas pendientes iniciado")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print("👋 Auto-análisis detenido")


app = FastAPI(
    title="Armario IA",
    description="Armario inteligente personal",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response: Response = await call_next(request)
        except Exception:
            raise
        if request.url.path.startswith("/uploads/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

app.add_middleware(CacheControlMiddleware)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(upload_router, prefix="/api", tags=["上传"])
app.include_router(wardrobe_router, prefix="/api", tags=["衣柜"])
app.include_router(config_router, prefix="/api", tags=["配置"])
app.include_router(weather_router, prefix="/api", tags=["天气"])
app.include_router(recommendation_router, prefix="/api", tags=["AI推荐"])
app.include_router(auth_router, prefix="/api", tags=["认证"])
app.include_router(packing_router, prefix="/api", tags=["Maleta"])
app.include_router(horoscope_router, prefix="/api", tags=["星座运势"])


@app.get("/api")
async def api_info():
    return {
        "message": "Armario IA API",
        "docs": "/docs",
        "endpoints": {
            "auth_login": "POST /api/auth/login",
            "auth_register": "POST /api/auth/register",
            "auth_check": "GET /api/auth/check",
            "auth_logout": "POST /api/auth/logout",
            "upload": "POST /api/upload",
            "wardrobe": "GET /api/wardrobe",
            "wardrobe_by_category": "GET /api/wardrobe/{category}",
            "clothes_detail": "GET /api/clothes/{id}",
            "delete_clothes": "DELETE /api/clothes/{id}",
            "weather": "GET /api/weather",
            "weather_suggestion": "GET /api/weather/suggestion",
            "ai_recommendation": "GET /api/recommendation",
            "daily_horoscope": "GET /api/horoscope/daily",
            "packing_list": "GET /api/maleta"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Static frontend (for Docker/production)
static_dir = Path(__file__).parent / "static"

if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(static_dir / "favicon.ico")

    @app.get("/")
    async def serve_root():
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/"):
            return {"error": "Not Found", "detail": f"Path {full_path} not found"}
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "message": "Backend is running. Frontend static files not found.",
            "api_info": "/api",
            "docs": "/docs"
        }
