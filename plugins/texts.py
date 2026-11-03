from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

#===============================================================#

async def texts(client, query):
    custom_cap = getattr(client, 'custom_caption', '') or client.messages.get('CUSTOM_CAPTION', '')
    cap_display = custom_cap if custom_cap else 'None (Original/Default)'
    msg = f"""<blockquote>**Text Configuration:**</blockquote>
**Start Message:**
<pre>{client.messages.get('START', 'Empty')}</pre>
**Force Sub Message:**
<pre>{client.messages.get('FSUB', 'Empty')}</pre>
**About Message:**
<pre>{client.messages.get('ABOUT', 'Empty')}</pre>
**Reply Message:**
<pre>{client.reply_text}</pre>
**Custom Caption:**
<pre>{cap_display}</pre>
    """
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('ꜱᴛᴀʀᴛ ᴛᴇxᴛ', callback_data='start_txt'), InlineKeyboardButton('ꜰꜱᴜʙ ᴛᴇxᴛ', callback_data='fsub_txt')],
        [InlineKeyboardButton('ʀᴇᴘʟʏ ᴛᴇxᴛ', callback_data='reply_txt'), InlineKeyboardButton('ᴀʙᴏᴜᴛ ᴛᴇxᴛ', callback_data='about_txt')],
        [InlineKeyboardButton('📝 ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ', callback_data='custom_caption_txt')],
        [InlineKeyboardButton('◂ ʙᴀᴄᴋ', callback_data='settings')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex("^custom_caption_txt$"))
async def custom_caption_txt(client: Client, query: CallbackQuery):
    await query.answer()
    ask_text = await client.ask(
        query.from_user.id,
        "<b>✏️ Send new custom caption template in the next 60 seconds:</b>\n\n"
        "• Parameters: <code>{file_name}</code>, <code>{size}</code>, <code>{caption}</code>\n"
        "• Supports HTML and Markdown formatting.\n"
        "• Send <code>0</code> to cancel or <code>del</code> to remove custom caption!",
        filters=filters.text,
        timeout=60
    )
    try:
        text = ask_text.text.strip()
        if text == '0':
            return await ask_text.reply("__Custom caption has not changed!__")
        if text.lower() in ('del', 'delete', 'remove', 'none'):
            await client.mongodb.del_caption()
            client.custom_caption = ""
            client.messages["CUSTOM_CAPTION"] = ""
            await texts(client, query)
            return await ask_text.reply("<b>🗑 Custom caption has been removed!</b>")

        await client.mongodb.set_caption(text)
        client.custom_caption = text
        client.messages["CUSTOM_CAPTION"] = text
        await texts(client, query)
        return await ask_text.reply("<b>✅ Custom caption has been changed!</b>")
    except Exception as e:
        return client.LOGGER(__name__, client.name).error(e)

#===============================================================#

@Client.on_callback_query(filters.regex("^start_txt$"))
async def start_txt(client: Client, query: CallbackQuery):
    await query.answer()
    ask_text = await client.ask(query.from_user.id, "Send new start text message in the next 60 seconds, send `0` to cancel or wait 60 seconds!\n\n__Note you can use both markdown and html formatting!__", filters=filters.text, timeout=60)
    try:
        text = ask_text.text
        if text == '0':
            return await ask_text.reply("__Start text has not changed!__")
        client.messages['START'] = text
        await texts(client, query)
        return await ask_text.reply("__Start text has been changed!__")
    except Exception as e:
        return client.LOGGER(__name__, client.name).error(e)

#===============================================================#

@Client.on_callback_query(filters.regex("^fsub_txt$"))
async def force_txt(client: Client, query: CallbackQuery):
    await query.answer()
    ask_text = await client.ask(query.from_user.id, "Send new force sub text message in the next 60 seconds, send `0` to cancel or wait 60 seconds!\n\n__Note you can use both markdown and html formatting!__", filters=filters.text, timeout=60)
    try:
        text = ask_text.text
        if text == '0':
            return await ask_text.reply("__Force Sub text has not changed!__")
        client.messages['FSUB'] = text
        await texts(client, query)
        return await ask_text.reply("__Force Sub text has been changed!__")
    except Exception as e:
        return client.LOGGER(__name__, client.name).error(e)

#===============================================================#

@Client.on_callback_query(filters.regex("^about_txt$"))
async def about_txt(client: Client, query: CallbackQuery):
    await query.answer()
    ask_text = await client.ask(query.from_user.id, "Send new about text message in the next 60 seconds, send `0` to cancel or wait 60 seconds!\n\n__Note you can use both markdown and html formatting!__", filters=filters.text, timeout=60)
    try:
        text = ask_text.text
        if text == '0':
            return await ask_text.reply("__About text has not changed!__")
        client.messages['ABOUT'] = text
        await texts(client, query)
        return await ask_text.reply("__About text has been changed!__")
    except Exception as e:
        return client.LOGGER(__name__, client.name).error(e)

#===============================================================#

@Client.on_callback_query(filters.regex("^reply_txt$"))
async def reply_txt(client: Client, query: CallbackQuery):
    await query.answer()
    ask_text = await client.ask(query.from_user.id, "Send new reply text message in the next 60 seconds, send `0` to cancel or wait 60 seconds!\n\n__Note you can use both markdown and html formatting!__", filters=filters.text, timeout=60)
    try:
        text = ask_text.text
        if text == '0':
            return await ask_text.reply("__Reply text has not changed!__")
        client.reply_text = text
        await texts(client, query)
        return await ask_text.reply("__Reply text has been changed!__")
    except Exception as e:
        return client.LOGGER(__name__, client.name).error(e)