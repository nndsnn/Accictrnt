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
    now = datetime.datetime.now()
    today_en = now.strftime("%A")
    today_ru = days_map.get(today_en, today_en)
    today_date = now.date()
    today_str = today_date.strftime("%Y-%m-%d")

    text = f"🔔 СЕГОДНЯ ({today_ru} {today_str}):\n\n"

    # Уроки
    c.execute("SELECT * FROM lessons WHERE day=?", (today_ru,))
    lessons = c.fetchall()

    if lessons:
        text += "📚 УРОКИ:\n"
        for lesson in lessons:
            subject = lesson[1]
            start_str = lesson[2]
            end_str = lesson[3]

            # Конвертируем время
            start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.datetime.strptime(end_str, "%H:%M").time()

            lesson_start = datetime.datetime.combine(today_date, start_time)
            lesson_end = datetime.datetime.combine(today_date, end_time)

            # Простые статусы: 3 варианта
            if now < lesson_start:
                # Урок ещё не начался
                mins_left = int((lesson_start - now).total_seconds() / 60)
                status = f"⏰ Через {mins_left} мин"

            elif lesson_start <= now <= lesson_end:
                # Урок идёт сейчас
                status = f"🟢 Идёт сейчас"

            else:
                # Урок уже прошёл
                status = f"✓ Прошёл"

            text += f"• {subject}: {start_str}-{end_str}\n  {status}\n"
        text += "\n"
    else:
        text += "📚 Уроков нет\n\n"

    # ДЗ на сегодня
    c.execute("SELECT * FROM homework WHERE deadline=?", (today_str,))
    hw = c.fetchall()

    if hw:
        text += "📝 ДЗ НА СЕГОДНЯ:\n"
        for item in hw:
            text += f"• {item[1]}: {item[2]}\n"
        text += "\n"
    else:
        text += "📝 ДЗ на сегодня нет\n\n"

    # События на сегодня
    c.execute(
        "SELECT * FROM events WHERE event_date=? AND user_id=? ORDER BY event_time",
        (today_str, message.from_user.id),
    )
    events = c.fetchall()

    if events:
        text += "🎯 СОБЫТИЯ СЕГОДНЯ:\n"
        for event in events:
            title = event[1]
            event_time_str = event[3]

            event_time = datetime.datetime.strptime(event_time_str, "%H:%M").time()
            event_datetime = datetime.datetime.combine(today_date, event_time)

            # Простые статусы для событий
            if now < event_datetime:
                # Событие ещё не началось
                mins_left = int((event_datetime - now).total_seconds() / 60)
                if mins_left <= 60:
                    status = f"⏰ Через {mins_left} мин"
                else:
                    hours_left = mins_left // 60
                    status = f"⏰ Через {hours_left} ч"
            else:
                # Событие уже прошло
                status = f"✓ Прошло"

            text += f"• {title}: {event_time_str}\n  {status}\n"
    else:
        text += "🎯 Событий сегодня нет"

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
Ы

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

        # Получаем обновленные настройки
        c.execute(
            "SELECT settings, notifications FROM users WHERE user_id=?",
            (user_id,)
        )
        result = c.fetchone()

        settings = result[0].split(',') if result else ['5', '1', '1', '1']
        notifications = result[1] if result else 1

        notifications_text = "✅ ВКЛ" if notifications == 1 else "❌ ВЫКЛ"

        # Обновляем клавиатуру в том же сообщении
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

        await callback.message.edit_text(
            "⚙️ Настройки:",
            reply_markup=keyboard
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

    # Возвращаемся в главное меню настроек
    c.execute(
        "SELECT settings, notifications FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()

    settings = result[0].split(',') if result else ['5', '1', '1', '1']
    notifications = result[1] if result else 1

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

    # Возвращаемся в главное меню настроек
    c.execute(
        "SELECT settings, notifications FROM users WHERE user_id=?",
        (user_id,)
    )
    result = c.fetchone()

    settings = result[0].split(',') if result else ['5', '1', '1', '1']
    notifications = result[1] if result else 1

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

    # Возвращаемся в меню настроек событий
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

    # Возвращаемся в меню настроек событий
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
        except ValueError:
            await message.answer(
                "❌ Ошибка формата времени. Используй ЧЧ:ММ",
                reply_markup=get_keyboard()
            )
        except Exception as e:
            await message.answer(
                f"❌ Ошибка: {str(e)}",
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

# Словарь для хранения уже отправленных уведомлений
sent_notifications = {}

async def check_notifications():
    """Фоновая задача для отправки уведомлений"""
    while True:
        try:
            now = datetime.datetime.now()
            today = now.date()
            today_str = today.strftime("%Y-%m-%d")

            # Для отладки
            current_time = now.strftime('%H:%M:%S')
            print(f"[{current_time}] Проверка уведомлений...")

            days_map = {
                "Monday": "Понедельник",
                "Tuesday": "Вторник",
                "Wednesday": "Среда",
                "Thursday": "Четверг",
                "Friday": "Пятница",
                "Saturday": "Суббота",
                "Sunday": "Воскресеньe",
            }
            today_en = now.strftime("%A")
            today_ru = days_map.get(today_en, today_en)

            # Получаем только пользователей с ВКЛЮЧЕННЫМИ уведомлениями
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

                # ==================== УВЕДОМЛЕНИЯ ОБ УРОКАХ ====================
                c.execute("SELECT * FROM lessons WHERE day=?", (today_ru,))
                lessons = c.fetchall()

                for lesson in lessons:
                    subject = lesson[1]
                    start_time = lesson[2]
                    end_time = lesson[3]

                    # Создаем уникальный ключ для этого уведомления
                    lesson_key = f"{user_id}_lesson_{subject}_{start_time}"

                    # Проверяем время до начала урока
                    start_datetime = datetime.datetime.strptime(start_time, "%H:%M")
                    lesson_start = datetime.datetime.combine(today, start_datetime.time())

                    # Сколько минут осталось до урока
                    time_diff_minutes = (lesson_start - now).total_seconds() / 60

                    # ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ РОВНО ЗА N МИНУТ
                    # Проверяем, что до урока осталось БОЛЬШЕ (N-1) минут, но НЕ БОЛЬШЕ N минут
                    # Например, для 5 минут: 4 < time_diff <= 5
                    if lesson_min - 1 < time_diff_minutes <= lesson_min:
                        if lesson_key not in sent_notifications:
                            sent_notifications[lesson_key] = now

                            # Рассчитываем, через сколько минут
                            mins_display = int(time_diff_minutes) + 1 if time_diff_minutes % 1 > 0 else int(time_diff_minutes)

                            try:
                                await bot.send_message(
                                    user_id,
                                    f"🔔 УРОК через {mins_display} мин:\n"
                                    f"{subject} {start_time}-{end_time}"
                                )
                            except Exception as e:
                                print(f"Ошибка отправки уведомления об уроке: {e}")

                # ==================== УВЕДОМЛЕНИЯ О ДЗ ====================

                # ДЗ на сегодня - отправляем только в 8:00 утра
                if now.hour == 8 and now.minute == 0:
                    hw_today_key = f"{user_id}_hw_today_{today_str}"

                    if hw_today_key not in sent_notifications:
                        c.execute(
                            "SELECT * FROM homework WHERE deadline=?",
                            (today_str,)
                        )
                        hw_today = c.fetchall()

                        if hw_today:
                            hw_text = "🔥 ДЗ НА СЕГОДНЯ:\n"
                            for hw in hw_today:
                                hw_text += f"• {hw[1]}: {hw[2]}\n"

                            try:
                                await bot.send_message(user_id, hw_text)
                                sent_notifications[hw_today_key] = now
                            except Exception as e:
                                print(f"Ошибка отправки уведомления о ДЗ на сегодня: {e}")

                # ДЗ за N дней до дедлайна - отправляем только в 8:00 утра
                if hw_days > 0 and now.hour == 8 and now.minute == 0:
                    reminder_date = today + datetime.timedelta(days=hw_days)
                    reminder_str = reminder_date.strftime("%Y-%m-%d")

                    hw_reminder_key = f"{user_id}_hw_reminder_{reminder_str}"

                    if hw_reminder_key not in sent_notifications:
                        c.execute(
                            "SELECT * FROM homework WHERE deadline=?",
                            (reminder_str,)
                        )
                        hw_reminder = c.fetchall()

                        if hw_reminder:
                            hw_text = f"⏰ ДЗ через {hw_days} дн:\n"
                            for hw in hw_reminder:
                                hw_text += f"• {hw[1]}: {hw[2]}\n"

                            try:
                                await bot.send_message(user_id, hw_text)
                                sent_notifications[hw_reminder_key] = now
                            except Exception as e:
                                print(f"Ошибка отправки уведомления о ДЗ: {e}")

                # ==================== УВЕДОМЛЕНИЯ О СОБЫТИЯХ ====================

                # События за N дней - отправляем только в 9:00 утра
                if event_days > 0 and now.hour == 9 and now.minute == 0:
                    event_reminder_date = today + datetime.timedelta(days=event_days)
                    event_reminder_str = event_reminder_date.strftime("%Y-%m-%d")

                    event_days_key = f"{user_id}_event_days_{event_reminder_str}"

                    if event_days_key not in sent_notifications:
                        c.execute(
                            "SELECT * FROM events WHERE user_id=? AND event_date=?",
                            (user_id, event_reminder_str)
                        )
                        events_reminder = c.fetchall()

                        if events_reminder:
                            events_text = f"📅 Событие через {event_days} дн:\n"
                            for event in events_reminder:
                                events_text += f"• {event[1]}: {event[2]} {event[3]}\n"

                            try:
                                await bot.send_message(user_id, events_text)
                                sent_notifications[event_days_key] = now
                            except Exception as e:
                                print(f"Ошибка отправки уведомления о событиях: {e}")

                # События за N часов - проверяем все события пользователя
                if event_hours > 0:
                    c.execute(
                        "SELECT * FROM events WHERE user_id=?",
                        (user_id,)
                    )
                    all_events = c.fetchall()

                    for event in all_events:
                        event_title = event[1]
                        event_date_str = event[2]
                        event_time_str = event[3]

                        event_datetime = datetime.datetime.strptime(
                            f"{event_date_str} {event_time_str}",
                            "%Y-%m-%d %H:%M"
                        )
                        time_diff = event_datetime - now
                        hours_diff = time_diff.total_seconds() / 3600

                        # Создаем уникальный ключ для этого уведомления
                        event_hours_key = f"{user_id}_event_hours_{event_title}_{event_date_str}_{event_time_str}"

                        # Проверяем, что до события осталось примерно N часов
                        # Для 1 часа: ±5 минут
                        # Для 2+ часов: ±30 минут
                        if event_hours == 1:
                            # 55-65 минут
                            if 55/60 <= hours_diff <= 65/60 and event_hours_key not in sent_notifications:
                                sent_notifications[event_hours_key] = now
                                minutes_left = int(hours_diff * 60)
                                try:
                                    await bot.send_message(
                                        user_id,
                                        f"⏰ Событие через ~1 ч ({minutes_left} мин):\n"
                                        f"{event_title}\n"
                                        f"в {event_time_str}"
                                    )
                                except Exception as e:
                                    print(f"Ошибка отправки уведомления о событии: {e}")

                        elif event_hours > 1:
                            # N часов ±30 минут
                            if (event_hours - 0.5) <= hours_diff <= (event_hours + 0.5) and event_hours_key not in sent_notifications:
                                sent_notifications[event_hours_key] = now
                                hours_display = int(hours_diff) if hours_diff % 1 < 0.5 else int(hours_diff) + 1
                                try:
                                    await bot.send_message(
                                        user_id,
                                        f"⏰ Событие через {hours_display} ч:\n"
                                        f"{event_title}\n"
                                        f"в {event_time_str}"
                                    )
                                except Exception as e:
                                    print(f"Ошибка отправки уведомления о событии: {e}")

            # Очищаем старые записи из словаря (старше 24 часов)
            keys_to_remove = []
            for key, timestamp in sent_notifications.items():
                if (now - timestamp).total_seconds() > 86400:  # 24 часа
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del sent_notifications[key]

            # Ждем 60 секунд до следующей проверки
            await asyncio.sleep(60)

        except Exception as e:
            print(f"❌ Критическая ошибка в уведомлениях: {e}")
            await asyncio.sleep(60)


# ==================== ЗАПУСК БОТА ====================


async def main():
    print("🤖 Бот запущен!")

    # Запускаем фоновую задачу проверки уведомлений
    asyncio.create_task(check_notifications())

    # Запускаем обработку сообщений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())