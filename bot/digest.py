import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError

from .database import Database
from .config import get_message

logger = logging.getLogger(__name__)


class DigestManager:
    def __init__(self, bot: TelegramClient, db: Database):
        self.bot = bot
        self.db = db
        self._running = False
        self._task = None

    async def start(self):
        """Start the digest scheduler."""
        self._running = True
        self._task = asyncio.create_task(self._scheduler())
        logger.info("Digest scheduler started")

    async def stop(self):
        """Stop the digest scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Digest scheduler stopped")

    async def _scheduler(self):
        """Main scheduler loop - checks every minute."""
        while self._running:
            try:
                current_time = datetime.now().strftime("%H:%M")

                # Get users who should receive digest now
                users = self.db.get_users_for_digest(current_time)

                for user in users:
                    await self.send_digest_to_user(user["user_id"], user["language"])

                # Also cleanup old posts once a day at midnight
                if current_time == "00:00":
                    deleted = self.db.cleanup_old_posts(days=7)
                    if deleted:
                        logger.info(f"Cleaned up {deleted} old posts")

                # Wait until next minute
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in digest scheduler: {e}")
                await asyncio.sleep(60)

    async def send_digest_to_user(self, user_id: int, lang: str = "uz"):
        """Send digest to a specific user."""
        try:
            posts = self.db.get_unsent_posts_for_user(user_id)

            if not posts:
                return

            # Group posts by channel
            channels = {}
            for post in posts:
                channel_title = post["channel_title"]
                if channel_title not in channels:
                    channels[channel_title] = []
                channels[channel_title].append(post)

            # Build digest message
            message = get_message(lang, "digest_header")

            for channel_title, channel_posts in channels.items():
                message += f"📢 <b>{channel_title}</b> ({len(channel_posts)} ta post)\n"

                for post in channel_posts[:5]:  # Limit to 5 posts per channel in summary
                    text = post["text"]
                    if len(text) > 100:
                        text = text[:100] + "..."
                    if text:
                        message += f"  • {text}\n"

                if len(channel_posts) > 5:
                    message += f"  <i>...va yana {len(channel_posts) - 5} ta</i>\n"
                message += "\n"

            # Send digest
            await self.bot.send_message(user_id, message, parse_mode="html")

            # Mark posts as sent
            post_ids = [p["id"] for p in posts]
            self.db.mark_posts_sent(post_ids)

            logger.info(f"Sent digest to user {user_id}: {len(posts)} posts")

        except FloodWaitError as e:
            logger.warning(f"Flood wait when sending digest to {user_id}: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error sending digest to {user_id}: {e}")

    async def send_manual_digest(self, user_id: int, lang: str = "uz") -> bool:
        """
        Send manual digest (for /digest command).
        Returns True if posts were found and sent.
        """
        posts = self.db.get_unsent_posts_for_user(user_id)

        if not posts:
            await self.bot.send_message(
                user_id,
                get_message(lang, "no_posts"),
                parse_mode="html"
            )
            return False

        await self.send_digest_to_user(user_id, lang)
        return True
