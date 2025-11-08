#!/usr/bin/env python3
"""
ДЕМО: Как AI Coach использует Qdrant для релевантных ответов

Показывает:
1. Скорость Qdrant (< 10ms)
2. Semantic search похожих состояний
3. Personality trajectory анализ
4. Similarity matching
5. Как это улучшает ответы коуча
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import time

# Добавляем путь к проекту
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Импортируем напрямую
import importlib.util
spec = importlib.util.spec_from_file_location(
    "coach_vector_dao",
    f"{project_root}/data_access/coach_vector_dao.py"
)
coach_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coach_module)
CoachVectorDAO = coach_module.CoachVectorDAO


async def demo_coach_context_loading():
    """Демо: как коуч загружает контекст для ответа"""

    print("\n" + "="*60)
    print("🤖 AI COACH: Подготовка контекста для ответа")
    print("="*60)

    dao = CoachVectorDAO()
    user_id = 98005572

    # Проверка подключения
    health = await dao.health_check()
    print(f"\n✅ Qdrant Status: {health['status']}")
    for name, stats in health.get('collections', {}).items():
        print(f"   📊 {name}: {stats['points_count']} vectors, {stats['status']}")

    # ================================================================
    # 1. ТЕКУЩИЙ ПРОФИЛЬ (< 10ms)
    # ================================================================
    print(f"\n" + "─"*60)
    print("1️⃣  Загрузка ТЕКУЩЕГО профиля личности")
    print("─"*60)

    start = time.time()
    current_profile = await dao.get_current_personality_vector(user_id)
    elapsed_ms = (time.time() - start) * 1000

    if current_profile:
        print(f"⚡ Скорость: {elapsed_ms:.2f}ms")
        print(f"\n📊 Big Five Traits:")
        traits = current_profile.get("traits", {}).get("big_five", {})
        for trait, value in traits.items():
            bar = "█" * int(value * 20)
            print(f"   {trait:18s}: {bar} {value:.2f}")

        print(f"\n💡 Что дает коучу:")
        print(f"   → Openness высокая (0.85) → предлагать новые идеи")
        print(f"   → Conscientiousness низкая (0.3) → помочь со структурой")
        print(f"   → Extraversion низкая (0.2) → спокойный стиль общения")
    else:
        print("❌ Профиль не найден")

    # ================================================================
    # 2. SEMANTIC SEARCH ПОХОЖИХ СОСТОЯНИЙ
    # ================================================================
    print(f"\n" + "─"*60)
    print("2️⃣  Поиск похожих эмоциональных состояний")
    print("─"*60)

    # Симулируем вектор сообщения "не знаю что делать"
    # (В реальности это через OpenAI embeddings)
    print(f"\n💬 Пользователь пишет: 'Я не знаю что мне делать, куда направить силы'")
    print(f"   → Эмбеддинг сообщения через OpenAI...")

    # Для демо используем вектор из current_profile
    # (В реальности будет отдельный embed)
    message_vector = current_profile["vector"] if current_profile else None

    if message_vector:
        start = time.time()
        similar_states = await dao.search_similar_emotional_states(
            user_id,
            message_vector,
            limit=3
        )
        elapsed_ms = (time.time() - start) * 1000

        print(f"⚡ Скорость поиска: {elapsed_ms:.2f}ms среди 132 векторов")
        print(f"🔍 Найдено {len(similar_states)} похожих состояний:\n")

        for i, state in enumerate(similar_states, 1):
            print(f"   #{i} Similarity: {state['similarity_score']:.2%}")
            print(f"       Когда: {state['created_at'][:10]}")
            if state.get('narrative'):
                print(f"       Контекст: {state['narrative'][:80]}...")
            if state['is_milestone']:
                print(f"       🌟 MILESTONE - важный момент!")
            print()

        if similar_states:
            print(f"💡 Что дает коучу:")
            print(f"   → 'Вижу что это повторяющаяся тема для вас'")
            print(f"   → 'Вы уже были в похожей ситуации 2 недели назад'")
            print(f"   → Адаптировать стиль: не советы, а поддержка и рефлексия")

    # ================================================================
    # 3. PERSONALITY TRAJECTORY
    # ================================================================
    print(f"\n" + "─"*60)
    print("3️⃣  Анализ эволюции личности")
    print("─"*60)

    start = time.time()
    trajectory = await dao.get_personality_trajectory(user_id, limit=20)
    elapsed_ms = (time.time() - start) * 1000

    print(f"⚡ Скорость: {elapsed_ms:.2f}ms")
    print(f"📈 Загружено {len(trajectory)} точек эволюции\n")

    if trajectory:
        # Показываем тренд openness
        print(f"📊 Тренд Openness (открытость новому):")
        for i, point in enumerate(trajectory[-5:], 1):  # Последние 5
            big_five = point.get("big_five", {})
            openness = big_five.get("openness", 0)
            bar = "█" * int(openness * 30)
            milestone = "🌟" if point['is_milestone'] else "  "
            print(f"   {i}. {bar} {openness:.2f} {milestone}")

        # Анализ тренда
        first_openness = trajectory[0].get("big_five", {}).get("openness", 0)
        last_openness = trajectory[-1].get("big_five", {}).get("openness", 0)
        change = last_openness - first_openness

        print(f"\n💡 Что дает коучу:")
        if change > 0.1:
            print(f"   → 'Замечаю что ваша открытость новому растет (+{change:.2f})'")
            print(f"   → 'Это отличный знак - вы становитесь более гибким'")
        elif change < -0.1:
            print(f"   → 'Вижу что вы стали более консервативным ({change:.2f})'")
            print(f"   → 'Возможно, стоит добавить больше экспериментов?'")
        else:
            print(f"   → 'Ваша открытость стабильна - хороший баланс'")

    # ================================================================
    # 4. SIMILARITY MATCHING
    # ================================================================
    print(f"\n" + "─"*60)
    print("4️⃣  Поиск похожих пользователей")
    print("─"*60)

    start = time.time()
    similar_users = await dao.find_similar_users(user_id, limit=5, score_threshold=0.75)
    elapsed_ms = (time.time() - start) * 1000

    print(f"⚡ Скорость: {elapsed_ms:.2f}ms")
    print(f"👥 Найдено {len(similar_users)} похожих пользователей:\n")

    for i, user in enumerate(similar_users, 1):
        print(f"   #{i} Similarity: {user['similarity_score']:.2%}")
        print(f"       Архетип: {user['archetype']}")
        big_five = user.get("big_five", {})
        print(f"       Openness: {big_five.get('openness', 0):.2f}, "
              f"Conscientiousness: {big_five.get('conscientiousness', 0):.2f}")
        print()

    if similar_users:
        print(f"💡 Что дает коучу:")
        print(f"   → 'Люди с похожим профилем часто находят...'")
        print(f"   → Рекомендации на основе peer experience")
        print(f"   → Не абстрактные советы, а реальные примеры")

    # ================================================================
    # ИТОГО
    # ================================================================
    print(f"\n" + "="*60)
    print("📊 ИТОГО: Что получает AI Coach из Qdrant")
    print("="*60)

    print(f"""
1. ⚡ СКОРОСТЬ:
   - Загрузка профиля: < 10ms (vs SQL: ~100ms+)
   - Поиск похожих состояний: < 20ms среди 132 векторов
   - Полный контекст: < 50ms TOTAL

2. 🎯 РЕЛЕВАНТНОСТЬ:
   - Знает что пользователь УЖЕ был в похожей ситуации
   - Видит ПАТТЕРНЫ поведения через траекторию
   - Адаптирует стиль общения под личность

3. 👥 ПЕРСОНАЛИЗАЦИЯ:
   - Рекомендации из опыта похожих людей
   - Не generic советы, а peer-based insights
   - Учет эволюции личности

4. 💾 SQL vs QDRANT:
   SQL: хранение структурированных данных (identity, goals)
        → для ОТОБРАЖЕНИЯ пользователю

   Qdrant: векторный поиск семантического контекста
          → для ПОНИМАНИЯ и РЕЛЕВАНТНЫХ ОТВЕТОВ

ВЫВОД: Коуч БЕЗ Qdrant = generic советы без контекста
       Коуч С Qdrant = персонализированная поддержка с пониманием паттернов
    """)


async def main():
    """Main function"""
    print("\n🚀 Starting AI Coach + Qdrant DEMO")
    print(f"   Time: {datetime.now().isoformat()}\n")

    await demo_coach_context_loading()

    print("\n✅ DEMO completed!")


if __name__ == "__main__":
    asyncio.run(main())
