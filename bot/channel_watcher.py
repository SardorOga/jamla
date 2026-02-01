import logging
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import Channel
from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError, FloodWaitError

from .database import Database
from .config import get_message

logger = logging.getLogger(__name__)


class ChannelWatcher:
    def __init__(self, client: TelegramClient, bot: TelegramClient, db: Database):
        self.client = client  # Userbot client for watching channels
        self.bot = bot        # Bot client for sending messages
        self.db = db
        self._watching_channels = set()
        self._lock = asyncio.Lock()

    async def start(self):
        """Start watching all subscribed channels."""
        channels = self.db.get_all_channels()
        for channel in channels:
            await self._add_channel_handler(channel["channel_id"])
        logger.info(f"Started watching {len(channels)} channels")

    async def resolve_channel(self, username: str) -> dict | None:
        """Resolve channel by username and return channel info."""
        try:
            # Remove @ if present
            username = username.lstrip("@")

            entity = await self.client.get_entity(username)

            if not isinstance(entity, Channel):
                logger.warning(f"{username} is not a channel")
                return None

            return {
                "username": username,
                "channel_id": entity.id,
                "title": entity.title,
            }
        except UsernameNotOccupiedError:
            logger.warning(f"Channel @{username} not found")
            return None
        except ChannelPrivateError:
            logger.warning(f"Channel @{username} is private")
            return None
        except FloodWaitError as e:
            logger.warning(f"Flood wait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return await self.resolve_channel(username)
        except Exception as e:
            logger.error(f"Error resolving channel @{username}: {e}")
            return None

    async def add_channel_for_user(self, user_id: int, channel_username: str) -> tuple[bool, str]:
        """
        Add a channel for a user.
        Returns (success, message_key).
        """
        user = self.db.get_or_create_user(user_id)
        lang = user.get("language", "uz")

        # Check if already added
        existing = self.db.get_channel_by_username(channel_username)
        if existing and self.db.user_has_channel(user_id, existing["id"]):
            return False, "channel_already_added"

        # Resolve channel
        channel_info = await self.resolve_channel(channel_username)
        if not channel_info:
            return False, "channel_not_found"

        # Add to database
        channel_db_id = self.db.add_channel(
            channel_info["username"],
            channel_info["channel_id"],
            channel_info["title"]
        )

        if not self.db.add_user_channel(user_id, channel_db_id):
            return False, "channel_already_added"

        # Start watching this channel
        await self._add_channel_handler(channel_info["channel_id"])

        logger.info(f"User {user_id} added channel @{channel_username}")
        return True, channel_info["title"]

    async def remove_channel_for_user(self, user_id: int, channel_username: str) -> tuple[bool, str]:
        """
        Remove a channel for a user.
        Returns (success, message_key).
        """
        channel = self.db.get_channel_by_username(channel_username.lstrip("@"))
        if not channel:
            return False, "channel_not_in_list"

        if not self.db.remove_user_channel(user_id, channel["id"]):
            return False, "channel_not_in_list"

        # Check if anyone else is watching this channel
        remaining_users = self.db.get_channel_users(channel["id"])
        if not remaining_users:
            await self._remove_channel_handler(channel["channel_id"])

        logger.info(f"User {user_id} removed channel @{channel_username}")
        return True, channel["title"]

    async def _add_channel_handler(self, channel_id: int):
        """Add event handler for a channel."""
        async with self._lock:
            if channel_id in self._watching_channels:
                return
            self._watching_channels.add(channel_id)

        logger.debug(f"Now watching channel {channel_id}")

    async def _remove_channel_handler(self, channel_id: int):
        """Remove event handler for a channel."""
        async with self._lock:
            self._watching_channels.discard(channel_id)

        logger.debug(f"Stopped watching channel {channel_id}")

    async def handle_new_message(self, event):
        """Handle new messages from watched channels."""
        try:
            # Get channel info
            chat = await event.get_chat()
            if not isinstance(chat, Channel):
                return

            channel_id = chat.id

            # Check if we're watching this channel
            if channel_id not in self._watching_channels:
                return

            channel = self.db.get_channel_by_id(channel_id)
            if not channel:
                return

            message_text = event.message.text or event.message.caption or ""

            # Get users subscribed to this channel
            users = self.db.get_channel_users(channel["id"])

            for user in users:
                user_id = user["user_id"]
                mode = user["mode"]
                lang = user["language"]

                if mode == "off":
                    continue

                if mode == "realtime":
                    # Forward message immediately
                    await self._send_realtime(user_id, event, channel, lang)
                elif mode == "digest":
                    # Save for digest
                    self.db.add_post(channel["id"], event.message.id, message_text)

        except Exception as e:
            logger.error(f"Error handling new message: {e}")

    async def _send_realtime(self, user_id: int, event, channel: dict, lang: str):
        """Send message to user in realtime mode."""
        try:
            # Send notification header
            header = get_message(lang, "new_post", channel=channel["title"])
            await self.bot.send_message(user_id, header, parse_mode="html")

            # Forward the actual message
            await self.bot.forward_messages(user_id, event.message)

            # Rate limiting - small delay between users
            await asyncio.sleep(0.1)

        except FloodWaitError as e:
            logger.warning(f"Flood wait when sending to {user_id}: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error sending realtime message to {user_id}: {e}")

    def setup_handlers(self):
        """Setup event handlers for the userbot client."""
        @self.client.on(events.NewMessage())
        async def on_new_message(event):
            # Only process messages from channels
            if event.is_channel and not event.is_group:
                await self.handle_new_message(event)
