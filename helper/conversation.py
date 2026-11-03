import asyncio

from pyrogram import StopPropagation
from pyrogram.handlers import MessageHandler


class ListenerTimeout(Exception):
    """Raised when listen()/ask() gets no matching message before the timeout."""


class ConversationMixin:
    """
    listen()/ask() for Kurigram, which (unlike pyrofork) ships without pyromod.
    Covers only the call shapes used by the plugins:
        await client.listen(user_id=..., filters=..., timeout=...)
        await client.ask(chat_id, text, filters=..., timeout=...)
    A matched message is consumed: handlers in later groups never see it.
    """

    LISTENER_GROUP = -100

    def _init_conversations(self):
        self._listeners = []
        self.add_handler(MessageHandler(self._resolve_listeners), group=self.LISTENER_GROUP)

    async def _resolve_listeners(self, client, message):
        for listener in list(getattr(self, "_listeners", [])):
            future = listener["future"]
            if future.done():
                continue
            if listener["chat_id"] is not None and getattr(message.chat, "id", None) != listener["chat_id"]:
                continue
            if listener["user_id"] is not None and getattr(message.from_user, "id", None) != listener["user_id"]:
                continue
            if listener["filters"] is not None and not await MessageHandler(None, listener["filters"]).check(client, message):
                continue
            future.set_result(message)
            raise StopPropagation

    async def listen(self, filters=None, timeout=None, chat_id=None, user_id=None):
        if chat_id is None and user_id is None:
            raise ValueError("listen() needs chat_id or user_id")
        if isinstance(chat_id, str):
            chat_id = (await self.get_chat(chat_id)).id
        listener = {
            "chat_id": chat_id,
            "user_id": user_id,
            "filters": filters,
            "future": asyncio.get_running_loop().create_future(),
        }
        self._listeners.append(listener)
        try:
            return await asyncio.wait_for(listener["future"], timeout)
        except asyncio.TimeoutError as e:
            raise ListenerTimeout(f"No reply within {timeout}s") from e
        finally:
            if listener in self._listeners:
                self._listeners.remove(listener)

    async def ask(self, chat_id, text, filters=None, timeout=None, user_id=None, **kwargs):
        sent = await self.send_message(chat_id, text, **kwargs)
        response = await self.listen(filters=filters, timeout=timeout, chat_id=sent.chat.id, user_id=user_id)
        response.sent_message = sent
        return response
