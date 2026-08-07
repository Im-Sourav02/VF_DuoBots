import asyncio
from pyrogram import filters, Client, ContinuePropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from helper.helper_func import encode
import re

#===============================================================#
# channel_post — Only active on Bot 1 (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬)
# Bot 2 and other bots pass control to next handler.
#===============================================================#

is_command = filters.create(
    lambda _, __, m: bool(
        (m.text and m.text.strip().startswith(('/', '!'))) or
        (m.caption and m.caption.strip().startswith(('/', '!')))
    )
)

@Client.on_message(filters.private & ~is_command)
async def channel_post(client: Client, message: Message):
    # Bot 2 — pass control to the next matching handler
    if getattr(client, 'bot_type', 'bot1') not in ('bot1', 'rin'):
        raise ContinuePropagation

    # Double check to never catch commands
    if (message.text and message.text.strip().startswith(('/', '!'))) or \
       (message.caption and message.caption.strip().startswith(('/', '!'))):
        raise ContinuePropagation

    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    reply_text = await message.reply_text("Please Wait...!", quote=True)
    try:
        post_message = await message.copy(chat_id=client.db, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await message.copy(chat_id=client.db, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("Something went Wrong..!")
        return

    converted_id  = post_message.id * abs(client.db)
    string        = f"get-{converted_id}"
    base64_string = await encode(string)
    link          = f"https://t.me/{client.username}?start={base64_string}"

    # Auto-chain to Bot 2 (Bot 1 only)
    bot2_link = None
    if getattr(client, 'bot_type', 'bot1') in ('bot1', 'rin'):
        from plugins.link_generator import _auto_chain_to_bot2, _build_reply
        bot2_link = await _auto_chain_to_bot2(client, link)

    if bot2_link:
        reply_text_str, reply_markup = _build_reply(link, bot2_link)
        await reply_text.edit(
            reply_text_str,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    else:
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")]
        ])
        await reply_text.edit(
            f"<b>Here is your link</b>\n\n{link}",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

    if not client.disable_btn:
        await post_message.edit_reply_markup(reply_markup)

#===============================================================#

@Client.on_message(filters.channel & filters.incoming)
async def new_post(client: Client, message: Message):
    # Only Bot 1 watches its DB channel for incoming posts
    if getattr(client, 'bot_type', 'bot1') not in ('bot1', 'rin'):
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
        print(e)
        pass
