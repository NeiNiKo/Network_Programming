import datetime
import logging
import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
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
            InlineKeyboardButton("наступний тиждень", callback_data="next_week"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>Вітаю шановне панство</b>\n\n"
        "Це бот для перегляду розкладу занять.\n"
        "Оберіть період, за котрий хочетье переглянути розклад:"
    )
    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=get_main_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    today = datetime.date.today()
    data = query.data
    lessons = []
    title = ""

    if data == "today":
        title = f"Рокзлад на сьогодні ({today.strftime('%d.%m.%Y')})"
        lessons = parse_schedule_by_range(today, today)
    elif data == "tomorrow":
        tomorrow = today + datetime.timedelta(days=1)
        title = f"Рокзлад на завтра ({tomorrow.strftime('%d.%m.%Y')})"
        lessons = parse_schedule_by_range(tomorrow, tomorrow)
    elif data == "this_week":
        monday = today - datetime.timedelta(days=today.weekday())
        sunday = monday + datetime.timedelta(days=6)
        title = f"Рокзлад на поточний тиждень ({monday.strftime('%d.%m')} - {sunday.strftime('%d.%m')})"
        lessons = parse_schedule_by_range(monday, sunday)
    elif data == "next_week":
        next_monday = today + datetime.timedelta(days=7 - today.weekday())
        next_sunday = next_monday + datetime.timedelta(days=6)
        title = f"Розклад на наступний тиждень ({next_monday.strftime('%d.%m')} = {next_sunday.strftime('%d.%m')})"
        lessons = parse_schedule_by_range(next_monday, next_sunday)

    result_text = format_schedule_message(lessons, title)

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
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Бот готовий працювати на пана")
    app.run_polling()

if __name__ == "__main__":
    main()


