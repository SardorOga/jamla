import logging
import re
from telethon import TelegramClient, events, Button

from .database import Database
from .channel_watcher import ChannelWatcher
from .digest import DigestManager
from .config import get_message

logger = logging.getLogger(__name__)

# Callback data patterns
MODE_PATTERN = re.compile(r"^mode:(\w+)$")
LANG_PATTERN = re.compile(r"^lang:(\w+)$")
SETTINGS_PATTERN = re.compile(r"^settings:(\w+)$")


class BotHandlers:
    def __init__(
        self,
        bot: TelegramClient,
        db: Database,
        watcher: ChannelWatcher,
        digest_manager: DigestManager
    ):
        self.bot = bot
        self.db = db
        self.watcher = watcher
        self.digest_manager = digest_manager
        self._waiting_for_time = set()  # Users waiting for time input

    def setup_handlers(self):
        """Setup all bot command handlers."""

        @self.bot.on(events.NewMessage(pattern="/start"))
        async def start_handler(event):
            user_id = event.sender_id
            username = event.sender.username

            user = self.db.get_or_create_user(user_id, username)
            lang = user.get("language", "uz")

            await event.respond(
                get_message(lang, "start"),
                parse_mode="html"
            )
            logger.info(f"User {user_id} started bot")

        @self.bot.on(events.NewMessage(pattern=r"/add\s+(@?\w+)"))
        async def add_channel_handler(event):
            user_id = event.sender_id
            user = self.db.get_or_create_user(user_id)
            lang = user.get("language", "uz")

            match = re.match(r"/add\s+(@?\w+)", event.text)
            if not match:
                return

            channel_username = match.group(1)

            success, result = await self.watcher.add_channel_for_user(user_id, channel_username)

            if success:
                await event.respond(
                    get_message(lang, "channel_added", channel=result),
                    parse_mode="html"
                )
            else:
                await event.respond(
                    get_message(lang, result),
                    parse_mode="html"
                )

        @self.bot.on(events.NewMessage(pattern=r"/remove\s+(@?\w+)"))
        async def remove_channel_handler(event):
            user_id = event.sender_id
            user = self.db.get_or_create_user(user_id)
            lang = user.get("language", "uz")

            match = re.match(r"/remove\s+(@?\w+)", event.text)
            if not match:
                return

            channel_username = match.group(1)

            success, result = await self.watcher.remove_channel_for_user(user_id, channel_username)

            if success:
                await event.respond(
                    get_message(lang, "channel_removed", channel=result),
                    parse_mode="html"
                )
            else:
                await event.respond(
                    get_message(lang, result),
                    parse_mode="html"
                )

        @self.bot.on(events.NewMessage(pattern="/list"))
        async def list_channels_handler(event):
            user_id = event.sender_id
            user = self.db.get_or_create_user(user_id)
            lang = user.get("language", "uz")

            channels = self.db.get_user_channels(user_id)

            if not channels:
                await event.respond(
                    get_message(lang, "no_channels"),
                    parse_mode="html"
                )
                return

            channel_list = "\n".join(
                f"• @{ch['channel_username']} - {ch['title']}"
                for ch in channels
            )

            await event.respond(
                get_message(lang, "your_channels", channels=channel_list),
                parse_mode="html"
            )

        @self.bot.on(events.NewMessage(pattern="/digest"))
        async def digest_handler(event):
            user_id = event.sender_id
            user = self.db.get_or_create_user(user_id)
            lang = user.get("language", "uz")

            await self.digest_manager.send_manual_digest(user_id, lang)

        @self.bot.on(events.NewMessage(pattern="/settings"))
        async def settings_handler(event):
            user_id = event.sender_id
            await self._show_settings(event, user_id)

        @self.bot.on(events.CallbackQuery())
        async def callback_handler(event):
            user_id = event.sender_id
            data = event.data.decode("utf-8")

            user = self.db.get_user(user_id)
            if not user:
                user = self.db.get_or_create_user(user_id)
            lang = user.get("language", "uz")

            # Handle mode change menu
            if data == "settings:mode":
                await self._show_mode_selection(event, lang)

            # Handle language change menu
            elif data == "settings:lang":
                await self._show_language_selection(event, lang)

            # Handle time change
            elif data == "settings:time":
                self._waiting_for_time.add(user_id)
                await event.edit(
                    get_message(lang, "enter_time"),
                    parse_mode="html"
                )

            # Handle back to settings
            elif data == "settings:back":
                await self._show_settings(event, user_id, edit=True)

            # Handle mode selection
            elif match := MODE_PATTERN.match(data):
                mode = match.group(1)
                self.db.update_user_mode(user_id, mode)

                mode_names = {
                    "realtime": get_message(lang, "mode_realtime"),
                    "digest": get_message(lang, "mode_digest"),
                    "off": get_message(lang, "mode_off"),
                }

                await event.answer(
                    get_message(lang, "mode_changed", mode=mode_names.get(mode, mode))
                )
                await self._show_settings(event, user_id, edit=True)

            # Handle language selection
            elif match := LANG_PATTERN.match(data):
                new_lang = match.group(1)
                self.db.update_user_language(user_id, new_lang)

                lang_names = {"uz": "O'zbekcha", "ru": "Русский"}

                await event.answer(
                    get_message(new_lang, "lang_changed", lang=lang_names.get(new_lang))
                )
                await self._show_settings(event, user_id, edit=True)

        @self.bot.on(events.NewMessage())
        async def message_handler(event):
            user_id = event.sender_id

            # Handle time input
            if user_id in self._waiting_for_time:
                self._waiting_for_time.discard(user_id)

                user = self.db.get_user(user_id)
                lang = user.get("language", "uz") if user else "uz"

                # Validate time format
                time_text = event.text.strip()
                if re.match(r"^\d{2}:\d{2}$", time_text):
                    try:
                        hours, minutes = map(int, time_text.split(":"))
                        if 0 <= hours < 24 and 0 <= minutes < 60:
                            self.db.update_user_digest_time(user_id, time_text)
                            await event.respond(
                                get_message(lang, "time_changed", time=time_text),
                                parse_mode="html"
                            )
                            return
                    except ValueError:
                        pass

                await event.respond(
                    get_message(lang, "invalid_time"),
                    parse_mode="html"
                )

    async def _show_settings(self, event, user_id: int, edit: bool = False):
        """Show settings menu."""
        user = self.db.get_user(user_id)
        if not user:
            user = self.db.get_or_create_user(user_id)

        lang = user.get("language", "uz")
        mode = user.get("mode", "realtime")
        digest_time = user.get("digest_time", "09:00")

        mode_names = {
            "realtime": get_message(lang, "mode_realtime"),
            "digest": get_message(lang, "mode_digest"),
            "off": get_message(lang, "mode_off"),
        }
        lang_names = {"uz": "O'zbekcha", "ru": "Русский"}

        text = (
            f"{get_message(lang, 'settings_title')}\n\n"
            f"{get_message(lang, 'current_mode', mode=mode_names.get(mode, mode))}\n"
            f"{get_message(lang, 'digest_time', time=digest_time)}\n"
            f"{get_message(lang, 'language', lang=lang_names.get(lang, lang))}"
        )

        buttons = [
            [Button.inline("📡 " + get_message(lang, "select_mode").rstrip(":"), b"settings:mode")],
            [Button.inline("⏰ " + get_message(lang, "digest_time", time="").rstrip(": "), b"settings:time")],
            [Button.inline("🌐 " + get_message(lang, "select_language").rstrip(":"), b"settings:lang")],
        ]

        if edit:
            await event.edit(text, buttons=buttons, parse_mode="html")
        else:
            await event.respond(text, buttons=buttons, parse_mode="html")

    async def _show_mode_selection(self, event, lang: str):
        """Show mode selection menu."""
        buttons = [
            [Button.inline(get_message(lang, "mode_realtime"), b"mode:realtime")],
            [Button.inline(get_message(lang, "mode_digest"), b"mode:digest")],
            [Button.inline(get_message(lang, "mode_off"), b"mode:off")],
            [Button.inline(get_message(lang, "back"), b"settings:back")],
        ]

        await event.edit(
            get_message(lang, "select_mode"),
            buttons=buttons,
            parse_mode="html"
        )

    async def _show_language_selection(self, event, lang: str):
        """Show language selection menu."""
        buttons = [
            [Button.inline("🇺🇿 O'zbekcha", b"lang:uz")],
            [Button.inline("🇷🇺 Русский", b"lang:ru")],
            [Button.inline(get_message(lang, "back"), b"settings:back")],
        ]

        await event.edit(
            get_message(lang, "select_language"),
            buttons=buttons,
            parse_mode="html"
        )
