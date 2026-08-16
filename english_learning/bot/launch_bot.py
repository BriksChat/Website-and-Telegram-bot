"""
launch_bot.py — настройка стартового экрана Telegram-интерфейса LearEnglish.

Основной интерфейс находится в run_bot.py. Этот модуль меняет стартовый
сценарий и компоновку меню:
- после /start сразу открывается меню;
- все пункты меню расположены в один столбец;
- после «✕ Закрыть меню» показывается краткое описание проекта.
"""
from telebot import types

from bot import run_bot as interface
from bot import telegram_dictionary


# Создаёт вертикальное меню из шести полноширинных строк.
def vertical_menu_keyboard(chat_id):
    """Возвращает каждый пункт меню на отдельной строке."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🎯 Учить слова", callback_data="ui:learn"),
        types.InlineKeyboardButton("📖 Словарь", callback_data="dict:open"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="ui:stats"),
        types.InlineKeyboardButton(
            "🌐 Сайт",
            url=interface.build_synced_site_url(chat_id),
        ),
        types.InlineKeyboardButton("❓ Помощь", callback_data="ui:help"),
        types.InlineKeyboardButton("✕ Закрыть меню", callback_data="ui:close"),
    )
    return keyboard


# Показывает описание проекта после закрытия раскрытого меню.
def show_project_description(chat_id, message_id=None):
    """Объясняет назначение LearEnglish и оставляет кнопку возврата в меню."""
    text = (
        "<b>LearEnglish</b>\n\n"
        "Сервис для изучения английских слов через сайт и Telegram-бота "
        "с единым прогрессом. Цель проекта — сделать обучение простым, "
        "понятным и доступным с любого устройства."
    )
    keyboard = interface.start_keyboard()

    if message_id:
        interface.edit_ui(chat_id, message_id, text, keyboard)
    else:
        interface.send_ui(chat_id, text, keyboard)


# Обрабатывает /start без удаления предыдущего диалога.
def handle_start_with_open_menu(message):
    """Связывает ID, скрывает Reply-клавиатуру и сразу открывает меню."""
    chat_id = message.chat.id
    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""

    if payload.startswith("link_"):
        site_chat_id = payload.removeprefix("link_").strip()
        if site_chat_id.isdigit():
            try:
                interface.bind_chat_ids(site_chat_id, str(chat_id))
            except Exception as error:
                print(f"Chat_ID link error: {error}")

    # Удаляем только команду /start, не затрагивая историю переписки.
    interface.delete_message_safely(chat_id, message.message_id)
    interface.original.clear_state(chat_id)
    interface.remove_reply_keyboard(chat_id)
    interface.show_menu(chat_id)


# run_bot использует эти функции по глобальным именам во время выполнения.
interface.menu_keyboard = vertical_menu_keyboard
interface.show_start_screen = show_project_description
interface.original.handle_start = handle_start_with_open_menu


if __name__ == "__main__":
    print("✅ Telegram-интерфейс LearEnglish запущен")
    interface.original.bot.infinity_polling()
