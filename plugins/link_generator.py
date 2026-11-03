from pyrogram import Client, filters, StopPropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.helper_func import encode, get_message_id, NO_PREVIEW
from helper import ui
from config import LOGGER, BOT1_DISPLAY_NAME, BOT2_DISPLAY_NAME

async def get_db_channels_info(client):
    """Get formatted database channels information with links"""
    db_channels = getattr(client, 'db_channels', {})
    primary_db  = getattr(client, 'primary_db_channel', client.db)

    if not db_channels:
        try:
            primary_chat = await client.get_chat(primary_db)
            if hasattr(primary_chat, 'invite_link') and primary_chat.invite_link:
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: <a href='{primary_chat.invite_link}'>{primary_chat.title}</a></blockquote>"
            else:
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: {primary_chat.title} (`{primary_db}`)</blockquote>"
        except:
            return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: `{primary_db}`</blockquote>"

    channels_info = ["<blockquote>✦ ᴀᴠᴀɪʟᴀʙʟᴇ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs:</blockquote>"]
    for channel_id_str, channel_data in db_channels.items():
        channel_name    = channel_data.get('name', 'ᴜɴᴋɴᴏᴡɴ')
        is_primary_text = "✦ ᴘʀɪᴍᴀʀʏ" if channel_data.get('is_primary', False) else "• sᴇᴄᴏɴᴅᴀʀʏ"
        try:
            chat = await client.get_chat(int(channel_id_str))
            if hasattr(chat, 'invite_link') and chat.invite_link:
                channels_info.append(f"{is_primary_text}: <a href='{chat.invite_link}'>{channel_name}</a>")
            else:
                channels_info.append(f"{is_primary_text}: {channel_name} (`{channel_id_str}`)")
        except:
            channels_info.append(f"{is_primary_text}: {channel_name} (`{channel_id_str}`)")

    return "\n".join(channels_info)


# ═══════════════════════════════════════════════════════════════
# AUTO-CHAIN: Store Bot 1 link in Bot 2 DB channel
# Returns bot2_link string, or None if Bot 2 not configured.
# ═══════════════════════════════════════════════════════════════

async def _auto_chain_to_bot2(client: Client, bot1_link: str) -> str | None:
    """
    Sends the Bot 1 link as a text message to BOT2_DB_CHANNEL.
    Encodes the message ID using standard base64 deep-link token.
    Returns the Bot 2 deep-link, or None if not configured.
    """
    bot2_db_channel   = getattr(client, 'bot2_db_channel', getattr(client, 'sephra_db_channel', 0))
    bot2_bot_username = getattr(client, 'bot2_bot_username', getattr(client, 'sephra_bot_username', ''))

    if not bot2_db_channel or not bot2_bot_username:
        return None  # Bot 2 not configured — skip auto-chain

    try:
        try:
            sent = await client.send_message(
                chat_id=bot2_db_channel,
                text=bot1_link,
                link_preview_options=NO_PREVIEW,
                disable_notification=True,
            )
        except TypeError:
            sent = await client.send_message(
                chat_id=bot2_db_channel,
                text=bot1_link,
                disable_notification=True,
            )
        converted_id = sent.id * abs(bot2_db_channel)
        string       = f"get-{converted_id}"
        b64_token    = await encode(string)
        bot2_link    = f"https://t.me/{bot2_bot_username}?start={b64_token}"
        client.LOGGER(__name__, client.name).info(
            f"Auto-chain: stored Bot1 link in Bot2 DB channel (msg_id={sent.id})"
        )
        return bot2_link
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Auto-chain to Bot2 failed: {type(e).__name__}: {e}")
        return None

_auto_chain_to_sephra = _auto_chain_to_bot2  # Backward compatibility alias


def _build_reply(bot1_link: str, bot2_link: str | None) -> tuple[str, InlineKeyboardMarkup]:
    """Build the reply text and keyboard for the admin."""
    if bot2_link:
        text = (
            f"<blockquote>✓ ʟɪɴᴋs ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ</blockquote>\n\n"
            f"<blockquote>🔒 <b>{BOT1_DISPLAY_NAME} Link</b> (internal — do not share directly):</blockquote>\n"
            f"<code>{bot1_link}</code>\n\n"
            f"<blockquote>📥 <b>{BOT2_DISPLAY_NAME} Link</b> (use this in channel posts):</blockquote>\n"
            f"<code>{bot2_link}</code>"
        )
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🔁 Share {BOT1_DISPLAY_NAME} URL", url=f"https://telegram.me/share/url?url={bot1_link}"),
                InlineKeyboardButton(f"📥 Share {BOT2_DISPLAY_NAME} URL", url=f"https://telegram.me/share/url?url={bot2_link}"),
            ]
        ])
    else:
        text = f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ</blockquote>\n\n<code>{bot1_link}</code>"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f"https://telegram.me/share/url?url={bot1_link}")]
        ])
    return text, reply_markup


async def _send_link_result(client: Client, user_id: int, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        await client.send_message(
            user_id,
            text,
            reply_markup=reply_markup,
            link_preview_options=NO_PREVIEW,
        )
    except TypeError:
        await client.send_message(user_id, text, reply_markup=reply_markup)


#===============================================================#
# /batch
#===============================================================#

@Client.on_message(filters.private & filters.command('batch'))
async def batch(client: Client, message: Message):
    if not ui.is_filestore(client):
        raise StopPropagation
    if message.from_user.id not in client.admins:
        await message.reply(client.reply_text)
        raise StopPropagation

    db_channels_info = await get_db_channels_info(client)

    while True:
        try:
            first_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ꜰɪʀsᴛ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>
{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                user_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        f_msg_id, source_channel_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply(
                "<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ"
            )
            continue

    while True:
        try:
            second_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ʟᴀsᴛ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>
{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                user_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        s_msg_id, _ = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply(
                "<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ"
            )
            continue

    client.LOGGER(__name__, client.name).info(
        f"Generating batch link with source channel: {source_channel_id}, "
        f"first_msg: {f_msg_id}, last_msg: {s_msg_id}"
    )
    string        = f"get-{f_msg_id * abs(source_channel_id)}-{s_msg_id * abs(source_channel_id)}"
    base64_string = await encode(string)
    bot1_link     = f"https://t.me/{client.username}?start={base64_string}"

    bot2_link = await _auto_chain_to_bot2(client, bot1_link)
    reply_text, reply_markup = _build_reply(bot1_link, bot2_link)
    await _send_link_result(client, message.from_user.id, reply_text, reply_markup)
    raise StopPropagation

#===============================================================#
# /genlink
#===============================================================#

@Client.on_message(filters.private & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    if not ui.is_filestore(client):
        raise StopPropagation
    if message.from_user.id not in client.admins:
        await message.reply(client.reply_text)
        raise StopPropagation

    db_channels_info = await get_db_channels_info(client)

    while True:
        try:
            channel_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>

{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                user_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        msg_id, source_channel_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        else:
            await channel_message.reply(
                "<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ"
            )
            continue

    base64_string = await encode(f"get-{msg_id * abs(source_channel_id)}")
    bot1_link     = f"https://t.me/{client.username}?start={base64_string}"

    bot2_link = await _auto_chain_to_bot2(client, bot1_link)
    reply_text, reply_markup = _build_reply(bot1_link, bot2_link)
    await _send_link_result(client, message.from_user.id, reply_text, reply_markup)
    raise StopPropagation

#===============================================================#
# /nbatch
#===============================================================#

@Client.on_message(filters.private & filters.command("nbatch"))
async def nbatch(client: Client, message: Message):
    if not ui.is_filestore(client):
        raise StopPropagation
    if message.from_user.id not in client.admins:
        await message.reply(client.reply_text)
        raise StopPropagation

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("<blockquote>✗ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ!</blockquote> ᴜsᴇ: /nbatch {number}")
        return

    batch_size       = int(args[1])
    db_channels_info = await get_db_channels_info(client)

    while True:
        try:
            first_message = await client.ask(
                text=f"""<blockquote>🚀 sᴇɴᴅ ᴅʙ ᴄʜᴀɴɴᴇʟ ꜰɪʀsᴛ ᴍᴇssᴀɢᴇ ʟɪɴᴋ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)...</blockquote>

{db_channels_info}""",
                chat_id=message.from_user.id,
                user_id=message.from_user.id,
                filters=(filters.text & ~filters.forwarded),
                timeout=60
            )
        except:
            return

        f_msg_id, source_channel_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply(
                "<blockquote>😫 ɪɴᴠᴀʟɪᴅ!</blockquote> sᴇɴᴅ ᴄᴏʀʀᴇᴄᴛ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴍᴇssᴀɢᴇ ʟɪɴᴋ."
            )
            continue

    s_msg_id      = f_msg_id + batch_size - 1
    string        = f"get-{f_msg_id * abs(source_channel_id)}-{s_msg_id * abs(source_channel_id)}"
    base64_string = await encode(string)
    bot1_link     = f"https://t.me/{client.username}?start={base64_string}"

    bot2_link = await _auto_chain_to_bot2(client, bot1_link)
    reply_text, reply_markup = _build_reply(bot1_link, bot2_link)
    await _send_link_result(client, message.from_user.id, reply_text, reply_markup)
    raise StopPropagation
