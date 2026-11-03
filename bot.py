#(©) Codeflix_Bots — Refactored for AIO three-bot deployment
import os
import json
import asyncio
from aiohttp import web
from plugins import web_server

from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from config import (
    LOGGER, PORT, OWNER_ID,
    SHORT_URL, SHORT_API, SHORT_TUT,
    BOT1_DISPLAY_NAME, BOT2_DISPLAY_NAME,
)
from helper import MongoDB
from helper.conversation import ConversationMixin

version = "v2.0.0"


# ═══════════════════════════════════════════════════════════════
# Bot — Shared filestore bot class (used by both Rin and Sephra)
# ═══════════════════════════════════════════════════════════════

class Bot(ConversationMixin, Client):
    def __init__(
        self,
        session, workers, db, fsub, token, admins, messages,
        auto_del, db_uri, db_name, api_id, api_hash, protect,
        disable_btn=True,
        bot_type="bot1",          # "bot1" | "bot2" (or legacy "rin" | "sephra")
        bot2_db_channel=0,        # For Bot1: the Bot2 DB channel ID
        bot2_bot_username="",     # For Bot1: used to build Bot2 deep-links
        sephra_db_channel=0,      # Legacy alias
        sephra_bot_username="",   # Legacy alias
        credits_enabled=False,    # MongoDB credits + verification tokens (𝘚𝘢𝘥𝘪𝘦 𝘚𝘪𝘯𝘬 only)
    ):
        super().__init__(
            name=session,
            api_hash=api_hash,
            api_id=api_id,
            plugins={"root": "plugins"},
            workers=workers,
            bot_token=token
        )
        self.bot_token       = token
        self.LOGGER          = LOGGER
        self.name            = session
        self.db              = db
        self.fsub            = fsub
        self.owner           = OWNER_ID
        self.fsub_dict       = {}
        self.admins          = admins + [OWNER_ID] if OWNER_ID not in admins else admins
        self.messages        = messages
        self.auto_del        = auto_del
        self.protect         = protect
        self.req_fsub        = {}
        self.disable_btn     = disable_btn
        self.reply_text      = messages.get('REPLY', 'Do not send any useless message in the bot.')
        self.custom_caption  = messages.get('CUSTOM_CAPTION', '')
        self.mongodb         = MongoDB(db_uri, db_name)
        self.req_channels    = []
        self.db_channels     = {}
        self.primary_db_channel = db

        # ── AIO multi-bot extras ─────────────────────────────
        self.bot_type            = bot_type          # "bot1" or "bot2"
        self.bot2_db_channel     = bot2_db_channel or sephra_db_channel
        self.bot2_bot_username   = bot2_bot_username or sephra_bot_username
        self.sephra_db_channel   = self.bot2_db_channel
        self.sephra_bot_username = self.bot2_bot_username
        self.credits_enabled     = credits_enabled

    # ── Startup ──────────────────────────────────────────────

    async def start(self):
        await super().start()
        self._init_conversations()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        # ── Force-sub channels (static config) ───────────────
        if len(self.fsub) > 0:
            for channel in self.fsub:
                try:
                    chat = await self.get_chat(channel[0])
                    name = chat.title
                    link = None
                    if not channel[1]:
                        link = chat.invite_link
                    if not link and not channel[2]:
                        chat_link = await self.create_chat_invite_link(channel[0], creates_join_request=channel[1])
                        link = chat_link.invite_link
                    if not channel[1]:
                        self.fsub_dict[channel[0]] = [name, link, False, 0]
                    if channel[1]:
                        self.fsub_dict[channel[0]] = [name, link, True, 0]
                        self.req_channels.append(channel[0])
                    if channel[2] > 0:
                        self.fsub_dict[channel[0]] = [name, None, channel[1], channel[2]]
                except Exception as e:
                    self.LOGGER(__name__, self.name).warning("Bot can't Export Invite link from Force Sub Channel!")
                    self.LOGGER(__name__, self.name).warning("\nBot Stopped.")
                    sys.exit()

        # ── Force-sub channels (from DB) ──────────────────────
        try:
            db_fsub_channels = await self.mongodb.get_fsub_channels()
            for channel_id_str, channel_data in db_fsub_channels.items():
                channel_id = int(channel_id_str)
                if channel_id in self.fsub_dict:
                    continue
                try:
                    chat = await self.get_chat(channel_id)
                    channel_data[0] = chat.title
                    self.fsub_dict[channel_id] = channel_data
                    if channel_data[2]:
                        self.req_channels.append(channel_id)
                except Exception as e:
                    self.LOGGER(__name__, self.name).warning(f"Could not load dynamic fsub channel {channel_id}: {e}")
                    await self.mongodb.remove_fsub_channel(channel_id)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Error loading dynamic fsub channels: {e}")

        await self.mongodb.set_channels(self.req_channels)

        # ── DB channels (from DB) ─────────────────────────────
        try:
            db_channels_data = await self.mongodb.get_db_channels()
            self.db_channels = {}
            self.primary_db_channel = self.db
            for channel_id_str, channel_data in db_channels_data.items():
                channel_id = int(channel_id_str)
                try:
                    chat = await self.get_chat(channel_id)
                    channel_data['name'] = chat.title
                    self.db_channels[channel_id_str] = channel_data
                    if channel_data.get('is_primary', False):
                        self.primary_db_channel = channel_id
                        self.db = channel_id
                except Exception as e:
                    self.LOGGER(__name__, self.name).warning(f"Could not load DB channel {channel_id}: {e}")
                    await self.mongodb.remove_db_channel(channel_id)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Error loading DB channels: {e}")

        # ── Shortener settings ────────────────────────────────
        try:
            shortner_settings      = await self.mongodb.get_shortner_settings()
            self.short_url         = shortner_settings.get('short_url', SHORT_URL)
            self.short_api         = shortner_settings.get('short_api', SHORT_API)
            self.tutorial_link     = shortner_settings.get('tutorial_link', SHORT_TUT)
            self.shortner_enabled  = shortner_settings.get('enabled', True)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Error loading shortner settings: {e}")
            self.short_url        = SHORT_URL
            self.short_api        = SHORT_API
            self.tutorial_link    = SHORT_TUT
            self.shortner_enabled = True

        # ── Misc bot settings ─────────────────────────────────
        try:
            self.auto_watermark = await self.mongodb.get_bot_setting('auto_watermark', True)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Error loading bot settings: {e}")
            self.auto_watermark = True

        # ── Custom Caption (from DB) ──────────────────────────
        try:
            db_caption = await self.mongodb.get_caption()
            if db_caption is not None:
                self.custom_caption = db_caption
                self.messages["CUSTOM_CAPTION"] = db_caption
            else:
                self.custom_caption = self.messages.get("CUSTOM_CAPTION", "")
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Error loading custom caption from DB: {e}")
            self.custom_caption = self.messages.get("CUSTOM_CAPTION", "")

        # ── Admins (from MongoDB "admins" collection) ─────────
        try:
            db_admins = await self.mongodb.get_admins_list()
            for a in db_admins:
                if a not in self.admins:
                    self.admins.append(a)
            # Ensure static config admins & owner exist in MongoDB
            for a in self.admins:
                if a not in db_admins:
                    await self.mongodb.add_admin(a)
            self.LOGGER(__name__, self.name).info(f"Loaded {len(self.admins)} admin(s) from MongoDB.")
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Error loading admins from DB: {e}")

        # ── Auto-clean expired premium users ──────────────────
        try:
            purged = await self.mongodb.clean_expired_pros()
            if purged > 0:
                self.LOGGER(__name__, self.name).info(f"Purged {purged} expired premium user(s) from database.")
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Error purging expired premium users: {e}")

        # ── Credits indexes (TTL for verification tokens) ─────
        if self.credits_enabled:
            try:
                await self.mongodb.ensure_credit_indexes()
                self.LOGGER(__name__, self.name).info("Credits enabled (verification-token indexes ready).")
            except Exception as e:
                self.LOGGER(__name__, self.name).warning(f"Could not create credit indexes: {type(e).__name__}: {e}")

        # ── Verify primary DB channel ─────────────────────────
        # Both Rin AND Sephra must have a valid DB channel.
        try:
            db_channel = await self.get_chat(self.db)
            self.db_channel = db_channel
            test = await self.send_message(chat_id=db_channel.id, text=f"Testing Message — {self.name}")
            await test.delete()
            self.LOGGER(__name__, self.name).info(f"Primary DB Channel: {self.primary_db_channel}")
            self.LOGGER(__name__, self.name).info(f"Total DB Channels: {len(self.db_channels)}")
        except Exception as e:
            self.LOGGER(__name__, self.name).error(
                f"[{self.name}] DB Channel verification FAILED!\n"
                f"  Channel ID: {self.db}\n"
                f"  Error: {e}\n"
                f"  Fix: Make sure the bot is Admin (with post & delete permissions) in the DB channel."
            )
            # Raise so only this bot fails -- does NOT kill the other bots
            raise RuntimeError(
                f"[{self.name}] DB Channel {self.db} is inaccessible. "
                f"Make the bot admin with post permission in that channel."
            ) from e

        self.LOGGER(__name__, self.name).info(f"[{self.bot_type.upper()}] Bot Started!!")

        # ── Notify owner ──────────────────────────────────────
        try:
            label = BOT1_DISPLAY_NAME if self.bot_type in ("bot1", "rin") else BOT2_DISPLAY_NAME
            restart_message = f"<b>›› [{label}] ʜᴇʏ sᴇɴᴘᴀɪ!!\n ɪ'ᴍ ᴀʟɪᴠᴇ ɴᴏᴡ 🍃...</b>"
            await self.send_message(chat_id=self.owner, text=restart_message)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"Failed to send restart notification to owner: {e}")

        self.username = usr_bot_me.username

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__, self.name).info("Bot stopped.")


# ═══════════════════════════════════════════════════════════════
# Web health-check server
# ═══════════════════════════════════════════════════════════════

async def web_app():
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
