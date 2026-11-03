import html
from typing import NamedTuple

from config import (
    BOT1_DISPLAY_NAME, BOT2_DISPLAY_NAME, START_MSG, ABOUT_TXT, CHANNELS_TXT,
    PREMIUM_LINK, OWNER_LINK, SUPPORT_LINK, PREMIUM_PRICE_TEXT,
    CREDITS_PER_BYPASS, CREDITS_PER_ACCESS,
)
from helper.styled_buttons import send_styled_photo, send_styled_message, edit_styled_media, edit_styled_message


class Screen(NamedTuple):
    photo: str
    caption: str
    buttons: list


# ── Identity ────────────────────────────────────────────────────────────────

def is_link_bot(client) -> bool:
    return getattr(client, "bot_type", "bot1") in ("bot2", "sephra")

def is_credits_bot(client) -> bool:
    return bool(getattr(client, "credits_enabled", False))

def bot_name(client) -> str:
    return BOT2_DISPLAY_NAME if is_link_bot(client) else BOT1_DISPLAY_NAME

def partner_name(client) -> str:
    return BOT1_DISPLAY_NAME if is_link_bot(client) else BOT2_DISPLAY_NAME


# ── Text helpers ────────────────────────────────────────────────────────────

def fill(template: str, client, user=None, **extra) -> str:
    """Format a message template; unknown/malformed placeholders leave the template untouched."""
    ctx = {
        "first": html.escape(user.first_name or "") if user else "",
        "last": html.escape(user.last_name or "") if user else "",
        "username": f"@{user.username}" if user and user.username else "N/A",
        "mention": user.mention if user else "",
        "id": user.id if user else "",
        "owner_id": client.owner,
        "bot_username": getattr(client, "username", "") or "",
        "bot_name": bot_name(client),
        "partner_name": partner_name(client),
        "earn": CREDITS_PER_BYPASS,
        "cost": CREDITS_PER_ACCESS,
        "price": html.escape(PREMIUM_PRICE_TEXT),
    }
    ctx.update(extra)
    try:
        return template.format(**ctx)
    except (KeyError, IndexError, ValueError):
        return template

def balance_panel(balance: int) -> str:
    return f"<blockquote>◍ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: <b>{balance} ᴄʀᴇᴅɪᴛ{'s' if balance != 1 else ''}</b></blockquote>"

PREMIUM_PANEL = "<blockquote>◍ ʏᴏᴜʀ ᴘʟᴀɴ: <b>ᴘʀᴇᴍɪᴜᴍ</b> — ɴᴏ ᴀᴅs, ɴᴏ ᴄʀᴇᴅɪᴛs ᴜsᴇᴅ</blockquote>"

async def account_panel(client, user_id: int) -> str:
    """Plan/balance panel for the credits bot; informational only, so DB errors just hide it."""
    if not is_credits_bot(client):
        return ""
    try:
        if await client.mongodb.is_pro(user_id):
            return PREMIUM_PANEL
        return balance_panel(await client.mongodb.get_credits(user_id))
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Could not load account panel: {type(e).__name__}")
        return ""


# ── Buttons ─────────────────────────────────────────────────────────────────

def button(label: str, callback: str | None = None, url: str | None = None, style: str = "primary") -> dict | None:
    """Styled button dict; returns None when a URL destination is not configured (button is dropped)."""
    if callback is None and not url:
        return None
    btn = {"text": label, "style": style}
    if url:
        btn["url"] = url
    else:
        btn["callback_data"] = callback
    return btn

def layout(*rows) -> list:
    return [[b for b in row if b] for row in rows if any(row)]

def close_button() -> dict:
    return button("🔴 CLOSE IT", "close", style="danger")

def back_button() -> dict:
    return button("BACK", "start")

def skip_ads_button() -> dict | None:
    return button(f"SKIP ADS ({PREMIUM_PRICE_TEXT.upper()})", url=PREMIUM_LINK, style="success")


# ── Screens ─────────────────────────────────────────────────────────────────

def _photo(client, key: str) -> str:
    return client.messages.get(key) or client.messages.get("START_PHOTO") or ""

async def home_screen(client, user) -> Screen:
    caption = fill(client.messages.get("START", START_MSG), client, user)
    panel = await account_panel(client, user.id)
    if panel:
        caption += "\n" + panel
    show_settings = user.id in client.admins
    buttons = layout(
        [button("HOW TO USE", "help"), button("CHANNELS", "channels")],
        [button("PREMIUM PLANS", "premium")],
        [button("SETTINGS", "settings", style="success")] if show_settings else [],
        [close_button()],
    )
    return Screen(client.messages.get("START_PHOTO", ""), caption, buttons)

def help_screen(client, user) -> Screen:
    buttons = layout(
        [button("PREMIUM", "premium", style="success"), button("OWNER", url=OWNER_LINK, style="default")],
        [button("SUPPORT", url=SUPPORT_LINK, style="default"), back_button()],
        [close_button()],
    )
    return Screen(_photo(client, "HELP_PHOTO"), fill(client.messages.get("HELP", ""), client, user), buttons)

def channels_screen(client, user) -> Screen:
    caption = fill(client.messages.get("CHANNELS", CHANNELS_TXT), client, user)
    return Screen(_photo(client, "CHANNELS_PHOTO"), caption, layout([back_button(), close_button()]))

def about_screen(client, user) -> Screen:
    caption = fill(client.messages.get("ABOUT", ABOUT_TXT), client, user)
    return Screen(client.messages.get("START_PHOTO", ""), caption, layout([back_button(), close_button()]))

async def premium_screen(client, user) -> Screen:
    caption = fill(client.messages.get("PREMIUM", ""), client, user)
    panel = await account_panel(client, user.id)
    if panel:
        caption += "\n" + panel
    buttons = layout(
        [button("BUY PREMIUM", url=PREMIUM_LINK, style="success")],
        [back_button(), close_button()],
    )
    return Screen(_photo(client, "PREMIUM_PHOTO"), caption, buttons)

def verify_screen(client, user, short_link: str, balance: int) -> Screen:
    caption = fill(client.messages.get("SHORT_MSG", ""), client, user) + "\n" + balance_panel(balance)
    tutorial = getattr(client, "tutorial_link", "")
    buttons = layout(
        [button("OPEN LINK", url=short_link), button("TUTORIAL", url=tutorial)],
        [skip_ads_button()],
        [close_button()],
    )
    return Screen(_photo(client, "SHORT_PIC"), caption, buttons)

def verified_screen(client, user, file_link: str, balance: int) -> Screen:
    caption = (
        fill(client.messages.get("VERIFIED", ""), client, user) + "\n"
        + f"<blockquote>◍ ʙᴀʟᴀɴᴄᴇ: <b>{balance} ᴄʀᴇᴅɪᴛs</b> — ᴛᴀᴘ <b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b> ᴛᴏ ᴏᴘᴇɴ ʏᴏᴜʀ ғɪʟᴇs "
        + f"(ᴜsᴇs {CREDITS_PER_ACCESS})</blockquote>"
    )
    buttons = layout(
        [button("CLICK HERE", url=file_link)],
        [skip_ads_button()],
        [close_button()],
    )
    return Screen(_photo(client, "VERIFIED_PHOTO"), caption, buttons)

def link_screen(client, user, link: str, time_str: str) -> Screen:
    caption = fill(client.messages.get("LINK", "{link}"), client, user, link=html.escape(link), time=time_str)
    buttons = layout(
        [button("OPEN LINK", url=link)],
        [back_button(), close_button()],
    )
    return Screen(_photo(client, "LINK_PHOTO"), caption, buttons)


# ── Sending / navigation ────────────────────────────────────────────────────

async def send_screen(client, chat_id: int, screen: Screen, message_effect_id=None):
    if screen.photo:
        return await send_styled_photo(client=client, chat_id=chat_id, photo=screen.photo, caption=screen.caption,
                                       reply_markup=screen.buttons, message_effect_id=message_effect_id)
    return await send_styled_message(client=client, chat_id=chat_id, text=screen.caption,
                                     reply_markup=screen.buttons, message_effect_id=message_effect_id)

async def show_screen(client, query, screen: Screen):
    """Swap the callback's message to `screen` in place; replace the message when its kind must change."""
    msg = query.message
    if screen.photo and msg.photo:
        if await edit_styled_media(client, msg.chat.id, msg.id, screen.photo, screen.caption, screen.buttons):
            return
    elif not screen.photo and msg.text:
        if await edit_styled_message(client, msg.chat.id, msg.id, screen.caption, screen.buttons, is_photo=False):
            return
    try:
        await msg.delete()
    except Exception:
        pass
    await send_screen(client, msg.chat.id, screen)
