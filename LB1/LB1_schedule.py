import csv
import datetime
from pathlib import Path

CSV_PATH = Path("TimeTable_18_10_2026.csv")

def parse_schedule_by_range(
        start_date: datetime.date, end_date: datetime.date
) -> list[dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Файл {CSV_PATH} не знайдено в папці проєкту")

    lessons = []

    with open(CSV_PATH, mode="r", encoding="cp1251") as f:
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

def format_schedule_message( lessons: list[dict], title: str = "Розклад") -> str:
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
            msg += f"\n <b>{day_name} ({date_str})</b>:\n"
            lesson_idx = 1
        msg += f"<b>{lesson_idx}.</b> <code>{item['time']}</code> - {item['subject']}\n"
        lesson_idx += 1

    return msg

