#!/usr/bin/env python3
"""
AI Question Merger — объединение баз вопросов через Claude.

Берёт структуру из v2 (программы/кластеры) и находит соответствия в core
для обогащения метаданными.

Использование:
    python merge_databases.py --analyze     # Анализ без изменений
    python merge_databases.py --merge       # Создать объединённую базу
    python merge_databases.py --sample 10   # Тест на 10 вопросах
"""

import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import os
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import anthropic

# ═══════════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

DATA_DIR = PROJECT_ROOT / "intelligent_question_core/data"
V2_FILE = DATA_DIR / "selfology_programs_v2.json"
CORE_FILE = DATA_DIR / "selfology_intelligent_core.json"
OUTPUT_FILE = DATA_DIR / "selfology_unified.json"

MODEL = "claude-sonnet-4-20250514"  # Claude Sonnet 4

# ═══════════════════════════════════════════════════════════════════════════════
# ПРОМПТЫ
# ═══════════════════════════════════════════════════════════════════════════════

MATCHER_SYSTEM = """Ты опытный психотерапевт с 20-летним стажем работы с рефлексивными практиками.

Твоя задача — найти СЕМАНТИЧЕСКОЕ соответствие между вопросами из двух баз данных.

ВАЖНО: Вопросы могут быть сформулированы по-разному, но иметь ОДИНАКОВЫЙ СМЫСЛ.

Примеры соответствий:
- "Чем вы гордитесь?" ≈ "Чем ты гордишься больше всего?"
- "Опиши своё состояние" ≈ "Как ты себя чувствуешь сейчас?"
- "О чём мечтаешь?" ≈ "Какие у тебя мечты о будущем?"

НЕ являются соответствиями:
- "Чем гордишься?" vs "Чего стыдишься?" (противоположный смысл)
- "Как дела на работе?" vs "Как дела в отношениях?" (разные домены)

Отвечай СТРОГО в формате JSON."""

MATCHER_USER = """Найди соответствие для вопроса из базы КНИГИ в базе БОТА.

ВОПРОС ИЗ КНИГИ (v2):
ID: {v2_id}
Текст: "{v2_text}"
Программа: {program}
Кластер: {cluster}

КАНДИДАТЫ ИЗ БАЗЫ БОТА (core):
{candidates}

Верни JSON:
{{
  "match_found": true/false,
  "core_id": "id вопроса из core или null",
  "confidence": 0.0-1.0,
  "reasoning": "почему это соответствие (или почему нет)"
}}

Если уверенность < 0.7, ставь match_found: false."""

QUALITY_SYSTEM = """Ты психотерапевт-редактор, проверяющий качество вопросов для книги самопознания и AI-коуча.

Твоя задача — выбрать ЛУЧШУЮ формулировку вопроса или предложить улучшенную версию.

КРИТЕРИИ:
1. Безопасность — не травмирует, не навешивает ярлыки
2. Приглашение — вопрос приглашает к размышлению, не допрашивает
3. Ясность — понятен без контекста
4. Глубина — достаточно глубоко, но не пугающе
5. Тон — тёплый, уважительный, на "ты"
6. Грамматика — правильный русский язык, буква "ё" где нужно

Отвечай СТРОГО в формате JSON."""

QUALITY_USER = """Сравни две формулировки одного вопроса и выбери лучшую (или предложи улучшенную).

ВАРИАНТ 1 (из книги v2):
"{v2_text}"

ВАРИАНТ 2 (из бота core):
"{core_text}"

КОНТЕКСТ:
- Программа: {program}
- Кластер: {cluster}

Верни JSON:
{{
  "winner": 1 или 2 или 0 (если нужна новая версия),
  "best_text": "лучший текст вопроса",
  "changes_made": ["что изменено"],
  "reasoning": "почему этот выбор"
}}"""


# ═══════════════════════════════════════════════════════════════════════════════
# ОСНОВНОЙ КЛАСС
# ═══════════════════════════════════════════════════════════════════════════════

class QuestionMerger:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.v2_data = None
        self.core_data = None
        self.core_questions = {}
        self.matches = []
        self.stats = {
            "total_v2": 0,
            "matched": 0,
            "unmatched": 0,
            "improved": 0
        }

    def load_data(self):
        """Загрузка обеих баз"""
        print("📚 Загрузка v2 (книги)...")
        with open(V2_FILE, encoding="utf-8") as f:
            self.v2_data = json.load(f)

        # Считаем вопросы в v2
        for prog in self.v2_data["programs"]:
            for block in prog["blocks"]:
                self.stats["total_v2"] += len(block["questions"])

        print(f"   Вопросов: {self.stats['total_v2']}")

        print("🤖 Загрузка core (бот)...")
        with open(CORE_FILE, encoding="utf-8") as f:
            self.core_data = json.load(f)

        # Индексируем core вопросы
        for q in self.core_data["questions"]:
            self.core_questions[q["id"]] = q

        print(f"   Вопросов: {len(self.core_questions)}")

    async def call_claude(self, system: str, user: str) -> dict:
        """Вызов Claude API"""
        try:
            message = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}]
            )

            # Парсим JSON из ответа
            text = message.content[0].text
            # Убираем возможные markdown блоки
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())
        except Exception as e:
            print(f"❌ Claude Error: {e}")
            return {"error": str(e)}

    def prepare_candidates(self, v2_text: str, limit: int = 15) -> str:
        """Подготовка списка кандидатов из core для сравнения"""
        # Простая эвристика — берём вопросы с похожими словами
        v2_words = set(v2_text.lower().split())

        scored = []
        for core_id, core_q in self.core_questions.items():
            core_words = set(core_q["text"].lower().split())
            overlap = len(v2_words & core_words)
            if overlap > 0:
                scored.append((overlap, core_id, core_q["text"]))

        # Сортируем по overlap и берём топ
        scored.sort(reverse=True)
        top = scored[:limit]

        # Форматируем для промпта
        lines = []
        for i, (_, core_id, text) in enumerate(top, 1):
            lines.append(f"{i}. ID: {core_id}\n   Текст: \"{text}\"")

        return "\n\n".join(lines) if lines else "Кандидатов не найдено"

    async def find_match(self, v2_q: dict, program: str, cluster: str) -> dict:
        """Найти соответствие для одного вопроса"""
        candidates = self.prepare_candidates(v2_q["text"])

        user_prompt = MATCHER_USER.format(
            v2_id=v2_q["id"],
            v2_text=v2_q["text"],
            program=program,
            cluster=cluster,
            candidates=candidates
        )

        result = await self.call_claude(MATCHER_SYSTEM, user_prompt)

        if "error" in result:
            return {"match_found": False, "error": result["error"]}

        return result

    async def improve_question(self, v2_text: str, core_text: str,
                                program: str, cluster: str) -> dict:
        """Выбрать лучшую формулировку"""
        user_prompt = QUALITY_USER.format(
            v2_text=v2_text,
            core_text=core_text,
            program=program,
            cluster=cluster
        )

        result = await self.call_claude(QUALITY_SYSTEM, user_prompt)

        if "error" in result:
            return {"winner": 1, "best_text": v2_text, "error": result["error"]}

        return result

    async def process_question(self, v2_q: dict, program: str, cluster: str) -> dict:
        """Полная обработка одного вопроса"""
        # 1. Найти соответствие
        match = await self.find_match(v2_q, program, cluster)

        result = {
            "v2_id": v2_q["id"],
            "v2_text": v2_q["text"],
            "program": program,
            "cluster": cluster,
            "match_found": match.get("match_found", False),
            "core_id": match.get("core_id"),
            "confidence": match.get("confidence", 0),
            "final_text": v2_q["text"],
            "core_metadata": None
        }

        # 2. Если нашли соответствие — выбираем лучшую формулировку
        if result["match_found"] and result["core_id"]:
            core_q = self.core_questions.get(result["core_id"])
            if core_q:
                # Сохраняем метаданные из core
                result["core_metadata"] = {
                    "classification": core_q.get("classification"),
                    "psychology": core_q.get("psychology"),
                    "processing_hints": core_q.get("processing_hints")
                }

                # Выбираем лучшую формулировку
                improvement = await self.improve_question(
                    v2_q["text"], core_q["text"], program, cluster
                )
                result["final_text"] = improvement.get("best_text", v2_q["text"])
                result["changes"] = improvement.get("changes_made", [])

                if result["final_text"] != v2_q["text"]:
                    self.stats["improved"] += 1

            self.stats["matched"] += 1
        else:
            self.stats["unmatched"] += 1

        return result

    async def run_analysis(self, sample_size: Optional[int] = None):
        """Анализ соответствий"""
        print("\n" + "═" * 60)
        print("🔍 АНАЛИЗ СООТВЕТСТВИЙ (Claude)")
        print("═" * 60)

        results = []
        count = 0

        for prog in self.v2_data["programs"]:
            for block in prog["blocks"]:
                for q in block["questions"]:
                    if sample_size and count >= sample_size:
                        break

                    print(f"\r   Обработка: {count + 1}/{sample_size or self.stats['total_v2']}", end="")

                    result = await self.process_question(q, prog["name"], block["name"])
                    results.append(result)
                    self.matches.append(result)
                    count += 1

                    # Rate limiting
                    await asyncio.sleep(0.5)

                if sample_size and count >= sample_size:
                    break
            if sample_size and count >= sample_size:
                break

        print("\n")
        self.print_stats()
        return results

    def print_stats(self):
        """Вывод статистики"""
        print("\n" + "─" * 40)
        print("📊 СТАТИСТИКА")
        print("─" * 40)
        print(f"   Обработано: {self.stats['matched'] + self.stats['unmatched']}")
        print(f"   ✅ Найдено соответствий: {self.stats['matched']}")
        print(f"   ❌ Без соответствия: {self.stats['unmatched']}")
        print(f"   ✏️  Улучшено формулировок: {self.stats['improved']}")

        if self.matches:
            match_rate = self.stats['matched'] / len(self.matches) * 100
            print(f"   📈 Match rate: {match_rate:.1f}%")

    def show_matches(self, limit: int = 20):
        """Показать найденные соответствия"""
        print("\n" + "═" * 60)
        print("🔗 НАЙДЕННЫЕ СООТВЕТСТВИЯ")
        print("═" * 60)

        matched = [m for m in self.matches if m["match_found"]]

        for i, m in enumerate(matched[:limit], 1):
            print(f"\n{i}. [{m['program']} → {m['cluster']}]")
            print(f"   Confidence: {m['confidence']:.0%}")
            print(f"   V2: {m['v2_text'][:60]}...")
            if m["final_text"] != m["v2_text"]:
                print(f"   → Final: {m['final_text'][:60]}...")
            if m.get("changes"):
                print(f"   Изменения: {', '.join(m['changes'])}")

        if len(matched) > limit:
            print(f"\n   ... и ещё {len(matched) - limit}")

    def save_results(self, output_file: Optional[Path] = None):
        """Сохранение результатов"""
        output = output_file or OUTPUT_FILE

        results = {
            "generated_at": datetime.now().isoformat(),
            "stats": self.stats,
            "matches": self.matches
        }

        with open(output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Результаты сохранены: {output}")


async def main():
    parser = argparse.ArgumentParser(description="AI Question Merger (Claude)")
    parser.add_argument("--analyze", action="store_true", help="Анализ соответствий")
    parser.add_argument("--sample", type=int, help="Ограничить количество (для теста)")
    args = parser.parse_args()

    merger = QuestionMerger()
    merger.load_data()

    sample = args.sample or 10  # По умолчанию 10 для теста

    print(f"\n⚠️  Тестовый режим: обработка {sample} вопросов")
    print("   Для полного прогона используй --sample N с нужным числом")

    await merger.run_analysis(sample_size=sample)
    merger.show_matches()
    merger.save_results(DATA_DIR / f"merge_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")


if __name__ == "__main__":
    asyncio.run(main())
