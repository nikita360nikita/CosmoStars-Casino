import json
import logging
import os
from datetime import datetime
import aiosqlite
from config import DB_PATH, INITIAL_DEMO_BALANCE

logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                telegram_payment_charge_id TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                bet_amount INTEGER NOT NULL,
                win_amount INTEGER NOT NULL,
                multiplier REAL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                gift_id TEXT NOT NULL,
                gift_name TEXT NOT NULL,
                gift_icon TEXT NOT NULL,
                rarity TEXT NOT NULL,
                stars_value INTEGER NOT NULL,
                serial_number INTEGER NOT NULL,
                total_edition INTEGER NOT NULL,
                is_sold INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                address TEXT NOT NULL,
                method TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Safe migration for terms_accepted column
        try:
            await db.execute("ALTER TABLE users ADD COLUMN terms_accepted INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.commit()
    logger.info("Database initialized successfully at %s", DB_PATH)

async def accept_user_terms(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET terms_accepted = 1 WHERE telegram_id = ?", (telegram_id,))
        await db.commit()

async def get_user_terms_accepted(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT terms_accepted FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return bool(row["terms_accepted"] == 1)
            return False

async def get_or_create_user(telegram_id: int, username: str = "", first_name: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                # Update username/first_name if changed
                await db.execute(
                    "UPDATE users SET username = ?, first_name = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?",
                    (username, first_name, telegram_id)
                )
                await db.commit()
                return dict(row)
            
            # New user with 0 starting stars
            initial_bal = INITIAL_DEMO_BALANCE
            await db.execute(
                "INSERT INTO users (telegram_id, username, first_name, balance, terms_accepted) VALUES (?, ?, ?, ?, 0)",
                (telegram_id, username, first_name, initial_bal)
            )
            if initial_bal > 0:
                await db.execute(
                    "INSERT INTO transactions (telegram_id, amount, type, details) VALUES (?, ?, ?, ?)",
                    (telegram_id, initial_bal, "welcome_bonus", "Начальный демо-баланс для теста")
                )
            await db.commit()
            
            async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur2:
                new_row = await cur2.fetchone()
                return dict(new_row)

async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_user_balance(telegram_id: int) -> int:
    """Gets the current balance of a user."""
    user = await get_user(telegram_id)
    return user["balance"] if user else 0

async def get_user_by_identifier(identifier: str | int) -> dict | None:
    """Finds a user either by numeric Telegram ID or @username."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        s = str(identifier).strip().lstrip("@")
        if s.isdigit():
            async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (int(s),)) as cur:
                row = await cur.fetchone()
                if row:
                    return dict(row)
        async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (s,)) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
    return None

async def change_balance(telegram_id: int, delta: int, tx_type: str, details: str = "", charge_id: str | None = None) -> int:
    """Safely increments or decrements user balance with transaction record."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise ValueError("Пользователь не найден")
            
            current_balance = row["balance"]
            new_balance = current_balance + delta
            if new_balance < 0:
                raise ValueError("Недостаточно звезд на балансе")

            await db.execute(
                "UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?",
                (new_balance, telegram_id)
            )
            await db.execute(
                "INSERT INTO transactions (telegram_id, amount, type, telegram_payment_charge_id, details) VALUES (?, ?, ?, ?, ?)",
                (telegram_id, delta, tx_type, charge_id, details)
            )
            await db.commit()
            return new_balance

async def log_game(telegram_id: int, game: str, bet: int, win: int, multiplier: float, details: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO game_history (telegram_id, game, bet_amount, win_amount, multiplier, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (telegram_id, game, bet, win, multiplier, json.dumps(details, ensure_ascii=False))
        )
        await db.commit()

async def get_user_history(telegram_id: int, limit: int = 15) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM game_history WHERE telegram_id = ? ORDER BY id DESC LIMIT ?",
            (telegram_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_top_winners(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT telegram_id, username, first_name, balance FROM users ORDER BY balance DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# --- USER GIFTS INVENTORY SYSTEM ---

async def add_user_gift(
    telegram_id: int,
    gift_id: str,
    gift_name: str,
    gift_icon: str,
    rarity: str,
    stars_value: int,
    serial_number: int,
    total_edition: int
) -> int:
    """Stores a won Telegram gift into the user's permanent collection."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO user_gifts 
               (telegram_id, gift_id, gift_name, gift_icon, rarity, stars_value, serial_number, total_edition, is_sold)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (telegram_id, gift_id, gift_name, gift_icon, rarity, stars_value, serial_number, total_edition)
        )
        await db.commit()
        return cursor.lastrowid

async def get_user_gifts(telegram_id: int, include_sold: bool = False) -> list[dict]:
    """Retrieves all gifts belonging to a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = "SELECT * FROM user_gifts WHERE telegram_id = ?"
        params = [telegram_id]
        if not include_sold:
            sql += " AND is_sold = 0"
        sql += " ORDER BY id DESC"
        async with db.execute(sql, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def sell_user_gift(gift_db_id: int, telegram_id: int) -> tuple[bool, int, str]:
    """Sells a user's gift back to the system for Stars."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_gifts WHERE id = ? AND telegram_id = ?", (gift_db_id, telegram_id)) as cursor:
            gift = await cursor.fetchone()
            if not gift:
                return False, 0, "Подарок не найден в вашем инвентаре"
            if gift["is_sold"] == 1:
                return False, 0, "Этот подарок уже продан"

            stars_value = gift["stars_value"]
            gift_name = gift["gift_name"]

            # Mark as sold
            await db.execute("UPDATE user_gifts SET is_sold = 1 WHERE id = ?", (gift_db_id,))
            await db.commit()

    # Credit balance
    new_balance = await change_balance(
        telegram_id=telegram_id,
        delta=stars_value,
        tx_type="sell_gift",
        details=f"Продажа подарка '{gift_name}': +{stars_value} XTR"
    )
    return True, new_balance, f"Подарок '{gift_name}' продан за {stars_value} ⭐️!"

async def consume_user_gift(gift_db_id: int, telegram_id: int) -> dict | None:
    """Marks a user's gift as consumed/used for an upgrade attempt."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_gifts WHERE id = ? AND telegram_id = ? AND is_sold = 0", (gift_db_id, telegram_id)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            gift_dict = dict(row)
            await db.execute("UPDATE user_gifts SET is_sold = 1 WHERE id = ?", (gift_db_id,))
            await db.commit()
            return gift_dict

async def sell_all_user_gifts(telegram_id: int) -> tuple[bool, int, int, str]:
    """Sells all unsold gifts in the user's inventory."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, stars_value FROM user_gifts WHERE telegram_id = ? AND is_sold = 0", (telegram_id,)) as cur:
            rows = await cur.fetchall()
            if not rows:
                return False, 0, 0, "У вас нет подарков для продажи"
            total_stars = sum(r["stars_value"] for r in rows)
            count = len(rows)
            await db.execute("UPDATE user_gifts SET is_sold = 1 WHERE telegram_id = ? AND is_sold = 0", (telegram_id,))
            await db.commit()

    new_balance = await change_balance(
        telegram_id=telegram_id,
        delta=total_stars,
        tx_type="sell_all_gifts",
        details=f"Массовая продажа {count} подарков: +{total_stars} XTR"
    )
    return True, new_balance, total_stars, f"Продано {count} подарков на сумму {total_stars} ⭐️!"

async def create_withdrawal(telegram_id: int, amount: int, address: str, method: str = "Telegram Stars") -> tuple[bool, int, str, int | None]:
    """Creates a withdrawal request, deducting stars from user balance."""
    if amount < 100:
        return False, 0, "Минимальная сумма вывода — 100 ⭐️", None
    
    current_balance = await get_user_balance(telegram_id)
    if current_balance < amount:
        return False, current_balance, "Недостаточно звёзд на балансе", None
    
    new_balance = await change_balance(
        telegram_id=telegram_id,
        delta=-amount,
        tx_type="withdrawal",
        details=f"Заявка на вывод: -{amount} XTR ({method} на {address})"
    )
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO withdrawals (telegram_id, amount, address, method, status) VALUES (?, ?, ?, ?, 'pending')",
            (telegram_id, amount, address, method)
        )
        await db.commit()
        wid = cursor.lastrowid
        
    return True, new_balance, f"Заявка на вывод {amount} ⭐️ успешно создана!", wid

async def get_user_withdrawals(telegram_id: int) -> list[dict]:
    """Retrieves user's withdrawal requests."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM withdrawals WHERE telegram_id = ? ORDER BY id DESC LIMIT 20",
            (telegram_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_setting(key: str, default: str = None) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            return default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, str(value)))
        await db.commit()

async def is_admin(telegram_id: int = None, username: str = None) -> bool:
    """Checks whether a given telegram_id or username belongs to an administrator."""
    from config import ADMIN_USERNAMES, ADMIN_CHAT_IDS
    if telegram_id and telegram_id in ADMIN_CHAT_IDS:
        return True
    if username and username.lower().lstrip("@") in ADMIN_USERNAMES:
        return True
    if telegram_id:
        user = await get_user(telegram_id)
        if user and user.get("username") and user["username"].lower() in ADMIN_USERNAMES:
            return True
    return False

async def get_all_admin_chat_ids() -> list[int]:
    """Returns all known Telegram chat IDs of configured administrators."""
    from config import ADMIN_USERNAMES, ADMIN_CHAT_IDS
    ids = set(ADMIN_CHAT_IDS)
    saved = await get_setting("admin_chat_ids")
    if saved:
        for s in saved.split(","):
            if s.strip().isdigit():
                ids.add(int(s.strip()))

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for uname in ADMIN_USERNAMES:
            async with db.execute("SELECT telegram_id FROM users WHERE LOWER(username) = ? LIMIT 1", (uname.lower(),)) as cursor:
                row = await cursor.fetchone()
                if row:
                    ids.add(row["telegram_id"])
    return list(ids)

async def get_admin_chat_id() -> int | None:
    all_ids = await get_all_admin_chat_ids()
    return all_ids[0] if all_ids else None

async def save_admin_chat_id(telegram_id: int):
    all_ids = set(await get_all_admin_chat_ids())
    all_ids.add(telegram_id)
    await set_setting("admin_chat_ids", ",".join(str(i) for i in all_ids))

async def get_casino_stats() -> dict:
    """Returns aggregated high-level casino metrics for administrators."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) as count, COALESCE(SUM(balance), 0) as total_bal FROM users") as cur:
            u_row = await cur.fetchone()
        async with db.execute("SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_sum FROM withdrawals WHERE status = 'pending'") as cur:
            w_pending = await cur.fetchone()
        async with db.execute("SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_sum FROM withdrawals WHERE status = 'completed'") as cur:
            w_completed = await cur.fetchone()
        async with db.execute("SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_sum FROM transactions WHERE type = 'deposit_stars'") as cur:
            dep_row = await cur.fetchone()

        return {
            "total_users": u_row["count"] if u_row else 0,
            "users_balance": u_row["total_bal"] if u_row else 0,
            "pending_withdrawals_count": w_pending["count"] if w_pending else 0,
            "pending_withdrawals_sum": w_pending["total_sum"] if w_pending else 0,
            "completed_withdrawals_count": w_completed["count"] if w_completed else 0,
            "completed_withdrawals_sum": w_completed["total_sum"] if w_completed else 0,
            "total_deposits_count": dep_row["count"] if dep_row else 0,
            "total_deposits_sum": dep_row["total_sum"] if dep_row else 0
        }

async def get_withdrawal_by_id(withdrawal_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_withdrawal_status(withdrawal_id: int, status: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE withdrawals SET status = ? WHERE id = ?", (status, withdrawal_id))
        await db.commit()
        return True

async def get_pending_withdrawals(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT w.*, u.username, u.first_name, u.balance
               FROM withdrawals w
               LEFT JOIN users u ON w.telegram_id = u.telegram_id
               WHERE w.status = 'pending'
               ORDER BY w.id ASC LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_recent_drops(limit: int = 12) -> list[dict]:
    """Returns recent big wins and drops for the live ticker feed."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT g.id, g.telegram_id, g.gift_name, g.gift_icon, g.rarity, g.stars_value, g.serial_number,
                      u.first_name, u.username, g.created_at
               FROM user_gifts g
               LEFT JOIN users u ON g.telegram_id = u.telegram_id
               ORDER BY g.id DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
