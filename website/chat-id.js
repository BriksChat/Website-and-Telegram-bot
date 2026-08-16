/*
 * chat-id.js — идентификация пользователя и синхронизация сайта с Telegram.
 *
 * Отвечает за:
 * - получение Telegram ID из URL или Telegram Web App;
 * - создание гостевого числового Chat_ID;
 * - сохранение выбранного ID в localStorage;
 * - формирование deep link для привязки сайта к Telegram-боту;
 * - ручную смену Chat_ID пользователем.
 *
 * Зависимости:
 * - Telegram Web App SDK (необязательно, используется при запуске внутри Telegram);
 * - script.js: глобальная переменная chat_id и функция loadProgress();
 * - config.js: TELEGRAM_BOT_URL.
 *
 * Подключается после script.js и перед ui.js.
 */
(function initialiseNumericChatId() {
  function generateNumericChatId() {
    return String(Math.floor(10000000 + Math.random() * 90000000));
  }

  function isNumericChatId(value) {
    return /^\d{5,20}$/.test(String(value || '').trim());
  }

  function getTelegramIdFromUrl() {
    const value = new URLSearchParams(window.location.search).get('telegram_id');
    return isNumericChatId(value) ? value : '';
  }

  function getTelegramIdFromWebApp() {
    const value = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    return isNumericChatId(value) ? String(value) : '';
  }

  function applyChatId(value) {
    chat_id = String(value);
    localStorage.setItem('chat_id', chat_id);

    const element = document.getElementById('currentChatId');
    if (element) element.textContent = chat_id;

    if (typeof loadProgress === 'function') {
      loadProgress();
    }
  }

  const urlTelegramId = getTelegramIdFromUrl();
  const webAppTelegramId = getTelegramIdFromWebApp();
  const savedChatId = localStorage.getItem('chat_id') || '';

  // Приоритет: ID из ссылки бота → Telegram Web App → сохранённый ID → новый гостевой ID.
  const resolvedChatId = urlTelegramId || webAppTelegramId ||
    (isNumericChatId(savedChatId) ? savedChatId : generateNumericChatId());

  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
  }

  applyChatId(resolvedChatId);

  // Убираем telegram_id из адресной строки после сохранения.
  if (urlTelegramId && window.history.replaceState) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // Сайт → бот: передаём текущий ID сайта через Telegram deep link.
  window.openTelegramBot = function openTelegramBotWithLink() {
    const baseUrl = window.TELEGRAM_BOT_URL || 'https://t.me/YOUR_BOT_USERNAME';
    const separator = baseUrl.includes('?') ? '&' : '?';
    const link = `${baseUrl}${separator}start=link_${encodeURIComponent(chat_id)}`;
    window.location.href = link;
  };

  window.changeChatId = function changeNumericChatId() {
    const newId = prompt('Введите числовой Chat_ID:', chat_id);
    if (newId === null) return;

    const trimmed = newId.trim();
    if (!isNumericChatId(trimmed)) {
      alert('Chat_ID должен содержать только цифры и иметь длину от 5 до 20 символов.');
      return;
    }

    if (trimmed === chat_id) {
      alert('Это тот же Chat_ID. Изменений нет.');
      return;
    }

    const confirmed = window.confirm(
      `Сменить Chat_ID с "${chat_id}" на "${trimmed}"?\n\n` +
      'После смены будет загружен прогресс нового пользователя.'
    );
    if (!confirmed) return;

    applyChatId(trimmed);
    alert(`Chat_ID изменён на "${chat_id}"`);
  };
})();
