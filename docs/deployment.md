# Публикация полной версии

Эта инструкция не привязана к конкретному домену, боту или аккаунту хостинга.

## Архитектура

```text
Браузер → статический сайт из website/
        → публичный HTTPS API → MySQL
Telegram-бот → тот же API → та же MySQL
```

## 1. База MySQL

Создайте управляемую MySQL и сохраните закрытую строку подключения в настройках серверного приложения:

```text
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE?charset=utf8mb4
```

Не публикуйте базу напрямую в интернете и не добавляйте пароль в Git.

## 2. API

Разверните корень репозитория по `Dockerfile`. Укажите:

```text
DATABASE_URL=<закрытая строка MySQL>
ADMIN_PASSWORD=<надёжный пароль>
SITE_URL=https://YOUR-DOMAIN.EXAMPLE
API_URL=http://127.0.0.1:5000
CORS_ORIGINS=https://YOUR-DOMAIN.EXAMPLE
```

Проверьте `https://YOUR-API-DOMAIN.EXAMPLE/api/health`. Ожидаемый ответ: `{"status":"ok"}`.

## 3. Статический сайт

В `website/config.js` замените локальный API на публичный HTTPS-адрес. Загрузите содержимое папки `website` на статический хостинг и направьте домен на этот хостинг.

## 4. Telegram

Создайте бота через `@BotFather` и добавьте в закрытые переменные серверного приложения:

```text
TELEGRAM_BOT_TOKEN=<секретный токен>
TELEGRAM_BOT_USERNAME=<username без @>
```

Также укажите ссылку на бота в `website/config.js`. После перезапуска серверного приложения бот и сайт будут использовать одну базу через API.
