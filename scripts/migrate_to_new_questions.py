#!/usr/bin/env python3
"""
Миграция на новый файл вопросов (1513 вопросов).
Генерирует search_indexes и добавляет недостающие структуры.
"""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "intelligent_question_core" / "data"
OLD_FILE = DATA_DIR / "selfology_intelligent_core.json"
NEW_FILE = DATA_DIR / "selfology_final_sequenced.json"
OUTPUT_FILE = DATA_DIR / "selfology_core_v2.json"


def build_search_indexes(questions: list) -> dict:
    """Строит индексы для быстрого поиска вопросов."""
    indexes = {
        "metadata": {
            "total_questions": len(questions),
            "generated_at": datetime.now().isoformat(),
            "version": "2.0"
        },
        "by_classification": {
            "domain": defaultdict(list),
            "depth_level": defaultdict(list),
            "energy_dynamic": defaultdict(list),
            "journey_stage": defaultdict(list)
        },
        "by_psychology": {
            "safety_level": defaultdict(list),
            "complexity": defaultdict(list),
            "emotional_weight": defaultdict(list),
            "trust_requirement": defaultdict(list)
        },
        "combinations": {
            "domain_depth": defaultdict(list),
            "domain_energy": defaultdict(list)
        },
        "by_source": defaultdict(list),
        "keywords": defaultdict(list)
    }

    for q in questions:
        qid = q.get("id")
        if not qid:
            continue

        # Классификация
        classification = q.get("classification", {})
        for field in ["domain", "depth_level", "energy_dynamic", "journey_stage"]:
            value = classification.get(field)
            if value:
                indexes["by_classification"][field][value].append(qid)

        # Психология
        psychology = q.get("psychology", {})
        for field in ["safety_level", "complexity", "emotional_weight", "trust_requirement"]:
            value = psychology.get(field)
            if value is not None:
                indexes["by_psychology"][field][str(value)].append(qid)

        # Комбинации (для оптимизации частых запросов)
        domain = classification.get("domain")
        depth = classification.get("depth_level")
        energy = classification.get("energy_dynamic")

        if domain and depth:
            key = f"{domain}_{depth}"
            indexes["combinations"]["domain_depth"][key].append(qid)
        if domain and energy:
            key = f"{domain}_{energy}"
            indexes["combinations"]["domain_energy"][key].append(qid)

        # Источник
        source = q.get("source", "unknown")
        indexes["by_source"][source].append(qid)

    # Конвертируем defaultdict в обычные dict
    def convert_defaultdict(obj):
        if isinstance(obj, defaultdict):
            return {k: convert_defaultdict(v) for k, v in obj.items()}
        elif isinstance(obj, dict):
            return {k: convert_defaultdict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return obj
        return obj

    return convert_defaultdict(indexes)


def migrate():
    """Основная функция миграции."""
    print("🔄 Загружаю файлы...")

    # Загружаем старый файл (для копирования структур)
    with open(OLD_FILE, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    print(f"  ✅ Старый файл: {len(old_data.get('questions', []))} вопросов")

    # Загружаем новый файл
    with open(NEW_FILE, 'r', encoding='utf-8') as f:
        new_data = json.load(f)
    print(f"  ✅ Новый файл: {len(new_data.get('questions', []))} вопросов")

    # Строим новую структуру
    print("\n🔧 Строю search_indexes...")
    questions = new_data.get("questions", [])
    search_indexes = build_search_indexes(questions)

    # Статистика по доменам
    print("\n📊 Статистика по доменам:")
    for domain, ids in search_indexes["by_classification"]["domain"].items():
        print(f"  {domain}: {len(ids)} вопросов")

    # Формируем итоговый файл
    output = {
        "core_metadata": {
            "version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "total_questions": len(questions),
            "source": "selfology_final_sequenced.json",
            "migration_from": "selfology_intelligent_core.json"
        },
        "questions": questions,
        "connections": old_data.get("connections", []),  # Копируем связи
        "taxonomy": old_data.get("taxonomy", {}),        # Копируем таксономию
        "energy_rules": old_data.get("energy_rules", {}), # Копируем правила энергии
        "search_indexes": search_indexes,
        "api_endpoints": old_data.get("api_endpoints", {})
    }

    # Сохраняем
    print(f"\n💾 Сохраняю в {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Размер файла
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"  ✅ Размер: {size_mb:.2f} MB")

    print("\n✅ Миграция завершена!")
    print(f"📁 Новый файл: {OUTPUT_FILE}")
    print("\n⚠️  Далее нужно:")
    print("1. Обновить orchestrator.py на selfology_core_v2.json")
    print("2. Протестировать загрузку")
    print("3. Проверить выбор вопросов")


if __name__ == "__main__":
    migrate()
