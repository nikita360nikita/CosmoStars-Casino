import hashlib
import hmac
import json
import logging
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web
from config import BASE_DIR, BOT_TOKEN
from database import (
    add_user_gift,
    change_balance,
    get_or_create_user,
    get_recent_drops,
    get_top_winners,
    get_user,
    get_user_gifts,
    get_user_history,
    log_game,
    sell_user_gift,
    sell_all_user_gifts,
    consume_user_gift,
    create_withdrawal,
    get_user_withdrawals,
)
from game_logic import (
    CASES_CATALOG,
    TELEGRAM_GIFTS,
    active_crash_sessions,
    cash_out_crash,
    open_case,
    play_coinflip,
    play_gift_upgrader,
    start_crash_round,
    start_mines_session,
    reveal_mines_tile,
    cash_out_mines,
    active_mines_sessions,
    start_storm_session,
    step_storm,
    cash_out_storm,
    active_storm_sessions,
)
from bot import create_stars_invoice_link

logger = logging.getLogger(__name__)

STATIC_DIR = BASE_DIR / "static"

def validate_telegram_data(init_data_raw: str, bot_token: str) -> dict | None:
    """Validates Telegram WebApp initData with HMAC-SHA256."""
    if not init_data_raw:
        return None
    try:
        parsed_data = dict(parse_qsl(init_data_raw, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None
        received_hash = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if hmac.compare_digest(calculated_hash, received_hash):
            user_data = json.loads(parsed_data.get("user", "{}"))
            return user_data
    except Exception as e:
        logger.warning("Telegram initData validation failed: %s", e)
    return None

def json_response(data: dict, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, ensure_ascii=False),
        content_type="application/json",
        status=status,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Init-Data",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        }
    )

# --- ROUTE HANDLERS ---

async def handle_options(request: web.Request) -> web.Response:
    return web.Response(
        status=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Init-Data",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        }
    )

async def handle_get_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")

async def get_request_user(request: web.Request) -> dict:
    """Extracts or identifies user from Telegram WebApp initData or query/json (for browser testing)."""
    # 1. Try initData header
    init_data = request.headers.get("X-Init-Data", "")
    user_info = validate_telegram_data(init_data, BOT_TOKEN)
    if user_info and "id" in user_info:
        user_id = user_info["id"]
        username = user_info.get("username", "")
        first_name = user_info.get("first_name", "Игрок")
        return await get_or_create_user(user_id, username, first_name)
    
    # 2. Try query or body user_id (for browser testing / fallback)
    user_id = None
    if request.can_read_body:
        try:
            body = await request.json()
            user_id = body.get("user_id")
        except Exception:
            pass

    if not user_id:
        user_id = request.query.get("user_id")

    if user_id:
        try:
            uid = int(user_id)
            return await get_or_create_user(uid, f"player_{uid}", f"Игрок #{uid}")
        except ValueError:
            pass

    # Default demo test user (ID 999999)
    return await get_or_create_user(999999, "demo_player", "Тестовый Игрок")

async def api_get_user(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    history = await get_user_history(user["telegram_id"], limit=10)
    gifts = await get_user_gifts(user["telegram_id"], include_sold=False)
    return json_response({
        "success": True,
        "user": user,
        "history": history,
        "gifts_count": len(gifts),
        "gifts_value": sum(g["stars_value"] for g in gifts)
    })

async def api_get_leaderboard(request: web.Request) -> web.Response:
    leaders = await get_top_winners(limit=10)
    return json_response({
        "success": True,
        "leaders": leaders
    })

async def api_get_cases(request: web.Request) -> web.Response:
    return json_response({
        "success": True,
        "cases": list(CASES_CATALOG.values()),
        "all_gifts": list(TELEGRAM_GIFTS.values())
    })

# --- CRASH (РАКЕТКА) ---
async def api_crash_start(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    bet = int(data.get("bet_amount", 0))

    if bet <= 0:
        return json_response({"success": False, "error": "Некорректная сумма ставки"}, 400)
    if user["balance"] < bet:
        return json_response({"success": False, "error": "Недостаточно звезд на балансе"}, 400)

    try:
        new_balance = await change_balance(
            telegram_id=user["telegram_id"],
            delta=-bet,
            tx_type="bet_crash",
            details=f"Ставка в Ракетке: {bet} XTR"
        )
        round_info = start_crash_round(user["telegram_id"], bet)
        return json_response({
            "success": True,
            "session_id": round_info["session_id"],
            "hash_proof": round_info["hash_proof"],
            "crash_point": round_info["crash_multiplier"],
            "bet_amount": bet,
            "new_balance": new_balance
        })
    except Exception as e:
        return json_response({"success": False, "error": str(e)}, 500)

async def api_crash_cashout(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    session_id = data.get("session_id")
    client_mult = float(data.get("multiplier", 1.0))

    session = active_crash_sessions.get(session_id)
    if not session or session["telegram_id"] != user["telegram_id"]:
        return json_response({"success": False, "error": "Сессия не найдена"}, 400)

    is_win, win_amount, final_mult, msg = cash_out_crash(session_id, client_mult)
    new_balance = user["balance"]

    if is_win:
        new_balance = await change_balance(
            telegram_id=user["telegram_id"],
            delta=win_amount,
            tx_type="win_crash",
            details=f"Выигрыш в Ракетке: {win_amount} XTR ({final_mult}x)"
        )
        await log_game(
            telegram_id=user["telegram_id"],
            game="crash",
            bet=session["bet_amount"],
            win=win_amount,
            multiplier=final_mult,
            details={"status": "won", "cashed_at": final_mult, "actual_crash": session["crash_multiplier"]}
        )
    else:
        await log_game(
            telegram_id=user["telegram_id"],
            game="crash",
            bet=session["bet_amount"],
            win=0,
            multiplier=final_mult,
            details={"status": "crashed", "actual_crash": session["crash_multiplier"]}
        )

    return json_response({
        "success": True,
        "is_win": is_win,
        "win_amount": win_amount,
        "final_multiplier": final_mult,
        "actual_crash": session["crash_multiplier"],
        "new_balance": new_balance,
        "message": msg
    })

# --- COINFLIP (МОНЕТКА) ---
async def api_coinflip_play(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    bet = int(data.get("bet_amount", 0))
    side = data.get("side", "heads")

    if bet <= 0:
        return json_response({"success": False, "error": "Некорректная сумма ставки"}, 400)
    if user["balance"] < bet:
        return json_response({"success": False, "error": "Недостаточно звезд на балансе"}, 400)
    if side not in ("heads", "tails"):
        return json_response({"success": False, "error": "Неверная сторона монеты"}, 400)

    try:
        balance_after_bet = await change_balance(
            telegram_id=user["telegram_id"],
            delta=-bet,
            tx_type="bet_coinflip",
            details=f"Ставка в Монетке ({side}): {bet} XTR"
        )
        result = play_coinflip(bet, side)
        final_balance = balance_after_bet

        if result["is_win"]:
            final_balance = await change_balance(
                telegram_id=user["telegram_id"],
                delta=result["win_amount"],
                tx_type="win_coinflip",
                details=f"Выигрыш в Монетке: +{result['win_amount']} XTR (x1.95)"
            )

        await log_game(
            telegram_id=user["telegram_id"],
            game="coinflip",
            bet=bet,
            win=result["win_amount"],
            multiplier=result["multiplier"],
            details=result
        )

        return json_response({
            "success": True,
            "winning_side": result["winning_side"],
            "chosen_side": side,
            "is_win": result["is_win"],
            "win_amount": result["win_amount"],
            "multiplier": result["multiplier"],
            "new_balance": final_balance,
            "proof": result["proof"]
        })
    except Exception as e:
        return json_response({"success": False, "error": str(e)}, 500)

# --- UPGRADER (УЛУЧШЕНИЕ ПОДАРКОВ И STARS) ---
async def api_upgrader_play(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()

    source_gift_id = data.get("source_gift_id")
    source_stars = int(data.get("source_stars", 0))
    target_gift_id = data.get("target_gift_id")

    if not target_gift_id or target_gift_id not in TELEGRAM_GIFTS:
        return json_response({"success": False, "error": "Выберите целевой подарок для улучшения"}, 400)

    source_value = 0
    consumed_gift_name = ""

    # Case A: Upgrading an existing gift from user's inventory
    if source_gift_id:
        consumed_gift = await consume_user_gift(int(source_gift_id), user["telegram_id"])
        if not consumed_gift:
            return json_response({"success": False, "error": "Подарок для улучшения не найден или уже продан"}, 400)
        source_value = consumed_gift["stars_value"]
        consumed_gift_name = consumed_gift["gift_name"]

    # Case B: Upgrading using Stars directly
    elif source_stars > 0:
        if user["balance"] < source_stars:
            return json_response({"success": False, "error": "Недостаточно звезд на балансе"}, 400)
        source_value = source_stars
        await change_balance(
            telegram_id=user["telegram_id"],
            delta=-source_stars,
            tx_type="upgrade_bet",
            details=f"Апгрейд {source_stars} XTR на {TELEGRAM_GIFTS[target_gift_id]['name']}"
        )
    else:
        return json_response({"success": False, "error": "Выберите подарок или сумму звезд для апгрейда"}, 400)

    try:
        result = play_gift_upgrader(source_value, target_gift_id)
        gift_db_id = None
        current_user = await get_user(user["telegram_id"])
        new_balance = current_user["balance"]

        if result["is_win"]:
            won_gift = result["winning_item"]
            gift_db_id = await add_user_gift(
                telegram_id=user["telegram_id"],
                gift_id=won_gift["id"],
                gift_name=won_gift["name"],
                gift_icon=won_gift["icon"],
                rarity=won_gift["rarity"],
                stars_value=won_gift["stars"],
                serial_number=won_gift["serial_number"],
                total_edition=won_gift["total_edition"]
            )

        await log_game(
            telegram_id=user["telegram_id"],
            game="upgrader",
            bet=source_value,
            win=result["target_value"] if result["is_win"] else 0,
            multiplier=result["multiplier"] if result["is_win"] else 0.0,
            details={
                "source_value": source_value,
                "source_gift": consumed_gift_name or f"{source_value} Stars",
                "target_gift": result["target_gift"]["name"],
                "is_win": result["is_win"]
            }
        )

        return json_response({
            "success": True,
            "is_win": result["is_win"],
            "source_value": source_value,
            "target_gift": result["target_gift"],
            "winning_item": result["winning_item"],
            "gift_db_id": gift_db_id,
            "multiplier": result["multiplier"],
            "win_chance_percent": result["win_chance_percent"],
            "win_sector_angle": result["win_sector_angle"],
            "stop_angle": result["stop_angle"],
            "new_balance": new_balance
        })
    except ValueError as ve:
        return json_response({"success": False, "error": str(ve)}, 400)
    except Exception as e:
        logger.error("Upgrader error: %s", e)
        return json_response({"success": False, "error": str(e)}, 500)

# --- CASES WITH REAL TELEGRAM GIFTS ---
async def api_case_open(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    case_id = data.get("case_id")

    case = CASES_CATALOG.get(case_id)
    if not case:
        return json_response({"success": False, "error": "Кейс не существует"}, 400)

    price = case["price"]
    if user["balance"] < price:
        return json_response({"success": False, "error": "Недостаточно звезд на открытие кейса"}, 400)

    try:
        # Deduct price of case
        balance_after_buy = await change_balance(
            telegram_id=user["telegram_id"],
            delta=-price,
            tx_type="case_buy",
            details=f"Открытие кейса '{case['name']}': {price} XTR"
        )

        drop_result = open_case(case_id)
        winning_item = drop_result["winning_item"]
        win_stars = winning_item["stars"]

        # Deposit real Telegram gift into user's inventory
        gift_db_id = await add_user_gift(
            telegram_id=user["telegram_id"],
            gift_id=winning_item["id"],
            gift_name=winning_item["name"],
            gift_icon=winning_item["icon"],
            rarity=winning_item["rarity"],
            stars_value=win_stars,
            serial_number=winning_item["serial_number"],
            total_edition=winning_item["total_edition"]
        )

        mult = round(win_stars / price, 2)
        await log_game(
            telegram_id=user["telegram_id"],
            game="cases",
            bet=price,
            win=win_stars,
            multiplier=mult,
            details={
                "case_id": case_id,
                "gift": winning_item["name"],
                "serial": winning_item["serial_number"],
                "rarity": winning_item["rarity"]
            }
        )

        return json_response({
            "success": True,
            "case_id": case_id,
            "case_name": case["name"],
            "winning_item": winning_item,
            "gift_db_id": gift_db_id,
            "stop_index": drop_result["stop_index"],
            "reel_items": drop_result["reel_items"],
            "win_amount": win_stars,
            "new_balance": balance_after_buy
        })
    except Exception as e:
        logger.error("Error opening case: %s", e)
        return json_response({"success": False, "error": str(e)}, 500)

# --- USER GIFTS INVENTORY API ---
async def api_get_user_gifts(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    gifts = await get_user_gifts(user["telegram_id"], include_sold=False)
    for g in gifts:
        meta = TELEGRAM_GIFTS.get(g.get("gift_id"), {})
        g["thumbnail"] = meta.get("thumbnail", "")
        g["ru_name"] = meta.get("ru_name", g.get("gift_name"))
        g["description"] = meta.get("description", "")
    total_val = sum(g["stars_value"] for g in gifts)
    return json_response({
        "success": True,
        "gifts": gifts,
        "total_value": total_val,
        "count": len(gifts)
    })

async def api_sell_user_gift(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    gift_id = int(data.get("gift_id", 0))

    if not gift_id:
        return json_response({"success": False, "error": "Не указан ID подарка"}, 400)

    ok, new_bal, msg = await sell_user_gift(gift_id, user["telegram_id"])
    if not ok:
        return json_response({"success": False, "error": msg}, 400)

    return json_response({
        "success": True,
        "message": msg,
        "new_balance": new_bal
    })

async def api_sell_all_user_gifts(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    ok, new_bal, total_stars, msg = await sell_all_user_gifts(user["telegram_id"])
    if not ok:
        return json_response({"success": False, "error": msg}, 400)
    return json_response({
        "success": True,
        "message": msg,
        "total_stars": total_stars,
        "new_balance": new_bal
    })

# --- WITHDRAWALS (ВЫВОД СРЕДСТВ) ---
async def api_create_withdrawal(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    amount = int(data.get("amount", 0))
    address = str(data.get("address", "")).strip()
    method = str(data.get("method", "Telegram Stars")).strip()

    if amount < 100:
        return json_response({"success": False, "error": "Минимальная сумма вывода 100 ⭐️"}, 400)
    if not address:
        return json_response({"success": False, "error": "Укажите адрес или username для вывода"}, 400)

    ok, new_bal, msg = await create_withdrawal(user["telegram_id"], amount, address, method)
    if not ok:
        return json_response({"success": False, "error": msg}, 400)

    return json_response({
        "success": True,
        "message": msg,
        "new_balance": new_bal
    })

async def api_get_withdrawals(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    withdrawals = await get_user_withdrawals(user["telegram_id"])
    return json_response({
        "success": True,
        "withdrawals": withdrawals
    })

# --- MINES (МИНЫ 5x5) HANDLERS ---
async def api_mines_start(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    bet = int(data.get("bet_amount", 0))
    mines_count = int(data.get("mines_count", 3))

    if bet <= 0:
        return json_response({"success": False, "error": "Некорректная ставка"}, 400)
    if user["balance"] < bet:
        return json_response({"success": False, "error": "Недостаточно звезд на балансе"}, 400)

    try:
        new_balance = await change_balance(
            telegram_id=user["telegram_id"],
            delta=-bet,
            tx_type="bet_mines",
            details=f"Ставка в Минах: {bet} XTR ({mines_count} мин)"
        )
        session_info = start_mines_session(user["telegram_id"], bet, mines_count)
        return json_response({
            "success": True,
            "session_id": session_info["session_id"],
            "proof": session_info["proof"],
            "bet_amount": bet,
            "mines_count": mines_count,
            "new_balance": new_balance
        })
    except Exception as e:
        return json_response({"success": False, "error": str(e)}, 400)

async def api_mines_reveal(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    session_id = data.get("session_id")
    tile_index = int(data.get("tile_index", -1))

    session = active_mines_sessions.get(session_id)
    if not session or session["telegram_id"] != user["telegram_id"]:
        return json_response({"success": False, "error": "Сессия не найдена"}, 400)

    try:
        res = reveal_mines_tile(session_id, tile_index)
        new_balance = user["balance"]
        if res["status"] == "lost":
            await log_game(
                telegram_id=user["telegram_id"],
                game="mines",
                bet=session["bet_amount"],
                win=0,
                multiplier=0.0,
                details={"status": "lost", "mines_count": session["mines_count"]}
            )
        elif res["status"] == "won":
            new_balance = await change_balance(
                telegram_id=user["telegram_id"],
                delta=res["win_amount"],
                tx_type="win_mines",
                details=f"Победа в Минах: {res['win_amount']} XTR ({res['multiplier']}x)"
            )
            await log_game(
                telegram_id=user["telegram_id"],
                game="mines",
                bet=session["bet_amount"],
                win=res["win_amount"],
                multiplier=res["multiplier"],
                details={"status": "won_all", "mines_count": session["mines_count"]}
            )

        return json_response({
            "success": True,
            **res,
            "new_balance": new_balance
        })
    except Exception as e:
        return json_response({"success": False, "error": str(e)}, 400)

async def api_mines_cashout(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    session_id = data.get("session_id")

    session = active_mines_sessions.get(session_id)
    if not session or session["telegram_id"] != user["telegram_id"]:
        return json_response({"success": False, "error": "Сессия не найдена"}, 400)

    ok, win_amount, mult, mines_list, msg = cash_out_mines(session_id)
    if not ok:
        return json_response({"success": False, "error": msg}, 400)

    new_balance = await change_balance(
        telegram_id=user["telegram_id"],
        delta=win_amount,
        tx_type="win_mines",
        details=f"Забор из Мин: {win_amount} XTR ({mult}x)"
    )
    await log_game(
        telegram_id=user["telegram_id"],
        game="mines",
        bet=session["bet_amount"],
        win=win_amount,
        multiplier=mult,
        details={"status": "cashed_out", "mines_count": session["mines_count"]}
    )

    return json_response({
        "success": True,
        "win_amount": win_amount,
        "multiplier": mult,
        "mine_positions": mines_list,
        "new_balance": new_balance,
        "message": msg
    })

# --- STORM (ШТОРМ) HANDLERS ---
async def api_storm_start(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    bet = int(data.get("bet_amount", 0))

    if bet <= 0:
        return json_response({"success": False, "error": "Некорректная ставка"}, 400)
    if user["balance"] < bet:
        return json_response({"success": False, "error": "Недостаточно звезд на балансе"}, 400)

    try:
        new_balance = await change_balance(
            telegram_id=user["telegram_id"],
            delta=-bet,
            tx_type="bet_storm",
            details=f"Ставка в Шторме: {bet} XTR"
        )
        session_info = start_storm_session(user["telegram_id"], bet)
        return json_response({
            "success": True,
            "session_id": session_info["session_id"],
            "proof": session_info["proof"],
            "bet_amount": bet,
            "multipliers": session_info["multipliers"],
            "total_levels": session_info["total_levels"],
            "new_balance": new_balance
        })
    except Exception as e:
        return json_response({"success": False, "error": str(e)}, 400)

async def api_storm_step(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    session_id = data.get("session_id")
    chosen_cloud = int(data.get("chosen_cloud", 0))

    session = active_storm_sessions.get(session_id)
    if not session or session["telegram_id"] != user["telegram_id"]:
        return json_response({"success": False, "error": "Сессия не найдена"}, 400)

    try:
        res = step_storm(session_id, chosen_cloud)
        new_balance = user["balance"]
        if res["status"] == "struck":
            await log_game(
                telegram_id=user["telegram_id"],
                game="storm",
                bet=session["bet_amount"],
                win=0,
                multiplier=0.0,
                details={"status": "struck", "level": res["level"]}
            )
        elif res["status"] == "won":
            new_balance = await change_balance(
                telegram_id=user["telegram_id"],
                delta=res["win_amount"],
                tx_type="win_storm",
                details=f"Победа в Шторме: {res['win_amount']} XTR ({res['multiplier']}x)"
            )
            await log_game(
                telegram_id=user["telegram_id"],
                game="storm",
                bet=session["bet_amount"],
                win=res["win_amount"],
                multiplier=res["multiplier"],
                details={"status": "won_top", "level": res["level"]}
            )

        return json_response({
            "success": True,
            **res,
            "new_balance": new_balance
        })
    except Exception as e:
        return json_response({"success": False, "error": str(e)}, 400)

async def api_storm_cashout(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    session_id = data.get("session_id")

    session = active_storm_sessions.get(session_id)
    if not session or session["telegram_id"] != user["telegram_id"]:
        return json_response({"success": False, "error": "Сессия не найдена"}, 400)

    ok, win_amount, mult, msg = cash_out_storm(session_id)
    if not ok:
        return json_response({"success": False, "error": msg}, 400)

    new_balance = await change_balance(
        telegram_id=user["telegram_id"],
        delta=win_amount,
        tx_type="win_storm",
        details=f"Забор из Шторма: {win_amount} XTR ({mult}x)"
    )
    await log_game(
        telegram_id=user["telegram_id"],
        game="storm",
        bet=session["bet_amount"],
        win=win_amount,
        multiplier=mult,
        details={"status": "cashed_out", "level": session["current_level"]}
    )

    return json_response({
        "success": True,
        "win_amount": win_amount,
        "multiplier": mult,
        "new_balance": new_balance,
        "message": msg
    })

# --- LIVE ACTIVITY FEED ---
async def api_get_live_feed(request: web.Request) -> web.Response:
    drops = await get_recent_drops(limit=15)
    enriched = []
    for d in drops:
        item_id = d.get("gift_id")
        meta = TELEGRAM_GIFTS.get(item_id, {})
        enriched.append({
            **d,
            "thumbnail": meta.get("thumbnail", ""),
            "ru_name": meta.get("ru_name", d.get("gift_name")),
        })

    # If DB has few drops, add simulated realistic drops from active players
    if len(enriched) < 10:
        import random
        simulated_users = [
            ("Pavel", "durov"),
            ("Александр", "sasha_crypto"),
            ("Михаил", "misha_ton"),
            ("Daria", "dasha_stars"),
            ("CryptoKing", "cryptoking"),
            ("Артем", "artem_tg"),
            ("Elena", "elena_vip"),
            ("Maxim", "max_win"),
            ("Sergey", "serg_lucky"),
            ("Anna", "anna_sparkle")
        ]
        gift_keys = list(TELEGRAM_GIFTS.keys())
        for i in range(12 - len(enriched)):
            fname, uname = random.choice(simulated_users)
            gkey = random.choice(gift_keys)
            gdata = TELEGRAM_GIFTS[gkey]
            enriched.append({
                "id": 9000 + i,
                "first_name": fname,
                "username": uname,
                "gift_name": gdata["name"],
                "ru_name": gdata["ru_name"],
                "gift_icon": gdata["icon"],
                "thumbnail": gdata.get("thumbnail", ""),
                "rarity": gdata["rarity"],
                "stars_value": gdata["stars"],
                "serial_number": random.randint(1, gdata["edition"])
            })

    return json_response({
        "success": True,
        "drops": enriched
    })

# --- DEPOSITS & TELEGRAM STARS ---
async def api_create_invoice(request: web.Request) -> web.Response:
    user = await get_request_user(request)
    data = await request.json()
    stars_amount = int(data.get("stars_amount", 50))

    if stars_amount < 1:
        return json_response({"success": False, "error": "Сумма звезд должна быть не менее 1"}, 400)

    link = await create_stars_invoice_link(user["telegram_id"], stars_amount)
    if not link:
        return json_response({
            "success": False,
            "error": "Не удалось создать счет Stars. Проверьте BOT_TOKEN в настройках."
        }, 500)

    return json_response({
        "success": True,
        "invoice_link": link,
        "stars_amount": stars_amount
    })

async def api_demo_add_stars(request: web.Request) -> web.Response:
    """Demo endpoint for testing in desktop browsers without real Stars."""
    user = await get_request_user(request)
    data = await request.json()
    amount = int(data.get("amount", 100))

    new_balance = await change_balance(
        telegram_id=user["telegram_id"],
        delta=amount,
        tx_type="demo_gift",
        details=f"Тестовое начисление: +{amount} XTR"
    )
    return json_response({
        "success": True,
        "amount": amount,
        "new_balance": new_balance
    })

def create_web_app() -> web.Application:
    app = web.Application()
    
    # Static files & index
    app.router.add_get("/", handle_get_index)
    app.router.add_static("/static/", path=STATIC_DIR, name="static")

    # API routes
    app.router.add_route("OPTIONS", "/{tail:.*}", handle_options)
    app.router.add_get("/api/user", api_get_user)
    app.router.add_get("/api/leaderboard", api_get_leaderboard)
    app.router.add_get("/api/cases", api_get_cases)
    app.router.add_get("/api/live_feed", api_get_live_feed)

    # Gifts inventory endpoints
    app.router.add_get("/api/user/gifts", api_get_user_gifts)
    app.router.add_post("/api/user/gifts/sell", api_sell_user_gift)
    app.router.add_post("/api/user/gifts/sell_all", api_sell_all_user_gifts)

    # Withdrawals endpoints
    app.router.add_post("/api/withdraw", api_create_withdrawal)
    app.router.add_get("/api/withdraw/history", api_get_withdrawals)

    # Game endpoints
    app.router.add_post("/api/games/crash/start", api_crash_start)
    app.router.add_post("/api/games/crash/cashout", api_crash_cashout)
    app.router.add_post("/api/games/coinflip", api_coinflip_play)
    app.router.add_post("/api/games/upgrader", api_upgrader_play)
    app.router.add_post("/api/cases/open", api_case_open)
    app.router.add_post("/api/games/mines/start", api_mines_start)
    app.router.add_post("/api/games/mines/reveal", api_mines_reveal)
    app.router.add_post("/api/games/mines/cashout", api_mines_cashout)
    app.router.add_post("/api/games/storm/start", api_storm_start)
    app.router.add_post("/api/games/storm/step", api_storm_step)
    app.router.add_post("/api/games/storm/cashout", api_storm_cashout)

    # Stars & Demo endpoints
    app.router.add_post("/api/deposit/create_invoice", api_create_invoice)
    app.router.add_post("/api/demo/add_stars", api_demo_add_stars)

    return app
