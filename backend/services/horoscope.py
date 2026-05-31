"""
Servicio de horóscopo - genera horóscopo determinista por signo zodiacal
"""
from datetime import datetime
from typing import Optional

from storage.db import (
    get_horoscope_record,
    upsert_horoscope_source,
)
from services.weather import WeatherInfo

ZODIAC_NAMES = {
    "aries": "Aries",
    "taurus": "Tauro",
    "gemini": "Géminis",
    "cancer": "Cáncer",
    "leo": "Leo",
    "virgo": "Virgo",
    "libra": "Libra",
    "scorpio": "Escorpio",
    "sagittarius": "Sagitario",
    "capricorn": "Capricornio",
    "aquarius": "Acuario",
    "pisces": "Piscis"
}

ZODIAC_ALIASES = {
    "aries": "aries",
    "tauro": "taurus",
    "taurus": "taurus",
    "geminis": "gemini",
    "gemini": "gemini",
    "cancer": "cancer",
    "cáncer": "cancer",
    "leo": "leo",
    "virgo": "virgo",
    "libra": "libra",
    "escorpio": "scorpio",
    "scorpio": "scorpio",
    "sagitario": "sagittarius",
    "sagittarius": "sagittarius",
    "capricornio": "capricorn",
    "capricorn": "capricorn",
    "acuario": "aquarius",
    "aquarius": "aquarius",
    "piscis": "pisces",
    "pisces": "pisces"
}

ZODIAC_TRAITS = {
    "aries": "acción",
    "taurus": "estabilidad",
    "gemini": "comunicación",
    "cancer": "empatía",
    "leo": "expresión",
    "virgo": "detalle",
    "libra": "equilibrio",
    "scorpio": "intuición",
    "sagittarius": "aventura",
    "capricorn": "disciplina",
    "aquarius": "creatividad",
    "pisces": "imaginación"
}

DEFAULT_COLORS = {
    "aries": "rojo coral",
    "taurus": "verde musgo",
    "gemini": "amarillo limón",
    "cancer": "blanco perla",
    "leo": "ámbar",
    "virgo": "azul niebla",
    "libra": "rosa sakura",
    "scorpio": "burdeos",
    "sagittarius": "azul índigo",
    "capricorn": "gris piedra",
    "aquarius": "azul eléctrico",
    "pisces": "azul marino"
}


def normalize_zodiac_sign(sign: Optional[str]) -> Optional[str]:
    if not sign:
        return None
    normalized = sign.strip().lower().replace(" ", "")
    if not normalized:
        return None
    return ZODIAC_ALIASES.get(normalized)


def build_weather_tip(weather: WeatherInfo) -> str:
    condition = weather.condition or ""
    feels_like = weather.feelsLike

    if "lluvia" in condition.lower() or "雨" in condition:
        return "Hoy podría llover, lleva un paraguas ligero y calzado antideslizante."
    if "nieve" in condition.lower() or "雪" in condition:
        return "Hace frío y podría nevar, abrígate bien y cuida el calzado."
    if feels_like >= 30:
        return "Sensación térmica alta, elige tejidos transpirables e hidrátate."
    if feels_like <= 8:
        return "Sensación térmica baja, usa capas y protege cuello y tobillos."
    if "sol" in condition.lower() or "晴" in condition:
        return "Buena luz solar, puedes complementar con accesorios de protección solar."

    return "Temperatura agradable, busca comodidad sin perder estilo."


def _to_lucky_number(raw_value: object, default: int = 7) -> int:
    try:
        lucky_number = int(raw_value)
    except Exception:
        lucky_number = default
    return min(max(lucky_number, 1), 99)


def fallback_horoscope_source(sign_key: str, weather: WeatherInfo, today: str) -> dict:
    day_seed = datetime.now().toordinal()
    sign_index = list(ZODIAC_NAMES.keys()).index(sign_key)
    lucky_number = ((day_seed + sign_index * 7) % 89) + 11
    trait = ZODIAC_TRAITS.get(sign_key, "ritmo")

    return {
        "current_date": today,
        "date_range": "",
        "description": f"Hoy tu palabra clave es «{trait}». Concéntrate en lo más importante y obtendrás resultados estables.",
        "mood": "estable y positivo",
        "color": DEFAULT_COLORS.get(sign_key, "azul claro"),
        "lucky_number": lucky_number,
        "lucky_time": "",
        "compatibility": "",
        "weather_tip": build_weather_tip(weather),
    }


def build_suggestion(weather: WeatherInfo, source_payload: dict) -> str:
    weather_tip = str(source_payload.get("weather_tip", "")).strip() or build_weather_tip(weather)
    lucky_time = str(source_payload.get("lucky_time", "")).strip()
    if lucky_time:
        return f"Momento recomendado: {lucky_time}. {weather_tip}"
    return weather_tip


def build_horoscope_response(
    *,
    today: str,
    sign_key: str,
    source_payload: dict,
    weather: WeatherInfo,
) -> dict:
    zodiac_name = ZODIAC_NAMES.get(sign_key, sign_key)
    summary = str(source_payload.get("description", "")).strip() or "Hoy es un día para mantener el equilibrio y centrarte en lo esencial."
    mood = str(source_payload.get("mood", "")).strip() or "estable"
    lucky_color = str(source_payload.get("color", "")).strip() or DEFAULT_COLORS.get(sign_key, "azul claro")
    lucky_number = _to_lucky_number(source_payload.get("lucky_number", 7))

    return {
        "date": today,
        "zodiac_sign": sign_key,
        "zodiac_name": zodiac_name,
        "is_configured": True,
        "summary": summary,
        "mood": mood,
        "lucky_color": lucky_color,
        "lucky_number": lucky_number,
        "suggestion": build_suggestion(weather, source_payload),
        "source_provider": "fallback",
    }


async def get_daily_horoscope(
    weather: WeatherInfo,
    zodiac_sign: str,
) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")

    sign_key = normalize_zodiac_sign(zodiac_sign)
    if not sign_key:
        return {
            "date": today,
            "zodiac_sign": "",
            "zodiac_name": "No configurado",
            "is_configured": False,
            "summary": "Aún no has configurado tu signo zodiacal. Ve a Ajustes para elegirlo y recibir tu horóscopo.",
            "mood": "---",
            "lucky_color": "blanco",
            "lucky_number": 6,
            "suggestion": build_weather_tip(weather),
            "source_provider": "none",
        }

    zodiac_name = ZODIAC_NAMES.get(sign_key, sign_key)

    cached = await get_horoscope_record(record_date=today, zodiac_sign=sign_key)
    if cached:
        source_payload = cached.get("source_payload") or {}
        source_provider = cached.get("source_provider", "cached")
    else:
        source_payload = fallback_horoscope_source(sign_key=sign_key, weather=weather, today=today)
        source_provider = "fallback"

        await upsert_horoscope_source(
            record_date=today,
            zodiac_sign=sign_key,
            zodiac_name=zodiac_name,
            source_provider=source_provider,
            source_payload=source_payload,
        )

    return build_horoscope_response(
        today=today,
        sign_key=sign_key,
        source_payload=source_payload,
        weather=weather,
    )
