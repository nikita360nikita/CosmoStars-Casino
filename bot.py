import logging
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    MenuButtonWebApp,
    PreCheckoutQuery,
    WebAppInfo,
)
from aiogram.client.session.aiohttp import AiohttpSession
from config import BOT_TOKEN, TELEGRAM_PROXY, WEB_APP_URL, REQUIRED_CHANNEL, REQUIRED_CHANNEL_URL
from database import (
    accept_user_terms,
    change_balance,
    get_or_create_user,
    get_top_winners,
    get_user,
    get_user_gifts,
    get_user_history,
    get_user_terms_accepted,
)

logger = logging.getLogger(__name__)

session = AiohttpSession(proxy=TELEGRAM_PROXY) if TELEGRAM_PROXY else None
bot = Bot(token=BOT_TOKEN, session=session) if BOT_TOKEN and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" else None
dp = Dispatcher()

async def check_channel_subscription(user_id: int) -> bool:
    """Verifies whether the user is subscribed to the mandatory Telegram channel."""
    if not REQUIRED_CHANNEL:
        return True
    if not bot:
        return True
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ("member", "administrator", "creator"):
            return True
        return False
    except Exception as e:
        logger.warning("Subscription check error (%s): %s", REQUIRED_CHANNEL, e)
        # If bot is not added to channel yet or channel not found, allow pass to avoid blocking
        return True

def get_sub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Подписаться на канал", url=REQUIRED_CHANNEL_URL)
            ],
            [
                InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_sub")
            ]
        ]
    )

def get_policy_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 Прочитать политику", callback_data="read_policy"),
                InlineKeyboardButton(text="✅ Принять условия", callback_data="accept_terms")
            ]
        ]
    )

def get_policy_read_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять условия и играть", callback_data="accept_terms")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_policy_prompt")
            ]
        ]
    )

def get_main_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    is_https = bool(webapp_url and webapp_url.strip().startswith("https://"))
    if is_https:
        top_button = InlineKeyboardButton(
            text="🎮 ИГРАТЬ",
            web_app=WebAppInfo(url=webapp_url.strip())
        )
    elif webapp_url and (webapp_url.startswith("https://") or "t.me/" in webapp_url):
        top_button = InlineKeyboardButton(
            text="🎮 ИГРАТЬ",
            url=webapp_url.strip()
        )
    else:
        top_button = InlineKeyboardButton(
            text="🎮 ИГРАТЬ",
            callback_data="open_app_info"
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [top_button],
            [
                InlineKeyboardButton(text="⭐️ Пополнить Звёзды", callback_data="buy_stars"),
                InlineKeyboardButton(text="↗️ Вывод средств", callback_data="withdraw_info")
            ],
            [
                InlineKeyboardButton(text="🎒 Мои Подарки", callback_data="my_gifts"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="check_balance")
            ],
            [
                InlineKeyboardButton(text="🏆 Топ игроков", callback_data="leaderboard"),
                InlineKeyboardButton(text="📜 Правила / О боте", callback_data="about_info")
            ]
        ]
    )

def get_deposit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐️ 25 Stars", callback_data="deposit_pack_25"),
                InlineKeyboardButton(text="⭐️ 50 Stars", callback_data="deposit_pack_50")
            ],
            [
                InlineKeyboardButton(text="⭐️ 100 Stars", callback_data="deposit_pack_100"),
                InlineKeyboardButton(text="⭐️ 250 Stars", callback_data="deposit_pack_250")
            ],
            [
                InlineKeyboardButton(text="⭐️ 500 Stars", callback_data="deposit_pack_500"),
                InlineKeyboardButton(text="⭐️ 1000 Stars", callback_data="deposit_pack_1000")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
            ]
        ]
    )

async def send_main_menu(message_or_callback, user, db_user=None, is_edit=False):
    if not db_user:
        db_user = await get_or_create_user(
            telegram_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "Игрок"
        )
    balance = db_user.get("balance", 0) if isinstance(db_user, dict) else (db_user["balance"] if db_user else 0)
    welcome_text = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"Добро пожаловать в <b>CosmoStars Casino</b> — лучшее Telegram Mini App казино на звёзды! ⭐️\n\n"
        f"🎮 <b>Доступные игры:</b>\n"
        f"• 🎁 <b>Кейсы:</b> 12 кейсов с реальными Telegram подарками и NFT!\n"
        f"• ⚡ <b>Апгрейдер:</b> улучшай свои Telegram подарки до ультра-редких!\n"
        f"• 💣 <b>Мины (Mines 5x5):</b> находи кристаллы и забирай растущий куш!\n"
        f"• ⛈️ <b>Шторм (Storm):</b> поднимайся по грозовой башне до x15.00!\n"
        f"• 🚀 <b>Ракетка (Crash):</b> успей забрать выигрыш до взрыва ракеты!\n"
        f"• 🪙 <b>Монетка (Coinflip):</b> Орёл или Решка со множителем x1.80!\n\n"
        f"⭐️ <b>Твой баланс:</b> <code>{balance}</code> ⭐️\n\n"
        f"<i>Нажми кнопку ниже, чтобы запустить игру:</i>"
    )

    markup = get_main_keyboard(WEB_APP_URL)
    if is_edit and isinstance(message_or_callback, types.CallbackQuery):
        try:
            await message_or_callback.message.edit_text(
                text=welcome_text,
                parse_mode="HTML",
                reply_markup=markup
            )
            return
        except Exception as e:
            logger.warning("edit_text failed in send_main_menu, sending as new message: %s", e)

    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.answer(
            text=welcome_text,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        await message_or_callback.answer(
            text=welcome_text,
            parse_mode="HTML",
            reply_markup=markup
        )

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    user = message.from_user
    db_user = await get_or_create_user(
        telegram_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "Игрок"
    )

    # 1. Check mandatory channel subscription
    is_subbed = await check_channel_subscription(user.id)
    if not is_subbed:
        sub_text = (
            f"👋 Привет, <b>{user.first_name}</b>!\n\n"
            f"📢 <b>Для доступа к боту необходимо подписаться на наш официальный канал:</b>\n"
            f"{REQUIRED_CHANNEL_URL}\n\n"
            f"В канале публикуются промокоды на Stars, анонсы обновлений и результаты крупных раздач.\n"
            f"После подписки нажмите кнопку <b>«Проверить подписку»</b> ниже."
        )
        await message.answer(sub_text, parse_mode="HTML", reply_markup=get_sub_keyboard())
        return

    # 2. Check Terms & Privacy Policy acceptance
    terms_accepted = await get_user_terms_accepted(user.id)
    if not terms_accepted:
        policy_prompt = (
            f"👋 Добро пожаловать в <b>CosmoStars Casino</b>! ⭐️\n\n"
            f"Перед началом игры, пожалуйста, подтвердите согласие с <b>Пользовательским соглашением</b> и <b>Политикой конфиденциальности</b> сервиса.\n\n"
            f"⚠️ <i>Сервис предназначен исключительно для лиц старше 18 лет. Нажимая кнопку «Принять условия», вы подтверждаете свой возраст и принимаете правила честной игры Provably Fair.</i>"
        )
        await message.answer(policy_prompt, parse_mode="HTML", reply_markup=get_policy_prompt_keyboard())
        return

    # 3. Everything is verified -> Open Main Menu
    if WEB_APP_URL and WEB_APP_URL.startswith("https://"):
        try:
            await bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=MenuButtonWebApp(
                    text="🎮 ИГРАТЬ",
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            )
        except Exception as e:
            logger.warning("Could not set chat menu button: %s", e)

    await send_main_menu(message, user, db_user, is_edit=False)

@dp.callback_query(F.data == "check_sub")
async def handle_check_sub(callback: types.CallbackQuery):
    user = callback.from_user
    is_subbed = await check_channel_subscription(user.id)
    if not is_subbed:
        await callback.answer("❌ Вы еще не подписались на наш канал! Подпишитесь и повторите попытку.", show_alert=True)
        return

    await callback.answer("✅ Подписка подтверждена!")
    db_user = await get_or_create_user(
        telegram_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "Игрок"
    )
    terms_accepted = await get_user_terms_accepted(user.id)

    if not terms_accepted:
        policy_prompt = (
            f"✅ Подписка подтверждена!\n\n"
            f"Теперь, пожалуйста, подтвердите согласие с <b>Пользовательским соглашением</b> и <b>Политикой конфиденциальности</b> сервиса.\n\n"
            f"⚠️ <i>Сервис предназначен исключительно для совершеннолетних пользователей (18+).</i>"
        )
        await callback.message.edit_text(policy_prompt, parse_mode="HTML", reply_markup=get_policy_prompt_keyboard())
        return

    await send_main_menu(callback, user, db_user, is_edit=True)

@dp.callback_query(F.data == "read_policy")
async def handle_read_policy(callback: types.CallbackQuery):
    await callback.answer()
    policy_full = (
        "📜 <b>ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ И ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ</b>\n\n"
        "<b>1. Общие положения:</b>\n"
        "• Сервис <b>CosmoStars Casino</b> является развлекательной платформой в формате Telegram Mini App.\n"
        "• Использование сервиса разрешено исключительно лицам, достигшим 18 лет.\n\n"
        "<b>2. Валюта и транзакции:</b>\n"
        "• Все платежи и ставки осуществляются исключительно в официальной валюте <b>Telegram Stars (XTR)</b> через защищенный интерфейс Telegram FZ-LLC.\n"
        "• Сервис не хранит платежные реквизиты или банковские карты пользователей.\n"
        "• Игровые подарки (Telegram Gifts) являются виртуальными коллекционными предметами.\n\n"
        "<b>3. Доказуемая честность (Provably Fair):</b>\n"
        "• Каждый раунд (Ракетка, Монетка, Апгрейдер, Кейсы) генерирует результат с криптографическим хэшем SHA-256 до совершения ставки, что исключает подкрутку исходов.\n\n"
        "<b>4. Конфиденциальность:</b>\n"
        "• Мы обрабатываем только ваш публичный Telegram ID и имя для поддержания баланса и инвентаря.\n\n"
        "<i>Нажимая кнопку ниже, вы полностью принимаете данные условия.</i>"
    )
    await callback.message.edit_text(policy_full, parse_mode="HTML", reply_markup=get_policy_read_keyboard())

@dp.callback_query(F.data == "back_to_policy_prompt")
async def handle_back_policy(callback: types.CallbackQuery):
    await callback.answer()
    policy_prompt = (
        f"Перед началом игры подтвердите согласие с <b>Пользовательским соглашением</b> и <b>Политикой конфиденциальности</b> сервиса.\n\n"
        f"⚠️ <i>Сервис предназначен исключительно для совершеннолетних пользователей (18+).</i>"
    )
    await callback.message.edit_text(policy_prompt, parse_mode="HTML", reply_markup=get_policy_prompt_keyboard())

@dp.callback_query(F.data == "accept_terms")
async def handle_accept_terms(callback: types.CallbackQuery):
    user = callback.from_user
    logger.info("User %s accepted terms", user.id)
    try:
        db_user = await get_or_create_user(
            telegram_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "Игрок"
        )
        await accept_user_terms(user.id)
    except Exception as e:
        logger.exception("Error saving accepted terms: %s", e)
        db_user = {"balance": 0}

    await callback.answer("✅ Условия соглашения приняты!")

    if WEB_APP_URL and WEB_APP_URL.startswith("https://"):
        try:
            await bot.set_chat_menu_button(
                chat_id=callback.message.chat.id,
                menu_button=MenuButtonWebApp(
                    text="🎮 ИГРАТЬ",
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            )
        except Exception as e:
            logger.warning("Could not set chat menu button: %s", e)

    await send_main_menu(callback, user, db_user, is_edit=True)

@dp.callback_query(F.data == "open_app_info")
async def handle_open_app_info(callback: types.CallbackQuery):
    await callback.answer()
    info_text = (
        "🎮 <b>CosmoStars Casino:</b>\n\n"
        f"👉 <a href='{WEB_APP_URL}'><b>НАЖМИТЕ ЗДЕСЬ, ЧТОБЫ ИГРАТЬ</b></a>"
    )
    await callback.message.answer(
        info_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ИГРАТЬ", url=WEB_APP_URL)]
        ])
    )

@dp.callback_query(F.data == "back_to_menu")
async def handle_back_menu(callback: types.CallbackQuery):
    user = callback.from_user
    db_user = await get_user(user.id)
    await callback.answer()
    await send_main_menu(callback, user, db_user, is_edit=True)

@dp.callback_query(F.data == "check_balance")
async def handle_check_balance(callback: types.CallbackQuery):
    user = callback.from_user
    db_user = await get_user(user.id)
    balance = db_user["balance"] if db_user else 0
    history = await get_user_history(user.id, limit=5)

    hist_text = ""
    if history:
        hist_text = "\n\n<b>Последние игры:</b>\n"
        for h in history:
            win_sym = "✅ +" if h["win_amount"] > 0 else "❌ -"
            hist_text += f"{win_sym}{h['win_amount'] or h['bet_amount']} ⭐️ в {h['game'].upper()} ({h['multiplier']}x)\n"

    await callback.answer()
    await callback.message.edit_text(
        f"💰 <b>Твой баланс:</b> <code>{balance}</code> ⭐️{hist_text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Пополнить", callback_data="buy_stars")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "buy_stars")
async def handle_buy_stars(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "⭐️ <b>Выберите пакет пополнения через Telegram Stars:</b>\n\n"
        "Оплата происходит мгновенно в официальном интерфейсе Telegram.\n"
        "Звёзды зачисляются на ваш баланс сразу после подтверждения.",
        parse_mode="HTML",
        reply_markup=get_deposit_keyboard()
    )

@dp.callback_query(F.data.startswith("deposit_pack_"))
async def handle_send_invoice(callback: types.CallbackQuery):
    stars_amount = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    payload = f"stars_deposit_{user_id}_{stars_amount}_{uuid.uuid4().hex[:8]}"

    await callback.answer()
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"⭐️ Пополнение на {stars_amount} Stars",
        description=f"Пополнение игрового счета в CosmoStars Casino на {stars_amount} ⭐️",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=f"{stars_amount} Stars", amount=stars_amount)],
        provider_token="",  # Must be empty string for Telegram Stars (XTR)
    )

@dp.callback_query(F.data == "my_gifts")
async def handle_my_gifts(callback: types.CallbackQuery):
    user = callback.from_user
    gifts = await get_user_gifts(user.id, include_sold=False)
    if not gifts:
        text = (
            "🎒 <b>Ваш инвентарь подарков пуст</b>\n\n"
            "Открывайте кейсы в Mini App, чтобы выиграть реальные подарки Telegram с серийными номерами!\n"
            "Их можно хранить в коллекции или мгновенно продавать за ⭐️ Stars."
        )
    else:
        text = f"🎒 <b>Ваша коллекция подарков ({len(gifts)} шт.):</b>\n\n"
        total_val = 0
        for g in gifts[:10]:
            total_val += g['stars_value']
            text += f"• {g['gift_icon']} <b>{g['gift_name']}</b> (<code>#{g['serial_number']}</code>) — <b>{g['stars_value']}</b> ⭐️\n"
        text += f"\n💰 <b>Общая ценность:</b> <code>{total_val}</code> ⭐️"

    open_app_btn = (
        InlineKeyboardButton(text="🎰 Открыть в Mini App", web_app=WebAppInfo(url=WEB_APP_URL))
        if WEB_APP_URL and WEB_APP_URL.startswith("https://")
        else InlineKeyboardButton(text="🎰 Открыть в Mini App", callback_data="open_app_info")
    )

    await callback.answer()
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [open_app_btn],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "leaderboard")
async def handle_leaderboard(callback: types.CallbackQuery):
    leaders = await get_top_winners(limit=10)
    text = "🏆 <b>Топ игроков по балансу звёзд:</b>\n\n"
    for i, l in enumerate(leaders, 1):
        name = l["first_name"] or l["username"] or f"Игрок {l['telegram_id']}"
        text += f"{i}. <b>{name}</b> — <code>{l['balance']}</code> ⭐️\n"

    await callback.answer()
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "about_info")
async def handle_about(callback: types.CallbackQuery):
    text = (
        "ℹ️ <b>О проекте CosmoStars Casino:</b>\n\n"
        "• Игровая платформа Telegram Mini App с азартными играми и кейсами подарков.\n"
        "• Безопасные расчёты в официальной валюте <b>Telegram Stars (XTR)</b>.\n"
        "• Инвентарь с подлинными коллекционными подарками Telegram.\n"
        "• Доказуемо честная механика <b>Provably Fair (SHA-256)</b>.\n\n"
        "📜 Все действия на платформе регулируются Пользовательским соглашением и Политикой конфиденциальности.\n\n"
        "Желаем удачи и крупных побед! 🚀"
    )
    await callback.answer()
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📜 Читать политику", callback_data="read_policy")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "withdraw_info")
async def handle_withdraw_info(callback: types.CallbackQuery):
    text = (
        "↗️ <b>Вывод средств:</b>\n\n"
        "• Минимальная сумма вывода: <b>100 ⭐️</b>.\n"
        "• Способы выплаты: <b>Telegram Stars</b>, <b>TON Wallet</b>, <b>USDT (TRC-20)</b>.\n"
        "• Создать заявку на вывод можно в приложении по кнопке <b>«↗ Вывод»</b> в верхнем меню.\n\n"
        "Все заявки обрабатываются автоматически или администрацией в течение 24 часов."
    )
    await callback.answer()
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ])
    )

# --- TELEGRAM STARS PAYMENTS HANDLERS ---
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payment = message.successful_payment
    stars_amount = payment.total_amount
    charge_id = payment.telegram_payment_charge_id
    user_id = message.from_user.id

    try:
        new_balance = await change_balance(
            telegram_id=user_id,
            delta=stars_amount,
            tx_type="deposit_stars",
            details=f"Пополнение через Telegram Stars: {stars_amount} XTR",
            charge_id=charge_id
        )

        success_msg = (
            f"🎉 <b>Оплата прошла успешно!</b>\n\n"
            f"Вам начислено: <b>+{stars_amount}</b> ⭐️\n"
            f"Ваш текущий баланс: <b>{new_balance}</b> ⭐️\n\n"
            f"Теперь вы можете открыть Mini App и начать играть!"
        )

        await message.answer(
            text=success_msg,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(WEB_APP_URL)
        )
    except Exception as e:
        logger.error("Failed to process payment: %s", e)
        await message.answer("Произошла ошибка при начислении звезд. Обратитесь в поддержку.")

async def create_stars_invoice_link(user_id: int, stars_amount: int) -> str | None:
    if not bot:
        return None
    try:
        payload = f"webapp_deposit_{user_id}_{stars_amount}_{uuid.uuid4().hex[:8]}"
        link = await bot.create_invoice_link(
            title=f"⭐️ Пополнение на {stars_amount} Stars",
            description=f"Пополнение игрового баланса на {stars_amount} Telegram Stars",
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=f"{stars_amount} Stars", amount=stars_amount)],
            provider_token=""
        )
        return link
    except Exception as e:
        logger.error("Failed to create invoice link: %s", e)
        return None
