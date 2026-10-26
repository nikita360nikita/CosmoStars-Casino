import asyncio
import logging
import sys
from aiohttp import web
from config import BOT_TOKEN, WEB_HOST, WEB_PORT, WEB_APP_URL
from database import init_db
from bot import bot, dp
from web_server import create_web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

async def start_web_server(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    logger.info("=" * 60)
    logger.info(f"🚀 Web Server & Mini App launched at: http://{WEB_HOST}:{WEB_PORT}")
    logger.info(f"🌐 Configured WebApp URL: {WEB_APP_URL}")
    logger.info("=" * 60)
    return runner

async def main():
    logger.info("Initializing database...")
    await init_db()

    app = create_web_app()
    runner = await start_web_server(app)

    # Start Telegram Bot polling if token is set
    if bot and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        logger.info("🤖 Starting Telegram Bot polling...")
        while True:
            try:
                bot_info = await bot.get_me()
                logger.info(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")
                await dp.start_polling(bot, drop_pending_updates=True)
            except Exception as e:
                logger.error(f"Telegram bot polling error: {e}, retrying in 5s...")
                await asyncio.sleep(5)
    else:
        logger.warning("⚠️ BOT_TOKEN is not set or set to default! Running WebApp only in test/browser mode.")
        logger.info(f"Open http://localhost:{WEB_PORT} in your browser to test the games!")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped gracefully.")
