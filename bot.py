import json
import random
import logging
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
from deep_translator import GoogleTranslator
from datetime import datetime

# Logger sozlash
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# JSON faylni yuklash
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Tokeningizni bu yerga joylashtiring
TOKEN = '7549293812:AAFbN74rZlBVvc2KHhTytODlY9uQG60C4WY'

# Foydalanuvchi til sozlamalari
user_languages: Dict[int, str] = {}

# Til tanlash klaviaturasi
def get_language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='uz'),
            InlineKeyboardButton("🇬🇧 English", callback_data='en'),
            InlineKeyboardButton("🇷🇺 Русский", callback_data='ru')
        ]
    ])

# Foydalanuvchi savolini loglash
def log_user_interaction(user_id: int, message: str, response: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("interaction_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] User({user_id}): {message} -> Bot: {response}\n")

# Aqlli javob funksiyasi (ko‘p javobli)
def get_smart_response(message: str, lang: str = 'uz') -> str:
    message_lower = message.lower()
    responses_found = []

    if "nima qilyapsan" in message_lower or "nima qilyapsiz" in message_lower or "nima qilayapsan" in message_lower:
        return {
            'uz': "Siz yuborgan savolga mos javob topishga harakat qilyapman! 😊",
            'en': "I'm trying to find the best answer to your question! 😊",
            'ru': "Я пытаюсь найти лучший ответ на ваш вопрос! 😊"
        }.get(lang, "Savolingizni ko'rib chiqyapman.")

    for item in data['responses']:
        for keyword in item['keywords']:
            if keyword in message_lower:
                base_response = item['response']
                if lang == 'uz':
                    responses_found.append(base_response)
                else:
                    try:
                        translated = GoogleTranslator(source='uz', target=lang).translate(base_response)
                        responses_found.append(translated)
                    except Exception as e:
                        logger.warning("Tarjima xatosi: %s", e)
                        responses_found.append(base_response)
                break  # Bitta itemdan faqat bitta javob olamiz

    if responses_found:
        return "\n\n".join(responses_found)

    defaults = {
        'uz': [
            "Kechirasiz, tushunmadim. Boshqacha so'rang?",
            "Sizning savolingizga aniq javob topilmadi.",
            "Bu haqida ma'lumotim yo'q, boshqa savol bering."
        ],
        'en': [
            "Sorry, I didn't understand that. Could you rephrase?",
            "I couldn't find an exact answer to your question.",
            "I don't have info about that, try another question."
        ],
        'ru': [
            "Извините, я не понял. Можете переформулировать?",
            "Я не нашел точного ответа на ваш вопрос.",
            "У меня нет информации об этом, спросите что-то другое."
        ]
    }
    return random.choice(defaults.get(lang, defaults['uz']))

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info("/start komandasi: user_id=%d", user_id)
    msg = (
        "Assalomu alaykum! SmartBotga xush kelibsiz.\n"
        "Iltimos, o'zingizga qulay tilni tanlang:\n\n"
        "Hello! Welcome to SmartBot. Please choose your preferred language:\n\n"
        "Здравствуйте! Добро пожаловать в SmartBot. Пожалуйста, выберите язык:"
    )
    await update.message.reply_text(msg, reply_markup=get_language_keyboard())

# /help komandasi
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_languages.get(user_id, 'uz')

    helps = {
        'uz': (
            "\nYordam menyusi:\n"
            "/start - Botni qayta ishga tushirish\n"
            "/help - Yordam menyusi\n"
            "/lang - Tilni o'zgartirish\n"
            "\nSavolingizni yozing, men javob beraman."
        ),
        'en': (
            "\nHelp menu:\n"
            "/start - Restart bot\n"
            "/help - Help menu\n"
            "/lang - Change language\n"
            "\nAsk me any question, I will try to answer."
        ),
        'ru': (
            "\nМеню помощи:\n"
            "/start - Перезапуск бота\n"
            "/help - Меню помощи\n"
            "/lang - Сменить язык\n"
            "\nЗадайте вопрос, и я постараюсь ответить."
        )
    }
    await update.message.reply_text(helps.get(lang, helps['uz']))

# /lang komandasi
async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_languages.get(user_id, 'uz')
    messages = {
        'uz': "Hozirgi til: O'zbekcha. Yangi tilni tanlang:",
        'en': "Current language: English. Choose new language:",
        'ru': "Текущий язык: Русский. Выберите новый язык:"
    }
    await update.message.reply_text(messages.get(lang, messages['uz']), reply_markup=get_language_keyboard())

# Til tanlandi
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data
    user_languages[user_id] = lang

    messages = {
        'uz': "Til o'zbekcha tanlandi! Endi savolingizni yozing.",
        'en': "Language set to English! Now you can ask your question.",
        'ru': "Язык выбран русский! Теперь задавайте вопросы."
    }
    await query.edit_message_text(messages.get(lang, messages['uz']))

# Xabarlar bilan ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    lang = user_languages.get(user_id, 'uz')

    await update.message.chat.send_action(action=ChatAction.TYPING)
    response = get_smart_response(message, lang)
    await update.message.reply_text(response)
    log_user_interaction(user_id, message, response)

# Main funksiya
async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lang", change_language))
    application.add_handler(CallbackQueryHandler(language_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ishga tushdi...")
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())