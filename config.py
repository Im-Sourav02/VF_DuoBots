import os
import logging
from logging.handlers import RotatingFileHandler

# Load .env file automatically (if present) — no-op in production if vars are set via platform
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Credentials have no source defaults: set them in the environment / .env (see .env.example).
_missing_env = []

def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        _missing_env.append(name)
    return value

def _required_int(name: str) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        _missing_env.append(name)
        return 0
    try:
        return int(raw)
    except ValueError:
        _missing_env.append(name)
        return 0

def _bool_env(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() == "true"

# ═══════════════════════════════════════════════════════════════
# SHARED SETTINGS
# ═══════════════════════════════════════════════════════════════

LOG_FILE_NAME = "bot.log"
PORT = int(os.environ.get("PORT", 5010))
OWNER_ID = _required_int("OWNER_ID")
WORKERS = int(os.environ.get("WORKERS", 5))

API_ID = _required("API_ID")
API_HASH = _required("API_HASH")

MSG_EFFECT = 5046509860389126442

# Fallbacks only: shortener settings saved from the /shortner panel (MongoDB) take precedence.
SHORT_URL = os.environ.get("SHORT_URL", "shortxlinks.com")
SHORT_API = os.environ.get("SHORT_API", "")
SHORT_TUT = os.environ.get("SHORT_TUT", "https://t.me/Infinix_Tutorial/10")
# Optional redirect wrapper around shortened links: https://<domain>/?to=<base64 short link>
REDIRECTOR_DOMAIN = os.environ.get("REDIRECTOR_DOMAIN", "").strip().strip("/")

# Identity mapping (established from .env usernames + runtime roles, not from prompt numbering):
#   BOT1_* = 𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 (@VeloraFileShareRoBot) — filestore, shortener, the ONLY bot with credits
#   BOT2_* = 𝖶𝖺𝗇𝖽𝖺 (@VFFileBot) — link protector, no credits, no ad-bypass accounting
# Prompt wording called Sadie Sink "Bot 2"; the deployed filestore/shortener client is BOT1_*.
BOT1_DISPLAY_NAME = os.environ.get("BOT1_DISPLAY_NAME", "𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬")
BOT2_DISPLAY_NAME = os.environ.get("BOT2_DISPLAY_NAME", "𝖶𝖺𝗇𝖽𝖺")

# ═══════════════════════════════════════════════════════════════
# SHARED UI DESTINATIONS (button targets)
# ═══════════════════════════════════════════════════════════════

PREMIUM_LINK       = os.environ.get("PREMIUM_LINK", "https://t.me/Infinix_Adult/27")
OWNER_LINK         = os.environ.get("OWNER_LINK", "https://t.me/DmSukunaa")
SUPPORT_LINK       = os.environ.get("SUPPORT_LINK", "https://t.me/Infinix_Syndicate")
PREMIUM_PRICE_TEXT = os.environ.get("PREMIUM_PRICE_TEXT", "₹1.5/Day")

# ═══════════════════════════════════════════════════════════════
# CREDITS (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 only)
# ═══════════════════════════════════════════════════════════════

CREDITS_PER_BYPASS = 2   # awarded once per verified shortener bypass
CREDITS_PER_ACCESS = 1   # charged per file/link (single or batch) opened by a non-premium user
VERIFY_TOKEN_TTL   = int(os.environ.get("VERIFY_TOKEN_TTL", 3600))   # seconds a verification link stays valid
VERIFY_MIN_SECONDS = int(os.environ.get("VERIFY_MIN_SECONDS", 0))    # reject redemptions faster than this after issue

DIVIDER = "────────────────"

# ═══════════════════════════════════════════════════════════════
# BOT 1 (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬) — Filestore Bot
# ═══════════════════════════════════════════════════════════════

BOT1_SESSION      = "bot1"
BOT1_TOKEN        = _required("BOT1_TOKEN")
BOT1_BOT_USERNAME = os.environ.get("BOT1_BOT_USERNAME", "VeloraFileShareRoBot")

BOT1_DB_URI      = _required("BOT1_DB_URI")
BOT1_DB_NAME     = os.environ.get("BOT1_DB_NAME", "VF_Bot1")
BOT1_DB_CHANNEL  = _required_int("BOT1_DB_CHANNEL")

BOT1_FSUBS       = []   # Populated dynamically via settings
BOT1_ADMINS      = [OWNER_ID]
BOT1_AUTO_DEL    = int(os.environ.get("BOT1_AUTO_DEL", 300))
BOT1_PROTECT     = _bool_env("BOT1_PROTECT", False)
BOT1_DISABLE_BTN = _bool_env("BOT1_DISABLE_BTN", False)

# Message templates are Telegram HTML. Placeholders: {first} {last} {username} {mention} {id}
# {bot_name} {partner_name} {earn} {cost} {price}. Escape literal "&", "<", ">" as &amp; &lt; &gt;.

START_PIC = os.environ.get("START_PIC", "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg")
START_MSG = os.environ.get("START_MESSAGE",
    "<b>➲ FILE SHARE BOT</b>\n\n"
    "<blockquote>◍ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {bot_name}, {first}. ᴄʜᴏᴏsᴇ ᴛʜᴇ ᴅᴇsɪʀᴇᴅ ᴏᴘᴛɪᴏɴ ғʀᴏᴍ ᴛʜᴇ ᴍᴇɴᴜ ʙᴇʟᴏᴡ.</blockquote>")
ABOUT_TXT = os.environ.get("ABOUT_MESSAGE", """<b>›› ᴄᴏᴍᴍᴜɴɪᴛʏ: <a href='https://t.me/Infinix_Syndicate'>ɪɴꜰɪɴɪx ꜱʏɴᴅɪᴄᴀᴛᴇ</a>
<blockquote expandable>›› ᴏᴡɴᴇʀ: <a href='https://t.me/DmSukunaa'>Sᴜᴋᴜɴᴀ</a>
›› ʟᴀɴɢᴜᴀɢᴇ: <a href='https://docs.python.org/3/'>Pʏᴛʜᴏɴ 3</a>
›› ʟɪʙʀᴀʀʏ: <a href='https://docs.kurigram.icu/'>Kᴜʀɪɢʀᴀᴍ</a>
›› ᴅᴀᴛᴀʙᴀsᴇ: <a href='https://www.mongodb.com/docs/'>Mᴏɴɢᴏ ᴅʙ</a>
›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @DmSukunaa</b></blockquote>""")
CHANNELS_TXT = os.environ.get("CHANNELS_MESSAGE",
    "<b>➲ OUR OFFICIAL NETWORK</b>\n\n"
    "<blockquote>◍ <i>ᴄʜᴇᴄᴋ ᴏᴜᴛ ᴏᴜʀ ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟs &amp; ᴄᴏᴍᴍᴜɴɪᴛɪᴇs!</i></blockquote>\n"
    "<blockquote expandable>‣ <b>ᴀɴɪᴍᴇ:</b> <a href='https://t.me/Animes_Infinix'>ᴀɴɪᴍᴇ ɪɴꜰɪɴɪx</a>\n"
    "‣ <b>ᴍᴏᴠɪᴇs:</b> <a href='https://t.me/Movies_Infinix'>ᴍᴏᴠɪᴇꜱ ɪɴꜰɪɴɪx</a>\n"
    "‣ <b>ᴡᴇʙsᴇʀɪᴇs:</b> <a href='https://t.me/Webseries_Infinix'>ᴡᴇʙꜱᴇʀɪᴇꜱ ɪɴꜰɪɴɪx</a>\n"
    "‣ <b>ᴀᴅᴜʟᴛ:</b> <a href='https://t.me/Infinix_Adult'>ᴄᴏʀɴʜᴜʙ</a>\n"
    "‣ <b>ᴍᴀɴʜᴡᴀ:</b> <a href='https://t.me/Pornhwa_Infinix'>ᴘᴏʀɴʜᴡᴀ</a>\n"
    "‣ <b>ᴄᴏᴍᴍᴜɴɪᴛʏ:</b> <a href='https://t.me/Infinix_Syndicate'>ɪɴꜰɪɴɪx ꜱʏɴᴅɪᴄᴀᴛᴇ</a>\n"
    "‣ <b>ᴅᴇᴠᴇʟᴏᴘᴇʀ:</b> @DmSukunaa</blockquote>")

CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "")

_PREMIUM_STEPS = (
    "<blockquote>◍ ᴛᴀᴘ <b>ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ</b> ʙᴇʟᴏᴡ.\n"
    "◍ sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴘʟᴀɴ &amp; ᴄᴏᴍᴘʟᴇᴛᴇ ᴘᴀʏᴍᴇɴᴛ.\n"
    "◍ ᴘʀᴇᴍɪᴜᴍ ɪs ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴏɴᴄᴇ ᴘᴀʏᴍᴇɴᴛ ɪs ᴄᴏɴғɪʀᴍᴇᴅ.</blockquote>"
)
_PREMIUM_BENEFITS_CREDITS = (
    "<blockquote expandable><b>≡ | PREMIUM BENEFITS:</b>\n"
    "‣ ɴᴏ sʜᴏʀᴛᴇɴᴇʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ\n"
    "‣ ɴᴏ ᴄʀᴇᴅɪᴛs ᴜsᴇᴅ ᴘᴇʀ ғɪʟᴇ/ʟɪɴᴋ\n"
    "‣ 4ᴋ ᴜʜᴅ (2160ᴘ) ғɪʟᴇs ᴜɴʟᴏᴄᴋᴇᴅ\n"
    "‣ ғɪʟᴇ ʀᴇǫᴜᴇsᴛs ᴠɪᴀ /request</blockquote>\n"
    + _PREMIUM_STEPS
)
_PREMIUM_BENEFITS_LINKS = (
    "<blockquote expandable><b>≡ | PREMIUM BENEFITS:</b>\n"
    "‣ ɴᴏ sʜᴏʀᴛᴇɴᴇʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴏɴ {partner_name}\n"
    "‣ ᴜɴɪɴᴛᴇʀʀᴜᴘᴛᴇᴅ ᴅᴏᴡɴʟᴏᴀᴅs\n"
    "‣ 4ᴋ ᴜʜᴅ (2160ᴘ) ғɪʟᴇs ᴜɴʟᴏᴄᴋᴇᴅ</blockquote>\n"
    + _PREMIUM_STEPS
)

BOT1_MESSAGES = {
    "START": os.environ.get("BOT1_START_MSG", START_MSG),
    "FSUB": os.environ.get("BOT1_FSUB_MSG",
        "<b>➲ JOIN REQUIRED</b>\n\n"
        "<blockquote>◍ ʏᴏᴜʀ ғɪʟᴇ ɪs ʀᴇᴀᴅʏ ‼️ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ʙᴇʟᴏᴡ, ᴛʜᴇɴ ᴛᴀᴘ ᴛʀʏ ᴀɢᴀɪɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇs.</blockquote>"),
    "ABOUT": os.environ.get("BOT1_ABOUT_MSG", ABOUT_TXT),
    "CHANNELS": os.environ.get("BOT1_CHANNELS_MSG", CHANNELS_TXT),
    "HELP": os.environ.get("BOT1_HELP_MSG",
        "<b>➲ 📖 HOW TO USE THIS BOT</b>\n\n"
        "<blockquote>◍ sᴇɴᴅ ᴀɴʏ ғɪʟᴇ ᴏʀ ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ᴀ sʜᴀʀᴇᴀʙʟᴇ ғɪʟᴇ sᴛᴏʀᴇ ʟɪɴᴋ.\n"
        "◍ ᴄʟɪᴄᴋ ᴏɴ sʜᴏʀᴛ ʟɪɴᴋs ᴛᴏ ᴠᴇʀɪғʏ ᴀᴄᴄᴇss, ᴏʀ ᴜᴘɢʀᴀᴅᴇ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ ғᴏʀ ᴅɪʀᴇᴄᴛ ᴀᴄᴄᴇss ᴡɪᴛʜᴏᴜᴛ ᴀᴅs.\n"
        "◍ ғʀᴇᴇ ᴜsᴇʀs: ᴏɴᴇ ᴠᴇʀɪғɪᴇᴅ ᴀᴅ ʙʏᴘᴀss ᴇᴀʀɴs <b>{earn} ᴄʀᴇᴅɪᴛs</b>; ᴇᴀᴄʜ ғɪʟᴇ/ʟɪɴᴋ ᴀᴄᴄᴇss ᴜsᴇs <b>{cost}</b>.\n"
        "◍ ғɪʟᴇs ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ, sᴏ ғᴏʀᴡᴀʀᴅ ᴛʜᴇᴍ ᴛᴏ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs.</blockquote>"),
    "PREMIUM": os.environ.get("BOT1_PREMIUM_MSG",
        "<b>➲ PREMIUM SUBSCRIPTION</b>\n\n"
        "<blockquote>◍ <i>ᴜɴʟᴏᴄᴋ ᴜʟᴛɪᴍᴀᴛᴇ ʙᴇɴᴇғɪᴛs &amp; ᴇɴᴊᴏʏ ᴜɴɪɴᴛᴇʀʀᴜᴘᴛᴇᴅ ᴅᴏᴡɴʟᴏᴀᴅs, sᴛᴀʀᴛɪɴɢ ᴀᴛ {price}!</i></blockquote>\n"
        + _PREMIUM_BENEFITS_CREDITS),
    "REPLY": os.environ.get("BOT1_REPLY_MSG", "<b>𝖥𝗈𝗋 𝖬𝗈𝗋𝖾 𝖩𝗈𝗂𝗇 - @VeloraFilms</b>"),
    "SHORT_MSG": os.environ.get("BOT1_SHORT_MSG",
        "<b>➲ SHORTENER VERIFICATION</b>\n"
        "<blockquote>◍ ᴇʜ? ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙʏᴘᴀss ᴛʜɪs ǫᴜɪᴄᴋ ʟɪɴᴋ ᴛᴏ ᴜɴʟᴏᴄᴋ ʏᴏᴜʀ ғɪʟᴇs</blockquote>\n"
        "<blockquote>◍ ᴛɪʀᴇᴅ ᴏғ ᴀɴɴᴏʏɪɴɢ ᴀᴅs &amp; ᴄᴀᴘᴛᴄʜᴀs? ᴊᴜsᴛ ɢᴇᴛ ᴠɪᴘ ᴛᴏ sᴋɪᴘ ɪᴛ ᴀʟʟ ᴀʟʀᴇᴀᴅʏ, ʙ-ʙᴀᴋᴀ!</blockquote>\n"
        + DIVIDER + "\n"
        "<blockquote>◍ ᴇᴀᴄʜ ᴀᴅ ʙʏᴘᴀss ɢɪᴠᴇs <b>{earn:02d} ᴄʀᴇᴅɪᴛs</b>, ᴀɴᴅ <b>{cost} ᴄʀᴇᴅɪᴛ</b> ɪs ᴜsᴇᴅ ᴘᴇʀ ғɪʟᴇ/ʟɪɴᴋ ᴀᴄᴄᴇss.</blockquote>\n"
        "<blockquote>≡ ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ — sᴛᴀʀᴛɪɴɢ ᴀᴛ ᴊᴜsᴛ {price}, ᴀᴅ-ғʀᴇᴇ ʟᴜxᴜʀʏ ᴀᴄᴄᴇss!</blockquote>"),
    "VERIFIED": os.environ.get("BOT1_VERIFIED_MSG",
        "<b>➲ VERIFICATION SUCCESSFUL ✅</b>\n"
        "<blockquote>◍ <i>{earn} ᴄʀᴇᴅɪᴛs ʜᴀᴠᴇ ʙᴇᴇɴ ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ!</i></blockquote>\n"
        + DIVIDER + "\n"
        "<blockquote>≡ <i>ᴛɪʀᴇᴅ ᴏғ ᴠᴇʀɪғʏɪɴɢ ᴇᴠᴇʀʏ ᴛɪᴍᴇ? ɢᴇᴛ ᴠɪᴘ ғᴏʀ ᴢᴇʀᴏ ᴀᴅs!</i></blockquote>"),
    "CUSTOM_CAPTION": os.environ.get("BOT1_CUSTOM_CAPTION", CUSTOM_CAPTION),
    "START_PHOTO":    os.environ.get("BOT1_START_PHOTO", START_PIC),
    "HELP_PHOTO":     os.environ.get("BOT1_HELP_PHOTO", ""),
    "CHANNELS_PHOTO": os.environ.get("BOT1_CHANNELS_PHOTO", ""),
    "PREMIUM_PHOTO":  os.environ.get("BOT1_PREMIUM_PHOTO", ""),
    "VERIFIED_PHOTO": os.environ.get("BOT1_VERIFIED_PHOTO", ""),
    "FSUB_PHOTO":  os.environ.get("BOT1_FSUB_PHOTO", "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg"),
    "SHORT_PIC":   os.environ.get("BOT1_SHORT_PIC",  "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg"),
    "SHORT":       os.environ.get("BOT1_SHORT",      "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg"),
}



# ═══════════════════════════════════════════════════════════════
# BOT 2 (𝖶𝖺𝗇𝖽𝖺) — Link Protector Bot
# ═══════════════════════════════════════════════════════════════

BOT2_SESSION      = "bot2"
# Optional: leave empty to run Bot 1 alone (main.py skips Bot 2).
BOT2_TOKEN        = os.environ.get("BOT2_TOKEN", "").strip()
BOT2_BOT_USERNAME = os.environ.get("BOT2_BOT_USERNAME", "VFFileBot")

BOT2_DB_URI       = os.environ.get("BOT2_DB_URI", "").strip() or BOT1_DB_URI
BOT2_DB_NAME      = os.environ.get("BOT2_DB_NAME", "VF_Bot2")
# Private Telegram channel where Bot1 links are stored as text messages.
# Bot2 must be admin with post permission in this channel.
_bot2_channel = os.environ.get("BOT2_DB_CHANNEL", "0").strip()
BOT2_DB_CHANNEL   = int(_bot2_channel) if _bot2_channel else 0

BOT2_FSUBS        = []
BOT2_ADMINS       = [OWNER_ID]
BOT2_AUTO_DEL     = int(os.environ.get("BOT2_AUTO_DEL", 300))
BOT2_PROTECT      = _bool_env("BOT2_PROTECT", False)
BOT2_DISABLE_BTN  = _bool_env("BOT2_DISABLE_BTN", True)

BOT2_MESSAGES = {
    "START": os.environ.get("BOT2_START_MSG",
        "<b>➲ FILE SHARE BOT</b>\n\n"
        "<blockquote>◍ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {bot_name}, {first}. ᴄʜᴏᴏsᴇ ᴛʜᴇ ᴅᴇsɪʀᴇᴅ ᴏᴘᴛɪᴏɴ ғʀᴏᴍ ᴛʜᴇ ᴍᴇɴᴜ ʙᴇʟᴏᴡ.</blockquote>"),
    "FSUB": os.environ.get("BOT2_FSUB_MSG", os.environ.get("SEPHRA_FSUB_MSG",
        "<b>➲ JOIN REQUIRED</b>\n\n"
        "<blockquote>◍ ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ, ᴛʜᴇɴ ᴛᴀᴘ ᴛʀʏ ᴀɢᴀɪɴ.</blockquote>")),
    "ABOUT": os.environ.get("BOT2_ABOUT_MSG", ABOUT_TXT),
    "CHANNELS": os.environ.get("BOT2_CHANNELS_MSG", CHANNELS_TXT),
    "HELP": os.environ.get("BOT2_HELP_MSG",
        "<b>➲ 📖 HOW TO USE THIS BOT</b>\n\n"
        "<blockquote>◍ ᴛᴀᴘ ᴀ ʟɪɴᴋ ғʀᴏᴍ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴏᴘᴇɴ ɪᴛ ʜᴇʀᴇ.\n"
        "◍ ɪ'ʟʟ sᴇɴᴅ ᴀ sᴇᴄᴜʀᴇ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ ᴛʜᴀᴛ ᴏᴘᴇɴs {partner_name}, ᴡʜᴇʀᴇ ʏᴏᴜʀ ғɪʟᴇs ᴀʀᴇ ᴅᴇʟɪᴠᴇʀᴇᴅ.\n"
        "◍ ᴛʜᴇ ʟɪɴᴋ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇs, sᴏ ᴏᴘᴇɴ ɪᴛ sᴏᴏɴ.</blockquote>"),
    "PREMIUM": os.environ.get("BOT2_PREMIUM_MSG",
        "<b>➲ PREMIUM SUBSCRIPTION</b>\n\n"
        "<blockquote>◍ <i>ᴜɴʟᴏᴄᴋ ᴜʟᴛɪᴍᴀᴛᴇ ʙᴇɴᴇғɪᴛs &amp; ᴇɴᴊᴏʏ ᴜɴɪɴᴛᴇʀʀᴜᴘᴛᴇᴅ ᴅᴏᴡɴʟᴏᴀᴅs, sᴛᴀʀᴛɪɴɢ ᴀᴛ {price}!</i></blockquote>\n"
        + _PREMIUM_BENEFITS_LINKS),
    "LINK": os.environ.get("BOT2_LINK_MSG",
        "<b>➲ DOWNLOAD LINK READY</b>\n\n"
        "<blockquote>{link}</blockquote>\n"
        "<blockquote>⏳ ᴛʜɪs ʟɪɴᴋ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇᴅ ɪɴ {time}.</blockquote>"),
    "REPLY": os.environ.get("BOT2_REPLY_MSG", "<b>For More Join - @Infinix_Adult</b>"),
    "SHORT_MSG": "",
    "CUSTOM_CAPTION": os.environ.get("BOT2_CUSTOM_CAPTION", CUSTOM_CAPTION),
    "START_PHOTO":    os.environ.get("BOT2_START_PHOTO", "https://images5.alphacoders.com/136/thumb-1920-1364203.jpeg"),
    "HELP_PHOTO":     os.environ.get("BOT2_HELP_PHOTO", ""),
    "CHANNELS_PHOTO": os.environ.get("BOT2_CHANNELS_PHOTO", ""),
    "PREMIUM_PHOTO":  os.environ.get("BOT2_PREMIUM_PHOTO", ""),
    "LINK_PHOTO":     os.environ.get("BOT2_LINK_PHOTO", ""),
    "FSUB_PHOTO":  os.environ.get("BOT2_FSUB_PHOTO",  "https://images5.alphacoders.com/136/thumb-1920-1364203.jpeg"),
    "SHORT_PIC":   "",
    "SHORT":       "",
}

if _missing_env:
    raise SystemExit(
        "Missing required environment variables: " + ", ".join(_missing_env) + ". See .env.example."
    )

# ═══════════════════════════════════════════════════════════════
# LEGACY ALIASES (kept for backward compatibility)
# ═══════════════════════════════════════════════════════════════

RIN_SESSION      = BOT1_SESSION
RIN_TOKEN        = BOT1_TOKEN
RIN_BOT_USERNAME = BOT1_BOT_USERNAME
RIN_DB_URI       = BOT1_DB_URI
RIN_DB_NAME      = BOT1_DB_NAME
RIN_DB_CHANNEL   = BOT1_DB_CHANNEL
RIN_FSUBS        = BOT1_FSUBS
RIN_ADMINS       = BOT1_ADMINS
RIN_AUTO_DEL     = BOT1_AUTO_DEL
RIN_PROTECT      = BOT1_PROTECT
RIN_DISABLE_BTN  = BOT1_DISABLE_BTN
RIN_MESSAGES     = BOT1_MESSAGES

SEPHRA_SESSION      = BOT2_SESSION
SEPHRA_TOKEN        = BOT2_TOKEN
SEPHRA_BOT_USERNAME = BOT2_BOT_USERNAME
SEPHRA_DB_URI       = BOT2_DB_URI
SEPHRA_DB_NAME      = BOT2_DB_NAME
SEPHRA_DB_CHANNEL   = BOT2_DB_CHANNEL
SEPHRA_FSUBS        = BOT2_FSUBS
SEPHRA_ADMINS       = BOT2_ADMINS
SEPHRA_AUTO_DEL     = BOT2_AUTO_DEL
SEPHRA_PROTECT      = BOT2_PROTECT
SEPHRA_DISABLE_BTN  = BOT2_DISABLE_BTN
SEPHRA_MESSAGES     = BOT2_MESSAGES

SESSION      = BOT1_SESSION
TOKEN        = BOT1_TOKEN
DB_URI       = BOT1_DB_URI
DB_NAME      = BOT1_DB_NAME
DB_CHANNEL   = BOT1_DB_CHANNEL
FSUBS        = BOT1_FSUBS
ADMINS       = BOT1_ADMINS
AUTO_DEL     = BOT1_AUTO_DEL
PROTECT      = BOT1_PROTECT
DISABLE_BTN  = BOT1_DISABLE_BTN
MESSAGES     = BOT1_MESSAGES

# ═══════════════════════════════════════════════════════════════
# LOGGER FACTORY
# ═══════════════════════════════════════════════════════════════

def LOGGER(name: str, client_name: str) -> logging.Logger:
    logger = logging.getLogger(f"{client_name}.{name}")
    if logger.handlers:
        return logger  # Already configured — avoid duplicate handlers
    formatter = logging.Formatter(
        f"[%(asctime)s - %(levelname)s] - {client_name} - %(name)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    file_handler = RotatingFileHandler(LOG_FILE_NAME, maxBytes=50_000_000, backupCount=10)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger
