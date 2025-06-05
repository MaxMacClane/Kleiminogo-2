#!/bin/bash

# Скрипт запуска системы опросов ДНП "Клеймёново-2"

echo "🏘️ Запуск системы опросов ДНП 'Клеймёново-2'"
echo "============================================"

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "📝 Создайте его командой: python -m venv venv"
    exit 1
fi

# Активируем виртуальное окружение
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Проверяем зависимости
echo "📦 Проверка зависимостей..."
pip install -r requirements.txt --quiet

# Проверяем базу данных
if [ ! -f "data/db.sqlite3" ]; then
    echo "🗄️ Инициализация базы данных..."
    mkdir -p data
    python init_db.py
    python add_questions.py
else
    echo "✅ База данных найдена"
fi

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "📝 Создайте .env файл с настройками (пример в README.md)"
    echo "🚀 Запуск без AI-модерации..."
else
    echo "✅ Конфигурация найдена"
fi

echo ""
echo "🚀 Запуск сервера на http://localhost:8000"
echo "🛑 Для остановки нажмите Ctrl+C"
echo ""

# Запускаем сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 