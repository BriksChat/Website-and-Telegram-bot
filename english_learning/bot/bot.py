"""
bot.py — Telegram-бот для проекта English Learning.

Предоставляет пользователю интерфейс для изучения английских существительных:
    - главное меню с кнопками
    - единственный игровой режим: "Выбор из 4 вариантов"
    - просмотр всех слов по карточкам (компактный вид с пагинацией)
    - добавление своих слов (в виртуальную карточку №99)
    - статистика индивидуального прогресса
    - показ chat_id для синхронизации с сайтом

Прогресс хранится в общей MySQL и доступен боту только через REST API.
Сайт использует тот же API, поэтому изменения синхронизируются.
"""
import telebot
from telebot import types
import random
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
import sys

# ==================== Добавляем корень проекта в sys.path ====================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bot.api_client import (
    load_words,
    get_total_cards,
    load_progress,
    save_progress,
    add_hard_word,
    add_custom_word,
)

# ==================== Инициализация бота ====================
# Токен хранится только в закрытой переменной окружения Amvera.
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "YOUR_BOT_USERNAME")
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")
bot = telebot.TeleBot(TOKEN)

# Состояния пользователя (FSM)
user_states = {}


# ==================== Работа с состояниями (FSM) ====================
def set_state(chat_id, state, data=None):
    """
    Устанавливает состояние пользователя (FSM).

    :param chat_id: int — ID чата Telegram
    :param state: str — название состояния
    :param data: dict — дополнительные данные для состояния
    """
    user_states[chat_id] = {"state": state, "data": data or {}}


def get_state(chat_id):
    """
    Возвращает текущее состояние пользователя.

    :param chat_id: int — ID чата Telegram
    :return: dict или None — текущее состояние
    """
    return user_states.get(chat_id)


def clear_state(chat_id):
    """
    Очищает состояние пользователя.

    :param chat_id: int — ID чата Telegram
    """
    if chat_id in user_states:
        del user_states[chat_id]


def save_state_data(chat_id, data):
    """
    Сохраняет обновлённые данные состояния.

    :param chat_id: int — ID чата
    :param data: dict — обновлённые данные
    """
    state = get_state(chat_id)
    if state:
        state["data"] = data
        user_states[chat_id] = state


# ==================== Клавиатуры ====================
def main_menu_keyboard():
    """
    Создаёт клавиатуру главного меню.
    Содержит кнопки: Учить слова, Все слова, Моя статистика,
    Мой Chat_ID, Перейти на сайт, Помощь.

    :return: ReplyKeyboardMarkup — клавиатура с основными кнопками
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🎯 Учить слова"),
        types.KeyboardButton("📖 Все слова"),
    )
    keyboard.add(
        types.KeyboardButton("📊 Моя статистика"),
        types.KeyboardButton("🔑 Мой Chat_ID"),
    )
    keyboard.add(
        types.KeyboardButton("🌐 Открыть сайт", web_app=types.WebAppInfo(url=SITE_URL)),
        types.KeyboardButton("❓ Помощь"),
    )
    return keyboard


def back_to_menu_keyboard():
    """
    Создаёт клавиатуру с кнопкой возврата в меню.

    :return: ReplyKeyboardMarkup — клавиатура с одной кнопкой
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("🔙 Назад в меню"))
    return keyboard


def answer_options_keyboard(options):
    """
    Создаёт inline-клавиатуру с вариантами ответа (4 кнопки).

    :param options: list — список вариантов ответа (должно быть 4)
    :return: InlineKeyboardMarkup — клавиатура с кнопками вариантов
    """
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=opt, callback_data=f"ans:{opt}") for opt in options]
    keyboard.add(*buttons)
    return keyboard


# ==================== Команды ====================
def register_commands(bot_instance):
    """
    Регистрирует команды бота в меню Telegram.

    :param bot_instance: TeleBot — экземпляр бота
    """
    bot_instance.set_my_commands([
        types.BotCommand("start", "🚀 Запустить бота"),
        types.BotCommand("help", "❓ Помощь"),
        types.BotCommand("menu", "🏠 Главное меню"),
        types.BotCommand("chatid", "🔑 Мой Chat_ID"),
    ])


# ==================== Обработчики команд ====================
def handle_start(message):
    """
    Обработчик команды /start.
    Приветствует пользователя, показывает его chat_id и главное меню.

    :param message: Message — сообщение от пользователя
    """
    chat_id = message.chat.id
    clear_state(chat_id)
    progress = load_progress(chat_id)

    bot.send_message(
        chat_id,
        "👋 <b>Привет! Добро пожаловать в English Learning!</b>\n\n"
        "📚 Здесь ты выучишь 300 самых популярных английских существительных.\n"
        "Каждый день — новая карточка из 10 слов.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>Ваш Chat_ID для синхронизации телеграм-бота с сайтом:</b>\n\n"
        f"<code>{chat_id}</code>\n\n"
        "💡 <i>Скопируй этот номер и укажи его на сайте через кнопку с карандашом — "
        "тогда прогресс в боте и на сайте будет общим!</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )

    if progress["finished"]:
        bot.send_message(
            chat_id,
            "🎉 Поздравляем! Ты прошёл все 30 карточек и выучил 300 существительных!\n\n"
            "Ты настоящий мастер английского! 🏆",
            reply_markup=main_menu_keyboard(),
        )
        return

    bot.send_message(
        chat_id,
        f"📍 Сейчас карточка №{progress['current_card']} из {get_total_cards()}\n\n"
        "Выбери действие в меню ниже 👇",
        reply_markup=main_menu_keyboard(),
    )


def handle_help(message):
    """
    Обработчик команды /help и кнопки "Помощь".

    :param message: Message — сообщение от пользователя
    """
    help_text = (
        "📚 <b>Помощь по English Learning</b>\n\n"
        "🎯 <b>Учить слова</b> — изучай текущую карточку из 10 слов "
        "в режиме выбора из 4 вариантов.\n\n"
        "📖 <b>Все слова</b> — посмотри весь список из 300 существительных "
        "по карточкам. Здесь же можно добавить своё слово.\n\n"
        "📊 <b>Моя статистика</b> — узнай свой прогресс: точность, серия, сложные слова.\n\n"
        "🔑 <b>Мой Chat_ID</b> — покажет твой уникальный номер для синхронизации с сайтом.\n\n"
        "❓ <b>Помощь</b> — ты здесь 😊\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌐 <b>Что такое Chat_ID и зачем он нужен?</b>\n\n"
        "<b>Chat_ID</b> — это твой уникальный номер в Telegram. "
        "Он нужен для <b>синхронизации прогресса</b> между ботом и сайтом.\n\n"
        "📌 <b>Как синхронизировать бота и сайт:</b>\n"
        "1️⃣ Нажми кнопку <b>'🔑 Мой Chat_ID'</b> в боте\n"
        "2️⃣ Скопируй номер (долгое нажатие на сообщение)\n"
        f'3️⃣ Открой сайт <a href="{SITE_URL}">{SITE_URL}</a>\n'
        "4️⃣ Нажми карандаш рядом с Chat_ID и введи этот номер\n"
        "5️⃣ Готово! Теперь прогресс в боте и на сайте — общий ✅\n\n"
        "💡 <i>Без синхронизации бот и сайт работают как два разных пользователя.</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


def handle_menu(message):
    """
    Обработчик команды /menu.

    :param message: Message — сообщение от пользователя
    """
    clear_state(message.chat.id)
    bot.send_message(
        message.chat.id,
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard(),
    )


def handle_show_chat_id(message):
    """
    Обработчик кнопки '🔑 Мой Chat_ID'.

    :param message: Message — сообщение от пользователя
    """
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>Ваш Chat_ID для синхронизации телеграм-бота с сайтом:</b>\n\n"
        f"<code>{chat_id}</code>\n\n"
        "💡 <i>Скопируй этот номер и укажи его на сайте через кнопку с карандашом.</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


# ==================== Главное меню ====================
def handle_main_menu(message):
    """
    Обработчик кнопок главного меню.

    :param message: Message — сообщение от пользователя
    """
    text = message.text
    chat_id = message.chat.id

    if text == "🎯 Учить слова":
        progress = load_progress(chat_id)
        if progress["finished"]:
            bot.send_message(
                chat_id,
                "🏆 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
                "Ты прошёл все 30 карточек и выучил 300 существительных!\n"
                "Ты настоящий мастер английского! 🎓\n\n"
                "Можешь повторять слова через '📖 Все слова' или "
                "добавлять свои через тот же раздел.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
            return

        card = get_card_by_id(progress["current_card"])
        start_mode_choice(chat_id, card)

    elif text == "📖 Все слова":
        show_all_words_menu(chat_id, page=0)

    elif text == "📊 Моя статистика":
        show_statistics(chat_id)

    elif text == "🔑 Мой Chat_ID":
        handle_show_chat_id(message)

    elif text == "❓ Помощь":
        handle_help(message)

    elif text == "🔙 Назад в меню":
        handle_menu(message)


# ==================== Вспомогательные функции ====================
def get_card_by_id(card_id):
    """
    Возвращает карточку по её ID.

    :param card_id: int — номер карточки (1-30 или 99)
    :return: dict или None — карточка со словами
    """
    words_data = load_words()
    for card in words_data["cards"]:
        if card["id"] == card_id:
            return card
    return None


# ==================== Режим: Выбор из 4 вариантов ====================
def start_mode_choice(chat_id, card):
    """
    Запускает режим "Выбор из 4 вариантов".

    :param chat_id: int — ID чата
    :param card: dict — текущая карточка со словами
    """
    words = card["words"]
    set_state(chat_id, "mode_choice", {
        "words": words,
        "current_index": 0,
        "correct_in_session": 0,
        "wrong_in_session": 0,
    })
    show_choice_question(chat_id)


def show_choice_question(chat_id):
    """
    Показывает вопрос в режиме "Выбор из 4 вариантов".

    :param chat_id: int — ID чата
    """
    state = get_state(chat_id)
    data = state["data"]
    words = data["words"]
    idx = data["current_index"]

    if idx >= len(words):
        finish_session(chat_id)
        return

    current_word = words[idx]
    correct_answer = current_word["ru"]

    all_words = load_words()
    all_ru = []
    for c in all_words["cards"]:
        for w in c["words"]:
            if w["ru"] != correct_answer:
                all_ru.append(w["ru"])

    wrong_options = random.sample(all_ru, min(3, len(all_ru)))
    options = [correct_answer] + wrong_options
    random.shuffle(options)

    data["correct_answer"] = correct_answer
    data["current_en"] = current_word["en"]
    save_state_data(chat_id, data)

    bot.send_message(
        chat_id,
        f"🎯 Вопрос {idx + 1} из {len(words)}\n\n"
        f"Как переводится слово: <b>{current_word['en']}</b>?",
        parse_mode="HTML",
        reply_markup=answer_options_keyboard(options),
    )


def handle_choice_answer(call):
    """
    Обработчик ответа в режиме "Выбор из 4 вариантов".

    :param call: CallbackQuery — нажатие inline-кнопки
    """
    chat_id = call.message.chat.id
    state = get_state(chat_id)

    if not state or state["state"] != "mode_choice":
        bot.answer_callback_query(call.id, "⏳ Сессия завершена")
        return

    data = state["data"]
    user_answer = call.data.replace("ans:", "")
    correct_answer = data["correct_answer"]

    progress = load_progress(chat_id)

    if user_answer == correct_answer:
        data["correct_in_session"] += 1
        progress["total_correct"] += 1
        progress["streak"] += 1
        if progress["streak"] > progress["best_streak"]:
            progress["best_streak"] = progress["streak"]
        save_progress(chat_id, progress)
        bot.answer_callback_query(call.id, "✅ Верно!")
        bot.send_message(chat_id, f"✅ Правильно! <b>{correct_answer}</b>", parse_mode="HTML")
    else:
        data["wrong_in_session"] += 1
        progress["total_wrong"] += 1
        progress["streak"] = 0
        add_hard_word(chat_id, data["current_en"])
        save_progress(chat_id, progress)
        bot.answer_callback_query(call.id, "❌ Неверно")
        bot.send_message(
            chat_id,
            f"❌ Неверно!\nПравильный ответ: <b>{correct_answer}</b>",
            parse_mode="HTML",
        )

    data["current_index"] += 1
    save_state_data(chat_id, data)
    show_choice_question(chat_id)


def finish_session(chat_id):
    """
    Завершает игровую сессию.

    :param chat_id: int — ID чата
    """
    state = get_state(chat_id)
    data = state["data"]
    correct = data["correct_in_session"]
    wrong = data["wrong_in_session"]
    total = correct + wrong

    progress = load_progress(chat_id)
    if progress["current_card"] not in progress["completed_cards"]:
        progress["completed_cards"].append(progress["current_card"])

    progress["current_card"] += 1
    if progress["current_card"] > 30:
        progress["finished"] = True
        progress["current_card"] = 30

    save_progress(chat_id, progress)

    message = (
        f"🎉 Сессия завершена!\n\n"
        f"✅ Правильных: {correct}\n"
        f"❌ Ошибок: {wrong}\n"
        f"📊 Точность: {round(correct / total * 100) if total > 0 else 0}%\n\n"
        f"🔥 Текущая серия: {progress['streak']}\n\n"
    )

    if progress["finished"]:
        message += (
            "🏆 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
            "Ты прошёл все 30 карточек и выучил 300 существительных!\n"
            "Ты настоящий мастер английского! 🎓"
        )
    else:
        message += (
            f"✅ <b>Карточка завершена!</b>\n"
            f"📅 Завтра тебя ждёт карточка №{progress['current_card']}"
        )

    bot.send_message(
        chat_id,
        message,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    clear_state(chat_id)


# ==================== Все слова (пагинация) ====================
def show_all_words_menu(chat_id, page):
    """
    Показывает компактное меню всех карточек с пагинацией.

    :param chat_id: int — ID чата
    :param page: int — номер страницы (начинается с 0)
    """
    words_data = load_words()
    progress = load_progress(chat_id)
    cards = [c for c in words_data["cards"] if c["id"] != 99]

    total_pages = (len(cards) + 5) // 6
    page = max(0, min(page, total_pages - 1))

    start = page * 6
    end = start + 6
    page_cards = cards[start:end]

    kb = types.InlineKeyboardMarkup(row_width=3)

    for c in page_cards:
        status = "✅" if c["id"] in progress["completed_cards"] else "⬜"
        current = " 👈" if c["id"] == progress["current_card"] else ""
        label = f"{c['id']}. {status}{current}"
        kb.add(types.InlineKeyboardButton(label, callback_data=f"card:{c['id']}"))

    kb.add(types.InlineKeyboardButton("➕ Добавить слово", callback_data="add_word"))

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"words_page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"words_page:{page + 1}"))
    if nav:
        kb.add(*nav)

    bot.send_message(
        chat_id,
        f"📖 <b>Все карточки</b> (стр. {page + 1} из {total_pages})\n\n"
        f"Нажми на номер карточки, чтобы увидеть 10 слов.",
        parse_mode="HTML",
        reply_markup=kb,
    )


def show_card_words(chat_id, card_id):
    """
    Показывает 10 слов выбранной карточки.

    :param chat_id: int — номер карточки
    """
    card = get_card_by_id(card_id)
    if not card:
        return

    text = f"📂 <b>Карточка {card_id}</b>\n\n"
    for i, word in enumerate(card["words"], 1):
        text += f"{i}. <b>{word['en']}</b> — {word['ru']}\n"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Назад к списку", callback_data="words_page:0"))

    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)


# ==================== Статистика ====================
def show_statistics(chat_id):
    """
    Показывает индивидуальную статистику пользователя.

    :param chat_id: int — ID чата
    """
    progress = load_progress(chat_id)
    total = progress["total_correct"] + progress["total_wrong"]
    accuracy = round(progress["total_correct"] / total * 100) if total > 0 else 0

    if total < 50:
        level = "🌱 Новичок"
    elif total < 150:
        level = "📚 Ученик"
    elif total < 300:
        level = "💪 Знаток"
    elif total < 500:
        level = "🎓 Эксперт"
    else:
        level = "👑 Мастер"

    hard_words_str = ", ".join(progress["hard_words"][:10]) if progress["hard_words"] else "—"

    text = (
        f"📊 <b>Моя статистика</b>\n\n"
        f"🎯 Уровень: <b>{level}</b>\n\n"
        f"📍 Текущая карточка: <b>{progress['current_card']}</b> из {get_total_cards()}\n"
        f"✅ Пройдено карточек: <b>{len(progress['completed_cards'])}</b>\n\n"
        f"✅ Правильных ответов: <b>{progress['total_correct']}</b>\n"
        f"❌ Ошибок: <b>{progress['total_wrong']}</b>\n"
        f"📊 Точность: <b>{accuracy}%</b>\n\n"
        f"🔥 Текущая серия: <b>{progress['streak']}</b>\n"
        f"🏆 Лучшая серия: <b>{progress['best_streak']}</b>\n\n"
        f"📚 Сложных слов: <b>{len(progress['hard_words'])}</b>\n"
        f"📝 Своих слов: <b>{len(progress['custom_words'])}</b>\n\n"
        f"🔴 <b>Сложные слова:</b>\n{hard_words_str}"
    )

    bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


# ==================== Добавление своего слова ====================
def handle_add_word_input(message):
    """
    Обработчик добавления пользовательского слова.

    :param message: Message — сообщение от пользователя
    """
    chat_id = message.chat.id
    text = message.text.strip()

    if "," not in text:
        bot.send_message(
            chat_id,
            "❗ Используй формат: <code>слово, перевод</code>\n"
            "Пример: <code>apple, яблоко</code>",
            parse_mode="HTML",
        )
        return

    parts = text.split(",", 1)
    en_word = parts[0].strip()
    ru_word = parts[1].strip()

    if not en_word or not ru_word:
        bot.send_message(chat_id, "❗ Заполни оба поля!")
        return

    add_custom_word(chat_id, en_word, ru_word)
    bot.send_message(
        chat_id,
        f"✅ Слово добавлено!\n"
        f"<b>{en_word}</b> — <b>{ru_word}</b>\n\n"
        f"Оно появится в разделе '📖 Все слова' → '📦 Добавленные слова'.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    clear_state(chat_id)


# ==================== Callback-обработчики ====================
def handle_words_callback(call):
    """
    Обработчик inline-кнопок в разделе "Все слова".

    :param call: CallbackQuery — нажатие inline-кнопки
    """
    chat_id = call.message.chat.id

    if call.data.startswith("words_page:"):
        page = int(call.data.split(":")[1])
        show_all_words_menu(chat_id, page)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("card:"):
        card_id = int(call.data.split(":")[1])
        show_card_words(chat_id, card_id)
        bot.answer_callback_query(call.id)

    elif call.data == "add_word":
        bot.send_message(
            chat_id,
            "✍️ Введи слово на английском, а затем через запятую — перевод на русском.\n\n"
            "Пример: <code>apple, яблоко</code>\n\n"
            "Или нажми '🔙 Назад в меню' для отмены.",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
        set_state(chat_id, "add_word")
        bot.answer_callback_query(call.id)


# ==================== Главный обработчик сообщений ====================
def handle_message(message):
    """
    Главный обработчик всех текстовых сообщений.

    :param message: Message — сообщение от пользователя
    """
    chat_id = message.chat.id
    state = get_state(chat_id)

    if state:
        state_name = state["state"]
        if state_name == "add_word":
            handle_add_word_input(message)
        return

    handle_main_menu(message)


# ==================== Регистрация обработчиков ====================
register_commands(bot)


@bot.message_handler(commands=["start"])
def cmd_start(message):
    handle_start(message)


@bot.message_handler(commands=["help"])
def cmd_help(message):
    handle_help(message)


@bot.message_handler(commands=["menu"])
def cmd_menu(message):
    handle_menu(message)


@bot.message_handler(commands=["chatid"])
def cmd_chatid(message):
    handle_show_chat_id(message)


@bot.callback_query_handler(func=lambda call: call.data.startswith("ans:"))
def callback_choice(call):
    handle_choice_answer(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith(("words_page:", "card:")) or call.data == "add_word")
def callback_words(call):
    handle_words_callback(call)


@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    handle_message(message)


# ==================== Запуск бота ====================
if __name__ == "__main__":
    print("=" * 50)
    print(f"🤖 Telegram-бот @{BOT_USERNAME}")
    print("=" * 50)
    print("✅ Бот запущен!")
    print("📡 Ожидание сообщений...")

    # Сворачиваем окно  бота в панель задаач
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)
    except Exception:
        pass

    bot.infinity_polling()
