#!/usr/bin/env python3
"""
Синхронизация текста вопросов между базами.

v2 (книги) → core (онбординг)

Использование:
    python sync_questions.py --dry-run    # Показать что изменится
    python sync_questions.py --apply      # Применить изменения
"""

import json
import argparse
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "intelligent_question_core/data"

V2_FILE = DATA_DIR / "selfology_programs_v2.json"
CORE_FILE = DATA_DIR / "selfology_intelligent_core.json"


def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения"""
    return text.lower().strip().replace("ё", "е")


def similarity(a: str, b: str) -> float:
    """Похожесть двух строк (0-1)"""
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def load_v2_questions() -> dict:
    """Загрузка вопросов из v2 (книги)"""
    with open(V2_FILE, encoding="utf-8") as f:
        data = json.load(f)

    questions = {}
    for prog in data["programs"]:
        for block in prog["blocks"]:
            for q in block["questions"]:
                questions[q["id"]] = {
                    "text": q["text"],
                    "program": prog["name"],
                    "block": block["name"],
                    "v2_id": q["id"]
                }
    return questions


def load_core_questions() -> dict:
    """Загрузка вопросов из core (онбординг)"""
    with open(CORE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    return {q["id"]: q for q in data["questions"]}


def find_matches(v2_questions: dict, core_questions: dict, threshold: float = 0.85) -> list:
    """Найти совпадения между базами по тексту"""
    matches = []

    # Индекс core вопросов по нормализованному тексту
    core_by_text = {}
    for core_id, core_q in core_questions.items():
        norm = normalize_text(core_q["text"])
        core_by_text[norm] = (core_id, core_q)

    for v2_id, v2_data in v2_questions.items():
        v2_norm = normalize_text(v2_data["text"])

        # Точное совпадение
        if v2_norm in core_by_text:
            core_id, core_q = core_by_text[v2_norm]
            matches.append({
                "v2_id": v2_id,
                "core_id": core_id,
                "v2_text": v2_data["text"],
                "core_text": core_q["text"],
                "similarity": 1.0,
                "program": v2_data["program"],
                "block": v2_data["block"],
                "needs_update": v2_data["text"] != core_q["text"]  # Разный регистр/пробелы
            })
            continue

        # Fuzzy matching
        best_match = None
        best_sim = 0
        for core_id, core_q in core_questions.items():
            sim = similarity(v2_data["text"], core_q["text"])
            if sim > best_sim and sim >= threshold:
                best_sim = sim
                best_match = (core_id, core_q)

        if best_match:
            core_id, core_q = best_match
            matches.append({
                "v2_id": v2_id,
                "core_id": core_id,
                "v2_text": v2_data["text"],
                "core_text": core_q["text"],
                "similarity": best_sim,
                "program": v2_data["program"],
                "block": v2_data["block"],
                "needs_update": True
            })

    return matches


def show_sync_plan(matches: list):
    """Показать план синхронизации"""
    updates = [m for m in matches if m["needs_update"] and m["v2_text"] != m["core_text"]]
    exact = [m for m in matches if m["similarity"] == 1.0]
    fuzzy = [m for m in matches if m["similarity"] < 1.0]

    print("═" * 60)
    print("📊 ПЛАН СИНХРОНИЗАЦИИ")
    print("═" * 60)
    print(f"\n✅ Точных совпадений: {len(exact)}")
    print(f"🔍 Fuzzy совпадений: {len(fuzzy)}")
    print(f"✏️  Требуют обновления: {len(updates)}")

    if updates:
        print("\n" + "─" * 60)
        print("📝 ИЗМЕНЕНИЯ ТЕКСТА (v2 → core):")
        print("─" * 60)

        for i, m in enumerate(updates[:20], 1):  # Показываем первые 20
            print(f"\n{i}. [{m['program']} → {m['block']}]")
            print(f"   Similarity: {m['similarity']:.0%}")
            print(f"   CORE: {m['core_text'][:70]}...")
            print(f"   → V2: {m['v2_text'][:70]}...")

        if len(updates) > 20:
            print(f"\n   ... и ещё {len(updates) - 20} изменений")

    return updates


def apply_sync(matches: list, dry_run: bool = True):
    """Применить синхронизацию"""
    updates = [m for m in matches if m["needs_update"] and m["v2_text"] != m["core_text"]]

    if not updates:
        print("\n✅ Нет изменений для применения")
        return

    if dry_run:
        print(f"\n⚠️  DRY RUN: {len(updates)} изменений НЕ применено")
        print("   Используй --apply для применения")
        return

    # Загружаем core и обновляем
    with open(CORE_FILE, encoding="utf-8") as f:
        core_data = json.load(f)

    # Создаём backup
    backup_file = CORE_FILE.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(core_data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Backup создан: {backup_file.name}")

    # Обновляем тексты
    core_by_id = {q["id"]: q for q in core_data["questions"]}
    updated = 0

    for m in updates:
        if m["core_id"] in core_by_id:
            core_by_id[m["core_id"]]["text"] = m["v2_text"]
            updated += 1

    # Сохраняем
    with open(CORE_FILE, "w", encoding="utf-8") as f:
        json.dump(core_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Обновлено вопросов в core: {updated}")


def main():
    parser = argparse.ArgumentParser(description="Синхронизация баз вопросов")
    parser.add_argument("--dry-run", action="store_true", help="Только показать план")
    parser.add_argument("--apply", action="store_true", help="Применить изменения")
    parser.add_argument("--threshold", type=float, default=0.85, help="Порог похожести (0-1)")
    args = parser.parse_args()

    print("📚 Загрузка v2 (книги)...")
    v2_questions = load_v2_questions()
    print(f"   Вопросов: {len(v2_questions)}")

    print("🤖 Загрузка core (онбординг)...")
    core_questions = load_core_questions()
    print(f"   Вопросов: {len(core_questions)}")

    print(f"\n🔍 Поиск совпадений (threshold={args.threshold})...")
    matches = find_matches(v2_questions, core_questions, args.threshold)
    print(f"   Найдено совпадений: {len(matches)}")

    updates = show_sync_plan(matches)

    if args.apply:
        apply_sync(matches, dry_run=False)
    else:
        apply_sync(matches, dry_run=True)


if __name__ == "__main__":
    main()
