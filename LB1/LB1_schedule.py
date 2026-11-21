import csv
import datetime
from pathlib import Path

CSV_PATH = Path("TimeTable_20_11_2026.csv")

LESSON_COLORS = {"Лк": "🟠", "Пз": "🟢","Лб": "🟣","Зал": "🟡","Екз": "🔴","Конс": "🔵"}

def get_lesson_color(subject: str) -> str:
    for lesson_type, color in LESSON_COLORS.items():
        if lesson_type in subject.split():
            return color
    return "⚪"

def parse_schedule_by_range(start_date: datetime.date, end_date: datetime.date) -> list[dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Файл {CSV_PATH} не знайдено в папці проєкту")

    lessons = []

    with open(CSV_PATH, mode="r", encoding="cp1251", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            date_str = row.get("Дата начала")
            if not date_str:
                continue

            try:
                lesson_date = datetime.datetime.strptime(
                    date_str.strip(), "%d.%m.%Y"
                ).date()
            except ValueError:
                continue

            if start_date <= lesson_date <= end_date:
                start_time = row.get("Время начала", "")[:5]
                end_time = row.get("Время завершения","")[:5]
                subject = row.get("Тема", "").strip()
                if not subject or not start_time or not end_time:
                    continue
                lessons.append(
                    {
                        "date": lesson_date,
                        "start_time": start_time,
                        "end_time": end_time,
                        "time": f"{start_time} - {end_time}",
                        "subject": subject,
                    }
                )
    lessons.sort(key=lambda x: (x["date"], x["start_time"]))
    return lessons

def format_schedule_message( lessons: list[dict], title: str = "Розклад", text_mode: str = "normal") -> str:
    if not lessons:
        return f"<b>{title}</b>\n\n Занять немає"
    msg = f"<b>{title}</b>\n\n"
    current_date = None
    lesson_idx = 1
    for item in lessons:
        if item["date"] != current_date:
            current_date = item["date"]
            day_name = current_date.strftime("%A")
            date_str = current_date.strftime("%d.%m.%Y")
            msg += f"\n<b>{day_name} ({date_str})</b>\n"
            lesson_idx = 1
        color = get_lesson_color(item["subject"])
        subject = item["subject"]
        if text_mode == "whisper":
            subject = subject.lower()
        elif text_mode == "scream":
            subject = subject.upper()
        msg += f"<b>{lesson_idx}.</b> <code>{item['time']}</code> {color} {subject}\n"
        lesson_idx += 1
    return msg.strip()

