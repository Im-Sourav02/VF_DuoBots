import os
import logging
from logging.handlers import RotatingFileHandler

# Load .env file automatically (if present) — no-op in production if vars are set via platform
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ═══════════════════════════════════════════════════════════════
# SHARED SETTINGS
# ═══════════════════════════════════════════════════════════════

LOG_FILE_NAME = "bot.log"
PORT = int(os.environ.get("PORT", 5010))
OWNER_ID = int(os.environ.get("OWNER_ID", 6123108288))
WORKERS = int(os.environ.get("WORKERS", 5))

API_ID = os.environ.get("API_ID", "21446955")
API_HASH = os.environ.get("API_HASH", "e6f34a6186963663342b88b88c2b4750")

MSG_EFFECT = 5046509860389126442

SHORT_URL = os.environ.get("SHORT_URL", "shortxlinks.com")
SHORT_API = os.environ.get("SHORT_API", "79d083375a3a6d9a1554ff6507494e72154bcb59")
SHORT_TUT = os.environ.get("SHORT_TUT", "https://t.me/Infinix_Tutorial/10")

BOT1_DISPLAY_NAME = "𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬"
BOT2_DISPLAY_NAME = "𝖶𝖺𝗇𝖽𝖺"

# ═══════════════════════════════════════════════════════════════
# BOT 1 (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬) — Filestore Bot
# ═══════════════════════════════════════════════════════════════

BOT1_SESSION      = "bot1"
BOT1_TOKEN        = os.environ.get("BOT1_TOKEN", "8942865689:AAEEQVat17zXX_ZXyMFVeV7Sozz9TRCq7X0")
BOT1_BOT_USERNAME = os.environ.get("BOT1_BOT_USERNAME", "VeloraFileShareRoBot")

BOT1_DB_URI = os.environ.get(
    "BOT1_DB_URI",
    "mongodb+srv://souravagarwal14092007:szXRs8g7fErCnn4@cluster0.xlsbf3o.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

BOT1_DB_NAME     = os.environ.get("BOT1_DB_NAME", "VF_Bot1")
BOT1_DB_CHANNEL  = int(os.environ.get("BOT1_DB_CHANNEL", -1002558171315))

BOT1_FSUBS       = []   # Populated dynamically via settings
BOT1_ADMINS      = [OWNER_ID]
BOT1_AUTO_DEL    = int(os.environ.get("BOT1_AUTO_DEL", 300))
BOT1_PROTECT     = os.environ.get("BOT1_PROTECT", "false").lower() == "true"
BOT1_DISABLE_BTN = os.environ.get("BOT1_DISABLE_BTN", "false").lower() == "true"

START_PIC = os.environ.get("START_PIC", "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg")
START_MSG = os.environ.get("START_MESSAGE", "<b>›› ʜᴇʏ!!, {first} ~ <blockquote>ʟᴏᴠᴇ ᴍᴏᴠɪᴇs & ᴡᴇʙsᴇʀɪᴇs? ɪ ᴀᴍ ᴍᴀᴅᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴛᴏ ғɪɴᴅ ᴡʜᴀᴛ ʏᴏᴜ aʀᴇ ʟᴏᴏᴋɪɴɢ ꜰᴏʀ.</blockquote></b>")
ABOUT_TXT = os.environ.get("ABOUT_MESSAGE", """<b>›› ᴄᴏᴍᴍᴜɴɪᴛʏ: <a href='https://t.me/Infinix_Syndicate'>ɪɴꜰɪɴɪx ꜱʏɴᴅɪᴄᴀᴛᴇ</a>
<blockquote expandable>›› ᴏᴡɴᴇʀ: <a href='https://t.me/DmSukunaa'>Sᴜᴋᴜɴᴀ</a>
›› ʟᴀɴɢᴜᴀɢᴇ: <a href='https://docs.python.org/3/'>Pʏᴛʜᴏɴ 3</a>
›› ʟɪʙʀᴀʀʏ: <a href='https://docs.pyrogram.org/'>Pʏʀᴏɢʀᴀᴍ ᴠ2</a>
›› ᴅᴀᴛᴀʙᴀsᴇ: <a href='https://www.mongodb.com/docs/'>Mᴏɴɢᴏ ᴅʙ</a>
›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @DmSukunaa</b></blockquote>""")
CHANNELS_TXT = os.environ.get("CHANNELS_MESSAGE", """<b>›› ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ: <a href='https://t.me/Animes_Infinix'>ᴀɴɪᴍᴇ ɪɴꜰɪɴɪx</a>
<blockquote expandable>›› ᴍᴏᴠɪᴇs: <a href='https://t.me/Movies_Infinix'>ᴍᴏᴠɪᴇꜱ ɪɴꜰɪɴɪx</a>
›› ᴡᴇʙsᴇʀɪᴇs: <a href='https://t.me/Webseries_Infinix'>ᴡᴇʙꜱᴇʀɪᴇꜱ ɪɴꜰɪɴɪx</a>
›› ᴀᴅᴜʟᴛ ᴄʜᴀɴɴᴇʟs: <a href='https://t.me/Infinix_Adult'>ᴄᴏʀɴʜᴜʙ</a>
›› ᴍᴀɴʜᴡᴀ ᴄʜᴀɴɴᴇʟ: <a href='https://t.me/Pornhwa_Infinix'>ᴘᴏʀɴʜᴡᴀ</a>
›› ᴄᴏᴍᴍᴜɴɪᴛʏ: <a href='https://t.me/Infinix_Syndicate'>ɪɴꜰɪɴɪx ꜱʏɴᴅɪᴄᴀᴛᴇ</a>
›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @DmSukunaa</b></blockquote>""")

CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "")

BOT1_MESSAGES = {
    "START": os.environ.get("BOT1_START_MSG", START_MSG),
    "FSUB": os.environ.get("BOT1_FSUB_MSG",
        "<b><blockquote>›› ʜᴇʏ ×</blockquote>\n  ʏᴏᴜʀ ғɪʟᴇ ɪs ʀᴇᴀᴅʏ ‼️ ʟᴏᴏᴋs ʟɪᴋᴇ ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ sᴜʙsᴄʀɪʙᴇᴅ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ʏᴇᴛ, sᴜʙsᴄʀɪʙᴇ ɴᴏᴡ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇs</b>"),
    "ABOUT": os.environ.get("BOT1_ABOUT_MSG", ABOUT_TXT),
    "CHANNELS": os.environ.get("BOT1_CHANNELS_MSG", CHANNELS_TXT),
    "REPLY": os.environ.get("BOT1_REPLY_MSG", "<b>𝖥𝗈𝗋 𝖬𝗈𝗋𝖾 𝖩𝗈𝗂𝗇 - @VeloraFilms</b>"),
    "SHORT_MSG": os.environ.get("BOT1_SHORT_MSG",
        "<b>📊 ʜᴇʏ {first}, \n\n‼️ ɢᴇᴛ ᴀʟʟ ꜰɪʟᴇꜱ ɪɴ ᴀ ꜱɪɴɢʟᴇ ʟɪɴᴋ ‼️\n\n ⌯ ʏᴏᴜʀ ʟɪɴᴋ ɪꜱ ʀᴇᴀᴅʏ, ᴋɪɴᴅʟʏ ᴄʟɪᴄᴋ ᴏɴ ᴏᴘᴇɴ ʟɪɴᴋ ʙᴜᴛᴛᴏɴ..</b>"),
    "CUSTOM_CAPTION": os.environ.get("BOT1_CUSTOM_CAPTION", CUSTOM_CAPTION),
    "START_PHOTO": os.environ.get("BOT1_START_PHOTO", START_PIC),
    "FSUB_PHOTO":  os.environ.get("BOT1_FSUB_PHOTO", "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg"),
    "SHORT_PIC":   os.environ.get("BOT1_SHORT_PIC",  "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg"),
    "SHORT":       os.environ.get("BOT1_SHORT",      "https://i.ibb.co/j99YZ78w/photo-2026-08-03-06-15-50-7669685325676937236.jpg"),
}



# ═══════════════════════════════════════════════════════════════
# BOT 2 (𝖶𝖺𝗇𝖽𝖺) — Link Protector Bot
# ═══════════════════════════════════════════════════════════════

BOT2_SESSION      = "bot2"
BOT2_TOKEN        = os.environ.get("BOT2_TOKEN", "8916730344:AAGa9hdqmxgSBT2GP8iPk9ek6t4ZPxB1F4M")
BOT2_BOT_USERNAME = os.environ.get("BOT2_BOT_USERNAME", "VFFileBot")

BOT2_DB_URI       = os.environ.get("BOT2_DB_URI", "mongodb+srv://souravagarwal14092007:szXRs8g7fErCnn4@cluster0.xlsbf3o.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
BOT2_DB_NAME      = os.environ.get("BOT2_DB_NAME", "VF_Bot2")
# Private Telegram channel where Bot1 links are stored as text messages.
# Bot2 must be admin with post permission in this channel.
BOT2_DB_CHANNEL   = int(os.environ.get("BOT2_DB_CHANNEL", 0))

BOT2_FSUBS        = []
BOT2_ADMINS       = [OWNER_ID]
BOT2_AUTO_DEL     = int(os.environ.get("BOT2_AUTO_DEL", 300))
BOT2_PROTECT      = os.environ.get("BOT2_PROTECT", False)
BOT2_DISABLE_BTN  = os.environ.get("BOT2_DISABLE_BTN", "true").lower() == "true"

BOT2_MESSAGES = {
    "START": os.environ.get("BOT2_START_MSG", START_MSG),
    "FSUB": os.environ.get("BOT2_FSUB_MSG", os.environ.get("SEPHRA_FSUB_MSG",
        "<b><blockquote>›› ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ!</blockquote></b>")),
    "ABOUT": os.environ.get("BOT2_ABOUT_MSG", ABOUT_TXT),
    "CHANNELS": os.environ.get("BOT2_CHANNELS_MSG", CHANNELS_TXT),
    "REPLY": os.environ.get("BOT2_REPLY_MSG", "<b>For More Join - @Infinix_Adult</b>"),
    "SHORT_MSG": "",
    "CUSTOM_CAPTION": os.environ.get("BOT2_CUSTOM_CAPTION", CUSTOM_CAPTION),
    "START_PHOTO": os.environ.get("BOT2_START_PHOTO", "https://images5.alphacoders.com/136/thumb-1920-1364203.jpeg"),
    "FSUB_PHOTO":  os.environ.get("BOT2_FSUB_PHOTO",  "https://images5.alphacoders.com/136/thumb-1920-1364203.jpeg"),
    "SHORT_PIC":   "",
    "SHORT":       "",
}

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
