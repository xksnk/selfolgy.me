#!/usr/bin/env python3
"""
Применение всех изменений к базе v2:
1. Новые описания кластеров (из rewrite)
2. Улучшенные формулировки вопросов (из merge)
3. Метаданные из core базы (из merge)

Создаёт единую master базу с полными данными.
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "intelligent_question_core/data"

# Файлы
V2_FILE = DATA_DIR / "selfology_programs_v2.json"
DESCRIPTIONS_FILE = DATA_DIR / "descriptions_rewrite_20251202_123147.json"
MERGE_FILE = DATA_DIR / "merge_analysis_20251202_133410.json"
OUTPUT_FILE = DATA_DIR / "selfology_master.json"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def apply_changes():
    print("📚 Загрузка данных...")

    # Загружаем всё
    v2_data = load_json(V2_FILE)
    descriptions = load_json(DESCRIPTIONS_FILE)
    merge_data = load_json(MERGE_FILE)

    print(f"   V2: {v2_data['metadata']['total_questions']} вопросов")
    print(f"   Описания: {len(descriptions)} переформулировок")
    print(f"   Merge: {merge_data['stats']['matched']} совпадений, {merge_data['stats']['improved']} улучшено")

    # Индексируем результаты merge по v2_id
    merge_index = {m["v2_id"]: m for m in merge_data["matches"]}

    # Статистика
    stats = {
        "descriptions_updated": 0,
        "questions_improved": 0,
        "metadata_added": 0
    }

    print("\n🔄 Применение изменений...")

    for prog in v2_data["programs"]:
        for block in prog["blocks"]:
            # 1. Обновляем описание кластера
            old_desc = block.get("description", "")
            if old_desc in descriptions:
                new_desc = descriptions[old_desc]
                if new_desc != old_desc:
                    block["description"] = new_desc
                    stats["descriptions_updated"] += 1

            # 2. Обновляем вопросы
            for q in block["questions"]:
                q_id = q.get("id")
                if q_id and q_id in merge_index:
                    match = merge_index[q_id]

                    # Улучшенная формулировка
                    if match.get("final_text") and match["final_text"] != q["text"]:
                        q["original_text"] = q["text"]  # Сохраняем оригинал
                        q["text"] = match["final_text"]
                        stats["questions_improved"] += 1

                    # Метаданные из core
                    if match.get("core_metadata"):
                        q["metadata"] = match["core_metadata"]
                        q["core_id"] = match.get("core_id")
                        q["match_confidence"] = match.get("confidence")
                        stats["metadata_added"] += 1

                    # Изменения для аудита
                    if match.get("changes"):
                        q["ai_changes"] = match["changes"]

    # Обновляем метаданные файла
    v2_data["metadata"]["unified_at"] = datetime.now().isoformat()
    v2_data["metadata"]["descriptions_updated"] = stats["descriptions_updated"]
    v2_data["metadata"]["questions_improved"] = stats["questions_improved"]
    v2_data["metadata"]["metadata_added"] = stats["metadata_added"]
    v2_data["version"] = "3.0-master"

    # Сохраняем
    print(f"\n💾 Сохранение в {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(v2_data, f, ensure_ascii=False, indent=2)

    # Итоги
    print("\n" + "═" * 50)
    print("✅ ПРИМЕНЕНИЕ ЗАВЕРШЕНО")
    print("═" * 50)
    print(f"   📝 Описаний обновлено: {stats['descriptions_updated']}")
    print(f"   ✨ Вопросов улучшено: {stats['questions_improved']}")
    print(f"   🏷️  Метаданных добавлено: {stats['metadata_added']}")
    print(f"\n   📁 Master файл: {OUTPUT_FILE.name}")

    return stats


if __name__ == "__main__":
    apply_changes()
