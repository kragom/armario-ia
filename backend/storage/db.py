"""
数据库连接和 CRUD 操作
"""
import aiosqlite
import json
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime
from domain.clothes import ClothesItem, ClothesCreate
from storage.models import (
    CLOTHES_TABLE_SQL,
    CLOTHES_INDEX_SQL,
    HOROSCOPE_RECORDS_TABLE_SQL,
    HOROSCOPE_RECORDS_INDEX_SQL,
    MIGRATE_ADD_USER_ID_SQL,
)

# 数据库文件路径
# 优先使用环境变量，方便 Docker 挂载 volume
import os
_default_path = Path(__file__).parent.parent / "wardrobe.db"
DB_PATH = Path(os.getenv("DB_FILE_PATH", _default_path))


async def init_db():
    """初始化数据库，创建表和索引"""
    # 确保数据库文件的父目录存在
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CLOTHES_TABLE_SQL)
        await db.execute(CLOTHES_INDEX_SQL)
        await db.execute(HOROSCOPE_RECORDS_TABLE_SQL)
        await db.execute(HOROSCOPE_RECORDS_INDEX_SQL)
        try:
            await db.execute(MIGRATE_ADD_USER_ID_SQL)
        except Exception:
            pass  # Columna ya existe
        await db.commit()


async def add_clothes(clothes: ClothesCreate, user_id: int = 1) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO clothes (
                user_id, category, item, style_semantics, season_semantics,
                usage_semantics, color_semantics, description, notes,
                image_filename, image_filename_thumb
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                clothes.category,
                clothes.item,
                json.dumps(clothes.style_semantics),
                json.dumps(clothes.season_semantics),
                json.dumps(clothes.usage_semantics),
                clothes.color_semantics,
                clothes.description,
                clothes.notes or "",
                clothes.image_filename,
                clothes.image_filename_thumb or ""
            )
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_clothes(user_id: int = 1) -> List[ClothesItem]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM clothes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [_row_to_clothes_item(row) for row in rows]


async def get_clothes_by_category(category: str, user_id: int = 1) -> List[ClothesItem]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM clothes WHERE category = ? AND user_id = ? ORDER BY created_at DESC",
            (category, user_id)
        )
        rows = await cursor.fetchall()
        return [_row_to_clothes_item(row) for row in rows]


async def get_clothes_by_id(clothes_id: int, user_id: int = 1) -> Optional[ClothesItem]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM clothes WHERE id = ? AND user_id = ?",
            (clothes_id, user_id)
        )
        row = await cursor.fetchone()
        if row:
            return _row_to_clothes_item(row)
        return None


async def delete_clothes(clothes_id: int, user_id: int = 1) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM clothes WHERE id = ? AND user_id = ?",
            (clothes_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_clothes(clothes_id: int, clothes: ClothesCreate, user_id: int = 1) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE clothes 
            SET category = ?, item = ?, style_semantics = ?, 
                season_semantics = ?, usage_semantics = ?, 
                color_semantics = ?, description = ?, notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                clothes.category,
                clothes.item,
                json.dumps(clothes.style_semantics),
                json.dumps(clothes.season_semantics),
                json.dumps(clothes.usage_semantics),
                clothes.color_semantics,
                clothes.description,
                clothes.notes or "",
                clothes_id,
                user_id
            )
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_horoscope_record(record_date: str, zodiac_sign: str) -> Optional[dict[str, Any]]:
    """按日期和星座获取缓存的运势记录。"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM horoscope_records
            WHERE record_date = ? AND zodiac_sign = ?
            LIMIT 1
            """,
            (record_date, zodiac_sign),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_horoscope_record(row)


async def upsert_horoscope_source(
    record_date: str,
    zodiac_sign: str,
    zodiac_name: str,
    source_provider: str,
    source_payload: dict[str, Any],
) -> int:
    """
    写入或更新星座原始数据（aztro/fallback）。
    已存在记录时，保留现有推理状态与推理内容。
    """
    payload_json = json.dumps(source_payload, ensure_ascii=False)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id FROM horoscope_records
            WHERE record_date = ? AND zodiac_sign = ?
            LIMIT 1
            """,
            (record_date, zodiac_sign),
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE horoscope_records
                SET zodiac_name = ?,
                    source_provider = ?,
                    source_payload = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (zodiac_name, source_provider, payload_json, existing["id"]),
            )
            await db.commit()
            return int(existing["id"])

        cursor = await db.execute(
            """
            INSERT INTO horoscope_records (
                record_date, zodiac_sign, zodiac_name, source_provider, source_payload, llm_status
            ) VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (record_date, zodiac_sign, zodiac_name, source_provider, payload_json),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def update_horoscope_inference(
    record_id: int,
    llm_status: str,
    llm_reasoning: Optional[str] = None,
    llm_error: Optional[str] = None,
) -> None:
    """更新运势推理状态与结果。"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE horoscope_records
            SET llm_status = ?,
                llm_reasoning = ?,
                llm_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (llm_status, llm_reasoning, llm_error, record_id),
        )
        await db.commit()


def _row_to_clothes_item(row: aiosqlite.Row) -> ClothesItem:
    """将数据库行转换为 ClothesItem"""
    return ClothesItem(
        id=row["id"],
        category=row["category"],
        item=row["item"],
        style_semantics=json.loads(row["style_semantics"] or "[]"),
        season_semantics=json.loads(row["season_semantics"] or "[]"),
        usage_semantics=json.loads(row["usage_semantics"] or "[]"),
        color_semantics=row["color_semantics"] or "",
        description=row["description"] or "",
        notes=row["notes"] or "",
        image_url=f"/uploads/{row['image_filename']}",
        thumbnail_url=f"/uploads/{row['image_filename_thumb']}" if row.get("image_filename_thumb") else "",
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
    )


def _row_to_horoscope_record(row: aiosqlite.Row) -> dict[str, Any]:
    """将数据库行转换为星座记录字典。"""
    return {
        "id": int(row["id"]),
        "record_date": row["record_date"],
        "zodiac_sign": row["zodiac_sign"],
        "zodiac_name": row["zodiac_name"],
        "source_provider": row["source_provider"] or "unknown",
        "source_payload": json.loads(row["source_payload"] or "{}"),
        "llm_status": row["llm_status"] or "pending",
        "llm_reasoning": row["llm_reasoning"] or "",
        "llm_error": row["llm_error"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
