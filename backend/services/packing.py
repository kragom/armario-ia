import json
from datetime import datetime, timedelta
from typing import Optional

import httpx

from domain.clothes import normalize_category_value
from services.weather import WeatherInfo
from services.recommendation import get_ai_recommendation
from storage.config_store import load_config
from storage.db import get_all_clothes

SEASON_MONTHS = {
    "primavera": [3, 4, 5],
    "verano": [6, 7, 8],
    "otoño": [9, 10, 11],
    "invierno": [12, 1, 2],
}


def _current_season() -> str:
    month = datetime.now().month
    for season, months in SEASON_MONTHS.items():
        if month in months:
            return season
    return "primavera"


async def generate_packing_list(
    days: int,
    weather: WeatherInfo,
    user_id: int,
    location: str = "",
) -> dict:
    config = load_config()
    today = datetime.now()
    all_items = await get_all_clothes(user_id)

    items_by_cat = {"top": [], "bottom": [], "shoes": [], "accessory": []}
    for item in all_items:
        cat = normalize_category_value(item.category)
        if cat in items_by_cat:
            items_by_cat[cat].append({
                "id": item.id,
                "name": item.item,
                "style": item.style_semantics,
                "season": item.season_semantics,
                "color": item.color_semantics,
                "image_url": item.image_url,
                "thumbnail_url": item.thumbnail_url,
            })

    total = sum(len(v) for v in items_by_cat.values())
    items_summary = ", ".join(
        f"{len(v)} {cat}" for cat, v in items_by_cat.items() if v
    )

    forecasts = []
    forecast_details = []
    for d in range(days):
        day_date = today + timedelta(days=d)
        date_str = day_date.strftime("%Y-%m-%d")
        if d == 0:
            w_desc = weather.condition or "despejado"
            w_temp = weather.temperature
            w_feels = weather.feelsLike
            w_hum = weather.humidity
        else:
            w_desc = weather.condition or "similar"
            w_temp = weather.temperature
            w_feels = weather.feelsLike
            w_hum = weather.humidity

        forecasts.append({
            "day": d + 1,
            "date": date_str,
            "weather": f"{w_desc}, {w_temp}°C (sensación {w_feels}°C), humedad {w_hum}%",
        })
        forecast_details.append(
            f"Día {d+1} ({date_str}): {w_desc}, {w_temp}°C"
        )

    if config.api_key:
        llm_result = await _generate_via_llm(
            config=config,
            days=days,
            location=location,
            forecasts=forecasts,
            items_top=items_by_cat["top"],
            items_bottom=items_by_cat["bottom"],
            items_shoes=items_by_cat["shoes"],
            items_accessory=items_by_cat["accessory"],
            season=_current_season(),
            weather=weather,
        )
        if llm_result:
            return llm_result

    return _generate_fallback(
        days=days,
        forecasts=forecasts,
        items_by_cat=items_by_cat,
        total=total,
        items_summary=items_summary,
    )


async def _generate_via_llm(
    config,
    days: int,
    location: str,
    forecasts: list,
    items_top: list,
    items_bottom: list,
    items_shoes: list,
    items_accessory: list,
    season: str,
    weather: WeatherInfo,
) -> Optional[dict]:
    api_base = config.api_base.rstrip("/")
    if not api_base.endswith("/v1"):
        api_base = f"{api_base}/v1"

    prompt = f"""Eres un estilista personal. Genera una lista de equipaje para un viaje de {days} días.

Destino: {location or "no especificado"}
Temporada: {season}
Clima general: {weather.condition or "variable"}, {weather.temperature}°C

Pronóstico por día:
{chr(10).join(f['weather'] for f in forecasts)}

Armario disponible:
- Camisetas/tops: {json.dumps([{k: v[k] for k in ('name','style','color') if k in v} for v in items_top], ensure_ascii=False)}
- Pantalones/faldas: {json.dumps([{k: v[k] for k in ('name','style','color') if k in v} for v in items_bottom], ensure_ascii=False)}
- Zapatos: {json.dumps([{k: v[k] for k in ('name','style','color') if k in v} for v in items_shoes], ensure_ascii=False)}
- Accesorios: {json.dumps([{k: v[k] for k in ('name','style','color') if k in v} for v in items_accessory], ensure_ascii=False)}

Reglas:
1. Cada día debe tener un outfit completo (top + bottom + shoes + hasta 2 accesorios)
2. NO repetir la misma prenda en días distintos (cada prenda se usa una sola vez)
3. Priorizar prendas de la temporada adecuada
4. Si no hay suficientes prendas, repetir las menos usadas

Responde ÚNICAMENTE con este JSON:
{{
  "days": [
    {{
      "day": 1,
      "date": "{forecasts[0]['date'] if forecasts else ''}",
      "weather_forecast": "breve descripción del día",
      "top": {"name": "nombre", "id": 0},
      "bottom": {"name": "nombre", "id": 0},
      "shoes": {"name": "nombre", "id": 0},
      "accessories": [{"name": "nombre", "id": 0}]
    }}
  ],
  "trip_summary": "resumen del viaje y estilo general (2 frases, español)",
  "items_not_to_forget": ["accesorio clave", "otro imprescindible"],
  "total_items": número total de prendas usadas
}}

Usa SOLO los IDs y nombres del armario listado arriba. Si falta una categoría, pon null o array vacío.
"""

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "Eres un asistente de moda. Respondes solo con JSON válido."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code != 200:
            return None

        content = (
            resp.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            return None
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(content)
        return {
            "days": data.get("days", []),
            "trip_summary": data.get("trip_summary", ""),
            "items_not_to_forget": data.get("items_not_to_forget", []),
            "total_items": data.get("total_items", 0),
        }
    except Exception as e:
        print(f"LLM packing error: {e}")
        return None


def _generate_fallback(days, forecasts, items_by_cat, total, items_summary):
    days_outfits = []
    item_pool = {cat: list(items) for cat, items in items_by_cat.items()}
    used_ids = set()

    for d in range(days):
        outfit = {"day": d + 1, "date": forecasts[d]["date"], "weather_forecast": forecasts[d]["weather"]}

        for cat, key in [("top", "top"), ("bottom", "bottom"), ("shoes", "shoes")]:
            available = [i for i in item_pool.get(cat, []) if i["id"] not in used_ids]
            if available:
                chosen = available[0]
                used_ids.add(chosen["id"])
                outfit[key] = {"name": chosen["name"], "id": chosen["id"]}
            else:
                outfit[key] = None

        available_acc = [i for i in item_pool.get("accessory", []) if i["id"] not in used_ids]
        outfit["accessories"] = []
        for acc in available_acc[:2]:
            used_ids.add(acc["id"])
            outfit["accessories"].append({"name": acc["name"], "id": acc["id"]})

        days_outfits.append(outfit)

    return {
        "days": days_outfits,
        "trip_summary": f"Viaje de {days} días con {total} prendas disponibles ({items_summary}).",
        "items_not_to_forget": ["Revisar el pronóstico antes de salir"],
        "total_items": len(used_ids),
    }
