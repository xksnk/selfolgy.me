#!/bin/bash

# Быстрый локальный запуск без Docker для максимально быстрой разработки
# Использует существующие сервисы в Docker (postgres, redis, qdrant)

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Проверяем существование виртуального окружения
if [[ ! -d "venv" ]]; then
    print_info "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
print_info "Активация виртуального окружения..."
source venv/bin/activate

# Устанавливаем зависимости если нужно
print_info "Проверка зависимостей..."
pip install -r requirements.txt > /dev/null 2>&1

# Загружаем переменные окружения для разработки
if [[ -f ".env.development" ]]; then
    export $(grep -v '^#' .env.development | xargs)
    print_success "Загружены настройки разработки"
else
    print_warning "Файл .env.development не найден, использую .env"
    export $(grep -v '^#' .env | xargs)
fi

# Переопределяем URLs для локального подключения к Docker сервисам
export DATABASE_URL="postgresql+asyncpg://n8n:sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=@localhost:5432/n8n"
export REDIS_URL="redis://localhost:6379"
export QDRANT_URL="http://localhost:6333"

print_info "Запуск Selfology локально с hot reload..."
print_success "URL: http://localhost:8001"
print_success "Health: http://localhost:8001/health"
print_warning "Нажмите Ctrl+C для остановки"

# Запускаем бот в polling режиме с hot reload через watchdog
pip install watchdog > /dev/null 2>&1

# Используем watchmedo для автоперезапуска при изменениях
watchmedo auto-restart \
    --directory=. \
    --pattern="*.py" \
    --ignore-patterns="*/logs/*;*/venv/*;*/__pycache__/*;*.pyc" \
    --recursive \
    -- python selfology_controller.py