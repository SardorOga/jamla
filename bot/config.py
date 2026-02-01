import os
from dataclasses import dataclass


@dataclass
class Config:
    API_ID: int
    API_HASH: str
    BOT_TOKEN: str
    SESSION_STRING: str
    DATABASE_PATH: str = "data/jamla.db"
    LOG_LEVEL: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        api_id = os.getenv("API_ID")
        api_hash = os.getenv("API_HASH")
        bot_token = os.getenv("BOT_TOKEN")
        session_string = os.getenv("SESSION_STRING")

        if not all([api_id, api_hash, bot_token, session_string]):
            raise ValueError(
                "Missing required environment variables. "
                "Please set API_ID, API_HASH, BOT_TOKEN, and SESSION_STRING"
            )

        return cls(
            API_ID=int(api_id),
            API_HASH=api_hash,
            BOT_TOKEN=bot_token,
            SESSION_STRING=session_string,
            DATABASE_PATH=os.getenv("DATABASE_PATH", "data/jamla.db"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        )


# Messages in Uzbek and Russian
MESSAGES = {
    "uz": {
        "start": (
            "👋 Salom! Men <b>Jamla</b> botiman.\n\n"
            "Men sizga Telegram kanallarini kuzatishda yordam beraman.\n\n"
            "📌 <b>Buyruqlar:</b>\n"
            "/add @kanal - Kanal qo'shish\n"
            "/remove @kanal - Kanalni o'chirish\n"
            "/list - Kanallar ro'yxati\n"
            "/digest - Oxirgi 24 soat xulosasi\n"
            "/settings - Sozlamalar"
        ),
        "channel_added": "✅ <b>{channel}</b> kanali qo'shildi!",
        "channel_removed": "🗑 <b>{channel}</b> kanali o'chirildi!",
        "channel_not_found": "❌ Bu kanal topilmadi yoki siz unga obuna bo'lmagansiz.",
        "channel_already_added": "⚠️ Bu kanal allaqachon qo'shilgan.",
        "channel_not_in_list": "⚠️ Bu kanal ro'yxatda yo'q.",
        "no_channels": "📭 Sizda hali kanallar yo'q.\n/add @kanal buyrug'i bilan qo'shing.",
        "your_channels": "📋 <b>Sizning kanallaringiz:</b>\n\n{channels}",
        "settings_title": "⚙️ <b>Sozlamalar</b>",
        "mode_realtime": "🔴 Realtime",
        "mode_digest": "📰 Digest",
        "mode_off": "🔕 O'chirilgan",
        "current_mode": "Joriy rejim: <b>{mode}</b>",
        "digest_time": "Digest vaqti: <b>{time}</b>",
        "language": "Til: <b>{lang}</b>",
        "mode_changed": "✅ Rejim o'zgartirildi: <b>{mode}</b>",
        "time_changed": "✅ Digest vaqti o'zgartirildi: <b>{time}</b>",
        "lang_changed": "✅ Til o'zgartirildi: <b>{lang}</b>",
        "no_posts": "📭 Oxirgi 24 soatda yangi postlar yo'q.",
        "digest_header": "📰 <b>Oxirgi 24 soat xulosasi</b>\n\n",
        "new_post": "📢 <b>{channel}</b> dan yangi post:",
        "error": "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
        "invalid_time": "❌ Noto'g'ri vaqt formati. Masalan: 09:00",
        "enter_time": "⏰ Yangi digest vaqtini kiriting (masalan: 09:00):",
        "select_mode": "📡 Xabar rejimini tanlang:",
        "select_language": "🌐 Tilni tanlang:",
        "back": "⬅️ Orqaga",
    },
    "ru": {
        "start": (
            "👋 Привет! Я бот <b>Jamla</b>.\n\n"
            "Я помогу вам отслеживать Telegram каналы.\n\n"
            "📌 <b>Команды:</b>\n"
            "/add @канал - Добавить канал\n"
            "/remove @канал - Удалить канал\n"
            "/list - Список каналов\n"
            "/digest - Сводка за 24 часа\n"
            "/settings - Настройки"
        ),
        "channel_added": "✅ Канал <b>{channel}</b> добавлен!",
        "channel_removed": "🗑 Канал <b>{channel}</b> удалён!",
        "channel_not_found": "❌ Канал не найден или вы не подписаны на него.",
        "channel_already_added": "⚠️ Этот канал уже добавлен.",
        "channel_not_in_list": "⚠️ Этого канала нет в списке.",
        "no_channels": "📭 У вас пока нет каналов.\nДобавьте командой /add @канал",
        "your_channels": "📋 <b>Ваши каналы:</b>\n\n{channels}",
        "settings_title": "⚙️ <b>Настройки</b>",
        "mode_realtime": "🔴 Realtime",
        "mode_digest": "📰 Дайджест",
        "mode_off": "🔕 Выключено",
        "current_mode": "Текущий режим: <b>{mode}</b>",
        "digest_time": "Время дайджеста: <b>{time}</b>",
        "language": "Язык: <b>{lang}</b>",
        "mode_changed": "✅ Режим изменён: <b>{mode}</b>",
        "time_changed": "✅ Время дайджеста изменено: <b>{time}</b>",
        "lang_changed": "✅ Язык изменён: <b>{lang}</b>",
        "no_posts": "📭 За последние 24 часа новых постов нет.",
        "digest_header": "📰 <b>Сводка за 24 часа</b>\n\n",
        "new_post": "📢 Новый пост от <b>{channel}</b>:",
        "error": "❌ Произошла ошибка. Попробуйте ещё раз.",
        "invalid_time": "❌ Неверный формат времени. Например: 09:00",
        "enter_time": "⏰ Введите новое время дайджеста (например: 09:00):",
        "select_mode": "📡 Выберите режим уведомлений:",
        "select_language": "🌐 Выберите язык:",
        "back": "⬅️ Назад",
    },
}


def get_message(lang: str, key: str, **kwargs) -> str:
    """Get a message in the specified language."""
    msg = MESSAGES.get(lang, MESSAGES["uz"]).get(key, MESSAGES["uz"].get(key, key))
    if kwargs:
        msg = msg.format(**kwargs)
    return msg
