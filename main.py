import asyncio
import datetime
import sqlite3
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

TOKEN = "8444869672:AAECHM3QrOlvrcriSbIbzumJ32x9b6f-7_c"
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

conn = sqlite3.connect("school.db", check_same_thread=False)
c = conn.cursor()


def init_db():
    """Инициализация базы данных"""
    c.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY,
            subject TEXT,
            start TEXT,
            end TEXT,
            day TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY,
            subject TEXT,
            task TEXT,
            deadline TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            title TEXT,
            event_date TEXT,
            event_time TEXT,
            user_id INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            settings TEXT DEFAULT '5,1,1,1',
            notifications INTEGER DEFAULT 1
        )
    """)
    conn.commit()


init_db()


def get_keyboard():
    """Создание основной клавиатуры"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📅 Расписание"),
                KeyboardButton(text="➕ Урок"),
            ],
            [
                KeyboardButton(text="📚 ДЗ"),
                KeyboardButton(text="➕ ДЗ"),
            ],
            [
                KeyboardButton(text="🎯 События"),
                KeyboardButton(text="➕ Событие"),
            ],
            [
                KeyboardButton(text="🔔 Сегодня"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
    )


# ==================== ОСНОВНЫЕ КОМАНДЫ ====================


@router.message(Command("start"))
async def start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    c.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()

    c.execute(
        "SELECT notifications FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()
    notifications_status = "✅ ВКЛЮЧЕНЫ" if result and result[0] == 1 \
        else "❌ ВЫКЛЮЧЕНЫ"

    await message.answer(
        f"Привет! Я школьный помощник.\n"
        f"Уведомления: {notifications_status}\n"
        f"Используй кнопки ниже:",
        reply_markup=get_keyboard(),
    )


@router.message(F.text == "📅 Расписание")
async def show_schedule(message: types.Message):
    """Показать расписание уроков"""
    c.execute("SELECT * FROM lessons ORDER BY day, start")
    lessons = c.fetchall()

    if not lessons:
        await message.answer("Расписание пустое.")
        return

    days = {}
    for lesson in lessons:
        day = lesson[4]
        if day not in days:
            days[day] = []
        days[day].append(lesson)

    text = "📅 РАСПИСАНИЕ:\n\n"
    days_order = [
        "Понедельник", "Вторник", "Среда", "Четверг",
        "Пятница", "Суббота", "Воскресенье",
    ]

    for day in days_order:
        if day in days:
            text += f"▫️ {day} ▫️\n"
            for lesson in days[day]:
                text += f"• {lesson[1]}: {lesson[2]}-{lesson[3]}\n"
            text += "\n"

    await message.answer(text)


@router.message(F.text == "📚 ДЗ")
async def show_homework(message: types.Message):
    """Показать домашние задания"""
    c.execute("SELECT * FROM homework ORDER BY deadline")
    hw = c.fetchall()

    if not hw:
        await message.answer("ДЗ нет.")
        return

    today = datetime.date.today()
    text = "📚 ДЗ:\n\n"

    for item in hw:
        deadline = datetime.datetime.strptime(item[3], "%Y-%m-%d").date()
        days = (deadline - today).days

        if days < 0:
            status = "❌ Просрочено"
        elif days == 0:
            status = "⏰ СЕГОДНЯ!"
        elif days <= 3:
            status = f"🔥 Через {days} дн."
        else:
            status = f"📅 Через {days} дн."

        text += f"• {item[1]}: {item[2]}\n  {status}\n\n"

    await message.answer(text)


@router.message(F.text == "🎯 События")
async def show_events(message: types.Message):
    """Показать события пользователя"""
    user_id = message.from_user.id
    c.execute(
        "SELECT * FROM events WHERE user_id=? "
        "ORDER BY event_date, event_time",
        (user_id,),
    )
    events = c.fetchall()

    if not events:
        await message.answer("Событий нет.")
        return

    today = datetime.date.today()
    text = "🎯 СОБЫТИЯ:\n\n"

    for event in events:
        event_date = datetime.datetime.strptime(event[2], "%Y-%m-%d").date()
        days = (event_date - today).days

        if days < 0:
            status = "❌ Прошло"
        elif days == 0:
            status = f"⏰ Сегодня {event[3]}"
        elif days == 1:
            status = f"🔥 Завтра {event[3]}"
        else:
            status = f"📅 Через {days} дн."

        text += f"• {event[1]}\n  {event[2]} {event[3]}\n  {status}\n\n"

    await message.answer(text)


@router.message(F.text == "🔔 Сегодня")
async def today_tasks(message: types.Message):
    """Показать задачи на сегодня"""
    days_map = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }
    today_en = datetime.datetime.now().strftime("%A")
    today_ru = days_map.get(today_en, today_en)
    today_date = datetime.date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    now = datetime.datetime.now()

    text = f"🔔 СЕГОДНЯ ({today_ru}):\n\n"

    # Уроки
    c.execute("SELECT * FROM lessons WHERE day=?", (today_ru,))
    lessons = c.fetchall()
    if lessons:
        text += "📚 УРОКИ:\n"
        for lesson in lessons:
            start_time = datetime.datetime.strptime(lesson[2], "%H:%M")
            lesson_time = datetime.datetime.combine(
                today_date, start_time.time()
            )

            if lesson_time > now:
                mins = int((lesson_time - now).total_seconds() / 60)
                status = f"⏰ Через {mins} мин"
            else:
                status = "✓ Прошел"

            text += f"• {lesson[1]}: {lesson[2]}-{lesson[3]}\n  {status}\n"
        text += "\n"

    # ДЗ
    c.execute("SELECT * FROM homework WHERE deadline=?", (today_str,))
    hw = c.fetchall()
    if hw:
        text += "📝 ДЗ:\n"
        for item in hw:
            text += f"• {item[1]}: {item[2]}\n"
        text += "\n"

    # События
    c.execute(
        "SELECT * FROM events WHERE event_date=? AND user_id=?",
        (today_str, message.from_user.id),
    )
    events = c.fetchall()
    if events:
        text += "🎯 СОБЫТИЯ:\n"
        for event in events:
            event_time = datetime.datetime.strptime(event[3], "%H:%M")
            event_datetime = datetime.datetime.combine(
                today_date, event_time.time()
            )

            if event_datetime > now:
                mins = int((event_datetime - now).total_seconds() / 60)
                if mins <= 60:
                    status = f"Через {mins} мин"
                else:
                    hours = mins // 60
                    status = f"Через {hours}ч"
            else:
                status = "✓ Прошло"

            text += f"• {event[1]}: {event[3]} ({status})\n"

    if not (lessons or hw or events):
        text += "Сегодня ничего нет!"

    await message.answer(text)


# ==================== ДОБАВЛЕНИЕ ДАННЫХ ====================


@router.message(F.text == "➕ Урок")
async def add_lesson_prompt(message: types.Message):
    """Подсказка для добавления урока"""
    await message.answer(
        "Добавить урок:\n"
        "Предмет Начало Конец День\n"
        "Пример: Математика 14:30 15:15 Понедельник"
    )


@router.message(F.text == "➕ ДЗ")
async def add_hw_prompt(message: types.Message):
    """Подсказка для добавления домашнего задания"""
    await message.answer(
        "Добавить ДЗ:\n"
        "Предмет Задание Срок\n"
        "Пример: Математика Упр.5-10 2024-12-20"
    )


@router.message(F.text == "➕ Событие")
async def add_event_prompt(message: types.Message):
    """Подсказка для добавления события"""
    await message.answer(
        "Добавить событие:\n"
        "Название Дата Время\n"
        "Пример: Концерт 2024-12-25 19:00"
    )


# ==================== НАСТРОЙКИ УВЕДОМЛЕНИЙ ====================


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: types.Message):
    """Главное меню настроек"""
    user_id = message.from_user.id

    c.execute(
        "SELECT settings, notifications FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()

    if result:
        settings = result[0].split(',')
        notifications = result[1]
    else:
        settings = ['5', '1', '1', '1']
        notifications = 1

    notifications_text = "✅ ВКЛ" if notifications == 1 else "❌ ВЫКЛ"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📚 Уроки: {settings[0]} мин",
                    callback_data="set_lesson"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"📝 ДЗ: {settings[1]} дн.",
                    callback_data="set_hw"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 События: {settings[2]} дн. {settings[3]} ч.",
                    callback_data="set_event"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🔔 Уведомления: {notifications_text}",
                    callback_data="toggle_notifications"
                ),
            ],
        ]
    )

    await message.answer("⚙️ Настройки:", reply_markup=keyboard)


@router.callback_query(F.data == "set_lesson")
async def set_lesson_menu(callback: types.CallbackQuery):
    """Меню настроек уроков"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="5 мин", callback_data="lesson_5")],
            [InlineKeyboardButton(text="10 мин", callback_data="lesson_10")],
            [InlineKeyboardButton(text="15 мин", callback_data="lesson_15")],
            [InlineKeyboardButton(text="30 мин", callback_data="lesson_30")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="back_settings"
            )],
        ]
    )
    await callback.message.edit_text(
        "За сколько минут напоминать об уроках?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "set_hw")
async def set_hw_menu(callback: types.CallbackQuery):
    """Меню настроек ДЗ"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 день", callback_data="hw_1")],
            [InlineKeyboardButton(text="2 дня", callback_data="hw_2")],
            [InlineKeyboardButton(text="3 дня", callback_data="hw_3")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="back_settings"
            )],
        ]
    )
    await callback.message.edit_text(
        "За сколько дней напоминать о ДЗ?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "set_event")
async def set_event_menu(callback: types.CallbackQuery):
    """Меню настроек событий"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Дни", callback_data="event_days_menu"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Часы", callback_data="event_hours_menu"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="back_settings"
                ),
            ],
        ]
    )
    await callback.message.edit_text(
        "Настройки событий:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "event_days_menu")
async def event_days_menu(callback: types.CallbackQuery):
    """Настройка дней для событий"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 день", callback_data="event_days_1")],
            [InlineKeyboardButton(text="2 дня", callback_data="event_days_2")],
            [InlineKeyboardButton(text="3 дня", callback_data="event_days_3")],
            [InlineKeyboardButton(text="0 дней", callback_data="event_days_0")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="set_event"
            )],
        ]
    )
    await callback.message.edit_text(
        "За сколько дней напоминать?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "event_hours_menu")
async def event_hours_menu(callback: types.CallbackQuery):
    """Настройка часов для событий"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 час", callback_data="event_hours_1")],
            [InlineKeyboardButton(text="2 часа", callback_data="event_hours_2")],
            [InlineKeyboardButton(text="3 часа", callback_data="event_hours_3")],
            [InlineKeyboardButton(text="0 часов", callback_data="event_hours_0")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="set_event"
            )],
        ]
    )
    await callback.message.edit_text(
        "За сколько часов напоминать?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: types.CallbackQuery):
    """Переключение уведомлений вкл/выкл"""
    user_id = callback.from_user.id

    c.execute(
        "SELECT notifications FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()

    if result:
        current = result[0]
        new = 0 if current == 1 else 1

        c.execute(
            "UPDATE users SET notifications=? WHERE user_id=?",
            (new, user_id)
        )
        conn.commit()

        status = "✅ ВКЛЮЧЕНЫ" if new == 1 else "❌ ВЫКЛЮЧЕНЫ"
        await callback.message.edit_text(f"Уведомления: {status}")
        await callback.message.answer(
            "Настройки сохранены!",
            reply_markup=get_keyboard()
        )

    await callback.answer()


@router.callback_query(F.data == "back_settings")
async def back_settings(callback: types.CallbackQuery):
    """Возврат в главное меню настроек"""
    user_id = callback.from_user.id

    c.execute(
        "SELECT settings, notifications FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()

    if result:
        settings = result[0].split(',')
        notifications = result[1]
    else:
        settings = ['5', '1', '1', '1']
        notifications = 1

    notifications_text = "✅ ВКЛ" if notifications == 1 else "❌ ВЫКЛ"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📚 Уроки: {settings[0]} мин",
                    callback_data="set_lesson"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"📝 ДЗ: {settings[1]} дн.",
                    callback_data="set_hw"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 События: {settings[2]} дн. {settings[3]} ч.",
                    callback_data="set_event"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🔔 Уведомления: {notifications_text}",
                    callback_data="toggle_notifications"
                ),
            ],
        ]
    )

    await callback.message.edit_text("⚙️ Настройки:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("lesson_"))
async def save_lesson(callback: types.CallbackQuery):
    """Сохранение настройки уроков"""
    user_id = callback.from_user.id
    minutes = callback.data.replace("lesson_", "")

    c.execute(
        "SELECT settings FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()
    settings = result[0].split(',') if result else ['5', '1', '1', '1']

    settings[0] = minutes
    new_settings = ','.join(settings)

    c.execute(
        "UPDATE users SET settings=? WHERE user_id=?",
        (new_settings, user_id)
    )
    conn.commit()

    await callback.message.edit_text(f"✅ Уроки: {minutes} мин")
    await callback.message.answer(
        "Настройки сохранены!",
        reply_markup=get_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hw_"))
async def save_hw(callback: types.CallbackQuery):
    """Сохранение настройки ДЗ"""
    user_id = callback.from_user.id
    days = callback.data.replace("hw_", "")

    c.execute(
        "SELECT settings FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()
    settings = result[0].split(',') if result else ['5', '1', '1', '1']

    settings[1] = days
    new_settings = ','.join(settings)

    c.execute(
        "UPDATE users SET settings=? WHERE user_id=?",
        (new_settings, user_id)
    )
    conn.commit()

    await callback.message.edit_text(f"✅ ДЗ: {days} дн.")
    await callback.message.answer(
        "Настройки сохранены!",
        reply_markup=get_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event_days_"))
async def save_event_days(callback: types.CallbackQuery):
    """Сохранение настройки дней для событий"""
    user_id = callback.from_user.id
    days = callback.data.replace("event_days_", "")

    c.execute(
        "SELECT settings FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()
    settings = result[0].split(',') if result else ['5', '1', '1', '1']

    settings[2] = days
    new_settings = ','.join(settings)

    c.execute(
        "UPDATE users SET settings=? WHERE user_id=?",
        (new_settings, user_id)
    )
    conn.commit()

    await callback.message.edit_text(f"✅ События: {days} дн.")
    await callback.message.answer(
        "Настройки сохранены!",
        reply_markup=get_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event_hours_"))
async def save_event_hours(callback: types.CallbackQuery):
    """Сохранение настройки часов для событий"""
    user_id = callback.from_user.id
    hours = callback.data.replace("event_hours_", "")

    c.execute(
        "SELECT settings FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()
    settings = result[0].split(',') if result else ['5', '1', '1', '1']

    settings[3] = hours
    new_settings = ','.join(settings)

    c.execute(
        "UPDATE users SET settings=? WHERE user_id=?",
        (new_settings, user_id)
    )
    conn.commit()

    await callback.message.edit_text(f"✅ События: {hours} ч.")
    await callback.message.answer(
        "Настройки сохранены!",
        reply_markup=get_keyboard()
    )
    await callback.answer()


# ==================== ОБРАБОТКА ВВОДА ДАННЫХ ====================


@router.message()
async def handle_input(message: types.Message):
    """Обработка всех текстовых сообщений"""
    text = message.text.strip()
    parts = text.split()

    if len(parts) == 4:  # Урок
        try:
            subject, start, end, day = parts
            datetime.datetime.strptime(start, "%H:%M")
            datetime.datetime.strptime(end, "%H:%M")

            c.execute(
                "INSERT INTO lessons (subject, start, end, day) "
                "VALUES (?, ?, ?, ?)",
                (subject, start, end, day)
            )
            conn.commit()
            await message.answer(
                f"✅ Урок: {subject} {start}-{end} {day}",
                reply_markup=get_keyboard()
            )
        except ValueError as en:
            await message.answer(
                "❌ Ошибка формата времени. Используй ЧЧ:ММ",
                reply_markup=get_keyboard()
            )
        except Exception as en:
            await message.answer(
                f"❌ Ошибка: {str(en)}",
                reply_markup=get_keyboard()
            )

    elif len(parts) == 3:  # ДЗ или событие
        try:
            # Пробуем как ДЗ
            datetime.datetime.strptime(parts[2], "%Y-%m-%d")
            subject, task, deadline = parts

            c.execute(
                "INSERT INTO homework (subject, task, deadline) "
                "VALUES (?, ?, ?)",
                (subject, task, deadline)
            )
            conn.commit()
            await message.answer(
                f"✅ ДЗ: {subject} - {task} до {deadline}",
                reply_markup=get_keyboard()
            )
        except ValueError:
            # Пробуем как событие
            try:
                title, date_str, time_str = parts
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
                datetime.datetime.strptime(time_str, "%H:%M")

                c.execute(
                    """INSERT INTO events
                       (title, event_date, event_time, user_id)
                       VALUES (?, ?, ?, ?)""",
                    (title, date_str, time_str, message.from_user.id)
                )
                conn.commit()
                await message.answer(
                    f"✅ Событие: {title} {date_str} {time_str}",
                    reply_markup=get_keyboard()
                )
            except ValueError:
                await message.answer(
                    "❌ Ошибка. Примеры:\n"
                    "ДЗ: Математика Упр.5-10 2024-12-20\n"
                    "Событие: Концерт 2024-12-25 19:00",
                    reply_markup=get_keyboard()
                )
            except Exception as e:
                await message.answer(
                    f"❌ Ошибка добавления события: {str(e)}",
                    reply_markup=get_keyboard()
                )
        except Exception as e:
            await message.answer(
                f"❌ Ошибка добавления ДЗ: {str(e)}",
                reply_markup=get_keyboard()
            )

    else:
        await message.answer(
            "Не понял. Используй кнопки.",
            reply_markup=get_keyboard()
        )


# ==================== СИСТЕМА УВЕДОМЛЕНИЙ ====================


async def check_notifications():
    """Фоновая задача для отправки уведомлений"""
    while True:
        try:
            now = datetime.datetime.now()
            today = now.date()
            today_str = today.strftime("%Y-%m-%d")

            days_map = {
                "Monday": "Понедельник",
                "Tuesday": "Вторник",
                "Wednesday": "Среда",
                "Thursday": "Четверг",
                "Friday": "Пятница",
                "Saturday": "Суббота",
                "Sunday": "Воскресенье",
            }
            today_en = now.strftime("%A")
            today_ru = days_map.get(today_en, today_en)

            # Получаем только пользователей с включенными уведомлениями
            c.execute(
                "SELECT user_id, settings FROM users WHERE notifications=1"
            )
            users = c.fetchall()

            for user_id, settings_str in users:
                settings = settings_str.split(',')
                lesson_min = int(settings[0])
                hw_days = int(settings[1])
                event_days = int(settings[2])
                event_hours = int(settings[3])

                # Уроки
                c.execute("SELECT * FROM lessons WHERE day=?", (today_ru,))
                lessons = c.fetchall()

                for lesson in lessons:
                    start_time = datetime.datetime.strptime(
                        lesson[2], "%H:%M"
                    )
                    lesson_datetime = datetime.datetime.combine(
                        today, start_time.time()
                    )
                    time_diff = (lesson_datetime - now).total_seconds() / 60

                    if 0 < time_diff <= lesson_min:
                        try:
                            await bot.send_message(
                                user_id,
                                f"🔔 УРОК через {int(time_diff)} мин: "
                                f"{lesson[1]} {lesson[2]}-{lesson[3]}"
                            )
                        except Exception as e:
                            print(f"Ошибка отправки уведомления об уроке: {e}")

                # ДЗ за N дней
                if hw_days > 0:
                    reminder_date = today + datetime.timedelta(days=hw_days)
                    reminder_str = reminder_date.strftime("%Y-%m-%d")

                    c.execute(
                        "SELECT * FROM homework WHERE deadline=?",
                        (reminder_str,)
                    )
                    hw_list = c.fetchall()

                    for hw in hw_list:
                        try:
                            await bot.send_message(
                                user_id,
                                f"⏰ ДЗ через {hw_days} дн: "
                                f"{hw[1]} - {hw[2]}"
                            )
                        except Exception as e:
                            print(f"Ошибка отправки уведомления о ДЗ: {e}")

                # ДЗ на сегодня
                c.execute(
                    "SELECT * FROM homework WHERE deadline=?",
                    (today_str,)
                )
                hw_today = c.fetchall()

                for hw in hw_today:
                    try:
                        await bot.send_message(
                            user_id,
                            f"🔥 ДЗ СЕГОДНЯ: {hw[1]} - {hw[2]}"
                        )
                    except Exception as e:
                        print(f"Ошибка отправки уведомления о ДЗ сегодня: {e}")

                # События
                c.execute(
                    "SELECT * FROM events WHERE user_id=?",
                    (user_id,)
                )
                events = c.fetchall()

                for event in events:
                    event_date_str = event[2]
                    event_time_str = event[3]

                    event_datetime = datetime.datetime.strptime(
                        f"{event_date_str} {event_time_str}",
                        "%Y-%m-%d %H:%M"
                    )
                    time_diff = event_datetime - now

                    # За N дней
                    if event_days > 0:
                        if (time_diff.days == event_days and
                                time_diff.total_seconds() > 0):
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"📅 Событие через {event_days} дн: "
                                    f"{event[1]} {event[2]} {event[3]}"
                                )
                            except Exception as e:
                                msg = f"Ошибка отправки уведомления о событии: {e}"
                                print(msg)

                    # За N часов
                    if event_hours > 0:
                        event_date = datetime.datetime.strptime(
                            event_date_str, "%Y-%m-%d"
                        ).date()
                        hours_diff = time_diff.total_seconds() / 3600

                        if (event_date == today and
                                event_hours - 0.1 <= hours_diff <=
                                event_hours + 0.1):
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"⏰ Событие через {event_hours} ч: "
                                    f"{event[1]} {event[3]}"
                                )
                            except Exception as e:
                                msg = f"Ошибка отправки уведомления о событии: {e}"
                                print(msg)

            await asyncio.sleep(60)

        except Exception as e:
            print(f"Критическая ошибка в уведомлениях: {e}")
            await asyncio.sleep(60)


# ==================== ЗАПУСК БОТА ====================


async def main():
    """Основная функция запуска бота"""
    print("🤖 Бот запущен!")
    asyncio.create_task(check_notifications())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
