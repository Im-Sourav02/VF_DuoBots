import asyncio
import re

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from config import (
    MSG_EFFECT, OWNER_ID, PREMIUM_LINK,
    CREDITS_PER_ACCESS, CREDITS_PER_BYPASS, VERIFY_TOKEN_TTL, VERIFY_MIN_SECONDS,
)
from plugins.shortner import shorten_verification_link
from helper.helper_func import (
    get_messages, force_sub, decode, batch_auto_del_notification, delete_message, convert_time,
)
from helper.styled_buttons import send_styled_message
from helper import ui

# Deep-link payloads handled by 𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 (the credits bot):
#   <base64 "get-…">   file / batch link (unchanged format)
#   v_<token>          return from the shortener; token is random, single-use, per user + link
#   yu3elk<base64>7    legacy "already shortened" marker; now treated as a plain file link
VERIFY_PREFIX = "v_"
LEGACY_SHORT_PREFIX = "yu3elk"
LEGACY_SHORT_SUFFIX = "7"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

UNAVAILABLE = "⚠️ <b>ғɪʟᴇ ᴀᴄᴄᴇss ɪs ᴛᴇᴍᴘᴏʀᴀʀɪʟʏ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ.</b> ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ɪɴ ᴀ ғᴇᴡ ᴍɪɴᴜᴛᴇs."
_VERIFY_ERRORS = {
    "invalid": "⚠️ <b>ɪɴᴠᴀʟɪᴅ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.</b>",
    "expired": "⌛ <b>ᴛʜɪs ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ ʜᴀs ᴇxᴘɪʀᴇᴅ.</b> ᴏᴘᴇɴ ʏᴏᴜʀ ғɪʟᴇ ʟɪɴᴋ ᴀɢᴀɪɴ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.",
    "used": "✓ <b>ᴛʜɪs ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ ᴡᴀs ᴀʟʀᴇᴀᴅʏ ᴜsᴇᴅ.</b> ᴏᴘᴇɴ ʏᴏᴜʀ ғɪʟᴇ ʟɪɴᴋ ᴀɢᴀɪɴ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.",
    "too_fast": "⏳ <b>ᴘʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴛʜᴇ sʜᴏʀᴛᴇɴᴇʀ sᴛᴇᴘs</b>, ᴛʜᴇɴ ᴏᴘᴇɴ ᴛʜᴇ ʟɪɴᴋ ᴀɢᴀɪɴ.",
}

#===============================================================#
# BOT 2 (𝖶𝖺𝗇𝖽𝖺) — send the Bot 1 link and auto-delete
#===============================================================#

async def _send_bot2_link(client: Client, message: Message, bot1_link: str):
    """Send the stored 𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 link with auto-delete (𝖶𝖺𝗇𝖽𝖺)."""
    auto_del = client.auto_del
    screen = ui.link_screen(client, message.from_user, bot1_link, convert_time(auto_del))
    sent = await ui.send_screen(client, message.chat.id, screen)
    if sent and auto_del > 0:
        asyncio.create_task(delete_message(sent, auto_del))

_send_sephra_link = _send_bot2_link  # Backward compatibility alias


async def _open_bot2_link(client: Client, message: Message, token_str: str):
    """Decode a 𝖶𝖺𝗇𝖽𝖺 deep link (b64 token, or plain integer for backward compatibility)."""
    msg_id = None
    try:
        if token_str.isdigit():
            msg_id = int(token_str)
        else:
            decoded_str = await decode(token_str)
            parts = decoded_str.split("-")
            if len(parts) == 2 and parts[0] == "get":
                msg_id = int(int(parts[1]) / abs(client.db))
            elif len(parts) == 1 and parts[0].isdigit():
                msg_id = int(parts[0])
        if not msg_id:
            return await message.reply("⚠️ Invalid link.")
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Bot2 token parse error: {e}")
        return await message.reply("⚠️ Invalid link.")

    try:
        fetched = await client.get_messages(chat_id=client.db, message_ids=msg_id)
        if fetched and fetched.text:
            return await _send_bot2_link(client, message, fetched.text.strip())
        return await message.reply("⚠️ Link expired or not found. Please request a new one.")
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Bot2 link fetch error: {e}")
        return await message.reply("⚠️ Could not retrieve the link. It may have expired.")

#===============================================================#
# START COMMAND
#===============================================================#

@Client.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # 1. Add user if not present
    present = await client.mongodb.present_user(user_id)
    if not present:
        try:
            await client.mongodb.add_user(user_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error adding a user:\n{e}")

    # 2. Check if banned
    if await client.mongodb.is_banned(user_id):
        return await message.reply("**You have been banned from using this bot!**")

    parts = message.text.split(" ", 1)
    payload = parts[1].strip() if len(parts) > 1 else ""

    if ui.is_link_bot(client):
        if payload:
            return await _open_bot2_link(client, message, payload)
        return await _send_home(client, message)

    if payload.startswith(VERIFY_PREFIX):
        return await _redeem_verification(client, message, payload[len(VERIFY_PREFIX):])
    if payload:
        return await _open_file_link(client, message, payload)
    return await _send_home(client, message)


async def _send_home(client: Client, message: Message):
    screen = await ui.home_screen(client, message.from_user)
    effect = None if ui.is_link_bot(client) else MSG_EFFECT
    await ui.send_screen(client, message.chat.id, screen, message_effect_id=effect)

#===============================================================#
# 𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 — file access with credits
#
#   A. Open file link:  premium / owner / shortener off -> deliver free (no credits earned or spent).
#                       Otherwise spend CREDITS_PER_ACCESS atomically; deliver only if that succeeded.
#                       Insufficient balance -> verification screen with a one-time shortened token link.
#   B. Return via v_<token>: claim the token atomically (owner, unexpired, unused), award
#                       CREDITS_PER_BYPASS once per token, show "Click Here" -> back to step A.
#   Any database error stops the flow before delivery.
#===============================================================#

async def _requires_credit(client: Client, user_id: int) -> bool:
    if user_id == OWNER_ID or not getattr(client, 'shortner_enabled', True):
        return False
    return not await client.mongodb.is_pro(user_id)


async def _open_file_link(client: Client, message: Message, payload: str):
    user_id = message.from_user.id

    if payload.startswith(LEGACY_SHORT_PREFIX) and payload.endswith(LEGACY_SHORT_SUFFIX) and len(payload) > 7:
        payload = payload[len(LEGACY_SHORT_PREFIX):-len(LEGACY_SHORT_SUFFIX)]

    try:
        source_channel_id, ids = await _resolve_file_ids(client, payload)
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Error decoding base64: {e}")
        return await message.reply("⚠️ Invalid or expired link.")

    try:
        needs_credit = await _requires_credit(client, user_id)
    except Exception as e:
        client.LOGGER(__name__, client.name).error(f"Access check failed: {type(e).__name__}: {e}")
        return await message.reply(UNAVAILABLE)
    if needs_credit and not ui.is_credits_bot(client):
        return await message.reply("⚠️ This link can only be opened with Premium on this bot.")

    temp_msg = await message.reply("⏳")
    messages_list = await _fetch_messages(client, source_channel_id, ids)
    if messages_list is None:
        return await temp_msg.edit_text("Something went wrong!")
    if not messages_list:
        return await temp_msg.edit("Couldn't find the files in the database.")

    balance = None
    if needs_credit:
        try:
            balance = await client.mongodb.spend_credit(user_id, CREDITS_PER_ACCESS)
        except Exception as e:
            client.LOGGER(__name__, client.name).error(f"Credit spend failed: {type(e).__name__}: {e}")
            return await temp_msg.edit_text(UNAVAILABLE)
        if balance is None:
            await temp_msg.delete()
            return await _show_verification(client, message, payload)
    await temp_msg.delete()

    delivered = await _deliver(client, message, messages_list)

    if needs_credit:
        if not delivered:
            try:
                await client.mongodb.refund_credit(user_id, CREDITS_PER_ACCESS)
                balance += CREDITS_PER_ACCESS
            except Exception as e:
                client.LOGGER(__name__, client.name).error(f"Credit refund failed for {user_id}: {type(e).__name__}")
        else:
            note = await message.reply(
                f"<blockquote>◍ <b>{CREDITS_PER_ACCESS} ᴄʀᴇᴅɪᴛ ᴜsᴇᴅ</b> — ʙᴀʟᴀɴᴄᴇ: <b>{balance} ᴄʀᴇᴅɪᴛs</b></blockquote>"
            )
            if client.auto_del > 0:
                asyncio.create_task(delete_message(note, client.auto_del))

    if delivered and client.auto_del > 0:
        asyncio.create_task(batch_auto_del_notification(
            bot_username=client.username,
            messages=delivered,
            delay_time=client.auto_del,
            transfer_link=payload,
            chat_id=user_id,
            client=client
        ))


async def _show_verification(client: Client, message: Message, payload: str):
    if not ui.is_credits_bot(client):
        return await message.reply("⚠️ This link can only be opened with Premium on this bot.")
    user = message.from_user
    try:
        balance = await client.mongodb.get_credits(user.id)
        token_doc = await client.mongodb.find_open_verify_token(user.id, payload, min(300, VERIFY_TOKEN_TTL // 2))
        short_link = token_doc["short_link"] if token_doc else None
        if not short_link:
            token_doc = await client.mongodb.create_verify_token(user.id, payload, VERIFY_TOKEN_TTL)
            verify_url = f"https://t.me/{client.username}?start={VERIFY_PREFIX}{token_doc['_id']}"
            short_link = await shorten_verification_link(verify_url, client)
            if not short_link:
                await client.mongodb.discard_verify_token(token_doc["_id"])
                return await message.reply("⚠️ Couldn't generate your verification link right now. Please try again shortly.")
            await client.mongodb.set_verify_short_link(token_doc["_id"], short_link)
    except Exception as e:
        client.LOGGER(__name__, client.name).error(f"Verification setup failed: {type(e).__name__}: {e}")
        return await message.reply(UNAVAILABLE)
    await ui.send_screen(client, message.chat.id, ui.verify_screen(client, user, short_link, balance))


async def _redeem_verification(client: Client, message: Message, token: str):
    user = message.from_user
    if not ui.is_credits_bot(client) or not _TOKEN_RE.match(token):
        return await message.reply(_VERIFY_ERRORS["invalid"])
    try:
        status, doc = await client.mongodb.claim_verify_token(token, user.id, VERIFY_MIN_SECONDS)
        if status != "claimed":
            return await message.reply(_VERIFY_ERRORS[status])
        file_link = f"https://t.me/{client.username}?start={doc['payload']}"

        if user.id == OWNER_ID or await client.mongodb.is_pro(user.id):
            await client.mongodb.mark_verify_token_rewarded(token)
            return await send_styled_message(
                client=client,
                chat_id=message.chat.id,
                text=ui.PREMIUM_PANEL + "\n<blockquote>◍ ɴᴏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ɴᴇᴇᴅᴇᴅ — ᴛᴀᴘ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴏᴘᴇɴ ʏᴏᴜʀ ғɪʟᴇs.</blockquote>",
                reply_markup=ui.layout([ui.button("CLICK HERE", url=file_link)], [ui.close_button()]),
            )

        # Idempotent: a retry after an interrupted first attempt will not add credits again,
        # but still shows the verified screen so the user can open the file link.
        await client.mongodb.award_credits_once(user.id, token, CREDITS_PER_BYPASS)
        await client.mongodb.mark_verify_token_rewarded(token)
        balance = await client.mongodb.get_credits(user.id)
    except Exception as e:
        client.LOGGER(__name__, client.name).error(f"Verification redeem failed: {type(e).__name__}: {e}")
        return await message.reply(UNAVAILABLE)

    await ui.send_screen(client, message.chat.id, ui.verified_screen(client, user, file_link, balance))

#===============================================================#
# File decoding / fetching / delivery (shared by every access path)
#===============================================================#

async def _resolve_file_ids(client: Client, base64_string: str):
    """Decode a file/batch payload into (source_channel_id, message ids). Raises on malformed input."""
    string   = await decode(base64_string)
    argument = string.split("-")
    ids      = []
    source_channel_id = None

    if len(argument) == 3:
        encoded_start = int(argument[1])
        encoded_end   = int(argument[2])

        primary_multiplier = abs(client.db)
        start_primary = int(encoded_start / primary_multiplier)
        end_primary   = int(encoded_end   / primary_multiplier)

        if encoded_start % primary_multiplier == 0 and encoded_end % primary_multiplier == 0:
            source_channel_id = client.db
            start = start_primary
            end   = end_primary
            client.LOGGER(__name__, client.name).info(
                f"Decoded batch from primary channel {source_channel_id}: {start}-{end}")
        else:
            db_channels = getattr(client, 'db_channels', {})
            for channel_id_str in db_channels.keys():
                channel_id = int(channel_id_str)
                channel_multiplier = abs(channel_id)
                start_test = int(encoded_start / channel_multiplier)
                end_test   = int(encoded_end   / channel_multiplier)
                if encoded_start % channel_multiplier == 0 and encoded_end % channel_multiplier == 0:
                    source_channel_id = channel_id
                    start = start_test
                    end   = end_test
                    client.LOGGER(__name__, client.name).info(
                        f"Decoded batch from secondary channel {source_channel_id}: {start}-{end}")
                    break
            if source_channel_id is None:
                source_channel_id = client.db
                start = start_primary
                end   = end_primary

        ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))

    elif len(argument) == 2:
        encoded_msg = int(argument[1])
        if hasattr(client, 'db_channel') and client.db_channel:
            primary_multiplier = abs(client.db_channel.id)
            msg_id_primary = int(encoded_msg / primary_multiplier)
            if encoded_msg % primary_multiplier == 0:
                source_channel_id = client.db_channel.id
                ids = [msg_id_primary]
            else:
                db_channels = getattr(client, 'db_channels', {})
                for channel_id_str in db_channels.keys():
                    channel_id = int(channel_id_str)
                    channel_multiplier = abs(channel_id)
                    msg_id_test = int(encoded_msg / channel_multiplier)
                    if encoded_msg % channel_multiplier == 0:
                        source_channel_id = channel_id
                        ids = [msg_id_test]
                        break
                if source_channel_id is None:
                    source_channel_id = client.db_channel.id if hasattr(client, 'db_channel') else client.db
                    ids = [msg_id_primary]
        else:
            source_channel_id = client.db
            ids = [int(encoded_msg / abs(client.db))]
    else:
        raise ValueError("unrecognised payload")

    return source_channel_id, ids


async def _fetch_messages(client: Client, source_channel_id, ids) -> list | None:
    """Messages for ids (None on unexpected failure)."""
    messages_list = []
    try:
        if source_channel_id:
            client.LOGGER(__name__, client.name).info(
                f"Trying to get messages from source channel: {source_channel_id}")
            try:
                msgs = await client.get_messages(chat_id=source_channel_id, message_ids=list(ids))
                valid_msgs = [msg for msg in msgs if msg is not None]
                messages_list.extend(valid_msgs)
                client.LOGGER(__name__, client.name).info(
                    f"Found {len(valid_msgs)} messages from source channel {source_channel_id}")
                if len(valid_msgs) < len(list(ids)):
                    missing_ids = [mid for mid in ids if mid not in {msg.id for msg in valid_msgs}]
                    if missing_ids:
                        additional_messages = await get_messages(client, missing_ids)
                        messages_list.extend(additional_messages)
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(
                    f"Error getting messages from source channel {source_channel_id}: {e}")
                messages_list = await get_messages(client, ids)
        else:
            messages_list = await get_messages(client, ids)
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Error getting messages: {e}")
        return None
    return messages_list


async def _deliver(client: Client, message: Message, messages_list: list) -> list:
    """Copy files to the user with caption/watermark rules. Returns the messages actually sent."""
    yugen_msgs = []
    for msg in messages_list:
        media = msg.document or msg.video or msg.audio or msg.photo or msg.animation or msg.voice
        file_name = getattr(media, "file_name", None) or ""
        file_size = getattr(media, "file_size", 0) or 0
        orig_caption = msg.caption.html if (msg.caption and hasattr(msg.caption, "html")) else (msg.caption or "")

        custom_caption = getattr(client, "custom_caption", "") or client.messages.get("CUSTOM_CAPTION", "")

        if custom_caption:
            from plugins.caption import format_custom_caption
            caption = format_custom_caption(custom_caption, file_name, file_size, orig_caption)
        elif getattr(client, 'auto_watermark', True):
            if msg.video or (msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/")):
                quality = ""
                match = re.search(r"(144p|240p|360p|480p|720p|1080p|1440p|2160p|4k)", file_name, re.IGNORECASE)
                if match:
                    quality = match.group(1).lower()
                elif msg.video and getattr(msg.video, "height", None):
                    quality = f"{msg.video.height}p"

                if quality:
                    caption = f'<a href="https://t.me/Infinix_Adult/24"><b>{quality} • ʙʏ ɪɴꜰɪɴɪx ᴀᴅᴜʟᴛ</b></a>'
                else:
                    caption = '<a href="https://t.me/Infinix_Adult/24"><b>ʙʏ ɪɴꜰɪɴɪx ᴀᴅᴜʟᴛ</b></a>'
            elif msg.document or msg.photo:
                caption = '<a href="https://t.me/Infinix_Adult/24"><b>ʙʏ ɪɴꜰɪɴɪx ᴀᴅᴜʟᴛ</b></a>'
            else:
                caption = ""
        else:
            caption = orig_caption
        reply_markup = msg.reply_markup if not client.disable_btn else None

        try:
            copied_msg = await msg.copy(
                chat_id=message.from_user.id,
                caption=caption,
                reply_markup=reply_markup,
                protect_content=client.protect
            )
            yugen_msgs.append(copied_msg)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    reply_markup=reply_markup,
                    protect_content=client.protect
                )
                yugen_msgs.append(copied_msg)
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Failed to send message after FloodWait: {e}")
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Failed to send message: {e}")
    return yugen_msgs

#===============================================================#

@Client.on_message(filters.command('request') & filters.private)
async def request_command(client: Client, message: Message):
    if ui.is_link_bot(client):
        return  # Only 𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 exposes this feature
    user_id  = message.from_user.id
    is_admin = user_id in client.admins

    if is_admin or user_id == OWNER_ID:
        await message.reply_text("🔹 **You are my sensei!**\nThis command is only for users.")
        return

    if not await client.mongodb.is_pro(user_id):
        reply_markup = ui.layout(
            [ui.button("BUY PREMIUM", url=PREMIUM_LINK, style="success")],
            [ui.button("PREMIUM PLANS", "premium")],
        )
        await send_styled_message(
            client=client,
            chat_id=message.chat.id,
            text="❌ <b>You are not a premium user.</b>\nUpgrade to premium to access this feature.",
            reply_markup=reply_markup
        )
        return

    if len(message.command) < 2:
        await message.reply("⚠️ **Send me your request in this format:**\n`/request Your_Request_Here`")
        return

    requested     = " ".join(message.command[1:])
    owner_message = (
        f"📩 **New Request from {message.from_user.mention}**\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📝 Request: `{requested}`"
    )
    await client.send_message(OWNER_ID, owner_message)
    await message.reply("✅ **Thanks for your request!**\nYour request will be reviewed soon. Please wait.")

#===============================================================#

@Client.on_message(filters.command('profile') & filters.private)
async def my_plan(client: Client, message: Message):
    if ui.is_link_bot(client):
        return  # Only 𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 exposes premium plans
    user_id  = message.from_user.id
    is_admin = user_id in client.admins

    if is_admin or user_id == OWNER_ID:
        await message.reply_text("🔹 You're my sensei! This command is only for users.")
        return

    is_user_premium = await client.mongodb.is_pro(user_id)

    if is_user_premium:
        await message.reply_text(
            "**👤 Profile Information:**\n\n"
            "🔸 Ads: Disabled\n"
            "🔸 Plan: Premium\n"
            "🔸 Credits: Not used (Premium)\n"
            "🔸 Request: Enabled\n\n"
            "🌟 You're a Premium User!"
        )
    else:
        credits_line = ""
        if ui.is_credits_bot(client):
            try:
                credits_line = f"🔸 Credits: {await client.mongodb.get_credits(user_id)}\n"
            except Exception:
                credits_line = "🔸 Credits: unavailable right now\n"
        await message.reply_text(
            "**👤 Profile Information:**\n\n"
            "🔸 Ads: Enabled\n"
            "🔸 Plan: Free\n"
            f"{credits_line}"
            "🔸 Request: Disabled\n\n"
            "🔓 Unlock Premium to get more benefits\n"
            "Contact: @GetoPro"
        )
