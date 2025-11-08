#!/bin/bash

# Selfology Development Helper Script
# Быстрый запуск и управление dev окружением с HOT RELOAD

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_highlight() {
    echo -e "${CYAN}🚀 $1${NC}"
}

show_help() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🚀 Selfology Development Helper${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Использование: ./dev.sh [команда]"
    echo ""
    echo -e "${GREEN}📦 Основные команды:${NC}"
    echo "  start       - Запустить dev режим с HOT RELOAD (Docker)"
    echo "  stop        - Остановить dev контейнеры"
    echo "  restart     - Перезапустить dev контейнеры"
    echo "  logs        - Показать логи контейнера в реальном времени"
    echo ""
    echo -e "${YELLOW}🔧 Управление:${NC}"
    echo "  shell       - Войти в shell контейнера"
    echo "  build       - Пересобрать dev образ (после изменения зависимостей)"
    echo "  status      - Статус контейнеров"
    echo "  clean       - Очистить dev контейнеры и образы"
    echo ""
    echo -e "${CYAN}🏃 Разработка:${NC}"
    echo "  local       - Запустить локально БЕЗ Docker (самый быстрый вариант)"
    echo "  test        - Запустить тесты"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}💡 Примеры:${NC}"
    echo "  ./dev.sh start       # Docker с hot reload - изменения применяются автоматически!"
    echo "  ./dev.sh logs        # Смотреть логи в реальном времени"
    echo "  ./dev.sh local       # Локальный запуск (БЕЗ Docker rebuild)"
    echo ""
    echo -e "${GREEN}⚡ HOT RELOAD активен:${NC}"
    echo "  - Любое изменение в .py файлах перезапускает бот автоматически"
    echo "  - НЕТ необходимости перезапускать контейнер"
    echo "  - Логи показываются в реальном времени"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

dev_start() {
    print_highlight "Запуск Selfology в dev режиме с HOT RELOAD..."

    # Проверяем, что существуют необходимые файлы
    if [[ ! -f ".env.development" ]]; then
        print_error ".env.development не найден! Создайте его из .env.example"
        exit 1
    fi

    if [[ ! -f "docker-compose.dev.yml" ]]; then
        print_error "docker-compose.dev.yml не найден!"
        exit 1
    fi

    print_info "Сборка dev образа (может занять минуту при первом запуске)..."
    docker-compose -f docker-compose.dev.yml build

    print_info "Запуск контейнеров..."
    docker-compose -f docker-compose.dev.yml up -d

    echo ""
    print_success "Dev режим запущен! 🎉"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}⚡ HOT RELOAD АКТИВЕН:${NC}"
    echo "  - Меняй код в любых .py файлах"
    echo "  - Бот АВТОМАТИЧЕСКИ перезапустится"
    echo "  - НЕТ необходимости перезапускать Docker"
    echo ""
    echo -e "${BLUE}📊 Полезные команды:${NC}"
    echo "  ./dev.sh logs     - Смотреть логи"
    echo "  ./dev.sh status   - Проверить статус"
    echo "  ./dev.sh stop     - Остановить"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

dev_stop() {
    print_info "Остановка dev контейнеров..."
    docker-compose -f docker-compose.dev.yml down
    print_success "Dev контейнеры остановлены"
}

dev_restart() {
    print_info "Перезапуск dev контейнеров..."
    dev_stop
    sleep 2
    dev_start
}

dev_logs() {
    print_info "Показываю логи dev контейнера (Ctrl+C для выхода)..."
    echo -e "${YELLOW}Следите за автоматическими перезапусками при изменении файлов${NC}"
    echo ""
    docker-compose -f docker-compose.dev.yml logs -f selfology-dev
}

dev_shell() {
    print_info "Вход в shell dev контейнера..."
    docker-compose -f docker-compose.dev.yml exec selfology-dev bash
}

dev_build() {
    print_info "Пересборка dev образа (используйте после изменения requirements.txt)..."
    docker-compose -f docker-compose.dev.yml build --no-cache
    print_success "Dev образ пересобран"
}

dev_status() {
    print_info "Статус dev контейнеров:"
    echo ""
    docker-compose -f docker-compose.dev.yml ps
}

dev_clean() {
    print_warning "Очистка dev контейнеров и образов..."
    read -p "Вы уверены? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f docker-compose.dev.yml down --rmi all --volumes --remove-orphans
        print_success "Dev окружение очищено"
    else
        print_info "Отменено"
    fi
}

dev_local() {
    print_highlight "Локальный запуск (БЕЗ Docker) - САМЫЙ БЫСТРЫЙ ВАРИАНТ"

    if [[ ! -f "run-local.sh" ]]; then
        print_error "run-local.sh не найден!"
        exit 1
    fi

    print_info "Запуск через run-local.sh..."
    chmod +x run-local.sh
    ./run-local.sh
}

dev_test() {
    print_info "Запуск тестов..."
    if [[ -f "docker-compose.test.yml" ]]; then
        docker-compose -f docker-compose.test.yml run --rm selfology-test pytest
    else
        print_info "Запуск тестов локально..."
        source venv/bin/activate 2>/dev/null || true
        pytest tests/
    fi
}

# Main logic
case "${1:-help}" in
    start)
        dev_start
        ;;
    stop)
        dev_stop
        ;;
    restart)
        dev_restart
        ;;
    logs)
        dev_logs
        ;;
    shell)
        dev_shell
        ;;
    build)
        dev_build
        ;;
    status)
        dev_status
        ;;
    clean)
        dev_clean
        ;;
    local)
        dev_local
        ;;
    test)
        dev_test
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
