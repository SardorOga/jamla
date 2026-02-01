#!/usr/bin/env python3
"""
Jamla Bot - Telegram kanal kuzatuvchi

Bu bot foydalanuvchilarga Telegram kanallarini kuzatish
va yangi postlarni olish imkonini beradi.
"""

import os
import sys
import signal
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

from .config import Config
from .database import Database
from .channel_watcher import ChannelWatcher
from .digest import DigestManager
from .handlers import BotHandlers

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


class JamlaBot:
    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.DATABASE_PATH)

        # Bot client (for interacting with users)
        self.bot = TelegramClient(
            "bot",
            config.API_ID,
            config.API_HASH
        )

        # Userbot client (for watching channels)
        self.userbot = TelegramClient(
            StringSession(config.SESSION_STRING),
            config.API_ID,
            config.API_HASH
        )

        self.watcher = ChannelWatcher(self.userbot, self.bot, self.db)
        self.digest_manager = DigestManager(self.bot, self.db)
        self.handlers = BotHandlers(self.bot, self.db, self.watcher, self.digest_manager)

        self._running = False

    async def start(self):
        """Start the bot."""
        logger.info("Starting Jamla Bot...")

        # Start clients
        await self.bot.start(bot_token=self.config.BOT_TOKEN)
        await self.userbot.start()

        logger.info("Telegram clients connected")

        # Setup handlers
        self.handlers.setup_handlers()
        self.watcher.setup_handlers()

        # Start services
        await self.watcher.start()
        await self.digest_manager.start()

        self._running = True
        logger.info("Jamla Bot is running!")

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping Jamla Bot...")
        self._running = False

        await self.digest_manager.stop()

        await self.bot.disconnect()
        await self.userbot.disconnect()

        logger.info("Jamla Bot stopped")


async def main():
    """Main entry point."""
    # Load config
    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Set log level
    logging.getLogger().setLevel(getattr(logging, config.LOG_LEVEL))

    # Create bot instance
    bot = JamlaBot(config)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(bot.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await bot.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
