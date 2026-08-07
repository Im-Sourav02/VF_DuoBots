from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import humanize

# ── Caption Helper ─────────────────────────────────────────────────────────

def format_custom_caption(template: str, file_name: str, file_size: int, orig_caption: str) -> str:
    """
    Replaces {file_name}, {size}, and {caption} in the template.
    Uses .replace() to safely preserve other HTML/Markdown syntax without KeyError.
    """
    if not template:
        return orig_caption or ""

    formatted_size = humanize.naturalsize(file_size) if file_size else "N/A"
    file_name_clean = file_name or "N/A"
    orig_caption_clean = orig_caption or ""

    res = template
    replacements = {
        "{file_name}": file_name_clean,
        "{filename}": file_name_clean,
        "{size}": formatted_size,
        "{file_size}": formatted_size,
        "{caption}": orig_caption_clean,
        "{original_caption}": orig_caption_clean,
    }
    for k, v in replacements.items():
        res = res.replace(k, v)

    return res

# ── Command: /set_caption ──────────────────────────────────────────────────

@Client.on_message(filters.private & filters.command(['set_caption', 'setcaption']))
async def set_caption_cmd(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    caption_text = None

    # Check if replied to a message
    if message.reply_to_message:
        reply = message.reply_to_message
        caption_text = reply.text.html if (reply.text and hasattr(reply.text, 'html')) else (reply.text or reply.caption.html if (reply.caption and hasattr(reply.caption, 'html')) else reply.caption)
    else:
        # Check command arguments
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            caption_text = parts[1]

    if not caption_text:
        help_text = (
            "<blockquote><b>📝 Cᴜsᴛᴏᴍ Cᴀᴘᴛɪᴏɴ Sᴇᴛᴛɪɴɢ</b></blockquote>\n\n"
            "<b>Yᴏᴜ ᴄᴀɴ sᴇᴛ ᴀ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ғᴏʀ ᴀʟʟ ғɪʟᴇs sᴇɴᴛ ʙʏ ᴛʜᴇ ʙᴏᴛ.</b>\n\n"
            "<b>Sᴜᴘᴘᴏʀᴛᴇᴅ Pᴀʀᴀᴍᴇᴛᴇʀs:</b>\n"
            "• <code>{file_name}</code> — Fɪʟᴇ ɴᴀᴍᴇ\n"
            "• <code>{size}</code> — Fɪʟᴇ sɪᴢᴇ (ᴇ.ɢ. 1.4 GB)\n"
            "• <code>{caption}</code> — Oʀɪɢɪɴᴀʟ ᴄᴀᴘᴛɪᴏɴ\n\n"
            "<b>Fᴏʀᴍᴀᴛᴛɪɴɢ Sᴜᴘᴘᴏʀᴛ:</b>\n"
            "• HTML: <code>&lt;b&gt;bold&lt;/b&gt;</code>, <code>&lt;i&gt;italic&lt;/i&gt;</code>, <code>&lt;code&gt;code&lt;/code&gt;</code>, <code>&lt;a href='...'&gt;link&lt;/a&gt;</code>\n"
            "• Markdown: <code>**bold**</code>, <code>__italic__</code>, <code>`code`</code>, <code>[link](url)</code>\n\n"
            "<b>Exᴀᴍᴘʟᴇ:</b>\n"
            "<code>/set_caption &lt;b&gt;📁 {file_name}&lt;/b&gt;\n\n📊 &lt;b&gt;Size:&lt;/b&gt; {size}\n\n&lt;a href='https://t.me/VeloraFilms'&gt;⚡ Jᴏɪɴ Oᴜʀ Cʜᴀɴɴᴇʟ&lt;/a&gt;</code>\n\n"
            "<i>Or reply to any formatted message with /set_caption</i>"
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Sᴇᴛ Cᴀᴘᴛɪᴏɴ Nᴏᴡ", callback_data="edit_caption_btn")],
            [InlineKeyboardButton("👁️ Vɪᴇᴡ Cᴜʀʀᴇɴᴛ Cᴀᴘᴛɪᴏɴ", callback_data="view_caption_btn")]
        ])
        return await message.reply(help_text, reply_markup=reply_markup, disable_web_page_preview=True)

    # Save caption to DB and memory
    await client.mongodb.set_caption(caption_text)
    client.custom_caption = caption_text
    client.messages["CUSTOM_CAPTION"] = caption_text

    # Show preview
    preview = format_custom_caption(caption_text, "Avengers.Endgame.2019.1080p.mkv", 2621440000, "Official HDRip")

    await message.reply(
        f"<b>✅ Cᴜsᴛᴏᴍ Cᴀᴘᴛɪᴏɴ Uᴘᴅᴀᴛᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n"
        f"<b>Rᴀᴡ Tᴇᴍᴘʟᴀᴛᴇ:</b>\n<pre>{caption_text}</pre>\n\n"
        f"<b>Pʀᴇᴠɪᴇᴡ:</b>\n{preview}",
        disable_web_page_preview=True
    )

# ── Command: /see_caption, /caption, /view_caption ─────────────────────────

@Client.on_message(filters.private & filters.command(['see_caption', 'seecaption', 'caption', 'view_caption', 'get_caption']))
async def see_caption_cmd(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    current = getattr(client, "custom_caption", "") or client.messages.get("CUSTOM_CAPTION", "")

    if not current:
        msg_text = (
            "<blockquote><b>📝 Cᴜsᴛᴏᴍ Cᴀᴘᴛɪᴏɴ Sᴛᴀᴛᴜs</b></blockquote>\n\n"
            "<b>Sᴛᴀᴛᴜs:</b> <i>No custom caption set (using default / original captions).</i>\n\n"
            "<b>Uꜱᴀɢᴇ:</b> <code>/set_caption &lt;your template&gt;</code>\n"
            "<b>Pᴀʀᴀᴍᴇᴛᴇʀꜱ:</b> <code>{file_name}</code>, <code>{size}</code>, <code>{caption}</code>"
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Sᴇᴛ Cᴀᴘᴛɪᴏɴ", callback_data="edit_caption_btn")],
            [InlineKeyboardButton("✕ Cʟᴏsᴇ", callback_data="close_caption_btn")]
        ])
        return await message.reply(msg_text, reply_markup=reply_markup)

    preview = format_custom_caption(current, "Avengers.Endgame.2019.1080p.mkv", 2621440000, "Official HDRip")

    msg_text = (
        f"<blockquote><b>📝 Cᴜʀʀᴇɴᴛ Cᴜsᴛᴏᴍ Cᴀᴘᴛɪᴏɴ</b></blockquote>\n\n"
        f"<b>Rᴀᴡ Tᴇᴍᴘʟᴀᴛᴇ:</b>\n<pre>{current}</pre>\n\n"
        f"<b>Lɪᴠᴇ Pʀᴇᴠɪᴇᴡ:</b>\n{preview}"
    )
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Eᴅɪᴛ Cᴀᴘᴛɪᴏɴ", callback_data="edit_caption_btn"), InlineKeyboardButton("🗑 Dᴇʟᴇᴛᴇ Cᴀᴘᴛɪᴏɴ", callback_data="del_caption_btn")],
        [InlineKeyboardButton("✕ Cʟᴏsᴇ", callback_data="close_caption_btn")]
    ])
    await message.reply(msg_text, reply_markup=reply_markup, disable_web_page_preview=True)

# ── Command: /del_caption ──────────────────────────────────────────────────

@Client.on_message(filters.private & filters.command(['del_caption', 'delcaption', 'rm_caption', 'rmcaption']))
async def del_caption_cmd(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    await client.mongodb.del_caption()
    client.custom_caption = ""
    client.messages["CUSTOM_CAPTION"] = ""

    await message.reply("<b>🗑 Cᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ʜᴀs ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ! Oʀɪɢɪɴᴀʟ ғɪʟᴇ ᴄᴀᴘᴛɪᴏɴs ᴡɪʟʟ ʙᴇ ᴜsᴇᴅ.</b>")

# ── Callback Handlers ──────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^view_caption_btn$"))
async def cb_view_caption(client: Client, query: CallbackQuery):
    if query.from_user.id not in client.admins:
        return await query.answer("Admins only.", show_alert=True)
    await query.answer()

    current = getattr(client, "custom_caption", "") or client.messages.get("CUSTOM_CAPTION", "")
    if not current:
        msg_text = (
            "<blockquote><b>📝 Cᴜsᴛᴏᴍ Cᴀᴘᴛɪᴏɴ Sᴛᴀᴛᴜs</b></blockquote>\n\n"
            "<b>Sᴛᴀᴛᴜs:</b> <i>No custom caption set.</i>\n\n"
            "<b>Uꜱᴀɢᴇ:</b> <code>/set_caption &lt;your template&gt;</code>\n"
            "<b>Pᴀʀᴀᴍᴇᴛᴇʀꜱ:</b> <code>{file_name}</code>, <code>{size}</code>, <code>{caption}</code>"
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Sᴇᴛ Cᴀᴘᴛɪᴏɴ", callback_data="edit_caption_btn")],
            [InlineKeyboardButton("✕ Cʟᴏsᴇ", callback_data="close_caption_btn")]
        ])
        return await query.message.edit_text(msg_text, reply_markup=reply_markup)

    preview = format_custom_caption(current, "Avengers.Endgame.2019.1080p.mkv", 2621440000, "Official HDRip")
    msg_text = (
        f"<blockquote><b>📝 Cᴜʀʀᴇɴᴛ Cᴜsᴛᴏᴍ Cᴀᴘᴛɪᴏɴ</b></blockquote>\n\n"
        f"<b>Rᴀᴡ Tᴇᴍᴘʟᴀᴛᴇ:</b>\n<pre>{current}</pre>\n\n"
        f"<b>Lɪᴠᴇ Pʀᴇᴠɪᴇᴡ:</b>\n{preview}"
    )
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Eᴅɪᴛ Cᴀᴘᴛɪᴏɴ", callback_data="edit_caption_btn"), InlineKeyboardButton("🗑 Dᴇʟᴇᴛᴇ Cᴀᴘᴛɪᴏɴ", callback_data="del_caption_btn")],
        [InlineKeyboardButton("✕ Cʟᴏsᴇ", callback_data="close_caption_btn")]
    ])
    await query.message.edit_text(msg_text, reply_markup=reply_markup, disable_web_page_preview=True)

@Client.on_callback_query(filters.regex("^edit_caption_btn$"))
async def cb_edit_caption(client: Client, query: CallbackQuery):
    if query.from_user.id not in client.admins:
        return await query.answer("Admins only.", show_alert=True)
    await query.answer()

    ask_msg = await client.ask(
        query.from_user.id,
        "<b>✏️ Sᴇɴᴅ ʏᴏᴜʀ ɴᴇᴡ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛᴇ ᴡɪᴛʜɪɴ 60 sᴇᴄᴏɴᴅs:</b>\n\n"
        "• Parameters: <code>{file_name}</code>, <code>{size}</code>, <code>{caption}</code>\n"
        "• Supports HTML & Markdown formatting.\n"
        "• Send <code>0</code> to cancel.",
        filters=filters.text,
        timeout=60
    )
    try:
        text = ask_msg.text
        if text.strip() == '0':
            return await ask_msg.reply("<b>❌ Cᴀᴘᴛɪᴏɴ ᴜᴘᴅᴀᴛᴇ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")

        await client.mongodb.set_caption(text)
        client.custom_caption = text
        client.messages["CUSTOM_CAPTION"] = text

        preview = format_custom_caption(text, "Avengers.Endgame.2019.1080p.mkv", 2621440000, "Official HDRip")
        await ask_msg.reply(
            f"<b>✅ Cᴜsᴛᴏᴍ Cᴀᴘᴛɪᴏɴ Uᴘᴅᴀᴛᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n"
            f"<b>Rᴀᴡ Tᴇᴍᴘʟᴀᴛᴇ:</b>\n<pre>{text}</pre>\n\n"
            f"<b>Pʀᴇᴠɪᴇᴡ:</b>\n{preview}",
            disable_web_page_preview=True
        )
    except Exception as e:
        client.LOGGER(__name__, client.name).error(f"Error setting custom caption via ask: {e}")

@Client.on_callback_query(filters.regex("^del_caption_btn$"))
async def cb_del_caption(client: Client, query: CallbackQuery):
    if query.from_user.id not in client.admins:
        return await query.answer("Admins only.", show_alert=True)
    await query.answer()

    await client.mongodb.del_caption()
    client.custom_caption = ""
    client.messages["CUSTOM_CAPTION"] = ""

    await query.message.edit_text("<b>🗑 Cᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ʜᴀs ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ! Oʀɪɢɪɴᴀʟ ғɪʟᴇ ᴄᴀᴘᴛɪᴏɴs ᴡɪʟʟ ʙᴇ ᴜsᴇᴅ.</b>")

@Client.on_callback_query(filters.regex("^close_caption_btn$"))
async def cb_close_caption(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass
