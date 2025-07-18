# Telegram Bot с LLM

Умный Telegram бот на Python с поддержкой локальной LLM через Ollama и генерацией изображений.

## 🌟 Особенности

- **Персонаж Алиса** - дружелюбный русскоязычный помощник
- **LLM интеграция** - умные ответы через Ollama
- **Выбор модели** - автоматический и интерактивный выбор из доступных моделей
- **Смена модели на лету** - переключение между моделями без перезапуска
- **Fallback режим** - шаблонные ответы если LLM недоступна
- **История диалогов** - контекстные беседы
- **Генерация изображений** - через Stable Diffusion (опционально)
- **Модульная архитектура** - легко расширяемая структура
- **Простая настройка** - через переменные окружения

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env файл - добавьте токен бота
```

**Получить токен бота:**
1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot` и следуйте инструкциям
3. Скопируйте токен в файл `.env`

### 3. Настройка Ollama (опционально)

```bash
# Установите Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Скачайте модели для выбора
ollama pull llama3.2:3b      # Быстрая модель ~2GB
ollama pull llama3.2:1b      # Очень быстрая модель ~1GB
ollama pull mistral:7b       # Альтернативная модель ~4GB

# Запустите сервер (если не запущен автоматически)
ollama serve
```

### 4. Запуск

```bash
python main.py
```

## ⚙️ Конфигурация

Все настройки в `.env` файле:

### Обязательные настройки:
- `BOT_TOKEN` - токен Telegram бота

### LLM настройки:
- `LLM_PROVIDER` - провайдер (ollama/openai/anthropic/none)
- `LLM_MODEL` - модель (auto для автовыбора)
- `LLM_TEMPERATURE` - креативность ответов (0.0-1.0)
- `MAX_HISTORY` - количество сообщений в истории

### Генерация изображений:
- `IMAGE_GENERATION` - включить/выключить (true/false)
- `IMAGE_PROVIDER` - провайдер изображений
- `IMAGE_MODEL` - модель для генерации

### Прочие настройки:
- `DEBUG` - режим отладки
- `LOG_LEVEL` - уровень логирования
- `STORAGE_TYPE` - тип хранилища данных

## 🤖 Команды бота

- `/start` - Знакомство с ботом
- `/help` - Справка по командам
- `/info` - Информация о персонаже
- `/clear` - Очистить историю (только с LLM)
- `/stats` - Статистика работы
- `/image <описание>` - Генерация изображения (если включено)

## 📁 Структура проекта

```
telegram-bot/
├── .env.example              # Пример конфигурации
├── .gitignore               # Git ignore файл
├── requirements.txt         # Python зависимости
├── README.md               # Документация
├── main.py                 # Точка входа
├── characters/             # Персонажи бота
│   └── alice.py            # Персонаж Алиса
├── config/                 # Конфигурация
│   ├── __init__.py
│   ├── settings.py         # Настройки приложения
│   └── logging_config.py   # Настройки логирования
├── core/                   # Ядро приложения
│   ├── application.py      # Основное приложение
│   ├── bot_factory.py      # Фабрика сервисов
│   └── registry.py         # Реестр сервисов
├── handlers/               # Обработчики событий
│   ├── __init__.py
│   ├── base_handler.py     # Базовый обработчик
│   ├── command_handlers.py # Обработчики команд
│   └── message_handlers.py # Обработчики сообщений
├── models/                 # Модели данных
│   └── base.py             # Базовые модели
├── services/               # Сервисы
│   ├── llm/                # LLM сервисы
│   │   ├── base_client.py  # Базовый LLM клиент
│   │   └── ollama_client.py # Ollama клиент
│   ├── image/              # Генерация изображений
│   │   ├── base_generator.py
│   │   └── stable_diffusion.py
│   └── storage/            # Хранилище данных
│       └── memory_storage.py
├── scripts/                # Утилиты
│   └── select_model.py     # Выбор модели Ollama
├── tests/                  # Тесты
│   ├── test_character.py   # Тесты персонажа
│   ├── test_llm.py        # Тесты LLM
│   └── debug_bot.py       # Отладочный бот
└── utils/                  # Вспомогательные утилиты
    └── formatters.py       # Форматирование сообщений
```

## 🔧 Режимы работы

1. **С LLM** - умные контекстные ответы через Ollama
2. **Шаблонный** - предустановленные ответы по ключевым словам
3. **Гибридный** - автоматическое переключение при недоступности LLM

Бот автоматически переключается в шаблонный режим если LLM недоступна.

## 🧪 Тестирование

### Тест персонажа
```bash
python tests/test_character.py
```

### Тест LLM (требует Ollama)
```bash
python tests/test_llm.py
```

### Простой тест бота
```bash
python tests/simple_test_bot.py
```

### Отладочный режим
```bash
python tests/debug_bot.py
```

## 📝 Логи

Логи сохраняются в папке `logs/`:
- `logs/bot.log` - основные логи
- `logs/error.log` - только ошибки

Также выводятся в консоль при запуске.

## 🔧 Разработка

### Установка зависимостей для разработки:
```bash
pip install pytest pytest-asyncio black mypy
```

### Форматирование кода:
```bash
black .
```

### Проверка типов:
```bash
mypy .
```

### Структура модулей:

- **characters/** - персонажи и их логика
- **services/** - бизнес-логика (LLM, изображения, хранилище)
- **handlers/** - обработка Telegram событий
- **core/** - архитектурное ядро (DI, фабрики)
- **config/** - конфигурация и настройки

## 🐛 Решение проблем

### Бот не отвечает
1. Проверьте токен в `.env` файле
2. Убедитесь что бот запущен: `python main.py`
3. Проверьте логи в `logs/error.log`

### LLM не работает
1. Убедитесь что Ollama запущен: `ollama serve`
2. Проверьте доступные модели: `ollama list`
3. Скачайте модель: `ollama pull llama3.2:3b`

### Ошибки на Windows
1. Убедитесь что используется Python 3.8+
2. Попробуйте запустить от администратора
3. Проверьте что все пути в `.env` используют прямые слеши

### Проблемы с изображениями
1. Генерация изображений требует много ресурсов
2. Убедитесь что `IMAGE_GENERATION=true` в `.env`
3. Для CPU генерации потребуется много времени

## 🚀 Деплой

### Docker (в разработке)
```bash
# Будет добавлено в следующих версиях
docker build -t telegram-bot .
docker run -d --env-file .env telegram-bot
```

### Systemd сервис (Linux)
```bash
# Создайте сервис файл
sudo nano /etc/systemd/system/telegram-bot.service

[Unit]
Description=Telegram Bot with LLM
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/telegram-bot
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target

# Запустите сервис
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## 📈 Мониторинг

Используйте команду `/stats` в боте для проверки:
- Статус LLM сервиса
- Количество активных диалогов
- Состояние генерации изображений
- Использование памяти

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Добавьте тесты для новой функциональности
4. Убедитесь что код соответствует стилю (black)
5. Создайте Pull Request

## 📄 Лицензия

MIT License - см. файл LICENSE

## 🐛 Известные ограничения

- Бот не распознает голосовые сообщения (планируется)
- LLM работает только с установленной Ollama
- Генерация изображений требует много ресурсов
- Поддерживается только русский язык интерфейса
- Хранилище только в памяти (Redis/файлы планируется)

## 🆘 Поддержка

Если у вас возникли проблемы:

1. Проверьте [Issues](../../issues) на GitHub
2. Посмотрите логи в `logs/error.log`
3. Попробуйте простой тест: `python tests/simple_test_bot.py`
4. Создайте новый Issue с описанием проблемы

## 🔮 Планы развития

- [ ] Поддержка голосовых сообщений
- [ ] Веб-интерфейс для управления
- [ ] Поддержка нескольких языков
- [ ] Docker контейнеризация
- [ ] Интеграция с базами данных
- [ ] Плагинная архитектура
- [ ] Metrics и мониторинг
- [ ] Поддержка групповых чатов

---

Создано с ❤️ для изучения современной архитектуры Python приложений