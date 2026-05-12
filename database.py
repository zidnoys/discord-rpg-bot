import aiosqlite
import json
from config import DATABASE_PATH


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                char_class TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 100,
                hp INTEGER NOT NULL,
                max_hp INTEGER NOT NULL,
                mp INTEGER NOT NULL,
                max_mp INTEGER NOT NULL,
                attack INTEGER NOT NULL,
                defense INTEGER NOT NULL,
                magic INTEGER NOT NULL,
                speed INTEGER NOT NULL,
                luck INTEGER NOT NULL,
                stat_points INTEGER DEFAULT 0,
                monsters_killed INTEGER DEFAULT 0,
                dungeons_cleared INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES characters(user_id),
                UNIQUE(user_id, item_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                user_id INTEGER PRIMARY KEY,
                weapon TEXT DEFAULT NULL,
                armor TEXT DEFAULT NULL,
                shield TEXT DEFAULT NULL,
                accessory TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES characters(user_id)
            )
        """)
        await db.commit()


async def get_character(user_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM characters WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None


async def create_character(
    user_id: int, name: str, char_class: str, stats: dict
) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO characters
            (user_id, name, char_class, hp, max_hp, mp, max_mp,
             attack, defense, magic, speed, luck)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                name,
                char_class,
                stats["hp"],
                stats["hp"],
                stats["mp"],
                stats["mp"],
                stats["attack"],
                stats["defense"],
                stats["magic"],
                stats["speed"],
                stats["luck"],
            ),
        )
        await db.execute(
            "INSERT INTO equipment (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()


async def update_character(user_id: int, **kwargs) -> None:
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            f"UPDATE characters SET {set_clause} WHERE user_id = ?", values
        )
        await db.commit()


async def delete_character(user_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM inventories WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM equipment WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_inventory(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM inventories WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_item(user_id: int, item_id: str, quantity: int = 1) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO inventories (user_id, item_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?""",
            (user_id, item_id, quantity, quantity),
        )
        await db.commit()


async def remove_item(user_id: int, item_id: str, quantity: int = 1) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT quantity FROM inventories WHERE user_id = ? AND item_id = ?",
            (user_id, item_id),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row["quantity"] < quantity:
                return False
            new_qty = row["quantity"] - quantity
            if new_qty <= 0:
                await db.execute(
                    "DELETE FROM inventories WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                )
            else:
                await db.execute(
                    "UPDATE inventories SET quantity = ? WHERE user_id = ? AND item_id = ?",
                    (new_qty, user_id, item_id),
                )
            await db.commit()
            return True


async def get_equipment(user_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM equipment WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None


async def equip_item(user_id: int, slot: str, item_id: str | None) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            f"UPDATE equipment SET {slot} = ? WHERE user_id = ?",
            (item_id, user_id),
        )
        await db.commit()


async def get_leaderboard(order_by: str = "level", limit: int = 10) -> list[dict]:
    valid_columns = {"level", "gold", "monsters_killed", "dungeons_cleared"}
    if order_by not in valid_columns:
        order_by = "level"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT * FROM characters ORDER BY {order_by} DESC, xp DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
