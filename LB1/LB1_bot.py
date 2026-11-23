import datetime
import logging
import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes, CallbackQueryHandler,
)
from LB1_schedule import format_schedule_message, parse_schedule_by_range

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,)
load_dotenv()
TOKEN = os.getenv("TOKEN")

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Сьогодні", callback_data="today"),
            InlineKeyboardButton("Завтра", callback_data="tomorrow"),
        ],
        [
            InlineKeyboardButton("Цей тиждень", callback_data="this_week"),
            InlineKeyboardButton("Наступний тиждень", callback_data="next_week"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    text = (
        "<b>Вітаю шановне панство</b>\n"
        "Це бот для перегляду розкладу занять.\n"
        "Оберіть період, за котрий хочете переглянути розклад:\n\n"
        "Також можете обрати режим відображення тексту розкладу, доступні наступні варіанти:\n"
        "/normal - текст за замовчуванням\n"
        "/whisper - текст малими літерами\n"
        "/scream - текст великими літерами"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())

async def whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if update.message is None:
        return
    if user_data is None:
        return
    user_data["text_mode"] = "whisper"
    await update.message.reply_text("Режим whisper увімкнено.\nНазви дисциплін відображаються малими літерами.")

async def scream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if update.message is None:
        return
    if user_data is None:
        return
    user_data["text_mode"] = "scream"
    await update.message.reply_text("Режим scream увімкнено.\nНазви дисциплін відображаються великими літерами.")

async def normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if update.message is None:
        return
    if user_data is None:
        return
    user_data["text_mode"] = "normal"
    await update.message.reply_text("Режим normal увімкнено.\nНазви дисциплін відображаються в оригіналі.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    if not isinstance(query.message, Message):
        return
    today = datetime.date.today()
    data = query.data
    if data == "today":
        title = f"Розклад на сьогодні ({today.strftime('%d.%m.%Y')})"
        lessons = parse_schedule_by_range(today, today)
    elif data == "tomorrow":
        tomorrow = today + datetime.timedelta(days=1)
        title = f"Розклад на завтра ({tomorrow.strftime('%d.%m.%Y')})"
        lessons = parse_schedule_by_range(tomorrow, tomorrow)
    elif data == "this_week":
        monday = today - datetime.timedelta(days=today.weekday())
        sunday = monday + datetime.timedelta(days=6)
        title = f"Розклад на поточний тиждень ({monday.strftime('%d.%m')} - {sunday.strftime('%d.%m')})"
        lessons = parse_schedule_by_range(monday, sunday)
    elif data == "next_week":
        next_monday = today + datetime.timedelta(days=7 - today.weekday())
        next_sunday = next_monday + datetime.timedelta(days=6)
        title = f"Розклад на наступний тиждень ({next_monday.strftime('%d.%m')} - {next_sunday.strftime('%d.%m')})"
        lessons = parse_schedule_by_range(next_monday, next_sunday)
    else:
        await query.message.reply_text("Невідома команда")
        return
    user_data = context.user_data
    text_mode = (
        user_data.get("text_mode", "normal")
        if user_data is not None
        else "normal"
    )
    result_text = format_schedule_message(lessons, title, text_mode)
    try:
        await query.message.edit_text(result_text, parse_mode="HTML", reply_markup=get_main_keyboard())
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

def main():
    if not TOKEN:
        raise ValueError("Токен не знайдено")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("whisper", whisper))
    app.add_handler(CommandHandler("scream", scream))
    app.add_handler(CommandHandler("normal", normal))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Бот готовий працювати на пана")
    app.run_polling()

if __name__ == "__main__":
    main()
