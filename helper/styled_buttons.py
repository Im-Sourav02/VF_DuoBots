import aiohttp
from pyrogram import Client
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    InputMediaPhoto,
    LinkPreviewOptions,
)

_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

_STYLE_TO_ENUM = {
    "primary": ButtonStyle.PRIMARY,
    "danger": ButtonStyle.DANGER,
    "success": ButtonStyle.SUCCESS,
}

def _is_bot_api_photo(photo) -> bool:
    """URLs and file_ids can go through the Bot API; local paths must use the MTProto fallback."""
    if not isinstance(photo, str) or not photo:
        return False
    if photo.startswith(("http://", "https://")):
        return True
    return "/" not in photo and "\\" not in photo and "." not in photo

def _pyro_parse_mode(parse_mode: str | None):
    return ParseMode.HTML if (parse_mode or "").upper() == "HTML" else ParseMode.DEFAULT

def _redact(err: Exception, bot_token: str) -> str:
    return str(err).replace(bot_token, "<bot-token>") if bot_token else str(err)

def _style_name(style) -> str | None:
    if isinstance(style, ButtonStyle):
        return None if style == ButtonStyle.DEFAULT else style.value
    return style

# ── Button Styling Helper ───────────────────────────────────────────────────

def style_button(
    btn_text: str,
    url: str | None = None,
    callback_data: str | None = None,
    style: str | None = None
) -> dict:
    """
    Returns a dict for Bot API inline keyboard with 'style' attribute.
    Valid styles: 'primary' (blue), 'danger' (red), 'success' (green).
    """
    if not style:
        lower = btn_text.lower().strip()
        if any(k in lower for k in ["premium", "buy", "vip", "danger", "cancel", "close", "delete"]):
            style = "danger"
        elif any(k in lower for k in ["try again", "retry", "setting", "home", "verified", "success"]):
            style = "success"
        elif any(k in lower for k in ["open", "link", "tutorial", "how to", "guide", "about"]):
            style = "primary"
        elif any(k in lower for k in ["channel", "join", "sub"]):
            style = "danger"
        else:
            style = "primary"

    btn_dict = {"text": btn_text, "style": style}
    if url:
        btn_dict["url"] = url
    elif callback_data:
        btn_dict["callback_data"] = callback_data
    return btn_dict

def to_styled_markup(reply_markup) -> dict | None:
    """
    Converts Pyrogram InlineKeyboardMarkup, list of rows, or dict to Bot API styled reply_markup.
    """
    if not reply_markup:
        return None

    if isinstance(reply_markup, dict) and "inline_keyboard" in reply_markup:
        return reply_markup

    rows = []
    if isinstance(reply_markup, InlineKeyboardMarkup):
        matrix = reply_markup.inline_keyboard
    elif isinstance(reply_markup, list):
        matrix = reply_markup
    else:
        return None

    for row in matrix:
        if not isinstance(row, list):
            row = [row]
        new_row = []
        for btn in row:
            if isinstance(btn, dict):
                if btn.get("style") == "default":
                    new_row.append({k: v for k, v in btn.items() if k != "style"})
                elif "style" not in btn:
                    styled = style_button(
                        btn_text=btn.get("text", ""),
                        url=btn.get("url"),
                        callback_data=btn.get("callback_data"),
                        style=btn.get("style")
                    )
                    new_row.append(styled)
                else:
                    new_row.append(btn)
            elif isinstance(btn, InlineKeyboardButton):
                text = btn.text
                url = getattr(btn, "url", None)
                cb = getattr(btn, "callback_data", None)
                st = _style_name(getattr(btn, "style", None))
                new_row.append(style_button(text, url, cb, st))
        if new_row:
            rows.append(new_row)

    return {"inline_keyboard": rows} if rows else None

def to_pyrogram_markup(reply_markup) -> InlineKeyboardMarkup | None:
    """
    Converts styled dict or list of rows back to Pyrogram InlineKeyboardMarkup for fallbacks.
    """
    if isinstance(reply_markup, InlineKeyboardMarkup):
        return reply_markup
    if not reply_markup:
        return None

    if isinstance(reply_markup, dict) and "inline_keyboard" in reply_markup:
        matrix = reply_markup["inline_keyboard"]
    elif isinstance(reply_markup, list):
        matrix = reply_markup
    else:
        return None

    rows = []
    for row in matrix:
        if not isinstance(row, list):
            row = [row]
        new_row = []
        for btn in row:
            if isinstance(btn, dict):
                text = btn.get("text", "")
                url = btn.get("url")
                cb = btn.get("callback_data")
                style = _STYLE_TO_ENUM.get(btn.get("style"), ButtonStyle.DEFAULT)
                new_row.append(InlineKeyboardButton(text, url=url, callback_data=cb, style=style))
            elif isinstance(btn, InlineKeyboardButton):
                new_row.append(btn)
        if new_row:
            rows.append(new_row)

    return InlineKeyboardMarkup(rows) if rows else None

# ── Styled Bot API Send / Edit Helpers ─────────────────────────────────────

async def send_styled_photo(
    client: Client,
    chat_id: int | str,
    photo: str,
    caption: str,
    reply_markup=None,
    message_effect_id: int | str | None = None,
    parse_mode: str = "HTML"
) -> Message | None:
    """
    Sends photo with styled colored buttons via Bot API HTTP, with Pyrogram fallback.
    """
    bot_token = getattr(client, "bot_token", None) or getattr(client, "_bot_token", None)
    styled_markup = to_styled_markup(reply_markup)

    if bot_token and _is_bot_api_photo(photo):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": chat_id,
                    "photo": photo,
                    "caption": caption,
                    "parse_mode": parse_mode
                }
                if styled_markup:
                    payload["reply_markup"] = styled_markup
                if message_effect_id:
                    payload["message_effect_id"] = message_effect_id

                async with session.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", json=payload) as resp:
                    res = await resp.json()
                    if res.get("ok"):
                        msg_id = res["result"]["message_id"]
                        return await client.get_messages(chat_id=chat_id, message_ids=msg_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Bot API sendPhoto failed: {_redact(e, bot_token)}")

    # Fallback to Pyrogram
    pyro_markup = to_pyrogram_markup(reply_markup)
    return await client.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=caption,
        parse_mode=_pyro_parse_mode(parse_mode),
        effect_id=message_effect_id,
        reply_markup=pyro_markup
    )

async def send_styled_message(
    client: Client,
    chat_id: int | str,
    text: str,
    reply_markup=None,
    message_effect_id: int | str | None = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True
) -> Message | None:
    """
    Sends text message with styled colored buttons via Bot API HTTP, with Pyrogram fallback.
    """
    bot_token = getattr(client, "bot_token", None) or getattr(client, "_bot_token", None)
    styled_markup = to_styled_markup(reply_markup)

    if bot_token:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_web_page_preview
                }
                if styled_markup:
                    payload["reply_markup"] = styled_markup
                if message_effect_id:
                    payload["message_effect_id"] = message_effect_id

                async with session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload) as resp:
                    res = await resp.json()
                    if res.get("ok"):
                        msg_id = res["result"]["message_id"]
                        return await client.get_messages(chat_id=chat_id, message_ids=msg_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Bot API sendMessage failed: {_redact(e, bot_token)}")

    # Fallback to Kurigram (pyrogram namespace). Bot API still uses disable_web_page_preview;
    # the MTProto client takes link_preview_options.
    pyro_markup = to_pyrogram_markup(reply_markup)
    send_kwargs = dict(
        chat_id=chat_id,
        text=text,
        parse_mode=_pyro_parse_mode(parse_mode),
        effect_id=message_effect_id,
        reply_markup=pyro_markup,
    )
    if disable_web_page_preview:
        send_kwargs["link_preview_options"] = _NO_PREVIEW
    return await client.send_message(**send_kwargs)

async def edit_styled_message(
    client: Client,
    chat_id: int | str,
    message_id: int,
    text_or_caption: str,
    reply_markup=None,
    is_photo: bool = False,
    parse_mode: str = "HTML"
) -> bool:
    """
    Edits text or photo caption with styled colored buttons via Bot API HTTP.
    """
    bot_token = getattr(client, "bot_token", None) or getattr(client, "_bot_token", None)
    styled_markup = to_styled_markup(reply_markup)

    if bot_token:
        try:
            async with aiohttp.ClientSession() as session:
                method = "editMessageCaption" if is_photo else "editMessageText"
                payload = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "parse_mode": parse_mode
                }
                if is_photo:
                    payload["caption"] = text_or_caption
                else:
                    payload["text"] = text_or_caption

                if styled_markup:
                    payload["reply_markup"] = styled_markup

                async with session.post(f"https://api.telegram.org/bot{bot_token}/{method}", json=payload) as resp:
                    res = await resp.json()
                    if res.get("ok"):
                        return True
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Bot API {method} failed: {_redact(e, bot_token)}")

    # Fallback to Pyrogram
    try:
        pyro_markup = to_pyrogram_markup(reply_markup)
        mode = _pyro_parse_mode(parse_mode)
        if is_photo:
            await client.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text_or_caption, parse_mode=mode, reply_markup=pyro_markup)
        else:
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text_or_caption, parse_mode=mode, reply_markup=pyro_markup)
        return True
    except Exception:
        return False

async def edit_styled_media(
    client: Client,
    chat_id: int | str,
    message_id: int,
    photo: str,
    caption: str,
    reply_markup=None,
    parse_mode: str = "HTML"
) -> bool:
    """
    Replaces a photo message's image + caption + styled buttons (editMessageMedia), with Pyrogram fallback.
    """
    bot_token = getattr(client, "bot_token", None) or getattr(client, "_bot_token", None)
    styled_markup = to_styled_markup(reply_markup)

    if bot_token and _is_bot_api_photo(photo):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "media": {"type": "photo", "media": photo, "caption": caption, "parse_mode": parse_mode},
                }
                if styled_markup:
                    payload["reply_markup"] = styled_markup
                async with session.post(f"https://api.telegram.org/bot{bot_token}/editMessageMedia", json=payload) as resp:
                    res = await resp.json()
                    if res.get("ok"):
                        return True
                    if "not modified" in str(res.get("description", "")):
                        return True
                    client.LOGGER(__name__, client.name).warning(f"Bot API editMessageMedia rejected: {res.get('description')}")
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Bot API editMessageMedia failed: {_redact(e, bot_token)}")

    try:
        await client.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(photo, caption=caption, parse_mode=_pyro_parse_mode(parse_mode)),
            reply_markup=to_pyrogram_markup(reply_markup),
        )
        return True
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            return True
        client.LOGGER(__name__, client.name).warning(f"edit_message_media fallback failed: {type(e).__name__}")
        return False
