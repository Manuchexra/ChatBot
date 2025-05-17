import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)
from database import Database
from datetime import datetime
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import os

# --- Konfiguratsiya ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7549293812:AAFbN74rZlBVvc2KHhTytODlY9uQG60C4WY"
ADMIN_IDS = [8041813332]  # Admin ID larini shu yerga yozing
DEFAULT_LANGUAGE = 'uz'
LANGUAGES = {
    'uz': "O'zbekcha",
    'ru': "Русский",
    'en': "English"
}

# --- Holatlar (ConversationHandler uchun) ---
LANGUAGE, ADMIN_MENU, ADD_QUESTION, ADD_ANSWER, CONFIRM_ADD = range(5)

# --- Logging sozlash ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Database obyektini yaratish ---
db = Database("knowledge_bot.db")

# --- Asosiy funksiyalar ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni ishga tushirish"""
    user = update.effective_user
    db.add_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_admin=(user.id in ADMIN_IDS))
    
    welcome_msg = (
        f"Salom, {user.first_name}!\n"
        "Men - aqlli yordamchi botman. Quyidagi buyruqlar orqali menga murojaat qilishingiz mumkin:\n\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam olish\n"
        "/language - Tilni o'zgartirish\n"
        "/quiz - Viktorina o'ynash\n"
        "/stats - Shaxsiy statistika\n"
        "/favorites - Sevimli savollar\n\n"
        "Shuningdek, siz menga har qanday savol yuborishingiz mumkin va men sizga javob berishga harakat qilaman!"
    )
    
    await update.message.reply_text(welcome_msg)
    db.log_action(user.id, "start")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam menyusini ko'rsatish"""
    help_text = (
        "📚 Yordam menyusi:\n\n"
        "/start - Botni qayta ishga tushirish\n"
        "/help - Yordam olish\n"
        "/language - Tilni o'zgartirish\n"
        "/quiz - Bilimingizni sinab ko'ring\n"
        "/stats - Shaxsiy statistika\n"
        "/favorites - Sevimli savollar\n"
        "/admin - Admin paneli (faqat adminlar uchun)\n\n"
        "Shuningdek, siz menga har qanday savol yuborishingiz mumkin va men sizga javob berishga harakat qilaman!"
    )
    await update.message.reply_text(help_text)
    db.log_action(update.effective_user.id, "help")

# --- Tilni o'zgartirish ---
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tilni tanlash menyusini ko'rsatish"""
    keyboard = [
        [InlineKeyboardButton(LANGUAGES['uz'], callback_data='uz')],
        [InlineKeyboardButton(LANGUAGES['ru'], callback_data='ru')],
        [InlineKeyboardButton(LANGUAGES['en'], callback_data='en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Iltimos, tilni tanlang:\nПожалуйста, выберите язык:\nPlease select language:",
        reply_markup=reply_markup
    )
    db.log_action(update.effective_user.id, "language_change_started")
    return LANGUAGE

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tanlangan tilni saqlash"""
    query = update.callback_query
    await query.answer()
    
    language = query.data
    user_id = query.from_user.id
    db.update_user_language(user_id, language)
    
    # Tanlangan tilga qarab javob berish
    messages = {
        'uz': "Til muvaffaqiyatli o'zgartirildi!",
        'ru': "Язык успешно изменен!",
        'en': "Language changed successfully!"
    }
    
    await query.edit_message_text(text=messages[language])
    db.log_action(user_id, "language_changed", details=f"new_lang:{language}")
    return ConversationHandler.END

# --- Viktorina rejimi ---
async def quiz_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Viktorina savolini yuborish"""
    user = update.effective_user
    question_data = db.get_random_question(db.get_user(user.id)['language'])
    
    if not question_data:
        await update.message.reply_text("Hozircha savollar mavjud emas. Iltimos, keyinroq urinib ko'ring.")
        return
    
    context.user_data['quiz_data'] = {
        'question_id': question_data['id'],
        'answer': question_data['answer']
    }
    
    keyboard = [
        [InlineKeyboardButton("🔄 Keyingi savol", callback_data='next_question')],
        [InlineKeyboardButton("📝 Javobni ko'rsatish", callback_data='show_answer')],
        [InlineKeyboardButton("❤️ Saqlash", callback_data='add_favorite')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"❓ Savol: {question_data['question']}",
        reply_markup=reply_markup
    )
    db.log_action(user.id, "quiz_started")

async def quiz_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Viktorina tugmalarini boshqarish"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    action = query.data
    quiz_data = context.user_data.get('quiz_data', {})
    
    if action == 'next_question':
        db.log_action(user_id, "quiz_next_question")
        await query.delete_message()
        await quiz_mode(update, context)
    
    elif action == 'show_answer':
        answer = quiz_data.get('answer', "Javob topilmadi")
        await query.edit_message_text(
            text=f"❓ Savol: {query.message.text}\n\n💡 Javob: {answer}",
            reply_markup=query.message.reply_markup
        )
        db.log_action(user_id, "quiz_answer_shown")
    
    elif action == 'add_favorite':
        if db.add_to_favorites(user_id, quiz_data['question_id']):
            await query.answer("✅ Savol sevimlilarga qo'shildi!")
            db.log_action(user_id, "quiz_added_to_favorites")
        else:
            await query.answer("⚠️ Bu savol allaqachon sevimlilarda bor")

# --- Foydalanuvchi statistikasi ---
async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi statistikasini ko'rsatish"""
    user = update.effective_user
    stats = db.get_user_stats(user.id)
    
    stats_text = (
        f"📊 <b>{user.first_name} statistikasi:</b>\n\n"
        f"📝 Qo'shilgan savollar: {stats['questions_added']}\n"
        f"👀 Jami ko'rishlar: {stats['total_views']}\n"
        f"❤️ Sevimlilar soni: {stats['favorites_count']}\n\n"
        "<i>Harakatlar tarixi:</i>\n"
    )
    
    for action, count in stats['actions'].items():
        stats_text += f"• {action}: {count}\n"
    
    await update.message.reply_text(stats_text, parse_mode='HTML')
    db.log_action(user.id, "viewed_stats")

# --- Sevimli savollar ---
async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining sevimli savollarini ko'rsatish"""
    user = update.effective_user
    favorites = db.get_user_favorites(user.id)
    
    if not favorites:
        await update.message.reply_text("Sizda hali sevimli savollar mavjud emas.")
        return
    
    for fav in favorites[:10]:  # Eng oxirgi 10 ta savol
        keyboard = [
            [InlineKeyboardButton("❌ O'chirish", callback_data=f"remove_fav_{fav['id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❓ {fav['question']}\n\n💡 {fav['answer']}",
            reply_markup=reply_markup
        )
    
    db.log_action(user.id, "viewed_favorites")

async def favorite_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sevimlilar tugmalarini boshqarish"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('remove_fav_'):
        question_id = int(query.data.split('_')[2])
        user_id = query.from_user.id
        
        if db.remove_from_favorites(user_id, question_id):
            await query.edit_message_text(
                text=query.message.text + "\n\n✅ Savol sevimlilardan olib tashlandi",
                reply_markup=None
            )
            db.log_action(user_id, "removed_from_favorites", details=f"question:{question_id}")

# --- Admin paneli ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panelini ko'rsatish"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Sizga ruxsat berilmagan!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📥 Ma'lumotlarni yuklab olish", callback_data='export_data')],
        [InlineKeyboardButton("➕ Yangi savol qo'shish", callback_data='add_question')],
        [InlineKeyboardButton("📊 Umumiy statistika", callback_data='full_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("👑 Admin paneli:", reply_markup=reply_markup)
    db.log_action(user.id, "admin_panel_opened")
    return ADMIN_MENU

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin paneli tugmalarini boshqarish"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_id = query.from_user.id
    
    if action == 'export_data':
        try:
            db.export_to_csv("exports")
            await query.message.reply_document(document=open('exports/knowledge.csv', 'rb'))
            await query.message.reply_document(document=open('exports/users.csv', 'rb'))
            await query.message.reply_document(document=open('exports/statistics.csv', 'rb'))
            db.log_action(user_id, "data_exported")
        except Exception as e:
            await query.message.reply_text(f"Xatolik yuz berdi: {str(e)}")
            logger.error(f"Export error: {str(e)}")
    
    elif action == 'add_question':
        await query.message.reply_text("Yangi savolni yuboring:")
        db.log_action(user_id, "started_adding_question")
        return ADD_QUESTION
    
    elif action == 'full_stats':
        stats = db.get_full_stats()
        await query.message.reply_text(
            f"📊 <b>Umumiy statistika:</b>\n\n"
            f"👥 Foydalanuvchilar: {stats['total_users']}\n"
            f"📚 Savollar: {stats['total_questions']}\n"
            f"👀 Ko'rishlar: {stats['total_views']}\n"
            f"❤️ Sevimlilar: {stats['total_favorites']}",
            parse_mode='HTML'
        )
        db.log_action(user_id, "viewed_full_stats")

async def add_question_step1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi savol qo'shish - 1-qadam"""
    context.user_data['new_question'] = update.message.text
    await update.message.reply_text("Endi bu savolga javobni yuboring:")
    db.log_action(update.effective_user.id, "added_question_text", details=update.message.text[:50])
    return ADD_ANSWER

async def add_question_step2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi savol qo'shish - 2-qadam"""
    context.user_data['new_answer'] = update.message.text
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("✅ Saqlash", callback_data='confirm_add')],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data='cancel_add')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🆕 Yangi savol:\n\n"
        f"❓ {context.user_data['new_question']}\n\n"
        f"💡 {context.user_data['new_answer']}\n\n"
        f"Yuqoridagi ma'lumotlarni saqlaymizmi?",
        reply_markup=reply_markup
    )
    db.log_action(user.id, "added_answer_text", details=update.message.text[:50])
    return CONFIRM_ADD

async def confirm_add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi savolni tasdiqlash"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    action = query.data
    
    if action == 'confirm_add':
        question_id = db.add_knowledge(
            question=context.user_data['new_question'],
            answer=context.user_data['new_answer'],
            author_id=user.id
        )
        await query.edit_message_text("✅ Savol muvaffaqiyatli qo'shildi!")
        db.log_action(user.id, "question_added", details=f"question_id:{question_id}")
    else:
        await query.edit_message_text("❌ Savol qo'shish bekor qilindi.")
        db.log_action(user.id, "question_add_cancelled")
    
    return ConversationHandler.END

# --- Xabarlarni qayta ishlash ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi xabarlarini qayta ishlash"""
    user = update.effective_user
    message = update.message.text
    
    # Avvalo, foydalanuvchi ma'lumotlarini yangilaymiz
    db.add_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_admin=(user.id in ADMIN_IDS))
    
    # Ma'lumotlar bazasidan qidirish
    user_lang = db.get_user(user.id)['language']
    results = db.search_knowledge(message, language=user_lang)
    
    if results:
        # Eng yaxshi 3 ta natijani yuboramiz
        for result in results[:3]:
            keyboard = [
                [InlineKeyboardButton("❤️ Saqlash", callback_data=f"fav_{result['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"❓ {result['question']}\n\n💡 {result['answer']}",
                reply_markup=reply_markup
            )
        db.log_action(user.id, "search_success", details=f"query:{message[:50]}")
    else:
        await update.message.reply_text("Afsuski, siz so'ragan mavzu bo'yicha ma'lumot topilmadi.")
        db.log_action(user.id, "search_failed", details=f"query:{message[:50]}")

async def message_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabarlardagi tugmalarni boshqarish"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('fav_'):
        question_id = int(query.data.split('_')[1])
        user_id = query.from_user.id
        
        if db.add_to_favorites(user_id, question_id):
            await query.answer("✅ Savol sevimlilarga qo'shildi!")
            db.log_action(user_id, "added_to_favorites", details=f"question:{question_id}")
        else:
            await query.answer("⚠️ Bu savol allaqachon sevimlilarda bor")

# --- Xatoliklar bilan ishlash ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botdagi xatoliklarni qayta ishlash"""
    logger.error(msg="Botda xatolik yuz berdi:", exc_info=context.error)
    
    if update.effective_message:
        await update.effective_message.reply_text(
            "Kechirasiz, botda texnik nosozlik yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )
    
    # Xatolikni log qilish
    if update.effective_user:
        db.log_action(
            update.effective_user.id,
            "error_occurred",
            details=str(context.error)[:200]
        )

# --- Asosiy dastur ---
def main():
    """Botni ishga tushirish"""
    application = Application.builder().token(TOKEN).build()
    
    # ConversationHandler til o'zgartirish uchun
    conv_language = ConversationHandler(
        entry_points=[CommandHandler('language', set_language)],
        states={
            LANGUAGE: [CallbackQueryHandler(language_chosen)]
        },
        fallbacks=[]
    )
    
    # ConversationHandler admin paneli uchun
    conv_admin = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_panel)],
        states={
            ADMIN_MENU: [CallbackQueryHandler(admin_button_handler)],
            ADD_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_step1)],
            ADD_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_step2)],
            CONFIRM_ADD: [CallbackQueryHandler(confirm_add_question)]
        },
        fallbacks=[]
    )
    
    # Command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stats', user_stats))
    application.add_handler(CommandHandler('favorites', show_favorites))
    application.add_handler(CommandHandler('quiz', quiz_mode))
    application.add_handler(conv_language)
    application.add_handler(conv_admin)
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(quiz_button_handler, pattern='^(next_question|show_answer|add_favorite)$'))
    application.add_handler(CallbackQueryHandler(favorite_button_handler, pattern='^remove_fav_'))
    application.add_handler(CallbackQueryHandler(message_button_handler, pattern='^fav_'))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    application.run_polling()

if __name__ == '__main__':
    main()