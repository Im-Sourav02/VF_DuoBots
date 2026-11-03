import asyncio
import logging
from bot import Bot, web_app
from config import (
    # Shared
    API_ID, API_HASH, WORKERS,
    # Bot 1 (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬) — filestore, credits enabled
    BOT1_SESSION, BOT1_TOKEN, BOT1_BOT_USERNAME,
    BOT1_DB_URI, BOT1_DB_NAME, BOT1_DB_CHANNEL,
    BOT1_FSUBS, BOT1_ADMINS, BOT1_MESSAGES,
    BOT1_AUTO_DEL, BOT1_PROTECT, BOT1_DISABLE_BTN,
    # Bot 2 (𝖶𝖺𝗇𝖽𝖺) — link protector, no credits
    BOT2_SESSION, BOT2_TOKEN, BOT2_BOT_USERNAME,
    BOT2_DB_URI, BOT2_DB_NAME, BOT2_DB_CHANNEL,
    BOT2_FSUBS, BOT2_ADMINS, BOT2_MESSAGES,
    BOT2_AUTO_DEL, BOT2_PROTECT, BOT2_DISABLE_BTN,
)


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S'
)
logger = logging.getLogger("aio.main")

# ═══════════════════════════════════════════════════════════════
# Bot factory helpers
# ═══════════════════════════════════════════════════════════════

def _make_bot1() -> Bot:
    return Bot(
        session=BOT1_SESSION,
        workers=WORKERS,
        db=BOT1_DB_CHANNEL,
        fsub=BOT1_FSUBS,
        token=BOT1_TOKEN,
        admins=BOT1_ADMINS,
        messages=BOT1_MESSAGES,
        auto_del=BOT1_AUTO_DEL,
        db_uri=BOT1_DB_URI,
        db_name=BOT1_DB_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        protect=BOT1_PROTECT,
        disable_btn=BOT1_DISABLE_BTN,
        bot_type="bot1",
        bot2_db_channel=BOT2_DB_CHANNEL,
        bot2_bot_username=BOT2_BOT_USERNAME,
        credits_enabled=True,
    )


def _make_bot2() -> Bot | None:
    if not BOT2_TOKEN:
        logger.warning("[SKIP] BOT2_TOKEN / Bot2_Token is empty -- Bot 2 (𝖶𝖺𝗇𝖽𝖺) will NOT start.")
        return None
    if not BOT2_DB_CHANNEL:
        logger.warning("[SKIP] BOT2_DB_CHANNEL is 0 -- Bot 2 (𝖶𝖺𝗇𝖽𝖺) will NOT start.")
        return None
    if (BOT2_DB_URI, BOT2_DB_NAME) == (BOT1_DB_URI, BOT1_DB_NAME):
        logger.warning(
            "BOT1 and BOT2 use the same MongoDB database; users, settings and 𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬's credits "
            "would be shared with 𝖶𝖺𝗇𝖽𝖺. Set distinct BOT1_DB_NAME / BOT2_DB_NAME."
        )
    return Bot(
        session=BOT2_SESSION,
        workers=WORKERS,
        db=BOT2_DB_CHANNEL,
        fsub=BOT2_FSUBS,
        token=BOT2_TOKEN,
        admins=BOT2_ADMINS,
        messages=BOT2_MESSAGES,
        auto_del=BOT2_AUTO_DEL,
        db_uri=BOT2_DB_URI,
        db_name=BOT2_DB_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        protect=BOT2_PROTECT,
        disable_btn=BOT2_DISABLE_BTN,
        bot_type="bot2",
        credits_enabled=False,
    )


# ═══════════════════════════════════════════════════════════════
# Start each bot individually — if one fails, log it and continue
# ═══════════════════════════════════════════════════════════════

async def safe_run_bot(bot):
    """
    Start a single bot, keep it running, and stop it cleanly on exit.
    If start() raises, log the error and return without crashing the process.
    """
    name = getattr(bot, 'name', repr(bot))
    try:
        await bot.start()
        logger.info(f"[OK] {name} is running.")
        # Keep this coroutine alive until the bot stops
        await asyncio.Event().wait()  # blocks forever
    except (RuntimeError, Exception) as e:
        logger.error(f"[FAILED] {name} failed to start: {e}")
    finally:
        try:
            await bot.stop()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════

async def main():
    candidates = [_make_bot1(), _make_bot2()]
    bots = [b for b in candidates if b is not None]

    logger.info(f"Starting {len(bots)} bot(s)…")

    # Run all bots concurrently; each handles its own errors
    await asyncio.gather(
        *(safe_run_bot(b) for b in bots),
        web_app(),
        return_exceptions=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("AIO stopped.")
