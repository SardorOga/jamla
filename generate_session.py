#!/usr/bin/env python3
"""
Session string generatori.

Bu script sizning Telegram accountingiz uchun session string yaratadi.
Session string userbot sifatida kanallarni kuzatish uchun kerak.

Ishlatish:
    python generate_session.py

Keyin telefon raqam va kod kiritasiz.
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = input("API_ID kiriting: ")
API_HASH = input("API_HASH kiriting: ")


async def main():
    async with TelegramClient(
        StringSession(),
        int(API_ID),
        API_HASH
    ) as client:
        print("\n✅ Session string yaratildi!\n")
        print("=" * 50)
        print(client.session.save())
        print("=" * 50)
        print("\nBu stringni .env faylga SESSION_STRING sifatida qo'shing.")


if __name__ == "__main__":
    asyncio.run(main())
