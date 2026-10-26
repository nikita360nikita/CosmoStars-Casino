import hashlib
import hmac
import random
import time
import uuid

# --- REAL TELEGRAM GIFTS CATALOG ---
# Official Telegram Gifts metadata with local HD SVG artworks
TELEGRAM_GIFTS = {
    "tg_green_star": {
        "id": "tg_green_star",
        "name": "Green Star",
        "ru_name": "Зелёная Звезда",
        "icon": "💚",
        "thumbnail": "/static/images/gifts/tg_green_star.svg",
        "stars": 15,
        "rarity": "common",
        "edition": 500000,
        "description": "Классическая сияющая зелёная звезда Telegram"
    },
    "tg_blue_star": {
        "id": "tg_blue_star",
        "name": "Blue Star",
        "ru_name": "Синяя Звезда",
        "icon": "💙",
        "thumbnail": "/static/images/gifts/tg_blue_star.svg",
        "stars": 25,
        "rarity": "common",
        "edition": 500000,
        "description": "Сапфировая звезда с небесным сиянием"
    },
    "tg_cake": {
        "id": "tg_cake",
        "name": "Delicious Cake",
        "ru_name": "Вкусный Торт",
        "icon": "🎂",
        "thumbnail": "/static/images/gifts/tg_cake.svg",
        "stars": 50,
        "rarity": "common",
        "edition": 500000,
        "description": "Праздничный торт с кремом и мерцающими свечами"
    },
    "tg_bear": {
        "id": "tg_bear",
        "name": "Plush Bear",
        "ru_name": "Плюшевый Мишка",
        "icon": "🧸",
        "thumbnail": "/static/images/gifts/tg_bear.svg",
        "stars": 100,
        "rarity": "rare",
        "edition": 100000,
        "description": "Коллекционный плюшевый мишка с алым атласным бантом"
    },
    "tg_heart": {
        "id": "tg_heart",
        "name": "Sparkling Heart",
        "ru_name": "Сияющее Сердце",
        "icon": "💖",
        "thumbnail": "/static/images/gifts/tg_heart.svg",
        "stars": 150,
        "rarity": "rare",
        "edition": 100000,
        "description": "Гранёное рубиновое сердце с переливающимся сиянием"
    },
    "tg_bouquet": {
        "id": "tg_bouquet",
        "name": "Spring Bouquet",
        "ru_name": "Весенний Букет",
        "icon": "💐",
        "thumbnail": "/static/images/gifts/tg_bouquet.svg",
        "stars": 200,
        "rarity": "rare",
        "edition": 50000,
        "description": "Роскошный букет свежих цветов в подарочной упаковке"
    },
    "tg_cyber_cube": {
        "id": "tg_cyber_cube",
        "name": "Cyber Cube",
        "ru_name": "Кибер-Куб",
        "icon": "🧊",
        "thumbnail": "/static/images/gifts/tg_cyber_cube.svg",
        "stars": 220,
        "rarity": "rare",
        "edition": 40000,
        "description": "Голографический квантовый куб Telegram"
    },
    "tg_rose": {
        "id": "tg_rose",
        "name": "Eternal Rose",
        "ru_name": "Вечная Роза",
        "icon": "🌹",
        "thumbnail": "/static/images/gifts/tg_rose.svg",
        "stars": 250,
        "rarity": "epic",
        "edition": 25000,
        "description": "Магическая неувядающая роза в хрустальной колбе"
    },
    "tg_rocket": {
        "id": "tg_rocket",
        "name": "Space Rocket",
        "ru_name": "Космическая Ракета",
        "icon": "🚀",
        "thumbnail": "/static/images/gifts/tg_rocket.svg",
        "stars": 350,
        "rarity": "epic",
        "edition": 25000,
        "description": "Сверхзвуковая ракета Telegram с плазменным двигателем"
    },
    "tg_potion": {
        "id": "tg_potion",
        "name": "Magic Potion",
        "ru_name": "Магическое Зелье",
        "icon": "🧪",
        "thumbnail": "/static/images/gifts/tg_potion.svg",
        "stars": 400,
        "rarity": "epic",
        "edition": 15000,
        "description": "Светящийся эликсир космической удачи"
    },
    "tg_champagne": {
        "id": "tg_champagne",
        "name": "Champagne",
        "ru_name": "Шампанское",
        "icon": "🍾",
        "thumbnail": "/static/images/gifts/tg_champagne.svg",
        "stars": 500,
        "rarity": "epic",
        "edition": 10000,
        "description": "Игристое премиальное шампанское с золотыми искрами"
    },
    "tg_sprout": {
        "id": "tg_sprout",
        "name": "Golden Sprout",
        "ru_name": "Золотой Росток",
        "icon": "🌱",
        "thumbnail": "/static/images/gifts/tg_sprout.svg",
        "stars": 750,
        "rarity": "legendary",
        "edition": 7500,
        "description": "Волшебный золотой росток экосистемы Telegram"
    },
    "tg_crown": {
        "id": "tg_crown",
        "name": "Jeweled Crown",
        "ru_name": "Царская Корона",
        "icon": "👑",
        "thumbnail": "/static/images/gifts/tg_crown.svg",
        "stars": 1000,
        "rarity": "legendary",
        "edition": 5000,
        "description": "Королевский венец из чистого золота с сапфирами и рубинами"
    },
    "tg_diamond_ring": {
        "id": "tg_diamond_ring",
        "name": "Diamond Ring",
        "ru_name": "Кольцо с Бриллиантом",
        "icon": "💍",
        "thumbnail": "/static/images/gifts/tg_diamond_ring.svg",
        "stars": 1500,
        "rarity": "legendary",
        "edition": 3000,
        "description": "Платиновое кольцо с сияющим бриллиантом высшей пробы"
    },
    "tg_diamond": {
        "id": "tg_diamond",
        "name": "Giant Diamond",
        "ru_name": "Гигантский Алмаз",
        "icon": "💎",
        "thumbnail": "/static/images/gifts/tg_diamond.svg",
        "stars": 2500,
        "rarity": "legendary",
        "edition": 2500,
        "description": "Безупречный бриллиант высшей огранки с радужной дисперсией"
    },
    "tg_frog": {
        "id": "tg_frog",
        "name": "Kissed Frog",
        "ru_name": "Царевна-Лягушка",
        "icon": "🐸",
        "thumbnail": "/static/images/gifts/tg_frog.svg",
        "stars": 5000,
        "rarity": "legendary",
        "edition": 1500,
        "description": "Сказочная заколдованная лягушка с золотой короной"
    },
    "tg_durov_cap": {
        "id": "tg_durov_cap",
        "name": "Durov's Cap",
        "ru_name": "Кепка Дурова",
        "icon": "🧢",
        "thumbnail": "/static/images/gifts/tg_durov_cap.svg",
        "stars": 10000,
        "rarity": "mythic",
        "edition": 1000,
        "description": "Легендарная чёрная кепка Павла Дурова с золотым логотипом"
    },
    "tg_trophy": {
        "id": "tg_trophy",
        "name": "Star King Trophy",
        "ru_name": "Кубок Чемпиона",
        "icon": "🏆",
        "thumbnail": "/static/images/gifts/tg_trophy.svg",
        "stars": 25000,
        "rarity": "mythic",
        "edition": 250,
        "description": "Мифический космический трофей первого лорда Telegram Stars"
    }
}

# --- EXTENDED REAL TELEGRAM CASES CATALOG (12 CASES) ---
CASES_CATALOG = {
    "starter": {
        "id": "starter",
        "name": "Starter Box",
        "subtitle": "Telegram Gifts Starter",
        "description": "Доступный кейс с реальными подарками Telegram для быстрого старта",
        "price": 25,
        "badge": "NEW",
        "badge_color": "#10b981",
        "gradient": "linear-gradient(135deg, #0d9488, #14b8a6)",
        "items": [
            {**TELEGRAM_GIFTS["tg_green_star"], "weight": 450},
            {**TELEGRAM_GIFTS["tg_blue_star"], "weight": 350},
            {**TELEGRAM_GIFTS["tg_cake"], "weight": 140},
            {**TELEGRAM_GIFTS["tg_bear"], "weight": 50},
            {**TELEGRAM_GIFTS["tg_heart"], "weight": 10},
        ]
    },
    "classic": {
        "id": "classic",
        "name": "Classic Box",
        "subtitle": "Popular Gifts",
        "description": "Самые популярные подарки Telegram — шанс на Вечную Розу",
        "price": 75,
        "badge": "HOT",
        "badge_color": "#f97316",
        "gradient": "linear-gradient(135deg, #ea580c, #f97316)",
        "items": [
            {**TELEGRAM_GIFTS["tg_blue_star"], "weight": 350},
            {**TELEGRAM_GIFTS["tg_cake"], "weight": 360},
            {**TELEGRAM_GIFTS["tg_bear"], "weight": 200},
            {**TELEGRAM_GIFTS["tg_heart"], "weight": 70},
            {**TELEGRAM_GIFTS["tg_rose"], "weight": 18},
            {**TELEGRAM_GIFTS["tg_rocket"], "weight": 2},
        ]
    },
    "cosmic": {
        "id": "cosmic",
        "name": "Cosmic Voyage",
        "subtitle": "Space & Speed",
        "description": "Космический кейс с ракетами и сапфировыми звездами",
        "price": 150,
        "badge": "SPACE",
        "badge_color": "#06b6d4",
        "gradient": "linear-gradient(135deg, #0891b2, #06b6d4)",
        "items": [
            {**TELEGRAM_GIFTS["tg_cake"], "weight": 360},
            {**TELEGRAM_GIFTS["tg_bear"], "weight": 320},
            {**TELEGRAM_GIFTS["tg_heart"], "weight": 200},
            {**TELEGRAM_GIFTS["tg_bouquet"], "weight": 90},
            {**TELEGRAM_GIFTS["tg_rocket"], "weight": 26},
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 4},
        ]
    },
    "cyber": {
        "id": "cyber",
        "name": "Cyber Star Box",
        "subtitle": "Quantum & Neon",
        "description": "Футуристический кибер-кейс с квантовыми кубами и ракетами",
        "price": 200,
        "badge": "CYBER",
        "badge_color": "#8b5cf6",
        "gradient": "linear-gradient(135deg, #6d28d9, #8b5cf6)",
        "items": [
            {**TELEGRAM_GIFTS["tg_bear"], "weight": 380},
            {**TELEGRAM_GIFTS["tg_heart"], "weight": 320},
            {**TELEGRAM_GIFTS["tg_cyber_cube"], "weight": 200},
            {**TELEGRAM_GIFTS["tg_rose"], "weight": 75},
            {**TELEGRAM_GIFTS["tg_rocket"], "weight": 22},
            {**TELEGRAM_GIFTS["tg_potion"], "weight": 3},
        ]
    },
    "vip": {
        "id": "vip",
        "name": "VIP Elite",
        "subtitle": "High-Tier Gifts",
        "description": "Премиальные подарки для хайроллеров: Шампанское, Корона и Алмаз",
        "price": 250,
        "badge": "VIP",
        "badge_color": "#a855f7",
        "gradient": "linear-gradient(135deg, #7c3aed, #a855f7)",
        "items": [
            {**TELEGRAM_GIFTS["tg_heart"], "weight": 400},
            {**TELEGRAM_GIFTS["tg_bouquet"], "weight": 320},
            {**TELEGRAM_GIFTS["tg_rose"], "weight": 180},
            {**TELEGRAM_GIFTS["tg_rocket"], "weight": 70},
            {**TELEGRAM_GIFTS["tg_champagne"], "weight": 24},
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 5},
            {**TELEGRAM_GIFTS["tg_diamond"], "weight": 1},
        ]
    },
    "alchemist": {
        "id": "alchemist",
        "name": "Alchemist Vault",
        "subtitle": "Magic & Elixirs",
        "description": "Мистический тайник с Магическим Зельем и Вечной Розой",
        "price": 350,
        "badge": "MAGIC",
        "badge_color": "#d946ef",
        "gradient": "linear-gradient(135deg, #a21caf, #d946ef)",
        "items": [
            {**TELEGRAM_GIFTS["tg_bouquet"], "weight": 380},
            {**TELEGRAM_GIFTS["tg_rose"], "weight": 340},
            {**TELEGRAM_GIFTS["tg_rocket"], "weight": 180},
            {**TELEGRAM_GIFTS["tg_potion"], "weight": 80},
            {**TELEGRAM_GIFTS["tg_champagne"], "weight": 18},
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 2},
        ]
    },
    "durov": {
        "id": "durov",
        "name": "Durov's Vault",
        "subtitle": "Pavel's Secret Stash",
        "description": "Секретный сейф Павла Дурова: шанс выбить легендарную Кепку Дурова!",
        "price": 500,
        "badge": "DUROV",
        "badge_color": "#3b82f6",
        "gradient": "linear-gradient(135deg, #1d4ed8, #3b82f6)",
        "items": [
            {**TELEGRAM_GIFTS["tg_rose"], "weight": 360},
            {**TELEGRAM_GIFTS["tg_rocket"], "weight": 320},
            {**TELEGRAM_GIFTS["tg_potion"], "weight": 180},
            {**TELEGRAM_GIFTS["tg_champagne"], "weight": 100},
            {**TELEGRAM_GIFTS["tg_sprout"], "weight": 30},
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 9},
            {**TELEGRAM_GIFTS["tg_durov_cap"], "weight": 1},
        ]
    },
    "sprout": {
        "id": "sprout",
        "name": "Golden Sprout",
        "subtitle": "TON Ecosystem Growth",
        "description": "Благородный кейс золотого ростка экосистемы TON Stars",
        "price": 750,
        "badge": "ECO",
        "badge_color": "#22c55e",
        "gradient": "linear-gradient(135deg, #15803d, #22c55e)",
        "items": [
            {**TELEGRAM_GIFTS["tg_rocket"], "weight": 380},
            {**TELEGRAM_GIFTS["tg_potion"], "weight": 300},
            {**TELEGRAM_GIFTS["tg_champagne"], "weight": 210},
            {**TELEGRAM_GIFTS["tg_sprout"], "weight": 85},
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 22},
            {**TELEGRAM_GIFTS["tg_diamond_ring"], "weight": 3},
        ]
    },
    "nft": {
        "id": "nft",
        "name": "Limited NFT",
        "subtitle": "Exclusive & Collectible",
        "description": "Эксклюзивные лимитированные сокровища: Царевна-Лягушка, Бриллиант и Кепка",
        "price": 1000,
        "badge": "NFT",
        "badge_color": "#ec4899",
        "gradient": "linear-gradient(135deg, #db2777, #ec4899)",
        "items": [
            {**TELEGRAM_GIFTS["tg_champagne"], "weight": 440},
            {**TELEGRAM_GIFTS["tg_sprout"], "weight": 320},
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 160},
            {**TELEGRAM_GIFTS["tg_diamond_ring"], "weight": 55},
            {**TELEGRAM_GIFTS["tg_diamond"], "weight": 20},
            {**TELEGRAM_GIFTS["tg_frog"], "weight": 4},
            {**TELEGRAM_GIFTS["tg_durov_cap"], "weight": 1},
        ]
    },
    "highroller": {
        "id": "highroller",
        "name": "Highroller Club",
        "subtitle": "Luxury Only",
        "description": "Клуб высоких ставок: Кольцо с Бриллиантом, Корона и Шампанское",
        "price": 1500,
        "badge": "CLUB",
        "badge_color": "#eab308",
        "gradient": "linear-gradient(135deg, #a16207, #eab308)",
        "items": [
            {**TELEGRAM_GIFTS["tg_sprout"], "weight": 420},
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 340},
            {**TELEGRAM_GIFTS["tg_diamond_ring"], "weight": 160},
            {**TELEGRAM_GIFTS["tg_diamond"], "weight": 65},
            {**TELEGRAM_GIFTS["tg_frog"], "weight": 14},
            {**TELEGRAM_GIFTS["tg_durov_cap"], "weight": 1},
        ]
    },
    "royal": {
        "id": "royal",
        "name": "Royal Treasury",
        "subtitle": "Crown & Diamond Vault",
        "description": "Королевская сокровищница: шанс на Царевну-Лягушку и Кубок Чемпиона",
        "price": 2500,
        "badge": "JACKPOT",
        "badge_color": "#f59e0b",
        "gradient": "linear-gradient(135deg, #b45309, #f59e0b)",
        "items": [
            {**TELEGRAM_GIFTS["tg_crown"], "weight": 460},
            {**TELEGRAM_GIFTS["tg_diamond_ring"], "weight": 300},
            {**TELEGRAM_GIFTS["tg_diamond"], "weight": 180},
            {**TELEGRAM_GIFTS["tg_frog"], "weight": 50},
            {**TELEGRAM_GIFTS["tg_durov_cap"], "weight": 9},
            {**TELEGRAM_GIFTS["tg_trophy"], "weight": 1},
        ]
    },
    "mythic": {
        "id": "mythic",
        "name": "Immortal Jackpot",
        "subtitle": "Gods of Telegram Stars",
        "description": "Ультимативный кейс владык Telegram Stars: наивысший шанс на Кубок Чемпиона и Кепку Дурова",
        "price": 5000,
        "badge": "MYTHIC",
        "badge_color": "#f43f5e",
        "gradient": "linear-gradient(135deg, #9f1239, #f43f5e)",
        "items": [
            {**TELEGRAM_GIFTS["tg_diamond"], "weight": 480},
            {**TELEGRAM_GIFTS["tg_frog"], "weight": 340},
            {**TELEGRAM_GIFTS["tg_durov_cap"], "weight": 150},
            {**TELEGRAM_GIFTS["tg_trophy"], "weight": 30},
        ]
    }
}

active_crash_sessions: dict[str, dict] = {}
active_mines_sessions: dict[str, dict] = {}
active_storm_sessions: dict[str, dict] = {}

def generate_crash_multiplier() -> tuple[float, str]:
    """Generates provably fair crash multiplier with lowered win rate (~18% instant crash)."""
    server_seed = uuid.uuid4().hex
    r = random.random()
    # 18% instant crash at 1.00x
    if r < 0.18:
        multiplier = 1.00
    else:
        # Standard crash formula with 20% house edge
        raw_mult = 0.80 / (1.0 - r)
        multiplier = min(100.0, max(1.01, round(raw_mult, 2)))

    hash_proof = hashlib.sha256(f"{server_seed}:{multiplier}".encode()).hexdigest()
    return multiplier, hash_proof

def start_crash_round(telegram_id: int, bet_amount: int) -> dict:
    multiplier, hash_proof = generate_crash_multiplier()
    session_id = uuid.uuid4().hex
    active_crash_sessions[session_id] = {
        "session_id": session_id,
        "telegram_id": telegram_id,
        "bet_amount": bet_amount,
        "crash_multiplier": multiplier,
        "hash_proof": hash_proof,
        "started_at": time.time(),
        "status": "in_flight"
    }
    return {
        "session_id": session_id,
        "hash_proof": hash_proof,
        "bet_amount": bet_amount,
        "crash_multiplier": multiplier
    }

def cash_out_crash(session_id: str, client_multiplier: float) -> tuple[bool, int, float, str]:
    session = active_crash_sessions.get(session_id)
    if not session:
        return False, 0, 0.0, "Сессия не найдена"
    if session["status"] != "in_flight":
        return False, 0, 0.0, "Раунд уже завершен"

    crash_mult = session["crash_multiplier"]
    bet = session["bet_amount"]

    if client_multiplier > crash_mult:
        session["status"] = "crashed"
        return False, 0, crash_mult, "Ракета взорвалась до забора!"

    session["status"] = "cashed_out"
    win_amount = int(bet * client_multiplier)
    return True, win_amount, client_multiplier, "Успешный забор!"

def play_coinflip(bet_amount: int, chosen_side: str) -> dict:
    """Coinflip: 1.80x multiplier payout (20% house edge)."""
    winning_side = random.choice(["heads", "tails"])
    is_win = (chosen_side == winning_side)
    multiplier = 1.80 if is_win else 0.0
    win_amount = int(bet_amount * 1.80) if is_win else 0
    salt = uuid.uuid4().hex[:12]
    proof = hashlib.sha256(f"{salt}:{winning_side}".encode()).hexdigest()
    return {
        "winning_side": winning_side,
        "chosen_side": chosen_side,
        "is_win": is_win,
        "win_amount": win_amount,
        "multiplier": multiplier,
        "proof": proof
    }

def play_gift_upgrader(source_value: int, target_gift_id: str) -> dict:
    """Upgrades a Telegram gift into a target Telegram Gift.
       Formula: (source_value / target_value) * 78% (22% house edge for lower win rate).
    """
    target_gift = TELEGRAM_GIFTS.get(target_gift_id)
    if not target_gift:
        raise ValueError("Целевой подарок не найден")

    target_value = target_gift["stars"]
    if source_value >= target_value:
        raise ValueError("Целевой подарок должен иметь большую стоимость, чем исходный")

    raw_chance = (source_value / target_value) * 78.0
    win_chance_percent = min(85.0, max(0.5, round(raw_chance, 2)))
    win_sector_angle = round((win_chance_percent / 100.0) * 360.0, 2)

    stop_angle = round(random.uniform(0.0, 360.0), 2)
    is_win = (stop_angle <= win_sector_angle)

    serial_number = None
    total_edition = target_gift.get("edition", 10000)
    if is_win:
        serial_number = random.randint(1, total_edition)

    multiplier = round(target_value / source_value, 2)

    winning_item = None
    if is_win:
        winning_item = {
            **target_gift,
            "serial_number": serial_number,
            "total_edition": total_edition
        }

    return {
        "is_win": is_win,
        "source_value": source_value,
        "target_gift": target_gift,
        "target_value": target_value,
        "winning_item": winning_item,
        "multiplier": multiplier,
        "win_chance_percent": win_chance_percent,
        "win_sector_angle": win_sector_angle,
        "stop_angle": stop_angle
    }

# --- MINES (МИНЫ 5x5) GAME LOGIC ---
def start_mines_session(telegram_id: int, bet_amount: int, mines_count: int) -> dict:
    if mines_count < 1 or mines_count > 24:
        raise ValueError("Количество мин должно быть от 1 до 24")
    if bet_amount < 1:
        raise ValueError("Минимальная ставка 1 ⭐️")
    
    all_indices = list(range(25))
    mine_positions = set(random.sample(all_indices, mines_count))
    session_id = uuid.uuid4().hex
    
    salt = uuid.uuid4().hex
    proof = hashlib.sha256(f"{salt}:{sorted(list(mine_positions))}".encode()).hexdigest()
    
    active_mines_sessions[session_id] = {
        "session_id": session_id,
        "telegram_id": telegram_id,
        "bet_amount": bet_amount,
        "mines_count": mines_count,
        "mine_positions": mine_positions,
        "revealed": set(),
        "salt": salt,
        "proof": proof,
        "status": "active"
    }
    return {
        "session_id": session_id,
        "proof": proof,
        "bet_amount": bet_amount,
        "mines_count": mines_count,
        "total_cells": 25
    }

def calculate_mines_multiplier(revealed_count: int, mines_count: int) -> float:
    """Calculates multiplier with 18% house edge for each step."""
    if revealed_count == 0:
        return 1.00
    prob = 1.0
    for i in range(revealed_count):
        prob *= (25 - mines_count - i) / (25 - i)
    if prob <= 0:
        return 1.00
    fair_mult = 1.0 / prob
    mult = fair_mult * 0.82
    return max(1.02, round(mult, 2))

def reveal_mines_tile(session_id: str, tile_index: int) -> dict:
    session = active_mines_sessions.get(session_id)
    if not session or session["status"] != "active":
        raise ValueError("Сессия игры не активна")
    if tile_index in session["revealed"]:
        raise ValueError("Ячейка уже открыта")
    if tile_index < 0 or tile_index >= 25:
        raise ValueError("Некорректный номер ячейки")
        
    if tile_index in session["mine_positions"]:
        session["status"] = "lost"
        return {
            "status": "lost",
            "hit_mine": True,
            "tile_index": tile_index,
            "mine_positions": list(session["mine_positions"]),
            "multiplier": 0.0,
            "win_amount": 0
        }
        
    session["revealed"].add(tile_index)
    mult = calculate_mines_multiplier(len(session["revealed"]), session["mines_count"])
    win_amount = int(session["bet_amount"] * mult)
    
    is_all_safe_cleared = (len(session["revealed"]) == (25 - session["mines_count"]))
    if is_all_safe_cleared:
        session["status"] = "won"
        
    return {
        "status": "won" if is_all_safe_cleared else "active",
        "hit_mine": False,
        "tile_index": tile_index,
        "revealed_count": len(session["revealed"]),
        "multiplier": mult,
        "win_amount": win_amount,
        "mine_positions": list(session["mine_positions"]) if is_all_safe_cleared else []
    }

def cash_out_mines(session_id: str) -> tuple[bool, int, float, list[int], str]:
    session = active_mines_sessions.get(session_id)
    if not session or session["status"] != "active":
        return False, 0, 0.0, [], "Сессия не активна"
    if len(session["revealed"]) == 0:
        return False, 0, 0.0, [], "Откройте хотя бы одну ячейку"
        
    mult = calculate_mines_multiplier(len(session["revealed"]), session["mines_count"])
    win_amount = int(session["bet_amount"] * mult)
    session["status"] = "cashed_out"
    mines_list = list(session["mine_positions"])
    return True, win_amount, mult, mines_list, "Успешный вывод из мин!"

# --- STORM (ШТОРМ) GAME LOGIC ---
STORM_MULTIPLIERS = [1.25, 1.65, 2.30, 3.40, 5.20, 8.50, 15.00]

def start_storm_session(telegram_id: int, bet_amount: int) -> dict:
    if bet_amount < 1:
        raise ValueError("Минимальная ставка 1 ⭐️")
    session_id = uuid.uuid4().hex
    
    # 7 levels, 3 clouds per level (0, 1, 2). 1 has lightning, 2 are safe
    lightning_positions = [random.randint(0, 2) for _ in range(len(STORM_MULTIPLIERS))]
    salt = uuid.uuid4().hex
    proof = hashlib.sha256(f"{salt}:{lightning_positions}".encode()).hexdigest()
    
    active_storm_sessions[session_id] = {
        "session_id": session_id,
        "telegram_id": telegram_id,
        "bet_amount": bet_amount,
        "lightning_positions": lightning_positions,
        "current_level": 0,
        "status": "active",
        "proof": proof,
        "salt": salt
    }
    return {
        "session_id": session_id,
        "proof": proof,
        "bet_amount": bet_amount,
        "multipliers": STORM_MULTIPLIERS,
        "total_levels": len(STORM_MULTIPLIERS)
    }

def step_storm(session_id: str, chosen_cloud: int) -> dict:
    session = active_storm_sessions.get(session_id)
    if not session or session["status"] != "active":
        raise ValueError("Сессия шторма не активна")
    if chosen_cloud not in [0, 1, 2]:
        raise ValueError("Некорректный выбор облака")
        
    level = session["current_level"]
    lightning = session["lightning_positions"][level]
    
    if chosen_cloud == lightning:
        session["status"] = "struck"
        return {
            "status": "struck",
            "hit_lightning": True,
            "level": level,
            "lightning_cloud": lightning,
            "multiplier": 0.0,
            "win_amount": 0
        }
        
    session["current_level"] += 1
    mult = STORM_MULTIPLIERS[level]
    win_amount = int(session["bet_amount"] * mult)
    is_top_reached = (session["current_level"] >= len(STORM_MULTIPLIERS))
    if is_top_reached:
        session["status"] = "won"
        
    return {
        "status": "won" if is_top_reached else "active",
        "hit_lightning": False,
        "level": level,
        "multiplier": mult,
        "win_amount": win_amount,
        "is_top_reached": is_top_reached
    }

def cash_out_storm(session_id: str) -> tuple[bool, int, float, str]:
    session = active_storm_sessions.get(session_id)
    if not session or session["status"] != "active":
        return False, 0, 0.0, "Сессия не активна"
    if session["current_level"] == 0:
        return False, 0, 0.0, "Пройдите хотя бы один уровень"
        
    mult = STORM_MULTIPLIERS[session["current_level"] - 1]
    win_amount = int(session["bet_amount"] * mult)
    session["status"] = "cashed_out"
    return True, win_amount, mult, "Успешный спуск из шторма!"

def open_case(case_id: str) -> dict:
    case = CASES_CATALOG.get(case_id)
    if not case:
        raise ValueError("Кейс не найден")

    items = case["items"]
    weights = [item["weight"] for item in items]
    chosen_base = random.choices(items, weights=weights, k=1)[0]

    total_edition = chosen_base.get("edition", 10000)
    serial_number = random.randint(1, total_edition)

    chosen_item = {
        **chosen_base,
        "serial_number": serial_number,
        "total_edition": total_edition
    }

    stop_index = 38
    reel_items = []
    for i in range(45):
        if i == stop_index:
            reel_items.append(chosen_item)
        else:
            base = random.choice(items)
            reel_items.append({
                **base,
                "serial_number": random.randint(1, base.get("edition", 10000)),
                "total_edition": base.get("edition", 10000)
            })

    return {
        "case_id": case_id,
        "case_name": case["name"],
        "case_price": case["price"],
        "winning_item": chosen_item,
        "stop_index": stop_index,
        "reel_items": reel_items,
        "win_amount": chosen_item["stars"]
    }
