from helper.helper_func import *
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import humanize
from config import MSG_EFFECT, OWNER_ID, START_PIC, START_MSG
from plugins.shortner import get_short
from helper.helper_func import get_messages, force_sub, decode, batch_auto_del_notification, delete_message, convert_time
from helper.styled_buttons import send_styled_photo, send_styled_message
import asyncio
import re

#===============================================================#
# BOT 2 (𝖶𝖺𝗇𝖽𝖺) helper — send the Bot 1 link and auto-delete
#===============================================================#

async def _send_bot2_link(client: Client, message: Message, bot1_link: str):
    """Send 'Download link : <bot1_link>' with auto-delete for Bot 2 (𝖶𝖺𝗇𝖽𝖺)."""
    auto_del = client.auto_del  # seconds (default 300)
    time_str = convert_time(auto_del)

    sent = await message.reply(
        f"<b>𝘋𝘰𝘸𝘯𝘭𝘰𝘢𝘥 𝘓𝘪𝘯𝘬 𝘪𝘴 𝘏𝘦𝘳𝘦 : \n <blockquote>{bot1_link}</blockquote>\n\n"
        f"<blockquote><b>⏳ 𝘛𝘩𝘪𝘴 𝘭𝘪𝘯𝘬 𝘸𝘪𝘭𝘭 𝘣𝘦 𝘢𝘶𝘵𝘰-𝘥𝘦𝘭𝘦𝘵𝘦𝘥 𝘪𝘯 {time_str}.</b></blockquote>",
        disable_web_page_preview=True
    )
    if auto_del > 0:
        asyncio.create_task(delete_message(sent, auto_del))

_send_sephra_link = _send_bot2_link  # Backward compatibility alias

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
    is_banned = await client.mongodb.is_banned(user_id)
    if is_banned:
        return await message.reply("**You have been banned from using this bot!**")

    text = message.text

    # ────────────────────────────────────────────────────────────
    # BOT 2 (𝖶𝖺𝗇𝖽𝖺) — deep-link handling
    # Decodes b64 token (or plain integer for backward compatibility)
    # ────────────────────────────────────────────────────────────
    if getattr(client, 'bot_type', 'bot1') in ('bot2', 'sephra') and len(text) > 7:
        msg_id = None
        try:
            token_str = text.split(" ", 1)[1].strip()
            if token_str.isdigit():
                msg_id = int(token_str)
            else:
                decoded_str = await decode(token_str)
                parts = decoded_str.split("-")
                if len(parts) == 2 and parts[0] == "get":
                    encoded_msg = int(parts[1])
                    msg_id = int(encoded_msg / abs(client.db))
                elif len(parts) == 1 and parts[0].isdigit():
                    msg_id = int(parts[0])

            if not msg_id:
                return await message.reply("⚠️ Invalid link.")
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Bot2 token parse error: {e}")
            return await message.reply("⚠️ Invalid link.")

        bot2_db_channel = client.db  # For Bot2, client.db IS the Bot2 DB channel
        try:
            fetched = await client.get_messages(chat_id=bot2_db_channel, message_ids=msg_id)
            if fetched and fetched.text:
                bot1_link = fetched.text.strip()
                return await _send_bot2_link(client, message, bot1_link)
            else:
                return await message.reply("⚠️ Link expired or not found. Please request a new one.")
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Bot2 link fetch error: {e}")
            return await message.reply("⚠️ Could not retrieve the link. It may have expired.")

    # ────────────────────────────────────────────────────────────
    # BOT 2 (𝖶𝖺𝗇𝖽𝖺) — normal /start (no deep-link)
    # ────────────────────────────────────────────────────────────
    if getattr(client, 'bot_type', 'bot1') in ('bot2', 'sephra') and len(text) <= 7:
        photo   = client.messages.get("START_PHOTO", START_PIC)
        caption = client.messages.get('START', START_MSG).format(
            first=message.from_user.first_name,
            last=message.from_user.last_name or "",
            username='@' + message.from_user.username if message.from_user.username else "N/A",
            mention=message.from_user.mention,
            id=message.from_user.id
        )
        buttons = [
            [
                {"text": "• ᴀʙᴏᴜᴛ", "callback_data": "about", "style": "primary"},
                {"text": "• ᴄʜᴀɴɴᴇʟs", "callback_data": "channels", "style": "danger"}
            ],
            [
                {"text": "• Close •", "callback_data": "close", "style": "danger"}
            ]
        ]
        if photo:
            await send_styled_photo(
                client=client,
                chat_id=message.chat.id,
                photo=photo,
                caption=caption,
                reply_markup=buttons
            )
        else:
            await send_styled_message(
                client=client,
                chat_id=message.chat.id,
                text=caption,
                reply_markup=buttons
            )
        return

    # ────────────────────────────────────────────────────────────
    # RIN BOT — deep-link handling (existing filestore logic)
    # ────────────────────────────────────────────────────────────
    if len(text) > 7:
        try:
            original_payload = text.split(" ", 1)[1]
            base64_string = original_payload

            is_short_link = False
            if base64_string.startswith("yu3elk"):
                base64_string = base64_string[6:-1]
                is_short_link = True

        except IndexError:
            return await message.reply("Invalid command format.")

        # 3. Check premium status
        is_user_pro = await client.mongodb.is_pro(user_id)

        # 4. Check if shortener is enabled
        shortner_enabled = getattr(client, 'shortner_enabled', True)

        # 5. If user is not premium AND shortener is enabled → show short URL
        if not is_user_pro and user_id != OWNER_ID and not is_short_link and shortner_enabled:
            try:
                short_link = get_short(f"https://t.me/{client.username}?start=yu3elk{base64_string}7", client)
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Shortener failed: {e}")
                return await message.reply("Couldn't generate short link.")

            short_photo   = client.messages.get("SHORT_PIC", "")
            short_caption = client.messages.get("SHORT_MSG", "")
            if short_caption:
                try:
                    short_caption = short_caption.format(
                        first=message.from_user.first_name,
                        last=message.from_user.last_name or "",
                        username='@' + message.from_user.username if message.from_user.username else "N/A",
                        mention=message.from_user.mention,
                        id=message.from_user.id
                    )
                except Exception:
                    pass
            tutorial_link = getattr(client, 'tutorial_link', "https://t.me/How_to_Download_7x/26")

            short_buttons = [
                [
                    {"text": "• ᴏᴘᴇɴ ʟɪɴᴋ", "url": short_link, "style": "primary"},
                    {"text": "ᴛᴜᴛᴏʀɪᴀʟ •", "url": tutorial_link, "style": "primary"}
                ],
                [
                    {"text": " • ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", "url": "https://t.me/Infinix_Adult/27", "style": "danger"}
                ]
            ]

            if short_photo:
                await send_styled_photo(
                    client=client,
                    chat_id=message.chat.id,
                    photo=short_photo,
                    caption=short_caption,
                    reply_markup=short_buttons
                )
            else:
                await send_styled_message(
                    client=client,
                    chat_id=message.chat.id,
                    text=short_caption,
                    reply_markup=short_buttons
                )
            return

        # 6. Decode and prepare file IDs
        try:
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

        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error decoding base64: {e}")
            return await message.reply("⚠️ Invalid or expired link.")

        # 7. Get messages from source channel
        temp_msg = await message.reply("⏳")
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
            await temp_msg.edit_text("Something went wrong!")
            client.LOGGER(__name__, client.name).warning(f"Error getting messages: {e}")
            return

        if not messages_list:
            return await temp_msg.edit("Couldn't find the files in the database.")
        await temp_msg.delete()

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
                await asyncio.sleep(e.x)
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    reply_markup=reply_markup,
                    protect_content=client.protect
                )
                yugen_msgs.append(copied_msg)
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Failed to send message: {e}")
                pass

        # 8. Auto-delete timer
        if messages_list and client.auto_del > 0:
            transfer_link = base64_string
            asyncio.create_task(batch_auto_del_notification(
                bot_username=client.username,
                messages=yugen_msgs,
                delay_time=client.auto_del,
                transfer_link=transfer_link,
                chat_id=message.from_user.id,
                client=client
            ))
        return

    # ────────────────────────────────────────────────────────────
    # 9. Normal start message (RIN bot, no deep-link)
    # ────────────────────────────────────────────────────────────
    else:
        if user_id in client.admins:
            buttons = [
                [
                    {"text": "• ᴀʙᴏᴜᴛ", "callback_data": "about", "style": "primary"},
                    {"text": "• ᴄʜᴀɴɴᴇʟs", "callback_data": "channels", "style": "danger"}
                ],
                [
                    {"text": "⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", "callback_data": "settings", "style": "success"},
                    {"text": "• Close •", "callback_data": "close", "style": "danger"}
                ]
            ]
        else:
            buttons = [
                [
                    {"text": "• ᴀʙᴏᴜᴛ", "callback_data": "about", "style": "primary"},
                    {"text": "• ᴄʜᴀɴɴᴇʟs", "callback_data": "channels", "style": "danger"}
                ],
                [
                    {"text": "• Close •", "callback_data": "close", "style": "danger"}
                ]
            ]

        photo          = client.messages.get("START_PHOTO", START_PIC)
        start_caption  = client.messages.get('START', START_MSG).format(
            first=message.from_user.first_name,
            last=message.from_user.last_name or "",
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        )

        if photo:
            await send_styled_photo(
                client=client,
                chat_id=message.chat.id,
                photo=photo,
                caption=start_caption,
                message_effect_id=MSG_EFFECT,
                reply_markup=buttons
            )
        else:
            await send_styled_message(
                client=client,
                chat_id=message.chat.id,
                text=start_caption,
                message_effect_id=MSG_EFFECT,
                reply_markup=buttons
            )
        return

#===============================================================#

@Client.on_message(filters.command('request') & filters.private)
async def request_command(client: Client, message: Message):
    if getattr(client, 'bot_type', 'bot1') not in ('bot1', 'rin'):
        return  # Only Bot 1 (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬) exposes this feature
    user_id  = message.from_user.id
    is_admin = user_id in client.admins

    if is_admin or user_id == OWNER_ID:
        await message.reply_text("🔹 **You are my sensei!**\nThis command is only for users.")
        return

    if not await client.mongodb.is_pro(user_id):
        reply_markup = [
            [{"text": "💎 Upgrade to Premium", "url": "https://t.me/Infinix_Adult/27", "style": "danger"}]
        ]
        await send_styled_message(
            client=client,
            chat_id=message.chat.id,
            text="❌ **You are not a premium user.**\nUpgrade to premium to access this feature.",
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
    if getattr(client, 'bot_type', 'bot1') not in ('bot1', 'rin'):
        return  # Only Bot 1 (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬) exposes premium plans
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
            "🔸 Request: Enabled\n\n"
            "🌟 You're a Premium User!"
        )
    else:
        await message.reply_text(
            "**👤 Profile Information:**\n\n"
            "🔸 Ads: Enabled\n"
            "🔸 Plan: Free\n"
            "🔸 Request: Disabled\n\n"
            "🔓 Unlock Premium to get more benefits\n"
            "Contact: @GetoPro"
        )
