# Jamla Bot 🔔

Telegram kanal kuzatuvchi bot. Foydalanuvchilarga sevimli kanallarini kuzatish va yangi postlarni olish imkonini beradi.

## Xususiyatlar

- 📡 **Realtime rejim** - Yangi postlar darhol forward qilinadi
- 📰 **Digest rejim** - Kuniga 1 marta barcha postlar yuboriladi
- 🌐 **Ko'p tilli** - O'zbek va Rus tillarini qo'llab-quvvatlaydi
- ⚙️ **Moslashuvchan** - Har bir foydalanuvchi o'z sozlamalarini belgilashi mumkin

## Buyruqlar

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni ishga tushirish |
| `/add @kanal` | Kanal qo'shish |
| `/remove @kanal` | Kanalni o'chirish |
| `/list` | Kanallar ro'yxati |
| `/digest` | Oxirgi 24 soat xulosasi |
| `/settings` | Sozlamalar |

## O'rnatish

### 1. Telegram credentials olish

1. [my.telegram.org](https://my.telegram.org) ga kiring
2. "API development tools" bo'limidan `API_ID` va `API_HASH` oling
3. [@BotFather](https://t.me/BotFather) dan yangi bot yarating va `BOT_TOKEN` oling

### 2. Session string yaratish

```bash
# Dependencies o'rnatish
pip install telethon

# Session string generatsiya qilish
python generate_session.py
```

Telefon raqam va tasdiqlash kodini kiriting. Natijada `SESSION_STRING` chiqadi.

### 3. .env faylni sozlash

```bash
cp .env.example .env
```

`.env` faylni oching va credentials kiriting:

```env
API_ID=12345678
API_HASH=abcdef1234567890
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
SESSION_STRING=1BVtsOK8Bu...
```

### 4. Docker bilan ishga tushirish

```bash
# Build va start
docker-compose up -d

# Loglarni ko'rish
docker-compose logs -f

# To'xtatish
docker-compose down
```

### Yoki Python bilan

```bash
# Dependencies
pip install -r requirements.txt

# Ishga tushirish
python -m bot.main
```

## Fayl strukturasi

```
jamla/
├── bot/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── handlers.py       # Bot buyruqlari
│   ├── database.py       # SQLite operatsiyalar
│   ├── channel_watcher.py # Kanal kuzatuv
│   ├── digest.py         # Digest yuborish
│   └── config.py         # Sozlamalar va xabarlar
├── data/                 # SQLite bazasi
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── generate_session.py
├── .env.example
└── README.md
```

## Texnologiyalar

- **Python 3.11+**
- **Telethon** - Telegram MTProto kutubxonasi
- **SQLite** - Ma'lumotlar bazasi
- **Docker** - Konteynerizatsiya

## Muhim eslatmalar

⚠️ **Userbot haqida:** Bot kanallarni kuzatish uchun sizning Telegram accountingizdan foydalanadi (userbot). Bu Telegram ToS ga mos, lekin bot spam yoki boshqa noto'g'ri maqsadlarda ishlatilmasligi kerak.

⚠️ **Rate limits:** Telegram cheklovlariga rioya qilish uchun bot avtomatik ravishda kechikishlar qo'shadi.

## Litsenziya

MIT License
