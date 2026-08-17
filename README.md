<p align="center">
  <img src="website/images/lear-logo.png" alt="LearEnglish" width="128">
</p>

<h1 align="center">LearEnglish</h1>

<p align="center">
  Учебная платформа для изучения английских слов: сайт, REST API, MySQL, админ-панель и Telegram-бот.
</p>

<p align="center">
  <strong>5 этапов · 300 слов · каждый этап можно использовать самостоятельно</strong>
</p>

---

## Что получится

~~~text
Сайт на REG.RU ─┐
                ├─ HTTPS API в Amvera ─ MySQL в Amvera
Telegram-бот ───┘
~~~

Сайт и бот работают через API. Пароли MySQL никогда не передаются в браузер и не хранятся в GitHub.

## Порядок запуска

| Этап | Результат | Инструкция |
|:---:|---|---|
| 1 | Автономное ядро работает на ПК | Быстрый старт ниже |
| 2 | Полная версия работает локально | Быстрый старт ниже |
| 3 | API и MySQL работают в Amvera | [Amvera: API и MySQL](docs/infoAmvara.md) |
| 4 | Сайт и админ-панель работают на REG.RU | [REG.RU: сайт и админ-панель](docs/reg-ru.md) |
| 5 | Подключён Telegram-бот | [Telegram-бот](docs/telegram-bot.md) |

> Проходите этапы по порядку. После успешной проверки любого этапа можно остановиться — уже настроенная часть продолжит работать.

## Быстрый старт

### 1. Автономное ядро

Python, база данных и регистрация не нужны.

1. Нажмите **Code → Download ZIP** и распакуйте архив.
2. Запустите **start-core.bat**.
3. Проверьте карточки, пары слов и сохранение прогресса.

Также можно открыть **core/index.html** двойным щелчком.

### 2. Полная версия на ПК

1. Создайте собственную копию через **Fork**.
2. Скачайте и распакуйте свою копию.
3. Запустите **scripts/setup-backend-windows.bat** и задайте **ADMIN_PASSWORD** в файле **.env**.
4. Запустите **scripts/start-api-windows.bat**, затем **scripts/start-website-windows.bat**.

Проверка API: [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)  
Сайт: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
Админ-панель: [http://127.0.0.1:8000/admin.html](http://127.0.0.1:8000/admin.html)

Правильный ответ API:

~~~json
{"status":"ok"}
~~~

## Подробные инструкции

- [Общая схема публикации](docs/deployment.md)
- [Amvera: Docker API, MySQL, переменные и типовые ошибки](docs/infoAmvara.md)
- [REG.RU: домен, сайт и админ-панель](docs/reg-ru.md)
- [Telegram: создание и подключение бота](docs/telegram-bot.md)
- [План проекта](docs/roadmap.md)

Админ-панель уже входит в проект. После публикации она открывается по адресу:

~~~text
https://ВАШ-ДОМЕН/admin.html
~~~

## Структура

| Путь | Назначение |
|---|---|
| **core/** | автономная версия |
| **english_learning/** | API и Telegram-бот |
| **website/** | сайт и админ-панель |
| **docs/** | подробные инструкции |
| **scripts/** | установка и запуск на Windows |
| **Dockerfile**, **amvera.yml** | готовая конфигурация Amvera |

## Безопасность

Никогда не публикуйте **.env**, **DATABASE_URL**, пароли MySQL, **ADMIN_PASSWORD**, **TELEGRAM_BOT_TOKEN** и токены GitHub.

В **website/config.js** разрешены только публичные адреса API и Telegram-бота — без паролей и токенов.
