# 🤖 SmartBot — Telegram JSON AI Bot

SmartBot — bu O‘zbek tilidagi foydalanuvchi savollariga **faqat `data.json` hujjatidagi maʼlumotlar asosida** javob beradigan Telegram botdir. U **AI’ga o‘xshab ishlaydi**, lekin **internetga ulanmaydi** va tashqi API’larsiz, faqat lokal (offline) maʼlumotlar bazasiga tayanadi.

---

## 🧠 Funksionallik

- ✅ Kalit so‘zlarga asoslangan savol-javob tizimi
- ✅ O‘zbek, Rus va Ingliz tillarini qo‘llab-quvvatlaydi
- ✅ JSON formatdagi maʼlumotlar asosida ishlaydi
- ✅ `deep-translator` yordamida avtomatik tarjima
- ✅ Foydalanuvchi savollari log-faylga yoziladi
- ✅ Bir nechta `keywords` uchun barcha `response`lar birgalikda yuboriladi

---

## 🗂 Loyihaning tuzilmasi

```
📁 ChatBot/
├── bot.py               # Asosiy bot kodi (async / PTB v20)
├── data.json            # Savol-javoblar bazasi
├── interaction_log.txt  # Foydalanuvchi loglari
├── requirements.txt     # Kutubxonalar ro‘yxati
└── README.md            # Loyihani tushuntiruvchi fayl
```

---

## 📚 Texnologiyalar

- Python 3.10+
- [`python-telegram-bot==20.0`](https://github.com/python-telegram-bot/python-telegram-bot)
- [`deep-translator`](https://github.com/nidhaloff/deep-translator)
- `asyncio`, `logging`, `json`, `datetime`

---

## 🚀 Boshlash

### 🔧 O‘rnatish

```bash
git clone https://github.com/username/smartbot.git
cd smartbot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### ⚙️ Tokenni sozlash

`bot.py` faylida quyidagi satrni toping:

```python
TOKEN = 'YOUR_BOT_TOKEN_HERE'
```

Va uni o‘zingizning BotFather’dan olingan token bilan almashtiring.

### ▶️ Botni ishga tushirish

```bash
python bot.py
```

---

## 💬 JSON maʼlumotlar namunasi

```json
{
  "responses": [
    {
      "keywords": ["salom", "hi", "hello"],
      "response": "Salom! Sizga qanday yordam bera olaman?"
    },
    {
      "keywords": ["python", "piton"],
      "response": "Python — bu juda kuchli va soddaligi bilan mashhur dasturlash tili."
    },
    {
      "keywords": ["c#", "c sharp", "csharp"],
      "response": "C# — bu Microsoft tomonidan yaratilgan zamonaviy, obyektga yo‘naltirilgan til."
    }
  ]
}
```

---

## 🌐 Qo‘llab-quvvatlanadigan tillar

- 🇺🇿 O'zbekcha
- 🇬🇧 English
- 🇷🇺 Русский

Bot foydalanuvchining tanlagan tiliga qarab javobni avtomatik tarjima qiladi.

---

## 📈 Foydalanuvchi faoliyatini loglash

Barcha savol va javoblar `interaction_log.txt` fayliga quyidagi formatda yoziladi:

```
[2025-05-17 20:12:34] User(123456789): c# haqida ayting -> Bot: C# — bu Microsoft...
```

---

## ✅ Kelajak rejalari (TODO)

- [ ] Admin panel orqali `data.json`ni o‘zgartirish
- [ ] Hujjat (PDF/Docx) o‘qishdan `data.json`ni avtomatik yaratish
- [ ] Qo‘shilgan so‘zlar uchun `fuzzy matching` opsiyasi (`rapidfuzz`)
- [ ] Caching va ishlashni o
