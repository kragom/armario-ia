"""
AI穿搭推荐服务
基于天气、星座运势和衣橱数据生成个性化推荐
"""
import httpx
from typing import Any

from domain.clothes import normalize_category_value
from services.horoscope import get_daily_horoscope
from services.weather import WeatherInfo
from storage.config_store import load_config
from storage.db import get_all_clothes

SEASON_ALIASES = {
    "primavera": {"primavera", "spring", "春", "春季"},
    "verano": {"verano", "summer", "夏", "夏季"},
    "otoño": {"otoño", "autumn", "fall", "秋", "秋季"},
    "invierno": {"invierno", "winter", "冬", "冬季"},
}

ZODIAC_STYLE_HINTS = {
    "aries": {"运动", "街头", "休闲", "sport", "casual"},
    "taurus": {"简约", "质感", "通勤", "minimal", "business"},
    "gemini": {"轻松", "层次", "日常", "casual", "daily"},
    "cancer": {"柔和", "舒适", "居家", "comfort", "daily"},
    "leo": {"亮眼", "时髦", "正式", "formal", "fashion"},
    "virgo": {"利落", "简约", "通勤", "minimal", "business"},
    "libra": {"平衡", "优雅", "约会", "elegant", "formal"},
    "scorpio": {"深色", "干练", "都市", "formal", "vintage"},
    "sagittarius": {"户外", "运动", "旅行", "sport", "casual"},
    "capricorn": {"通勤", "商务", "经典", "business", "formal"},
    "aquarius": {"个性", "创意", "街头", "street", "casual"},
    "pisces": {"柔和", "文艺", "轻盈", "vintage", "casual"},
}

GOAL_ALIASES = {
    "commute": {"commute", "work", "office", "通勤", "上班", "工作", "出勤"},
    "date": {"date", "dating", "约会", "聚会", "见面"},
    "sport": {"sport", "gym", "workout", "run", "运动", "健身", "跑步", "训练"},
    "formal": {"formal", "business", "meeting", "interview", "商务", "正式", "面试", "会议"},
    "daily": {"daily", "casual", "weekend", "日常", "休闲", "周末", "出街"},
    "travel": {"travel", "trip", "旅行", "出游", "旅游"},
}

def normalize_seasons(raw_values: list[str]) -> set[str]:
    normalized: set[str] = set()
    for value in raw_values or []:
        token = (value or "").strip().lower()
        if not token:
            continue
        for canonical, aliases in SEASON_ALIASES.items():
            if token in aliases:
                normalized.add(canonical)
                break
    return normalized


def build_temperature_profile(weather: WeatherInfo) -> dict[str, Any]:
    feels_like = weather.feelsLike

    if feels_like <= 5:
        return {
            "label": "Frío",
            "allowed_seasons": {"invierno"},
            "advice": "Prioriza abrigo. Elige chaquetas gruesas, pantalones largos y calzado térmico.",
            "purchase_hints": {
                "top": ["Chaqueta de plumas", "Jersey de lana", "Camiseta térmica"],
                "bottom": ["Pantalón térmico", "Leggins gruesos"],
                "shoes": ["Botas de nieve", "Zapatos antideslizantes"],
                "accessory": ["Bufanda", "Gorro de lana", "Guantes"],
            },
        }
    if feels_like <= 14:
        return {
            "label": "Fresco",
            "allowed_seasons": {"otoño", "invierno"},
            "advice": "Superposición ligera. Chaqueta y pantalón largo como base.",
            "purchase_hints": {
                "top": ["Chaqueta ligera", "Cárdigan", "Sudadera"],
                "bottom": ["Pantalón recto", "Jeans"],
                "shoes": ["Zapatillas", "Mocasines"],
                "accessory": ["Pañuelo", "Reloj clásico"],
            },
        }
    if feels_like <= 24:
        return {
            "label": "Templado",
            "allowed_seasons": {"primavera", "otoño"},
            "advice": "Temperatura agradable. Opta por capas ligeras y telas transpirables.",
            "purchase_hints": {
                "top": ["Camisa", "Jersey fino", "Cazadora ligera"],
                "bottom": ["Pantalón casual", "Pantalón cropped"],
                "shoes": ["Zapatillas blancas", "Zapatos casual"],
                "accessory": ["Collar sencillo", "Pulsera minimalista"],
            },
        }
    if feels_like <= 30:
        return {
            "label": "Cálido",
            "allowed_seasons": {"primavera", "verano"},
            "advice": "Prioriza tejidos ligeros y transpirables. Evita capas gruesas.",
            "purchase_hints": {
                "top": ["Camiseta manga corta", "Camisa de lino"],
                "bottom": ["Pantalón ligero", "Shorts"],
                "shoes": ["Zapatillas transpirables", "Sandalias"],
                "accessory": ["Gorra", "Gafas de sol"],
            },
        }
    return {
        "label": "Caluroso",
        "allowed_seasons": {"verano"},
        "advice": "Elige tejidos que absorban el sudor y sean transpirables. Mínimas capas.",
        "purchase_hints": {
            "top": ["Camiseta transpirable", "Top"],
            "bottom": ["Pantalón corto", "Shorts ligeros"],
            "shoes": ["Sandalias", "Zapatillas de malla"],
            "accessory": ["Sombrero", "Gafas de sol"],
        },
    }


def is_temperature_compatible(item: dict, allowed_seasons: set[str]) -> bool:
    item_seasons = normalize_seasons(item.get("season_semantics", []))
    if not item_seasons:
        return False
    return bool(item_seasons & allowed_seasons)


def normalize_goal(goal: str | None) -> tuple[str, str]:
    raw_goal = (goal or "").strip()
    if not raw_goal:
        return "", ""

    lowered = raw_goal.lower()
    for canonical, aliases in GOAL_ALIASES.items():
        if lowered in aliases:
            return raw_goal, canonical

    for canonical, aliases in GOAL_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return raw_goal, canonical

    return raw_goal, lowered


def usage_tokens(values: list[str]) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        token = (value or "").strip().lower()
        if not token:
            continue
        normalized.add(token)
        for canonical, aliases in GOAL_ALIASES.items():
            if token in aliases:
                normalized.add(canonical)
                break
    return normalized


def score_item(
    item: dict,
    category: str,
    horoscope: dict,
    weather: WeatherInfo,
    temperature_profile: dict[str, Any],
    normalized_goal: str,
) -> tuple[int, list[str]]:
    score = 5
    if is_temperature_compatible(item, temperature_profile["allowed_seasons"]):
        score += 3
        reasons = [f"季节标签匹配{temperature_profile['label']}温度策略"]
    else:
        reasons = [f"季节标签未完全命中{temperature_profile['label']}策略，作为兜底候选"]

    lucky_color = horoscope.get("lucky_color", "")
    color_tokens = build_color_tokens(lucky_color)
    searchable_text = " ".join([
        str(item.get("item", "")),
        str(item.get("color_semantics", "")),
        str(item.get("description", "")),
    ]).lower()

    if color_tokens and any(token in searchable_text for token in color_tokens):
        score += 4
        reasons.append(f"颜色接近今日幸运色「{lucky_color}」")

    sign_key = horoscope.get("zodiac_sign", "")
    style_hints = ZODIAC_STYLE_HINTS.get(sign_key, set())
    style_values = {
        str(v).strip().lower()
        for v in item.get("style_semantics", [])
        if str(v).strip()
    }
    if style_hints and (style_values & style_hints):
        score += 3
        reasons.append("风格与今日星座运势倾向一致")

    if category == "shoes" and ("雨" in weather.condition or "雪" in weather.condition):
        if any(keyword in searchable_text for keyword in ("防水", "短靴", "boot", "靴")):
            score += 2
            reasons.append("天气有降水，鞋履更注重防滑/防水")

    if normalized_goal:
        item_usage = usage_tokens(item.get("usage_semantics", []))
        if normalized_goal in item_usage:
            score += 4
            reasons.append(f"使用场景匹配本次目标「{normalized_goal}」")

    return score, reasons


def pick_best_item(
    candidates: list[dict],
    category: str,
    horoscope: dict,
    weather: WeatherInfo,
    temperature_profile: dict[str, Any],
    normalized_goal: str,
) -> tuple[dict | None, str]:
    if not candidates:
        return None, ""

    best_item = None
    best_score = -1
    best_reasons: list[str] = []

    for item in candidates:
        score, reasons = score_item(
            item,
            category,
            horoscope,
            weather,
            temperature_profile,
            normalized_goal,
        )
        if score > best_score:
            best_score = score
            best_item = item
            best_reasons = reasons

    return best_item, "；".join(best_reasons)


def build_purchase_suggestion(
    category: str,
    temperature_profile: dict[str, Any],
    horoscope: dict,
) -> dict[str, Any]:
    names = {
        "top": "Top",
        "bottom": "Bottom",
        "shoes": "Shoes",
    }
    hints = temperature_profile["purchase_hints"].get(category, [])
    zodiac_name = horoscope.get("zodiac_name", "Horóscopo de hoy")
    lucky_color = horoscope.get("lucky_color", "neutro")
    return {
        "category": category,
        "title": f"Sugerencia: añadir {names.get(category, category)}",
        "reason": f"No hay {names.get(category, category)} que se ajuste a la temperatura actual. Mejor priorizar prendas básicas de temporada.",
        "keywords": hints,
        "horoscope_hint": f"El color de la suerte de {zodiac_name} es {lucky_color} — prioriza ese tono si puedes.",
    }


def extract_wardrobe_accessories(
    all_clothes: list[dict],
    categories: list[str],
) -> list[dict]:
    accessories = []
    for item, category in zip(all_clothes, categories):
        if category == "accessory":
            accessories.append(item)
            continue
        text = f"{item.get('item', '')} {item.get('description', '')}".lower()
        if any(keyword in text for keyword in ACCESSORY_KEYWORDS):
            accessories.append(item)
    return accessories


def build_purchase_accessories(
    temperature_profile: dict[str, Any],
    horoscope: dict,
) -> list[dict]:
    lucky_color = horoscope.get("lucky_color", "neutro")
    zodiac_name = horoscope.get("zodiac_name", "Astrología")
    base_items = temperature_profile["purchase_hints"].get("accessory", ["Pulsera sencilla", "Reloj clásico"])
    return [
        {
            "name": accessory_name,
            "reason": f"Combinando {zodiac_name} con la sensación térmica, el color {lucky_color} o tonos similares armonizan mejor.",
            "from_wardrobe": False,
            "should_buy": True,
        }
        for accessory_name in base_items[:2]
    ]


def build_recommendation_summary(
    selected: dict[str, dict | None],
    purchase_suggestions: list[dict],
) -> str:
    outfit_parts = []
    for category in ("top", "bottom", "shoes"):
        item = selected.get(category)
        if item:
            outfit_parts.append(f"{category}: {item.get('item', '未命名')}")

    summary = " + ".join(outfit_parts) if outfit_parts else "No hay combinaciones directas disponibles."
    if purchase_suggestions:
        summary += f" Necesitas añadir {len(purchase_suggestions)} categoría(s) esencial/es."
    return summary


async def get_ai_recommendation(
    weather: WeatherInfo,
    zodiac_sign: str | None = None,
    goal: str | None = None,
    user_id: int = 1,
) -> dict:
    all_clothes_items = await get_all_clothes(user_id)
    all_clothes = [
        {
            "id": item.id,
            "category": item.category,
            "item": item.item,
            "style_semantics": item.style_semantics,
            "season_semantics": item.season_semantics,
            "usage_semantics": item.usage_semantics,
            "color_semantics": item.color_semantics,
            "description": item.description,
            "image_url": item.image_url,
        }
        for item in all_clothes_items
    ]

    horoscope = await get_daily_horoscope(
        weather=weather,
        zodiac_sign=zodiac_sign or "",
    )
    goal_raw, goal_normalized = normalize_goal(goal)
    temperature_profile = build_temperature_profile(weather)

    by_category: dict[str, list[dict]] = {"top": [], "bottom": [], "shoes": []}
    all_by_category: dict[str, list[dict]] = {"top": [], "bottom": [], "shoes": []}
    normalized_categories: list[str] = []
    for item in all_clothes:
        category = normalize_category_value(str(item.get("category", "")))
        normalized_categories.append(category)
        if category not in by_category:
            continue
        all_by_category[category].append(item)
        if is_temperature_compatible(item, temperature_profile["allowed_seasons"]):
            by_category[category].append(item)

    selected: dict[str, dict | None] = {}
    selection_reasons: dict[str, str] = {}
    purchase_suggestions: list[dict] = []

    for category in ("top", "bottom", "shoes"):
        chosen, reason = pick_best_item(
            by_category[category],
            category=category,
            horoscope=horoscope,
            weather=weather,
            temperature_profile=temperature_profile,
            normalized_goal=goal_normalized,
        )
        used_fallback = False
        if chosen is None and category == "shoes" and all_by_category["shoes"]:
            fallback_item, fallback_reason = pick_best_item(
                all_by_category["shoes"],
                category=category,
                horoscope=horoscope,
                weather=weather,
                temperature_profile=temperature_profile,
                normalized_goal=goal_normalized,
            )
            if fallback_item is not None:
                chosen = fallback_item
                fallback_prefix = "衣柜暂无完全匹配当前温度策略的鞋履，已从现有鞋履中选择最合适的一双"
                reason = f"{fallback_prefix}；{fallback_reason}" if fallback_reason else fallback_prefix
                used_fallback = True

        selected[category] = chosen
        selection_reasons[category] = reason
        if chosen is None:
            purchase_suggestions.append(
                build_purchase_suggestion(category, temperature_profile, horoscope)
            )
        elif used_fallback:
            purchase_suggestions.append(
                build_purchase_suggestion(category, temperature_profile, horoscope)
            )

    accessory_candidates = extract_wardrobe_accessories(all_clothes, normalized_categories)
    compatible_accessories = []
    for item in accessory_candidates:
        # 饰品优先按季节匹配；无季节标签时保留可选。
        if is_temperature_compatible(item, temperature_profile["allowed_seasons"]) or not item.get("season_semantics"):
            compatible_accessories.append(item)

    suggested_accessories: list[dict[str, Any]] = []
    if compatible_accessories:
        scored = []
        for item in compatible_accessories:
            score, reasons = score_item(
                item,
                category="accessory",
                horoscope=horoscope,
                weather=weather,
                temperature_profile=temperature_profile,
                normalized_goal=goal_normalized,
            )
            scored.append((score, item, "；".join(reasons)))
        scored.sort(key=lambda value: value[0], reverse=True)
        for _, item, reason in scored[:2]:
            suggested_accessories.append(
                {
                    "name": item.get("item", "饰品"),
                    "reason": reason or "与今日运势风格匹配",
                    "from_wardrobe": True,
                    "should_buy": False,
                    "item": item,
                }
            )
    else:
        suggested_accessories = build_purchase_accessories(temperature_profile, horoscope)

    recommendation_text = await get_llm_recommendation(
        weather=weather,
        horoscope=horoscope,
        temperature_profile=temperature_profile,
        selected=selected,
        selection_reasons=selection_reasons,
        purchase_suggestions=purchase_suggestions,
        suggested_accessories=suggested_accessories,
        goal_raw=goal_raw,
        goal_normalized=goal_normalized,
    )

    return {
        "weather": {
            "temperature": weather.temperature,
            "feelsLike": weather.feelsLike,
            "condition": weather.condition,
            "icon": weather.icon,
            "humidity": weather.humidity,
            "windDir": weather.windDir,
            "windScale": weather.windScale,
            "location": weather.location,
            "obsTime": weather.obsTime,
        },
        "horoscope": horoscope,
        "temperature_rule": {
            "label": temperature_profile["label"],
            "allowed_seasons": sorted(list(temperature_profile["allowed_seasons"])),
            "advice": temperature_profile["advice"],
        },
        "recommendation_text": recommendation_text,
        "outfit_summary": build_recommendation_summary(selected, purchase_suggestions),
        "selection_reasons": selection_reasons,
        "suggested_top": selected.get("top"),
        "suggested_bottom": selected.get("bottom"),
        "suggested_shoes": selected.get("shoes"),
        "suggested_accessories": suggested_accessories,
        "purchase_suggestions": purchase_suggestions,
        "goal_raw": goal_raw,
        "goal_normalized": goal_normalized,
    }


async def get_llm_recommendation(
    weather: WeatherInfo,
    horoscope: dict,
    temperature_profile: dict[str, Any],
    selected: dict[str, dict | None],
    selection_reasons: dict[str, str],
    purchase_suggestions: list[dict],
    suggested_accessories: list[dict],
    goal_raw: str,
    goal_normalized: str,
) -> str:
    """
    使用 LLM 生成推荐文案，失败时回退到规则文本。
    """
    from services.key_rotator import get_current_key, rotate_key

    config = load_config()
    key = await get_current_key()
    if not key:
        return generate_basic_recommendation(
            weather=weather,
            horoscope=horoscope,
            temperature_profile=temperature_profile,
            selected=selected,
            selection_reasons=selection_reasons,
            purchase_suggestions=purchase_suggestions,
            suggested_accessories=suggested_accessories,
            goal_raw=goal_raw,
            goal_normalized=goal_normalized,
        )

    def item_name(category: str) -> str:
        item = selected.get(category)
        return item["item"] if item else "缺失"

    purchase_lines = "\n".join(
        [f"- {entry['title']}: {', '.join(entry.get('keywords', []))}" for entry in purchase_suggestions]
    ) or "- No hay sugerencias de compra"

    accessory_lines = "\n".join(
        [
            f"- {entry.get('name', 'Accesorio')} ({'En el armario' if entry.get('from_wardrobe') else 'Sugerido'}): {entry.get('reason', '')}"
            for entry in suggested_accessories
        ]
    ) or "- Sin sugerencias de accesorios"

    prompt = f"""
Eres un asesor de moda práctico y con estilo. Basándote en la siguiente información, genera una recomendación en formato Markdown en español:

Clima:
- Temperatura: {weather.temperature}°C, Sensación térmica: {weather.feelsLike}°C, {weather.condition}
- Humedad: {weather.humidity}% / Viento: {weather.windScale}

Horóscopo:
- Signo: {horoscope.get('zodiac_name', 'No establecido')}
- Palabra clave: {horoscope.get('mood', 'Equilibrio')}
- Color de la suerte: {horoscope.get('lucky_color', 'Neutro')}
- Resumen: {horoscope.get('summary', '')}

Estrategia de temperatura:
- Nivel: {temperature_profile['label']}
- Temporadas válidas: {', '.join(sorted(list(temperature_profile['allowed_seasons'])))}
- Consejo: {temperature_profile['advice']}

Selección del armario (solo prendas que coinciden con la temperatura):
- Superior: {item_name('top')} ({selection_reasons.get('top', 'Sin coincidencia')})
- Inferior: {item_name('bottom')} ({selection_reasons.get('bottom', 'Sin coincidencia')})
- Zapatos: {item_name('shoes')} ({selection_reasons.get('shoes', 'Sin coincidencia')})

Sugerencias de compra:
{purchase_lines}

Accesorios:
{accessory_lines}

Objetivo:
- Original: {goal_raw or 'No especificado'}
- Escenario: {goal_normalized or 'No especificado'}

Instrucciones de salida:
1. Da una conclusión de outfit para hoy (2-3 frases)
2. Indica claramente qué prendas ya tienes y cuáles deberías comprar
3. Añade 1 sugerencia de accesorio relacionada con el horóscopo
4. NO uses bloques de código
"""

    try:
        api_base = config.api_base.rstrip("/")
        if not api_base.endswith("/v1"):
            api_base = f"{api_base}/v1"

        payload = {
            "model": config.model,
            "messages": [
                {
                    "role":             "system",
                    "content": "Eres un asesor de moda profesional. Enfatiza recomendaciones prácticas y adaptación a la temperatura. Responde en español.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.6,
        }

        for attempt in range(2):
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()

            if response.status_code == 429 and attempt == 0:
                key = await rotate_key()
                if key:
                    continue
                break

            break

        print(f"LLM API请求失败: {response.status_code}")
        return generate_basic_recommendation(
            weather=weather,
            horoscope=horoscope,
            temperature_profile=temperature_profile,
            selected=selected,
            selection_reasons=selection_reasons,
            purchase_suggestions=purchase_suggestions,
            suggested_accessories=suggested_accessories,
            goal_raw=goal_raw,
            goal_normalized=goal_normalized,
        )
    except Exception as exc:
        print(f"调用LLM失败: {exc}")
        return generate_basic_recommendation(
            weather=weather,
            horoscope=horoscope,
            temperature_profile=temperature_profile,
            selected=selected,
            selection_reasons=selection_reasons,
            purchase_suggestions=purchase_suggestions,
            suggested_accessories=suggested_accessories,
            goal_raw=goal_raw,
            goal_normalized=goal_normalized,
        )


def generate_basic_recommendation(
    weather: WeatherInfo,
    horoscope: dict,
    temperature_profile: dict[str, Any],
    selected: dict[str, dict | None],
    selection_reasons: dict[str, str],
    purchase_suggestions: list[dict],
    suggested_accessories: list[dict],
    goal_raw: str,
    goal_normalized: str,
) -> str:
    """
    生成规则版推荐文本（不依赖 LLM）。
    """
    lines = [
        f"### Outfit recomendado para hoy",
        f"Sensación térmica: **{weather.feelsLike}°C** → Estrategia **{temperature_profile['label']}**: {temperature_profile['advice']}",
    ]

    if goal_raw or goal_normalized:
        lines.append(f"Objetivo: **{goal_raw or goal_normalized}**")

    lines.extend([
        "",
        "### Prendas seleccionadas del armario",
    ])

    category_names = {"top": "Superior", "bottom": "Inferior", "shoes": "Zapatos"}
    for category in ("top", "bottom", "shoes"):
        item = selected.get(category)
        if item:
            lines.append(
                f"- {category_names[category]}: **{item.get('item', 'Sin nombre')}** ({selection_reasons.get(category, 'Coincide con temperatura')})"
            )
        else:
            lines.append(f"- {category_names[category]}: Sin prenda que coincida con la temperatura")

    if purchase_suggestions:
        lines.extend(["", "### Lista de compras"])
        for entry in purchase_suggestions:
            keywords = " / ".join(entry.get("keywords", [])) or "Básicos"
            lines.append(f"- {entry['title']}: {keywords}. {entry['horoscope_hint']}")

    if suggested_accessories:
        lines.extend(["", "### Accesorios (según horóscopo)"])
        for entry in suggested_accessories[:2]:
            source = "En el armario" if entry.get("from_wardrobe") else "Sugerido"
            lines.append(f"- **{entry.get('name', 'Accesorio')}** ({source}): {entry.get('reason', '')}")

    horoscope_tip = horoscope.get("suggestion", "")
    if horoscope_tip:
        lines.extend(["", f"✨ {horoscope_tip}"])

    return "\n".join(lines)
