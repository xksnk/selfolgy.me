#!/usr/bin/env python3
"""
Генератор метаданных для вопросов программ.

Гибридный подход:
1. Правила по позиции в блоке (complexity, emotional_weight, energy_dynamic)
2. Наследование от block_metadata (journey_stage, depth, safety)
3. AI-генерация для сложных параметров (domain, requires_context)
4. Пометка needs_human_review если confidence < 0.75

Использование:
    python intelligent_question_core/metadata_generator.py
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncpg
import re

# Настройки БД
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'selfology',
    'user': 'selfology_user',
    'password': 'selfology_secure_2024'
}


# ============================================================
# ПРАВИЛА ПО ПОЗИЦИИ В БЛОКЕ
# ============================================================

POSITION_RULES = {
    # Foundation блоки - мягкий вход
    "Foundation": {
        1: {"complexity": 1, "emotional_weight": 1, "energy_dynamic": "OPENING"},
        2: {"complexity": 1, "emotional_weight": 1, "energy_dynamic": "OPENING"},
        3: {"complexity": 2, "emotional_weight": 2, "energy_dynamic": "NEUTRAL"},
        4: {"complexity": 2, "emotional_weight": 2, "energy_dynamic": "NEUTRAL"},
        "default": {"complexity": 2, "emotional_weight": 2, "energy_dynamic": "NEUTRAL"},
    },
    # Exploration блоки - углубление
    "Exploration": {
        1: {"complexity": 2, "emotional_weight": 2, "energy_dynamic": "NEUTRAL"},
        2: {"complexity": 3, "emotional_weight": 3, "energy_dynamic": "PROCESSING"},
        3: {"complexity": 3, "emotional_weight": 3, "energy_dynamic": "PROCESSING"},
        4: {"complexity": 4, "emotional_weight": 4, "energy_dynamic": "HEAVY"},
        5: {"complexity": 4, "emotional_weight": 4, "energy_dynamic": "HEAVY"},
        6: {"complexity": 3, "emotional_weight": 3, "energy_dynamic": "HEALING"},
        "default": {"complexity": 3, "emotional_weight": 3, "energy_dynamic": "PROCESSING"},
    },
    # Integration блоки - синтез и закрытие
    "Integration": {
        1: {"complexity": 4, "emotional_weight": 3, "energy_dynamic": "PROCESSING"},
        2: {"complexity": 4, "emotional_weight": 3, "energy_dynamic": "HEALING"},
        3: {"complexity": 3, "emotional_weight": 2, "energy_dynamic": "HEALING"},
        4: {"complexity": 3, "emotional_weight": 2, "energy_dynamic": "HEALING"},
        "default": {"complexity": 3, "emotional_weight": 2, "energy_dynamic": "HEALING"},
    }
}


# Depth level mapping от типа блока
DEPTH_BY_BLOCK_TYPE = {
    "Foundation": "SURFACE",       # Поверхностный уровень
    "Exploration": "CONSCIOUS",    # Осознанный уровень, переход к EDGE
    "Integration": "SHADOW"        # Глубокий уровень
}

# Journey stage mapping
JOURNEY_STAGE_BY_BLOCK_TYPE = {
    "Foundation": "ENTRY",
    "Exploration": "EXPLORATION",
    "Integration": "INTEGRATION"
}


# ============================================================
# ОПРЕДЕЛЕНИЕ DOMAIN ПО КЛЮЧЕВЫМ СЛОВАМ
# ============================================================

DOMAIN_KEYWORDS = {
    "IDENTITY": [
        "себя", "личност", "кто я", "идентичн", "само", "подлинн",
        "аутентичн", "маск", "роль", "я есть", "сущност"
    ],
    "RELATIONSHIPS": [
        "отношен", "семь", "друз", "любов", "близк", "партнёр",
        "люди", "связ", "общени", "доверие", "одинок", "близост"
    ],
    "CAREER": [
        "работ", "карьер", "професс", "бизнес", "призван", "навык",
        "достижен", "коллег", "начальн", "зарплат", "офис"
    ],
    "HEALTH": [
        "здоровь", "тело", "сон", "еда", "спорт", "болезн",
        "самочувств", "энерги", "устало", "физич", "ощущени"
    ],
    "EMOTIONAL": [
        "эмоци", "чувств", "настроен", "радост", "грусть", "страх",
        "гнев", "тревог", "спокойств", "счасть", "грусн"
    ],
    "PURPOSE": [
        "смысл", "цел", "мечт", "будущ", "зачем", "ценност",
        "приоритет", "важн", "жизн", "путь", "направлен"
    ],
    "GROWTH": [
        "развит", "рост", "обучен", "опыт", "урок", "измен",
        "трансформ", "новое", "учиться", "навык"
    ],
    "FINANCES": [
        "деньг", "финанс", "богатств", "бедн", "доход", "расход",
        "инвестиц", "крипт", "накоплен", "зарабатыва"
    ],
    "TIME": [
        "врем", "прошл", "будущ", "сейчас", "момент", "история",
        "воспоминан", "план", "расписан", "когда"
    ],
    "TECHNOLOGY": [
        "технолог", "AI", "алгоритм", "соцсет", "экран", "цифров",
        "интернет", "онлайн", "гаджет", "информаци"
    ]
}


# ============================================================
# ПРАВИЛА ДЛЯ RECOMMENDED_MODEL
# ============================================================

def determine_recommended_model(
    depth_level: str,
    emotional_weight: int,
    energy_dynamic: str,
    domain: str
) -> str:
    """
    Определить рекомендуемую AI модель для обработки ответа.

    Правила:
    - Claude Sonnet: SHADOW/CORE depth, HEAVY energy, emotional_weight >= 4
    - GPT-4o: Средняя сложность, эмоциональная поддержка
    - GPT-4o-mini: Простые вопросы, SURFACE depth
    """
    # Claude для глубокой работы
    if depth_level in ("SHADOW", "CORE"):
        return "claude-sonnet-4"
    if emotional_weight >= 4:
        return "claude-sonnet-4"
    if energy_dynamic == "HEAVY":
        return "claude-sonnet-4"

    # GPT-4o для средней сложности
    if depth_level in ("EDGE", "CONSCIOUS"):
        return "gpt-4o"
    if emotional_weight >= 3:
        return "gpt-4o"
    if energy_dynamic == "PROCESSING":
        return "gpt-4o"

    # GPT-4o-mini для простых вопросов
    return "gpt-4o-mini"


# ============================================================
# ОПРЕДЕЛЕНИЕ REQUIRES_CONTEXT
# ============================================================

CONTEXT_INDICATORS = [
    r"то\s+что\s+ты",
    r"ранее\s+говорил",
    r"как\s+ты\s+сказал",
    r"в\s+прошлом\s+ответе",
    r"учитывая\s+что",
    r"исходя\s+из",
    r"опираясь\s+на",
    r"как\s+мы\s+обсуждали",
    r"вернёмся\s+к",
    r"связан\s+с\s+тем"
]


def check_requires_context(question_text: str) -> bool:
    """Проверить, требует ли вопрос контекста предыдущих ответов."""
    text_lower = question_text.lower()
    for pattern in CONTEXT_INDICATORS:
        if re.search(pattern, text_lower):
            return True
    return False


# ============================================================
# ОСНОВНАЯ ЛОГИКА ГЕНЕРАЦИИ
# ============================================================

def determine_domain(question_text: str) -> tuple[str, float]:
    """
    Определить domain вопроса по ключевым словам.
    Возвращает (domain, confidence).
    """
    text_lower = question_text.lower()
    scores = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text_lower:
                score += 1
        if score > 0:
            scores[domain] = score

    if not scores:
        return ("GENERAL", 0.5)

    # Выбираем domain с максимальным счётом
    best_domain = max(scores, key=scores.get)
    max_score = scores[best_domain]

    # Confidence зависит от количества совпадений
    confidence = min(0.95, 0.5 + max_score * 0.15)

    return (best_domain, confidence)


def generate_question_metadata(
    question_text: str,
    position_in_block: int,
    block_type: str,
    block_metadata: Dict
) -> Dict[str, Any]:
    """
    Сгенерировать метаданные для вопроса.

    Алгоритм:
    1. Получить базовые значения из правил позиции
    2. Унаследовать от block_metadata
    3. Определить domain по тексту
    4. Рассчитать recommended_model
    5. Определить requires_context
    6. Рассчитать confidence и needs_human_review
    """
    # 1. Правила по позиции
    block_rules = POSITION_RULES.get(block_type, POSITION_RULES["Exploration"])
    position_rule = block_rules.get(position_in_block, block_rules["default"])

    complexity = position_rule["complexity"]
    emotional_weight = position_rule["emotional_weight"]
    energy_dynamic = position_rule["energy_dynamic"]

    # 2. Наследование от блока
    journey_stage = JOURNEY_STAGE_BY_BLOCK_TYPE.get(block_type, "EXPLORATION")
    depth_level = DEPTH_BY_BLOCK_TYPE.get(block_type, "CONSCIOUS")
    safety_level = block_metadata.get("base_safety_minimum", 3)
    trust_requirement = max(1, safety_level - 1)

    # Корректировка depth по позиции в Exploration блоках
    if block_type == "Exploration":
        if position_in_block >= 4:
            depth_level = "EDGE"
        if position_in_block >= 5:
            depth_level = "SHADOW"

    # 3. Определить domain
    domain, domain_confidence = determine_domain(question_text)

    # 4. Recommended model
    recommended_model = determine_recommended_model(
        depth_level, emotional_weight, energy_dynamic, domain
    )

    # 5. Requires context
    requires_context = check_requires_context(question_text)

    # 6. Confidence и review
    # Базовый confidence зависит от уверенности в domain
    confidence_score = domain_confidence

    # Понижаем confidence для сложных вопросов (требуют экспертной оценки)
    if emotional_weight >= 4:
        confidence_score *= 0.85
    if depth_level in ("SHADOW", "CORE"):
        confidence_score *= 0.9

    needs_human_review = confidence_score < 0.75

    return {
        "journey_stage": journey_stage,
        "depth_level": depth_level,
        "domain": domain,
        "energy_dynamic": energy_dynamic,
        "complexity": complexity,
        "emotional_weight": emotional_weight,
        "safety_level": safety_level,
        "trust_requirement": trust_requirement,
        "recommended_model": recommended_model,
        "requires_context": requires_context,
        "confidence_score": round(confidence_score, 3),
        "needs_human_review": needs_human_review
    }


# ============================================================
# ПРИМЕНЕНИЕ К БД
# ============================================================

async def update_questions_metadata(conn: asyncpg.Connection) -> Dict[str, int]:
    """Обновить метаданные всех вопросов в БД."""

    # Получаем все вопросы с информацией о блоках
    questions = await conn.fetch("""
        SELECT
            q.id,
            q.question_id,
            q.text,
            q.position_in_block,
            b.block_type,
            b.base_journey_stage,
            b.base_depth_range,
            b.base_energy_dynamic,
            b.base_safety_minimum,
            b.base_complexity_range,
            b.base_emotional_weight_range
        FROM selfology.program_questions q
        JOIN selfology.program_blocks b ON q.block_id = b.block_id
        ORDER BY q.id
    """)

    stats = {
        "total": len(questions),
        "updated": 0,
        "needs_review": 0,
        "by_model": {},
        "by_domain": {},
        "by_depth": {}
    }

    print(f"📊 Обрабатываю {len(questions)} вопросов...")

    for q in questions:
        # Собираем block_metadata
        block_metadata = {
            "base_journey_stage": q["base_journey_stage"],
            "base_depth_range": q["base_depth_range"],
            "base_energy_dynamic": q["base_energy_dynamic"],
            "base_safety_minimum": q["base_safety_minimum"] or 3,
            "base_complexity_range": q["base_complexity_range"],
            "base_emotional_weight_range": q["base_emotional_weight_range"]
        }

        # Генерируем метаданные
        position = q["position_in_block"] or 1
        metadata = generate_question_metadata(
            q["text"],
            position,
            q["block_type"],
            block_metadata
        )

        # Обновляем в БД
        await conn.execute("""
            UPDATE selfology.program_questions SET
                journey_stage = $1,
                depth_level = $2,
                domain = $3,
                energy_dynamic = $4,
                complexity = $5,
                emotional_weight = $6,
                safety_level = $7,
                trust_requirement = $8,
                recommended_model = $9,
                requires_context = $10,
                confidence_score = $11,
                needs_human_review = $12,
                updated_at = NOW()
            WHERE id = $13
        """,
            metadata["journey_stage"],
            metadata["depth_level"],
            metadata["domain"],
            metadata["energy_dynamic"],
            metadata["complexity"],
            metadata["emotional_weight"],
            metadata["safety_level"],
            metadata["trust_requirement"],
            metadata["recommended_model"],
            metadata["requires_context"],
            metadata["confidence_score"],
            metadata["needs_human_review"],
            q["id"]
        )

        stats["updated"] += 1
        if metadata["needs_human_review"]:
            stats["needs_review"] += 1

        # Статистика по моделям
        model = metadata["recommended_model"]
        stats["by_model"][model] = stats["by_model"].get(model, 0) + 1

        # Статистика по domain
        domain = metadata["domain"]
        stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1

        # Статистика по depth
        depth = metadata["depth_level"]
        stats["by_depth"][depth] = stats["by_depth"].get(depth, 0) + 1

    return stats


async def main():
    print("=" * 60)
    print("🧠 ГЕНЕРАЦИЯ МЕТАДАННЫХ ДЛЯ ВОПРОСОВ")
    print("=" * 60)

    # Подключение к БД
    print(f"\n🔗 Подключаюсь к БД: {DB_CONFIG['database']}...")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ Подключение установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return

    try:
        # Обновляем метаданные
        stats = await update_questions_metadata(conn)

        # Выводим статистику
        print(f"\n{'=' * 60}")
        print("📈 СТАТИСТИКА ГЕНЕРАЦИИ:")
        print(f"{'=' * 60}")
        print(f"Всего вопросов: {stats['total']}")
        print(f"Обновлено: {stats['updated']}")
        print(f"Требуют ревью психолога: {stats['needs_review']}")

        print(f"\n📊 По рекомендуемой модели:")
        for model, count in sorted(stats['by_model'].items()):
            pct = count / stats['total'] * 100
            print(f"  {model}: {count} ({pct:.1f}%)")

        print(f"\n🎯 По domain:")
        for domain, count in sorted(stats['by_domain'].items(), key=lambda x: -x[1]):
            pct = count / stats['total'] * 100
            print(f"  {domain}: {count} ({pct:.1f}%)")

        print(f"\n🌊 По depth_level:")
        for depth, count in sorted(stats['by_depth'].items()):
            pct = count / stats['total'] * 100
            print(f"  {depth}: {count} ({pct:.1f}%)")

        print(f"{'=' * 60}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()
        print("\n🔒 Соединение закрыто")

    print("\n✅ Генерация метаданных завершена!")


if __name__ == '__main__':
    asyncio.run(main())
