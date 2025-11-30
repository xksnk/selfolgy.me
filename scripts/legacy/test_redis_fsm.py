#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Redis FSM Storage

Проверяет:
1. Подключение к Redis
2. Создание FSM state
3. Сохранение state в Redis
4. Восстановление state после "перезапуска"
5. Instance locking
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь проекта
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import redis.asyncio as redis

# Конфигурация из .env
REDIS_FSM_HOST = os.getenv("REDIS_FSM_HOST", "172.18.0.8")
REDIS_FSM_PORT = int(os.getenv("REDIS_FSM_PORT", "6379"))
REDIS_FSM_DB = int(os.getenv("REDIS_FSM_DB", "1"))
BOT_TOKEN = "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g"

# Тестовые состояния
class TestStates(StatesGroup):
    waiting = State()
    processing = State()

async def test_redis_connection():
    """Тест 1: Подключение к Redis"""
    print("=" * 50)
    print("ТЕСТ 1: Проверка подключения к Redis")
    print("=" * 50)

    try:
        r = await redis.Redis(
            host=REDIS_FSM_HOST,
            port=REDIS_FSM_PORT,
            db=REDIS_FSM_DB,
            decode_responses=True
        )

        # Проверяем PING
        pong = await r.ping()
        print(f"✅ Redis PING: {pong}")

        # Устанавливаем тестовое значение
        await r.set("test:key", "test_value", ex=10)
        value = await r.get("test:key")
        print(f"✅ Redis SET/GET: {value}")

        # Очищаем
        await r.delete("test:key")
        await r.close()

        print("✅ ТЕСТ 1 ПРОЙДЕН\n")
        return True

    except Exception as e:
        print(f"❌ ТЕСТ 1 ПРОВАЛЕН: {e}\n")
        return False

async def test_fsm_storage():
    """Тест 2: FSM Storage с сохранением состояния"""
    print("=" * 50)
    print("ТЕСТ 2: FSM Storage персистентность")
    print("=" * 50)

    try:
        # Создаем Redis storage (без custom key_builder для простоты)
        storage = RedisStorage.from_url(
            f"redis://{REDIS_FSM_HOST}:{REDIS_FSM_PORT}/{REDIS_FSM_DB}"
        )

        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=storage)

        # Симулируем пользователя
        test_user_id = 999999
        test_chat_id = 999999

        print(f"Тестовый пользователь: {test_user_id}")

        # Создаем FSM context
        # Получаем storage напрямую для тестирования
        from aiogram.fsm.storage.base import StorageKey
        key = StorageKey(bot_id=bot.id, chat_id=test_chat_id, user_id=test_user_id)

        # Устанавливаем состояние
        await storage.set_state(key=key, state=TestStates.waiting)
        print(f"✅ Установлено состояние: {TestStates.waiting.state}")

        # Устанавливаем данные
        test_data = {"step": 1, "answer": "test answer", "timestamp": "2025-10-02"}
        await storage.set_data(key=key, data=test_data)
        print(f"✅ Сохранены данные: {test_data}")

        # Проверяем что данные сохранились
        saved_state = await storage.get_state(key=key)
        saved_data = await storage.get_data(key=key)

        print(f"✅ Считано состояние: {saved_state}")
        print(f"✅ Считаны данные: {saved_data}")

        # Проверяем совпадение
        assert saved_state == TestStates.waiting.state, "State mismatch!"
        assert saved_data == test_data, "Data mismatch!"

        # Симулируем "перезапуск" - создаем новый storage
        print("\n🔄 Симуляция перезапуска бота...")
        await bot.session.close()
        await storage.close()

        # Новый bot и storage (как после перезапуска)
        storage2 = RedisStorage.from_url(
            f"redis://{REDIS_FSM_HOST}:{REDIS_FSM_PORT}/{REDIS_FSM_DB}"
        )
        bot2 = Bot(token=BOT_TOKEN)
        key2 = StorageKey(bot_id=bot2.id, chat_id=test_chat_id, user_id=test_user_id)

        # Проверяем что состояния восстановились после "перезапуска"
        restored_state = await storage2.get_state(key=key2)
        restored_data = await storage2.get_data(key=key2)

        print(f"✅ После перезапуска - состояние: {restored_state}")
        print(f"✅ После перезапуска - данные: {restored_data}")

        assert restored_state == TestStates.waiting.state, "State not persisted!"
        assert restored_data == test_data, "Data not persisted!"

        # Очистка
        await storage2.set_state(key=key2, state=None)
        await bot2.session.close()
        await storage2.close()

        print("✅ ТЕСТ 2 ПРОЙДЕН: Состояния сохраняются между перезапусками!\n")
        return True

    except Exception as e:
        print(f"❌ ТЕСТ 2 ПРОВАЛЕН: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def test_instance_locking():
    """Тест 3: Instance Locking"""
    print("=" * 50)
    print("ТЕСТ 3: Instance Locking (защита от дублей)")
    print("=" * 50)

    try:
        r = await redis.Redis(
            host=REDIS_FSM_HOST,
            port=REDIS_FSM_PORT,
            db=REDIS_FSM_DB,
            decode_responses=True
        )

        lock_key = "test:instance:lock"

        # Первый экземпляр получает блокировку
        lock1 = await r.set(lock_key, "instance1:pid:12345", nx=True, ex=30)
        print(f"✅ Экземпляр 1 получил блокировку: {lock1}")
        assert lock1 == True, "First instance should get lock"

        # Второй экземпляр НЕ должен получить блокировку
        lock2 = await r.set(lock_key, "instance2:pid:67890", nx=True, ex=30)
        print(f"✅ Экземпляр 2 НЕ получил блокировку: {lock2}")
        assert lock2 is None or lock2 == False, "Second instance should NOT get lock"

        # Проверяем кто держит блокировку
        lock_holder = await r.get(lock_key)
        print(f"✅ Блокировку держит: {lock_holder}")
        assert "instance1" in lock_holder, "Lock should be held by instance1"

        # Освобождаем блокировку
        await r.delete(lock_key)
        print(f"✅ Блокировка освобождена")

        # Теперь второй экземпляр может получить блокировку
        lock3 = await r.set(lock_key, "instance2:pid:67890", nx=True, ex=30)
        print(f"✅ Экземпляр 2 теперь получил блокировку: {lock3}")
        assert lock3 == True, "After release, second instance should get lock"

        # Очистка
        await r.delete(lock_key)
        await r.close()

        print("✅ ТЕСТ 3 ПРОЙДЕН: Instance locking работает корректно!\n")
        return True

    except Exception as e:
        print(f"❌ ТЕСТ 3 ПРОВАЛЕН: {e}\n")
        return False

async def main():
    """Запуск всех тестов"""
    print("\n🧪 ТЕСТИРОВАНИЕ REDIS FSM STORAGE")
    print("=" * 50)
    print(f"Redis Host: {REDIS_FSM_HOST}")
    print(f"Redis Port: {REDIS_FSM_PORT}")
    print(f"Redis DB: {REDIS_FSM_DB}")
    print("=" * 50)
    print()

    results = []

    # Тест 1: Подключение
    results.append(await test_redis_connection())

    # Тест 2: FSM Storage
    results.append(await test_fsm_storage())

    # Тест 3: Instance Locking
    results.append(await test_instance_locking())

    # Итоги
    print("=" * 50)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Пройдено: {passed}/{total}")

    if passed == total:
        print("✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
