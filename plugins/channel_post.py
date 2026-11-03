import asyncio
from pyrogram import filters, Client, ContinuePropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from helper.helper_func import encode, NO_PREVIEW
from helper import ui


def _is_command_message(message: Message) -> bool:
    if getattr(message, "command", None):
        return True
    raw = message.text or message.caption
    if raw is None:
        return False
    stripped = str(raw).lstrip("\ufeff\u200b\u200c\u200d\u2060 \t")
    if stripped.startswith(("/", "!")):
        return True
    for ent in list(message.entities or []) + list(message.caption_entities or []):
        ent_type = getattr(ent, "type", None)
        name = getattr(ent_type, "name", None) or str(ent_type)
        if "BOT_COMMAND" in name.upper():
            return True
    return False


#===============================================================#
# channel_post — Bot 1 filestore catch-all (group 1). Commands and
# active /batch asks skip this handler so /start and /broadcast
# never get the unused-message reply.
#===============================================================#

def _has_active_listener(client: Client, message: Message) -> bool:
    chat_id = getattr(message.chat, "id", None)
    user_id = getattr(message.from_user, "id", None)
    for listener in list(getattr(client, "_listeners", []) or []):
        future = listener.get("future")
        if future is None or future.done():
            continue
        if listener.get("chat_id") is not None and listener["chat_id"] != chat_id:
            continue
        if listener.get("user_id") is not None and listener["user_id"] != user_id:
            continue
        return True
    return False


# Group 1 so /start /broadcast /batch always run first. Commands still skip here
# because later groups run unless the earlier handler raises StopPropagation.
@Client.on_message(filters.private, group=1)
async def channel_post(client: Client, message: Message):
    if not ui.is_filestore(client):
        raise ContinuePropagation

    if _is_command_message(message):
        raise ContinuePropagation

    if message.service:
        raise ContinuePropagation

    if _has_active_listener(client, message):
        raise ContinuePropagation

    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    wait_msg = await message.reply_text("Please Wait...!")
    try:
        post_message = await message.copy(chat_id=client.db, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        post_message = await message.copy(chat_id=client.db, disable_notification=True)
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"channel_post copy failed: {e}")
        await wait_msg.edit_text("Something went Wrong..!")
        return

    converted_id  = post_message.id * abs(client.db)
    string        = f"get-{converted_id}"
    base64_string = await encode(string)
    link          = f"https://t.me/{client.username}?start={base64_string}"

    from plugins.link_generator import _auto_chain_to_bot2, _build_reply
    bot2_link = await _auto_chain_to_bot2(client, link)

    if bot2_link:
        reply_text_str, reply_markup = _build_reply(link, bot2_link)
        await wait_msg.edit(
            reply_text_str,
            reply_markup=reply_markup,
            link_preview_options=NO_PREVIEW
        )
    else:
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")]
        ])
        await wait_msg.edit(
            f"<b>Here is your link</b>\n\n{link}",
            reply_markup=reply_markup,
            link_preview_options=NO_PREVIEW
        )

    if not client.disable_btn:
        await post_message.edit_reply_markup(reply_markup)


#===============================================================#

@Client.on_message(filters.channel & filters.incoming)
async def new_post(client: Client, message: Message):
    if not ui.is_filestore(client):
        raise ContinuePropagation
    if message.chat.id != client.db:
        return
    if client.disable_btn:
        return

    converted_id  = message.id * abs(client.db)
    string        = f"get-{converted_id}"
    base64_string = await encode(string)
    link          = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup  = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")]
    ])
    try:
        await message.edit_reply_markup(reply_markup)
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"new_post markup failed: {e}")
