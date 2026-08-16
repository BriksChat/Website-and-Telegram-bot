"""
run_bot.py — минималистичный Telegram-интерфейс проекта learenglish.

Интерфейс работает в одном редактируемом сообщении:
- системное меню Telegram содержит только команду /start;
- старая Reply-клавиатура полностью скрывается;
- после /start сразу показывается раскрытое меню;
- меню состоит из четырёх разделов в сетке 2 × 2;
- недавняя история чата очищается в пределах ограничений Telegram;
- обучение, статистика и помощь используют общий прогресс сайта и бота.
"""
import random
from urllib.parse import urlencode

from telebot import types

from bot import bot as original
from bot.api_client import bind_chat_ids


# ID текущего интерфейсного сообщения для каждого пользователя.
ui_messages = {}


# Формирует персональную ссылку на сайт с автоматической синхронизацией.
def build_synced_site_url(chat_id):
    """Возвращает URL сайта с Telegram Chat_ID в query-параметре."""
    query = urlencode({"telegram_id": str(chat_id)})
    return f"{original.SITE_URL.rstrip('/')}?{query}"


# Безопасно удаляет сообщение, не останавливая бота при ошибке Telegram.
def delete_message_safely(chat_id, message_id):
    """Пытается удалить сообщение и игнорирует ожидаемые ограничения API."""
    if not message_id:
        return
    try:
        original.bot.delete_message(chat_id, message_id)
    except Exception:
        pass


# Очищает последние сообщения перед командой /start.
def clear_recent_history(chat_id, latest_message_id, limit=100):
    """Удаляет до 100 последних сообщений, доступных боту и не старше лимита Telegram."""
    first_message_id = max(1, latest_message_id - limit + 1)
    for message_id in range(latest_message_id, first_message_id - 1, -1):
        delete_message_safely(chat_id, message_id)

    ui_messages.pop(chat_id, None)


# Принудительно скрывает старую Reply-клавиатуру под полем ввода.
def remove_reply_keyboard(chat_id):
    """Отправляет служебное сообщение с ReplyKeyboardRemove и сразу удаляет его."""
    try:
        cleanup = original.bot.send_message(
            chat_id,
            "Обновляем интерфейс…",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        delete_message_safely(chat_id, cleanup.message_id)
    except Exception:
        pass


# Отправляет новый одноэкранный интерфейс.
def send_ui(chat_id, text, keyboard, parse_mode="HTML"):
    """Удаляет предыдущий экран и отправляет новый с inline-кнопками."""
    delete_message_safely(chat_id, ui_messages.get(chat_id))
    sent = original.bot.send_message(
        chat_id,
        text,
        parse_mode=parse_mode,
        reply_markup=keyboard,
    )
    ui_messages[chat_id] = sent.message_id
    return sent


# Редактирует текущий экран вместо создания новых сообщений.
def edit_ui(chat_id, message_id, text, keyboard, parse_mode="HTML"):
    """Обновляет текст и inline-кнопки существующего сообщения."""
    try:
        original.bot.edit_message_text(
            text,
            chat_id,
            message_id,
            parse_mode=parse_mode,
            reply_markup=keyboard,
        )
        ui_messages[chat_id] = message_id
    except Exception as error:
        if "message is not modified" not in str(error).lower():
            send_ui(chat_id, text, keyboard, parse_mode=parse_mode)


# Создаёт стартовый экран после закрытия меню.
def start_keyboard():
    """Возвращает единственную кнопку повторного открытия меню."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("☰ Меню", callback_data="ui:menu"))
    return keyboard


# Создаёт раскрытое меню в две колонки и три строки.
def menu_keyboard(chat_id):
    """Возвращает сетку 2 × 2 и широкую кнопку закрытия в третьей строке."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        types.InlineKeyboardButton("🎯 Учить слова", callback_data="ui:learn"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="ui:stats"),
    )
    keyboard.row(
        types.InlineKeyboardButton("🌐 Сайт", url=build_synced_site_url(chat_id)),
        types.InlineKeyboardButton("❓ Помощь", callback_data="ui:help"),
    )
    keyboard.row(
        types.InlineKeyboardButton("✕ Закрыть меню", callback_data="ui:close")
    )
    return keyboard


# Создаёт навигацию информационных разделов.
def section_keyboard():
    """Возвращает кнопки перехода к словам и раскрытия меню."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        types.InlineKeyboardButton("← К словам", callback_data="ui:learn"),
        types.InlineKeyboardButton("☰ Меню", callback_data="ui:menu"),
    )
    return keyboard


# Загружает карточку и создаёт состояние подбора пар.
def create_learning_state(chat_id):
    """Подготавливает две независимо перемешанные колонки текущей карточки."""
    progress = original.load_progress(chat_id)
    if progress.get("finished"):
        return None

    card = original.get_card_by_id(progress["current_card"])
    if not card or not card.get("words"):
        return None

    words = card["words"]
    ru_order = list(range(len(words)))
    en_order = list(range(len(words)))
    random.shuffle(ru_order)
    random.shuffle(en_order)

    data = {
        "card_id": card["id"],
        "words": words,
        "ru_order": ru_order,
        "en_order": en_order,
        "matched": [],
        "selected_ru": None,
        "selected_en": None,
        "feedback": "",
    }
    original.set_state(chat_id, "telegram_matching", data)
    return data


# Возвращает незавершённую игровую сессию или создаёт новую.
def get_learning_state(chat_id):
    """Сохраняет состояние карточки при переходах между разделами."""
    state = original.get_state(chat_id)
    if state and state.get("state") == "telegram_matching":
        return state["data"]
    return create_learning_state(chat_id)


# Формирует текст экрана обучения.
def learning_text(data):
    """Показывает название, текущую пару и номер карточки."""
    if data is None:
        return "🏆 <b>Обучение завершено</b>\n\nВсе доступные карточки пройдены."

    matched = len(data["matched"])
    total = len(data["words"])
    text = (
        "<b>English Learning</b>\n"
        "Найди правильные пары слов\n\n"
        f"Пара <b>{min(matched + 1, total)}</b> из <b>{total}</b> · "
        f"Карточка <b>{data['card_id']}</b>"
    )
    if data.get("feedback"):
        text += f"\n\n{data['feedback']}"
    return text


# Создаёт игровую доску из двух колонок.
def learning_keyboard(data):
    """Возвращает русские и английские слова и кнопку открытия меню."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    if data is not None:
        matched = set(data["matched"])
        for ru_index, en_index in zip(data["ru_order"], data["en_order"]):
            ru_word = data["words"][ru_index]
            en_word = data["words"][en_index]

            ru_prefix = "✓ " if ru_index in matched else (
                "• " if data.get("selected_ru") == ru_index else ""
            )
            en_prefix = "✓ " if en_index in matched else (
                "• " if data.get("selected_en") == en_index else ""
            )

            keyboard.row(
                types.InlineKeyboardButton(
                    f"{ru_prefix}{ru_word['ru']}",
                    callback_data=f"ui:pair:ru:{ru_index}",
                ),
                types.InlineKeyboardButton(
                    f"{en_prefix}{en_word['en']}",
                    callback_data=f"ui:pair:en:{en_index}",
                ),
            )

    keyboard.row(types.InlineKeyboardButton("☰ Меню", callback_data="ui:menu"))
    return keyboard


# Показывает стартовый экран с одной кнопкой меню.
def show_start_screen(chat_id, message_id=None):
    """Открывает минимальный экран после закрытия раскрытого меню."""
    text = "<b>learenglish</b>"
    keyboard = start_keyboard()
    if message_id:
        edit_ui(chat_id, message_id, text, keyboard)
    else:
        send_ui(chat_id, text, keyboard)


# Показывает раскрытое меню.
def show_menu(chat_id, message_id=None):
    """Показывает сетку из четырёх разделов новым сообщением или редактированием."""
    text = "<b>Меню</b>"
    keyboard = menu_keyboard(chat_id)
    if message_id:
        edit_ui(chat_id, message_id, text, keyboard)
    else:
        send_ui(chat_id, text, keyboard)


# Показывает текущую карточку обучения.
def show_learning(chat_id, message_id=None):
    """Открывает текущую игровую сессию без сброса выбранных пар."""
    data = get_learning_state(chat_id)
    text = learning_text(data)
    keyboard = learning_keyboard(data)

    if message_id:
        edit_ui(chat_id, message_id, text, keyboard)
    else:
        send_ui(chat_id, text, keyboard)


# Показывает статистику как на сайте.
def show_statistics(chat_id, message_id):
    """Загружает правильные ответы, ошибки и точность из общего прогресса."""
    progress = original.load_progress(chat_id)
    correct = int(progress.get("total_correct", 0))
    wrong = int(progress.get("total_wrong", 0))
    total = correct + wrong
    accuracy = round(correct / total * 100) if total else 0

    edit_ui(
        chat_id,
        message_id,
        "📊 <b>Статистика</b>\n\n"
        f"Правильно: <b>{correct}</b>\n"
        f"Неправильно: <b>{wrong}</b>\n"
        f"Точность: <b>{accuracy}%</b>",
        section_keyboard(),
    )


# Показывает раздел помощи по образцу сайта.
def show_help(chat_id, message_id):
    """Объясняет обучение, синхронизацию и хранение данных."""
    edit_ui(
        chat_id,
        message_id,
        "❓ <b>Как пользоваться</b>\n\n"
        "<b>🎯 Обучение</b>\n"
        "Выберите русское слово, затем найдите его английский перевод. "
        "Правильная пара будет отмечена галочкой.\n\n"
        "<b>🔄 Синхронизация</b>\n"
        "Сайт и Telegram-бот используют общий Chat_ID и одну базу MySQL.\n\n"
        "<b>🔐 Хранение данных</b>\n"
        "Бот обращается к базе через защищённый REST API.",
        section_keyboard(),
    )


# Сохраняет завершённую карточку и переводит прогресс вперёд.
def complete_card(chat_id, data):
    """Добавляет карточку в completed_cards и открывает следующую."""
    progress = original.load_progress(chat_id)
    card_id = data["card_id"]

    if card_id not in progress["completed_cards"]:
        progress["completed_cards"].append(card_id)

    progress["current_card"] += 1
    total_cards = original.get_total_cards()
    if progress["current_card"] > total_cards:
        progress["current_card"] = total_cards
        progress["finished"] = True

    original.save_progress(chat_id, progress)
    original.clear_state(chat_id)


# Обрабатывает выбор слова в одной из двух колонок.
def handle_pair_callback(call):
    """Сравнивает пару, обновляет статистику и перерисовывает доску."""
    chat_id = call.message.chat.id
    state = original.get_state(chat_id)

    if not state or state.get("state") != "telegram_matching":
        original.bot.answer_callback_query(call.id, "Карточка обновлена")
        show_learning(chat_id, call.message.message_id)
        return

    data = state["data"]
    _, _, side, raw_index = call.data.split(":")
    index = int(raw_index)

    if index in data["matched"]:
        original.bot.answer_callback_query(call.id)
        return

    if side == "ru":
        data["selected_ru"] = index
    else:
        data["selected_en"] = index

    data["feedback"] = ""
    if data["selected_ru"] is not None and data["selected_en"] is not None:
        progress = original.load_progress(chat_id)

        if data["selected_ru"] == data["selected_en"]:
            data["matched"].append(data["selected_ru"])
            progress["total_correct"] += 1
            progress["streak"] += 1
            progress["best_streak"] = max(
                progress.get("best_streak", 0),
                progress["streak"],
            )
            data["feedback"] = "✅ Правильно"
        else:
            progress["total_wrong"] += 1
            progress["streak"] = 0
            data["feedback"] = "Попробуйте ещё раз"

        original.save_progress(chat_id, progress)
        data["selected_ru"] = None
        data["selected_en"] = None

    original.save_state_data(chat_id, data)
    original.bot.answer_callback_query(call.id)

    if len(data["matched"]) == len(data["words"]):
        complete_card(chat_id, data)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("Продолжить", callback_data="ui:learn"))
        edit_ui(
            chat_id,
            call.message.message_id,
            "🎉 <b>Карточка пройдена!</b>\n\nПрогресс сохранён.",
            keyboard,
        )
        return

    edit_ui(
        chat_id,
        call.message.message_id,
        learning_text(data),
        learning_keyboard(data),
    )


# Обрабатывает /start и возможную привязку ID сайта.
def handle_start(message):
    """Связывает ID, очищает недавний диалог и сразу показывает раскрытое меню."""
    chat_id = message.chat.id
    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""

    if payload.startswith("link_"):
        site_chat_id = payload.removeprefix("link_").strip()
        if site_chat_id.isdigit():
            try:
                bind_chat_ids(site_chat_id, str(chat_id))
            except Exception as error:
                print(f"Chat_ID link error: {error}")

    original.clear_state(chat_id)
    clear_recent_history(chat_id, message.message_id)
    remove_reply_keyboard(chat_id)
    show_menu(chat_id)


# Перенаправляет старую команду /menu на раскрытое меню.
def handle_menu_command(message):
    """Удаляет команду пользователя и сразу показывает раскрытое меню."""
    delete_message_safely(message.chat.id, message.message_id)
    remove_reply_keyboard(message.chat.id)
    show_menu(message.chat.id)


# Очищает системное меню Telegram и оставляет только /start.
def register_start_command_only():
    """Заменяет список команд бота одной командой запуска."""
    original.bot.set_my_commands([
        types.BotCommand("start", "Запустить learenglish"),
    ])


# Основной bot.py вызывает эти функции из уже зарегистрированных обработчиков.
original.handle_start = handle_start
original.handle_menu = handle_menu_command
original.main_menu_keyboard = lambda: types.ReplyKeyboardRemove()
register_start_command_only()


# Маршрутизирует все кнопки нового интерфейса.
@original.bot.callback_query_handler(func=lambda call: call.data.startswith("ui:"))
def callback_new_interface(call):
    """Открывает меню, обучение, статистику, помощь или стартовый экран."""
    action = call.data.split(":")[1]
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if action == "pair":
        handle_pair_callback(call)
        return

    original.bot.answer_callback_query(call.id)

    if action == "menu":
        show_menu(chat_id, message_id)
    elif action == "close":
        show_start_screen(chat_id, message_id)
    elif action == "learn":
        show_learning(chat_id, message_id)
    elif action == "stats":
        show_statistics(chat_id, message_id)
    elif action == "help":
        show_help(chat_id, message_id)


if __name__ == "__main__":
    print("✅ Telegram-интерфейс learenglish запущен")
    original.bot.infinity_polling()
