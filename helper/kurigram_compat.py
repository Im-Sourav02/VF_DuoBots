"""Kurigram InlineKeyboardButton compatibility.

Kurigram's constructor is:
    (text, icon_custom_emoji_id, style, url, callback_data, ...)

Older Pyrogram/pyrofork used:
    (text, callback_data, url, ...)

Positional `InlineKeyboardButton("Label", "fsub")` therefore stores "fsub" as an
emoji id, and send/edit crashes with ValueError when Kurigram does int("fsub").
This wrapper restores the old argument order and is applied before plugins load.
"""
from pyrogram.enums import ButtonStyle
from pyrogram.types.bots_and_keyboards.inline_keyboard_button import (
    InlineKeyboardButton as _KurigramIKB,
)


class InlineKeyboardButton(_KurigramIKB):
    def __init__(
        self,
        text: str,
        callback_data=None,
        url=None,
        *,
        icon_custom_emoji_id=None,
        style=ButtonStyle.DEFAULT,
        **kwargs,
    ):
        super().__init__(
            text,
            icon_custom_emoji_id=icon_custom_emoji_id,
            style=style,
            url=url,
            callback_data=callback_data,
            **kwargs,
        )


def apply_inline_keyboard_compat():
    import pyrogram.types as types
    import pyrogram.types.bots_and_keyboards as keyboards
    import pyrogram.types.bots_and_keyboards.inline_keyboard_button as ikb_mod

    types.InlineKeyboardButton = InlineKeyboardButton
    keyboards.InlineKeyboardButton = InlineKeyboardButton
    ikb_mod.InlineKeyboardButton = InlineKeyboardButton
