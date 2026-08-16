"""Dictionary interface for Telegram with shared and personal words."""
from math import ceil

from telebot import types

from bot import api_client
from bot import run_bot as interface

PAGE_SIZE = 8


def dictionary_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📚 Общий словарь", callback_data="dict:common:1"),
        types.InlineKeyboardButton("🔎 Найти слово", callback_data="dict:search"),
        types.InlineKeyboardButton("📝 Мои слова", callback_data="dict:personal:1"),
        types.InlineKeyboardButton("➕ Добавить своё слово", callback_data="dict:add"),
        types.InlineKeyboardButton("☰ Меню", callback_data="ui:menu"),
    )
    return keyboard


def show_dictionary_menu(chat_id, message_id=None):
    text = (
        "📖 <b>Словарь</b>\n\n"
        "Здесь можно просматривать общий словарь, искать слова, "
        "а также добавлять, изменять и удалять свои слова."
    )
    if message_id:
        interface.edit_ui(chat_id, message_id, text, dictionary_menu_keyboard())
    else:
        interface.send_ui(chat_id, text, dictionary_menu_keyboard())


def _common_words():
    result = []
    for card in api_client.load_words().get("cards", []):
        if card.get("id") == 99:
            continue
        for word in card.get("words", []):
            result.append({
                "card_id": card.get("id"),
                "en": word.get("en", ""),
                "ru": word.get("ru", ""),
            })
    return result


def _render_common(chat_id, message_id, page=1, search=""):
    words = _common_words()
    if search:
        needle = search.casefold()
        words = [
            item for item in words
            if needle in item["en"].casefold() or needle in item["ru"].casefold()
        ]

    total_pages = max(1, ceil(len(words) / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    items = words[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    title = "🔎 <b>Результаты поиска</b>" if search else "📚 <b>Общий словарь</b>"
    lines = [title, ""]
    if search:
        lines.append(f"Запрос: <b>{search}</b>")
        lines.append("")
    if items:
        for item in items:
            lines.append(f"<b>{item['en']}</b> — {item['ru']}  <i>({item['card_id']})</i>")
    else:
        lines.append("Слова не найдены.")
    lines.append("")
    lines.append(f"Страница {page} из {total_pages} · Найдено: {len(words)}")

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    nav = []
    base = "dict:common" if not search else "dict:searchpage"
    if page > 1:
        nav.append(types.InlineKeyboardButton("← Назад", callback_data=f"{base}:{page - 1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("Далее →", callback_data=f"{base}:{page + 1}"))
    if nav:
        keyboard.row(*nav)
    keyboard.row(
        types.InlineKeyboardButton("🔎 Поиск", callback_data="dict:search"),
        types.InlineKeyboardButton("← Словарь", callback_data="dict:open"),
    )
    interface.edit_ui(chat_id, message_id, "\n".join(lines), keyboard)


def _personal_page(chat_id, page=1):
    return api_client.list_custom_words(chat_id, page=page, per_page=PAGE_SIZE)


def _render_personal(chat_id, message_id, page=1):
    data = _personal_page(chat_id, page)
    items = data.get("items", [])
    page = data.get("page", 1)
    total_pages = data.get("total_pages", 1)

    lines = ["📝 <b>Мои слова</b>", ""]
    if items:
        for item in items:
            lines.append(f"<b>{item['en']}</b> — {item['ru']}")
    else:
        lines.append("У вас пока нет своих слов.")
    lines.append("")
    lines.append(f"Страница {page} из {total_pages} · Всего: {data.get('total', 0)}")

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for item in items:
        keyboard.row(
            types.InlineKeyboardButton(
                f"✏️ {item['en'][:18]}",
                callback_data=f"dict:edit:{item['id']}",
            ),
            types.InlineKeyboardButton(
                "🗑 Удалить",
                callback_data=f"dict:delete:{item['id']}:{page}",
            ),
        )
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("← Назад", callback_data=f"dict:personal:{page - 1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("Далее →", callback_data=f"dict:personal:{page + 1}"))
    if nav:
        keyboard.row(*nav)
    keyboard.row(
        types.InlineKeyboardButton("➕ Добавить", callback_data="dict:add"),
        types.InlineKeyboardButton("← Словарь", callback_data="dict:open"),
    )
    interface.edit_ui(chat_id, message_id, "\n".join(lines), keyboard)


def _find_personal_word(chat_id, word_id):
    page = 1
    while True:
        data = _personal_page(chat_id, page)
        for item in data.get("items", []):
            if int(item["id"]) == int(word_id):
                return item
        if page >= data.get("total_pages", 1):
            return None
        page += 1


def _prompt(chat_id, state_name, text, data=None):
    interface.original.set_state(chat_id, state_name, data or {})
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Отмена", callback_data="dict:open"))
    interface.send_ui(chat_id, text, keyboard)


def _parse_pair(text):
    if "," not in text:
        raise ValueError("Используйте формат: английское слово, перевод")
    en_word, ru_word = [part.strip() for part in text.split(",", 1)]
    if not en_word or not ru_word:
        raise ValueError("Заполните английское слово и перевод")
    return en_word, ru_word


previous_handle_message = interface.original.handle_message


def handle_dictionary_message(message):
    chat_id = message.chat.id
    state = interface.original.get_state(chat_id)
    if not state or not str(state.get("state", "")).startswith("dict_"):
        previous_handle_message(message)
        return

    text = (message.text or "").strip()
    interface.delete_message_safely(chat_id, message.message_id)

    try:
        if state["state"] == "dict_search":
            interface.original.clear_state(chat_id)
            interface.original.set_state(chat_id, "dict_search_results", {"query": text})
            sent = interface.send_ui(chat_id, "Поиск…", dictionary_menu_keyboard())
            _render_common(chat_id, sent.message_id, page=1, search=text)
            return

        if state["state"] == "dict_add":
            en_word, ru_word = _parse_pair(text)
            api_client.add_custom_word(chat_id, en_word, ru_word)
            interface.original.clear_state(chat_id)
            sent = interface.send_ui(chat_id, "✅ Слово добавлено", dictionary_menu_keyboard())
            _render_personal(chat_id, sent.message_id, page=1)
            return

        if state["state"] == "dict_edit":
            en_word, ru_word = _parse_pair(text)
            word_id = state.get("data", {}).get("word_id")
            api_client.update_custom_word(chat_id, word_id, en_word, ru_word)
            interface.original.clear_state(chat_id)
            sent = interface.send_ui(chat_id, "✅ Слово изменено", dictionary_menu_keyboard())
            _render_personal(chat_id, sent.message_id, page=1)
            return
    except Exception as error:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("Отмена", callback_data="dict:open"))
        interface.send_ui(chat_id, f"❌ {error}\n\nПопробуйте ещё раз.", keyboard)


interface.original.handle_message = handle_dictionary_message


@interface.original.bot.callback_query_handler(func=lambda call: call.data.startswith("dict:"))
def callback_dictionary(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    parts = call.data.split(":")
    action = parts[1]

    interface.original.bot.answer_callback_query(call.id)

    if action == "open":
        interface.original.clear_state(chat_id)
        show_dictionary_menu(chat_id, message_id)
    elif action == "common":
        interface.original.clear_state(chat_id)
        _render_common(chat_id, message_id, page=int(parts[2]))
    elif action == "search":
        _prompt(chat_id, "dict_search", "🔎 <b>Поиск слова</b>\n\nВведите английское слово или русский перевод.")
    elif action == "searchpage":
        state = interface.original.get_state(chat_id) or {}
        query = state.get("data", {}).get("query", "")
        _render_common(chat_id, message_id, page=int(parts[2]), search=query)
    elif action == "personal":
        interface.original.clear_state(chat_id)
        _render_personal(chat_id, message_id, page=int(parts[2]))
    elif action == "add":
        _prompt(
            chat_id,
            "dict_add",
            "➕ <b>Добавить своё слово</b>\n\n"
            "Введите английское слово и перевод через запятую.\n"
            "Пример: <code>apple, яблоко</code>",
        )
    elif action == "edit":
        word_id = int(parts[2])
        item = _find_personal_word(chat_id, word_id)
        if item is None:
            show_dictionary_menu(chat_id, message_id)
            return
        _prompt(
            chat_id,
            "dict_edit",
            "✏️ <b>Изменить слово</b>\n\n"
            f"Сейчас: <b>{item['en']}</b> — {item['ru']}\n\n"
            "Введите новое английское слово и перевод через запятую.",
            {"word_id": word_id},
        )
    elif action == "delete":
        word_id = int(parts[2])
        page = int(parts[3])
        api_client.delete_custom_word(chat_id, word_id)
        _render_personal(chat_id, message_id, page=page)
